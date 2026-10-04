/* Config behavior QA (SPEC 8, 9 and 13).
   Usage: node source/qa/qa_config.cjs SITE_DIR [--json OUT.json]

   1. config.js as shipped (all empty): no third-party requests at all, no ad requests, no AdSense tag,
      ad slots take zero space, every Mega Pack CTA and nav link hidden, Buy button says Coming soon,
      tip link hidden, no console errors.
   2. Dummy config (ADSENSE_CLIENT, AD_SLOT_IN_ARTICLE, PACK_URL, TIP_URL set; Google requests stubbed):
      the AdSense script tag is injected exactly once on ad pages and never on no-ads pages,
      in-article slots appear but never inside the tool, at least 150px from any button, and not in print,
      pack CTAs and the Mega Pack nav link appear with the checkout URL, the tip link appears. */
const fs = require('fs'), path = require('path');
const { serve, launch, reporter } = require('./lib.cjs');
const argv = process.argv.slice(2);
const SITE = argv[0];
const JSON_OUT = argv.includes('--json') ? argv[argv.indexOf('--json') + 1] : null;
if (!SITE) { console.error('usage: node qa_config.cjs SITE_DIR'); process.exit(2); }

const AD_PAGES = ['/', '/bingo-card-generator/', '/bingo/christmas/', '/word-search/halloween/', '/guides/bingo-patterns/',
  '/christmas-printables/', '/bingo/', '/about/', '/bedtime-routine-chart/toddler-picture-chart/'];
const NOAD_PAGES = ['/premium/', '/privacy/', '/terms/', '/contact/', '/embed/', '/embed/bingo/', '/embed/word-search/', '/bingo-caller/', '/404.html'];
const DUMMY = { ADSENSE_CLIENT: 'ca-pub-0000000000000000', AD_SLOT_IN_ARTICLE: '1234567890',
  PACK_URL: 'https://frogsdream.lemonsqueezy.com/checkout/buy/test', PACK_PRICE: '$7', TIP_URL: 'https://ko-fi.com/example',
  CONTACT_EMAIL: 'hello@frogsdream.com' };

