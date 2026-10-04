/* Lighthouse mobile audit (SPEC 13: 95+ for Performance, Accessibility, Best Practices and SEO).
   Usage: node source/qa/qa_lighthouse.mjs SITE_DIR [--json OUT.json] [--min 95]
   Needs the lighthouse npm package: run_all.sh installs it into source/qa/node_modules, or set LH_DIR to a folder
   whose node_modules holds lighthouse and chrome-launcher. Uses the Playwright Chromium binary.
   The site is served locally with gzip, so the scores approximate the real host (Hostinger adds HTTP/2 and caching). */
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
import { fileURLToPath, pathToFileURL } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { serve, chromium } = require('./lib.cjs');
const argv = process.argv.slice(2);
const SITE = argv[0];
const JSON_OUT = argv.includes('--json') ? argv[argv.indexOf('--json') + 1] : null;
const MIN = argv.includes('--min') ? +argv[argv.indexOf('--min') + 1] : 95;
const PAGES = ['/', '/bingo-card-generator/', '/bingo/baby-shower/', '/word-search/halloween/', '/guides/bingo-patterns/', '/bingo-caller/'];

const lhRoot = process.env.LH_DIR || here;
const req2 = createRequire(path.join(lhRoot, 'package.json'));
let lighthouse, launcher;
try {
  lighthouse = (await import(pathToFileURL(req2.resolve('lighthouse')).href)).default;
  launcher = await import(pathToFileURL(req2.resolve('chrome-launcher')).href);
} catch (e) {
  console.log('SKIP lighthouse is not installed (npm install --prefix source/qa lighthouse@13)');
  process.exit(3);
}

const { server, base } = await serve(SITE);
const chromePath = chromium.executablePath();
const chrome = await launcher.launch({ chromePath, chromeFlags: ['--headless=new', '--no-sandbox', '--disable-gpu'] });
const results = [];
let fails = 0;
for (const p of PAGES) {
  const r = await lighthouse(base + p, { port: chrome.port, output: 'json', logLevel: 'error',
    onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'] });
  const lhr = r.lhr;
  const sc = Object.fromEntries(Object.entries(lhr.categories).map(([k, v]) => [k, Math.round(v.score * 100)]));
  const a = lhr.audits;
  const metrics = {
    FCP: a['first-contentful-paint'].displayValue, LCP: a['largest-contentful-paint'].displayValue,
    TBT: a['total-blocking-time'].displayValue, CLS: a['cumulative-layout-shift'].displayValue,
    bytes: Math.round((a['total-byte-weight'].numericValue || 0) / 1024) + ' KiB',
  };
  const failing = Object.values(a).filter(x => x.score !== null && x.score < 0.9 && x.scoreDisplayMode !== 'informative' && x.scoreDisplayMode !== 'notApplicable' && x.scoreDisplayMode !== 'manual')
    .map(x => x.id + (x.displayValue ? ' (' + x.displayValue + ')' : ''));
  const detail = {};
  for (const id of ['color-contrast', 'crawlable-anchors', 'link-name', 'button-name', 'label', 'target-size', 'heading-order', 'image-alt', 'is-crawlable', 'canonical']) {
    if (a[id] && a[id].score !== null && a[id].score < 1 && a[id].details && a[id].details.items)
      detail[id] = a[id].details.items.slice(0, 8).map(i => (i.node && (i.node.snippet + ' ' + (i.node.explanation || '').split('\n')[1])) || i.snippet || JSON.stringify(i).slice(0, 200));
  }
  const rb = (a['render-blocking-resources'] || a['render-blocking-insight'] || {}).details;
  const blocking = rb && rb.items ? rb.items.map(i => i.url).filter(u => !u.startsWith(base)) : [];
  // the SEO "is-crawlable" and canonical audits differ locally because canonicals point at frogsdream.com
  const pass = Object.values(sc).every(v => v >= MIN) && blocking.length === 0;
  if (!pass) fails++;
  results.push({ page: p, pass, scores: sc, metrics, thirdPartyRenderBlocking: blocking, lowAudits: failing, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'} ${p}  perf ${sc.performance}  a11y ${sc.accessibility}  bp ${sc['best-practices']}  seo ${sc.seo}  ` +
    `FCP ${metrics.FCP} LCP ${metrics.LCP} TBT ${metrics.TBT} CLS ${metrics.CLS} ${metrics.bytes}` +
    (failing.length ? '\n     audits under 0.9: ' + failing.join(', ') : '') +
    Object.entries(detail).map(([k, v]) => '\n     ' + k + ': ' + v.join('\n        ')).join(''));
}
await chrome.kill();
server.close();
console.log(`\nLighthouse: ${PAGES.length - fails} passed, ${fails} failed (minimum ${MIN})`);
if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify(results, null, 1));
process.exit(fails ? 1 : 0);
