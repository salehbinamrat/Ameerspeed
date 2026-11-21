"""Synthetic RouterOS v6 CHAP/PAP handshake regression.

This test verifies the actual page scripts in Chromium, with local fake RouterOS
responses. It does NOT replace a real HotSpot authentication test.
"""
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import hashlib
import shutil
import os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://portal.ameer.invalid'


def simulate(browser, kind):
    context = browser.new_context(viewport={'width': 320, 'height': 568})
    page = context.new_page()
    errs = []
    received = []
    page.on('pageerror', lambda error: errs.append(str(error)))
    expected = hashlib.md5(bytes([0xf9, 0xef, 0x0d, 0xd8, 0x0b])).hexdigest()

    def fulfill(route):
        req = route.request
        target = urlsplit(req.url)
        name = target.path
        query = parse_qs(target.query)
        if name == '/login' and query.get('var') == ['chapdata']:
            if kind == 'chap':
                return route.fulfill(status=200, content_type='text/plain',
                                     body='AMEER_CHAP_V1\nCHAP\n\\371\n\\357\\015\\330\\013\n')
            if kind == 'pap':
                return route.fulfill(status=200, content_type='text/plain',
                                     body='AMEER_CHAP_V1\nPAP\n')
            return route.fulfill(status=200, content_type='text/html',body='<html>stale RouterOS template</html>')
        if name == '/login' and query.get('var') == ['callBack']:
            if req.method == 'POST':
                params = parse_qs(req.post_data or '', keep_blank_values=True)
                received.append(params)
                return route.fulfill(status=200,content_type='application/json',body='{"logged_in":"yes","action":"onLoggedIn"}')
            return route.fulfill(status=200,content_type='application/json',body='{"logged_in":"no","action":"onLoginStart"}')
        if name == '/status' and query.get('var') == ['callBack']:
            return route.fulfill(status=200,content_type='application/json',body='{"logged_in":"yes","action":"onStatusQuery","username":"202020","remain_bytes_total":"---","uptime":"1m"}')
        if name in ('','/','/index.html'):
            name = '/index.html'
        local = ROOT / name.lstrip('/')
        if local.is_file():
            mime = 'application/javascript' if name.endswith('.js') else 'text/css' if name.endswith('.css') else 'text/html'
            return route.fulfill(status=200,content_type=mime,body=local.read_bytes())
        return route.fulfill(status=404,body='not found')

    context.route('**/*', fulfill)
    html = (ROOT/'index.html').read_text('utf8').replace('<head>','<head><base href="'+BASE+'/">')
    page.set_content(html,wait_until='load')
    page.locator('input[name=username]').fill('202020')
    page.locator('button.login-submit').click()
    if kind == 'bad':
        page.locator('#alternateLoginBtn:not([hidden])').wait_for(timeout=8000)
        assert not received, 'Never submit a card before identifying authentication method'
        page.wait_for_function("document.getElementById('error').textContent.indexOf('الدخول البديل') !== -1", timeout=4000)
        assert page.locator('button.login-submit').is_enabled()
    else:
        page.locator('#status.active').wait_for(timeout=8000)
        assert len(received) == 1, received
        assert received[0]['username'] == ['202020']
        if kind == 'chap':
            assert received[0]['password'] == [expected], received
        elif kind == 'pap':
            assert 'password' not in received[0],received
    assert not errs,errs
    print('PASS RouterOS challenge browser',kind)
    context.close()


with sync_playwright() as p:
    chrome=os.getenv('PLAYWRIGHT_CHROMIUM_PATH') or shutil.which('chromium')
    opts={'headless':True,'args':['--no-sandbox']}
    if chrome: opts['executable_path']=chrome
    browser=p.chromium.launch(**opts)
    for kind in ['chap','pap','bad']:
        simulate(browser,kind)
    browser.close()
