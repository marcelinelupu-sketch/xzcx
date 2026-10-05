/* Headless Chromium QA for every tool page, the embed pages and a sample of themed pages.
   Usage: node source/qa/qa_browser.cjs SITE_DIR [--all-themes] [--json OUT.json] [--shots DIR]

   At 360px and 1280px for each page:
     no console errors or page errors, no unexpected third-party requests, no horizontal scroll,
     Generate renders new sheets, nothing overflows a sheet,
     Print (window.print stubbed, then page.pdf with print media) gives one PDF page per sheet,
       each with the "Made free at frogsdream.com" credit,
     Download PDF produces a real PDF with the credit on every page and no banned dashes,
     the share link (1280px) restores identical sheets.
   --all-themes also runs every themed page at 1280px (generate, print and PDF download).
   jsPDF is self-hosted at /assets/js/vendor/jspdf.umd.min.js, so ANY request to another host fails the check,
   including during Download PDF. */
const fs = require('fs'), path = require('path'), os = require('os'), { execFileSync } = require('child_process');
const { serve, launch, reporter } = require('./lib.cjs');

const argv = process.argv.slice(2);
const SITE = argv.find(a => !a.startsWith('--') && argv[argv.indexOf(a) - 1] !== '--json' && argv[argv.indexOf(a) - 1] !== '--shots');
const ALL = argv.includes('--all-themes');
const JSON_OUT = argv.includes('--json') ? argv[argv.indexOf('--json') + 1] : null;
const SHOTS = argv.includes('--shots') ? argv[argv.indexOf('--shots') + 1] : null;
if (!SITE) { console.error('usage: node qa_browser.cjs SITE_DIR [--all-themes]'); process.exit(2); }
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'fdqa-'));
const CREDIT = 'Made free at frogsdream.com';
const BANNED = /[–—]/;

const TOOLS = ['/bingo-card-generator/', '/word-search-maker/', '/scavenger-hunt-generator/', '/word-scramble-maker/',
  '/bedtime-routine-chart/', '/reward-chart-maker/'];
const EMBEDS = ['/embed/bingo/', '/embed/word-search/', '/embed/word-scramble/'];
const SAMPLE = ['/bingo/baby-shower/', '/bingo/christmas/', '/bingo/90-ball-bingo-tickets/', '/bingo/75-ball-bingo-cards/',
  '/bingo/addition-facts-to-20/', '/bingo/icebreaker-find-someone-who/', '/bingo/sight-words-kindergarten/',
  '/word-search/frog-life-cycle/', '/word-search/us-states/', '/scavenger-hunt/nature-walk/', '/scavenger-hunt/teen-photo/',
  '/word-scramble/thanksgiving/', '/bedtime-routine-chart/morning-and-bedtime-routine/',
  '/reward-chart-maker/potty-training-chart/', '/reward-chart-maker/chore-chart-for-kids/'];

