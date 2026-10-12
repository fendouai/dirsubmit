"""Controlled offline tests for strict Unloc inputs, guards and real navigation.

All browser requests are intercepted. No live submission, external POST, user
browser profile, or real Unloc server action is used by these tests.
"""
import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from dirsubmit import engine
from dirsubmit.automation import task_payload, validate_result
from dirsubmit.config import load_product, product_template
from dirsubmit.models import Copy, Product
from dirsubmit.recipes import load_recipe


ROOT = Path(__file__).resolve().parents[1]
RECIPE_PATH = ROOT / "recipes" / "unloc.json"


def product_for(name="WarmQuant"):
    if name == "WarmQuant":
        return Product(name, "https://warmquant.com/",
                       tagline="AI English drafts with writing angles and editable saved drafts.",
                       categories=["Writing", "Productivity"], pricing="Freemium",
                       email="support@example.test", submitter_name="fei wang")
    return Product("WeWorkBuddy", "https://weworkbuddy.com/",
                   tagline="Source-backed topic research, creator idea backlogs and exports.",
                   categories=["Research", "Productivity"], pricing="Free",
                   email="owner@example.test", submitter_name="fei wang")


def fixture_html(outcome="success"):
    # Paid checkout is deliberately placed before the real form. The real
    # form starts in a paid intent so the recipe must choose listing explicitly.
    return r"""
      <aside><h1>Received.</h1><p>The listing is pending review.</p></aside>
      <form id="paid-bait">
        <input name="intent" type="radio" value="pin" checked>
        <input name="toolName" value="paid bait name">
        <input name="toolUrl" value="https://paid.example.test/">
        <input name="toolTagline" value="paid bait tagline">
        <input name="submittedBy" value="Paid Person">
        <input name="submittedEmail" value="paid@example.test">
        <input name="unlocHp" value="paid bait company">
        <button type="submit">Continue to checkout · $149/mo</button>
      </form>
      <form id="tool" class="relative space-y-6" autocomplete="off" novalidate>
        <fieldset><legend>What do you want to do?</legend>
          <label><input name="intent" type="radio" value="pin" checked>Category pin</label>
          <label><input name="intent" type="radio" value="claim">Claim #1</label>
          <label><input name="intent" type="radio" value="listing">Free listing</label>
        </fieldset>
        <label for="toolName">Tool name</label><input id="toolName" name="toolName" required>
        <label for="toolUrl">Website</label><input id="toolUrl" name="toolUrl" type="url" required>
        <label for="toolTagline">Tool description</label>
        <input id="toolTagline" name="toolTagline" minlength="20" required>
        <select id="categorySlug" name="categorySlug" required>
          <option value="">Choose one</option>
          <option value="writing-content">Writing &amp; Content</option>
          <option value="social-creators">Social &amp; Creators</option>
        </select>
        <select id="pricing" name="pricing" required>
          <option value="freemium" selected>Free options</option>
          <option value="free">Free</option><option value="paid">Paid</option>
        </select>
        <input id="submittedBy" name="submittedBy" required pattern="\s*\S+(?:\s+\S+)+\s*">
        <input id="submittedEmail" name="submittedEmail" type="email" required>
        <div aria-hidden="true" style="position:fixed;left:-10000px">
          <label for="unlocHp">Company website</label>
          <input id="unlocHp" name="unlocHp" tabindex="-1" value="">
        </div>
        <button type="submit">Submit for review</button>
      </form>
      <script>
        const outcome = __OUTCOME__, form = document.querySelector('#tool');
        sessionStorage.setItem('fixtureCounts', JSON.stringify({tool:0,paid:0,paidClicks:0}));
        const updateCounts = key => {
          const counts = JSON.parse(sessionStorage.getItem('fixtureCounts'));
          counts[key]++; sessionStorage.setItem('fixtureCounts', JSON.stringify(counts));
        };
        document.querySelectorAll('input[name="intent"]').forEach(input => {
          input.addEventListener('click', () => {
            if (input.value !== 'listing') updateCounts('paidClicks');
          });
        });
        document.querySelector('#paid-bait').onsubmit = e => {
          e.preventDefault(); updateCounts('paid');
        };
        document.querySelector('#submittedEmail').addEventListener('input', () => {
          if (outcome === 'autofilled_honeypot') document.querySelector('#unlocHp').value = 'autofill.example.test';
          if (outcome === 'intent_drift') form.querySelector('[name="intent"][value="pin"]').checked = true;
          if (outcome === 'pricing_drift') document.querySelector('#pricing').value = 'paid';
        });
        if (outcome === 'missing_category') form.querySelector('option[value="writing-content"]').remove();
        if (outcome === 'ambiguous_form') document.body.append(form.cloneNode(true));
        form.onsubmit = e => {
          e.preventDefault(); updateCounts('tool');
          sessionStorage.setItem('fixtureFields', JSON.stringify(Object.fromEntries(new FormData(form))));
          form.querySelector('button').textContent = 'Sending…';
          if (outcome === 'server_error') {
            const error = document.createElement('p');
            error.setAttribute('role','alert'); error.textContent='Could not save this listing.';
            form.append(error); form.querySelector('button').textContent='Submit for review';
          } else if (outcome === 'no_receipt') {
            form.querySelector('button').textContent='Submit for review';
          } else if (outcome === 'wrong_url') {
            document.body.insertAdjacentHTML('beforeend','<main><h1>Received.</h1><p>The listing is pending review.</p></main>');
          } else {
            location.href='/submit/thanks';
          }
        };
      </script>
    """.replace("__OUTCOME__", json.dumps(outcome))


