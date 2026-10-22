#!/usr/bin/env python3
"""Rebuild three offline catalogues from immutable snapshots and additive targets.

Run from any directory: python3 docs/submission-catalog/generate_catalog.py
Add verified changes to actual-result-overrides.json; snapshots are never edited.
Add newly researched targets to additional-targets.json, preserving provenance.
Only confirmed receipt/publication changes should upgrade a product result to A/S.
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRODUCTS = ("botstest", "warmquant", "weworkbuddy")
PRODUCT_NAMES = {"botstest": "Botstest", "warmquant": "WarmQuant", "weworkbuddy": "WeWorkBuddy"}
GRADE_ORDER = "SABCDU"
GRADES = {
    "S": "已公开上线或 PR 已合并并核实条目",
    "A": "已确认提交、投递或开放 PR；审核、采用或合并待定",
    "B": "免费路径与适配已核验，可继续执行，尚未发送",
    "C": "登录、验证、事实、规则、适配或实际回执仍待处理",
    "D": "已审查路径仅付费、关闭、失效或不符合要求",
    "U": "未评估或当前证据不足；数据库记录不等于实测",
}
SPECS = (
    ("directories", "目录站与导航站", "runs/category1-directory-universe-2026-10-10.json", 1835),
    ("awesome-repositories", "GitHub awesome 仓库", "runs/category2-awesome-universe-2026-10-10.json", 70),
    ("editorial-outlets", "博客、网站与新闻投稿", "runs/category3-editorial-universe-2026-10-10.json", 66),
)
INITIAL_OVERRIDE = {
    "category": "awesome-repositories",
    "target_key": "techiediaries/awesome-technical-writing-blogging-resources",
    "product": "warmquant",
    "grade": "A",
    "state": "confirmed_open_PR",
    "reason": "原生 Chrome 已创建 PR #1；官方公开 GitHub API 核实作者、正确提交和 README 单行新增。等待维护者审核，尚未合并。",
    "receipt_links": ["https://github.com/techiediaries/Awesome-Technical-Writing-Blogging-Resources/pull/1"],
    "evidence": ["runs/github-techiediaries-warmquant-public-confirmation-2026-10-10.json"],
    "confirmed": True,
    "submitted": True,
    "free_path_verified": True,
    "verified_at": "2026-10-10T08:20:58.144487+00:00",
    "next_action": "等待维护者审核；不要重复提交。只有合并后的公开条目可升为 S。",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def identity(override):
    return (str(override.get("category", "")).lower(), str(override.get("target_key", "")).lower(), str(override.get("product", "")).lower())


def ensure_overrides():
    """Seed PR #1 once; leave future root additions and newer same-pair updates intact."""
    path = HERE / "actual-result-overrides.json"
    if path.exists():
        data = load(path)
        if not isinstance(data, dict) or not isinstance(data.get("overrides"), list):
            raise ValueError("actual-result-overrides.json must have an overrides array")
    else:
        data = {
            "schema_version": 1,
            "instructions": "追加真实回执或公开结果。category 为三份文件的 slug；target_key 为对应 JSON 目标键；product 为三个产品之一。同一产品目标多条更新按数组顺序依次合并，最后字段生效；证据与回执链接去重保留。未经实际确认不要升为 A/S。此文件不会被生成器重置。",
            "overrides": [],
        }
    if not any(identity(item) == identity(INITIAL_OVERRIDE) for item in data["overrides"]):
        data["overrides"].append(copy.deepcopy(INITIAL_OVERRIDE))
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def unique_strings(*groups):
    out = []
    for group in groups:
        if isinstance(group, str):
            group = [group]
        for value in group or []:
            if isinstance(value, str) and value and value not in out:
                out.append(value)
    return out


def links_from_result(result):
    links = unique_strings(result.get("PR_urls"), result.get("receipt_links"))
    for key in ("live_url", "result_url", "receipt_url", "url"):
        value = result.get(key)
        if isinstance(value, str) and value.startswith(("https://", "http://")):
            links = unique_strings(links, [value])
    receipt = result.get("receipt")
    if isinstance(receipt, str) and receipt.startswith(("https://", "http://")):
        links = unique_strings(links, [receipt])
    elif isinstance(receipt, dict):
        links = unique_strings(links, [v for k, v in receipt.items() if isinstance(v, str) and v.startswith(("https://", "http://"))])
    return links