function pdfText(file) {
  try { return execFileSync('pdftotext', ['-layout', file, '-'], { encoding: 'utf8' }); } catch (e) { return null; }
}
function pdfPages(file, buf) {
  try { return +/Pages:\s+(\d+)/.exec(execFileSync('pdfinfo', [file], { encoding: 'utf8' }))[1]; }
  catch (e) { return (buf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length; }
}

(async () => {
  const R = reporter();
  const { server, base } = await serve(SITE);
  const browser = await launch();
  const allThemes = ALL ? JSON.parse(fs.readFileSync(path.join(SITE, 'assets/js/themes.json'), 'utf8')) : [];
  const themePaths = (Array.isArray(allThemes) ? allThemes : allThemes.themes || []).map(t => t.path);

  async function newCtx(width) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 500 ? 740 : 900 }, acceptDownloads: true, locale: 'en-US',
      isMobile: width < 500, hasTouch: width < 500, deviceScaleFactor: width < 500 ? 2 : 1 });
    await ctx.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: base });
    return ctx;
  }

  async function checkToolPage(ctx, url, width, opt) {
    const W = `[${width}] ${url} `;
    const page = await ctx.newPage();
    const errors = [], external = [];
    page.on('console', m => { if (m.type() === 'error' || (m.type() === 'warning' && !/speech|voices/i.test(m.text()))) errors.push(m.type() + ': ' + m.text()); });
    page.on('pageerror', e => errors.push('pageerror: ' + e));
    page.on('request', r => { const u = r.url(); if (!u.startsWith(base) && !u.startsWith('data:') && !u.startsWith('blob:')) external.push(u); });
    page.on('dialog', d => d.accept().catch(() => {}));
    await page.goto(base + url, { waitUntil: 'load' });
    try { await page.waitForSelector('.sheet', { timeout: 15000 }); } catch (e) { R.ok(false, W + 'preview rendered'); await page.close(); return; }
    // Generate visible on first screen (spec: top of the page above the fold on mobile)
    const genBox = await page.evaluate(() => { const b = document.getElementById('fd-generate').getBoundingClientRect(); return { top: b.top, bottom: b.bottom, h: innerHeight }; });
    if (opt.full) R.ok(genBox.bottom > 0 && genBox.top < genBox.h, W + `Generate button in first viewport (top ${Math.round(genBox.top)} of ${genBox.h})`);
    const before = await page.evaluate(() => FD.tool.state().seed);
    const rendered = page.evaluate(() => new Promise(r => document.addEventListener('fd:rendered', e => r(e.detail), { once: true })));
    await page.click('#fd-generate');
    const det = await Promise.race([rendered, new Promise(r => setTimeout(() => r(null), 10000))]);
    R.ok(det && det.pages > 0 && det.seed !== before, W + `Generate renders new sheets (${det && det.pages} pages)`);
    const lay = await page.evaluate(() => {
      const bad = [];
      document.querySelectorAll('.sheet-body').forEach((b, i) => { if (b.scrollHeight > b.clientHeight + 2 || b.scrollWidth > b.clientWidth + 2) bad.push('sheet ' + (i + 1)); });
      return { h: document.documentElement.scrollWidth - document.documentElement.clientWidth, bad, frames: document.querySelectorAll('.sheet-frame').length };
    });
    R.ok(lay.h <= 0, W + `no horizontal page scroll (${lay.h}px)`);
    R.ok(lay.bad.length === 0, W + 'nothing overflows a sheet ' + (lay.bad.length ? JSON.stringify(lay.bad.slice(0, 5)) : ''));
    if (SHOTS && opt.full) await page.screenshot({ path: path.join(SHOTS, url.replace(/\W+/g, '_') + width + '.png') });

    // Print: stub window.print, click Print, then render print media to PDF
    await page.evaluate(() => { window.__printed = 0; window.print = () => { window.__printed++; }; });
    await page.click('#fd-print');
    await page.waitForFunction(() => window.__printed > 0, null, { timeout: 5000 }).catch(() => {});
    const printed = await page.evaluate(() => window.__printed);
    await page.emulateMedia({ media: 'print' });
    const pv = await page.evaluate((CREDIT) => {
      const vis = el => { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden' && el.getClientRects().length > 0; };
      const frames = [...document.querySelectorAll('.sheet-frame')];
      const hiddenOk = ['.site-header', '.site-footer', '.crumbs', '.tool-controls', '.prose', '.faq', '.related', '.page-head', '.ad-slot', '.tool-status', 'button']
        .every(sel => [...document.querySelectorAll(sel)].every(e => !vis(e) || e.closest('.sheet')));
      return { frames: frames.length, credits: frames.filter(f => f.innerText.includes(CREDIT)).length, hiddenOk };
    }, CREDIT);
    R.ok(printed > 0 && pv.frames > 0 && pv.credits === pv.frames, W + `Print: ${pv.frames} sheets, credit line on ${pv.credits}`);
    R.ok(pv.hiddenOk, W + 'Print hides header, footer, controls, prose, buttons and ads');
    const pfile = path.join(TMP, 'print.pdf');
    await page.pdf({ path: pfile, preferCSSPageSize: true, printBackground: true });
    const pPages = pdfPages(pfile, fs.readFileSync(pfile));
    const pText = pdfText(pfile);
    const pCred = pText == null ? pPages : (pText.match(/Made free at frogsdream\.com/g) || []).length;
    R.ok(pPages === pv.frames && pCred === pPages, W + `print PDF: ${pPages} pages for ${pv.frames} sheets, credit found ${pCred} times`);
    if (pText != null) R.ok(!BANNED.test(pText), W + 'print PDF text has no em or en dashes');
    await page.emulateMedia({ media: 'screen' });

    // Download PDF
    if (opt.pdf !== false) {
      try {
        const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 45000 }), page.click('#fd-pdf')]);
        const f = path.join(TMP, 'dl.pdf');
        await dl.saveAs(f);
        const buf = fs.readFileSync(f), n = pdfPages(f, buf), t = pdfText(f);
        const cred = t == null ? n : (t.match(/Made free at frogsdream\.com/g) || []).length;
        R.ok(buf.slice(0, 5).toString() === '%PDF-' && n === pv.frames, W + `Download PDF: ${dl.suggestedFilename()} ${buf.length} B, ${n} pages (preview ${pv.frames})`);
        R.ok(cred >= n, W + `Download PDF has the credit line on every page (${cred}/${n})`);
        if (t != null) R.ok(!BANNED.test(t), W + 'Download PDF text has no em or en dashes');
        if (SHOTS && opt.full) fs.copyFileSync(f, path.join(SHOTS, url.replace(/\W+/g, '_') + width + '.pdf'));
      } catch (e) { R.ok(false, W + 'Download PDF: ' + e.message.split('\n')[0]); }
    }

    // Share link restores identical sheets
    if (opt.share) {
      const sheetsA = await page.evaluate(() => document.getElementById('fd-sheets').innerHTML);
      await page.click('#fd-share');
      await page.waitForTimeout(300);
      let link = await page.evaluate(() => navigator.clipboard.readText().catch(() => ''));
      if (!link) link = await page.evaluate(() => (document.querySelector('.modal input, .modal textarea') || {}).value || '');
      const p2 = await ctx.newPage();
      p2.on('pageerror', e => errors.push('share pageerror: ' + e));
      await p2.goto(link.replace('https://frogsdream.com', base));
      await p2.waitForSelector('.sheet');
      await p2.waitForTimeout(400);
      const sheetsB = await p2.evaluate(() => document.getElementById('fd-sheets').innerHTML);
      R.ok(link.includes('#s=') && sheetsA === sheetsB, W + 'share link restores identical sheets');
      await p2.close();
    }
    R.ok(errors.length === 0, W + 'no console errors or warnings ' + (errors.length ? JSON.stringify(errors.slice(0, 3)) : ''));
    R.ok(external.length === 0, W + 'no third-party requests ' + (external.length ? JSON.stringify(external.slice(0, 3)) : ''));
    const store = await page.evaluate(() => ({ ls: localStorage.length, ck: document.cookie }));
    R.ok(store.ls === 0 && !store.ck, W + `no localStorage or cookies set (ePrivacy; tools use sessionStorage only) ls=${store.ls}`);
    await page.close();
  }

  async function checkCaller(ctx, width) {
    const W = `[${width}] /bingo-caller/ `;
    const page = await ctx.newPage();
    const errors = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    page.on('dialog', d => d.accept().catch(() => {}));
    await page.goto(base + '/bingo-caller/');
    await page.waitForSelector('#cl-next:not([disabled])', { timeout: 10000 });
    await page.click('#cl-next');
    const big1 = await page.textContent('#cl-big');
    await page.keyboard.press('Space');
    await page.waitForTimeout(150);
    const last = await page.$$eval('#cl-last li', l => l.length);
    R.ok(/\d/.test(big1) && last >= 2, W + `Call next and space bar call numbers (${big1}, ${last} in last calls)`);
    await page.click('#cl-undo');
    R.ok((await page.$$eval('#cl-last li', l => l.length)) === last - 1, W + 'Undo removes the last call');
    const h = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    R.ok(h <= 0, W + 'no horizontal scroll');
    await page.reload();
    await page.waitForSelector('#cl-next:not([disabled])');
    R.ok((await page.$$eval('#cl-last li', l => l.length)) === last - 1, W + 'game survives a reload');
    await page.selectOption('#cl-mode', 'words');
    await page.waitForFunction(() => document.querySelectorAll('#cl-theme option').length > 1, null, { timeout: 5000 }).catch(() => {});
    const opts = await page.$$eval('#cl-theme option', o => o.length);
    await page.selectOption('#cl-mode', '75');
    R.ok(opts > 90, W + `themed list dropdown filled (${opts - 1} lists)`);
    R.ok(errors.length === 0, W + 'no console errors ' + (errors.length ? JSON.stringify(errors.slice(0, 3)) : ''));
    await page.close();
  }

  for (const width of [360, 1280]) {
    const ctx = await newCtx(width);
    for (const u of TOOLS) await checkToolPage(ctx, u, width, { full: true, share: width === 1280 });
    for (const u of EMBEDS) await checkToolPage(ctx, u, width, { full: true, share: false });
    for (const u of SAMPLE) await checkToolPage(ctx, u, width, { full: true, share: width === 1280 });
    await checkCaller(ctx, width);
    await ctx.close();
  }
  if (ALL) {
    const ctx = await newCtx(1280);
    for (const u of themePaths.filter(p => !SAMPLE.includes(p))) await checkToolPage(ctx, u, 1280, { full: false, share: false });
    await ctx.close();
  }
  await browser.close(); server.close();
  fs.rmSync(TMP, { recursive: true, force: true });
  console.log(`\nBrowser QA: ${R.results.length - R.fails} passed, ${R.fails} failed`);
  if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify(R.results, null, 1));
  process.exit(R.fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