def receipt_html(outcome):
    if outcome == "incomplete_receipt":
        return "<main><h1>Received.</h1><p>An unrelated status.</p></main>"
    if outcome == "outside_main":
        return "<main><h1>Received.</h1></main><aside>The listing is pending review.</aside>"
    return "<main><h1>Received.</h1><p>The listing is pending review.</p></main>"


def run_offline(monkeypatch, tmp_path, product=None, outcome="success"):
    recipe = replace(load_recipe(RECIPE_PATH), wait_ms=40)
    captured = {"requests": []}
    original_launch = engine._launch_browser
    original_run = engine._run_playwright

    def launch_offline(playwright, cdp_url=None):
        browser = original_launch(playwright)
        context = browser.new_context()
        context.set_default_timeout(150)

        def route_request(route):
            request = route.request
            captured["requests"].append((request.method, request.url))
            # Interception prevents all network activity, including POST.
            if request.method != "GET":
                route.abort()
            elif request.url == recipe.submit_url:
                if outcome == "initial_receipt":
                    route.fulfill(status=302, headers={"location": "/submit/thanks"})
                else:
                    route.fulfill(status=200, content_type="text/html", body=fixture_html(outcome))
            elif request.url == "https://unloc.tools/submit/thanks":
                route.fulfill(status=200, content_type="text/html", body=receipt_html(outcome))
            else:
                route.abort()
        context.route("**/*", route_request)
        original_close = browser.close

        def capture_and_close():
            page = context.pages[0]
            captured["counts"] = page.evaluate(
                "JSON.parse(sessionStorage.getItem('fixtureCounts') || "
                "'{\"tool\":0,\"paid\":0,\"paidClicks\":0}')")
            captured["saved_fields"] = page.evaluate("JSON.parse(sessionStorage.getItem('fixtureFields') || '{}')")
            captured["url"] = page.url
            if page.locator("#tool").count():
                captured["current_fields"] = {
                    name: page.locator("#tool [name='" + name + "']").first.input_value()
                    for name in engine.build_values(recipe, product or product_for(), Copy(recipe.slug))
                }
                captured["honeypot"] = page.locator("#tool [name='unlocHp']").first.input_value()
                captured["paid_bait_name"] = page.locator("#paid-bait [name='toolName']").input_value()
                captured["alerts"] = page.locator("[role='alert']").all_inner_texts()
            original_close()
        monkeypatch.setattr(browser, "close", capture_and_close)
        return browser

    monkeypatch.setattr(engine, "_launch_browser", launch_offline)
    monkeypatch.setattr(engine, "_run_playwright",
                        lambda *a, **k: original_run(*a, **k, timeout=0.35))
    result = engine.submit(recipe, product or product_for(), Copy(recipe.slug),
                           mode="headless", evidence_dir=tmp_path)
    return result, captured


