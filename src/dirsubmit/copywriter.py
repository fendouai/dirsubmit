"""由 Product 生成每个目录的差异化文案。

有 LLM key 时调用 LLM；否则回退到确定性模板，保证离线可跑。
"""

from __future__ import annotations

from .llm import LLMClient, LLMUnavailable, extract_json
from .models import Copy, Product, Recipe


_PROMPT = """你是 SaaS 目录提交专家。为目录「{dir_name}」（受众：{dir_audience}）写一份提交文案。

产品信息：
- 名称：{name}
- 网址：{url}
- 一句话：{tagline}
- 简介：{description}
- 功能：{features}
- 定价：{pricing}
- 候选分类：{categories}
- 关键词：{keywords}

要求：
1. 文案针对该目录的受众调整措辞，与其它目录的文案区分开，不要照抄简介。
2. 简介 120-180 字英文。
3. 分类尽量从候选分类里选，没有合适的就给出最贴切的一个。
4. 只输出 JSON，格式：
{{"tagline": "...", "description": "...", "category": "...", "tags": ["...", "..."]}}
"""


def _fallback_copy(product: Product, recipe: Recipe) -> Copy:
    category = product.categories[0] if product.categories else "Software"
    tags = (product.keywords + product.categories)[:5]
    return Copy(
        directory=recipe.slug,
        tagline=product.tagline or f"{product.name} — {category}",
        description=product.description or product.tagline or product.name,
        category=category,
        tags=tags or ["saas"],
    )


def generate_copy(product: Product, recipe: Recipe, llm: LLMClient) -> Copy:
    if not llm.available():
        return _fallback_copy(product, recipe)

    audience = "startup founders and makers" if recipe.tier != "manual" else "general audience"
    prompt = _PROMPT.format(
        dir_name=recipe.name,
        dir_audience=audience,
        name=product.name,
        url=product.url,
        tagline=product.tagline,
        description=product.description or "（无）",
        features=", ".join(str(f) for f in product.features) or "（无）",
        pricing=str(product.pricing or "（无）"),
        categories=", ".join(str(c) for c in product.categories) or "（无）",
        keywords=", ".join(str(k) for k in product.keywords) or "（无）",
    )
    try:
        raw = llm.chat([{"role": "user", "content": prompt}], json_mode=True)
        data = extract_json(raw)
        if data:
            return Copy(
                directory=recipe.slug,
                tagline=data.get("tagline", "") or _fallback_copy(product, recipe).tagline,
                description=data.get("description", "") or _fallback_copy(product, recipe).description,
                category=data.get("category", "") or _fallback_copy(product, recipe).category,
                tags=data.get("tags", []) or _fallback_copy(product, recipe).tags,
            )
    except LLMUnavailable as e:
        print(f"  [warn] {recipe.slug}: {e}，回退模板文案")
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] {recipe.slug}: 文案生成失败（{e}），回退模板文案")
    return _fallback_copy(product, recipe)


_MESSAGE_PROMPT = """你是 SaaS 内容分发专家。为渠道「{channel}」（分类：{category}）写一条产品发布内容。

产品：{name}（{url}）
一句话：{tagline}
简介：{description}

要求：
- 分类为 social/community：写一条 1-3 句的短帖（含卖点 + 链接 + 3-5 个 hashtag）。
- 分类为 blog：写一篇 200-400 字的 Markdown 短文（含标题）。
- 分类为 review/launch：写一段适合平台审核的产品介绍（150-250 字，客观不浮夸）。
- 只输出 JSON：{{"title": "...", "message": "..."}}
"""


def generate_message(product: Product, channel: dict, llm: LLMClient) -> dict:
    """为 API/纯人工渠道生成适配文案，返回 {"title":..., "message":...}。"""
    category = channel.get("category", "social")
    name = channel.get("name", channel.get("slug", ""))

    def fallback():
        if category == "blog":
            return {"title": f"Introducing {product.name}",
                    "message": f"# {product.name}\n\n{product.description}\n\n"
                               f"{product.tagline}\n\n{product.url}"}
        if category in ("review", "launch"):
            return {"title": product.name,
                    "message": f"{product.name} — {product.tagline}\n\n"
                               f"{product.description}\n\n{product.url}"}
        return {"title": product.name,
                "message": f"{product.tagline}\n{product.url}\n"
                           f"#{' #'.join(product.keywords[:4])}"}

    if not llm.available():
        return fallback()

    prompt = _MESSAGE_PROMPT.format(
        channel=name, category=category, name=product.name, url=product.url,
        tagline=product.tagline, description=product.description or "（无）")
    try:
        raw = llm.chat([{"role": "user", "content": prompt}], json_mode=True)
        data = extract_json(raw)
        if data and data.get("message"):
            return {"title": data.get("title", product.name),
                    "message": data.get("message", "")}
    except LLMUnavailable as e:
        print(f"  [warn] {name}: {e}，回退模板")
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] {name}: 文案生成失败（{e}），回退模板")
    return fallback()
