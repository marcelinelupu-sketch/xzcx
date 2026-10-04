/* Bingo uniqueness: for every mode, grid and every built bingo theme list, 30 cards per generation are all
   different, cards hold valid values (75-ball column ranges, 1 to 30, words from the list without repeats),
   and the same seed rebuilds the same cards. Run: node source/tests/test_bingo_unique.cjs [seeds] */
const assert = require('assert'), fs = require('fs'), path = require('path');
const FD = require('./load-bingo.cjs')();
const def = FD.bingo.def;
const SEEDS = +(process.argv[2] || 200);

function run(words, options, seed, paper) {
  const state = { title: 'Test', words, options, paper: paper || 'letter', seed };
  const c = { warnings: [], errors: [], rand: FD.rng.create(seed), warn: m => c.warnings.push(m), error: m => c.errors.push(m),
    sub: (...k) => FD.rng.create(FD.rng.derive(seed, ...k)) };
  c.items = def.parse(words, state, c);
  if (c.errors.length) return { errors: c.errors };
  return { m: def.build(state, c), warnings: c.warnings, errors: [] };
}
function cardsOf(m) { return m.pages.flatMap(p => p.cards || []); }
function texts(card) { return card.cells.map(x => (x.free ? '*' : x.t)); }

/* theme lists from the content folder plus a few synthetic lists */
const dir = path.join(__dirname, '..', 'content', 'themes', 'bingo');
const lists = {};
for (const f of fs.existsSync(dir) ? fs.readdirSync(dir) : []) {
  if (!f.endsWith('.json')) continue;
  const d = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
  if ((d.items || []).length) lists[f] = { words: d.items.map(i => (typeof i === 'string' ? i : i.square + ' | ' + i.call)), opts: d.defaultOptions || {} };
}
const gen = n => Array.from({ length: n }, (_, i) => 'Word ' + (i + 1));
lists['synthetic-24'] = { words: gen(24), opts: {} };
lists['synthetic-75'] = { words: gen(75), opts: {} };
lists['addition'] = { words: Array.from({ length: 40 }, (_, i) => (i % 19 + 2) + ' | ' + (i % 9 + 1) + ' + ' + (i % 19 + 1 - (i % 9))), opts: {} };

let checked = 0;
const t0 = Date.now();
for (let s = 1; s <= SEEDS; s++) {
  const seed = FD.rng.derive('uniq', s);
  /* word mode, every list, every grid, free on and off */
  for (const [name, L] of Object.entries(lists)) {
    for (const grid of [3, 4, 5]) {
      for (const free of [true, false]) {
        const r = run(L.words, Object.assign({}, L.opts, { mode: 'word', grid, free, cards: 30, perPage: 4, caller: s % 10 === 0 }), seed);
        const need = grid * grid - (free && grid % 2 ? 1 : 0), uniq = new Set(L.words.map(w => w.split('|')[0].trim().toLowerCase())).size;
        if (uniq < need) { assert.ok(r.errors.length && /Allow repeats/.test(r.errors[0]), name + ': short list must show the friendly error'); continue; }
        assert.strictEqual(r.errors.length, 0, name + ' ' + grid + ': ' + r.errors.join(' '));
        const cards = cardsOf(r.m), keys = new Set(cards.map(c => texts(c).join('\u0001')));
        assert.strictEqual(cards.length, 30);
        assert.strictEqual(keys.size, 30, name + ' grid ' + grid + ' seed ' + seed + ': duplicate card');
        for (const c of cards) {
          const t = texts(c), vals = t.filter(x => x !== '*');
          assert.strictEqual(t.length, grid * grid);
          assert.strictEqual(new Set(vals.map(v => v.toLowerCase())).size, vals.length, name + ': repeated word on one card');
          if (free && grid % 2) assert.strictEqual(t[(grid * grid - 1) / 2], '*', 'free center');
          else assert.ok(!t.includes('*'), 'no free square on even grids or when off');
        }
        checked += 30;
      }
    }
  }
  /* number modes */
  for (const [mode, grid] of [['75', 5], ['30', 3], ['30', 4], ['30', 5]]) {
    const r = run([], { mode, grid, free: true, cards: 30, perPage: 2, caller: true }, seed);
    assert.strictEqual(r.errors.length, 0);
    const cards = cardsOf(r.m);
    assert.strictEqual(new Set(cards.map(c => texts(c).join(','))).size, 30, mode + ' duplicate card');
    for (const c of cards) {
      const t = texts(c);
      t.forEach((v, i) => {
        if (v === '*') { assert.strictEqual(i, (grid * grid - 1) / 2); return; }
        const n = +v;
        if (mode === '75') { const col = i % 5; assert.ok(n >= col * 15 + 1 && n <= col * 15 + 15, '75-ball column range'); }
        else assert.ok(n >= 1 && n <= 30);
      });
      assert.strictEqual(new Set(t).size, t.length, 'no repeated numbers');
    }
    checked += 30;
  }
}
/* determinism */
const a = run(lists['synthetic-75'].words, { mode: 'word', grid: 5, cards: 30 }, 12345), b = run(lists['synthetic-75'].words, { mode: 'word', grid: 5, cards: 30 }, 12345);
assert.strictEqual(JSON.stringify(a.m), JSON.stringify(b.m), 'same seed, same cards');
/* short list: friendly error without repeats, works with repeats */
const short = run(gen(10), { mode: 'word', grid: 5, cards: 5 }, 1);
assert.ok(short.errors.length && /needs 24/.test(short.errors[0]), 'short list error');
const rep = run(gen(10), { mode: 'word', grid: 5, cards: 30, repeats: true }, 1);
assert.strictEqual(rep.errors.length, 0);
assert.strictEqual(new Set(cardsOf(rep.m).map(c => texts(c).join())).size, 30, 'repeats still unique');
/* addition facts: squares show answers, caller sheet shows problems */
const add = run(['12 | 7 + 5', '10 | 6 + 4', '9 | 4 + 5', '8 | 3 + 5', '7 | 2 + 5', '6 | 1 + 5', '5 | 2 + 3', '4 | 1 + 3', '3 | 1 + 2'], { mode: 'word', grid: 3, free: true, cards: 3, caller: true }, 9);
assert.ok(cardsOf(add.m)[0].cells.every(c => c.free || /^\d+$/.test(c.t)), 'squares are answers');
assert.ok(add.m.caller.order.every(x => /\+/.test(x)), 'call order shows problems');
console.log('bingo uniqueness: ' + checked + ' cards checked over ' + SEEDS + ' seeds and ' + Object.keys(lists).length + ' lists, all unique (' + (Date.now() - t0) + ' ms)');
