"""API 渠道发布：覆盖所有可通过官方 API 自动化发布的渠道。

设计：每个渠道声明「必需凭证」（环境变量）。
- 凭证未配置 → 状态 `disabled`（不启用，distribute 自动跳过）
- 已配置 → 执行发布，返回 `published` / `failed`

文本类渠道全实现；媒体类（图片/视频）渠道已留结构，缺媒体时返回 disabled。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Tuple

import requests

_UA = {"User-Agent": "dirsubmit/0.1"}


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# 每个 API 渠道的必需凭证（环境变量）
REQUIREMENTS: Dict[str, list] = {
    "telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
    "discord": ["DISCORD_WEBHOOK_URL"],
    "slack": ["SLACK_WEBHOOK_URL"],
    "webhook": ["WEBHOOK_URL"],
    "devto": ["DEVTO_API_KEY"],
    "bluesky": ["BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"],
    "mastodon": ["MASTODON_INSTANCE", "MASTODON_ACCESS_TOKEN"],
    "wordpress": ["WORDPRESS_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
    "ghost": ["GHOST_ADMIN_URL", "GHOST_ADMIN_KEY"],
    "hashnode": ["HASHNODE_TOKEN"],
    "x": ["X_ACCESS_TOKEN"],
    "linkedin": ["LINKEDIN_ACCESS_TOKEN"],
    "facebook": ["FACEBOOK_PAGE_ID", "FACEBOOK_ACCESS_TOKEN"],
    "threads": ["THREADS_ACCESS_TOKEN"],
    "instagram": ["INSTAGRAM_USER_ID", "INSTAGRAM_ACCESS_TOKEN"],
    "pinterest": ["PINTEREST_ACCESS_TOKEN", "PINTEREST_BOARD_ID"],
    "youtube": ["YOUTUBE_ACCESS_TOKEN"],
    "tiktok": ["TIKTOK_ACCESS_TOKEN", "TIKTOK_OPEN_ID"],
}


def is_configured(api_type: str) -> Tuple[bool, list]:
    missing = [v for v in REQUIREMENTS.get(api_type, []) if not _env(v)]
    return len(missing) == 0, missing


def publish(api_type: str, title: str, message: str, dry_run: bool = False,
            extra: Dict[str, str] | None = None) -> Tuple[str, str]:
    ok, missing = is_configured(api_type)
    if not ok:
        return "disabled", f"未配置 {', '.join(missing)}"
    if dry_run:
        return "dry-run", f"[{api_type}] 仅演练：{title}"

    handler = _HANDLERS.get(api_type)
    if handler is None:
        return "skipped", f"未实现 {api_type}"
    try:
        return handler(title, message, extra or {})
    except Exception as e:  # noqa: BLE001
        return "failed", f"{api_type} 发布异常：{e}"


# ---------- 文本/消息渠道 ----------

def _telegram(title, message, extra):
    text = f"*{title}*\n\n{message}"
    r = requests.post(f"https://api.telegram.org/bot{_env('TELEGRAM_BOT_TOKEN')}/sendMessage",
                      json={"chat_id": extra.get("chat_id") or _env("TELEGRAM_CHAT_ID"),
                            "text": text, "parse_mode": "Markdown"}, timeout=30)
    ok = r.ok and r.json().get("ok")
    return ("published" if ok else "failed", "已发送" if ok else f"Telegram {r.status_code}")


def _discord(title, message, extra):
    r = requests.post(extra.get("webhook_url") or _env("DISCORD_WEBHOOK_URL"),
                      json={"content": f"**{title}**\n{message}"}, timeout=30)
    return ("published" if r.status_code in (200, 204) else "failed", f"Discord {r.status_code}")


def _slack(title, message, extra):
    r = requests.post(extra.get("webhook_url") or _env("SLACK_WEBHOOK_URL"),
                      json={"text": f"*{title}*\n{message}"}, timeout=30)
    ok = r.status_code == 200 and r.text.strip() == "ok"
    return ("published" if ok else "failed", f"Slack {r.status_code}")


def _webhook(title, message, extra):
    r = requests.post(extra.get("url") or _env("WEBHOOK_URL"),
                      json={"title": title, "message": message}, headers=_UA, timeout=30)
    return ("published" if r.ok else "failed", f"Webhook {r.status_code}")


# ---------- 博客渠道 ----------

def _devto(title, message, extra):
    r = requests.post("https://dev.to/api/articles",
                      headers={"api-key": _env("DEVTO_API_KEY"), **_UA},
                      json={"article": {"title": title, "body_markdown": message,
                                        "published": False}}, timeout=30)
    ok = r.ok and "id" in r.json()
    return ("published" if ok else "failed",
            "已创建草稿" if ok else f"DEV.to {r.status_code}")


def _wordpress(title, message, extra):
    url = _env("WORDPRESS_URL").rstrip("/")
    r = requests.post(f"{url}/wp-json/wp/v2/posts",
                      auth=(_env("WORDPRESS_USERNAME"), _env("WORDPRESS_APP_PASSWORD")),
                      json={"title": title, "content": message, "status": "draft"}, timeout=30)
    return ("published" if r.ok else "failed",
            "已创建草稿" if r.ok else f"WordPress {r.status_code}")


def _ghost(title, message, extra):
    url = _env("GHOST_ADMIN_URL").rstrip("/")
    key = _env("GHOST_ADMIN_KEY")
    key_id, secret = key.split(":", 1)
    header = base64.urlsafe_b64encode(json.dumps(
        {"alg": "HS256", "typ": "JWT", "kid": key_id}).encode()).decode().rstrip("=")
    now = int(time.time())
    payload = base64.urlsafe_b64encode(json.dumps(
        {"iat": now, "exp": now + 300, "aud": "/admin/"}).encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    token = f"{header}.{payload}.{sig}"
    r = requests.post(f"{url}/ghost/api/admin/posts/",
                      headers={"Authorization": f"Ghost {token}", **_UA},
                      json={"posts": [{"title": title,
                                       "mobiledoc": json.dumps(
                                           {"version": "0.3.1", "atoms": [], "cards": [],
                                            "markups": [],
                                            "sections": [[1, "p", [[0, [], 0, message]]]]}),
                                       "status": "draft"}]}, timeout=30)
    return ("published" if r.ok else "failed",
            "已创建草稿" if r.ok else f"Ghost {r.status_code}")


def _hashnode(title, message, extra):
    query = ("mutation PublishPost($input: PublishPostInput!) "
             "{ publishPost(input: $input) { post { url } } }")
    pub = _env("HASHNODE_PUBLICATION_ID")
    variables = {"input": {"title": title, "contentMarkdown": message,
                           "publicationId": pub or None}}
    r = requests.post("https://gql.hashnode.com",
                      headers={"Authorization": _env("HASHNODE_TOKEN")},
                      json={"query": query, "variables": variables}, timeout=30)
    ok = r.ok and "errors" not in r.json()
    return ("published" if ok else "failed",
            "已发布" if ok else f"Hashnode {r.status_code}: {r.text[:120]}")


# ---------- 社交渠道（OAuth access token） ----------

def _bluesky(title, message, extra):
    s = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",
                      json={"identifier": _env("BLUESKY_HANDLE"),
                            "password": _env("BLUESKY_APP_PASSWORD")}, timeout=30)
    if not s.ok:
        return "failed", f"Bluesky 登录失败 {s.status_code}"
    data = s.json()
    text = f"{title}\n\n{message}"[:3000]
    r = requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",
                      headers={"Authorization": f"Bearer {data['accessJwt']}"},
                      json={"repo": data["did"], "collection": "app.bsky.feed.post",
                            "record": {"$type": "app.bsky.feed.post", "text": text,
                                       "createdAt": datetime.now(timezone.utc).isoformat()}},
                      timeout=30)
    return ("published" if r.ok else "failed", "已发布" if r.ok else f"Bluesky {r.status_code}")


def _mastodon(title, message, extra):
    instance = _env("MASTODON_INSTANCE").rstrip("/")
    r = requests.post(f"{instance}/api/v1/statuses",
                      headers={"Authorization": f"Bearer {_env('MASTODON_ACCESS_TOKEN')}"},
                      data={"status": f"{title}\n\n{message}"}, timeout=30)
    return ("published" if r.ok else "failed", "已发布" if r.ok else f"Mastodon {r.status_code}")


def _x(title, message, extra):
    text = f"{title}\n{message}"[:280]
    r = requests.post("https://api.x.com/2/tweets",
                      headers={"Authorization": f"Bearer {_env('X_ACCESS_TOKEN')}"},
                      json={"text": text}, timeout=30)
    return ("published" if r.ok else "failed", "已发布" if r.ok else f"X {r.status_code}")


def _linkedin(title, message, extra):
    person = _env("LINKEDIN_PERSON_ID") or "me"
    r = requests.post("https://api.linkedin.com/v2/ugcPosts",
                      headers={"Authorization": f"Bearer {_env('LINKEDIN_ACCESS_TOKEN')}",
                               "X-Restli-Protocol-Version": "2.0.0", **_UA},
                      json={"author": f"urn:li:person:{person}",
                            "lifecycleState": "PUBLISHED",
                            "specificContent": {"com.linkedin.ugc.ShareContent": {
                                "shareCommentary": {"text": f"{title}\n{message}"},
                                "shareMediaCategory": "NONE"}},
                            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}},
                      timeout=30)
    return ("published" if r.ok else "failed", "已发布" if r.ok else f"LinkedIn {r.status_code}")


def _facebook(title, message, extra):
    r = requests.post(f"https://graph.facebook.com/v19.0/{_env('FACEBOOK_PAGE_ID')}/feed",
                      data={"message": f"{title}\n{message}",
                            "access_token": _env("FACEBOOK_ACCESS_TOKEN")}, timeout=30)
    return ("published" if r.ok else "failed", "已发布" if r.ok else f"Facebook {r.status_code}")


def _threads(title, message, extra):
    user_id = _env("THREADS_USER_ID")
    r = requests.post(f"https://graph.threads.net/v1.0/{user_id}/threads",
                      data={"media_type": "TEXT", "text": f"{title}\n{message}",
                            "access_token": _env("THREADS_ACCESS_TOKEN")}, timeout=30)
    return ("published" if r.ok else "failed", "已发布" if r.ok else f"Threads {r.status_code}")


# ---------- 媒体渠道（需图片/视频，文本分发暂不支持） ----------

def _instagram(title, message, extra):
    if not extra.get("image_url"):
        return "disabled", "Instagram 需要图片（image_url），纯文本暂不支持"
    r = requests.post(f"https://graph.facebook.com/v19.0/{_env('INSTAGRAM_USER_ID')}/media",
                      data={"image_url": extra["image_url"], "caption": f"{title}\n{message}",
                            "access_token": _env("INSTAGRAM_ACCESS_TOKEN")}, timeout=30)
    return ("published" if r.ok else "failed", "已发布" if r.ok else f"Instagram {r.status_code}")


def _pinterest(title, message, extra):
    if not extra.get("image_url"):
        return "disabled", "Pinterest 需要图片（image_url）"
    r = requests.post("https://api.pinterest.com/v5/pins",
                      headers={"Authorization": f"Bearer {_env('PINTEREST_ACCESS_TOKEN')}"},
                      json={"board_id": _env("PINTEREST_BOARD_ID"),
                            "title": title, "description": message,
                            "media_source": {"source_type": "image_url",
                                             "url": extra["image_url"]}}, timeout=30)
    return ("published" if r.ok else "failed", "已发布" if r.ok else f"Pinterest {r.status_code}")


def _youtube(title, message, extra):
    if not extra.get("video_file"):
        return "disabled", "YouTube 需要视频文件（video_file）"
    return "skipped", "YouTube 视频上传需分块上传，暂未实现"


def _tiktok(title, message, extra):
    if not extra.get("video_file"):
        return "disabled", "TikTok 需要视频文件（video_file）"
    return "skipped", "TikTok 视频上传暂未实现"


_HANDLERS = {
    "telegram": _telegram, "discord": _discord, "slack": _slack, "webhook": _webhook,
    "devto": _devto, "wordpress": _wordpress, "ghost": _ghost, "hashnode": _hashnode,
    "bluesky": _bluesky, "mastodon": _mastodon, "x": _x, "linkedin": _linkedin,
    "facebook": _facebook, "threads": _threads, "instagram": _instagram,
    "pinterest": _pinterest, "youtube": _youtube, "tiktok": _tiktok,
}
