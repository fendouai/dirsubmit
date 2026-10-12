import json
import sqlite3
from dirsubmit import engine
from dirsubmit.automation import task_payload, validate_result
from dirsubmit.cli import build_parser, cmd_resume
from dirsubmit.models import Copy, FieldSpec, Product, Recipe
from dirsubmit.store import Store


def test_products_do_not_share_copies_or_status(tmp_path):
    a = Store(tmp_path / 'db', 'https://a.test/')
    b = Store(tmp_path / 'db', 'https://b.test')
    a.upsert_copy(Copy('x', tagline='A'))
    a.set_status('x', 'semi', 'submitted', 'confirmed')
    assert b.get_copy('x') is None
    assert b.get_status('x') is None
    b.upsert_copy(Copy('x', tagline='B'))
    assert a.get_copy('x').tagline == 'A'
    b.set_status('x', 'semi', 'blocked')
    assert b.all_submissions()[0]['submitted_at'] is None
    a.close(); b.close()


def test_legacy_database_migration_preserves_records(tmp_path):
    db = tmp_path / 'db'
    c = sqlite3.connect(db)
    c.execute('CREATE TABLE submissions (directory TEXT PRIMARY KEY,tier TEXT,status TEXT,submitted_at TEXT,last_checked_at TEXT,live_url TEXT,note TEXT)')
    c.execute("INSERT INTO submissions VALUES ('x','auto','submitted','y',NULL,'','old')")
    c.commit(); c.close()
    s = Store(db)
    assert s.get_status('x') == 'submitted'
    assert s.all_submissions()[0]['note'] == 'old'
    s.close()


def test_missing_required_data_never_runs_browser(monkeypatch):
    r = Recipe('x','X',tier='auto',fields=[FieldSpec('email',required=True,source='email')])
    monkeypatch.setattr(engine, '_run_playwright', lambda *a: (_ for _ in ()).throw(AssertionError()))
    assert engine.submit(r,Product('A','https://a.test'),Copy('x'))[0] == 'blocked'


def test_computer_use_task_and_resume_bound_to_product(tmp_path):
    r = Recipe('x','X',tier='semi')
    p = Product('A','https://a.test')
    status, note = engine.submit(r,p,Copy('x'),mode='computer-use',evidence_dir=tmp_path)
    assert status == 'needs_handoff'
    task_path = next(tmp_path.glob('*.json'))
    task = json.loads(task_path.read_text())
    result = dict(task_id=task['id'], product_url=p.url, directory='x',status='submitted',evidence_text='Your product is awaiting review')
    result_path = tmp_path / 'result.json'; result_path.write_text(json.dumps(result))
    args = build_parser().parse_args(['--db',str(tmp_path/'db'),'resume','--task',str(task_path),'--result',str(result_path)])
    assert cmd_resume(args) == 0
    s = Store(tmp_path/'db',p.url); assert s.get_status('x') == 'submitted'; s.close()
    result['product_url'] = 'https://b.test'; result_path.write_text(json.dumps(result))
    assert cmd_resume(args) == 1


def test_claim_without_evidence_is_not_success():
    assert validate_result({'status':'submitted'})[0] == 'unverified'
    assert validate_result({'status':'submitted','evidence_text':'OK'}, fill_only=True)[0] == 'unverified'


class Bridge:
    def __init__(self, missing=False, confirmed=False):
        self.calls = []; self.missing = missing; self.confirmed = confirmed
    def connected(self): return True
    def call(self, cmd, **kw):
        self.calls.append(cmd)
        if cmd == 'fill' and self.missing: return {'status':'error'}
        return {'status':'ok','result':{'confirmed':self.confirmed}}


def test_extension_missing_required_does_not_click():
    r = Recipe('x','X',tier='semi',submit_selector='button',fields=[FieldSpec('name',required=True,source='name')])
    b = Bridge(missing=True)
    assert engine.submit(r,Product('A','https://a.test'),Copy('x'),mode='extension',bridge=b)[0] == 'blocked'
    assert 'click' not in b.calls


def test_extension_click_is_unverified_without_confirmation():
    b=Bridge(); r=Recipe('x','X',tier='auto',submit_selector='button')
    assert engine.submit(r,Product('A','https://a.test'),Copy('x'),mode='extension',bridge=b)[0] == 'unverified'
    assert b.calls.count('click') == 1


