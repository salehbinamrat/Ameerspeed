"""Runtime verification of high-priority fixes. Browser/RouterOS simulator, not live router."""
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import json, shutil, os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
URL='https://portal.ameer.invalid'

def content_type(path):
    return 'application/javascript' if path.endswith('.js') else 'text/css' if path.endswith('.css') else 'text/html' if path.endswith('.html') else 'image/webp' if path.endswith('.webp') else 'image/png' if path.endswith('.png') else 'font/woff2'

def run(p,mode,username='123456',status_username='123456',speed='hotspot'):
    chrome=os.getenv('PLAYWRIGHT_CHROMIUM_PATH') or shutil.which('chromium')
    kwargs={'headless':True,'args':['--no-sandbox']}
    if chrome:kwargs['executable_path']=chrome
    browser=p.chromium.launch(**kwargs)
    ctx=browser.new_context(viewport={'width':320,'height':568})
    events=[]
    state={'logged':False,'statusName':status_username}
    def fulfill(route):
        req=route.request;u=urlsplit(req.url);path=u.path
        if path=='/login' and u.query=='var=callBack':
            if req.method=='POST':
                fields=parse_qs(req.post_data or '')
                events.append(('login',fields))
                state['logged']=True
                return route.fulfill(status=200,content_type='application/json',body=json.dumps({'action':'onLoggedIn','logged_in':'yes'}))
            return route.fulfill(status=200,content_type='application/json',body=json.dumps({'action':'onLoginStart','logged_in':'no'}))
        if path=='/status' and u.query=='var=callBack':
            events.append(('status',{}))
            return route.fulfill(status=200,content_type='application/json',body=json.dumps({'action':'onStatusQuery','logged_in':'yes' if state['logged'] else 'no','username':state['statusName'],'remain_bytes_total':'---','session_time_left':'1w2d','uptime':'1h'}))
        if path=='/logout':
            events.append(('logout',u.query))
            state['logged']=False
            return route.fulfill(status=200,content_type='application/json',body=json.dumps({'action':'onLoggedOut','logged_in':'no'}))
        if path.startswith('/najm-speed.gif'):
            return route.fulfill(status=404,body='pulse')
        if path in ('','/','/index.html'):
            path='/index.html'
        local=ROOT/path.lstrip('/')
        if local.is_file():return route.fulfill(status=200,content_type=content_type(path),body=local.read_bytes())
        return route.fulfill(status=404,body='not found')
    ctx.route('**/*',fulfill)
    page=ctx.new_page()
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.evaluate("""() => {
      var stored={};
      Object.defineProperty(window,'localStorage',{configurable:true,value:{
         getItem:function(k){return Object.prototype.hasOwnProperty.call(stored,k)?stored[k]:null;},
         setItem:function(k,v){stored[k]=String(v);},
         removeItem:function(k){delete stored[k];}
      }});
      var cookies={};
      Object.defineProperty(document,'cookie',{configurable:true,
        get:function(){return Object.keys(cookies).map(function(k){return k+'='+cookies[k];}).join('; ');},
        set:function(s){var p=s.split(';')[0].split('='); if(s.indexOf('1970')!==-1) delete cookies[p[0]]; else cookies[p[0]]=p.slice(1).join('=');}
      });
    }""")
    html=(ROOT/'index.html').read_text('utf-8').replace('<head>','<head><base href="'+URL+'/">')
    page.set_content(html,wait_until='load')
    page.locator('input[name=username]').fill(username)
    page.locator('input[name=speed-choice][value="%s"]'%speed).check(force=True)
    page.locator('button.login-submit').click()
    page.locator('#status.active').wait_for(timeout=8000)
    assert page.locator('#username').inner_text()==status_username.replace('%2B','+'),(mode,page.locator('#username').inner_text())
    assert 'أسبوع' in page.locator('#session_time_left').inner_text(),mode
    assert 'غير محدود' in page.locator('#remain_bytes_total').inner_text(),mode
    if mode=='foreign':
        assert 'مختلف' in page.locator('#status .title').inner_text(),page.locator('#status .title').inner_text()
        assert '123456' not in [x['user'] for x in page.evaluate('JSON.parse(localStorage.getItem("alameer_verified_card_routes_v1")||"[]")')]
        assert not page.evaluate('document.cookie.includes("username=123456")')
    else:
        assert 'نجاح' in page.locator('#status .title').inner_text()
        assert page.evaluate('JSON.parse(localStorage.getItem("alameer_verified_card_routes_v1")||"[]")')
        assert page.locator('#speedSignalNotice').inner_text() if speed!='hotspot' else True
        if mode=='stored':
            assert page.evaluate('JSON.parse(localStorage.getItem("alameer_verified_card_routes_v1")||"[]")[0].speed')==speed
            # Simulate reopening the portal in a fresh tab with no sessionStorage.
            page.evaluate('try{sessionStorage.clear()}catch(e){}; showLoginBusy(false); cookieLogin()')
            page.wait_for_timeout(950)
            posts=[ev[1] for ev in events if ev[0]=='login']
            assert len(posts)==2 and posts[-1].get('domain')==[speed],posts
            # Legacy cookie without a verified mapping must never silently use hotspot.
            page.evaluate('localStorage.removeItem("alameer_verified_card_routes_v1"); showLoginBusy(false); cookieLogin()')
            page.wait_for_timeout(80)
            assert len([ev for ev in events if ev[0]=='login'])==2,events
            # Restore verified record for the following privacy test.
            page.evaluate('storeConfirmedCardSpeed("123456","najm-speed-10m")')
            page.locator('.logout-submit').click()
            page.wait_for_timeout(100)
            assert any('erase-cookie=on' in v for name,v in events if name=='logout'),events
            page.locator('.lt1.pc2').click()
            page.once('dialog',lambda d:d.accept())
            page.locator('#clearSavedCardsBtn').click()
            assert page.evaluate('localStorage.getItem("alameer_verified_card_routes_v1")') is None
            assert page.locator('#previousCardsEmpty').is_visible()
    assert not errors, errors
    print('PASS high priority browser',mode,[(e[0]) for e in events])
    browser.close()

with sync_playwright() as p:
    run(p,'foreign',username='123456',status_username='987654')
    run(p,'correct',username='123+45',status_username='123%2B45')
    run(p,'stored',username='123456',status_username='123456',speed='najm-speed-10m')
