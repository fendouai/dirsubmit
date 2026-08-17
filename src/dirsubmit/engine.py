"""提交引擎：headless + CDP 双模式，按 tier 分发。"""

from __future__ import annotations

from typing import Dict, List

from .models import Copy, Product, Recipe

_AI_SOURCES = {"ai.tagline", "ai.description", "ai.category", "ai.tags"}


def resolve_value(source: str, product: Product, copy: Copy) -> str:
    """把字段 source 解析成实际要填的值。"""
    if source.startswith("ai."):
        key = source[3:]
        if key == "tags":
            return ", ".join(copy.tags)
        return getattr(copy, key, "") or ""
    val = getattr(product, source, "")
    if isinstance(val, list):
        return ", ".join(str(x) for x in val)
    return str(val or "")


def build_values(recipe: Recipe, product: Product, copy: Copy) -> Dict[str, str]:
    """按 recipe 的 fields 生成 name -> value 映射。"""
    values = {}
    for f in recipe.fields:
        if f.submit:
            continue
        values[f.name] = f.file_path or resolve_value(f.source, product, copy)
    return values


def make_cheatsheet(recipe: Recipe, product: Product, copy: Copy) -> str:
    """manual 档：生成人肉粘贴清单。"""
    lines = [f"# {recipe.name} 提交清单", "",
             f"- 提交页：{recipe.submit_url}",
             f"- DR：{recipe.dr} | tier：{recipe.tier} | 需登录：{recipe.requires_auth}", ""]
    for f in recipe.fields:
        if f.submit:
            continue
        val = resolve_value(f.source, product, copy)
        lines.append(f"- **{f.name}** ({f.type})：{val}")
    lines += ["", "（复制以上内容，人工到提交页粘贴）"]
    return "\n".join(lines)


def _find(page, sel):
    """跨 frame 定位：先主 frame，再子 iframe。返回 locator 或 None。"""
    loc = page.locator(sel).first
    try:
        if loc.count() > 0:
            return loc
    except Exception:
        pass
    for fr in page.frames:
        try:
            floc = fr.locator(sel).first
            if floc.count() > 0:
                return floc
        except Exception:
            continue
    return None


def _fill(page, field, value: str, submit_selector: str) -> bool:
    """填单个字段，按 selectors 顺序尝试（跨 iframe）。返回是否填到。"""
    from playwright.sync_api import TimeoutError as PWTimeout

    selectors = field.selectors or [f"[name='{field.name}']"]
    for sel in selectors:
        loc = _find(page, sel)
        if loc is None:
            continue
        try:
            if field.type == "file":
                loc.set_input_files(value)
                return True
            loc.wait_for(state="visible", timeout=5000)
            if field.type in ("select",):
                loc.select_option(value)
            elif field.type == "checkbox":
                if value and value.lower() in ("true", "yes", "1"):
                    loc.check()
            else:
                loc.fill(value)
            return True
        except PWTimeout:
            continue
        except Exception:
            continue
    return False


def _run_playwright(recipe: Recipe, values: Dict[str, str], cdp_url: str | None):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        if cdp_url:
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
        else:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

        page.goto(recipe.submit_url, timeout=30000, wait_until="domcontentloaded")
        if recipe.wait_ms:
            page.wait_for_timeout(recipe.wait_ms)

        missing = []
        for f in recipe.fields:
            if f.submit:
                continue
            if not _fill(page, f, values.get(f.name, ""), recipe.submit_selector):
                missing.append(f.name)
                print(f"    [warn] 未定位到字段 {f.name}（tried {f.selectors or []}）")

        # 文件上传是异步的，等上传完成再提交
        if any(f.type == "file" for f in recipe.fields):
            page.wait_for_timeout(5000)

        submitted = False
        if recipe.submit_selector:
            try:
                btn = _find(page, recipe.submit_selector)
                if btn is not None:
                    btn.click(timeout=5000)
                    submitted = True
                else:
                    print("    [warn] 未找到提交按钮，表单已填，请人工确认")
            except Exception:
                print("    [warn] 提交按钮点击失败，表单已填，请人工确认")

        page.wait_for_timeout(1500)
        browser.close()
        return submitted, missing


def _run_extension(recipe: Recipe, values: Dict[str, str], bridge):
    """通过 Chrome 扩展（本地 WebSocket）填表提交。返回 (submitted, missing)。"""
    if bridge is None or not bridge.connected():
        return False, ["扩展未连接（先加载 extension/ 并点一下扩展图标唤醒）"]

    r = bridge.call("navigate", url=recipe.submit_url, timeout=30)
    if r.get("status") != "ok":
        return False, [f"导航失败：{r.get('error')}"]

    if recipe.wait_ms:
        bridge.call("wait", ms=recipe.wait_ms)

    missing = []
    for f in recipe.fields:
        if f.submit:
            continue
        if f.type == "file":
            print(f"    [warn] 扩展模式暂不支持文件上传（{f.name}），跳过")
            continue
        filled = False
        for sel in (f.selectors or [f"[name='{f.name}']"]):
            r = bridge.call("fill", selector=sel,
                            value=values.get(f.name, ""), type=f.type)
            if r.get("status") == "ok":
                filled = True
                break
        if not filled:
            missing.append(f.name)
            print(f"    [warn] 未定位到字段 {f.name}（tried {f.selectors or []}）")

    submitted = False
    if recipe.submit_selector:
        r = bridge.call("click", selector=recipe.submit_selector)
        submitted = r.get("status") == "ok"

    bridge.call("wait", ms=1500)
    return submitted, missing


def submit(recipe: Recipe, product: Product, copy: Copy, mode: str = "headless",
           cdp_url: str = "http://localhost:9222", dry_run: bool = False,
           bridge=None):
    """返回 (status, note)。mode ∈ headless|cdp|extension。"""
    values = build_values(recipe, product, copy)

    if recipe.tier == "manual":
        return "manual", "已生成粘贴清单，需人工提交"

    if dry_run:
        return "dry-run", "仅演练，未实际提交"

    if mode == "extension":
        submitted, missing = _run_extension(recipe, values, bridge)
        note = "已提交" if submitted else "表单已填，未确认提交"
        if missing:
            note += f"；缺字段 {missing}"
        return "submitted" if submitted else "failed", note

    if recipe.tier == "semi" and mode != "cdp":
        return ("failed",
                "semi 目录需登录态，请用 --mode cdp（先以调试端口启动 Chrome 并登录该站）或 --mode extension（Chrome 扩展）")

    cdp = cdp_url if (recipe.tier == "semi" or mode == "cdp") else None
    try:
        submitted, missing = _run_playwright(recipe, values, cdp)
    except Exception as e:  # noqa: BLE001
        return "failed", f"提交异常：{e}"

    note = "已提交" if submitted else "表单已填，未确认提交"
    if missing:
        note += f"；缺字段 {missing}"
    return "submitted" if submitted else "failed", note


def cheatsheet_file(recipe: Recipe, product: Product, copy: Copy, out_dir: str = "cheatsheets"):
    from pathlib import Path

    d = Path(out_dir)
    d.mkdir(exist_ok=True)
    p = d / f"{recipe.slug}.md"
    p.write_text(make_cheatsheet(recipe, product, copy), encoding="utf-8")
    return str(p)
