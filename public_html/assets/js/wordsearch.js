/* frogsdream word search maker (SPEC 3.2, TOOL-CONTRACT.md).
   Options (names in tools/wordsearch.controls.html): size 10-20, difficulty easy|medium|hard,
   case upper|lower, showList, puzzles 1-10, key.
   Placement: longest words first, randomized backtracking with up to 500 attempts per word.
   If a grid is impossible the grid grows by 1 and placement starts again; a word is never dropped.
   Filler letters are random A-Z, re-rolled wherever they spell a blocked word or a second copy of a list word. */
(function (FD) {
  'use strict';
  var MIN = 10, MAX = 20, MAX_WORDS = 40, ATTEMPTS = 500, BUDGET = 12000;
  var AREA = { letter: { w: 7.7, h: 9.9 }, a4: { w: 7.47, h: 10.59 } }; /* inches inside margins, minus credit band */
  var ALL = [[0, 1], [1, 0], [1, 1], [-1, 1], [0, -1], [-1, 0], [-1, -1], [1, -1]]; /* [dr, dc] */
  var DIRS = { easy: ALL.slice(0, 2), medium: ALL.slice(0, 4), hard: ALL };
  var HOW = {
    easy: 'Words go across and down.',
    medium: 'Words go across, down and diagonally.',
    hard: 'Words hide in every direction, even backwards.'
  };
  var AZ = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  /* Small blocklist of rude words, stored in ROT13 so the source stays tidy. Only filler letters are re-rolled. */
  var BLOCK = 'NFF SHPX SHX SPX FUVG PHAG QVPX PBPX GVG CVFF PENC SNT FRK CBEA FYHG JUBER OVGPU QNZA ANMV ENCR CRAVF OBBO AVTT XXX PHZ JNAX GJNG WVM UBR'
    .split(' ').map(function (w) { return w.replace(/[A-Z]/g, function (c) { return AZ[(AZ.indexOf(c) + 13) % 26]; }); });

  function lettersOf(s) { return String(s).normalize('NFD').replace(/[^A-Za-z]/g, '').toUpperCase(); }
  function fmt(s, o) { return o.case === 'lower' ? s.toLowerCase() : s.toUpperCase(); }
  function clampSize(v) { v = parseInt(v, 10); return isNaN(v) ? 12 : Math.max(MIN, Math.min(MAX, v)); }

  /* Every in-bounds start for a word of length L, grouped by direction, then interleaved in a random order
     so each allowed direction is equally likely even though diagonals have fewer starts. */
  function candidates(L, n, dirs, rand) {
    var lists = dirs.map(function (d) {
      var out = [];
      for (var r = 0; r < n; r++) {
        var re = r + d[0] * (L - 1);
        if (re < 0 || re >= n) continue;
        for (var c = 0; c < n; c++) {
          var ce = c + d[1] * (L - 1);
          if (ce >= 0 && ce < n) out.push([r, c, d[0], d[1]]);
        }
      }
      return FD.rng.shuffle(out, rand);
    }), order = [], live = lists.filter(function (l) { return l.length; });
    while (live.length) {
      var j = Math.floor(rand() * live.length);
      order.push(live[j].pop());
      if (!live[j].length) live.splice(j, 1);
    }
    return order;
  }

  /* Try to place every word in an n x n grid. Returns placements or null when the budget runs out. */
  function place(words, n, dirs, rand) {
    var g = new Array(n * n).fill(''), cnt = new Array(n * n).fill(0), out = [], steps = 0;
    function fits(w, p) {
      var shared = 0;
      for (var i = 0; i < w.length; i++) {
        var k = (p[0] + p[2] * i) * n + p[1] + p[3] * i;
        if (g[k]) { if (g[k] !== w[i]) return false; shared++; }
      }
      return shared < w.length; /* never hide a word completely inside another */
    }
    function put(w, p, add) {
      for (var i = 0; i < w.length; i++) {
        var k = (p[0] + p[2] * i) * n + p[1] + p[3] * i;
        cnt[k] += add;
        g[k] = cnt[k] ? w[i] : '';
      }
    }
    var paths = [];
    function cellsOf(L, p) { var a = []; for (var i = 0; i < L; i++) a.push((p[0] + p[2] * i) * n + p[1] + p[3] * i); return a; }
    function within(cells, path) { for (var i = 0; i < cells.length; i++) if (path.indexOf(cells[i]) < 0) return false; return true; }
    /* After placing a word, no list word may show up a second time using the new letters
       (copies inside a longer list word, like EGG in EGGS, cannot be avoided and are allowed). */
    function inherentAll(cells, j, L) {
      for (var z = 0; z < paths.length; z++) if ((z === j || paths[z].length > L) && within(cells, paths[z])) return true;
      return false;
    }
    function clean(fresh) {
      var me = paths.length - 1, own = findAll(g, n, words[me].letters); /* the new word anywhere in the grid */
      for (var h = 0; h < own.length; h++) if (!inherentAll(own[h], me, own[h].length)) return false;
      for (var j = 0; j < paths.length; j++) {
        var t = words[j].letters, L = t.length;
        for (var f = 0; f < fresh.length; f++) {
          var k = fresh[f], r = Math.floor(k / n), c = k % n;
          for (var d = 0; d < 8; d++) {
            var dr = ALL[d][0], dc = ALL[d][1];
            for (var i = 0; i < L; i++) {
              if (t[i] !== g[k]) continue;
              var r0 = r - dr * i, c0 = c - dc * i, r1 = r0 + dr * (L - 1), c1 = c0 + dc * (L - 1);
              if (r0 < 0 || r0 >= n || c0 < 0 || c0 >= n || r1 < 0 || r1 >= n || c1 < 0 || c1 >= n) continue;
              var cells = [], ok = true;
              for (var q = 0; q < L && ok; q++) { var x = (r0 + dr * q) * n + c0 + dc * q; if (g[x] !== t[q]) ok = false; else cells.push(x); }
              if (!ok) continue;
              if (!inherentAll(cells, j, L)) return false;
            }
          }
        }
      }
      return true;
    }
    function rec(i) {
      if (i === words.length) return true;
      var w = words[i].letters, cand = candidates(w.length, n, dirs, rand), tries = 0;
      for (var j = 0; j < cand.length && tries < ATTEMPTS; j++) {
        if (++steps > BUDGET) return false;
        tries++;
        if (!fits(w, cand[j])) continue;
        put(w, cand[j], 1);
        var path = cellsOf(w.length, cand[j]);
        paths.push(path);
        if (!clean(path)) { paths.pop(); put(w, cand[j], -1); continue; }
        out.push(cand[j]);
        if (rec(i + 1)) return true;
        out.pop();
        paths.pop();
        put(w, cand[j], -1);
        if (steps > BUDGET) return false;
      }
      return false;
    }
    if (!rec(0)) return null;
    return { grid: g, used: cnt.map(Boolean), at: out };
  }

  /* All runs of `t` in the grid in any of the 8 directions, as arrays of cell indexes. */
  function findAll(g, n, t) {
    var hits = [];
    for (var k = 0; k < g.length; k++) {
      if (g[k] !== t[0]) continue;
      var r = Math.floor(k / n), c = k % n;
      for (var d = 0; d < 8; d++) {
        var dr = ALL[d][0], dc = ALL[d][1], er = r + dr * (t.length - 1), ec = c + dc * (t.length - 1), ok = true, cells = [k];
        if (er < 0 || er >= n || ec < 0 || ec >= n) continue;
        for (var i = 1; i < t.length && ok; i++) {
          var q = (r + dr * i) * n + c + dc * i;
          if (g[q] !== t[i]) ok = false; else cells.push(q);
        }
        if (ok) hits.push(cells);
      }
    }
    return hits;
  }

  /* Fill empty cells, then re-roll filler letters that spell a blocked word or an extra copy of a list word. */
  function fill(res, words, n, rand) {
    var g = res.grid, used = res.used;
    function roll(k) { g[k] = AZ[Math.floor(rand() * 26)]; }
    for (var k = 0; k < g.length; k++) if (!used[k]) roll(k);
    var own = {};
    words.forEach(function (w, i) {
      var p = res.at[i], a = [];
      for (var j = 0; j < w.letters.length; j++) a.push((p[0] + p[2] * j) * n + p[1] + p[3] * j);
      own[a.join(',')] = own[a.slice().reverse().join(',')] = 1;
    });
    for (var round = 0; round < 80; round++) {
      var bad = [];
      BLOCK.concat(words.map(function (w) { return w.letters; })).forEach(function (t, ti) {
        findAll(g, n, t).forEach(function (cells) {
          if (ti >= BLOCK.length && own[cells.join(',')]) return;
          for (var i = 0; i < cells.length; i++) if (!used[cells[i]]) { bad.push(cells[i]); return; }
        });
      });
      if (!bad.length) return true;
      bad.forEach(roll);
    }
    return false;
  }

  /* Build one puzzle: start at the chosen size (or the longest word), grow by 1 until everything fits. */
  function makePuzzle(words, size, dirs, ctx, index) {
    var longest = Math.max.apply(null, words.map(function (w) { return w.letters.length; }));
    var sorted = words.slice().sort(function (a, b) { return b.letters.length - a.letters.length; });
    for (var n = Math.max(size, longest); n <= MAX; n++) {
      for (var t = 0; t < (n === MAX ? 6 : 2); t++) {
        var rand = ctx.sub('puzzle', index, n, t);
        var order = FD.rng.shuffle(sorted, rand).sort(function (a, b) { return b.letters.length - a.letters.length; });
        var res = place(order, n, dirs, rand);
        if (!res) continue;
        fill(res, order, n, ctx.sub('fill', index, n, t));
        return {
          index: index, n: n, grid: res.grid.join(''),
          at: order.map(function (w, i) { var p = res.at[i]; return { w: w.text, r: p[0], c: p[1], dr: p[2], dc: p[3], len: w.letters.length }; })
        };
      }
    }
    return null;
  }

  /* ---------- geometry shared by preview and PDF (inches) ---------- */
  function listGeom(words, o) {
    if (!o.showList) return null;
    var longest = Math.max.apply(null, words.map(function (w) { return w.length; }));
    var cols = longest > 16 ? 2 : longest > 11 ? 3 : 4, rows = Math.ceil(words.length / cols), small = rows > 6;
    var f = small ? 10 : 11.5, rh = f * 1.42 / 72;
    return { cols: cols, rows: rows, f: f, rh: rh, h: 0.5 + rows * rh };
  }

  function svg(pz, o, key) {
    var n = pz.n, s = '<svg viewBox="-0.15 -0.15 ' + (n + 0.3) + ' ' + (n + 0.3) + '" preserveAspectRatio="xMidYMin meet" role="img" aria-label="' +
      (key ? 'Answer key grid' : 'Word search grid, ' + n + ' by ' + n) + '"><rect class="ws-bd" x="-0.1" y="-0.1" width="' + (n + 0.2) + '" height="' + (n + 0.2) + '" rx="0.35"/>';
    if (key) pz.at.forEach(function (p) {
      var x = p.c + 0.5, y = p.r + 0.5, len = Math.sqrt(p.dr * p.dr + p.dc * p.dc) * (p.len - 1);
      var ang = Math.atan2(p.dr, p.dc) * 180 / Math.PI;
      s += '<rect class="ws-hl" x="' + (x - 0.42).toFixed(2) + '" y="' + (y - 0.4).toFixed(2) + '" width="' + (len + 0.84).toFixed(2) +
        '" height="0.8" rx="0.4" transform="rotate(' + ang + ' ' + x + ' ' + y + ')"/>';
    });
    s += '<g class="ws-l">';
    for (var k = 0; k < pz.grid.length; k++) {
      s += '<text x="' + (k % n + 0.5) + '" y="' + (Math.floor(k / n) + 0.71) + '">' + fmt(pz.grid[k], o) + '</text>';
    }
    return s + '</g></svg>';
  }

  function keySub(m, group) {
    if (!m.multi) return '';
    var a = group[0].index + 1, z = group[group.length - 1].index + 1;
    return a === z ? 'Puzzle ' + a : 'Puzzles ' + a + ' to ' + z;
  }

  function sortedWords(pz) {
    return pz.at.map(function (p) { return p.w; }).sort(function (a, b) { return a.localeCompare(b); });
  }

  FD.tool.register({
    id: 'wordsearch',
    noun: 'words',
    hint: 'One word or short phrase per line. Spaces and punctuation are skipped in the grid.',

    parse: function (lines, state, ctx) {
      var items = [], seen = {}, skipped = [], dup = [];
      lines.forEach(function (line) {
        var text = line.split('|')[0].trim(), L = lettersOf(text);
        if (!text) return;
        if (L.length < 2) { skipped.push(text); return; }
        if (seen[L]) { dup.push(text); return; }
        seen[L] = 1;
        items.push({ text: text, letters: L });
      });
      if (skipped.length) ctx.warn('Skipped ' + skipped.map(function (s) { return '"' + s + '"'; }).join(', ') + ' (needs 2 or more letters).');
      if (dup.length) ctx.warn('Skipped ' + dup.map(function (s) { return '"' + s + '"'; }).join(', ') + ' because it is already in the list.');
      var long = items.filter(function (w) { return w.letters.length > MAX; });
      if (long.length) ctx.error(long.map(function (w) { return '"' + w.text + '"'; }).join(', ') + (long.length > 1 ? ' are' : ' is') +
        ' longer than the biggest grid (20 by 20). Shorten ' + (long.length > 1 ? 'them' : 'it') + ' or split it over two lines.');
      if (items.length > MAX_WORDS) { ctx.warn('A word search holds up to ' + MAX_WORDS + ' words, so the first ' + MAX_WORDS + ' are used.'); items = items.slice(0, MAX_WORDS); }
      if (!items.length) ctx.error('Add at least one word to hide in the grid.');
      return items;
    },

    build: function (state, ctx) {
      var o = state.options, size = clampSize(o.size), dirs = DIRS[o.difficulty] || DIRS.medium;
      var count = Math.max(1, Math.min(10, o.puzzles || 1)), puzzles = [], failed = false;
      for (var p = 0; p < count; p++) {
        var pz = makePuzzle(ctx.items, size, dirs, ctx, p);
        if (!pz) { failed = true; break; }
        puzzles.push(pz);
      }
      if (failed) {
        ctx.warn('These ' + ctx.items.length + ' words do not all fit, even in a 20 by 20 grid. Remove a few words or shorten the longest ones.');
        puzzles = [];
      } else {
        var grown = puzzles.filter(function (pz) { return pz.n > size; });
        if (grown.length) {
          var big = Math.max.apply(null, grown.map(function (pz) { return pz.n; }));
          ctx.warn('The grid grew to ' + big + ' by ' + big + ' so every word fits.');
        }
      }
      return { title: state.title || 'Word Search', opts: o, paper: state.paper, puzzles: puzzles, multi: count > 1, how: HOW[o.difficulty] || HOW.medium };
    },

    render: function (m, ctx) {
      var h = FD.h, o = m.opts;
      m.puzzles.forEach(function (pz) {
        var body = ctx.sheet({ label: m.title + (m.multi ? ' puzzle ' + (pz.index + 1) : '') });
        ctx.header(body, m.title, m.multi ? 'Puzzle ' + (pz.index + 1) : '');
        body.appendChild(h('p', { cls: 'ws-how', text: 'Find the ' + pz.at.length + ' hidden words. ' + m.how }));
        body.appendChild(h('div', { cls: 'ws-grid', html: svg(pz, o, false) }));
        var words = sortedWords(pz), G = listGeom(words, o);
        if (G) body.appendChild(h('div', { cls: 'ws-list' }, h('b', { text: 'Find these words' }),
          h('ul', { style: '--c:' + G.cols + ';--f:' + G.f + 'pt' }, words.map(function (w) { return h('li', { text: fmt(w, o) }); }))));
      });
      if (!o.key || !m.puzzles.length) return;
      for (var i = 0; i < m.puzzles.length; i += 4) {
        var group = m.puzzles.slice(i, i + 4);
        var body = ctx.sheet({ key: true, label: m.title + ' answer key' });
        ctx.header(body, m.title, keySub(m, group), { key: true, noName: true });
        if (!m.multi) { body.appendChild(h('div', { cls: 'ws-grid', html: svg(group[0], o, true) })); continue; }
        body.appendChild(h('div', { cls: 'ws-keys' }, group.map(function (pz) {
          return h('div', null, h('p', { text: 'Puzzle ' + (pz.index + 1) }), h('div', { cls: 'ws-grid', html: svg(pz, o, true) }));
        })));
      }
    },

    pdf: function (m, P) {
      var doc = P.doc, o = m.opts, b = P.box, IN = 72, first = true;
      function page() { if (!first) P.addPage(); first = false; }
      function grid(pz, x, y, side, key) {
        var n = pz.n, u = side / (n + 0.3), x0 = x + 0.15 * u, y0 = y + 0.15 * u;
        doc.setLineWidth(Math.max(1, u * 0.06)); P.stroke('accent');
        P.roundRect(x0 - 0.1 * u, y0 - 0.1 * u, (n + 0.2) * u, (n + 0.2) * u, 0.35 * u, 'S');
        if (key) {
          doc.setLineCap('round');
          [['accent', 0.84], ['highlight', 0.76]].forEach(function (pass) {
            P.stroke(pass[0]); doc.setLineWidth(pass[1] * u);
            pz.at.forEach(function (p) {
              var ex = p.c + p.dc * (p.len - 1), ey = p.r + p.dr * (p.len - 1);
              doc.line(x0 + (p.c + 0.5) * u, y0 + (p.r + 0.5) * u, x0 + (ex + 0.5) * u, y0 + (ey + 0.5) * u);
            });
          });
          doc.setLineCap('butt');
        }
        P.font('bold', u * 0.6).textColor('ink');
        for (var k = 0; k < pz.grid.length; k++) {
          P.center(fmt(pz.grid[k], o), x0 + (k % n + 0.5) * u, y0 + (Math.floor(k / n) + 0.71) * u);
        }
      }
      m.puzzles.forEach(function (pz) {
        page();
        var y = P.header(m.title, m.multi ? 'Puzzle ' + (pz.index + 1) : '');
        P.font('body', 11).textColor('ink').text('Find the ' + pz.at.length + ' hidden words. ' + m.how, b.x, y);
        y += 12;
        var words = sortedWords(pz), G = listGeom(words, o), listH = G ? G.h * IN : 0;
        var side = Math.min(b.w, b.y + b.h - y - listH - (G ? 12 : 4));
        grid(pz, b.x + (b.w - side) / 2, y, side, false);
        if (G) {
          var top = b.y + b.h - listH;
          doc.setLineWidth(1.5); P.stroke('accent2'); doc.setLineDashPattern([4, 3], 0);
          P.roundRect(b.x, top, b.w, listH, 10, 'S'); doc.setLineDashPattern([], 0);
          P.font('display', 13).textColor('accent').text('Find these words', b.x + 13, top + 20);
          var colW = (b.w - 26) / G.cols, rh = G.rh * IN, bx = G.f * 0.72;
          doc.setLineWidth(0.9); P.stroke('ink');
          words.forEach(function (w, i) {
            var cx = b.x + 13 + Math.floor(i / G.rows) * colW, cy = top + 30 + (i % G.rows) * rh;
            P.roundRect(cx, cy + rh * 0.5 - bx * 0.5, bx, bx, 1.5, 'S');
            var t = fmt(w, o), fs = P.fit(t, colW - bx - 12, G.f, 6);
            P.font('body', fs).textColor('ink').text(t, cx + bx + 5, cy + rh * 0.5 + fs * 0.35);
          });
        }
      });
      if (!o.key || !m.puzzles.length) return;
      for (var i = 0; i < m.puzzles.length; i += 4) {
        var group = m.puzzles.slice(i, i + 4);
        page();
        var y = P.header(m.title, keySub(m, group), { key: true, noName: true });
        if (!m.multi) { var s = Math.min(b.w, b.y + b.h - y); grid(group[0], b.x + (b.w - s) / 2, y, s, true); continue; }
        var gap = 14, cw = (b.w - gap) / 2, ch = (b.y + b.h - y - gap) / 2;
        group.forEach(function (pz, j) {
          var cx = b.x + (j % 2) * (cw + gap), cy = y + Math.floor(j / 2) * (ch + gap);
          P.font('display', 11).textColor('accent').text('Puzzle ' + (pz.index + 1), cx, cy + 10);
          var side2 = Math.min(cw, ch - 16);
          grid(pz, cx + (cw - side2) / 2, cy + 16, side2, true);
        });
      }
    }
  });
})(window.FD = window.FD || {});
