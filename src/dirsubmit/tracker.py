"""审核状态跟踪：重抓目录页验证产品是否已上线。"""

from __future__ import annotations

import re

import requests

from .models import Product, Recipe

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}


def check(recipe: Recipe, product: Product) -> tuple[str, str]:
    """返回 (status, note)。status ∈ approved|pending|rejected。"""
    v = recipe.verify or {}
    vtype = v.get("type", "search")
    url = (v.get("url") or recipe.homepage or "").replace("{name}", product.name)

    if not url:
        return "pending", "未配置 verify url"

    try:
        r = requests.get(url, headers=_UA, timeout=20, allow_redirects=True)
        if r.status_code >= 400:
            return "pending", f"HTTP {r.status_code}"
        html = r.text
    except requests.RequestException as e:
        return "pending", f"抓取失败：{e}"

    if vtype == "url":
        # 直接检查产品 URL 是否出现在页面里
        needle = product.url.rstrip("/")
        live = needle in html
    else:
        # 站内搜索：产品名出现即视为收录
        name = re.escape(product.name)
        live = bool(re.search(name, html, re.IGNORECASE))

    if live:
        return "approved", f"已收录（{url}）"
    return "pending", "尚未收录，可能仍在审核中"