(async () => {
  const R = reporter();
  const { server, base } = await serve(SITE);
  const browser = await launch();

  async function visit(ctx, url, width) {
    const page = await ctx.newPage();
    const errors = [], external = [], adReq = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    page.on('request', r => {
      const u = r.url();
      if (!u.startsWith(base) && !u.startsWith('data:') && !u.startsWith('blob:')) external.push(u);
      if (/adsbygoogle\.js/.test(u)) adReq.push(u);
    });
    await page.goto(base + url, { waitUntil: 'load' });
    await page.waitForTimeout(700);
    return { page, errors, external, adReq };
  }

  // ---------------------------------------------------------------- 1. empty config
  for (const width of [360, 1280]) {
    const ctx = await browser.newContext({ viewport: { width, height: 800 }, locale: 'en-US' });
    for (const url of AD_PAGES.concat(NOAD_PAGES)) {
      const W = `[empty config ${width}] ${url} `;
      const { page, errors, external } = await visit(ctx, url, width);
      const st = await page.evaluate(() => {
        const vis = el => { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden' && el.getClientRects().length > 0; };
        return {
          adTags: document.querySelectorAll('script[src*="adsbygoogle"], ins.adsbygoogle').length,
          slots: [...document.querySelectorAll('.ad-slot')].map(s => s.getBoundingClientRect().height + (vis(s) ? 1 : 0)),
          packVisible: [...document.querySelectorAll('[data-pack]')].filter(vis).length,
          premiumLinks: [...document.querySelectorAll('a[href="/premium/"], a[href$="frogsdream.com/premium/"]')].filter(vis).map(a => (a.closest('[class]') || a).className + ': ' + a.textContent.trim()),
          buy: [...document.querySelectorAll('[data-pack-buy]')].map(a => ({ href: a.getAttribute('href'), text: a.textContent.trim() })),
          tip: [...document.querySelectorAll('[data-tip]')].filter(vis).length,
          email: [...document.querySelectorAll('[data-email] a[href^="mailto:"]')].length,
        };
      });
      R.ok(external.length === 0, W + 'no third-party requests ' + (external.length ? JSON.stringify(external.slice(0, 3)) : ''));
      R.ok(st.adTags === 0 && st.slots.every(h => h === 0), W + `no ad tags, ad slots take no space (${st.slots.length} slots)`);
      const ctaOk = st.packVisible === 0 && (url === '/premium/' || url === '/embed/' || st.premiumLinks.length === 0);
      R.ok(ctaOk, W + 'no premium CTAs visible ' + (ctaOk ? '' : JSON.stringify(st.premiumLinks)));
      if (st.buy.length) R.ok(st.buy.every(b => !b.href && b.text === 'Coming soon'), W + 'Buy button shows Coming soon without a link');
      R.ok(st.tip === 0, W + 'tip link hidden');
      if (url === '/contact/') R.ok(st.email > 0, W + 'mailto link assembled by JS');
      R.ok(errors.length === 0, W + 'no console errors ' + (errors.length ? JSON.stringify(errors.slice(0, 3)) : ''));
      await page.close();
    }
    await ctx.close();
  }

  // ---------------------------------------------------------------- 2. dummy config
  const cfgJs = 'window.FD_CONFIG = ' + JSON.stringify(DUMMY) + ';';
  for (const width of [360, 1280]) {
    const ctx = await browser.newContext({ viewport: { width, height: 800 }, locale: 'en-US' });
    await ctx.route('**/assets/js/config.js*', r => r.fulfill({ body: cfgJs, contentType: 'application/javascript' }));
    await ctx.route(/googlesyndication|doubleclick|googleadservices|fundingchoices|google\.com/, r => r.fulfill({ body: '/* stub */', contentType: 'application/javascript' }));
    for (const url of AD_PAGES.concat(NOAD_PAGES)) {
      const W = `[dummy config ${width}] ${url} `;
      const { page, errors, adReq } = await visit(ctx, url, width);
      const noAds = NOAD_PAGES.includes(url);
      const st = await page.evaluate(() => {
        const vis = el => { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden' && el.getClientRects().length > 0; };
        const tags = document.querySelectorAll('script[src*="pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"]');
        const slots = [...document.querySelectorAll('.ad-slot.on')];
        const btns = [...document.querySelectorAll('button, .btn, input[type=submit]')].filter(vis).map(b => b.getBoundingClientRect());
        const near = [];
        slots.forEach(s => {
          const r = s.getBoundingClientRect();
          btns.forEach(b => {
            const dx = Math.max(0, b.left - r.right, r.left - b.right), dy = Math.max(0, b.top - r.bottom, r.top - b.bottom);
            if (Math.hypot(dx, dy) < 150) near.push(Math.round(Math.hypot(dx, dy)));
          });
        });
        return {
          tags: tags.length, src: tags[0] ? tags[0].src : '', async: tags[0] ? tags[0].async : null, cors: tags[0] ? tags[0].crossOrigin : null,
          slots: slots.length, inTool: document.querySelectorAll('.tool .adsbygoogle, .tool .ad-slot').length, near,
          labelled: slots.every(s => /Advertisement/i.test(getComputedStyle(s, '::before').content + s.textContent)),
          packVisible: [...document.querySelectorAll('[data-pack]')].filter(e => !e.hidden && getComputedStyle(e).display !== 'none' || (e.closest('.nav') && !e.hidden)).length,
          packTotal: document.querySelectorAll('[data-pack]').length,
          buy: [...document.querySelectorAll('[data-pack-buy]')].map(a => a.getAttribute('href')),
          tip: [...document.querySelectorAll('[data-tip]')].filter(vis).map(a => a.getAttribute('href')),
        };
      });
      if (noAds) {
        R.ok(st.tags === 0 && adReq.length === 0 && st.slots === 0, W + 'no AdSense tag or slots on a no-ads page');
      } else {
        R.ok(st.tags === 1 && adReq.length === 1 && st.async && st.cors === 'anonymous' && st.src.endsWith('client=' + DUMMY.ADSENSE_CLIENT),
          W + `AdSense script injected once (tags ${st.tags}, requests ${adReq.length}, async, crossorigin)`);
        R.ok(st.inTool === 0, W + 'no ads inside the tool container');
        R.ok(st.slots <= 2 && st.labelled, W + `${st.slots} in-article slots, labelled Advertisement`);
        R.ok(st.near.length === 0, W + 'ad slots at least 150px from any button ' + (st.near.length ? JSON.stringify(st.near) : ''));
        await page.emulateMedia({ media: 'print' });
        const printAds = await page.evaluate(() => [...document.querySelectorAll('.ad-slot, ins.adsbygoogle')].filter(e => getComputedStyle(e).display !== 'none').length);
        R.ok(printAds === 0, W + 'ads hidden in print');
        await page.emulateMedia({ media: 'screen' });
      }
      R.ok(st.packTotal === 0 || st.packVisible === st.packTotal, W + `pack CTAs shown with PACK_URL (${st.packVisible}/${st.packTotal})`);
      R.ok(st.buy.every(h => h === DUMMY.PACK_URL), W + 'Buy buttons link to PACK_URL');
      R.ok(st.tip.length >= 1 && st.tip.every(h => h === DUMMY.TIP_URL) || url.startsWith('/embed/'), W + 'tip link shown with TIP_URL');
      R.ok(errors.length === 0, W + 'no console errors ' + (errors.length ? JSON.stringify(errors.slice(0, 3)) : ''));
      await page.close();
    }
    await ctx.close();
  }
  await browser.close(); server.close();
  console.log(`\nConfig QA: ${R.results.length - R.fails} passed, ${R.fails} failed`);
  if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify(R.results, null, 1));
  process.exit(R.fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