@pytest.mark.parametrize("name, category, pricing", [
    ("WarmQuant", "writing-content", "freemium"),
    ("WeWorkBuddy", "social-creators", "free"),
])
def test_known_product_values_map_without_using_ai_or_product_name_as_person(name, category, pricing):
    recipe = load_recipe(RECIPE_PATH)
    product = product_for(name)
    values = engine.build_values(recipe, product, Copy(recipe.slug, tagline="Unreviewed generated text", category="Unrelated"))
    assert values["categorySlug"] == category and values["pricing"] == pricing
    assert values["toolTagline"] == product.tagline
    assert values["submittedBy"] == product.submitter_name and values["submittedBy"] != product.name
    assert engine.validate_values(recipe, values) == []


@pytest.mark.parametrize("changes", [
    {"categories": ["Robotics"]},
    {"pricing": "Unknown"},
    {"tagline": "x" * 19},
    {"tagline": "x" * 161},
    {"tagline": "A long enough line\nwith an unsupported newline"},
    {"submitter_name": "feiwang"},
    {"submitter_name": ""},
    {"email": "invalid"},
    {"url": "http://warmquant.com/"},
    {"name": "x"},
])
def test_invalid_input_blocks_before_any_browser_or_agent(monkeypatch, changes):
    recipe = load_recipe(RECIPE_PATH)
    product = replace(product_for(), **changes)
    monkeypatch.setattr(engine, "_run_playwright", lambda *a, **k: pytest.fail("browser opened"))
    monkeypatch.setattr("dirsubmit.automation.run_computer_use", lambda *a, **k: pytest.fail("executor called"))
    for mode in ("headless", "computer-use"):
        status, note = engine.submit(recipe, product, Copy(recipe.slug), mode=mode)
        assert status == "blocked"
        assert "fallback" in note or any(field.name in note for field in recipe.fields)


@pytest.mark.parametrize("size", [20, 160])
def test_complete_tagline_boundaries_are_valid_without_truncation(size):
    recipe = load_recipe(RECIPE_PATH)
    values = engine.build_values(recipe, replace(product_for(), tagline="x" * size), Copy(recipe.slug))
    assert values["toolTagline"] == "x" * size
    assert engine.validate_values(recipe, values) == []


def test_product_files_load_separate_verified_submitter_and_current_pricing():
    for filename in ("warmquant.yaml", "weworkbuddy.yaml", "botstest.yaml"):
        product = load_product(ROOT / "products" / filename)
        assert product.submitter_name == "fei wang" and product.email
    recipe = load_recipe(RECIPE_PATH)
    assert engine.build_values(recipe, load_product(ROOT / "products/warmquant.yaml"), Copy(recipe.slug))["pricing"] == "freemium"
    assert engine.build_values(recipe, load_product(ROOT / "products/weworkbuddy.yaml"), Copy(recipe.slug))["pricing"] == "free"
    with pytest.raises(ValueError):
        engine.build_values(recipe, load_product(ROOT / "products/botstest.yaml"), Copy(recipe.slug))


def test_extension_without_guard_reading_blocks_before_navigation():
    class UnreadableBridge:
        def connected(self):
            return True
        def call(self, *args, **kwargs):
            pytest.fail("unsupported extension performed an action")
    recipe = load_recipe(RECIPE_PATH)
    assert engine.submit(recipe, product_for(), Copy(recipe.slug), mode="extension",
                         bridge=UnreadableBridge())[0] == "blocked"


@pytest.mark.parametrize("name", ["WarmQuant", "WeWorkBuddy"])
def test_browser_single_free_submission_requires_navigation_and_actual_receipt(monkeypatch, tmp_path, name):
    product = product_for(name)
    (status, _), captured = run_offline(monkeypatch, tmp_path, product)
    assert status == "submitted"
    assert captured["counts"] == {"tool": 1, "paid": 0, "paidClicks": 0}
    assert captured["saved_fields"]["intent"] == "listing"
    assert captured["saved_fields"]["unlocHp"] == ""
    assert captured["saved_fields"]["categorySlug"] == ("writing-content" if name == "WarmQuant" else "social-creators")
    assert captured["saved_fields"]["pricing"] == ("freemium" if name == "WarmQuant" else "free")
    assert captured["url"] == "https://unloc.tools/submit/thanks"
    assert all(method == "GET" for method, _ in captured["requests"])
    assert captured["requests"][:2] == [
        ("GET", "https://unloc.tools/submit"), ("GET", "https://unloc.tools/submit/thanks")]
    assert list(tmp_path.glob("*/page.png"))


