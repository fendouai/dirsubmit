"""Public-listing verification; all HTTP responses are offline fixtures."""
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from dirsubmit import cli, recipes, tracker
from dirsubmit.models import Product, Recipe
from dirsubmit.store import Store


PRODUCT = Product('Botstest', 'https://botstest.com/')
PRODUCT_LINK = '<a href="https://botstest.com/">Botstest</a>'


def public_recipe(**kwargs):
    data = dict(slug='directory', name='Directory', homepage='https://directory.test',
                verify={'type': 'search', 'url': 'https://directory.test/search?q={name}'})
    data.update(kwargs)
    return Recipe(**data)


def response(url, text=PRODUCT_LINK, status_code=200):
    return SimpleNamespace(status_code=status_code, url=url, text=text)


def forbid_network(*args, **kwargs):
    raise AssertionError('This source must not issue an HTTP request')


@pytest.mark.parametrize('vtype', ['manual', 'unknown', None, {'bad': True}])
def test_unsupported_verification_never_requests_page(monkeypatch, vtype):
    monkeypatch.setattr(tracker.requests, 'get', forbid_network)
    recipe = public_recipe(verify={'type': vtype, 'url': 'https://directory.test'})
    assert tracker.check(recipe, PRODUCT)[0] == 'pending'


def test_actual_unloc_manual_verification_never_requests_homepage(monkeypatch):
    monkeypatch.setattr(tracker.requests, 'get', forbid_network)
    recipe = recipes.load_recipe(Path(__file__).resolve().parents[1] / 'recipes/unloc.json')
    assert tracker.check(recipe, Product('WarmQuant', 'https://warmquant.com/'))[0] == 'pending'


def test_non_string_verify_url_never_requests_page(monkeypatch):
    monkeypatch.setattr(tracker.requests, 'get', forbid_network)
    recipe = public_recipe(verify={'type': 'url', 'url': ['https://directory.test']})
    assert tracker.check(recipe, PRODUCT)[0] == 'pending'


@pytest.mark.parametrize('path', [
    '/dashboard/my-products', '/account/tools/edit/33469716', '/auth/signup',
    '/login', '/submit/thanks', '/success', '/s/submit', '/users/sign_in',
    '/%64ashboard/my-products',
])
def test_explicit_nonpublic_source_does_not_prove_listing(monkeypatch, path):
    monkeypatch.setattr(tracker.requests, 'get', forbid_network)
    recipe = public_recipe(verify={'type': 'url', 'url': 'https://directory.test' + path})
    assert tracker.check(recipe, PRODUCT)[0] == 'pending'


@pytest.mark.parametrize('tier', ['semi', 'free', 'github'])
@pytest.mark.parametrize('kind', ['destination_marker', 'pr_url'])
def test_github_intake_is_not_approved_regardless_of_execution_tier(monkeypatch, tier, kind):
    monkeypatch.setattr(tracker.requests, 'get', forbid_network)
    if kind == 'destination_marker':
        recipe = public_recipe(slug='github-best-of-ai-ai-directories', tier=tier)
    else:
        recipe = public_recipe(slug='not-a-github-slug', tier=tier,
                               homepage='https://github.com/best-of-ai/ai-directories',
                               verify={'type': 'url', 'url': 'https://github.com/best-of-ai/ai-directories/pull/435'})
    assert tracker.check(recipe, PRODUCT)[0] == 'pending'


@pytest.mark.parametrize('final_url', [
    'https://botstest.com/', 'https://unrelated.test/listing',
    'https://directory.test/dashboard/my-products',
    'https://directory.test/account/tools', 'https://directory.test/auth/signin',
    'https://directory.test/submit/thanks', '',
])
def test_redirect_or_result_context_cannot_approve_intake(monkeypatch, final_url):
    monkeypatch.setattr(tracker.requests, 'get', lambda *a, **k: response(final_url))
    assert tracker.check(public_recipe(), PRODUCT)[0] == 'pending'


def test_final_product_address_is_not_directory_publication(monkeypatch):
    product = Product('Acme', 'https://directory.test/app')
    monkeypatch.setattr(tracker.requests, 'get', lambda *a, **k: response(
        product.url, '<a href="https://directory.test/app">Acme</a>'))
    assert tracker.check(public_recipe(), product)[0] == 'pending'


def test_mismatched_configured_official_host_never_requests(monkeypatch):
    monkeypatch.setattr(tracker.requests, 'get', forbid_network)
    recipe = public_recipe(verify={'type': 'url', 'url': PRODUCT.url})
    assert tracker.check(recipe, PRODUCT)[0] == 'pending'


