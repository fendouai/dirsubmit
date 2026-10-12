"""Recipe browser execution with confirmation, evidence and agent handoff."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Dict
from .models import Copy, Product, Recipe


def resolve_value(source: str, product: Product, copy: Copy) -> str:
    owner, key = (copy, source[3:]) if source.startswith("ai.") else (product, source)
    indexed = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\[([0-9]+)\]", key)
    if indexed:
        items = getattr(owner, indexed[1], "")
        if not isinstance(items, list):
            return ""
        try:
            index = int(indexed[2])
        except ValueError:
            return ""
        value = items[index] if index < len(items) else ""
    else:
        value = getattr(owner, key, "")
    return ", ".join(str(x) for x in value) if isinstance(value, list) else str(value or "")


def build_values(recipe, product, copy):
    values = {}
    for field in recipe.fields:
        if field.submit:
            continue
        value = field.file_path or resolve_value(field.source, product, copy)
        if field.value_map and value:
            if value not in field.value_map:
                raise ValueError(f"{field.name}: unsupported directory value; no fallback selected")
            value = field.value_map[value]
        values[field.name] = value
    return values


def validate_values(recipe, values):
    """Validate supplied facts before opening a browser; never truncate or guess."""
    errors = []
    for field in recipe.fields:
        if field.submit:
            continue
        value = values.get(field.name, "")
        if field.required and not value.strip():
            errors.append(f"{field.name}: missing required value")
            continue
        if not value and not field.required:
            continue
        rules = field.constraints
        for key, size in (("length", len(value)), ("words", len(value.split()))):
            if "min_" + key in rules and size < rules["min_" + key]:
                errors.append(f"{field.name}: below minimum {key}")
            if "max_" + key in rules and size > rules["max_" + key]:
                errors.append(f"{field.name}: exceeds maximum {key}")
        if "allowed" in rules and value not in rules["allowed"]:
            errors.append(f"{field.name}: unsupported allowed value")
        if rules.get("pattern") and not re.fullmatch(rules["pattern"], value):
            errors.append(f"{field.name}: invalid format")
    return errors


def make_cheatsheet(recipe, product, copy):
    lines = [f"# {recipe.name} 提交清单", "", f"- 提交页：{recipe.submit_url}",
             f"- DR：{recipe.dr} | tier：{recipe.tier} | 需登录：{recipe.requires_auth}", ""]
    values = build_values(recipe, product, copy)
    lines.extend(f"- **{f.name}** ({f.type})：{values[f.name]}"
                 for f in recipe.fields if not f.submit)
    return "\n".join(lines)


def _find(page, selector, include_hidden=False):
    for frame in page.frames:
        try:
            for loc in frame.locator(selector).all():
                if include_hidden or loc.is_visible():
                    return loc
        except Exception:
            continue
    return None


def _fill(page, field, value, submit_selector=""):
    for selector in field.selectors or [f'[name="{field.name}"]']:
        loc = _find(page, selector, include_hidden=field.type == "file")
        if loc is None:
            continue
        try:
            if field.type == "file":
                loc.set_input_files(value)
            elif field.type == "select":
                try:
                    loc.select_option(value=value)
                except Exception:
                    loc.select_option(label=value)
            elif field.type == "checkbox":
                loc.set_checked(value.lower() in {"true", "yes", "1"})
            elif field.type == "radio":
                loc.check()
            else:
                loc.fill(value)
            return True
        except Exception:
            continue
    return False


def _confirmed(page, success):
    if "all_of" in success:
        conditions = success["all_of"]
        return bool(conditions) and all(_condition_matches(page, condition) for condition in conditions)
    if success.get("url_equals") and success["url_equals"] == page.url:
        return True
    if success.get("url_contains") and success["url_contains"] in page.url:
        return True
    if success.get("selector") and _find(page, success["selector"]):
        return True
    if success.get("text"):
        return any(success["text"] in frame.locator("body").inner_text()
                   for frame in page.frames if frame.locator("body").count())
    return False


def _condition_matches(page, condition):
    """New AND conditions inspect visible content in the main document only."""
    if condition.get("url_equals") and page.url != condition["url_equals"]:
        return False
    if condition.get("url_contains") and condition["url_contains"] not in page.url:
        return False
    texts = list(condition.get("texts", []))
    if condition.get("text"):
        texts.append(condition["text"])
    if condition.get("selector") or texts:
        try:
            matches = page.main_frame.locator(condition.get("selector", "body")).all()
            return any(loc.is_visible() and all(text in loc.inner_text() for text in texts) for loc in matches)
        except Exception:
            return False
    return bool(condition.get("url_equals") or condition.get("url_contains"))


def _guard_expected(check, values):
    return check["value"] if "value" in check else values[check["field"]]


def _pre_submit_error(page, checks, values):
    """Read DOM properties, including hidden honeypots, immediately before click."""
    for check in checks:
        try:
            matches = []
            for frame in page.frames:
                matches.extend(loc for loc in frame.locator(check["selector"]).all()
                               if check.get("include_hidden") or loc.is_visible())
            if len(matches) != 1:
                return "Pre-submit check needs exactly one matching input; no submission"
            if matches[0].input_value() != _guard_expected(check, values):
                return "Pre-submit DOM value changed or unsafe plan/honeypot value; no submission"
        except Exception:
            return "Unable to read a required pre-submit DOM value; no submission"
    return ""


class _PreSubmitBlocked(ValueError):
    pass


def _launch_browser(playwright, cdp_url=None):
    if cdp_url:
        return playwright.chromium.connect_over_cdp(cdp_url)
    options = {"headless": True}
    if os.environ.get("DIRSUBMIT_BROWSER_EXECUTABLE"):
        options["executable_path"] = os.environ["DIRSUBMIT_BROWSER_EXECUTABLE"]
    try:
        return playwright.chromium.launch(**options)
    except Exception as exc:
        if "executable_path" in options or "Executable doesn't exist" not in str(exc):
            raise
        # Use installed Chrome with an isolated temporary profile, never its user profile.
        return playwright.chromium.launch(headless=True, channel="chrome")


def _run_playwright(recipe, values, cdp_url, fill_only=False, evidence_dir="runs", timeout=15):
    from playwright.sync_api import sync_playwright
    import uuid
    errors = validate_values(recipe, values)
    if errors:
        return "blocked", "; ".join(errors)
    with sync_playwright() as p:
        browser = _launch_browser(p, cdp_url)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        clicked = False
        status, note = "failed", ""
        try:
            page.goto(recipe.submit_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(recipe.wait_ms)
            if recipe.success and _confirmed(page, recipe.success):
                raise _PreSubmitBlocked("提交前已存在确认信号，需人工核验，未点击提交")
            for step in recipe.steps:
                if step["action"] == "wait":
                    page.wait_for_timeout(step.get("ms", 500))
                else:
                    loc = _find(page, step["selector"])
                    if loc is None:
                        raise ValueError(f"Missing step selector: {step['selector']}")
                    if step["action"] == "click":
                        loc.click()
                    else:
                        loc.fill(values.get(step.get("field", ""), step.get("value", "")))
            auth_selector = recipe.auth.get("logged_in_selector")
            login_required = recipe.auth.get("login_required_selector")
            if (auth_selector and not _find(page, auth_selector)) or (login_required and _find(page, login_required)):
                status, note = "needs_auth", "登录后可重跑；Google/邮箱验证请使用 browser-use 或 computer-use"
            else:
                missing = [f.name for f in recipe.fields if not f.submit and
                           not _fill(page, f, values.get(f.name, ""))]
                required = [f.name for f in recipe.fields if f.required and not f.submit and f.name in missing]
                if required:
                    status, note = "blocked", f"必填字段未填：{required}；未点击提交"
                elif fill_only:
                    status, note = "filled", f"仅填表；缺少可选字段：{missing}"
                else:
                    btn = _find(page, recipe.submit_selector) if recipe.submit_selector else None
                    if btn is None:
                        status, note = "blocked", "未找到提交按钮；请使用 agent 接管"
                    else:
                        # From here on failures are uncertain; never retry final clicks.
                        if recipe.success and _confirmed(page, recipe.success):
                            raise _PreSubmitBlocked("提交前已存在确认信号，需人工核验，未点击提交")
                        guard_error = _pre_submit_error(page, recipe.pre_submit_checks, values)
                        if guard_error:
                            raise _PreSubmitBlocked(guard_error)
                        clicked = True
                        btn.click(timeout=5000)
                        deadline = time.monotonic() + timeout
                        while recipe.success and time.monotonic() < deadline:
                            if _confirmed(page, recipe.success):
                                status, note = "submitted", "已看到目录确认信号"
                                break
                            page.wait_for_timeout(250)
                        else:
                            status, note = "unverified", "已尝试提交，未看到确认信号；禁止自动重复提交"
        except Exception as exc:
            status = "unverified" if clicked else "blocked" if isinstance(exc, _PreSubmitBlocked) else "failed"
            note = f"{type(exc).__name__}: {exc}"
        finally:
            evidence = Path(evidence_dir) / f"{recipe.slug}-{uuid.uuid4().hex}"
            evidence.mkdir(parents=True, exist_ok=True)
            try:
                page.screenshot(path=str(evidence / "page.png"), full_page=True)
                (evidence / "result.json").write_text(json.dumps({"status": status, "note": note, "url": page.url}, ensure_ascii=False), encoding="utf-8")
                note += f"；证据：{evidence}"
            except Exception:
                pass
            # Leave user's CDP page and browser open for OAuth/dialog recovery.
            if not cdp_url:
                browser.close()
        return status, note


def _run_extension(recipe, values, bridge, fill_only=False, timeout=15):
    if recipe.pre_submit_checks or "all_of" in recipe.success:
        return "blocked", "扩展不支持精确 DOM 守卫/AND 回执；请使用 headless/CDP 或 agent 接管"
    errors = validate_values(recipe, values)
    if errors:
        return "blocked", "; ".join(errors)
    if bridge is None or not bridge.connected():
        return "failed", "扩展未连接"
    r = bridge.call("navigate", url=recipe.submit_url)
    if r.get("status") != "ok":
        return "failed", f"导航失败：{r.get('error')}"
    bridge.call("wait", ms=recipe.wait_ms)
    for step in recipe.steps:
        args = {k: v for k, v in step.items() if k != "action"}
        if step["action"] == "fill":
            args["value"] = values.get(args.pop("field", ""), args.get("value", ""))
        if bridge.call(step["action"], **args).get("status") != "ok":
            return "blocked", "预备步骤失败；未提交"
    if recipe.auth.get("login_required_selector"):
        r = bridge.call("inspect", selector=recipe.auth["login_required_selector"])
        if r.get("result", {}).get("found"):
            return "needs_auth", "需要登录；请接管浏览器后重跑"
    if recipe.auth.get("logged_in_selector"):
        r = bridge.call("inspect", selector=recipe.auth["logged_in_selector"])
        if not r.get("result", {}).get("found"):
            return "needs_auth", "需要登录；请接管浏览器后重跑"
    missing = []
    for f in recipe.fields:
        if f.submit:
            continue
        if f.type == "file":
            missing.append(f.name)
            continue
        for sel in f.selectors or [f'[name="{f.name}"]']:
            if bridge.call("fill", selector=sel, value=values.get(f.name, ""), type=f.type).get("status") == "ok":
                break
        else:
            missing.append(f.name)
    required = [f.name for f in recipe.fields if f.required and f.name in missing]
    if required:
        return "blocked", f"必填字段未填：{required}；未提交（文件请用 CDP/Computer Use 上传）"
    if fill_only:
        return "filled", f"仅填表；缺少可选字段：{missing}"
    if not recipe.submit_selector:
        return "blocked", "未配置提交按钮"
    if recipe.success:
        before = bridge.call("inspect", **recipe.success)
        if before.get("result", {}).get("confirmed"):
            return "blocked", "提交前已存在确认信号，未点击提交"
    r = bridge.call("click", selector=recipe.submit_selector)
    if r.get("status") != "ok":
        return "unverified", "点击结果不确定；请检查浏览器，勿自动重试"
    deadline = time.monotonic() + timeout
    while recipe.success and time.monotonic() < deadline:
        r = bridge.call("inspect", **recipe.success)
        if r.get("result", {}).get("confirmed"):
            return "submitted", f"已看到确认信号；{r.get('result')}"
        bridge.call("wait", ms=250)
    return "unverified", "已点击，未看到确认信号；禁止自动重复提交"


def cdp_available(cdp_url):
    try:
        import requests
        return requests.get(cdp_url.rstrip("/") + "/json/version", timeout=2).ok
    except Exception:
        return False


def resolve_mode(recipe, bridge, cdp_url):
    if recipe.tier == "manual":
        return "manual", ""
    if recipe.tier == "auto" and not recipe.requires_auth:
        return "headless", ""
    if bridge is not None and bridge.connected():
        return "extension", ""
    if cdp_available(cdp_url):
        return "cdp", ""
    return None, "需要登录态：请连接 Chrome 扩展/CDP，或使用 --mode computer-use 接管"


def submit(recipe, product, copy, mode="auto", cdp_url="http://localhost:9222",
           dry_run=False, bridge=None, fill_only=False, evidence_dir="runs", max_steps=60, computer_command=None):
    try:
        values = build_values(recipe, product, copy)
    except ValueError as exc:
        return "blocked", str(exc)
    if dry_run:
        return "dry-run", "仅演练，未实际提交"
    errors = validate_values(recipe, values)
    if errors:
        return "blocked", "; ".join(errors)
    if mode == "computer-use":
        from .automation import task_payload, save_task, run_computer_use
        payload = task_payload(recipe, product, copy, fill_only)
        path = save_task(payload, evidence_dir)
        command = computer_command or os.environ.get("DIRSUBMIT_COMPUTER_COMMAND")
        if command:
            status, note = run_computer_use(payload, command)
            path.with_suffix(".result.json").write_text(json.dumps({"status": status, "note": note}, ensure_ascii=False), encoding="utf-8")
            return status, f"{note}；任务：{path}"
        return "needs_handoff", f"Computer Use 接管任务：{path}；结果使用 dirsubmit resume 导入"
    if recipe.tier == "manual" and mode != "browser-use":
        return "manual", "已生成粘贴清单，需人工提交"
    if mode == "browser-use":
        from .automation import task_payload, save_task, run_browser_use
        payload = task_payload(recipe, product, copy, fill_only)
        path = save_task(payload, evidence_dir)
        status, note = run_browser_use(payload, cdp_url, max_steps)
        path.with_suffix(".result.json").write_text(json.dumps({"status": status, "note": note}, ensure_ascii=False), encoding="utf-8")
        return status, f"{note}；任务：{path}"
    if mode == "auto":
        mode, error = resolve_mode(recipe, bridge, cdp_url)
        if mode is None:
            return "needs_auth", error
    try:
        if mode == "extension":
            return _run_extension(recipe, values, bridge, fill_only)
        if mode not in {"headless", "cdp"}:
            return "failed", f"Unknown mode: {mode}"
        if (recipe.requires_auth or recipe.tier == "semi") and mode == "headless":
            return "needs_auth", "需要真实浏览器登录态，使用 CDP/extension/browser-use/computer-use"
        return _run_playwright(recipe, values, cdp_url if mode == "cdp" else None, fill_only, evidence_dir)
    except Exception as exc:
        return "failed", f"提交异常：{exc}"


def cheatsheet_file(recipe, product, copy, out_dir="cheatsheets"):
    import hashlib
    path = Path(out_dir) / hashlib.sha256(product.url.encode()).hexdigest()[:12] / f"{recipe.slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(make_cheatsheet(recipe, product, copy), encoding="utf-8")
    return str(path)