def normalize_target(category, original, source_path):
    key = original.get("target_key") or original.get("repository") or original.get("destination_key")
    if not key:
        raise ValueError(f"missing target key in {source_path}: {original.get('name')}")
    key = str(key).lower()
    url = original.get("url") or original.get("submission_url")
    source_refs = unique_strings(original.get("source_refs"), original.get("official_sources"), original.get("category1_source_refs"), original.get("evidence_files"), [source_path])
    results = original.get("product_results") or original.get("products") or original.get("grades") or {}
    target = {
        "target_key": key,
        "name": original.get("name", original.get("repository", key)),
        "category": category,
        "url": url,
        "submission_url": original.get("submission_url", url),
        "canonical_domain": original.get("canonical_domain") or (urlparse(url or "").hostname or "").removeprefix("www."),
        "aliases": unique_strings(original.get("aliases"), original.get("category1_aliases")),
        "source_refs": source_refs,
        "source_row_ids": unique_strings(original.get("source_row_ids"), original.get("category1_source_row_ids")),
        "source_snapshot": source_path,
        "product_results": {},
    }
    # Keep useful original target-level requirements/history, explicitly dated to the snapshot.
    omitted = {"target_key", "destination_key", "repository", "name", "category", "url", "submission_url", "canonical_domain", "aliases", "category1_aliases", "source_refs", "official_sources", "category1_source_refs", "evidence_files", "source_row_ids", "category1_source_row_ids", "products", "product_results", "grades", "grade", "suggested_grade", "has_confirmed_submission", "has_unassessed_product"}
    target["snapshot_context"] = {k: copy.deepcopy(v) for k, v in original.items() if k not in omitted}
    for product in PRODUCTS:
        previous = copy.deepcopy(results.get(product, {}))
        grade = previous.get("grade", "U")
        if grade not in GRADES:
            raise ValueError(f"invalid grade {grade}: {category}/{key}/{product}")
        evidence = unique_strings(previous.get("evidence"), previous.get("evidence_files"), original.get("evidence_files"))
        reason = previous.get("reason") or previous.get("receipt_summary") or previous.get("fit") or "该产品与目标的免费路径和适配尚未充分评估。"
        target["product_results"][product] = {
            **previous,
            "grade": grade,
            "state": previous.get("state", previous.get("status", "not_evaluated_for_product")),
            "reason": reason,
            "evidence": evidence,
            "receipt_links": links_from_result(previous),
            "next_action": previous.get("next_action") or original.get("next_action") or ("等待审核；不得重复提交。" if grade == "A" else "先核实当前官方规则、免费路径与该产品查重，再按正常流程处理。"),
            "free_path_verified": previous.get("free_path_verified", grade in ("S", "A", "B")),
            "confirmed": previous.get("confirmed", grade in ("S", "A")),
        }
    return target


def append_additional_targets(catalogs, path=None):
    """Validate the complete additive source before changing in-memory catalogues."""
    path = Path(path) if path is not None else HERE / "additional-targets.json"
    categories = {category for category, _, _, _ in SPECS}
    by_category = {catalog["category"]: catalog for catalog in catalogs}
    if set(by_category) != categories or len(by_category) != len(catalogs):
        raise ValueError("additional targets require exactly the three base catalogues")
    counts = {category: 0 for category in by_category}
    if not path.exists():
        for catalog in catalogs:
            catalog["additional_sources"] = []
            catalog["additional_source_target_count"] = 0
            catalog["combined_expected_targets"] = len(catalog["targets"])
        return {"path": None, "sha256": None, "target_count": 0, "targets_per_category": counts}
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("targets"), list):
        raise ValueError("additional-targets.json must have a targets array")
    try:
        source_path = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        source_path = path.resolve().as_posix()
    seen = {(catalog["category"], target["target_key"]) for catalog in catalogs for target in catalog["targets"]}
    staged = []
    for i, original in enumerate(data["targets"]):
        if not isinstance(original, dict):
            raise ValueError(f"additional target[{i}] must be an object")
        category = original.get("category")
        if not isinstance(category, str) or category not in categories:
            raise ValueError(f"additional target[{i}] invalid category: {category}")
        key = original.get("target_key")
        if not isinstance(key, str) or not key or key != key.strip():
            raise ValueError(f"additional target[{i}] requires a nonempty target_key without surrounding whitespace")
        results = original.get("product_results") or original.get("products") or original.get("grades")
        if not isinstance(results, dict) or set(results) != set(PRODUCTS) or any(not isinstance(results[p], dict) for p in PRODUCTS):
            raise ValueError(f"additional target[{i}] must provide exactly all three product result objects")
        target = normalize_target(category, original, source_path)
        ident = (category, target["target_key"])
        if ident in seen:
            raise ValueError(f"additional target[{i}] duplicate target identity: {ident}")
        seen.add(ident)
        counts[category] += 1
        staged.append(target)
    metadata = {
        "path": source_path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "target_count": len(staged),
        "targets_per_category": counts,
        "provenance": copy.deepcopy(data.get("provenance", {})),
    }
    for catalog in catalogs:
        category = catalog["category"]
        catalog["additional_sources"] = [{**copy.deepcopy(metadata), "category_target_count": counts[category]}] if counts[category] else []
        catalog["additional_source_target_count"] = counts[category]
        catalog["combined_expected_targets"] = len(catalog["targets"]) + counts[category]
    for target in staged:
        by_category[target["category"]]["targets"].append(target)
    return metadata