@pytest.mark.parametrize("outcome", [
    "autofilled_honeypot", "intent_drift", "pricing_drift", "missing_category", "ambiguous_form",
])
def test_last_dom_guards_block_autofill_paid_drift_and_ambiguous_forms(monkeypatch, tmp_path, outcome):
    (status, _), captured = run_offline(monkeypatch, tmp_path, outcome=outcome)
    assert status == "blocked"
    assert captured["counts"] == {"tool": 0, "paid": 0, "paidClicks": 0}
    assert captured["paid_bait_name"] == "paid bait name"
    assert ("GET", "https://unloc.tools/submit/thanks") not in captured["requests"]
    if outcome == "autofilled_honeypot":
        assert captured["honeypot"] == "autofill.example.test"  # Actual value, not unchanged HTML attribute.


@pytest.mark.parametrize("outcome", ["no_receipt", "server_error", "wrong_url", "incomplete_receipt", "outside_main"])
def test_no_complete_receipt_is_unverified_and_never_retried(monkeypatch, tmp_path, outcome):
    (status, _), captured = run_offline(monkeypatch, tmp_path, outcome=outcome)
    assert status == "unverified"
    assert captured["counts"] == {"tool": 1, "paid": 0, "paidClicks": 0}
    if outcome in {"no_receipt", "server_error", "wrong_url"}:
        expected = engine.build_values(load_recipe(RECIPE_PATH), product_for(), Copy("unloc"))
        assert captured["current_fields"] == expected
        assert captured["honeypot"] == ""
    if outcome == "server_error":
        assert captured["alerts"] == ["Could not save this listing."]
    assert json.loads(next(tmp_path.glob("*/result.json")).read_text())["status"] == "unverified"


def test_generic_thanks_redirect_before_click_blocks_without_touching_a_form(monkeypatch, tmp_path):
    (status, _), captured = run_offline(monkeypatch, tmp_path, outcome="initial_receipt")
    assert status == "blocked"
    assert captured["url"] == "https://unloc.tools/submit/thanks"
    assert captured["counts"] == {"tool": 0, "paid": 0, "paidClicks": 0}


def test_old_or_success_remains_compatible_and_new_and_requires_same_visible_scope():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = engine._launch_browser(playwright)
        try:
            context = browser.new_context()
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content("<main>Received.</main><aside>The listing is pending review.</aside>")
            assert engine._confirmed(page, {"selector": "missing", "text": "Received."})
            assert not engine._confirmed(page, {"all_of": [
                {"selector": "main", "texts": ["Received.", "The listing is pending review."]}]})
            assert not engine._confirmed(page, load_recipe(RECIPE_PATH).success)
        finally:
            browser.close()


def valid_agent_result(payload):
    checks = payload["recipe"]["pre_submit_checks"]
    values = payload["field_values"]
    return {
        "task_id": payload["id"], "product_url": payload["product_url"], "directory": payload["directory"],
        "status": "submitted", "evidence_text": "Sending followed by the visible pending-review receipt.",
        "pre_submit_observations": [
            {"selector": c["selector"], "count": 1, "value": c["value"] if "value" in c else values[c["field"]]}
            for c in checks
        ],
        "confirmation": {
            "submit_click_count": 1,
            "before": {"url": payload["submit_url"], "elements": []},
            "after": {"url": "https://unloc.tools/submit/thanks", "elements": [
                {"selector": "main", "count": 1, "visible": True, "text": "Received. The listing is pending review."}
            ]},
        },
    }


