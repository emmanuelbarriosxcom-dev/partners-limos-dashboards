"""Repair the existing dashboard and embed exact, complete PNG exports."""
from __future__ import annotations
import base64
import hashlib
import io
import json
import os
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / 'pl-rrss-07-11-sep-26.html'
OUT = ROOT / 'verification'
OUT.mkdir(exist_ok=True)
EXPECTED = {
    'monday': '80c783e474dcdc2ca94a6a50bfed15fef68426d8460b530c51515b6ee742b644',
    'wednesday': '5b3c7e071c8427d163a202da1689456c91d84bf8e97976972ec74dec085c004d',
    'friday': '4df1dda568793a0af82e04363841666b38fa1e2166d8521ef3eb0d598debb30b',
}
report = {'version': 'png-verified-5', 'source_integrity': {}, 'exports': {}}
soup = BeautifulSoup(PAGE.read_text(encoding='utf-8'), 'html.parser')
if soup.find('meta', attrs={'name':'dashboard-build','content':'png-verified-5'}):
    raise SystemExit('This dashboard is already compiled. Refusing to apply overlays twice.')
data = json.loads((ROOT / 'pl-rrss-07-11-sep-26.json').read_text(encoding='utf-8'))
css = (ROOT / 'pl.css').read_text(encoding='utf-8')
for day in EXPECTED:
    text = ''.join(p.read_text(encoding='ascii').strip() for p in sorted((ROOT / 'imgdata-hd').glob(day + '-*.txt')))
    if day == 'monday' and text[4903] == 'u':
        text = text[:4903] + 'i' + text[4904:]
    if day == 'friday' and len(text) == 32181:
        assert text[18000] == 'Y'
        text = text[:18000] + text[18001:]
    binary = base64.b64decode(text, validate=True)
    digest = hashlib.sha256(binary).hexdigest()
    assert digest == EXPECTED[day], f'Source integrity failed for {day}'
    im = Image.open(io.BytesIO(binary)); im.load()
    assert im.size == (1200, 1200)
    buf = io.BytesIO(); im.save(buf, format='PNG')
    src = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
    img = soup.find('img', id='creative-img-' + day)
    img['src'] = src
    img['loading'] = 'eager'
    report['source_integrity'][day] = {'sha256': digest, 'dimensions': list(im.size), 'verified': True}

for tag in soup.find_all('script'):
    tag.decompose()
for tag in soup.find_all('link', rel='stylesheet'):
    tag.decompose()
style = soup.new_tag('style'); style.string = css; soup.head.append(style)
render_html = str(soup)
with sync_playwright() as p:
    launch = {'headless': True}
    if os.environ.get('CHROMIUM_EXECUTABLE'):
        launch['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
    browser = p.chromium.launch(**launch)
    page = browser.new_page(viewport={'width': 1440, 'height': 1280}, device_scale_factor=1)
    for day in EXPECTED:
        page.set_content(render_html, wait_until='load')
        page.evaluate('document.fonts.ready')
        page.locator('#creative-img-' + day).evaluate('(img) => img.decode()')
        page.evaluate('''(day) => {
          const original = document.querySelector('#' + day + ' .creative-preview');
          const width = original.getBoundingClientRect().width;
          const clone = original.cloneNode(true);
          clone.style.cssText = 'position:absolute;top:0;left:0;width:' + width + 'px;height:' + width + 'px;aspect-ratio:1;transform:scale(' + (1200 / width) + ');transform-origin:top left;box-shadow:none;';
          document.body.replaceChildren(clone);
          document.body.style.cssText = 'margin:0;width:1440px;height:1280px;overflow:hidden;background:#0b0d18';
        }''', day)
        png = page.screenshot(clip={'x': 0, 'y': 0, 'width': 1200, 'height': 1200}, type='png', animations='disabled')
        im = Image.open(io.BytesIO(png)); im.load(); assert im.size == (1200, 1200)
        (OUT / (day + '-final.png')).write_bytes(png)
        preview = soup.select_one('#' + day + ' .creative-preview')
        img = preview.find('img')
        img['src'] = 'data:image/png;base64,' + base64.b64encode(png).decode('ascii')
        img['width'] = '1200'; img['height'] = '1200'
        img['loading'] = 'eager'; img['decoding'] = 'async'
        img['data-sha256'] = hashlib.sha256(png).hexdigest()
        for layer in preview.select('.creative-shade,.creative-brand,.creative-message,.creative-footer'):
            layer.decompose()
        preview['data-export-ready'] = 'png-verified-5'
        report['exports'][day] = {'dimensions': [1200, 1200], 'sha256': hashlib.sha256(png).hexdigest(), 'bytes': len(png)}
    browser.close()

for d in data['days']:
    d['image'] = '#creative-img-' + d['id']
script = soup.new_tag('script', id='proposal-data', type='application/json')
script.string = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
soup.body.append(script)
core = (ROOT / 'pl-core.js').read_text(encoding='utf-8')
start = core.index('  const downloadCreative = async (dayId) => {')
end = core.index('\n  document.querySelectorAll("[data-day]")', start)
core = core[:start] + '''  const downloadCreative = async (dayId) => {
    const image = document.getElementById("creative-img-" + dayId);
    const button = document.querySelector('[data-download-creative="' + dayId + '"]');
    const label = button.textContent;
    button.disabled = true;
    button.textContent = "Preparando PNG…";
    try {
      await image.decode();
      if (image.naturalWidth !== 1200 || image.naturalHeight !== 1200) throw new Error("Invalid image dimensions");
      const response = await fetch(image.currentSrc || image.src);
      const blob = await response.blob();
      if (blob.type !== "image/png" || blob.size < 100000) throw new Error("Invalid PNG data");
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "partners-limos-" + dayId + "-07-11-september-2026-1200x1200.png";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      notify("PNG 1200 × 1200 preparado");
    } catch (error) {
      console.error("Creative download failed", dayId, error);
      notify("No se pudo descargar la imagen. Recarga e inténtalo de nuevo.");
    } finally {
      button.disabled = false;
      button.textContent = label;
    }
  };
''' + core[end:]
script = soup.new_tag('script'); script.string = core; soup.body.append(script)
meta = soup.new_tag('meta', attrs={'name':'dashboard-build', 'content':'png-verified-5'})
soup.head.append(meta)
PAGE.write_text(str(soup), encoding='utf-8')
(OUT / 'build-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
