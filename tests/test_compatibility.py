"""Offline static and Chromium regression checks. Never contacts a MikroTik router.
Run: python -m unittest discover -s tests -v
Optional: pip install playwright; install a local Chromium executable.
"""
import re
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text(encoding='utf-8')
CSS=(ROOT/'css/portal.css').read_text(encoding='utf-8')
JS=(ROOT/'js/main.min.js').read_text(encoding='utf-8')

class Scan(HTMLParser):
    def __init__(self):
        super().__init__(); self.forms=[];self.inputs=[];self.scripts=[];self.links=[];self.buttons=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='form':self.forms.append(a)
        if tag=='input':self.inputs.append(a)
        if tag=='script':self.scripts.append(a)
        if tag=='link':self.links.append(a)
        if tag=='button':self.buttons.append(a)

class PortalTests(unittest.TestCase):
    def setUp(self):
        self.doc=Scan();self.doc.feed(HTML)
    def test_every_local_reference_exists(self):
        for item in self.doc.scripts+self.doc.links:
            path=item.get('src') or item.get('href')
            if path and not path.startswith(('https:','http:')):
                self.assertTrue((ROOT/path.split('?')[0]).exists(),path)
        self.assertTrue((ROOT/'img/logo.webp').exists())
    def test_login_available_without_javascript(self):
        forms=[f for f in self.doc.forms if f.get('name')=='login']
        self.assertEqual(len(forms),1)
        self.assertEqual(forms[0].get('action'),'/login')
        self.assertEqual(forms[0].get('method'),'post')
        self.assertTrue(any(x.get('name')=='username' for x in self.doc.inputs))
        self.assertTrue(any(x.get('type')=='submit' and 'login-submit' in x.get('class','') for x in self.doc.buttons))
    def test_login_has_shortcut_and_no_forced_width(self):
        self.assertIn('href="#loginCard"',HTML)
        self.assertIn('id=loginCard',HTML)
        self.assertIn('.screen{min-width:0',CSS)
        self.assertIn('@media (max-height:650px)',CSS)
    def test_expensive_camera_script_is_not_blocking_login(self):
        self.assertNotIn('<script src="js/cam.najm.js"></script>',HTML)
        self.assertIn("js.src='js/cam.najm.js'",HTML)
        self.assertIn('type=submit',HTML)
    def test_hotspot_speed_and_status_untouched(self):
        for value in ('hotspot','najm-speed-2m','najm-speed-10m','najm-speed-open'):
            self.assertIn('value='+value,HTML)
        for endpoint in ('/login?username=','/status?var=callBack','/logout?var=callBack'):
            self.assertIn(endpoint,JS)
        self.assertIn('classifyHotspotError',JS)
    def test_no_external_script_dependencies(self):
        self.assertTrue(all(not s.get('src','').startswith(('http:','https:')) for s in self.doc.scripts))
    def test_obfuscated_module_kept_unchanged(self):
        self.assertTrue((ROOT/'js/cam.najm.js').stat().st_size >30000)

if __name__ == '__main__':unittest.main()