@pytest.mark.parametrize("mutation", [
    "no_observations", "bad_honeypot", "paid_intent", "two_clicks", "initial_thanks",
    "wrong_task", "wrong_product", "wrong_directory", "receipt_text_missing", "receipt_hidden",
])
def test_agent_success_strings_cannot_bypass_guards_or_and_evidence(mutation):
    payload = task_payload(load_recipe(RECIPE_PATH), product_for(), Copy("unloc"))
    result = valid_agent_result(payload)
    assert validate_result(result, payload=payload)[0] == "submitted"
    if mutation == "no_observations":
        result.pop("pre_submit_observations")
    elif mutation == "bad_honeypot":
        result["pre_submit_observations"][1]["value"] = "autofilled"
    elif mutation == "paid_intent":
        result["pre_submit_observations"][0]["value"] = "pin"
    elif mutation == "two_clicks":
        result["confirmation"]["submit_click_count"] = 2
    elif mutation == "initial_thanks":
        result["confirmation"]["before"] = copy.deepcopy(result["confirmation"]["after"])
    elif mutation == "wrong_task":
        result["task_id"] = "different"
    elif mutation == "wrong_product":
        result["product_url"] = "https://different.example.test/"
    elif mutation == "wrong_directory":
        result["directory"] = "other-directory"
    elif mutation == "receipt_text_missing":
        result["confirmation"]["after"]["elements"][0]["text"] = "Received."
    elif mutation == "receipt_hidden":
        result["confirmation"]["after"]["elements"][0]["visible"] = False
    assert validate_result(result, payload=payload)[0] == "unverified"


def test_computer_handoff_and_resume_apply_same_structured_validation(monkeypatch, tmp_path):
    from dirsubmit.cli import build_parser, cmd_resume
    from dirsubmit.store import Store

    recipe = load_recipe(RECIPE_PATH)
    monkeypatch.delenv("DIRSUBMIT_COMPUTER_COMMAND", raising=False)
    status, _ = engine.submit(recipe, product_for(), Copy(recipe.slug), mode="computer-use", evidence_dir=tmp_path)
    assert status == "needs_handoff"
    task_path = next(tmp_path.glob("*.json"))
    payload = json.loads(task_path.read_text())
    assert payload["field_values"]["submittedBy"] == "fei wang"
    result = valid_agent_result(payload)
    result.pop("confirmation")
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result))
    args = build_parser().parse_args(["--db", str(tmp_path / "test.db"), "resume",
                                     "--task", str(task_path), "--result", str(result_path)])
    assert cmd_resume(args) == 0
    store = Store(tmp_path / "test.db", payload["product_url"])
    try:
        assert store.get_status("unloc") == "unverified"
    finally:
        store.close()
    result_path.write_text(json.dumps(valid_agent_result(payload)))
    assert cmd_resume(args) == 0
    store = Store(tmp_path / "test.db", payload["product_url"])
    try:
        assert store.get_status("unloc") == "submitted"
    finally:
        store.close()


@pytest.mark.parametrize("invalid", [
    {"success": {"all_of": []}},
    {"success": {"all_of": [{"text": "Received."}], "text": "OR bypass"}},
    {"pre_submit_checks": [{"selector": "input", "field": ["unhashable"]}]},
    {"pre_submit_checks": [{"selector": "input", "value": "", "field": "toolName"}]},
    {"fields": [{"name": "toolName", "constraints": {"max_length": True}}]},
    {"fields": [{"name": "toolName", "constraints": {"min_length": 30, "max_length": 20}}]},
    {"fields": [{"name": "toolName", "value_map": {"Writing": 123}}]},
])
def test_invalid_guard_or_constraint_configuration_is_rejected(tmp_path, invalid):
    data = {"slug": "invalid", "name": "Invalid", "fields": [{"name": "toolName"}]}
    data.update(invalid)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_recipe(path)


