"""加载与校验 recipes/*.json。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .models import FieldSpec, Recipe

_VALID_TIERS = {"auto", "semi", "manual"}


def load_recipe(path: Path) -> Recipe:
    data = json.loads(path.read_text(encoding="utf-8"))
    slug = data.get("slug") or path.stem
    fields = [FieldSpec(**f) for f in data.get("fields", [])]
    tier = data.get("tier", "manual")
    if tier not in _VALID_TIERS:
        raise ValueError(f"{slug}: 非法 tier '{tier}'，可选 {_VALID_TIERS}")
    return Recipe(
        slug=slug,
        name=data.get("name", slug),
        submit_url=data.get("submit_url", ""),
        homepage=data.get("homepage", ""),
        dr=int(data.get("dr", 0)),
        tier=tier,
        requires_auth=bool(data.get("requires_auth", False)),
        verify=data.get("verify", {}),
        fields=fields,
        submit_selector=data.get("submit_selector", ""),
        wait_ms=int(data.get("wait_ms", 0)),
    )


def load_all(recipes_dir: str | Path = "recipes") -> List[Recipe]:
    d = Path(recipes_dir)
    if not d.is_dir():
        return []
    recipes = []
    for p in sorted(d.glob("*.json")):
        try:
            recipes.append(load_recipe(p))
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            print(f"[warn] 跳过 {p.name}: {e}")
    return recipes


def by_slug(recipes: List[Recipe], slug: str):
    for r in recipes:
        if r.slug == slug:
            return r
    return None
