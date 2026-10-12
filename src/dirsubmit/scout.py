"""Read-only form discovery; observed Google buttons aren't proof of working OAuth."""
from __future__ import annotations

SNAPSHOT_JS = r"""() => {
 const visible = e => !!e.getClientRects().length;
 return {
   url: location.href, title: document.title,
   fields: [...document.querySelectorAll('input,textarea,select,[contenteditable=true]')]
    .filter(e => visible(e) && e.type !== 'password' && e.type !== 'hidden')
    .map(e => ({name:e.name || '', id:e.id || '', type:e.type || e.tagName.toLowerCase(),
      label:e.labels?.[0]?.innerText || e.getAttribute('aria-label') || '',
      placeholder:e.getAttribute('placeholder') || '', required:e.required || false,
      options:e.tagName === 'SELECT' ? [...e.options].map(o=>({value:o.value,label:o.label})) : []})),
   links: [...document.querySelectorAll('a,button,[role=button]')].filter(visible)
    .map(e => ({text:(e.innerText || e.getAttribute('aria-label') || '').trim(),url:e.href || ''}))
    .filter(e => /submit|add.{0,15}(tool|product|site)|list your|google|sign in|log in/i.test(e.text)).slice(0,60),
   google_button_visible: [...document.querySelectorAll('a,button,[role=button]')]
    .some(e=>visible(e) && /google/i.test(e.innerText || e.getAttribute('aria-label') || '')),
   warning:'Google button visibility does not prove login or submission works.'
 };
}"""


def discover(url, cdp_url=None):
    from playwright.sync_api import sync_playwright
    from .engine import _launch_browser
    with sync_playwright() as p:
        browser = _launch_browser(p, cdp_url)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return {"url": page.url, "frames": [frame.evaluate(SNAPSHOT_JS) for frame in page.frames]}
        finally:
            if not cdp_url:
                browser.close()