def test_browser_use_structured_schema_and_task_binding_without_network(monkeypatch):
    import sys
    from types import SimpleNamespace
    from dirsubmit.automation import run_browser_use

    captured = {}

    class FakeAgent:
        def __init__(self, **kwargs):
            self.payload = json.loads(kwargs["task"])
            self.schema = kwargs["output_model_schema"]
            captured["json_schema"] = self.schema.model_json_schema()

        async def run(self, **kwargs):
            result = valid_agent_result(self.payload)
            # Use the actual new Pydantic model, not a schema-shaped stub.
            validated = self.schema.model_validate(result)
            return SimpleNamespace(final_result=lambda: validated.model_dump_json())

    monkeypatch.setitem(sys.modules, "browser_use", SimpleNamespace(
        Agent=FakeAgent, BrowserSession=lambda **k: object(), ChatOpenAI=lambda **k: object()))
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-key")
    payload = task_payload(load_recipe(RECIPE_PATH), product_for(), Copy("unloc"))
    status, _ = run_browser_use(payload, "http://unused.example.test")
    assert status == "submitted"
    assert "confirmation" in captured["json_schema"]["properties"]
    assert "pre_submit_observations" in captured["json_schema"]["properties"]


@pytest.mark.parametrize("success", [
    {"text": "Awaiting review", "selector": "missing-selector"},
    {"selector": "main", "text": "missing text"},
    {"url_contains": "/thanks", "text": "missing text"},
    {"url_equals": "https://unloc.tools/submit/thanks", "text": "missing text"},
])
def test_guarded_agent_keeps_legacy_or_rules_and_requires_new_confirmation(success):
    recipe = replace(load_recipe(RECIPE_PATH), success=success)
    payload = task_payload(recipe, product_for(), Copy("unloc"))
    result = valid_agent_result(payload)
    result["confirmation"]["after"]["elements"] = [
        {"selector": "body", "count": 1, "visible": True, "text": "Awaiting review"},
        {"selector": "main", "count": 1, "visible": True, "text": "Awaiting review"},
    ]
    assert validate_result(result, payload=payload)[0] == "submitted"
    absent = copy.deepcopy(result)
    absent["confirmation"]["after"] = {"url": payload["submit_url"], "elements": []}
    assert validate_result(absent, payload=payload)[0] == "unverified"
    existing = copy.deepcopy(result)
    existing["confirmation"]["before"] = copy.deepcopy(existing["confirmation"]["after"])
    if "url_contains" not in success and "url_equals" not in success:
        existing["confirmation"]["before"]["url"] = payload["submit_url"]
    assert validate_result(existing, payload=payload)[0] == "unverified"


@pytest.mark.parametrize("result", [[], None])
def test_computer_executor_non_object_result_retains_uncertainty(monkeypatch, result):
    from types import SimpleNamespace
    from dirsubmit import automation

    payload = task_payload(load_recipe(RECIPE_PATH), product_for(), Copy("unloc"))
    calls = []

    def execute(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout=json.dumps(result))

    monkeypatch.setattr(automation.subprocess, "run", execute)
    status, note = automation.run_computer_use(payload, "offline-fixture-executor")
    assert status == "unverified" and "JSON object" in note
    assert len(calls) == 1  # No fallback or retry after the executor's uncertain outcome.


@pytest.mark.parametrize("invalid", ["array", "null", "url_list", "url_null"])
def test_resume_invalid_executor_output_records_unverified_without_sqlite_type_error(tmp_path, invalid):
    from dirsubmit.cli import build_parser, cmd_resume
    from dirsubmit.store import Store

    payload = task_payload(load_recipe(RECIPE_PATH), product_for(), Copy("unloc"))
    result = valid_agent_result(payload)
    if invalid == "array":
        result = []
    elif invalid == "null":
        result = None
    elif invalid == "url_list":
        result["live_url"] = ["invalid"]
    else:
        result["live_url"] = None
    task_path, result_path = tmp_path / "task.json", tmp_path / "result.json"
    task_path.write_text(json.dumps(payload))
    result_path.write_text(json.dumps(result))
    db_path = tmp_path / "test.db"
    args = build_parser().parse_args(["--db", str(db_path), "resume",
                                     "--task", str(task_path), "--result", str(result_path)])
    assert cmd_resume(args) == 0
    store = Store(db_path, payload["product_url"])
    try:
        row = store.all_submissions()[0]
        assert row["status"] == "unverified" and row["live_url"] == ""
        assert row["submitted_at"] is None
    finally:
        store.close()


def test_product_template_never_supplies_a_fake_submitter_name(tmp_path):
    path = tmp_path / "product.yaml"
    path.write_text(product_template())
    assert load_product(path).submitter_name == ""
    assert 'submitter_name: ""' in path.read_text()
