/* Renders the three watermarked Mega Pack preview images used on /premium/.
   Usage: python3 source/build.py --out /tmp/fd-site && node source/art/make_pack_samples.cjs /tmp/fd-site
   Writes source/static/assets/img/pack/sample-{bingo,word-search,chart}.png (600 x 776, US Letter ratio).
   The pages are drawn by the real generators in print layout, with a SAMPLE watermark laid over them. */
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const { serve, launch } = require('../qa/lib.cjs');
const SITE = process.argv[2];
if (!SITE) { console.error('usage: node make_pack_samples.cjs BUILT_SITE_DIR'); process.exit(2); }
const OUT = path.join(__dirname, '..', 'static', 'assets', 'img', 'pack');
const JOBS = [
  { name: 'sample-bingo', url: '/bingo/christmas/', opts: { mode: 'word', grid: '5', perPage: '2', cards: '2', caller: false } },
  { name: 'sample-word-search', url: '/word-search/frog-life-cycle/', opts: { puzzles: '1', key: false } },
  { name: 'sample-chart', url: '/bedtime-routine-chart/', opts: { palette: 'mint', layout: 'strip' } },
];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const { server, base } = await serve(SITE);
  const browser = await launch();
  // 816 CSS px per Letter width; scale so the screenshot comes out about 600 px wide
  const ctx = await browser.newContext({ viewport: { width: 1100, height: 1400 }, deviceScaleFactor: 600 / 816, locale: 'en-US' });
  const page = await ctx.newPage();
  for (const job of JOBS) {
    await page.goto(base + job.url + '?seed=20261004');
    await page.waitForSelector('.sheet');
    await page.evaluate(async (opts) => {
      const done = new Promise(r => document.addEventListener('fd:rendered', r, { once: true }));
      const paper = document.getElementById('fd-paper'); if (paper) paper.value = 'letter';
      for (const [k, v] of Object.entries(opts)) {
        const el = document.querySelector('#fd-form [name="' + k + '"]');
        if (!el) continue;
        if (el.type === 'checkbox') el.checked = !!v; else el.value = v;
      }
      document.getElementById('fd-form').dispatchEvent(new Event('change', { bubbles: true }));
      await Promise.race([done, new Promise(r => setTimeout(r, 1500))]);
    }, job.opts);
    await page.evaluate(() => {
      document.querySelectorAll('.sheets, .sheet-frame, .sheet').forEach(e => e.style.setProperty('--s', '1', 'important'));
      const f = document.querySelector('.sheet');
      f.style.boxShadow = 'none';
      const w = document.createElement('div');
      w.textContent = 'SAMPLE';
      w.setAttribute('style', 'position:absolute;left:50%;top:50%;transform:translate(-50%,-50%) rotate(-35deg);font:700 150px/1 system-ui,sans-serif;letter-spacing:12px;color:rgba(240,122,90,.33);border:10px solid rgba(240,122,90,.33);border-radius:28px;padding:10px 40px;pointer-events:none;z-index:9');
      f.appendChild(w);
    });
    const raw = path.join(OUT, job.name + '.raw.png');
    await page.locator('.sheet').first().screenshot({ path: raw });
    execFileSync('python3', ['-c', `
from PIL import Image
im = Image.open(${JSON.stringify(raw)}).convert('RGB').resize((600, 776), Image.LANCZOS)
im = im.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
im.save(${JSON.stringify(path.join(OUT, job.name + '.png'))}, optimize=True)
`]);
    fs.unlinkSync(raw);
    console.log('wrote', job.name + '.png');
  }
  await browser.close(); server.close();
})().catch(e => { console.error(e); process.exit(1); });
