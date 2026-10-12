"""Verify listing links, avoiding product-name echoes in search pages."""
from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit
import requests
from .models import Product, Recipe

_UA = {"User-Agent": "Mozilla/5.0 dirsubmit/0.1"}
_GITHUB_HOSTS = {'github.com', 'api.github.com', 'raw.githubusercontent.com'}
_PRIVATE_PREFIXES = {
    'account', 'accounts', 'dashboard', 'admin', 'auth', 'oauth',
    'login', 'signin', 'sign-in', 'signup', 'sign-up', 'register',
    'my-products', 'my-submissions', 'submit', 'submission',
    'thanks', 'thank-you', 'thank_you', 'thankyou', 'success',
    'submitted', 'submission-success', 'submission-received',
    'confirmation', 'receipt', 'checkout', 'callback',
}
_NESTED_PRIVATE_ROUTES = {
    ('user', 'signin'), ('user', 'signup'), ('user', 'login'),
    ('users', 'sign_in'), ('users', 'sign_up'), ('users', 'login'),
    ('s', 'submit'),
}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.urls.extend(value for key,value in attrs if key == 'href' and value)


def _identity(url):
    if not isinstance(url, str):
        return '', ''
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {'http', 'https'}:
            return '', ''
        return (parsed.hostname or '').lower().removeprefix('www.'), parsed.path.rstrip('/')
    except (TypeError, ValueError):
        return '', ''


def _non_listing_source(recipe, url):
    """These sources cannot prove publication, regardless of execution tier."""
    host, _ = _identity(url)
    if str(recipe.slug or '').lower().startswith('github-') or host in _GITHUB_HOSTS:
        return 'GitHub PR/仓库需单独核验合并与上游收录；页面链接不算批准'
    parts = tuple(p for p in unquote(urlsplit(url).path).lower().split('/') if p)
    if (parts and parts[0] in _PRIVATE_PREFIXES) or parts[:2] in _NESTED_PRIVATE_ROUTES:
        return '账户、登录、提交或回执页面不作为公开收录证明'
    return ''


def check(recipe: Recipe, product: Product) -> tuple[str, str]:
    config = recipe.verify or {}
    if not isinstance(config, dict):
        return 'pending', '无有效 verify 配置'
    vtype = config.get('type')
    if vtype == 'manual':
        return 'pending', '此目录配置为人工核验；未请求页面'
    if not isinstance(vtype, str) or vtype not in {'search', 'url'}:
        return 'pending', '未配置支持的公开核验类型；未请求页面'
    url = config.get('url') or recipe.homepage or ''
    if not isinstance(url, str):
        return 'pending', 'verify URL 必须是字符串；未请求页面'
    url = url.replace('{name}',quote(product.name,safe='')).replace('{url}',quote(product.url,safe=''))
    if not url:
        return 'pending','未配置 verify url'
    source_host, _ = _identity(url)
    official_host, _ = _identity(recipe.homepage or url)
    target = _identity(product.url)
    if not source_host or not official_host or not target[0]:
        return 'pending', '核验来源或产品不是有效 HTTP(S) URL'
    if source_host != official_host:
        return 'pending', '核验 URL 不属于预期官方目录域名；未请求页面'
    source_note = _non_listing_source(recipe, url)
    if source_note:
        return 'pending', source_note
    try:
        response = requests.get(url,headers=_UA,timeout=20,allow_redirects=True)
        if not 200 <= response.status_code < 300:
            return 'pending',f'HTTP {response.status_code}'
        final_url = getattr(response, 'url', '')
        final_identity = _identity(final_url)
        if final_identity[0] != official_host:
            return 'pending', '最终页面不属于预期官方目录域名；不能证明收录'
        source_note = _non_listing_source(recipe, final_url)
        if source_note:
            return 'pending', source_note
        if final_identity == target:
            return 'pending', '最终页面是产品自身地址；不能证明目录收录'
        links = Links(); links.feed(response.text)
        for link in links.urls:
            try:
                linked_identity = _identity(urljoin(final_url, link))
            except ValueError:
                continue
            if linked_identity == target:
                return 'approved',f'已发现公开目录中的产品链接（{final_url}）'
        return 'pending','未找到产品链接，可能仍在审核中；仅产品名出现不算收录'
    except requests.RequestException as exc:
        return 'pending',f'抓取失败：{exc}'
