"""Dirsubmit CLI：init / gen / submit / status / list / recipes / distribute。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import api, channels, config, copywriter, engine, recipes, tracker
from .llm import LLMClient
from .store import Store


def _product(args):
    return config.load_product(args.product)


def _recipes(args):
    return recipes.load_all(args.recipes)


def _store(args):
    return Store(args.db)


def _start_bridge(args):
    """mode ∈ extension|auto 时启动 WebSocket 桥（后台），等待 Chrome 扩展连入。"""
    mode = getattr(args, "mode", None)
    if mode not in ("extension", "auto"):
        return None
    from .ext_bridge import ExtBridge

    port = int(getattr(args, "ext_port", None) or
               os.environ.get("DIRSUBMIT_EXT_PORT", "8721"))
    bridge = ExtBridge(port=port)
    bridge.start(wait=0)  # 不阻塞
    if mode == "extension":
        print(f"等待 Chrome 扩展连入 ws://127.0.0.1:{port} ...")
        if bridge.wait_for_client(timeout=15.0):
            print("  ✓ 扩展已连接")
        else:
            print("  ✗ 扩展未连接（请在 Chrome 加载 extension/ 目录，并点一下扩展图标唤醒）")
    else:  # auto：短暂检测窗口，检测到就用，检测不到走 CDP/headless
        bridge.wait_for_client(timeout=3.0)
        if bridge.connected():
            print("  ✓ 检测到 Chrome 扩展，semi 目录将走扩展")
    return bridge


def cmd_init(args):
    p = Path(args.product)
    if p.exists() and not args.force:
        print(f"{p} 已存在，用 --force 覆盖。")
        return 1
    p.write_text(config.product_template(), encoding="utf-8")
    print(f"已生成 {p}，请填写产品信息后运行 `dirsubmit gen`。")
    return 0


def cmd_gen(args):
    product = _product(args)
    all_recipes = _recipes(args)
    if not all_recipes:
        print(f"recipes 目录（{args.recipes}）没有 JSON，请先添加目录食谱。")
        return 1
    provider = args.provider or os.environ.get("DIRSUBMIT_LLM", "openai")
    llm = LLMClient(provider)
    store = _store(args)

    targets = all_recipes
    if args.only:
        targets = [r for r in all_recipes if r.slug in args.only.split(",")]

    print(f"生成 {len(targets)} 个目录的文案（provider={provider}，模型={llm.model}）...")
    for r in targets:
        copy = copywriter.generate_copy(product, r, llm)
        store.upsert_copy(copy)
        print(f"  ✓ {r.slug}  category={copy.category}  tags={','.join(copy.tags)}")
    store.close()
    return 0


def cmd_submit(args):
    product = _product(args)
    all_recipes = _recipes(args)
    store = _store(args)
    cdp_url = args.cdp_url or os.environ.get("DIRSUBMIT_CDP_URL", "http://localhost:9222")
    bridge = _start_bridge(args)

    targets = [r for r in all_recipes if r.tier in args.tier.split(",")]
    if args.only:
        targets = [r for r in targets if r.slug in args.only.split(",")]

    print(f"提交 {len(targets)} 个目录（tier={args.tier}，mode={args.mode}，dry_run={args.dry_run}）...")
    for r in targets:
        copy = store.get_copy(r.slug)
        if copy is None:
            print(f"  [skip] {r.slug} 无文案，先跑 `dirsubmit gen`")
            continue
        if not args.force and store.get_status(r.slug) in ("submitted", "approved"):
            print(f"  [skip] {r.slug} 已提交，用 --force 重跑")
            continue

        if r.tier == "manual":
            path = engine.cheatsheet_file(r, product, copy)
            status, note = "manual", f"粘贴清单已生成：{path}"
        else:
            status, note = engine.submit(
                r, product, copy, mode=args.mode, cdp_url=cdp_url,
                dry_run=args.dry_run, bridge=bridge
            )
        store.set_status(r.slug, r.tier, status, note)
        print(f"  [{status}] {r.slug}  {note}")
    store.close()
    if bridge is not None:
        bridge.stop()
    return 0


def cmd_status(args):
    product = _product(args)
    all_recipes = _recipes(args)
    store = _store(args)

    rows = store.all_submissions()
    by_dir = {r["directory"]: r for r in rows}

    targets = all_recipes
    if args.only:
        targets = [r for r in all_recipes if r.slug in args.only.split(",")]

    print(f"{'目录':<22}{'tier':<8}{'状态':<10}说明")
    for r in targets:
        row = by_dir.get(r.slug)
        if not row:
            continue
        status = row["status"]
        note = row["note"] or ""
        if args.check and status in ("submitted", "pending"):
            st, n = tracker.check(r, product)
            store.update_checked(r.slug, st, n)
            status, note = st, n
        print(f"{r.slug:<22}{r.tier:<8}{status:<10}{note}")
    store.close()
    return 0


def cmd_list(args):
    all_recipes = _recipes(args)
    if args.tier:
        all_recipes = [r for r in all_recipes if r.tier in args.tier.split(",")]
    print(f"{'目录':<24}{'DR':>4}  {'tier':<8}需登录")
    for r in all_recipes:
        print(f"{r.slug:<24}{r.dr:>4}  {r.tier:<8}{'是' if r.requires_auth else '否'}")
    return 0


def cmd_recipes(args):
    all_recipes = _recipes(args)
    print(f"共 {len(all_recipes)} 个目录食谱：")
    for r in all_recipes:
        print(f"  {r.slug:<24} {r.name}")
    return 0


def cmd_distribute(args):
    """统一分发：API 渠道（全自动）+ 浏览器目录（auto/semi）+ 纯人工（草稿）。"""
    product = _product(args)
    all_recipes = _recipes(args)
    store = _store(args)
    provider = args.provider or os.environ.get("DIRSUBMIT_LLM", "openai")
    llm = LLMClient(provider)
    cdp_url = args.cdp_url or os.environ.get("DIRSUBMIT_CDP_URL", "http://localhost:9222")
    bridge = _start_bridge(args)

    chans = channels.all_channels(all_recipes)
    targets = channels.filter_channels(chans, args.tier, args.only)

    print(f"分发到 {len(targets)} 个渠道（tier={args.tier}，dry_run={args.dry_run}）...")
    drafts = Path(args.drafts)
    stats = {}
    for ch in targets:
        slug, method, tier = ch["slug"], ch["method"], ch["tier"]
        if method == "api":
            msg = copywriter.generate_message(product, ch, llm)
            status, note = api.publish(ch["api"]["type"], msg["title"], msg["message"],
                                       dry_run=args.dry_run)
        elif method == "browser":
            r = ch["recipe"]
            copy = store.get_copy(slug)
            if copy is None:
                copy = copywriter.generate_copy(product, r, llm)
                store.upsert_copy(copy)
            if r.tier == "manual":
                path = engine.cheatsheet_file(r, product, copy)
                status, note = "manual", f"粘贴清单：{path}"
            else:
                status, note = engine.submit(r, product, copy, mode=args.mode,
                                             cdp_url=cdp_url, dry_run=args.dry_run,
                                             bridge=bridge)
        else:  # manual 渠道：生成草稿供人工发布
            msg = copywriter.generate_message(product, ch, llm)
            drafts.mkdir(exist_ok=True)
            p = drafts / f"{slug}.md"
            p.write_text(f"# {msg['title']}\n\n{msg['message']}\n", encoding="utf-8")
            status, note = "manual", f"草稿：{p}"
        store.set_status(slug, tier, status, note)
        stats[status] = stats.get(status, 0) + 1
        print(f"  [{status}] {slug:<16} {note}")
    store.close()
    if bridge is not None:
        bridge.stop()
    print(f"\n汇总：{', '.join(f'{k}={v}' for k, v in sorted(stats.items()))}")
    return 0


def cmd_channels(args):
    """列出所有渠道及其启用状态（enabled / disabled / manual）。"""
    all_recipes = _recipes(args)
    chans = channels.all_channels(all_recipes)
    print(f"{'渠道':<18}{'分类':<12}{'方式':<10}{'tier':<8}状态")
    for ch in chans:
        st = channels.channel_status(ch)
        print(f"{ch['slug']:<18}{ch['category']:<12}{ch['method']:<10}{ch['tier']:<8}{st}")
    enabled = sum(1 for c in chans if channels.channel_status(c) == "enabled")
    print(f"\n{enabled}/{len(chans)} 个渠道已启用（其余未配置凭证，配好即自动启用）")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="dirsubmit", description="SaaS 目录提交工具")
    p.add_argument("--product", default="product.yaml", help="产品信息文件")
    p.add_argument("--recipes", default="recipes", help="目录食谱目录")
    p.add_argument("--db", default="dirsubmit.db", help="SQLite 路径")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="生成 product.yaml 模板")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("gen", help="生成每个目录的差异化 AI 文案")
    sp.add_argument("--provider", help="openai|deepseek|gemini|ollama")
    sp.add_argument("--only", help="只处理指定 slug（逗号分隔）")
    sp.set_defaults(func=cmd_gen)

    sp = sub.add_parser("submit", help="按 tier 提交到目录")
    sp.add_argument("--mode", choices=["auto", "headless", "cdp", "extension"], default="auto",
                    help="auto=自动选择（默认）")
    sp.add_argument("--tier", default="auto,semi,manual", help="只提交指定 tier")
    sp.add_argument("--cdp-url", help="CDP 地址，默认 http://localhost:9222")
    sp.add_argument("--ext-port", help="扩展 WebSocket 端口，默认 8721")
    sp.add_argument("--only", help="只处理指定 slug")
    sp.add_argument("--dry-run", action="store_true", help="只演练不提交")
    sp.add_argument("--force", action="store_true", help="重跑已提交的")
    sp.set_defaults(func=cmd_submit)

    sp = sub.add_parser("status", help="查看/核验提交状态")
    sp.add_argument("--check", action="store_true", help="重抓目录页核验是否收录")
    sp.add_argument("--only", help="只查看指定 slug")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("list", help="列出目录（按 DR/tier）")
    sp.add_argument("--tier", help="按 tier 过滤")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("recipes", help="列出所有目录食谱")
    sp.set_defaults(func=cmd_recipes)

    sp = sub.add_parser("distribute", help="统一分发到 API + 浏览器 + 手动渠道")
    sp.add_argument("--provider", help="openai|deepseek|gemini|ollama")
    sp.add_argument("--mode", choices=["auto", "headless", "cdp", "extension"], default="auto",
                    help="auto=自动选择（默认）")
    sp.add_argument("--tier", default="auto,semi,manual", help="只分发指定 tier")
    sp.add_argument("--cdp-url", help="CDP 地址，默认 http://localhost:9222")
    sp.add_argument("--ext-port", help="扩展 WebSocket 端口，默认 8721")
    sp.add_argument("--only", help="只分发指定 slug（逗号分隔）")
    sp.add_argument("--dry-run", action="store_true", help="只演练不实际发布")
    sp.add_argument("--drafts", default="drafts", help="纯人工渠道草稿目录")
    sp.set_defaults(func=cmd_distribute)

    sp = sub.add_parser("channels", help="列出所有渠道及启用状态")
    sp.set_defaults(func=cmd_channels)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