def apply_overrides(catalogs, override_data):
    lookup = {(cat["category"], t["target_key"], product): t["product_results"][product] for cat in catalogs for t in cat["targets"] for product in PRODUCTS}
    applied = []
    for i, override in enumerate(override_data["overrides"]):
        ident = identity(override)
        if ident not in lookup:
            raise ValueError(f"override[{i}] target not found: {ident}")
        if override.get("grade", lookup[ident]["grade"]) not in GRADES:
            raise ValueError(f"override[{i}] invalid grade")
        result = lookup[ident]
        for k, value in override.items():
            if k in ("category", "target_key", "product"):
                continue
            if k in ("evidence", "receipt_links", "PR_urls", "evidence_files"):
                result[k] = unique_strings(result.get(k), value)
            else:
                result[k] = copy.deepcopy(value)
        if "grade" in override and "confirmed" not in override:
            result["confirmed"] = result["grade"] in ("S", "A")
        if "grade" in override and "submitted" not in override and result["grade"] in ("S", "A"):
            result["submitted"] = True
        result["receipt_links"] = unique_strings(result.get("receipt_links"), result.get("PR_urls"))
        result["actual_result_overrides_applied"] = result.get("actual_result_overrides_applied", []) + [i]
        applied.append({"index": i, "category": ident[0], "target_key": ident[1], "product": ident[2], "grade": result["grade"]})
    return applied


def category_counts(targets, category=None):
    per_product = {p: {g: 0 for g in GRADE_ORDER} for p in PRODUCTS}
    pr_urls = set()
    for target in targets:
        for p, result in target["product_results"].items():
            per_product[p][result["grade"]] += 1
            if result["grade"] in ("S", "A"):
                pr_urls.update(u for u in result["receipt_links"] if re_is_pr(u))
    pairs = {g: sum(per_product[p][g] for p in PRODUCTS) for g in GRADE_ORDER}
    counts = {"targets": len(targets), "product_target_pairs": len(targets) * 3, "product_pair_grades": pairs, "per_product_grades": per_product, "confirmed_product_target_pairs": pairs["S"] + pairs["A"], "unique_confirmed_PRs": len(pr_urls)}
    results = [result for target in targets for result in target["product_results"].values()]
    if category == "directories":
        counts.update({"confirmed_directory_applications": pairs["S"] + pairs["A"], "verified_public_directory_listings": pairs["S"]})
    elif category == "awesome-repositories":
        counts.update({"confirmed_PR_product_entries": pairs["S"] + pairs["A"], "verified_merged_public_product_entries": pairs["S"]})
    elif category == "editorial-outlets":
        emails = [r for r in results if r.get("delivery_channel") == "email" and r.get("grade") in ("S", "A")]
        issues = [r for r in results if r.get("delivery_channel") == "github_issue" and r.get("grade") in ("S", "A")]
        delivered = [r for r in results if r.get("grade") in ("S", "A")]
        counts.update({"actual_editorial_email_pitches_sent": len(emails), "actual_editorial_issue_pitches_submitted": len(issues), "confirmed_editorial_acknowledgements": sum(r.get("editorial_acknowledgement") is True for r in delivered), "verified_public_articles": pairs["S"], "sent_email_is_editorial_acknowledgement": False, "sent_email_is_publication": False, "public_issue_is_editorial_publication": False})
    return counts


def re_is_pr(url):
    return url.startswith("https://github.com/") and "/pull/" in url


def escape_md(value):
    text = html.escape(str(value or ""), quote=False)
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def link_for_reference(reference):
    if reference.startswith(("http://", "https://")):
        return reference
    path, separator, fragment = reference.partition("#")
    if path.startswith("/tmp/"):
        return None  # Ephemeral cache reference stays visible, durable snapshot retains the finding.
    if path.startswith("/Users/f/Documents/github/dirsubmit/"):
        path = str(Path(path).relative_to(ROOT))
    if path.startswith(("runs/", "docs/", "articles/", "recipes/")):
        if (ROOT / path).exists():
            return "../../" + quote(path, safe="/") + ("#" + fragment if separator and fragment else "")
    if path in ("awesome-saas-directories.md", "AGENTS.md"):
        return "../../" + path + ("#" + fragment if separator and fragment else "")
    return None


def md_refs(refs):
    out = []
    for index, ref in enumerate(unique_strings(refs), 1):
        url = link_for_reference(ref)
        label = ref if not url else ("来源" + str(index) if ref.startswith("http") else ref)
        out.append(f"[{escape_md(label)}](<{url}>)" if url else escape_md(ref))
    return "<br>".join(out) or "—"


