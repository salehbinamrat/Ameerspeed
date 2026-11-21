"""Check login success/rejection using a fake RouterOS XHR endpoint, not a live router."""
import os,re,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_text()
html=re.sub(r'<script[^>]*src=[^>]*></script>','',html)
html=re.sub(r'<script>.*?</script>','',html,flags=re.S)
html=re.sub(r'<link href="css/portal\.css(?:\?[^"]+)?" rel="stylesheet"\s*/>', lambda _: '<style>'+(ROOT/'css/portal.css').read_text()+'</style>', html)
with sync_playwright() as p:
    chrome=os.getenv('PLAYWRIGHT_CHROMIUM_PATH') or shutil.which('chromium')
    opts={'args':['--no-sandbox'],'headless':True}
    if chrome:opts['executable_path']=chrome
    browser=p.chromium.launch(**opts)
    for scenario in ('success','not_found'):
        page=browser.new_page(viewport={'width':320,'height':568})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html)
        page.evaluate('''(scenario) => {
            let cookieText='';
            Object.defineProperty(document,'cookie',{configurable:true,get(){return cookieText;},set(v){cookieText=v;}});
            class FakeXHR {
                constructor(){this.readyState=0;this.status=0;this.responseText='';}
                open(method,url){this.url=url;this.method=method;}
                send(){
                   let r={action:'onLoginStart',logged_in:'no'};
                   if(this.method==='POST' && this.url==='/login?var=callBack'){
                     r = scenario==='success' ? {action:'onLoggedIn',logged_in:'yes',username:'123456'} : {action:'onLoginError',error_orig:'user not found',logged_in:'no'};
                   }else if(this.url.indexOf('/status?')===0){
                     r={action:'onStatusQuery',logged_in:'yes',username:'123456',remain_bytes_total:'2048',session_time_left:'1h',uptime:'3m'};
                   }
                   this.status=200;this.responseText=JSON.stringify(r);this.readyState=4;
                   if(this.onreadystatechange)this.onreadystatechange();
                }
                setRequestHeader(){}
                abort(){}
            }
            window.XMLHttpRequest=FakeXHR;
        }''',scenario)
        for f in ('hotInImprover.min.js','hotCookie.min.js','hotBlocker.min.js','main.min.js'):
            page.add_script_tag(content=(ROOT/'js'/f).read_text())
        page.evaluate('document.dispatchEvent(new Event("DOMContentLoaded"))')
        page.locator('input[name=username]').fill('123456')
        page.locator('button.login-submit').click()
        if scenario=='success':
            assert page.locator('#status.active').count()==1,'Expected logged-in view'
            assert page.locator('#login.inactive').count()==1,'Expected login page hidden'
        else:
            assert page.locator('#login').is_visible(),'Login should remain available after error'
            assert page.locator('#error').text_content()=='الكرت خطأ، حاول بكرت آخر',page.locator('#error').text_content()
            assert page.locator('button.login-submit').is_enabled(),'Retry must remain possible'
        assert not errors,errors
        print('PASS router response simulation:',scenario)
        page.close()
    browser.close()