def test_required_file_extension_does_not_submit(tmp_path):
    b=Bridge(); r=Recipe('x','X',tier='semi',submit_selector='button',fields=[FieldSpec('logo',type='file',required=True,file_path='/tmp/logo.png')])
    assert engine.submit(r,Product('A','https://a.test'),Copy('x'),mode='extension',bridge=b)[0] == 'blocked'
    assert 'click' not in b.calls


def test_fill_only_never_clicks():
    b=Bridge(); r=Recipe('x','X',tier='semi',submit_selector='button')
    assert engine.submit(r,Product('A','https://a.test'),Copy('x'),mode='extension',bridge=b,fill_only=True)[0] == 'filled'
    assert 'click' not in b.calls


def test_auth_required_auto_tier_never_uses_headless(monkeypatch):
    monkeypatch.setattr(engine,'cdp_available',lambda u:False)
    assert engine.resolve_mode(Recipe('x','X',tier='auto',requires_auth=True),None,'x')[0] is None


def test_computer_executor_protocol(tmp_path):
    import sys
    from dirsubmit.automation import run_computer_use
    script=tmp_path/'executor.py'
    script.write_text('import json,sys\np=json.load(sys.stdin)\nprint(json.dumps(dict(task_id=p["id"],product_url=p["product_url"],directory=p["directory"],status="submitted",evidence_text="Awaiting review")))')
    payload=task_payload(Recipe('x','X'),Product('A','https://a.test'),Copy('x'))
    import shlex
    assert run_computer_use(payload,shlex.join([sys.executable,str(script)]))[0]=='submitted'


def test_extension_login_gate_never_clicks():
    class LoginBridge(Bridge):
        def call(self,cmd,**kw):
            self.calls.append(cmd)
            return {'status':'ok','result':{'found':True}}
    b=LoginBridge()
    r=Recipe('x','X',tier='semi',auth={'login_required_selector':'a.google'},submit_selector='button')
    assert engine.submit(r,Product('A','https://a.test'),Copy('x'),mode='extension',bridge=b)[0]=='needs_auth'
    assert 'click' not in b.calls


def test_tracker_search_echo_is_not_a_listing(monkeypatch):
    from dirsubmit import tracker
    class Response:
        status_code = 200
        text = '<h1>Search results for Acme Tool</h1>'
        url = 'https://directory.test/search?q=Acme%20Tool'
    monkeypatch.setattr(tracker.requests,'get',lambda *a,**kw:Response())
    recipe = Recipe('x','X',homepage='https://directory.test',
                    verify={'type': 'search', 'url': 'https://directory.test/search?q={name}'})
    assert tracker.check(recipe,Product('Acme Tool','https://acme.test'))[0]=='pending'


def test_tracker_note_is_not_saved_as_url(tmp_path):
    s=Store(tmp_path/'db','https://a.test')
    s.set_status('x','semi','submitted',live_url='https://directory.test/x')
    s.update_checked('x','pending',note='Waiting for review')
    row=s.all_submissions()[0]
    assert row['live_url']=='https://directory.test/x'; assert row['note']=='Waiting for review'
    s.close()


def test_dry_run_does_not_touch_browser_or_status(tmp_path,monkeypatch):
    import yaml
    from dirsubmit.cli import cmd_submit
    product=tmp_path/'product.yaml'
    product.write_text(yaml.safe_dump({'name':'A','url':'https://a.test'}))
    recipe_dir=tmp_path/'recipes';recipe_dir.mkdir()
    (recipe_dir/'x.json').write_text(json.dumps({'name':'X','tier':'auto','fields':[]}))
    db=tmp_path/'db';s=Store(db,'https://a.test');s.upsert_copy(Copy('x'));s.set_status('x','auto','submitted','original');s.close()
    monkeypatch.setattr(engine,'_run_playwright',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('browser opened')))
    args=build_parser().parse_args(['--product',str(product),'--recipes',str(recipe_dir),'--db',str(db),'submit','--dry-run','--force'])
    assert cmd_submit(args)==0
    s=Store(db,'https://a.test');assert s.get_status('x')=='submitted'; assert s.all_submissions()[0]['note']=='original';s.close()


def test_invalid_agent_result_does_not_crash():
    assert validate_result([])[0]=='unverified'
    assert validate_result({'status':'submitted','evidence_text':None})[0]=='unverified'


