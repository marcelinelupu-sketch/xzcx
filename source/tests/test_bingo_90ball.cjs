/* 90-ball strip validity: 1000 random strips. Each strip is 6 tickets of 3 x 9, every row has 5 numbers,
   every ticket has 15, column ranges 1-9, 10-19 ... 80-90, each ticket column holds 1 to 3 numbers sorted
   top to bottom, and the strip covers 1 to 90 exactly once. Run: node source/tests/test_bingo_90ball.cjs */
const assert = require('assert');
const FD = require('./load-bingo.cjs')();
const N = +(process.argv[2] || 1000);
const lo = c => (c === 0 ? 1 : c * 10), hi = c => (c === 8 ? 90 : c * 10 + 9);

function check(strip, label) {
  assert.strictEqual(strip.length, 6, label + ': 6 tickets');
  const seen = new Array(91).fill(0);
  strip.forEach((tk, t) => {
    const L = label + ' ticket ' + (t + 1);
    assert.strictEqual(tk.length, 3, L + ': 3 rows');
    let total = 0;
    tk.forEach((row, r) => {
      assert.strictEqual(row.length, 9, L + ': 9 columns');
      const filled = row.filter(Boolean).length;
      assert.strictEqual(filled, 5, L + ' row ' + (r + 1) + ': 5 numbers, got ' + filled);
      total += filled;
      row.forEach((v, c) => {
        if (!v) return;
        assert.ok(Number.isInteger(v) && v >= lo(c) && v <= hi(c), L + ': ' + v + ' outside column ' + c + ' range');
        seen[v]++;
      });
    });
    assert.strictEqual(total, 15, L + ': 15 numbers');
    for (let c = 0; c < 9; c++) {
      const col = tk.map(row => row[c]).filter(Boolean);
      assert.ok(col.length >= 1 && col.length <= 3, L + ' column ' + c + ': 1 to 3 numbers, got ' + col.length);
      for (let i = 1; i < col.length; i++) assert.ok(col[i] > col[i - 1], L + ' column ' + c + ': sorted top to bottom');
    }
  });
  for (let n = 1; n <= 90; n++) assert.strictEqual(seen[n], 1, label + ': number ' + n + ' appears ' + seen[n] + ' times');
}

const keys = new Set();
const t0 = Date.now();
for (let i = 0; i < N; i++) {
  const seed = FD.rng.derive('strip-test', i);
  const strip = FD.bingo.strip90(FD.rng.create(seed));
  check(strip, 'strip ' + i + ' (seed ' + seed + ')');
  keys.add(JSON.stringify(strip));
  /* determinism: the same seed gives the same strip */
  if (i < 50) assert.strictEqual(JSON.stringify(FD.bingo.strip90(FD.rng.create(seed))), JSON.stringify(strip), 'seed ' + seed + ' is not deterministic');
}
assert.strictEqual(keys.size, N, 'all strips different');

/* the full tool path: build() in 90-ball mode for 30 tickets gives 5 valid strips */
const def = FD.bingo.def;
function ctxFor(state) {
  const c = { warnings: [], errors: [], rand: FD.rng.create(state.seed), warn: m => c.warnings.push(m), error: m => c.errors.push(m),
    sub: (...k) => FD.rng.create(FD.rng.derive(state.seed, ...k)) };
  return c;
}
for (let s = 1; s <= 50; s++) {
  const state = { title: 'T', words: [], options: { mode: '90', cards: 30, caller: true }, paper: s % 2 ? 'letter' : 'a4', seed: s * 7919 };
  const ctx = ctxFor(state);
  ctx.items = def.parse(state.words, state, ctx);
  assert.strictEqual(ctx.errors.length, 0);
  const m = def.build(state, ctx);
  assert.strictEqual(m.pages.length, 5);
  m.pages.forEach((p, i) => check(p.tickets, 'build seed ' + state.seed + ' strip ' + i));
  assert.strictEqual(m.caller.check.length, 90);
  assert.strictEqual(JSON.stringify([...m.caller.order].sort((a, b) => a - b)), JSON.stringify([...m.caller.check].sort((a, b) => a - b)));
}
console.log('90-ball strips: ' + N + ' random strips valid, 50 tool builds valid (' + (Date.now() - t0) + ' ms)');
