// Word search placement test (SPEC 3.2): for every themed word search list that exists in
// source/content (plus the main tool page sample list), at the page's default settings,
// generate 200 seeds and assert that every word is placed, readable in the grid, in an allowed
// direction, and that filler letters never spell a blocked word.
// Run: node source/tests/test_wordsearch.mjs [--seeds N]   (exit code 1 on any failure)
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const SRC = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const argi = process.argv.indexOf('--seeds');
const SEEDS = argi > 0 ? parseInt(process.argv[argi + 1], 10) : 200;

// Load the real rng.js and wordsearch.js in a sandbox and capture the registered plugin.
let def = null;
const sandbox = { window: {}, console };
sandbox.window.FD = { tool: { register: (d) => { def = d; } } };
vm.createContext(sandbox);
for (const f of ['rng.js', 'wordsearch.js']) {
  vm.runInContext(fs.readFileSync(path.join(SRC, 'static/assets/js', f), 'utf8'), sandbox, { filename: f });
}
const FD = sandbox.window.FD;
if (!def || def.id !== 'wordsearch') { console.error('wordsearch.js did not register'); process.exit(1); }

// Form defaults, read from the controls partial so the test follows the real UI.
const partial = fs.readFileSync(path.join(SRC, 'tools/wordsearch.controls.html'), 'utf8');
const formDefaults = {
  size: parseInt(/name="size">[\s\S]*?value="(\d+)" selected/.exec(partial)[1], 10),
  difficulty: /name="difficulty">[\s\S]*?value="(\w+)" selected/.exec(partial)[1],
  case: 'upper', puzzles: 1,
  showList: /name="showList" checked/.test(partial), key: /name="key" checked/.test(partial),
};

const DIRS = { easy: ['0,1', '1,0'], medium: ['0,1', '1,0', '1,1', '-1,1'] };
const AZ = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const BLOCK = ['ASS', 'FUCK', 'SHIT', 'CUNT', 'DICK', 'COCK', 'TIT', 'PISS', 'FAG', 'SEX', 'PORN', 'SLUT', 'WHORE', 'BITCH', 'NAZI', 'RAPE', 'NIGG'];

function itemLine(it) {
  if (typeof it === 'string') return it;
  if (it && it.square) return it.square + (it.call ? ' | ' + it.call : '');
  if (it && it.text) return it.text;
  return String(it);
}

function lists() {
  const out = [];
  const dir = path.join(SRC, 'content/themes/word-search');
  if (fs.existsSync(dir)) {
    for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.json')).sort()) {
      const d = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
      out.push({ name: 'word-search/' + f.replace(/\.json$/, ''), lines: (d.items || []).map(itemLine), options: d.defaultOptions || {} });
    }
  }
  const tool = path.join(SRC, 'content/tools/word-search-maker.json');
  if (fs.existsSync(tool)) {
    const d = JSON.parse(fs.readFileSync(tool, 'utf8'));
    out.push({ name: 'tools/word-search-maker', lines: (d.items || []).map(itemLine), options: d.defaultOptions || {} });
  }
  return out;
}

function run(lines, options, seed) {
  const state = { title: 'Test', words: lines, options: { ...formDefaults, ...options }, paper: 'letter', ink: false, stamp: true, seed };
  const ctx = {
    state, seed, rand: FD.rng.create(seed), warnings: [], errors: [],
    warn(m) { ctx.warnings.push(m); }, error(m) { ctx.errors.push(m); },
    sub(...k) { return FD.rng.create(FD.rng.derive(seed, ...k)); },
  };
  const items = def.parse(lines, state, ctx);
  ctx.items = items;
  if (ctx.errors.length) return { ctx, items, model: null };
  return { ctx, items, model: def.build(state, ctx) };
}

