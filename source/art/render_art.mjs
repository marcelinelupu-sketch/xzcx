// Rasterizes the mascot SVGs to transparent PNGs in source/art/png/ for build.py
// (OG images, favicon.ico, apple-touch-icon, logo.png). Run after make_mascots.py:
//   node source/art/render_art.mjs
import { createRequire } from 'module';
import { readFileSync, mkdirSync, readdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const here = dirname(fileURLToPath(import.meta.url));
const img = join(here, '..', 'static', 'assets', 'img');
const out = join(here, 'png');
mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage();
const jobs = readdirSync(img).filter(f => f.startsWith('frog-') && f.endsWith('.svg')).map(f => [join(img, f), f.replace('.svg', '.png'), 800, 800]);
jobs.push([join(here, '..', 'static', 'favicon.svg'), 'favicon.png', 512, 410]);
for (const [src, name, w, h] of jobs) {
  const svg = readFileSync(src, 'utf8');
  await page.setViewportSize({ width: w, height: h });
  await page.setContent(`<html><body style="margin:0;background:transparent">${svg.replace('<svg ', `<svg width="${w}" height="${h}" `)}</body></html>`);
  await page.locator('svg').screenshot({ path: join(out, name), omitBackground: true });
  console.log('wrote', name);
}
await browser.close();
