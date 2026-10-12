"""Offline checks for indexed values and separation from newsletter forms."""
from pathlib import Path

import pytest

from dirsubmit.engine import _confirmed, _fill, _find, _launch_browser, build_values, resolve_value
from dirsubmit.models import Copy, Product
from dirsubmit.recipes import load_recipe


RECIPE_PATH = Path(__file__).resolve().parents[1] / "recipes" / "insidr-ai.json"


@pytest.mark.parametrize("source, expected", [
    ("categories[0]", "Writing"),
    ("categories[1]", "Productivity"),
    ("categories", "Writing, Productivity"),
    ("ai.tags[0]", "English"),
    ("ai.category", "Generated category"),
    ("categories[2]", ""),
    ("categories[-1]", ""),
    ("categories[0][0]", ""),
    ("description[0]", ""),
    ("missing[0]", ""),
    ("categories[" + "9" * 5000 + "]", ""),
])
def test_list_item_values_are_bounded_and_do_not_replace_list_values(source, expected):
    product = Product("WarmQuant", "https://warmquant.com/", description="English writing",
                      categories=["Writing", "Productivity"])
    copy = Copy("insidr-ai", category="Generated category", tags=["English", "Drafts"])
    assert resolve_value(source, product, copy) == expected


def test_empty_primary_category_blocks_before_opening_browser(monkeypatch):
    from dirsubmit import engine

    recipe = load_recipe(RECIPE_PATH)
    product = Product("WarmQuant", "https://warmquant.com/", description="English writing")
    monkeypatch.setattr(engine, "_run_playwright", lambda *args, **kwargs: pytest.fail("browser opened"))
    status, note = engine.submit(recipe, product, Copy(recipe.slug), mode="cdp")
    assert status == "blocked"
    assert "tag" in note


def test_insidr_form_and_receipt_never_select_newsletter():
    from playwright.sync_api import sync_playwright

    recipe = load_recipe(RECIPE_PATH)
    assert recipe.tier == "semi" and not recipe.requires_auth
    product = Product("WarmQuant", "https://warmquant.com/",
                      description="WarmQuant provides English writing assistance.",
                      categories=["Writing", "Productivity"])
    values = build_values(recipe, product, Copy(recipe.slug, category="Unrelated generated category"))
    # Both forms deliberately reuse Elementor field names, IDs and success text.
    html = """
      <form id="newsletter" class="elementor-form" name="Newsletter">
        <input type="hidden" name="form_id" value="newsletter">
        <input type="hidden" name="post_id" value="3417">
        <textarea id="form-field-message" name="form_fields[message]">newsletter message</textarea>
        <input id="form-field-name" name="form_fields[name]" value="newsletter name">
        <input id="form-field-email" name="form_fields[email]" type="email" value="newsletter@example.test">
        <button type="submit">Subscribe</button>
        <div class="elementor-message-success" role="alert">Your submission was successful</div>
      </form>
      <form id="tool" class="elementor-form" name="Submit tools" aria-label="Submit tools">
        <input type="hidden" name="form_id" value="6ad8e4a">
        <input type="hidden" name="post_id" value="3417">
        <textarea id="form-field-message" name="form_fields[message]"></textarea>
        <input id="form-field-name" name="form_fields[name]" type="text">
        <input id="form-field-email" name="form_fields[email]" type="text" required>
        <button type="submit"><span></span></button>
      </form>
      <script>
        window.fixtureSubmits = {newsletter: 0, tool: 0};
        document.querySelectorAll('form').forEach(form => {
          form.addEventListener('submit', event => {
            event.preventDefault(); window.fixtureSubmits[form.id]++;
            if (form.id === 'tool') {
              form.reset();
              const receipt = document.createElement('div');
              receipt.className = 'elementor-message elementor-message-success';
              receipt.setAttribute('role', 'alert');
              receipt.textContent = 'Your submission was successful';
              form.append(receipt);
            }
          });
        });
      </script>
    """
    with sync_playwright() as playwright:
        browser = _launch_browser(playwright)
        try:
            context = browser.new_context()
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(html)
            assert not _confirmed(page, recipe.success)
            for field in recipe.fields:
                assert _fill(page, field, values[field.name])
            assert page.locator("#tool [name='form_fields[message]']").input_value() == product.description
            assert page.locator("#tool [name='form_fields[name]']").input_value() == product.url
            assert page.locator("#tool [name='form_fields[email]']").input_value() == "Writing"
            assert page.locator("#newsletter [name='form_fields[message]']").input_value() == "newsletter message"
            assert page.locator("#newsletter [name='form_fields[name]']").input_value() == "newsletter name"
            assert page.locator("#newsletter [name='form_fields[email]']").input_value() == "newsletter@example.test"
            button = _find(page, recipe.submit_selector)
            assert button is not None
            button.click()
            assert page.evaluate("window.fixtureSubmits") == {"newsletter": 0, "tool": 1}
            assert _confirmed(page, recipe.success)
            assert page.locator(recipe.success["selector"]).inner_text() == recipe.verify["native_success_text"]
        finally:
            browser.close()