function checkModel(name, seed, items, model, options, fails) {
  const o = { ...formDefaults, ...options };
  const allowed = DIRS[o.difficulty] || null;
  const want = Math.max(1, Math.min(10, o.puzzles || 1));
  const bad = (m) => { fails.push(`${name} seed ${seed}: ${m}`); };
  if (model.puzzles.length !== want) return bad(`expected ${want} puzzles, got ${model.puzzles.length}`);
  for (const pz of model.puzzles) {
    const n = pz.n, g = pz.grid;
    if (g.length !== n * n || !/^[A-Z]+$/.test(g)) bad(`grid is not ${n}x${n} A-Z`);
    if (n < Math.max(10, Math.min(20, o.size)) || n > 20) bad(`grid size ${n} out of range`);
    if (pz.at.length !== items.length) bad(`placed ${pz.at.length} of ${items.length} words`);
    const used = new Set();
    const placed = new Set(pz.at.map((p) => p.w));
    for (const it of items) if (!placed.has(it.text)) bad(`word "${it.text}" missing`);
    for (const p of pz.at) {
      const it = items.find((x) => x.text === p.w);
      if (allowed && !allowed.includes(p.dr + ',' + p.dc)) bad(`"${p.w}" uses direction ${p.dr},${p.dc} not allowed on ${o.difficulty}`);
      let s = '';
      for (let i = 0; i < p.len; i++) {
        const r = p.r + p.dr * i, c = p.c + p.dc * i;
        if (r < 0 || r >= n || c < 0 || c >= n) { bad(`"${p.w}" runs off the grid`); break; }
        s += g[r * n + c]; used.add(r * n + c);
      }
      if (it && s !== it.letters) bad(`"${p.w}" reads "${s}" in the grid`);
    }
    // Each list word can be found only once (a copy inside a longer list word, like EGG in EGGS, is allowed).
    const D8 = [[0, 1], [1, 0], [1, 1], [-1, 1], [0, -1], [-1, 0], [-1, -1], [1, -1]];
    const paths = pz.at.map((p) => Array.from({ length: p.len }, (_, i) => (p.r + p.dr * i) * n + p.c + p.dc * i));
    pz.at.forEach((p, j) => {
      const it = items.find((x) => x.text === p.w); if (!it) return;
      const t = it.letters;
      for (let k = 0; k < g.length; k++) for (const [dr, dc] of D8) {
        const cells = [];
        for (let i = 0; i < t.length; i++) {
          const r = Math.floor(k / n) + dr * i, c = k % n + dc * i;
          if (r < 0 || r >= n || c < 0 || c >= n || g[r * n + c] !== t[i]) break;
          cells.push(r * n + c);
        }
        if (cells.length !== t.length) continue;
        const ok = paths.some((q, z) => (z === j || q.length > t.length) && cells.every((x) => q.includes(x)));
        if (!ok) bad(`"${p.w}" can be found twice in the grid`);
      }
    });
    // Blocked words must not appear through filler cells in any direction.
    for (const t of BLOCK) {
      for (let k = 0; k < g.length; k++) {
        for (const [dr, dc] of [[0, 1], [1, 0], [1, 1], [-1, 1], [0, -1], [-1, 0], [-1, -1], [1, -1]]) {
          const r0 = Math.floor(k / n), c0 = k % n, cells = [];
          let ok = true;
          for (let i = 0; i < t.length && ok; i++) {
            const r = r0 + dr * i, c = c0 + dc * i;
            if (r < 0 || r >= n || c < 0 || c >= n || g[r * n + c] !== t[i]) ok = false; else cells.push(r * n + c);
          }
          if (ok && cells.some((q) => !used.has(q))) bad(`filler spells a blocked word at cell ${k}`);
        }
      }
    }
  }
}

const fails = [];
let total = 0, grown = 0, maxMs = 0;
const all = lists();
if (!all.length) { console.error('No word search lists found in source/content'); process.exit(1); }
for (const L of all) {
  let listGrown = 0, sizes = new Set();
  const t0 = Date.now();
  for (let s = 1; s <= SEEDS; s++) {
    const seed = FD.rng.derive('ws-test', s) >>> 0;
    const a = performance.now();
    const { ctx, items, model } = run(L.lines, L.options, seed);
    maxMs = Math.max(maxMs, performance.now() - a);
    total++;
    if (!model) { fails.push(`${L.name} seed ${seed}: parse error: ${ctx.errors.join(' ')}`); continue; }
    if (items.length !== L.lines.length) fails.push(`${L.name}: parse kept ${items.length} of ${L.lines.length} lines (${ctx.warnings.join(' ')})`);
    checkModel(L.name, seed, items, model, L.options, fails);
    model.puzzles.forEach((pz) => sizes.add(pz.n));
    if (ctx.warnings.some((w) => /grew/.test(w))) listGrown++;
    if (s === 1) {
      const again = run(L.lines, L.options, seed).model;
      if (JSON.stringify(again) !== JSON.stringify(model)) fails.push(`${L.name}: same seed gave a different model`);
    }
  }
  grown += listGrown;
  const o = { ...formDefaults, ...L.options };
  console.log(`${L.name.padEnd(40)} ${String(L.lines.length).padStart(2)} words  size ${o.size} ${o.difficulty.padEnd(6)} grids ${[...sizes].sort((a, b) => a - b).join('/')}  grew ${listGrown}/${SEEDS}  ${Date.now() - t0} ms`);
}

// Edge cases the spec calls out.
{
  const r = run(['Supercalifragilisticexpialidocious', 'Cat'], {}, 7);
  if (!r.ctx.errors.length) fails.push('edge: a word longer than 20 letters should be an error');
  const r2 = run(['Metamorphosis', 'Frog', 'Pond'], { size: 10 }, 7);
  if (!r2.model || r2.model.puzzles[0].n !== 13) fails.push('edge: a 13-letter word in a 10 grid should grow the grid to 13');
  const many = Array.from({ length: 40 }, (_, i) => 'PO' + AZ[i % 26] + AZ[(i * 7) % 26] + AZ[(i * 3) % 26] + 'ND');
  const r3 = run(many, { size: 10, difficulty: 'hard', puzzles: 3 }, 11);
  if (r3.model) checkModel('edge: 40 seven-letter words', 11, r3.items, r3.model, { size: 10, difficulty: 'hard', puzzles: 3 }, fails);
  else fails.push('edge: 40 words should still build');
  const r4 = run(['Lily pad', "Mother's Day", 'Eggs', 'eggs'], {}, 3);
  if (r4.items.length !== 3 || r4.items[1].letters !== 'MOTHERSDAY') fails.push('edge: spaces/punctuation/duplicates not handled');
}

console.log(`\n${all.length} lists x ${SEEDS} seeds = ${total} runs, slowest build ${maxMs.toFixed(1)} ms, ${grown} runs grew the grid.`);
if (fails.length) {
  console.log(`FAIL: ${fails.length} problems`);
  fails.slice(0, 40).forEach((f) => console.log('  ' + f));
  process.exit(1);
}
console.log('PASS: every word placed in every run.');