@pytest.mark.parametrize('vtype', ['search', 'url'])
def test_normal_public_search_or_detail_accepts_target_link(monkeypatch, vtype):
    final_url = 'https://www.directory.test/tools/botstest'
    text = '<main><h1>Botstest</h1>' + PRODUCT_LINK + '</main><footer>Other submissions pending review</footer>'
    seen = []
    def get(url, **kwargs):
        seen.append(url)
        return response(final_url, text)
    monkeypatch.setattr(tracker.requests, 'get', get)
    recipe = public_recipe(requires_auth=True, verify={
        'type': vtype, 'url': 'https://directory.test/search?q={name}' if vtype == 'search' else final_url})
    status, note = tracker.check(recipe, PRODUCT)
    assert status == 'approved' and final_url in note
    assert len(seen) == 1


def test_relative_href_uses_final_directory_url(monkeypatch):
    final_url = 'https://directory.test/catalog/current/'
    product = Product('Acme', 'https://directory.test/catalog/products/acme')
    monkeypatch.setattr(tracker.requests, 'get', lambda *a, **k: response(
        final_url, '<a href="../products/acme">Acme</a>'))
    assert tracker.check(public_recipe(), product)[0] == 'approved'


@pytest.mark.parametrize('text', [
    '<h1>Botstest search results</h1>',
    '<a href="https://botstest.com.evil/">Botstest</a>',
    '<a href="javascript://botstest.com/">Botstest</a>',
    '<a href="https://[broken/">Botstest</a>',
])
def test_name_echo_or_nonproduct_link_does_not_approve(monkeypatch, text):
    monkeypatch.setattr(tracker.requests, 'get', lambda *a, **k: response('https://directory.test/search', text))
    assert tracker.check(public_recipe(), PRODUCT)[0] == 'pending'


def test_broken_unrelated_link_does_not_hide_valid_product_link(monkeypatch):
    monkeypatch.setattr(tracker.requests, 'get', lambda *a, **k: response(
        'https://directory.test/search', '<a href="https://[broken/">Bad</a>' + PRODUCT_LINK))
    assert tracker.check(public_recipe(), PRODUCT)[0] == 'approved'


@pytest.mark.parametrize('status_code', [302, 404])
def test_non_success_response_cannot_approve_link(monkeypatch, status_code):
    monkeypatch.setattr(tracker.requests, 'get', lambda *a, **k: response(
        'https://directory.test/search', status_code=status_code))
    assert tracker.check(public_recipe(), PRODUCT)[0] == 'pending'


def test_request_failure_retains_pending(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.ConnectionError('offline fixture')
    monkeypatch.setattr(tracker.requests, 'get', fail)
    assert tracker.check(public_recipe(), PRODUCT)[0] == 'pending'


@pytest.mark.parametrize('previous_status', ['submitted', 'unverified'])
@pytest.mark.parametrize('source', ['github', 'receipt', 'product_redirect'])
def test_cli_check_preserves_intake_and_submission_timestamp(tmp_path, monkeypatch, previous_status, source):
    recipe = public_recipe()
    if source == 'github':
        recipe = public_recipe(slug='github-best-of-ai-ai-directories', tier='semi')
        monkeypatch.setattr(tracker.requests, 'get', forbid_network)
    elif source == 'receipt':
        recipe = public_recipe(verify={'type': 'url', 'url': 'https://directory.test/account/tools'})
        monkeypatch.setattr(tracker.requests, 'get', forbid_network)
    else:
        monkeypatch.setattr(tracker.requests, 'get', lambda *a, **k: response(PRODUCT.url))
    db = tmp_path / 'isolated-submissions.db'
    store = Store(db, product_url=PRODUCT.url)
    store.set_status(recipe.slug, 'semi', 'submitted', note='Original intake receipt')
    if previous_status == 'unverified':
        store.set_status(recipe.slug, 'semi', 'unverified', note='Uncertain final click; do not retry')
    before = store.all_submissions()[0]
    store.close()
    monkeypatch.setattr(cli, '_product', lambda args: PRODUCT)
    monkeypatch.setattr(cli, '_recipes', lambda args: [recipe])
    monkeypatch.setattr(cli, '_store', lambda args: Store(db, product_url=PRODUCT.url))
    assert cli.cmd_status(SimpleNamespace(only=None, check=True)) == 0
    store = Store(db, product_url=PRODUCT.url)
    after = store.all_submissions()[0]
    store.close()
    assert after['status'] == before['status'] == previous_status
    assert after['submitted_at'] == before['submitted_at'] and after['submitted_at']
    assert after['last_checked_at']