def write_markdown(catalog):
    slug = catalog["category"]
    counts = catalog["counts"]
    lines = [f"# {catalog['name']}提交清单", "", f"更新于 {catalog['generated_at_utc']}。共 {counts['targets']} 个目标、{counts['product_target_pairs']} 个产品与目标组合。", "", "这是已知来源范围的完整候选清单；未测试项保持 U，不能据此声称已覆盖全网。每个产品独立评级。目录申请、开放 PR、稿件或邮件投递与实际上线分别记录；邮件已发出不表示编辑确认收到、采用或公开刊登。", "", f"[交互查看](index.html) · [完整 JSON]({slug}.json) · [结果覆写](actual-result-overrides.json)", "", "| 级别 | 判据 | 产品目标数 |", "|---|---|---:|"]
    for grade in GRADE_ORDER:
        lines.append(f"| {grade} | {GRADES[grade]} | {counts['product_pair_grades'][grade]} |")
    lines += ["", "| # | 目标 / 正常投稿入口 | Botstest | WarmQuant | WeWorkBuddy | 状态、原因与下一动作 | 回执 / 证据 | 来源 |", "|---:|---|---|---|---|---|---|---|"]
    for number, target in enumerate(catalog["targets"], 1):
        url = target["submission_url"] or target["url"]
        title = f"[{escape_md(target['name'])}](<{url}>)" if url else escape_md(target["name"])
        grades = [target["product_results"][p]["grade"] for p in PRODUCTS]
        explanations = []
        evidence = []
        for p in PRODUCTS:
            result = target["product_results"][p]
            explanations.append(f"**{PRODUCT_NAMES[p]}**：{escape_md(result['state'])}<br>{escape_md(result['reason'])}<br>下一动作：{escape_md(result['next_action'])}")
            refs = unique_strings(result["receipt_links"], result["evidence"])
            receipt = result.get("receipt_metadata") or {}
            if refs or receipt:
                meta = ""
                if receipt:
                    task = receipt.get("task_row") or {}
                    meta = "<br>发送提示：" + escape_md(receipt.get("send_notice", "")) + "<br>任务主题：" + escape_md(task.get("subject", "")) + "<br>唯一匹配任务行：" + escape_md(task.get("unique_matched_sent_task_row_count", "")) + "<br>任务查询：" + escape_md(receipt.get("sent_query", ""))
                evidence.append(f"**{PRODUCT_NAMES[p]}**<br>{md_refs(refs)}{meta}")
        lines.append("| " + " | ".join([str(number), title, *grades, "<br><br>".join(explanations), "<br><br>".join(evidence) or "—", md_refs(target["source_refs"])]) + " |")
    lines += ["", "来源与边界", "", f"原始评估文件：[{catalog['source_snapshot']}](../../{catalog['source_snapshot']})。它保持不变；当前真实结果通过 actual-result-overrides.json 逐产品合并。", "", f"基础快照目标 {catalog['base_expected_targets']}，独立增量目标 {catalog['additional_source_target_count']}，合并目标 {catalog['combined_expected_targets']}。增量目标先验证类别、身份去重和三个产品记录，再与真实结果覆写合并；准备稿不能预先升级为 A/S。"]
    for source in catalog["additional_sources"]:
        lines += ["", f"增量来源：{md_refs([source['path']])}；SHA-256：`{source['sha256']}`。原始调查文件及其哈希保留在该增量文件的 provenance 中。"]
    lines += ["", "S/A 必须有实际提交、邮件发出、开放 PR 或公开条目证据；B 是准备可执行，不能计作已提交。邮件实际发出与编辑确认收到、采用、刊登分开记录。仅浏览过网页、离线稿件、提交按钮点击或数据库里的免费标签均不证明完成投稿。来源引用的临时缓存路径只作为历史引用；完整发现与版本信息保留在原始评估 JSON。", ""]
    (HERE / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")


def write_readme(catalogs, generated_at):
    counts = {c["category"]: c["counts"] for c in catalogs}
    dirs = counts["directories"]
    gh = counts["awesome-repositories"]
    editorial = counts["editorial-outlets"]
    base_counts = "、".join(f"{c['name']} {c['base_expected_targets']}" for c in catalogs)
    added_counts = "、".join(f"{c['name']} {c['additional_source_target_count']}" for c in catalogs)
    text = f"""# 三类产品提交清单

[打开本地筛选页](index.html)。可按类别、产品、S/A/B/C/D/U 级别和名称筛选；默认每页 100 个目标，也可以显示全部。不需要安装依赖、启动服务或联网加载数据。

更新于 {generated_at}。三类结果独立统计：

- 目录：{dirs['targets']} 个候选，{dirs['confirmed_directory_applications']} 份已确认申请，其中 {dirs['verified_public_directory_listings']} 个公开条目已核实。
- GitHub：{gh['targets']} 个仓库，{gh['unique_confirmed_PRs']} 个独立 PR，覆盖 {gh['confirmed_PR_product_entries']} 条产品记录；公开合并条目 {gh['verified_merged_public_product_entries']}。
- 投稿：{editorial['targets']} 个候选，实际邮件投递 {editorial['actual_editorial_email_pitches_sent']} 份，官方周刊 Issue 投稿 {editorial['actual_editorial_issue_pitches_submitted']} 份，编辑确认回复 {editorial['confirmed_editorial_acknowledgements']}，公开刊登 {editorial['verified_public_articles']}。

邮件发出或周刊 Issue 创建仅证明已投递，不表示编辑确认收到、不表示采用，也不表示公开刊登。公开可读的自荐 Issue 是稿件回执，不能算周刊刊发。目录审核收件、PR 创建与稿件投递不能混成同一种编辑确认。

| 类别 | 完整列表 | 机器可读记录 |
|---|---|---|
| 目录站与导航站 | [directories.md](directories.md) | [directories.json](directories.json) |
| GitHub awesome 仓库 | [awesome-repositories.md](awesome-repositories.md) | [awesome-repositories.json](awesome-repositories.json) |
| 博客、网站与新闻投稿 | [editorial-outlets.md](editorial-outlets.md) | [editorial-outlets.json](editorial-outlets.json) |

每个目标分别记录 Botstest、WarmQuant、WeWorkBuddy 的状态、原因、证据、来源、回执链接和下一动作。U 不代表已尝试；B 不代表已提交；A 表示已确认提交、投递或开放 PR，审核与采用待定；S 表示已核实公开结果。发出提示、任务查询和唯一任务行数量为最小邮件凭证，不复制邮箱正文或预览。

## 更新真实结果

三个原始来源文件保留在 `runs/category{{1,2,3}}-*-universe-2026-10-10.json`。基础预期目标数保持：{base_counts}。生成器先验证基础快照数量及身份，再读取独立增量来源 [additional-targets.json](additional-targets.json)，追加已保留官方证据和调查文件哈希的新目标；本次增量：{added_counts}。类别必须有效、同一类别的目标身份不能重复、每个目标必须提供三个产品结果。不要为扩大清单或更新状态修改原始快照和基础预期数量。

基础来源、增量来源及其 SHA-256 分开记录在输出 JSON 和 [generation-validation.json](generation-validation.json) 中；基础预期与合并后的实际数量分别校验。目标合并后再依次应用 [actual-result-overrides.json](actual-result-overrides.json) 的 `overrides` 数组。增量文件中的 B/C 是准备或条件状态，实际投递仍须取得回执后逐产品覆写为 A/S。

覆写记录示例：

```json
{{
  "category": "awesome-repositories",
  "target_key": "techiediaries/awesome-technical-writing-blogging-resources",
  "product": "warmquant",
  "grade": "A",
  "state": "confirmed_open_PR",
  "reason": "已创建并通过官方公开 API 核实；等待维护者审核。",
  "receipt_links": ["https://github.com/techiediaries/Awesome-Technical-Writing-Blogging-Resources/pull/1"],
  "evidence": ["runs/github-techiediaries-warmquant-public-confirmation-2026-10-10.json"],
  "next_action": "等待审核，不重复提交。"
}}
```

`category` 取三个列表的文件名，`target_key` 取对应 JSON 中的键，`product` 取 `botstest`、`warmquant`、`weworkbuddy`。同一产品目标追加多条记录时，后面的字段依次生效，已有回执和证据去重保留；其他产品不受影响。只有实际提交、投递、开放 PR 或公开结果可以升级至 A/S。不要保存验证码、凭证或无关邮件内容。

在仓库根目录执行：

```sh
python3 docs/submission-catalog/generate_catalog.py
```

脚本只使用 Python 标准库，输出三个 JSON、三个 Markdown、嵌入数据的 `index.html`、本说明和 [generation-validation.json](generation-validation.json)。已存在的真实结果覆写文件不会被重置，Store、主报告、AGENTS.md 和三个原始快照不会被修改。
"""
    (HERE / "README.md").write_text(text, encoding="utf-8")


HTML_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>三类产品提交清单</title>
<style>
:root{color-scheme:light dark;--bg:#f4f6f8;--fg:#18202b;--panel:#fff;--muted:#647084;--line:#d9dfe7;--link:#175bb8}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1500px;margin:auto;padding:28px 22px}h1{font-size:28px;margin:0 0 6px}p{margin:8px 0}.muted{color:var(--muted)}a{color:var(--link);text-decoration:none}a:hover{text-decoration:underline}header,.filters,.summary,.table-wrap,footer{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin:0 0 16px}.filters{display:flex;gap:12px;flex-wrap:wrap;align-items:end}.field{display:flex;flex-direction:column;gap:4px}.field.search{flex:1;min-width:220px}select,input,button{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:8px 10px}button{cursor:pointer}button:disabled{opacity:.45;cursor:default}input{width:100%}.summary{display:flex;gap:10px;flex-wrap:wrap}.stat{padding:8px 12px;border-radius:8px;background:var(--bg)}.table-wrap{padding:0;overflow:auto}table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:12px;min-width:160px}th{position:sticky;top:0;background:var(--panel);white-space:nowrap}td:first-child,th:first-child{min-width:250px;max-width:330px}td:last-child{min-width:145px}.name{font-weight:650;overflow-wrap:anywhere}.tag{display:inline-block;padding:2px 7px;border-radius:5px;font-weight:700;border:1px solid var(--line);margin-right:5px}.gS{background:#e5f6ee;color:#146242}.gA{background:#e8f0fe;color:#174ea6}.gB{background:#e9f4f7;color:#126070}.gC{background:#fff5d6;color:#775706}.gD{background:#fcebec;color:#993f45}.gU{background:#edf0f4;color:#566174}.state{font-size:12px;color:var(--muted);overflow-wrap:anywhere;margin-top:5px}details{margin-top:8px}summary{cursor:pointer;color:var(--link)}.detail{margin-top:7px;overflow-wrap:anywhere;font-size:13px}.detail p{margin:6px 0}.refs{padding-left:16px;margin:6px 0}.refs li{margin:4px 0}.pager{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px}.empty{padding:30px;text-align:center}.legend{display:flex;gap:9px;flex-wrap:wrap;font-size:12px;margin-top:10px}.download{display:flex;gap:12px;flex-wrap:wrap}.result-links{margin-top:6px;overflow-wrap:anywhere}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}@media(prefers-color-scheme:dark){:root{--bg:#15191f;--fg:#e8edf3;--panel:#20262e;--muted:#a2afbf;--line:#3a4552;--link:#8ab4f8}}@media(max-width:700px){main{padding:14px 10px}h1{font-size:23px}.filters{gap:8px}th,td{padding:9px;min-width:145px}}
</style></head>
<body><main>
<header><h1>三类产品提交清单</h1><p>Botstest · WarmQuant · WeWorkBuddy</p><p class="muted" id="scope"></p><p class="muted">已知候选清单完整保留，逐产品评级。B 表示尚未发送，A 表示已确认提交、投递或开放 PR，审核与采用待定；S 表示已核实公开结果。邮件发出与编辑确认收到、采用、刊登分别记录。PR 创建与合并分开记录。</p><div class="download"><a href="directories.md">目录 Markdown</a><a href="awesome-repositories.md">GitHub Markdown</a><a href="editorial-outlets.md">投稿 Markdown</a><a href="actual-result-overrides.json">最新结果覆写</a></div><div class="legend" id="legend"></div></header>
<section class="filters" aria-label="清单筛选"><label class="field">类别<select id="category"><option value="all">全部类别</option><option value="directories">目录站与导航站</option><option value="awesome-repositories">GitHub awesome 仓库</option><option value="editorial-outlets">博客、网站与新闻投稿</option></select></label><label class="field">产品<select id="product"><option value="all">三个产品</option><option value="botstest">Botstest</option><option value="warmquant">WarmQuant</option><option value="weworkbuddy">WeWorkBuddy</option></select></label><label class="field">结果级别<select id="grade"><option value="all">全部级别</option><option value="S">S · 已公开</option><option value="A">A · 已提交 / 投递 / 开放 PR</option><option value="B">B · 可执行未发送</option><option value="C">C · 条件待处理</option><option value="D">D · 不适配 / 仅付费 / 失效</option><option value="U">U · 未充分评估</option></select></label><label class="field search">名称、域名、原因或状态<input id="search" type="search" placeholder="搜索目标、域名、状态、原因" autocomplete="off"></label><button id="reset" type="button">重置</button></section>
<section class="summary" id="stats" aria-live="polite"></section>
<div class="pager"><button id="prev" type="button">上一页</button><span id="page-status" aria-live="polite"></span><button id="next" type="button">下一页</button><label>每页 <select id="page-size"><option value="100">100 个目标</option><option value="250">250 个目标</option><option value="all">全部目标</option></select></label><span class="muted">全部记录可通过翻页或“全部目标”查看。</span></div>
<section class="table-wrap"><table><thead id="table-head"></thead><tbody id="table-body"></tbody></table></section>
<footer><p>所有操作使用零费用方案。来源中的 DR、自动化或免费标签只作发现线索，不能证明当前收件或适配。</p><p class="muted">目录数据归属 mezmer90 / AI BrandFactory（CC BY 4.0），平台清单归属 xioanchin（MIT）；另复用官方 LinkFlow / Backlink Pilot 源快照。完整来源、版本、规则与实际回执见各项“详情”及 JSON 文件。</p><div class="download"><a href="directories.json">完整目录 JSON</a><a href="awesome-repositories.json">完整 GitHub JSON</a><a href="editorial-outlets.json">完整投稿 JSON</a><a href="generate_catalog.py">离线生成脚本</a></div></footer>
</main>
<script id="catalog-data" type="application/json">__CATALOG_JSON__</script>
<script>
'use strict';
const catalog = JSON.parse(document.getElementById('catalog-data').textContent);
const categories = Object.fromEntries(catalog.catalogs.map(c => [c.category,c.name]));
const allRows = catalog.catalogs.flatMap(c => c.targets);
const products = ['botstest','warmquant','weworkbuddy'];
const productNames = {botstest:'Botstest',warmquant:'WarmQuant',weworkbuddy:'WeWorkBuddy'};
const gradeOrder = ['S','A','B','C','D','U'];
const controls = Object.fromEntries(['category','product','grade','search','page-size'].map(id=>[id,document.getElementById(id)]));
let page = 0;
const el = (tag, text, className) => {const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;};
function safeHref(ref){
 if(typeof ref!=='string')return null;
 if(/^https?:\/\//.test(ref)){try{const u=new URL(ref);return ['https:','http:'].includes(u.protocol)?u.href:null;}catch{return null;}}
 const path=ref.split('#')[0];
 if(/^(runs|docs|articles|recipes)\//.test(path)){return '../../'+path.split('/').map(encodeURIComponent).join('/')+(ref.includes('#')?'#'+ref.split('#').slice(1).join('#'):'');}
 if(['awesome-saas-directories.md','AGENTS.md'].includes(path))return '../../'+path;
 return null;
}
function link(label,href){const a=el('a',label);const safe=safeHref(href);if(safe){a.href=safe;if(safe.startsWith('http')){a.target='_blank';a.rel='noopener noreferrer';}}else return el('span',label);return a;}
function appendRefs(parent,refs,label){if(!refs?.length)return;parent.append(el('strong',label));const list=el('ul',undefined,'refs');for(const ref of [...new Set(refs)]){const li=el('li');li.append(link(ref,ref));list.append(li);}parent.append(list);}
function selectedProducts(){return controls.product.value==='all'?products:[controls.product.value];}
function filteredRows(){const ps=selectedProducts();const q=controls.search.value.trim().toLowerCase();return allRows.filter(t=>{
 if(controls.category.value!=='all'&&t.category!==controls.category.value)return false;
 if(controls.grade.value!=='all'&&!ps.some(p=>t.product_results[p].grade===controls.grade.value))return false;
 if(q){const values=[t.name,t.target_key,t.canonical_domain,t.submission_url,...(t.aliases||[]),...ps.flatMap(p=>{const r=t.product_results[p];return [r.grade,r.state,r.reason,r.next_action];})];if(!values.join(' ').toLowerCase().includes(q))return false;}
 return true;
});}
function render(){
 const rows=filteredRows(),ps=selectedProducts();const size=controls['page-size'].value==='all'?Math.max(rows.length,1):Number(controls['page-size'].value);const pageCount=Math.max(1,Math.ceil(rows.length/size));page=Math.max(0,Math.min(page,pageCount-1));
 document.getElementById('page-status').textContent=`${rows.length.toLocaleString()} 个目标 · 第 ${page+1} / ${pageCount} 页`;
 document.getElementById('prev').disabled=page===0;document.getElementById('next').disabled=page>=pageCount-1;
 const gradeCounts=Object.fromEntries(gradeOrder.map(g=>[g,0]));let matchingPairs=0;for(const t of rows)for(const p of ps){const r=t.product_results[p];if(controls.grade.value==='all'||r.grade===controls.grade.value){gradeCounts[r.grade]++;matchingPairs++;}}
 const stats=document.getElementById('stats');stats.replaceChildren(el('span',`${rows.length.toLocaleString()} 个目标`,'stat'),el('span',`${matchingPairs.toLocaleString()} 个匹配产品目标`,'stat'));for(const g of gradeOrder)stats.append(el('span',`${g} · ${gradeCounts[g].toLocaleString()}`,'stat'));
 const header=el('tr');header.append(el('th','目标 / 类别'));for(const p of ps)header.append(el('th',productNames[p]));header.append(el('th','来源与规则'));document.getElementById('table-head').replaceChildren(header);
 const body=document.getElementById('table-body');const frag=document.createDocumentFragment();
 for(const t of rows.slice(page*size,(page+1)*size)){
  const tr=el('tr');const main=el('td');const name=el('div',undefined,'name');name.append(link(t.name,t.submission_url||t.url));main.append(name,el('div',categories[t.category],'muted'),el('div',t.canonical_domain||t.target_key,'state'));tr.append(main);
  for(const p of ps){const r=t.product_results[p];const td=el('td');td.append(el('span',r.grade,`tag g${r.grade}`),el('span',catalog.grades[r.grade]),el('div',r.state,'state'));if(r.receipt_links?.length){const links=el('div',undefined,'result-links');r.receipt_links.forEach((u,i)=>{if(i)links.append(el('span',' · '));links.append(link(u.includes('/pull/')?'PR #'+u.split('/pull/')[1]:'公开结果 / 回执',u));});td.append(links);}const details=el('details');details.append(el('summary','原因 / 下一动作 / 证据'));const content=el('div',undefined,'detail');content.append(el('p',r.reason||'暂无充分证据。'),el('p','下一动作：'+r.next_action));appendRefs(content,r.evidence,'证据');if(r.receipt_metadata){const m=r.receipt_metadata,task=m.task_row||{};content.append(el('p','发送提示：'+(m.send_notice||'')),el('p','任务主题：'+(task.subject||'')),el('p','唯一匹配任务行：'+(task.unique_matched_sent_task_row_count??'')),el('p','任务查询：'+(m.sent_query||'')));}if(r.verified_at)content.append(el('p','核实时间：'+r.verified_at));details.append(content);td.append(details);tr.append(td);}
  const td=el('td');const details=el('details');details.append(el('summary',`${t.source_refs.length} 个来源 / 规则`));const content=el('div',undefined,'detail');appendRefs(content,t.source_refs,'来源');const ctx=t.snapshot_context||{};for(const k of ['zero_cost_scope','official_submission_support','manuscript_requirements','ai_content_policy','copyright_exclusivity','success_criteria','classification_basis'])if(ctx[k])content.append(el('p',String(ctx[k])));if(t.source_row_ids.length)content.append(el('p','原始来源行：'+t.source_row_ids.join(', ')));details.append(content);td.append(details);tr.append(td);frag.append(tr);
 }
 if(!rows.length){const tr=el('tr');const td=el('td','没有匹配的目标。','empty');td.colSpan=ps.length+2;tr.append(td);frag.append(tr);}
 body.replaceChildren(frag);
}
for(const [name,control] of Object.entries(controls))control.addEventListener(name==='search'?'input':'change',()=>{page=0;render();});
document.getElementById('prev').addEventListener('click',()=>{page--;render();});document.getElementById('next').addEventListener('click',()=>{page++;render();});document.getElementById('reset').addEventListener('click',()=>{controls.category.value='all';controls.product.value='all';controls.grade.value='all';controls.search.value='';controls['page-size'].value='100';page=0;render();});
document.getElementById('scope').textContent=`更新 ${catalog.generated_at_utc} · ${allRows.length.toLocaleString()} 个已知目标 · ${(allRows.length*3).toLocaleString()} 个产品目标组合。此页离线运行，不发送网络请求。`;
const legend=document.getElementById('legend');for(const grade of gradeOrder){const span=el('span');span.append(el('span',grade,`tag g${grade}`),el('span',catalog.grades[grade]));legend.append(span);}render();
</script></body></html>
'''


def main():
    override_data = ensure_overrides()
    now = datetime.now(timezone.utc).isoformat()
    catalogs = []
    immutable_hashes = {}
    for category, title, source_path, expected in SPECS:
        source = ROOT / source_path
        immutable_hashes[source_path] = hashlib.sha256(source.read_bytes()).hexdigest()
        snapshot = load(source)
        targets = [normalize_target(category, t, source_path) for t in snapshot["targets"]]
        if len(targets) != expected or len({t["target_key"] for t in targets}) != expected:
            raise ValueError(f"{category} target count/identity changed; inspect source before updating expected count")
        catalogs.append({"schema_version": 1, "category": category, "name": title, "generated_at_utc": now, "source_snapshot": source_path, "source_sha256": immutable_hashes[source_path], "grades": GRADES, "products": PRODUCT_NAMES, "scope": snapshot.get("scope", snapshot.get("coverage_scope", "已知来源范围内候选；未测试项保持 U。")), "attribution": snapshot.get("attribution", {}), "source_snapshot_counts": snapshot.get("counts", {}), "base_expected_targets": expected, "base_actual_targets": len(targets), "targets": targets})
    additional_source = append_additional_targets(catalogs)
    applied = apply_overrides(catalogs, override_data)
    for catalog in catalogs:
        catalog["targets"].sort(key=lambda t: (min(GRADE_ORDER.index(r["grade"]) for r in t["product_results"].values()), t["name"].lower(), t["target_key"]))
        catalog["counts"] = category_counts(catalog["targets"], catalog["category"])
        if catalog["counts"]["targets"] != catalog["combined_expected_targets"]:
            raise ValueError(f"{catalog['category']} combined target count changed unexpectedly")
        catalog["actual_result_overrides_applied"] = [a for a in applied if a["category"] == catalog["category"]]
        (HERE / (catalog["category"] + ".json")).write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_markdown(catalog)
    write_readme(catalogs, now)
    browser_data = {"generated_at_utc": now, "grades": GRADES, "catalogs": [{"category": c["category"], "name": c["name"], "counts": c["counts"], "targets": c["targets"]} for c in catalogs]}
    # Escaping '<' prevents any untrusted source text from ending the JSON script block.
    embedded = json.dumps(browser_data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    (HERE / "index.html").write_text(HTML_TEMPLATE.replace("__CATALOG_JSON__", embedded), encoding="utf-8")
    for path, digest in immutable_hashes.items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Source snapshot changed unexpectedly: {path}")
    if additional_source["path"] and hashlib.sha256((ROOT / additional_source["path"]).read_bytes()).hexdigest() != additional_source["sha256"]:
        raise RuntimeError("Additional target source changed unexpectedly")
    totals = {g: sum(c["counts"]["product_pair_grades"][g] for c in catalogs) for g in GRADE_ORDER}
    qa = {"generated_at_utc": now, "source_snapshots_unchanged": immutable_hashes, "expected_targets": {s[0]: s[3] for s in SPECS}, "base_expected_targets": {s[0]: s[3] for s in SPECS}, "base_actual_targets": {c["category"]: c["base_actual_targets"] for c in catalogs}, "additional_source": additional_source, "additional_source_sha256": additional_source["sha256"], "additional_targets": additional_source["targets_per_category"], "combined_expected_targets": {c["category"]: c["combined_expected_targets"] for c in catalogs}, "actual_counts": {c["category"]: c["counts"] for c in catalogs}, "total_targets": sum(c["counts"]["targets"] for c in catalogs), "total_product_target_pairs": sum(c["counts"]["product_target_pairs"] for c in catalogs), "total_pair_grades": totals, "applied_overrides": applied, "html_embedded_JSON_matches_output": True, "HTML_fetch_or_external_assets": False, "Store_or_main_report_or_AGENTS_modified": False}
    (HERE / "generation-validation.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
