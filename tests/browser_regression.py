"""Chromium DOM layout checks (no network, no RouterOS) using inline resources.
Usage: python tests/browser_regression.py
"""
from pathlib import Path
import re
import os
import shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_text()
# External resources are inlined because this sandbox blocks all browser navigation.
html=re.sub(r'<script[^>]*src=[^>]*></script>','',html)
html=re.sub(r'<script>.*?</script>','',html,flags=re.S)
html=re.sub(r'<link href="css/portal\.css(?:\?[^"]+)?" rel="stylesheet"\s*/>', lambda _: '<style>'+(ROOT/'css/portal.css').read_text()+'</style>', html)
with sync_playwright() as p:
    chrome=os.getenv('PLAYWRIGHT_CHROMIUM_PATH') or shutil.which('chromium')
    options={'args':['--no-sandbox'],'headless':True}
    if chrome:options['executable_path']=chrome
    browser=p.chromium.launch(**options)
    for width,height in [(280,560),(320,568),(360,640),(375,667),(430,932)]:
        page=browser.new_page(viewport={'width':width,'height':height})
        page.set_content(html)
        result=page.evaluate('''() => {let b=document.querySelector('.login-submit').getBoundingClientRect();return {width:document.documentElement.scrollWidth,buttonTop:Math.round(b.top),buttonBottom:Math.round(b.bottom),action:document.forms.login.getAttribute("action"),scrollHeight:document.documentElement.scrollHeight}}''')
        assert result['width']<=width,(width,result)
        assert result['buttonTop'] < height,(width,result)
        assert result['buttonBottom'] < height or result['scrollHeight']>height,(width,result)
        assert result['action'].endswith('/login'),result
        print('PASS viewport',width,height,result)
        page.close()
    browser.close()
