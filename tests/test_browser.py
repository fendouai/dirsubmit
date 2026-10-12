"""Real Chromium end-to-end tests against a local directory fixture."""
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from dirsubmit.engine import _run_playwright
from dirsubmit.models import FieldSpec, Recipe


@pytest.fixture
def directory():
    state = {'posts': 0}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            name = '' if self.path == '/missing' else '<input required name="name">'
            confirm = self.path != '/uncertain'
            html = f'''<form>{name}<textarea name="description"></textarea>
            <button type="submit">Submit</button></form><div id="result"></div>
            <script>document.querySelector('form').onsubmit=async(e)=>{{e.preventDefault();
            await fetch('/submitted',{{method:'POST'}});
            {'document.querySelector("#result").textContent="Awaiting review";' if confirm else ''}
            }};</script>'''
            self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers()
            self.wfile.write(html.encode())
        def do_POST(self):
            state['posts'] += 1
            self.send_response(200); self.end_headers(); self.wfile.write(b'OK')
    server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    yield f'http://127.0.0.1:{server.server_port}',state
    server.shutdown(); server.server_close(); thread.join()


def run_case(directory,tmp_path,path,fill_only=False):
    url,state = directory
    recipe = Recipe('fixture','Fixture',submit_url=url+path,tier='auto',submit_selector='button',
                    success={'text':'Awaiting review'},fields=[FieldSpec('name',required=True), FieldSpec('description',type='textarea')])
    result = _run_playwright(recipe,{'name':'Acme','description':'Public product'},None,fill_only,tmp_path,timeout=1)
    assert list(tmp_path.glob('*/page.png'))
    return result,state


def test_real_browser_missing_required_never_submits(directory,tmp_path):
    result,state=run_case(directory,tmp_path,'/missing')
    assert result[0]=='blocked'; assert state['posts']==0


def test_real_browser_confirms_single_submission(directory,tmp_path):
    result,state=run_case(directory,tmp_path,'/form')
    assert result[0]=='submitted'; assert state['posts']==1


def test_real_browser_uncertain_never_retries(directory,tmp_path):
    result,state=run_case(directory,tmp_path,'/uncertain')
    assert result[0]=='unverified'; assert state['posts']==1


def test_real_browser_fill_only(directory,tmp_path):
    result,state=run_case(directory,tmp_path,'/form',True)
    assert result[0]=='filled'; assert state['posts']==0


def test_read_only_scout_discovers_form_without_submitting(directory):
    from dirsubmit.scout import discover
    url,state=directory
    snapshot=discover(url+'/form')
    assert snapshot['frames'][0]['fields'][0]['name']=='name'
    assert snapshot['frames'][0]['google_button_visible'] is False
    assert state['posts']==0
