/* Shared helpers for the Frog's Dream browser QA scripts.
   Serves a built site folder over HTTP and launches headless Chromium (Playwright). */
const http = require('http'), fs = require('fs'), path = require('path'), zlib = require('zlib');
const PW = process.env.PW_PATH || '/opt/node22/lib/node_modules/playwright';
const { chromium } = require(PW);

const TYPES = {
  '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.ttf': 'font/ttf', '.woff2': 'font/woff2',
  '.txt': 'text/plain', '.xml': 'application/xml', '.webmanifest': 'application/manifest+json',
};

function serve(root) {
  root = path.resolve(root);
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0].split('#')[0]);
    if (p.endsWith('/')) p += 'index.html';
    const f = path.join(root, p);
    if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) {
      res.writeHead(404, { 'content-type': 'text/html' });
      return fs.createReadStream(path.join(root, '404.html')).pipe(res);
    }
    const type = TYPES[path.extname(f)] || 'application/octet-stream';
    if (/text|javascript|json|svg|xml|manifest/.test(type) && /gzip/.test(req.headers['accept-encoding'] || '')) {
      res.writeHead(200, { 'content-type': type, 'content-encoding': 'gzip', 'cache-control': 'max-age=3600' });
      return res.end(zlib.gzipSync(fs.readFileSync(f)));
    }
    res.writeHead(200, { 'content-type': type, 'cache-control': 'max-age=3600' });
    fs.createReadStream(f).pipe(res);
  });
  return new Promise(r => server.listen(0, '127.0.0.1', () => r({ server, base: 'http://127.0.0.1:' + server.address().port })));
}

/* Locate a local jsPDF 2.5.1 build for sandboxes without internet. */
function findJsPDF() {
  const cands = [process.env.JSPDF, path.join(__dirname, 'vendor', 'jspdf.umd.min.js')].filter(Boolean);
  return cands.find(f => fs.existsSync(f)) || null;
}

function launch() {
  return chromium.launch();
}

function reporter() {
  const results = [];
  return {
    results,
    ok(cond, msg) { results.push({ ok: !!cond, msg }); console.log((cond ? 'ok   ' : 'FAIL ') + msg); return !!cond; },
    get fails() { return results.filter(r => !r.ok).length; },
  };
}

module.exports = { serve, findJsPDF, launch, reporter, chromium };
