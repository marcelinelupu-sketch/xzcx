/* frogsdream rng.js: seeded random numbers so a seed always rebuilds the same sheets.
   FD.rng.create(seed) -> rand() in [0,1); FD.rng.shuffle(arr, rand) -> new shuffled array. */
(function (FD) {
  'use strict';
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      var t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function hash(str) {
    str = String(str);
    var h1 = 0xdeadbeef, h2 = 0x41c6ce57;
    for (var i = 0; i < str.length; i++) {
      var c = str.charCodeAt(i);
      h1 = Math.imul(h1 ^ c, 2654435761);
      h2 = Math.imul(h2 ^ c, 1597334677);
    }
    h1 = Math.imul(h1 ^ h1 >>> 16, 2246822507) ^ Math.imul(h2 ^ h2 >>> 13, 3266489909);
    return h1 >>> 0;
  }
  function toSeed(v) {
    if (typeof v === 'number' && isFinite(v)) return v >>> 0;
    if (/^\d+$/.test(String(v || ''))) return parseInt(v, 10) >>> 0;
    return hash(v || '');
  }
  function newSeed() {
    try { return crypto.getRandomValues(new Uint32Array(1))[0] >>> 0; } catch (e) { return (Math.random() * 4294967296) >>> 0; }
  }
  function create(seed) {
    var s = toSeed(seed), r = mulberry32(s);
    r.seed = s;
    return r;
  }
  function shuffle(arr, rand) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rand() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function int(rand, lo, hi) { return lo + Math.floor(rand() * (hi - lo + 1)); }
  function pick(arr, rand) { return arr[Math.floor(rand() * arr.length)]; }
  /* derive(seed, 'puzzle', 3): an independent sub-seed, so puzzle 3 never depends on puzzle 2 */
  function derive() { return hash(Array.prototype.join.call(arguments, ':')); }
  FD.rng = { mulberry32: mulberry32, create: create, hash: hash, toSeed: toSeed, newSeed: newSeed, shuffle: shuffle, int: int, pick: pick, derive: derive };
})(window.FD = window.FD || {});
