"""Full-page JS/CSS regression with mocked MikroTik paths. No external or router traffic."""
import json
import os
import shutil
import urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
EVENTS=[]
STATUS={'logged_in':False}

def content_type(path):
    if path.endswith('.css'):return 'text/css'
    if path.endswith('.js'):return 'application/javascript'
    if path.endswith('.woff') or path.endswith('.woff2'):return 'font/woff2'
    if path.endswith('.webp'):return 'image/webp'
    if path.endswith('.png'):return 'image/png'
    return 'text/html; charset=utf-8'

def intercept(route):
    request=route.request
    uri=urllib.parse.urlsplit(request.url)
    path=uri.path
    headers={'access-control-allow-origin':'*','access-control-allow-headers':'content-type','access-control-allow-methods':'POST,GET,OPTIONS'}
    if request.method=='OPTIONS':return route.fulfill(status=204,headers=headers,body='')
    if path in ('/login','/status','/logout'):
        EVENTS.append((request.method,path,request.post_data or ''))
        if path=='/login' and 'var=chapdata' in uri.query:
            return route.fulfill(status=200,body='AMEER_CHAP_V1\nPAP\n',content_type='text/plain',headers=headers)
        if path=='/login' and 'var=native' in uri.query:
            source=(ROOT/'login.html').read_text('utf-8')
            body=source.split('$(if var == "native")',1)[1].split('$(if chap-id)',1)[0]
            body+='<script>function submitCompatibleLogin(){return true;}</script></body></html>'
            return route.fulfill(status=200,body=body,content_type='text/html',headers=headers)
        if path=='/login' and request.method=='POST':
            fields=urllib.parse.parse_qs(request.post_data or '')
            STATUS['logged_in']=fields.get('username')==['123456']
            data={'action':'onLoggedIn','logged_in':'yes'} if STATUS['logged_in'] else {'action':'onLoginError','logged_in':'no','error_orig':'user not found'}
        elif path=='/login':data={'action':'onLoginStart','logged_in':'no'}
        elif path=='/status':data={'action':'onStatusQuery','logged_in':'yes' if STATUS['logged_in'] else 'no','username':'123456','uptime':'5m','session_time_left':'2h'}
        else:data={'action':'onLoggedOut','logged_in':'no'}
        return route.fulfill(status=200,body=json.dumps(data),content_type='application/json',headers=headers)
    local=(ROOT/path.lstrip('/'))
    if not local.is_file():return route.fulfill(status=404,body='missing',headers=headers)
    return route.fulfill(status=200,body=local.read_bytes(),content_type=content_type(path),headers=headers)

with sync_playwright() as p:
    chrome=os.getenv('PLAYWRIGHT_CHROMIUM_PATH') or shutil.which('chromium')
    opts={'headless':True,'args':['--no-sandbox']}
    if chrome:opts['executable_path']=chrome
    browser=p.chromium.launch(**opts)
    page=browser.new_page(viewport={'width':320,'height':568})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/*',intercept)
    page.evaluate("""window.__signals=[]; window.Image=function(){Object.defineProperty(this,'src',{set:function(v){window.__signals.push(v)}})};""")
    html=(ROOT/'index.html').read_text('utf-8').replace('<head>','<head><base href="https://portal.example.invalid/">')
    page.set_content(html,wait_until='load')
    page.locator('input[name="username"]').fill('123456')
    page.locator('input[value="najm-speed-10m"]').check(force=True)
    page.locator('.login-submit').click()
    page.locator('#status.active').wait_for(timeout=7000)
    page.wait_for_timeout(800)
    posts=[item for item in EVENTS if item[0]=='POST' and item[1]=='/login']
    assert len(posts)==1,posts
    assert 'username=123456' in posts[0][2],posts
    assert len(page.evaluate('window.__signals'))==3,'Duplicate speed signals'
    assert not errors,errors
    page.close()
    browser.close()
print('PASS full page: original scripts, speed choice, POST, status, no JS runtime errors')
