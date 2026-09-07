"""Browser checks for the existing dashboard, locally or on its public URL."""
from __future__ import annotations
import base64
import functools
import hashlib
import http.server
import io
import json
import os
import sys
import threading
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification'
OUT.mkdir(exist_ok=True)
FILE = 'pl-rrss-07-11-sep-26.html'
DAYS = ['monday', 'wednesday', 'friday']
report = {'version': 'png-verified-5', 'checks': {}, 'errors': []}
if len(sys.argv) > 1:
    url = sys.argv[1]
else:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_address[1]}/{FILE}'
report['url'] = url
with sync_playwright() as p:
    launch = {'headless': True}
    if os.environ.get('CHROMIUM_EXECUTABLE'):
        launch['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
    browser = p.chromium.launch(**launch)
    for view, width, height, dpr in [('desktop',1440,1000,1),('mobile',390,844,2)]:
        context = browser.new_context(viewport={'width':width,'height':height},device_scale_factor=dpr,accept_downloads=True)
        page = context.new_page()
        page.on('pageerror',lambda e:report['errors'].append(str(e)))
        response = page.goto(url,wait_until='networkidle',timeout=60000)
        assert response and response.status == 200
        assert page.locator('meta[name="dashboard-build"]').get_attribute('content') == 'png-verified-5'
        assert page.locator('[data-approved-count]').inner_text() == '0/3'
        data = page.locator('#proposal-data').evaluate('(el)=>JSON.parse(el.textContent)')
        expected_days = {d['id']:d for d in data['days']}
        checks = {'http_status':response.status,'downloads':{},'platforms_checked':0,'initial_pending':True}
        for day in DAYS:
            selector = '#creative-img-' + day
            page.locator(selector).evaluate('(img)=>img.decode()')
            src = page.locator(selector).get_attribute('src')
            source_bytes = base64.b64decode(src.split(',',1)[1],validate=True)
            expected_sha = page.locator(selector).get_attribute('data-sha256')
            assert hashlib.sha256(source_bytes).hexdigest() == expected_sha
            page.locator('#'+day+' .creative-preview').screenshot(path=str(OUT/(view+'-'+day+'.png')))
            with page.expect_download(timeout=15000) as event:
                page.locator('[data-download-creative="'+day+'"]').click()
            dl=event.value
            target=OUT/(view+'-'+dl.suggested_filename)
            dl.save_as(str(target))
            got=target.read_bytes()
            assert hashlib.sha256(got).hexdigest()==expected_sha, 'Preview/download mismatch'
            im=Image.open(io.BytesIO(got));im.load();assert im.size==(1200,1200) and im.format=='PNG'
            checks['downloads'][day]={'filename':dl.suggested_filename,'dimensions':[1200,1200],'bytes':len(got),'sha256':expected_sha,'identical_to_preview':True}
            for platform in ['facebook','instagram','linkedin','google']:
                page.locator('#'+day+' [data-platform="'+platform+'"]').click()
                expected=expected_days[day]['platforms'][platform]
                assert page.locator('#'+day+' [data-caption-body]').inner_text()==expected['caption']
                assert page.locator('#'+day+' [data-link-anchor]').get_attribute('href')==expected['url']
                checks['platforms_checked']+=1
            page.locator('#'+day+' [data-platform="instagram"]').click()
        checks['horizontal_overflow'] = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        assert checks['horizontal_overflow'] is False
        page.screenshot(path=str(OUT/(view+'-dashboard.png')),full_page=True)
        page.locator('#monday [data-set-status="approved"]').click()
        page.locator('#friday [data-set-status="changes"]').click()
        page.locator('#review-notes').fill('QA: temporary browser-only review note.')
        page.reload(wait_until='networkidle')
        assert page.locator('[data-approved-count]').inner_text()=='1/3'
        assert page.locator('#monday [data-status-pill]').inner_text()=='Aprobado'
        assert page.locator('#friday [data-status-pill]').inner_text()=='Pedir cambios'
        assert page.locator('#review-notes').input_value()=='QA: temporary browser-only review note.'
        checks['approval_and_notes_persist']=True
        with page.expect_download(timeout=10000) as event:
            page.locator('#download-summary').click()
        target=OUT/(view+'-review-summary.txt');event.value.save_as(str(target))
        assert 'QA: temporary browser-only review note.' in target.read_text()
        checks['review_export']=True
        if view=='desktop':
            context.grant_permissions(['clipboard-read','clipboard-write'])
            page.locator('#monday [data-copy-link]').click()
            assert page.evaluate('navigator.clipboard.readText()')==expected_days['monday']['platforms']['instagram']['url']
            page.locator('#monday [data-copy-caption]').click()
            assert page.evaluate('navigator.clipboard.readText()').startswith(expected_days['monday']['platforms']['instagram']['caption'])
            checks['clipboard_link_and_caption']=True
        else:
            page.locator('.menu-toggle').click()
            assert page.locator('.menu-toggle').get_attribute('aria-expanded')=='true'
            page.locator('.week-nav a[href="#friday"]').click()
            assert page.locator('.menu-toggle').get_attribute('aria-expanded')=='false'
            checks['mobile_navigation']=True
        page.evaluate('localStorage.removeItem("partners-weekly-review-2026-09-07")')
        report['checks'][view]=checks
        context.close()
    browser.close()
assert not report['errors'], report['errors']
report['passed']=True
(OUT/'verification-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
