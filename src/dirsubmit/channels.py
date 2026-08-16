"""渠道注册表：API 渠道 + 浏览器目录渠道 + 纯人工渠道统一抽象。

渠道字段：slug / name / category / tier(auto|semi|manual) / method(api|browser|manual)
"""

from __future__ import annotations

from typing import Dict, List

from . import api as api_module
from . import recipes as recipe_loader
from .models import Recipe


def _ch(slug, name, category, tier, method, api_type=None):
    c = {"slug": slug, "name": name, "category": category, "tier": tier, "method": method}
    if api_type:
        c["api"] = {"type": api_type}
    return c


# API 原生渠道（官方 API，全自动；凭证未配置则 disabled）
API_CHANNELS: List[dict] = [
    # 博客 / 长文
    _ch("devto", "DEV.to", "blog", "auto", "api", "devto"),
    _ch("wordpress", "WordPress", "blog", "auto", "api", "wordpress"),
    _ch("ghost", "Ghost", "blog", "auto", "api", "ghost"),
    _ch("hashnode", "Hashnode", "blog", "auto", "api", "hashnode"),
    # 社交 / 消息
    _ch("x", "X / Twitter", "social", "auto", "api", "x"),
    _ch("linkedin", "LinkedIn", "social", "auto", "api", "linkedin"),
    _ch("facebook", "Facebook Page", "social", "auto", "api", "facebook"),
    _ch("threads", "Threads", "social", "auto", "api", "threads"),
    _ch("bluesky", "Bluesky", "social", "auto", "api", "bluesky"),
    _ch("mastodon", "Mastodon", "social", "auto", "api", "mastodon"),
    _ch("telegram", "Telegram", "social", "auto", "api", "telegram"),
    _ch("discord", "Discord", "community", "auto", "api", "discord"),
    _ch("slack", "Slack", "community", "auto", "api", "slack"),
    _ch("webhook", "Generic Webhook", "social", "auto", "api", "webhook"),
    # 媒体（需图片/视频，缺媒体则 disabled）
    _ch("instagram", "Instagram", "social", "auto", "api", "instagram"),
    _ch("pinterest", "Pinterest", "social", "auto", "api", "pinterest"),
    _ch("youtube", "YouTube", "video", "auto", "api", "youtube"),
    _ch("tiktok", "TikTok", "video", "auto", "api", "tiktok"),
]

# 纯人工渠道（无 API、无表单，只生成草稿 + 人肉提交）
MANUAL_CHANNELS: List[dict] = [
    _ch("reddit", "Reddit", "community", "manual", "manual"),
    _ch("hackernews", "Hacker News", "community", "manual", "manual"),
    _ch("indiehackers", "Indie Hackers", "community", "manual", "manual"),
    _ch("lobsters", "Lobsters", "community", "manual", "manual"),
    _ch("medium", "Medium", "blog", "manual", "manual"),
    _ch("substack", "Substack", "blog", "manual", "manual"),
    _ch("capterra", "Capterra", "review", "manual", "manual"),
    _ch("appsumo", "AppSumo", "launch", "manual", "manual"),
]


def browser_channel(r: Recipe) -> dict:
    return {"slug": r.slug, "name": r.name, "category": "directory",
            "tier": r.tier, "method": "browser", "recipe": r}


def all_channels(recipe_list: List[Recipe]) -> List[dict]:
    """合并三类渠道：API + 浏览器目录 + 纯人工。"""
    return list(API_CHANNELS) + [browser_channel(r) for r in recipe_list] + list(MANUAL_CHANNELS)


def filter_channels(channels: List[dict], tier: str = "auto,semi,manual",
                    only: str = "") -> List[dict]:
    tiers = set(tier.split(","))
    result = [c for c in channels if c["tier"] in tiers]
    if only:
        slugs = set(only.split(","))
        result = [c for c in result if c["slug"] in slugs]
    return result


def channel_status(ch: dict) -> str:
    """返回渠道的启用状态：enabled / disabled（+原因）/ manual。"""
    if ch["method"] == "manual":
        return "manual"
    if ch["method"] == "api":
        ok, missing = api_module.is_configured(ch["api"]["type"])
        return "enabled" if ok else f"disabled ({', '.join(missing)})"
    # browser：auto 始终可用；semi 需 CDP；manual 生成清单
    return "enabled" if ch["tier"] == "auto" else ("needs-cdp" if ch["tier"] == "semi" else "manual")
