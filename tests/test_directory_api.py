"""Offline-only guard regressions; every transport is an in-memory fixture."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from dirsubmit import directory_api as d
from dirsubmit.models import Product
from dirsubmit.store import Store

URL = 'https://acme.example/'
EMAIL = 'contact@example.com'

@pytest.fixture(autouse=True)
def no_real_sessions(monkeypatch):
    def forbidden(*a, **kw):
        pytest.fail('No real HTTP session is allowed in offline tests')
    monkeypatch.setattr(d.requests, 'Session', forbidden)

class Response:
    def __init__(self, url, status=200, body=None):
        self.url, self.status_code, self.data = url, status, body
        self.content = json.dumps(body).encode()
    def json(self):
        if self.data is None:
            raise ValueError('contact@example.com secret-session')
        return self.data

def entry(**updates):
    v = {'id': 123, 'url': URL, 'tier': 'free', 'title': 'Acme', 'description': 'Original description', 'email': EMAIL, 'token': 'secret-session'}
    v.update(updates)
    return v

def setup(tmp_path):
    return Product(name='Acme', url=URL, email='business@acme.example', submitter_email=EMAIL), Store(tmp_path/'fixture.db', product_url=URL)

def transport(monkeypatch, responses):
    calls = []
    def request(method, url, payload=None):
        calls.append((method, url, payload))
        assert len([c for c in calls if c[0]=='POST']) <= 1
        value = responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value
    monkeypatch.setattr(d, '_request', request)
    return calls

def success(monkeypatch):
    return transport(monkeypatch, [Response(d.LISTINGS, body={'ok':True,'listings':[]}), Response(d.SUBMIT, 201, {'ok':True,'listing':entry()}), Response(d.LISTING+'123', body={'ok':True,'listing':entry()})])

def test_exact_payload_public_check_sanitization_and_no_replay(monkeypatch,tmp_path):
    p,s=setup(tmp_path);calls=success(monkeypatch)
    r=d.submit_curlship(p,s,tmp_path/'receipts')
    assert r['status']=='approved' and calls==[('GET',d.LISTINGS,None),('POST',d.SUBMIT,{'url':URL,'email':EMAIL}),('GET',d.LISTING+'123',None)]
    row=s.all_submissions()[0]
    assert row['directory']=='curlship.com' and row['product_key']==URL.rstrip('/') and row['submitted_at'] and row['last_checked_at'] and row['live_url']==d.LISTING+'123'
    text=Path(r['receipt']).read_text();receipt=json.loads(text)
    assert receipt['grade']=='S' and receipt['actual_submission'] is True and receipt['independent_public_verified'] is True
    assert EMAIL not in text and 'secret-session' not in text and 'token' not in text
    assert set(receipt['public_listing_fields'])=={'id','url','tier'}
    assert d.submit_curlship(p,s,tmp_path/'different-evidence-directory')['status']=='skipped'
    assert len(calls)==3
    s.close()

@pytest.mark.parametrize('url,email', [('http://acme.example/',EMAIL),('https://u:p@acme.example/',EMAIL),('https://acme.example:443/',EMAIL),('https://localhost/',EMAIL),('https://127.0.0.1/',EMAIL),('https://acme.example/p',EMAIL),('https://acme.example/?tier=paid',EMAIL),('https://acme.example/#x',EMAIL),(URL+' ',EMAIL),(URL,'a@b\r\nCc:x@y.com'),(URL,'')])
def test_invalid_input_blocks_before_network(tmp_path,url,email):
    p,s=setup(tmp_path);p.url=url;p.submitter_email=email
    assert d.submit_curlship(p,s,tmp_path)['status']=='blocked'
    assert s.all_submissions()==[];s.close()

def test_wrong_product_store_cannot_send_or_modify(tmp_path):
    p,s=setup(tmp_path);s.product_key='https://other.example'
    assert d.submit_curlship(p,s,tmp_path)['status']=='blocked' and s.all_submissions()==[];s.close()

def test_company_contact_is_not_registration_mailbox_fallback(tmp_path):
    p,s=setup(tmp_path);p.email=EMAIL;p.submitter_email=''
    assert d.submit_curlship(p,s,tmp_path)['status']=='blocked' and s.all_submissions()==[];s.close()

@pytest.mark.parametrize('host',['linktr.ee','bio.link','x.com','linkedin.com','medium.com','www.linktr.ee','profile.bio.link','www.x.com','app.linkedin.com','writer.medium.com'])
def test_known_disallowed_social_and_bio_hosts_block_before_any_request(tmp_path,host):
    p,s=setup(tmp_path);p.url='https://'+host+'/';s.product_key=p.url.rstrip('/')
    assert d.submit_curlship(p,s,tmp_path)['status']=='blocked' and s.all_submissions()==[];s.close()

@pytest.mark.parametrize('status',['submitted','approved','unverified'])
def test_protected_store_state_no_network_or_downgrade(tmp_path,status):
    p,s=setup(tmp_path);s.set_status(d.SLUG,'auto',status,'original','https://curlship.com/api/listing/9');before=s.all_submissions()
    assert d.submit_curlship(p,s,tmp_path)['status']=='skipped' and s.all_submissions()==before;s.close()

def test_dry_run_no_network_receipt_or_store(tmp_path):
    p,s=setup(tmp_path);assert d.submit_curlship(p,s,tmp_path/'no-file',True)['status']=='dry-run'
    assert not (tmp_path/'no-file').exists() and s.all_submissions()==[];s.close()

def test_existing_www_domain_blocks_without_claiming_new_submission(monkeypatch,tmp_path):
    p,s=setup(tmp_path);calls=transport(monkeypatch,[Response(d.LISTINGS,body={'ok':True,'listings':[entry(url='https://www.acme.example/other')]} )])
    assert d.submit_curlship(p,s,tmp_path)['status']=='blocked' and len(calls)==1 and s.all_submissions()==[];s.close()

@pytest.mark.parametrize('body',[None,{'ok':False,'listings':[]},{'ok':True,'listings':[],'has_more':True},{'ok':True,'listings':[],'total':2},{'ok':True,'listings':[{'url':None}]}])
def test_incomplete_or_malformed_duplicate_check_never_posts(monkeypatch,tmp_path,body):
    p,s=setup(tmp_path);calls=transport(monkeypatch,[Response(d.LISTINGS,body=body)])
    assert d.submit_curlship(p,s,tmp_path)['status']=='blocked' and len(calls)==1 and s.all_submissions()==[];s.close()

@pytest.mark.parametrize('status',[200,302,409,500])
def test_non201_is_uncertain_and_blocks_replay(monkeypatch,tmp_path,status):
    p,s=setup(tmp_path);calls=transport(monkeypatch,[Response(d.LISTINGS,body={'ok':True,'listings':[]}),Response(d.SUBMIT,status,{'ok':True,'listing':entry()})])
    assert d.submit_curlship(p,s,tmp_path/'r')['status']=='unverified' and s.get_status(d.SLUG)=='unverified'
    assert d.submit_curlship(p,s,tmp_path/'r2')['status']=='skipped' and len(calls)==2;s.close()

def test_post_timeout_keeps_durable_reservation_and_redacts_error(monkeypatch,tmp_path):
    p,s=setup(tmp_path);calls=transport(monkeypatch,[Response(d.LISTINGS,body={'ok':True,'listings':[]}),d.requests.Timeout(EMAIL+' secret-session')])
    r=d.submit_curlship(p,s,tmp_path/'r');assert r['status']=='unverified' and s.get_status(d.SLUG)=='unverified'
    receipt=Path(r['receipt']).read_text();assert EMAIL not in receipt and 'secret-session' not in receipt and EMAIL not in r['note']
    assert d.submit_curlship(p,s,tmp_path/'r2')['status']=='skipped' and len(calls)==2;s.close()

def test_confirmed201_receipt_save_failure_preserves_intake_and_replay_guard(monkeypatch,tmp_path):
    p,s=setup(tmp_path);calls=transport(monkeypatch,[Response(d.LISTINGS,body={'ok':True,'listings':[]}),Response(d.SUBMIT,201,{'ok':True,'listing':entry()})])
    def cannot_save(*a,**kw):raise OSError(EMAIL+' secret-session')
    monkeypatch.setattr(d,'_save',cannot_save)
    r=d.submit_curlship(p,s,tmp_path/'r')
    assert r['status']=='submitted' and r['live_url']==d.LISTING+'123' and s.get_status(d.SLUG)=='submitted'
    assert s.all_submissions()[0]['submitted_at'] and 'receipt persistence failed' in r['note']
    assert EMAIL not in r['note'] and 'secret-session' not in r['note']
    assert d.submit_curlship(p,s,tmp_path/'different-evidence-dir')['status']=='skipped' and len(calls)==2;s.close()

def test_duplicate_scope_is_host_www_not_registered_root_and409_never_creation(monkeypatch,tmp_path):
    p,s=setup(tmp_path);calls=transport(monkeypatch,[Response(d.LISTINGS,body={'ok':True,'listings':[entry(url='https://different.acme.example/')]}),Response(d.SUBMIT,409,{'ok':False})])
    r=d.submit_curlship(p,s,tmp_path)
    assert r['status']=='unverified' and len(calls)==2
    proof=json.loads(Path(r['receipt']).read_text())
    assert proof['actual_submission'] is False and 'not registered-root/eTLD' in proof['duplicate_check_scope']
    assert d.submit_curlship(p,s,tmp_path/'r2')['status']=='skipped' and len(calls)==2;s.close()

@pytest.mark.parametrize('changes',[{'id':True},{'id':456},{'url':'https://different.example/'},{'tier':'featured'},{'title':''},{'description':'changed'}])
def test_creation201_distinct_from_wrong_or_missing_public_proof(monkeypatch,tmp_path,changes):
    p,s=setup(tmp_path);calls=transport(monkeypatch,[Response(d.LISTINGS,body={'ok':True,'listings':[]}),Response(d.SUBMIT,201,{'ok':True,'listing':entry()}),Response(d.LISTING+'123',body={'ok':True,'listing':entry(**changes)})])
    r=d.submit_curlship(p,s,tmp_path);assert r['status']=='submitted' and s.get_status(d.SLUG)=='submitted'
    proof=json.loads(Path(r['receipt']).read_text());assert proof['grade']=='A' and proof['actual_submission'] is True and proof['independent_public_verified'] is False
    assert len(calls)==3;s.close()

def test_redirected_duplicate_response_blocked_and_POST_redirect_not_followed(monkeypatch,tmp_path):
    p,s=setup(tmp_path);calls=transport(monkeypatch,[Response('https://different.example/',body={'ok':True,'listings':[]})])
    assert d.submit_curlship(p,s,tmp_path)['status']=='blocked' and len(calls)==1;s.close()

def test_atomically_reserved_product_scope_prevents_second_claim(tmp_path):
    p,s=setup(tmp_path);second=Store(tmp_path/'fixture.db',product_url=URL)
    assert s.reserve_attempt(d.SLUG,'auto') is True and second.reserve_attempt(d.SLUG,'auto') is False
    other=Store(tmp_path/'fixture.db',product_url='https://other.example/')
    assert other.reserve_attempt(d.SLUG,'auto') is True
    assert len(s.all_submissions())==len(other.all_submissions())==1
    s.close();second.close();other.close()

def test_real_transport_new_anonymous_sessions_no_retry_redirect_or_env_auth(monkeypatch):
    sessions=[]
    class Cookies:
        def clear(self):self.cleared=True
    class Session:
        def __init__(self):self.cookies=Cookies();self.trust_env=True;self.auth='secret';self.mounts=[];sessions.append(self)
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def mount(self,url,adapter):self.mounts.append((url,adapter.max_retries.total))
        def request(self,method,url,**kwargs):
            assert self.trust_env is False and self.auth is None and self.cookies.cleared
            assert kwargs['allow_redirects'] is False and kwargs['timeout']==30
            assert set(kwargs['headers'])=={'Accept','Content-Type','User-Agent'}
            return Response(url,body={'ok':True})
    monkeypatch.setattr(d.requests,'Session',Session)
    d._request('GET',d.LISTINGS);d._request('POST',d.SUBMIT,{'url':URL,'email':EMAIL});d._request('GET',d.LISTING+'123')
    assert len(sessions)==3 and all(s.mounts==[('https://',0)] for s in sessions)

def test_CLI_reuses_API_registry_without_LLM_browser_or_duplicate_Store_write(monkeypatch,tmp_path):
    from dirsubmit import cli
    p,s=setup(tmp_path);calls=success(monkeypatch)
    def forbidden(*a,**kw):pytest.fail('CurlShip-only CLI must not initialize LLM or native/browser bridge')
    monkeypatch.setattr(cli,'_product',lambda a:p);monkeypatch.setattr(cli,'_store',lambda a:s);monkeypatch.setattr(cli,'_recipes',lambda a:[])
    monkeypatch.setattr(cli,'LLMClient',forbidden);monkeypatch.setattr(cli,'_start_bridge',forbidden);monkeypatch.setattr(cli.copywriter,'generate_message',forbidden)
    args=SimpleNamespace(provider=None,cdp_url=None,tier='auto',only=d.SLUG,force=True,mode='auto',dry_run=False,evidence_dir=str(tmp_path/'r'),drafts=str(tmp_path/'drafts'))
    assert cli.cmd_distribute(args)==0 and len(calls)==3
    check=Store(tmp_path/'fixture.db',product_url=URL);row=check.all_submissions()[0]
    assert row['status']=='approved' and row['submitted_at'] and row['live_url']==d.LISTING+'123';check.close()

def test_API_registration_is_explicit_zero_auth_and_not_generic_message_publish():
    from dirsubmit import api, channels
    ch=next(c for c in channels.API_CHANNELS if c['slug']==d.SLUG)
    assert ch['category']=='directory' and ch['method']=='api' and api.REQUIREMENTS['curlship']==[]
    assert channels.channel_status(ch)=='enabled'
    assert api.publish('curlship','unused title','unused generated message')[0]=='skipped'

def test_optional_submitter_email_config_and_legacy_defaults(tmp_path):
    from dirsubmit import config
    p=tmp_path/'product.yaml';p.write_text('name: Acme\nurl: '+URL+'\nemail: business@acme.example\nsubmitter_email: '+EMAIL+'\n')
    product=config.load_product(p)
    assert product.email=='business@acme.example' and product.submitter_email==EMAIL
    p.write_text('name: Acme\nurl: '+URL+'\nemail: business@acme.example\n')
    assert config.load_product(p).submitter_email=='' and Product(name='Legacy',url=URL).submitter_email==''
    assert 'submitter_email:' in config.product_template()


def test_CLI_fill_only_directory_previews_without_HTTP_receipt_or_reservation(monkeypatch, tmp_path, capsys):
    from dirsubmit import cli
    p, s = setup(tmp_path)
    before = s.all_submissions()
    def forbidden(*a, **kw):
        pytest.fail('API fill-only must not issue HTTP, publish, generate copy or start a bridge')
    monkeypatch.setattr(cli, '_product', lambda a: p)
    monkeypatch.setattr(cli, '_store', lambda a: s)
    monkeypatch.setattr(cli, '_recipes', lambda a: [])
    monkeypatch.setattr(cli, 'LLMClient', forbidden)
    monkeypatch.setattr(cli, '_start_bridge', forbidden)
    monkeypatch.setattr(cli.copywriter, 'generate_message', forbidden)
    monkeypatch.setattr(cli.api, 'publish', forbidden)
    monkeypatch.setattr(d, '_request', forbidden)
    args = SimpleNamespace(provider=None, cdp_url=None, tier='auto', only=d.SLUG,
                           force=True, mode='computer-use', dry_run=False, fill_only=True,
                           evidence_dir=str(tmp_path / 'no-receipts'), drafts=str(tmp_path / 'drafts'))
    assert cli.cmd_distribute(args) == 0
    assert '[preview]' in capsys.readouterr().out
    assert not (tmp_path / 'no-receipts').exists()
    check = Store(tmp_path / 'fixture.db', product_url=URL)
    assert check.all_submissions() == before
    check.close()


@pytest.mark.parametrize('only', ['', d.SLUG])
@pytest.mark.parametrize('fill_only', [False, True])
def test_registered_directory_API_excludes_stale_recipe_and_preserves_approved_force(monkeypatch, tmp_path, capsys, only, fill_only):
    from dirsubmit import cli, channels
    from dirsubmit.models import Recipe
    p, s = setup(tmp_path)
    s.set_status(d.SLUG, 'free', 'approved', 'original public receipt', d.LISTING + '99')
    before = s.all_submissions()
    registration = next(ch for ch in channels.API_CHANNELS if ch['slug'] == d.SLUG)
    monkeypatch.setattr(channels, 'API_CHANNELS', [registration])
    monkeypatch.setattr(channels, 'MANUAL_CHANNELS', [])
    monkeypatch.setattr(cli, '_product', lambda a: p)
    monkeypatch.setattr(cli, '_store', lambda a: s)
    monkeypatch.setattr(cli, '_recipes', lambda a: [Recipe(slug=d.SLUG, name='Legacy CurlShip browser route', tier='auto')])
    def forbidden(*a, **kw):
        pytest.fail('Registered directory API must not use a same-slug legacy browser route, HTTP or LLM')
    monkeypatch.setattr(cli, 'LLMClient', forbidden)
    monkeypatch.setattr(cli, '_start_bridge', forbidden)
    monkeypatch.setattr(cli.engine, 'submit', forbidden)
    monkeypatch.setattr(cli.copywriter, 'generate_copy', forbidden)
    monkeypatch.setattr(d, '_request', forbidden)
    args = SimpleNamespace(provider=None, cdp_url=None, tier='auto', only=only,
                           force=True, mode='auto', dry_run=False, fill_only=fill_only,
                           evidence_dir=str(tmp_path / 'no-receipts'), drafts=str(tmp_path / 'drafts'))
    assert cli.cmd_distribute(args) == 0
    output = capsys.readouterr().out
    assert '分发到 1 个渠道' in output
    assert ('[preview]' if fill_only else '[skipped]') in output
    check = Store(tmp_path / 'fixture.db', product_url=URL)
    assert check.all_submissions() == before
    check.close()
    assert not (tmp_path / 'no-receipts').exists()


def test_directory_API_route_priority_is_registry_driven_and_other_recipes_keep_order(monkeypatch):
    from dirsubmit import channels
    from dirsubmit.models import Recipe
    main = next(ch for ch in channels.API_CHANNELS if ch['slug'] == d.SLUG)
    alias = {**main, 'slug': 'fixture-other-directory-API'}
    message = next(ch for ch in channels.API_CHANNELS if ch['slug'] == 'wordpress')
    manual = next(ch for ch in channels.MANUAL_CHANNELS if ch['slug'] == 'reddit')
    monkeypatch.setattr(channels, 'API_CHANNELS', [main, alias, message])
    monkeypatch.setattr(channels, 'MANUAL_CHANNELS', [manual])
    ordinary = Recipe(slug='ordinary-old-recipe', name='Existing normal browser directory', tier='semi')
    unrelated_message = Recipe(slug='wordpress', name='Existing same-slug non-directory recipe', tier='semi')
    supplied = [Recipe(slug=d.SLUG, name='Stale primary'), ordinary,
                Recipe(slug=alias['slug'], name='Stale other registered directory API'), unrelated_message]
    result = channels.all_channels(supplied)
    assert [ch['slug'] for ch in result] == [d.SLUG, alias['slug'], 'wordpress', ordinary.slug, 'wordpress', 'reddit']
    browsers = [ch for ch in result if ch['method'] == 'browser']
    assert [ch['recipe'] for ch in browsers] == [ordinary, unrelated_message]
    assert supplied[0].slug == d.SLUG and len(supplied) == 4
    assert len(channels.filter_channels(result, 'auto,semi,manual', d.SLUG)) == 1
    assert len(channels.filter_channels(result, 'auto,semi,manual', alias['slug'])) == 1


def test_CLI_fill_only_message_API_does_not_publish_or_overwrite_history(monkeypatch, tmp_path, capsys):
    from dirsubmit import cli
    p, s = setup(tmp_path)
    s.set_status('wordpress', 'auto', 'approved', 'existing confirmed history', 'https://blog.example/post')
    before = s.all_submissions()
    def forbidden(*a, **kw):
        pytest.fail('Message API fill-only must not initialize an LLM, publish or generate content')
    monkeypatch.setattr(cli, '_product', lambda a: p)
    monkeypatch.setattr(cli, '_store', lambda a: s)
    monkeypatch.setattr(cli, '_recipes', lambda a: [])
    monkeypatch.setattr(cli, 'LLMClient', forbidden)
    monkeypatch.setattr(cli, '_start_bridge', forbidden)
    monkeypatch.setattr(cli.copywriter, 'generate_message', forbidden)
    monkeypatch.setattr(cli.api, 'publish', forbidden)
    args = SimpleNamespace(provider=None, cdp_url=None, tier='auto', only='wordpress',
                           force=True, mode='auto', dry_run=False, fill_only=True,
                           evidence_dir=str(tmp_path / 'no-receipts'), drafts=str(tmp_path / 'drafts'))
    assert cli.cmd_distribute(args) == 0
    assert '[preview]' in capsys.readouterr().out
    check = Store(tmp_path / 'fixture.db', product_url=URL)
    assert check.all_submissions() == before
    assert not (tmp_path / 'no-receipts').exists()
    check.close()


def test_timeout_prevents_www_and_case_alias_replay_before_any_HTTP(monkeypatch, tmp_path):
    p, s = setup(tmp_path)
    calls = transport(monkeypatch, [Response(d.LISTINGS, body={'ok': True, 'listings': []}),
                                    d.requests.Timeout('offline ambiguous result')])
    assert d.submit_curlship(p, s, tmp_path / 'first')['status'] == 'unverified'
    original_rows = [tuple(r) for r in s.conn.execute('SELECT product_key,directory,status FROM submissions')]
    s.close()
    for url in ['https://www.acme.example/', 'HTTPS://ACME.EXAMPLE/', 'https://WWW.ACME.EXAMPLE/']:
        alias = Store(tmp_path / 'fixture.db', product_url=url)
        product = Product(name='Same Acme', url=url, submitter_email=EMAIL)
        assert d.submit_curlship(product, alias, tmp_path / url.split('//')[1].rstrip('/'))['status'] == 'skipped'
        assert [tuple(r) for r in alias.conn.execute('SELECT product_key,directory,status FROM submissions')] == original_rows
        alias.close()
    assert len(calls) == 2  # one original GET+POST; aliases must not even recheck the index


def test_concurrent_aliases_both_preflight_but_only_one_atomic_POST(monkeypatch, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock
    database = tmp_path / 'window.db'
    initial = Store(database, product_url=URL)
    initial.close()
    rendezvous, lock, calls = Barrier(2), Lock(), []
    def request(method, url, payload=None):
        with lock:
            calls.append((method, url, payload))
        if method == 'GET':
            rendezvous.wait(timeout=5)
            return Response(d.LISTINGS, body={'ok': True, 'listings': []})
        raise d.requests.Timeout('offline ambiguous result')
    monkeypatch.setattr(d, '_request', request)
    def run(index, url):
        store = Store(database, product_url=url)
        try:
            return d.submit_curlship(Product(name='Same Acme', url=url, submitter_email=EMAIL),
                                     store, tmp_path / ('separate-receipts-' + str(index)))['status']
        finally:
            store.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, i, u) for i, u in enumerate([URL, 'https://WWW.ACME.EXAMPLE/'])]
        statuses = [f.result(timeout=10) for f in futures]
    assert sorted(statuses) == ['skipped', 'unverified']
    assert len([c for c in calls if c[0] == 'GET']) == 2
    assert len([c for c in calls if c[0] == 'POST']) == 1
    check = Store(database, product_url=URL)
    assert check.conn.execute('SELECT COUNT(*) FROM submissions').fetchone()[0] == 1
    check.close()


def test_canonical_receipts_preserve_original_payload_keys_and_independent_domains(monkeypatch, tmp_path):
    urls = ['https://www.AcMe.example/', 'https://app.acme.example/', 'https://other.example/']
    calls, created = [], {}
    def request(method, url, payload=None):
        calls.append((method, url, payload))
        if url == d.LISTINGS:
            return Response(url, body={'ok': True, 'listings': []})
        if method == 'POST':
            item = entry(id=100 + len(created), url=payload['url'])
            created[d.LISTING + str(item['id'])] = item
            return Response(url, 201, {'ok': True, 'listing': item})
        return Response(url, body={'ok': True, 'listing': created[url]})
    monkeypatch.setattr(d, '_request', request)
    proofs = []
    for url in urls:
        product = Product(name='Independent app', url=url, submitter_email=EMAIL)
        store = Store(tmp_path / 'products.db', product_url=url)
        outcome = d.submit_curlship(product, store, tmp_path / 'receipts')
        assert outcome['status'] == 'approved'
        proof = json.loads(Path(outcome['receipt']).read_text())
        assert proof['product'] == url.rstrip('/')
        assert store.all_submissions()[0]['product_key'] == url.rstrip('/')
        assert store.all_submissions()[0]['status'] == 'approved'
        proofs.append(outcome['receipt'])
        store.close()
    assert [c[2]['url'] for c in calls if c[0] == 'POST'] == urls
    assert len(set(proofs)) == 3
    # All original approved histories still protect their own www/case aliases.
    for url in ['https://ACME.EXAMPLE/', 'https://www.app.acme.example/', 'HTTPS://WWW.OTHER.EXAMPLE/']:
        store = Store(tmp_path / 'products.db', product_url=url)
        assert d.submit_curlship(Product(name='Existing app', url=url, submitter_email=EMAIL),
                                 store, tmp_path / 'different-receipts')['status'] == 'skipped'
        store.close()
    assert len(calls) == 9


@pytest.mark.parametrize('status', ['approved', 'submitted', 'unverified'])
@pytest.mark.parametrize('check_requested', [False, True])
def test_CLI_status_directory_API_displays_scoped_history_without_reverification(monkeypatch, tmp_path, capsys, status, check_requested):
    from dirsubmit import cli
    from dirsubmit.models import Recipe
    p, s = setup(tmp_path)
    live = d.LISTING + '99'
    s.set_status(d.SLUG, 'auto', status, 'saved original receipt state', live)
    before = s.all_submissions()
    def forbidden(*a, **kw):
        pytest.fail('Local API status must not submit, recheck, generate content or start a browser')
    monkeypatch.setattr(cli, '_product', lambda a: p)
    monkeypatch.setattr(cli, '_store', lambda a: s)
    # A stale same-slug recipe must not invoke the generic HTTP checker.
    monkeypatch.setattr(cli, '_recipes', lambda a: [Recipe(slug=d.SLUG, name='Legacy CurlShip recipe')])
    monkeypatch.setattr(cli.tracker, 'check', forbidden)
    monkeypatch.setattr(cli.api, 'submit_directory', forbidden)
    monkeypatch.setattr(cli.api, 'publish', forbidden)
    monkeypatch.setattr(d, '_request', forbidden)
    monkeypatch.setattr(cli, 'LLMClient', forbidden)
    monkeypatch.setattr(cli, '_start_bridge', forbidden)
    assert cli.cmd_status(SimpleNamespace(only=d.SLUG, check=check_requested)) == 0
    output = capsys.readouterr().out
    assert sum(line.startswith(d.SLUG) for line in output.splitlines()) == 1
    assert status in output and live in output
    assert ('未请求HTTP' in output) == check_requested
    check = Store(tmp_path / 'fixture.db', product_url=URL)
    assert check.all_submissions() == before
    check.close()


def test_CLI_status_only_excludes_API_and_keeps_normal_recipe_check_behavior(monkeypatch, tmp_path, capsys):
    from dirsubmit import cli
    from dirsubmit.models import Recipe
    p, s = setup(tmp_path)
    s.set_status(d.SLUG, 'auto', 'approved', 'protected API history', d.LISTING + '99')
    s.set_status('fixture-directory', 'semi', 'submitted', 'awaiting generic review', 'https://directory.example/listing')
    curl_before = [row for row in s.all_submissions() if row['directory'] == d.SLUG]
    calls = []
    def generic(recipe, product):
        calls.append((recipe.slug, product.url))
        return 'pending', 'generic review remains pending'
    def forbidden(*a, **kw):
        pytest.fail('Filtered API status must never create or issue HTTP')
    monkeypatch.setattr(cli, '_product', lambda a: p)
    monkeypatch.setattr(cli, '_store', lambda a: s)
    monkeypatch.setattr(cli, '_recipes', lambda a: [Recipe(slug='fixture-directory', name='Fixture', tier='semi')])
    monkeypatch.setattr(cli.tracker, 'check', generic)
    monkeypatch.setattr(cli.api, 'submit_directory', forbidden)
    monkeypatch.setattr(d, '_request', forbidden)
    assert cli.cmd_status(SimpleNamespace(only='fixture-directory', check=True)) == 0
    output = capsys.readouterr().out
    assert d.SLUG not in output and 'fixture-directory' in output and 'submitted' in output
    assert calls == [('fixture-directory', URL)]
    check = Store(tmp_path / 'fixture.db', product_url=URL)
    rows = check.all_submissions()
    assert [row for row in rows if row['directory'] == d.SLUG] == curl_before
    normal = next(row for row in rows if row['directory'] == 'fixture-directory')
    assert normal['status'] == 'submitted' and normal['last_checked_at']
    assert normal['live_url'] == 'https://directory.example/listing'
    check.close()


def test_CLI_status_directory_API_does_not_display_another_product_history(monkeypatch, tmp_path, capsys):
    from dirsubmit import cli
    p, s = setup(tmp_path)
    s.set_status(d.SLUG, 'auto', 'approved', 'Acme original only', d.LISTING + '99')
    before = s.all_submissions()
    s.close()
    other_url = 'https://other.example/'
    other = Store(tmp_path / 'fixture.db', product_url=other_url)
    def forbidden(*a, **kw):
        pytest.fail('Wrong-product empty local view must not perform network actions')
    monkeypatch.setattr(cli, '_product', lambda a: Product(name='Other', url=other_url))
    monkeypatch.setattr(cli, '_store', lambda a: other)
    monkeypatch.setattr(cli, '_recipes', lambda a: [])
    monkeypatch.setattr(cli.tracker, 'check', forbidden)
    monkeypatch.setattr(cli.api, 'submit_directory', forbidden)
    monkeypatch.setattr(d, '_request', forbidden)
    assert cli.cmd_status(SimpleNamespace(only=d.SLUG, check=True)) == 0
    output = capsys.readouterr().out
    assert d.SLUG not in output and d.LISTING + '99' not in output
    check = Store(tmp_path / 'fixture.db', product_url=URL)
    assert check.all_submissions() == before
    check.close()
