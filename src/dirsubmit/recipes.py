"""加载与校验 recipes/*.json。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .models import FieldSpec, Recipe

_VALID_TIERS = {"auto", "semi", "manual"}


def _validate_field(slug, field):
    if not isinstance(field.value_map, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in field.value_map.items()):
        raise ValueError(f"{slug}: {field.name} value_map must map exact strings to strings")
    rules = field.constraints
    if not isinstance(rules, dict) or set(rules) - {"min_length", "max_length", "min_words", "max_words", "allowed", "pattern"}:
        raise ValueError(f"{slug}: invalid constraints for {field.name}")
    for key in ("min_length", "max_length", "min_words", "max_words"):
        if key in rules and (type(rules[key]) is not int or rules[key] < 0):
            raise ValueError(f"{slug}: {field.name} {key} must be a nonnegative integer")
    for lower, upper in (("min_length", "max_length"), ("min_words", "max_words")):
        if lower in rules and upper in rules and rules[lower] > rules[upper]:
            raise ValueError(f"{slug}: contradictory constraints for {field.name}")
    if "allowed" in rules and (not isinstance(rules["allowed"], list) or
                               not rules["allowed"] or any(not isinstance(v, str) for v in rules["allowed"])):
        raise ValueError(f"{slug}: {field.name} allowed must be a nonempty string array")
    if "pattern" in rules:
        import re
        if not isinstance(rules["pattern"], str):
            raise ValueError(f"{slug}: {field.name} pattern must be a string")
        try:
            re.compile(rules["pattern"])
        except re.error as exc:
            raise ValueError(f"{slug}: invalid pattern for {field.name}") from exc


def _validate_success(slug, success):
    if "all_of" not in success:
        return  # Preserve the legacy selector/text/url_contains OR semantics.
    if set(success) != {"all_of"} or not isinstance(success["all_of"], list) or not success["all_of"]:
        raise ValueError(f"{slug}: all_of must be a nonempty condition array without OR keys")
    for condition in success["all_of"]:
        if not isinstance(condition, dict) or not condition or set(condition) - {"url_equals", "url_contains", "selector", "text", "texts"}:
            raise ValueError(f"{slug}: invalid all_of confirmation condition")
        for key, value in condition.items():
            if key == "texts":
                if not isinstance(value, list) or not value or any(not isinstance(v, str) or not v for v in value):
                    raise ValueError(f"{slug}: texts must be a nonempty array of nonempty strings")
            elif not isinstance(value, str) or not value:
                raise ValueError(f"{slug}: confirmation {key} must be a nonempty string")


def _validate_guards(slug, checks, fields):
    if not isinstance(checks, list):
        raise ValueError(f"{slug}: pre_submit_checks must be an array")
    names = {f.name for f in fields if not f.submit}
    for check in checks:
        if not isinstance(check, dict) or set(check) - {"selector", "value", "field", "include_hidden"}:
            raise ValueError(f"{slug}: invalid pre-submit value check")
        if not isinstance(check.get("selector"), str) or not check["selector"]:
            raise ValueError(f"{slug}: each value check requires an exact selector")
        if ("value" in check) == ("field" in check):
            raise ValueError(f"{slug}: each value check requires exactly one value or field")
        if "value" in check and not isinstance(check["value"], str):
            raise ValueError(f"{slug}: checked value must be a string")
        if "field" in check and (not isinstance(check["field"], str) or check["field"] not in names):
            raise ValueError(f"{slug}: checked field is not a recipe field")
        if "include_hidden" in check and type(check["include_hidden"]) is not bool:
            raise ValueError(f"{slug}: include_hidden must be a boolean")


def load_recipe(path: Path) -> Recipe:
    data = json.loads(path.read_text(encoding="utf-8"))
    slug = data.get("slug") or path.stem
    fields = [FieldSpec(**f) for f in data.get("fields", [])]
    tier = data.get("tier", "manual")
    if tier not in _VALID_TIERS:
        raise ValueError(f"{slug}: 非法 tier '{tier}'，可选 {_VALID_TIERS}")
    for key in ("success", "auth"):
        if not isinstance(data.get(key, {}), dict):
            raise ValueError(f"{slug}: {key} must be an object")
    for field in fields:
        _validate_field(slug, field)
    _validate_success(slug, data.get("success", {}))
    _validate_guards(slug, data.get("pre_submit_checks", []), fields)
    if not isinstance(data.get("steps", []), list):
        raise ValueError(f"{slug}: steps must be an array")
    for step in data.get("steps", []):
        if not isinstance(step, dict):
            raise ValueError(f"{slug}: each step must be an object")
        if step.get("action") == "click" and step.get("selector") == data.get("submit_selector"):
            raise ValueError(f"{slug}: pre-submit steps cannot click the final submit selector")
        if step.get("action") not in {"click", "wait", "fill"}:
            raise ValueError(f"{slug}: unsupported step {step}")
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
        success=data.get("success", {}),
        auth=data.get("auth", {}),
        steps=data.get("steps", []),
        pre_submit_checks=data.get("pre_submit_checks", []),
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
