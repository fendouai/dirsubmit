"""加载 product.yaml 与环境变量。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

from .models import Product


def load_product(path: str | Path = "product.yaml") -> Product:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"未找到 {p}，请先运行 `dirsubmit init` 生成模板并填写。"
        )
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return Product(
        name=data.get("name", ""),
        url=data.get("url", ""),
        tagline=data.get("tagline", ""),
        description=data.get("description", ""),
        features=[str(x) for x in data.get("features", [])],
        pricing=str(data.get("pricing", "")),
        categories=[str(x) for x in data.get("categories", [])],
        keywords=[str(x) for x in data.get("keywords", [])],
        logo_url=data.get("logo_url", ""),
        email=data.get("email", ""),
        twitter=data.get("twitter", ""),
    )


def product_template() -> str:
    return """# 产品信息（AI 文案与表单填充的唯一数据源）
name: My SaaS          # 产品名
url: https://example.com
tagline: 一句话卖点
description: |
  2-4 句产品介绍，说明做什么、给谁用、解决什么问题。
features:
  - 功能点 1
  - 功能点 2
  - 功能点 3
pricing: Freemium      # 定价模型
categories:            # 候选分类，AI 会按目录挑选
  - Productivity
  - AI
keywords:
  - automation
  - saas
logo_url: https://example.com/logo.png
email: you@example.com  # 部分目录需要
twitter: yourhandle
"""


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def load_dotenv(path: str | Path = ".env") -> None:
    """加载 .env 到 os.environ（只填充未设置的变量）。"""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
