"""非浏览器逻辑的单元测试。"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dirsubmit import copywriter, engine, recipes, tracker  # noqa: E402
from dirsubmit.llm import LLMClient, extract_json  # noqa: E402
from dirsubmit.models import Product  # noqa: E402
from dirsubmit.store import Store  # noqa: E402


def _product():
    return Product(
        name="Acme Tool", url="https://acme.example.com",
        tagline="Automate anything", description="A great tool.",
        features=["fast", "easy"], pricing="Freemium",
        categories=["Productivity", "AI"], keywords=["automation"],
        email="a@b.com",
    )


def test_load_recipe(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({
        "name": "X", "slug": "x", "tier": "auto",
        "fields": [{"name": "name", "source": "name", "selectors": ["#n"]}],
    }))
    r = recipes.load_recipe(p)
    assert r.tier == "auto"
    assert r.fields[0].source == "name"


def test_load_recipe_invalid_tier(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"name": "X", "tier": "bogus"}))
    with pytest.raises(ValueError):
        recipes.load_recipe(p)


def test_fallback_copy_no_llm():
    os.environ.pop("DEEPSEEK_API_KEY", None)
    llm = LLMClient("deepseek")
    assert llm.available() is False
    from dirsubmit.models import Recipe
    r = Recipe(slug="x", name="X", tier="auto")
    c = copywriter.generate_copy(_product(), r, llm)
    assert c.category == "Productivity"
    assert c.tagline  # 非空回退


def test_resolve_value_mapping():
    p = _product()
    from dirsubmit.models import Copy
    c = Copy(directory="x", tagline="t", description="d", category="cat", tags=["a", "b"])
    assert engine.resolve_value("name", p, c) == "Acme Tool"
    assert engine.resolve_value("ai.category", p, c) == "cat"
    assert engine.resolve_value("ai.tags", p, c) == "a, b"
    assert engine.resolve_value("features", p, c) == "fast, easy"


def test_store_roundtrip(tmp_path):
    from dirsubmit.models import Copy
    db = tmp_path / "t.db"
    s = Store(db)
    s.upsert_copy(Copy(directory="x", tagline="t", description="d",
                       category="c", tags=["a"]))
    got = s.get_copy("x")
    assert got.tagline == "t"
    assert got.tags == ["a"]
    s.set_status("x", "auto", "submitted", "ok")
    assert s.get_status("x") == "submitted"
    s.close()


def test_tracker_search_match():
    from dirsubmit.models import Recipe
    r = Recipe(slug="x", name="X", homepage="https://x.com",
               verify={"type": "search", "url": "https://x.com/?q={name}"})
    import dirsubmit.tracker as t
    monkey = pytest.MonkeyPatch()
    class FakeResp:
        status_code = 200
        text = "<html>... Acme Tool ...</html>"
    monkey.setattr(t.requests, "get", lambda *a, **k: FakeResp())
    status, _ = t.check(r, _product())
    assert status == "approved"


def test_tracker_no_match():
    from dirsubmit.models import Recipe
    r = Recipe(slug="x", name="X", homepage="https://x.com",
               verify={"type": "search", "url": "https://x.com/?q={name}"})
    import dirsubmit.tracker as t
    monkey = pytest.MonkeyPatch()
    class FakeResp:
        status_code = 200
        text = "<html>nothing here</html>"
    monkey.setattr(t.requests, "get", lambda *a, **k: FakeResp())
    status, _ = t.check(r, _product())
    assert status == "pending"


def test_extract_json():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('prefix {"b": 2} suffix') == {"b": 2}
    assert extract_json("no json here") is None


def test_api_is_configured():
    import dirsubmit.api as a
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    os.environ.pop("TELEGRAM_CHAT_ID", None)
    ok, missing = a.is_configured("telegram")
    assert ok is False
    assert "TELEGRAM_BOT_TOKEN" in missing


def test_api_publish_disabled():
    import dirsubmit.api as a
    os.environ.pop("WEBHOOK_URL", None)
    status, note = a.publish("webhook", "t", "m")
    assert status == "disabled"
    assert "WEBHOOK_URL" in note


def test_api_publish_dryrun():
    os.environ["WEBHOOK_URL"] = "https://example.com/hook"
    import dirsubmit.api as a
    status, note = a.publish("webhook", "title", "msg", dry_run=True)
    assert status == "dry-run"
    os.environ.pop("WEBHOOK_URL", None)


def test_api_unknown_type():
    import dirsubmit.api as a
    status, note = a.publish("nonexistent", "t", "m")
    assert status == "skipped"  # 无凭证要求 → 通过配置检查，但无 handler → 未实现

