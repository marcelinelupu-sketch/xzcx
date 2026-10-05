/* Headless Chromium check for the bingo card generator and the bingo caller.
   Usage: node source/tests/browser_bingo.cjs <built site dir> [screenshot dir]
   Builds nothing itself: run python3 source/build.py --out DIR first. jsPDF is self-hosted in the site, so any
   request to another host (including during Download PDF) is a failure. Exits 1 on any failure. */
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require(process.env.PW_PATH || '/opt/node22/lib/node_modules/playwright');
const [SITE, SHOTS] = process.argv.slice(2);
if (!SITE) { console.error('usage: node browser_bingo.cjs SITE_DIR [SHOT_DIR]'); process.exit(2); }
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.ttf': 'font/ttf', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0].split('#')[0]);
  if (p.endsWith('/')) p += 'index.html';
  const f = path.join(SITE, p);
  if (!f.startsWith(path.resolve(SITE)) || !fs.existsSync(f)) { res.writeHead(404); return res.end('nf'); }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});
let fails = 0;
const ok = (cond, msg) => { if (!cond) { fails++; console.log('FAIL ' + msg); } else console.log('ok   ' + msg); };

(async () => {
  await new Promise(r => server.listen(0, r));
  const base = 'http://127.0.0.1:' + server.address().port;
  const browser = await chromium.launch();
  for (const width of [360, 1280]) {
    const ctx = await browser.newContext({ viewport: { width, height: 900 }, acceptDownloads: true, locale: 'en-US' });
    const page = await ctx.newPage();
    const errors = [], external = [];
    page.on('request', r => { const u = r.url(); if (!u.startsWith(base) && !u.startsWith('data:') && !u.startsWith('blob:')) external.push(u); });
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    page.on('dialog', dlg => dlg.accept().catch(() => {}));
    const W = '[' + width + 'px] ';

    async function rendered(action) {
      const p = page.evaluate(() => new Promise(r => document.addEventListener('fd:rendered', e => r(e.detail), { once: true })));
      await action();
      return p;
    }
    async function overflow() {
      return page.evaluate(() => {
        const bad = [];
        document.querySelectorAll('.bg-c span, .bg-slips span, .bg-ord li').forEach(s => {
          const c = s.closest('.bg-c, .bg-slips > div, .bg-ord li');
          const a = s.getBoundingClientRect(), b = c.getBoundingClientRect();
          if (a.width > b.width + 1 || a.right > b.right + 1 || a.left < b.left - 1) bad.push(s.textContent);
        });
        document.querySelectorAll('.bg-area').forEach(ar => {
          const r = ar.getBoundingClientRect();
          ar.querySelectorAll('.bg-blk').forEach(bk => { const q = bk.getBoundingClientRect(); if (q.bottom > r.bottom + 2 || q.right > r.right + 2) bad.push('block outside area'); });
        });
        document.querySelectorAll('.sheet-body').forEach(sb => { if (sb.scrollHeight > sb.clientHeight + 2) bad.push('sheet body overflow'); });
        return bad;
      });
    }
    async function pdfDownload(label) {
      const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 30000 }), page.click('#fd-pdf')]);
      const file = await dl.path(), buf = fs.readFileSync(file);
      const pages = (buf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length;
      ok(buf.slice(0, 5).toString() === '%PDF-' && pages > 0, W + label + ': PDF downloaded (' + buf.length + ' bytes, ' + pages + ' pages, ' + dl.suggestedFilename() + ')');
      if (SHOTS) fs.copyFileSync(file, path.join(SHOTS, label.replace(/\W+/g, '_') + '_' + width + '.pdf'));
      return pages;
    }

    /* ---- generator page ---- */
    await page.goto(base + '/bingo-card-generator/');
    await page.waitForSelector('.sheet');
    let d = await rendered(() => page.click('#fd-generate'));
    ok(d.pages >= 5, W + 'word mode default renders ' + d.pages + ' pages');
    const genVisible = await page.locator('#fd-generate').isVisible();
    ok(genVisible, W + 'Generate button visible');
    const hscroll = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    ok(hscroll <= 0, W + 'no horizontal page scroll (' + hscroll + ')');
    const cards = await page.$$eval('.bg-blk', b => b.length);
    ok(cards === 10, W + '10 card blocks shown (' + cards + ')');
    const caller = await page.$$eval('.sheet-key', s => s.length);
    ok(caller >= 1, W + 'caller sheet present');
    ok((await overflow()).length === 0, W + 'word mode: nothing overflows ' + JSON.stringify(await overflow()).slice(0, 200));
    if (SHOTS) await page.screenshot({ path: path.join(SHOTS, 'gen_' + width + '.png'), fullPage: false });
    const pdfPages = await pdfDownload('word');
    ok(pdfPages === d.pages, W + 'PDF page count matches preview (' + pdfPages + ' vs ' + d.pages + ')');
    await page.emulateMedia({ media: 'print' });
    const printPdf = await page.pdf({ preferCSSPageSize: true, printBackground: true });
    const printPages = (printPdf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length;
    ok(printPages === d.pages, W + 'print preview has ' + printPages + ' pages (expected ' + d.pages + ')');
    if (SHOTS) fs.writeFileSync(path.join(SHOTS, 'print_' + width + '.pdf'), printPdf);
    await page.emulateMedia({ media: 'screen' });

    const combos = [
      { mode: '75', perPage: '1' }, { mode: '75', perPage: '4' }, { mode: '90', cards: '12' }, { mode: '30', grid: '4', perPage: '4' },
      { mode: 'word', grid: '3', perPage: '1' }, { mode: 'word', grid: '4', perPage: '4' }, { mode: 'word', grid: '5', perPage: '1', names: true }
    ];
    for (const c of combos) {
      d = await rendered(async () => {
        await page.selectOption('#bg-mode', c.mode);
        if (c.grid) await page.selectOption('#bg-grid', c.grid);
        if (c.perPage && c.mode !== '90') await page.selectOption('#bg-per', c.perPage);
        if (c.cards) await page.fill('#bg-cards', c.cards);
        await page.setChecked('#bg-names', !!c.names, { force: true });
        await page.click('#fd-generate');
      });
      const label = JSON.stringify(c);
      const msg = await page.textContent('#fd-msg');
      ok(d.pages > 0, W + label + ' renders ' + d.pages + ' pages; msg: ' + msg.trim().slice(0, 90));
      const of = await overflow();
      ok(of.length === 0, W + label + ' nothing overflows ' + JSON.stringify(of).slice(0, 200));
      if (c.mode === '90') {
        const strips = await page.$$eval('.bg-grid', g => g.length);
        ok(strips === 12, W + '90-ball: 12 tickets in 2 strips (' + strips + ')');
        const nums = await page.$$eval('.sheet:not(.sheet-key)', sh => sh.map(s => [...s.querySelectorAll('.bg-c')].map(c => +c.textContent).filter(Boolean).sort((a, b) => a - b).join(',')));
        const full = Array.from({ length: 90 }, (_, i) => i + 1).join(',');
        ok(nums.every(n => n === full), W + '90-ball: every strip covers 1 to 90 once');
      }
      if (SHOTS) await page.locator('.sheet-frame').first().screenshot({ path: path.join(SHOTS, 'sheet_' + Object.values(c).join('-') + '_' + width + '.png') });
      if (width === 1280) await pdfDownload(Object.values(c).join('-'));
    }
    /* long phrases (find someone who) at 4 per page with name lines: everything must still fit */
    const long = ['Has a pet that is not a cat or a dog', 'Can whistle a whole song', 'Was born in another country', 'Has never seen snow', 'Plays a musical instrument',
      'Can say hello in three languages', 'Has the same birthday month as you', 'Likes pineapple on pizza', 'Has climbed a mountain', 'Is the youngest in the family',
      'Has met someone famous', 'Can touch their nose with their tongue', 'Reads before bed every night', 'Has a collection of something unusual', 'Has been on a sailboat',
      'Knows how to knit', 'Has broken a bone', 'Prefers tea to coffee', 'Can juggle', 'Has a hidden talent', 'Has run a race', 'Grows vegetables at home',
      'Speaks more than two languages', 'Has visited three continents', 'Supercalifragilisticexpialidocious'];
    d = await rendered(async () => {
      await page.selectOption('#bg-mode', 'word'); await page.selectOption('#bg-grid', '5'); await page.selectOption('#bg-per', '4');
      await page.setChecked('#bg-names', true); await page.fill('#fd-words', long.join('\n')); await page.click('#fd-generate');
    });
    const ofl = await overflow();
    ok(ofl.length === 0, W + 'long phrases with name lines fit ' + JSON.stringify(ofl).slice(0, 200));
    if (SHOTS) await page.locator('.sheet-frame').first().screenshot({ path: path.join(SHOTS, 'sheet_long_' + width + '.png') });
    if (width === 1280) await pdfDownload('long-names');
    await page.setChecked('#bg-names', false);

    /* short list error, then share link restores the same cards */
    await page.selectOption('#bg-mode', 'word'); await page.selectOption('#bg-grid', '5'); await page.setChecked('#bg-names', false);
    await page.fill('#fd-words', 'one\ntwo\nthree');
    await page.waitForTimeout(500);
    const err = await page.textContent('#fd-msg');
    ok(/needs 24/.test(err), W + 'short list shows the friendly error: ' + err.trim());
    await page.click('#fd-reset');
    await page.waitForTimeout(400);
    const before = await page.$$eval('.bg-c', c => c.map(x => x.textContent).join('|'));
    await ctx.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
    const link = await page.evaluate(() => { const s = FD.tool.state(); return location.href.split('#')[0] + '#s=' + FD.share.encode({ t: s.title, w: s.words, o: s.options, p: s.paper, i: s.ink ? 1 : 0, f: s.stamp ? 1 : 0, s: s.seed }); });
    const p2 = await ctx.newPage();
    await p2.goto(link); await p2.waitForSelector('.bg-c');
    const after = await p2.$$eval('.bg-c', c => c.map(x => x.textContent).join('|'));
    ok(before === after, W + 'share link restores identical cards');
    await p2.close();

    /* themed page */
    await page.goto(base + '/bingo/baby-shower/');
    await page.waitForSelector('.sheet');
    d = await rendered(() => page.click('#fd-generate'));
    ok(d.pages >= 6, W + 'baby shower theme renders ' + d.pages + ' pages');
    ok((await overflow()).length === 0, W + 'baby shower: nothing overflows');
    await pdfDownload('baby-shower');

    /* ---- caller ---- */
    await page.goto(base + '/bingo-caller/');
    await page.waitForSelector('#cl-board .cl-c');
    await page.evaluate(() => sessionStorage.removeItem('fd:caller'));
    await page.reload(); await page.waitForSelector('#cl-board .cl-c');
    ok(await page.$$eval('#cl-board .cl-c', c => c.length) === 75, W + 'caller: 75-ball board');
    await page.click('#cl-next');
    await page.locator('body').click({ position: { x: 5, y: 5 } }).catch(() => {});
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    await page.keyboard.press('Space');
    await page.keyboard.press('Space');
    let count = await page.textContent('#cl-count');
    ok(/^3 of 75/.test(count), W + 'caller: button plus space bar called 3 (' + count + ')');
    const big = await page.textContent('#cl-big');
    ok(/^[BINGO] \d+$/.test(big), W + 'caller: display shows ' + big);
    ok(await page.$$eval('#cl-board .cl-c.on', c => c.length) === 3, W + 'caller: board highlights 3');
    ok(await page.$$eval('#cl-last li', c => c.length) === 3, W + 'caller: last calls list');
    await page.click('#cl-undo');
    ok(/^2 of 75/.test(await page.textContent('#cl-count')), W + 'caller: undo');
    await page.reload(); await page.waitForSelector('#cl-board .cl-c');
    ok(/^2 of 75/.test(await page.textContent('#cl-count')), W + 'caller: game survives a reload');
    await page.selectOption('#cl-mode', '90');
    await page.click('#cl-apply');
    ok(await page.$$eval('#cl-board .cl-c', c => c.length) === 90, W + 'caller: 90-ball board');
    await page.check('#cl-uk');
    await page.click('#cl-next');
    const say = await page.textContent('#cl-say');
    ok(/, /.test(say), W + 'caller: UK call shown (' + say + ')');
    await page.selectOption('#cl-mode', 'words');
    await page.waitForFunction(() => document.querySelectorAll('#cl-theme option').length > 1, null, { timeout: 5000 }).catch(() => {});
    const nThemes = await page.$$eval('#cl-theme option', o => o.length - 1);
    ok(nThemes > 0, W + 'caller: themed lists loaded (' + nThemes + ')');
    if (nThemes) {
      await page.selectOption('#cl-theme', { index: 1 });
      await page.waitForTimeout(100);
      const okBoard = await page.$$eval('#cl-board .cl-c', c => c.length);
      if (/Press "Start/.test(await page.textContent('#cl-msg'))) { await page.click('#cl-apply'); }
      ok((await page.$$eval('#cl-board .cl-c', c => c.length)) > 5, W + 'caller: themed word board (' + okBoard + ')');
    }
    await page.click('#cl-auto');
    await page.waitForTimeout(300);
    ok(/^1 of/.test(await page.textContent('#cl-count')), W + 'caller: auto-call starts with a call');
    await page.click('#cl-auto');
    await page.click('#cl-full');
    await page.waitForTimeout(300);
    ok(await page.evaluate(() => document.getElementById('tool').classList.contains('cl-proj')), W + 'caller: projector mode on');
    if (SHOTS) await page.screenshot({ path: path.join(SHOTS, 'caller_proj_' + width + '.png') });
    await page.click('#cl-full');
    await page.waitForTimeout(300);
    const hs2 = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    ok(hs2 <= 0, W + 'caller: no horizontal page scroll (' + hs2 + ')');
    if (SHOTS) await page.screenshot({ path: path.join(SHOTS, 'caller_' + width + '.png'), fullPage: true });

    ok(errors.length === 0, W + 'no console errors ' + JSON.stringify(errors).slice(0, 300));
    ok(external.length === 0, W + 'no third-party requests (jsPDF self-hosted) ' + JSON.stringify(external.slice(0, 3)));
    /* ePrivacy: tools keep user input in sessionStorage only (cleared when the tab closes); no localStorage, no cookies */
    const store = await page.evaluate(() => ({ ls: localStorage.length, ss: sessionStorage.length, ck: document.cookie }));
    const cookies = await ctx.cookies();
    ok(store.ls === 0 && !store.ck && cookies.length === 0 && store.ss > 0,
      W + `storage: sessionStorage only (${store.ss} keys), localStorage ${store.ls}, cookies ${cookies.length}`);
    await ctx.close();
  }
  await browser.close();
  server.close();
  console.log(fails ? fails + ' check(s) failed' : 'all browser checks passed');
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