def test_legacy_confirmation_text_alone_cannot_mark_resume_submitted(tmp_path):
    recipe = Recipe('x', 'X', submit_url='https://directory.test/submit',
                    success={'text': 'Awaiting review'})
    payload = task_payload(recipe, Product('A', 'https://a.test'), Copy('x'))
    task_path = tmp_path / 'task.json'
    task_path.write_text(json.dumps(payload))
    result = dict(task_id=payload['id'], product_url=payload['product_url'],
                  directory='x', status='submitted', evidence_text='Awaiting review')
    result_path = tmp_path / 'result.json'
    result_path.write_text(json.dumps(result))
    args = build_parser().parse_args(['--db', str(tmp_path / 'db'), 'resume',
                                     '--task', str(task_path), '--result', str(result_path)])
    # The result import succeeds, but the claimed submission must stay unverified.
    assert cmd_resume(args) == 0
    store = Store(tmp_path / 'db', payload['product_url'])
    assert store.get_status('x') == 'unverified'
    store.close()


def test_legacy_success_rejects_preexisting_receipt_and_repeated_clicks():
    from copy import deepcopy
    payload = task_payload(Recipe('x', 'X', submit_url='https://directory.test/submit',
                                 success={'text': 'Awaiting review'}),
                           Product('A', 'https://a.test'), Copy('x'))
    after = {'url': payload['submit_url'], 'elements': [
        {'selector': 'body', 'count': 1, 'visible': True, 'text': 'Awaiting review'}]}
    result = dict(task_id=payload['id'], product_url=payload['product_url'], directory='x',
                  status='submitted', evidence_text='Awaiting review',
                  confirmation={'before': deepcopy(after), 'after': after, 'submit_click_count': 1})
    assert validate_result(result, payload=payload)[0] == 'unverified'
    result['confirmation']['before']['elements'][0]['text'] = 'Submit your product'
    assert validate_result(result, payload=payload)[0] == 'submitted'
    for click_count in (0, 2, True):
        result['confirmation']['submit_click_count'] = click_count
        assert validate_result(result, payload=payload)[0] == 'unverified'


def test_legacy_success_keeps_or_rules_with_actual_after_observations():
    for success, after in [
        ({'text': 'Awaiting review', 'selector': '#absent'},
         {'url': 'https://directory.test/submit', 'elements': [
             {'selector': 'body', 'count': 1, 'visible': True, 'text': 'Awaiting review'}]}),
        ({'selector': '#receipt'},
         {'url': 'https://directory.test/submit', 'elements': [
             {'selector': '#receipt', 'count': 1, 'visible': True, 'text': 'Queued'}]}),
        ({'url_contains': '/thanks'},
         {'url': 'https://directory.test/thanks', 'elements': []}),
    ]:
        payload = task_payload(Recipe('x', 'X', submit_url='https://directory.test/submit',
                                     success=success), Product('A', 'https://a.test'), Copy('x'))
        result = dict(task_id=payload['id'], product_url=payload['product_url'], directory='x',
                      status='submitted', evidence_text='Queued', confirmation={
                          'before': {'url': payload['submit_url'], 'elements': []},
                          'after': after, 'submit_click_count': 1})
        assert validate_result(result, payload=payload)[0] == 'submitted'
        result['confirmation']['after'] = result['confirmation']['before']
        assert validate_result(result, payload=payload)[0] == 'unverified'


def test_invalid_page_observations_cannot_prove_absence_before_submission():
    from copy import deepcopy
    payload = task_payload(Recipe('x', 'X', submit_url='https://directory.test/submit',
                                 success={'url_contains': '/thanks'}),
                           Product('A', 'https://a.test'), Copy('x'))
    valid = dict(task_id=payload['id'], product_url=payload['product_url'], directory='x',
                 status='submitted', evidence_text='Queued', confirmation={
                     'before': {'url': payload['submit_url'], 'elements': []},
                     'after': {'url': 'https://directory.test/thanks', 'elements': []},
                     'submit_click_count': 1})
    assert validate_result(valid, payload=payload)[0] == 'submitted'
    malformed = ('not observed', None, [{}], [
        {'selector': 'body', 'count': True, 'visible': False, 'text': ''}])
    for page in ('before', 'after'):
        for elements in malformed:
            result = deepcopy(valid)
            result['confirmation'][page]['elements'] = elements
            assert validate_result(result, payload=payload)[0] == 'unverified'
        result = deepcopy(valid)
        del result['confirmation'][page]['elements']
        assert validate_result(result, payload=payload)[0] == 'unverified'
