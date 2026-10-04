/* frogsdream bingo card generator. Modes: word bingo (default), 75-ball numbers, 90-ball UK strips, numbers 1 to 30.
   Options (tools/bingo.controls.html): mode, grid, free, freeText, cards, perPage, repeats, caller, names.
   Word list lines may be "square | call" (addition facts: the square shows the answer, the caller sheet shows the problem). */
(function (FD) {
  'use strict';
  var AREA = { letter: { w: 7.7, h: 9.9 }, a4: { w: 7.47, h: 10.59 } }; /* inches inside margins, minus credit band */
  var HEAD = 1.0, MAX_ITEMS = 100, LETTERS = ['B', 'I', 'N', 'G', 'O'], IN = 72;
  var root = null;

  /* ---------- options ---------- */
  function bool(v, d) { return v === undefined || v === null || v === '' ? d : v === true || v === 'true' || v === 1 || v === '1' || v === 'on'; }
  function num(v, lo, hi, d) { v = Math.round(+v); return isFinite(v) ? Math.max(lo, Math.min(hi, v)) : d; }
  function norm(o) {
    o = o || {};
    var mode = ['word', '75', '90', '30'].indexOf(String(o.mode)) >= 0 ? String(o.mode) : 'word';
    var per = +o.perPage;
    return {
      mode: mode, grid: mode === '75' ? 5 : num(o.grid, 3, 5, 5), free: bool(o.free, true),
      freeText: String(o.freeText == null ? 'FREE' : o.freeText).trim().slice(0, 20),
      cards: num(o.cards, 1, 30, 10), perPage: per === 1 || per === 4 ? per : 2,
      repeats: bool(o.repeats, false), caller: bool(o.caller, true), names: bool(o.names, false)
    };
  }

  /* ---------- text fitting (shared by preview and PDF, sizes in pt, lengths in inches) ---------- */
  function tw(s, pt) {
    var u = 0;
    for (var i = 0; i < s.length; i++) {
      var c = s.charAt(i);
      u += c === ' ' || /[ilIj.,;:!|'`]/.test(c) ? 0.27 : /[ftr()\/\-]/.test(c) ? 0.36 : /[mw@%]/.test(c) ? 0.88 : /[MW]/.test(c) ? 0.98 : /[A-Z]/.test(c) ? 0.68 : 0.56;
    }
    return u * pt / IN;
  }
  function wrap(text, w, pt, hard) {
    var lines = [], cur = '';
    String(text).split(/\s+/).filter(Boolean).forEach(function (wd) {
      while (hard && tw(wd, pt) > w && wd.length > 2) { /* very long word: split it with a hyphen */
        var k = wd.length - 1;
        while (k > 1 && tw(wd.slice(0, k) + '-', pt) > w) k--;
        var cut = brk(wd, k);
        if (cur) { lines.push(cur); cur = ''; }
        lines.push(wd.slice(0, cut) + (wd[cut - 1] === '-' ? '' : '-')); wd = wd.slice(cut);
      }
      var t = cur ? cur + ' ' + wd : wd;
      if (!cur || tw(t, pt) <= w) cur = t; else { lines.push(cur); cur = wd; }
    });
    if (cur) lines.push(cur);
    return lines;
  }
  /* Where to break a long word that fits up to k letters: after its own hyphen if it has one,
     else at a syllable-like spot (Thermo-meter, Pachy-cephalosaurus) with 3+ letters on each side. */
  function brk(wd, k) {
    var hy = wd.lastIndexOf('-', k - 1);
    if (hy >= 2) return hy + 1;
    var V = /[aeiouy]/i;
    for (var j = k; j >= 3; j--) {
      if (wd.length - j < 3) continue;
      var a = wd[j - 1], b = wd[j], c = wd[j + 1] || '';
      if (V.test(a) && !V.test(b) && V.test(c)) return j;
      if (!V.test(a) && !V.test(b) && /[a-z]/i.test(a + b) && !/^(ch|sh|th|ph|wh|ck|ng|gh|qu)$/i.test(a + b)) return j;
    }
    return k;
  }
  function fit(text, w, h, max, min) {
    min = min || 5;
    /* first try whole words down to 70% of the size, then allow hyphenating long words before going smaller */
    for (var hard = 0; hard < 2; hard++) {
      for (var pt = Math.floor(max * 2) / 2; pt >= (hard ? min : Math.max(min, max * 0.7)); pt -= 0.5) {
        var lines = wrap(text, w, pt, hard);
        if (lines.length * pt * 1.12 / IN <= h && lines.every(function (l) { return tw(l, pt) <= w; })) return { pt: pt, lines: lines };
      }
    }
    return { pt: min, lines: wrap(text, w, min, 1) };
  }
  function lineFit(text, w, max, min) {
    var pt = max;
    while (pt > (min || 6) && tw(text, pt) > w) pt -= 0.5;
    return pt;
  }

  /* ---------- 90-ball strip: 6 tickets of 3 x 9, 15 numbers each, 5 per row, covering 1 to 90 exactly once ---------- */
  function colRange(c) { var lo = c === 0 ? 1 : c * 10, hi = c === 8 ? 90 : c * 10 + 9, a = []; for (var n = lo; n <= hi; n++) a.push(n); return a; }
  function strip90(r) {
    var shuffle = FD.rng.shuffle, cols = [], c, t, i, counts, tries;
    for (c = 0; c < 9; c++) cols.push(colRange(c));
    /* 1. how many numbers each ticket gets in each column: at least 1, at most 3, 15 per ticket, column totals 9/10.../11 */
    for (tries = 0; ; tries++) {
      counts = []; var tot = [], ok = true;
      for (t = 0; t < 6; t++) { counts.push([1, 1, 1, 1, 1, 1, 1, 1, 1]); tot.push(9); }
      var tokens = [];
      for (c = 0; c < 9; c++) for (i = 6; i < cols[c].length; i++) tokens.push(c);
      tokens = shuffle(tokens, r);
      for (i = 0; i < tokens.length; i++) {
        var opts = [];
        for (t = 0; t < 6; t++) if (tot[t] < 15 && counts[t][tokens[i]] < 3) opts.push(t);
        if (!opts.length) { ok = false; break; }
        t = opts[Math.floor(r() * opts.length)];
        counts[t][tokens[i]]++; tot[t]++;
      }
      if (ok) break;
      if (tries > 500) throw new Error('strip90: could not balance counts');
    }
    /* 2. which rows each column uses, so every row ends up with exactly 5 numbers */
    var layout = counts.map(function (cnt) { return rowsFor(cnt, r); });
    /* 3. deal the numbers: shuffle each column, hand them out, sort top to bottom inside a ticket column */
    var tickets = [];
    for (t = 0; t < 6; t++) tickets.push([[0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0]]);
    for (c = 0; c < 9; c++) {
      var deck = shuffle(cols[c], r), k = 0;
      for (t = 0; t < 6; t++) {
        var take = deck.slice(k, k + counts[t][c]).sort(function (a, b) { return a - b; });
        k += counts[t][c];
        layout[t][c].forEach(function (row, j) { tickets[t][row][c] = take[j]; });
      }
    }
    return tickets;
  }
  function rowsFor(cnt, r) {
    var tries, c, out, fill;
    for (tries = 0; tries < 30; tries++) {
      out = []; fill = [0, 0, 0];
      var order = FD.rng.shuffle([0, 1, 2, 3, 4, 5, 6, 7, 8], r), ok = true;
      order.sort(function (a, b) { return cnt[b] - cnt[a]; });
      for (var i = 0; i < 9 && ok; i++) {
        c = order[i];
        var free = [0, 1, 2].filter(function (x) { return fill[x] < 5; });
        if (free.length < cnt[c]) { ok = false; break; }
        out[c] = FD.rng.shuffle(free, r).slice(0, cnt[c]).sort();
        out[c].forEach(function (x) { fill[x]++; });
      }
      if (ok && fill[0] === 5 && fill[1] === 5 && fill[2] === 5) return out;
    }
    /* fallback that always balances: give each column the least filled rows */
    out = []; fill = [0, 0, 0];
    FD.rng.shuffle([0, 1, 2, 3, 4, 5, 6, 7, 8], r).forEach(function (col) {
      out[col] = [0, 1, 2].sort(function (a, b) { return fill[a] - fill[b] || a - b; }).slice(0, cnt[col]).sort();
      out[col].forEach(function (x) { fill[x]++; });
    });
    return out;
  }

  /* ---------- one card: returns an array of grid*grid cell texts, '' marks the free square ---------- */
  function makeCard(mode, grid, free, pool, r) {
    var need = grid * grid - (free ? 1 : 0), center = (grid * grid - 1) / 2, vals, i, cells = [];
    if (mode === '75') {
      var colVals = [];
      for (var c = 0; c < 5; c++) {
        var nums = []; for (i = 1; i <= 15; i++) nums.push(c * 15 + i);
        colVals.push(FD.rng.shuffle(nums, r).slice(0, 5));
      }
      for (i = 0; i < 25; i++) cells.push(free && i === 12 ? '' : String(colVals[i % 5][Math.floor(i / 5)]));
      return cells;
    }
    if (mode === '30') {
      var all = []; for (i = 1; i <= 30; i++) all.push(String(i));
      vals = FD.rng.shuffle(all, r).slice(0, need);
    } else {
      vals = FD.rng.shuffle(pool, r).slice(0, need);
      if (vals.length < need) {
        while (vals.length < need) vals.push(pool[Math.floor(r() * pool.length)]);
        vals = FD.rng.shuffle(vals, r);
      }
    }
    for (i = 0, c = 0; i < grid * grid; i++) cells.push(free && i === center ? '' : vals[c++]);
    return cells;
  }

  /* ---------- geometry (inches), relative to the area under the header ---------- */
  function cardGeo(paper, per, grid, letters) {
    var A = AREA[paper] || AREA.letter, gap = 0.34, cols = per === 4 ? 2 : 1, rows = per === 1 ? 1 : 2;
    var top = per === 1 ? HEAD : 0, lab = per === 1 ? 0 : 0.36;
    var bw = (A.w - gap * (cols - 1)) / cols, bh = (A.h - top - gap * (rows - 1)) / rows;
    var ch = Math.min(bw / grid, (bh - lab - 0.06) / (grid + (letters ? 0.5 : 0)), per === 1 ? 1.6 : 9);
    var cw = Math.min(bw / grid, ch * 1.45), cell = Math.min(cw, ch); /* squares may be wider than tall to use the page width */
    var blocks = [];
    for (var i = 0; i < per; i++) blocks.push({ x: (i % cols) * (bw + gap), y: Math.floor(i / cols) * (bh + gap) });
    return { per: per, bw: bw, bh: bh, lab: lab, cw: cw, ch: ch, cell: cell, lh: letters ? cell * 0.5 : 0, gx: (bw - cw * grid) / 2, blocks: blocks };
  }
  function cellLayout(text, G, numeric, names) {
    var c = G.cell;
    if (numeric) return { pt: Math.min(40, c * IN * 0.42), lines: [text] };
    return fit(text, G.cw - 0.14, names ? G.ch * 0.6 : G.ch - 0.14, Math.min(26, c * IN * 0.29));
  }
  function callerGeo(paper, check, order, numbers) {
    var A = AREA[paper] || AREA.letter, avail = A.h - HEAD, CH = 0.52, OH = 0.36, GAP = 0.2;
    var longest = function (arr, pre) { return arr.reduce(function (m, s, i) { var t = (pre ? (i + 1) + '. ' : '') + s; return tw(t, 1) > tw(m, 1) ? t : m; }, ''); };
    var lc = longest(check), maxW = tw(lc, 12);
    var sc = numbers ? (check.length >= 75 ? 15 : 10) : maxW > 2.6 ? 2 : maxW > 1.7 ? 3 : maxW > 1.2 ? 4 : 5;
    var oc = numbers ? 10 : maxW > 2.2 ? 2 : maxW > 1.5 ? 3 : 4;
    var r1 = Math.ceil(check.length / sc), r2 = Math.ceil(order.length / oc), sh = 0.36, lh = 0.25;
    var pages = [['check', 'order']];
    if (CH + r1 * sh + GAP + OH + r2 * lh > avail) { sh = 0.3; lh = 0.21; }
    if (CH + r1 * sh + GAP + OH + r2 * lh > avail) {
      pages = [['check'], ['order']];
      sh = Math.min(0.36, (avail - CH) / r1); lh = Math.min(0.25, (avail - OH) / r2);
    }
    var sw = A.w / sc, ow = A.w / oc;
    return {
      pages: pages, sc: sc, oc: oc, r1: r1, r2: r2, sw: sw, sh: sh, ow: ow, lh: lh, CH: CH, OH: OH, GAP: GAP,
      spt: Math.min(11, sh * IN * 0.45, lineFit(lc, sw - 0.3, 11, 5)),
      opt: Math.min(10.5, lh * IN * 0.62, lineFit(longest(order, true), ow - 0.12, 10.5, 5))
    };
  }

  function hashCells(cells) { return FD.rng.hash(cells.join('\u0001')); }

  /* ---------- the plugin ---------- */
  var def = {
    id: 'bingo',
    noun: 'words',
    hint: 'One word or phrase per line. For math bingo write "answer | problem", for example 12 | 7 + 5.',

    init: function (els) {
      root = els.root;
    },

    parse: function (lines, state, ctx) {
      var o = norm(state.options);
      if (root) {
        root.setAttribute('data-bm', o.mode);
        var lab = root.querySelector('#bg-cards-l');
        if (lab) lab.textContent = o.mode === '90' ? 'Tickets (6 per strip)' : 'Cards';
      }
      if (o.mode !== 'word') return lines;
      var items = [], seen = {}, dups = 0;
      lines.forEach(function (l) {
        var p = l.split('|'), sq = p[0].trim(), call = (p[1] || '').trim(), k = (sq + '|' + call).toLowerCase();
        if (!sq) return;
        if (seen[k]) { dups++; return; }
        seen[k] = 1;
        items.push({ sq: sq, call: call });
      });
      if (dups) ctx.warn('Skipped ' + dups + ' repeated ' + (dups === 1 ? 'line' : 'lines') + '.');
      if (items.length > MAX_ITEMS) { ctx.warn('Using the first ' + MAX_ITEMS + ' lines.'); items = items.slice(0, MAX_ITEMS); }
      var u = uniqSquares(items).length, g = o.grid, need = g * g - (o.free && g % 2 ? 1 : 0);
      if (!u) ctx.error('Add some words, one per line.');
      else if (u < need && !o.repeats) {
        ctx.error('Your list has ' + u + ' different ' + (u === 1 ? 'word' : 'words') + ', and a ' + g + ' x ' + g + ' card needs ' + need +
          '. Add ' + (need - u) + ' more, choose a smaller grid, or tick "Allow repeats".');
      } else if (u < need) ctx.warn('The list is shorter than a card, so some words appear twice on a card.');
      return items;
    },

    build: function (state, ctx) {
      var o = norm(state.options), paper = AREA[state.paper] ? state.paper : 'letter';
      var m = { title: state.title || 'Bingo', mode: o.mode, paper: paper, opts: o, pages: [], caller: null };
      if (o.mode === '90') {
        var ns = Math.ceil(o.cards / 6);
        if (o.cards % 6) ctx.warn('90-ball tickets come in strips of 6, so you get ' + ns + (ns === 1 ? ' full strip' : ' full strips') + ' (' + ns * 6 + ' tickets) that each use 1 to 90 once.');
        var A = AREA[paper], th = (A.h - HEAD - 5 * 0.14) / 6;
        m.strip = { gap: 0.14, th: th, lab: 0.2, rh: (th - 0.2) / 3, cw: A.w / 9 };
        for (var s = 0; s < ns; s++) m.pages.push({ type: 'strip', n: s + 1, of: ns, tickets: strip90(ctx.sub('strip', s)) });
      } else {
        var grid = o.mode === '75' ? 5 : o.grid, free = o.free && grid % 2 === 1, numeric = o.mode !== 'word';
        var pool = numeric ? [] : uniqSquares(ctx.items), G = cardGeo(paper, o.perPage, grid, grid === 5);
        var seen = {}, dupe = false, cards = [], memo = {};
        for (var i = 0; i < o.cards; i++) {
          var cells, key;
          for (var a = 0; a < 60; a++) {
            cells = makeCard(o.mode, grid, free, pool, ctx.sub('card', i, a));
            key = hashCells(cells);
            if (!seen[key]) break;
          }
          if (seen[key]) dupe = true;
          seen[key] = 1;
          cards.push({ n: i + 1, cells: cells.map(function (t) {
            if (!t) return { free: true };
            var k = t;
            if (!memo[k]) memo[k] = cellLayout(t, G, numeric, o.names);
            return { t: t, pt: memo[k].pt, lines: memo[k].lines };
          }) });
        }
        /* one text size per card so neighbouring squares read evenly (never forced below 9pt) */
        cards.forEach(function (cd) {
          var sz = Infinity;
          cd.cells.forEach(function (x) { if (!x.free) sz = Math.min(sz, x.pt); });
          sz = Math.max(sz, 9);
          cd.cells.forEach(function (x) { if (!x.free && x.pt > sz) x.pt = sz; });
        });
        if (dupe) ctx.warn('The list is too short to make every card different. Add more words.');
        else if (!numeric && pool.length === grid * grid - (free ? 1 : 0) && o.cards > 1) ctx.warn('Every card uses the same words in a different order. Add a few more words for a better game.');
        var fc = G.cell, freeFit = fit(o.freeText || ' ', G.cw - 0.14, G.ch * 0.3, Math.min(20, fc * IN * 0.17));
        m.grid = grid; m.geo = G; m.letters = grid === 5; m.names = !numeric && o.names; m.free = { size: fc * 0.44, pt: freeFit.pt, lines: o.freeText ? freeFit.lines : [] };
        for (var p = 0; p < cards.length; p += o.perPage) m.pages.push({ type: 'cards', cards: cards.slice(p, p + o.perPage) });
        m.total = cards.length;
      }
      if (o.caller) {
        var check, order, numbers = o.mode !== 'word', r = ctx.sub('calls');
        if (numbers) {
          var max = o.mode === '75' ? 75 : o.mode === '90' ? 90 : 30;
          check = [];
          for (var n = 1; n <= max; n++) check.push(o.mode === '75' ? LETTERS[Math.floor((n - 1) / 15)] + ' ' + n : String(n));
          order = FD.rng.shuffle(check, r);
        } else {
          check = ctx.items.map(function (it) { return it.call ? it.call + ' = ' + it.sq : it.sq; });
          order = FD.rng.shuffle(ctx.items, r).map(function (it) { return it.call || it.sq; });
        }
        m.caller = { check: check, order: order, numbers: numbers, G: callerGeo(paper, check, order, numbers) };
      }
      return m;
    },

    render: function (m, ctx) {
      var h = FD.h;
      function pos(x, y, w, hh) { return 'left:' + x.toFixed(3) + 'in;top:' + y.toFixed(3) + 'in;width:' + w.toFixed(3) + 'in;height:' + hh.toFixed(3) + 'in'; }
      m.pages.forEach(function (pg) {
        var body, area;
        if (pg.type === 'strip') {
          var S = m.strip;
          body = ctx.sheet({ label: m.title + ' strip ' + pg.n });
          ctx.header(body, m.title, '90-ball strip ' + pg.n + ' of ' + pg.of + ', tickets ' + ((pg.n - 1) * 6 + 1) + ' to ' + pg.n * 6);
          area = h('div', { cls: 'bg-area' });
          pg.tickets.forEach(function (tk, t) {
            var blk = h('div', { cls: 'bg-blk', style: pos(0, t * (S.th + S.gap), S.cw * 9, S.th) },
              h('div', { cls: 'bg-tl', style: 'height:' + S.lab + 'in' }, 'Ticket ' + ((pg.n - 1) * 6 + t + 1)));
            var gr = h('div', { cls: 'bg-grid', style: 'grid-template-columns:repeat(9,' + S.cw.toFixed(3) + 'in);grid-auto-rows:' + S.rh.toFixed(3) + 'in;font-size:' + Math.min(20, S.rh * IN * 0.56).toFixed(1) + 'pt' });
            tk.forEach(function (row) { row.forEach(function (v) { gr.appendChild(h('div', { cls: 'bg-c' + (v ? '' : ' bg-e'), text: v ? String(v) : '' })); }); });
            blk.appendChild(gr);
            area.appendChild(blk);
          });
          body.appendChild(area);
          return;
        }
        var G = m.geo;
        body = ctx.sheet({ label: m.title + ' card ' + pg.cards[0].n });
        if (G.per === 1) ctx.header(body, m.title, m.total > 1 ? 'Card ' + pg.cards[0].n + ' of ' + m.total : '');
        area = h('div', { cls: 'bg-area' });
        pg.cards.forEach(function (card, i) {
          var b = G.blocks[i], gw = G.cw * m.grid;
          var blk = h('div', { cls: 'bg-blk' + (G.per > 1 ? ' bg-cut' : ''), style: pos(b.x, b.y, G.bw, G.bh) });
          if (G.per > 1) blk.appendChild(h('div', { cls: 'bg-lab', style: 'height:' + G.lab + 'in' }, h('b', { text: m.title }), h('span', { text: 'Card ' + card.n })));
          var inner = h('div', { style: 'margin-left:' + G.gx.toFixed(3) + 'in;width:' + gw.toFixed(3) + 'in' });
          if (m.letters) {
            inner.appendChild(h('div', { cls: 'bg-let', style: 'height:' + G.lh.toFixed(3) + 'in;font-size:' + (G.lh * IN * 0.62).toFixed(1) + 'pt' },
              LETTERS.map(function (L) { return h('span', { text: L }); })));
          }
          var gr = h('div', { cls: 'bg-grid', style: 'grid-template-columns:repeat(' + m.grid + ',' + G.cw.toFixed(3) + 'in);grid-auto-rows:' + G.ch.toFixed(3) + 'in' });
          card.cells.forEach(function (cell) {
            if (cell.free) {
              gr.appendChild(h('div', { cls: 'bg-c bg-fr', html: FD.frogSVG('bg-frog') },
                m.free.lines.length ? h('div', { style: 'font-size:' + m.free.pt + 'pt' }, m.free.lines.map(function (l) { return h('span', { text: l }); })) : null));
              return;
            }
            gr.appendChild(h('div', { cls: 'bg-c' + (m.names ? ' bg-hn' : ''), style: 'font-size:' + cell.pt + 'pt' },
              h('div', null, cell.lines.map(function (l) { return h('span', { text: l }); })),
              m.names ? h('div', { cls: 'bg-nm', text: 'Name' }) : null));
          });
          var sv = gr.querySelectorAll('.bg-frog');
          for (var k = 0; k < sv.length; k++) sv[k].setAttribute('style', 'width:' + m.free.size.toFixed(3) + 'in;height:' + m.free.size.toFixed(3) + 'in');
          inner.appendChild(gr);
          blk.appendChild(inner);
          area.appendChild(blk);
        });
        body.appendChild(area);
      });
      if (m.caller) {
        var C = m.caller, Q = C.G;
        Q.pages.forEach(function (parts, pi) {
          var body = ctx.sheet({ key: true, label: m.title + ' caller sheet' });
          ctx.header(body, m.title, 'Caller sheet' + (Q.pages.length > 1 ? ', page ' + (pi + 1) + ' of 2' : ''), { noName: true });
          if (parts.indexOf('check') >= 0) {
            body.appendChild(h('h3', { cls: 'bg-h' }, 'Cut-out checklist'));
            body.appendChild(h('p', { cls: 'bg-note' }, 'Tick each one as it is called, or cut along the dashed lines to make calling slips.'));
            var g = h('div', { cls: 'bg-slips', style: 'grid-template-columns:repeat(' + Q.sc + ',' + Q.sw.toFixed(3) + 'in);grid-auto-rows:' + Q.sh.toFixed(3) + 'in;font-size:' + Q.spt + 'pt' });
            C.check.forEach(function (t) { g.appendChild(h('div', null, h('i'), h('span', { text: t }))); });
            body.appendChild(g);
          }
          if (parts.indexOf('order') >= 0) {
            body.appendChild(h('h3', { cls: 'bg-h', style: parts.length > 1 ? 'margin-top:' + Q.GAP + 'in' : null }, 'Call in this order'));
            var ol = h('ol', { cls: 'bg-ord', style: 'grid-template-columns:repeat(' + Q.oc + ',1fr);grid-template-rows:repeat(' + Q.r2 + ',' + Q.lh.toFixed(3) + 'in);font-size:' + Q.opt + 'pt' });
            C.order.forEach(function (t, i) { ol.appendChild(h('li', null, h('b', { text: (i + 1) + '.' }), ' ' + t)); });
            body.appendChild(ol);
          }
        });
      }
    },

    pdf: function (m, P) {
      var doc = P.doc, b = P.box, first = true;
      function page() { if (!first) P.addPage(); first = false; }
      function lines(ls, pt, cx, cy, font) {
        var lh = pt * 1.12, top = cy - ls.length * lh / 2;
        P.font(font || 'bold', pt);
        ls.forEach(function (l, i) {
          var s = pt;
          while (s > 5 && P.width(l, s) > (m.geo ? m.geo.cw * IN : 999) - 8) s -= 0.5;
          if (s !== pt) P.font(font || 'bold', s);
          P.center(l, cx, top + i * lh + pt * 0.86);
          if (s !== pt) P.font(font || 'bold', pt);
        });
      }
      m.pages.forEach(function (pg) {
        page();
        if (pg.type === 'strip') {
          var S = m.strip, y0 = P.header(m.title, '90-ball strip ' + pg.n + ' of ' + pg.of + ', tickets ' + ((pg.n - 1) * 6 + 1) + ' to ' + pg.n * 6);
          var cw = S.cw * IN, rh = S.rh * IN, fs = Math.min(20, rh * 0.56);
          pg.tickets.forEach(function (tk, t) {
            var ty = y0 + t * (S.th + S.gap) * IN;
            P.font('bold', 9).textColor('accent').text('Ticket ' + ((pg.n - 1) * 6 + t + 1), b.x, ty + 10);
            var gy = ty + S.lab * IN;
            tk.forEach(function (row, ri) {
              row.forEach(function (v, ci) {
                var x = b.x + ci * cw, y = gy + ri * rh;
                if (!v) { P.fill('soft'); doc.rect(x, y, cw, rh, 'F'); }
              });
            });
            doc.setLineWidth(0.75); P.stroke('line');
            for (var i = 1; i < 9; i++) doc.line(b.x + i * cw, gy, b.x + i * cw, gy + 3 * rh);
            for (i = 1; i < 3; i++) doc.line(b.x, gy + i * rh, b.x + 9 * cw, gy + i * rh);
            doc.setLineWidth(2); P.stroke('accent'); doc.rect(b.x, gy, 9 * cw, 3 * rh, 'S');
            P.font('display', fs).textColor('ink');
            tk.forEach(function (row, ri) { row.forEach(function (v, ci) { if (v) P.center(String(v), b.x + ci * cw + cw / 2, gy + ri * rh + rh / 2 + fs * 0.35); }); });
          });
          return;
        }
        var G = m.geo, c = G.cw * IN, ch = G.ch * IN, n = m.grid, y0 = b.y;
        if (G.per === 1) y0 = Math.max(b.y + (HEAD - 0.2) * IN, P.header(m.title, m.total > 1 ? 'Card ' + pg.cards[0].n + ' of ' + m.total : ''));
        pg.cards.forEach(function (card, i) {
          var bl = G.blocks[i], bx = b.x + bl.x * IN, by = y0 + bl.y * IN;
          if (G.per > 1) {
            doc.setLineWidth(0.6); doc.setDrawColor(190, 190, 190); doc.setLineDashPattern([3, 3], 0);
            P.roundRect(bx - 0.12 * IN, by - 0.12 * IN, (G.bw + 0.24) * IN, (G.bh + 0.24) * IN, 6, 'S'); doc.setLineDashPattern([], 0);
            var lt = P.fit(m.title, G.bw * IN * 0.68, 14, 8);
            P.font('display', lt).textColor('accent').text(m.title, bx, by + 16);
            P.font('body', 9.5).textColor('muted').text('Card ' + card.n, bx + G.bw * IN, by + 15, { align: 'right' });
            by += G.lab * IN;
          }
          var gx = bx + G.gx * IN;
          if (m.letters) {
            var lh = G.lh * IN;
            P.fill('accent'); doc.rect(gx, by, c * n, lh, 'F');
            P.font('display', lh * 0.62).textColor('white');
            LETTERS.forEach(function (L, k) { P.center(L, gx + k * c + c / 2, by + lh * 0.72); });
            by += lh;
          }
          card.cells.forEach(function (cell, k) {
            var x = gx + (k % n) * c, y = by + Math.floor(k / n) * ch, cx = x + c / 2;
            if (cell.free) {
              P.fill('soft'); doc.rect(x, y, c, ch, 'F');
              var fs = m.free.size * IN, has = m.free.lines.length, fy = y + (has ? ch * 0.08 : (ch - fs) / 2);
              P.frog(cx - fs / 2, fy, fs);
              if (has) { P.textColor('accent'); lines(m.free.lines, m.free.pt, cx, y + ch * 0.78, 'display'); }
              return;
            }
            P.textColor('ink');
            if (m.names) {
              lines(cell.lines, cell.pt, cx, y + ch * 0.4, 'display');
              doc.setLineWidth(0.6); P.stroke('line'); doc.line(x + 0.08 * IN, y + ch - 0.06 * IN, x + c - 0.08 * IN, y + ch - 0.06 * IN);
              P.font('body', 6.5).textColor('muted').text('Name', x + 0.08 * IN, y + ch - 0.06 * IN - 2.5);
            } else lines(cell.lines, cell.pt, cx, y + ch / 2, 'display');
          });
          doc.setLineWidth(0.75); P.stroke('line');
          for (var j = 1; j < n; j++) { doc.line(gx + j * c, by, gx + j * c, by + n * ch); doc.line(gx, by + j * ch, gx + n * c, by + j * ch); }
          doc.setLineWidth(2); P.stroke('accent'); doc.rect(gx, by - (m.letters ? G.lh * IN : 0), n * c, n * ch + (m.letters ? G.lh * IN : 0), 'S');
        });
      });
      if (m.caller) {
        var C = m.caller, Q = C.G;
        Q.pages.forEach(function (parts, pi) {
          page();
          var y = P.header(m.title, 'Caller sheet' + (Q.pages.length > 1 ? ', page ' + (pi + 1) + ' of 2' : ''), { noName: true });
          if (parts.indexOf('check') >= 0) {
            P.font('display', 13).textColor('accent').text('Cut-out checklist', b.x, y + 10);
            P.font('body', 9).textColor('muted').text('Tick each one as it is called, or cut along the dashed lines to make calling slips.', b.x, y + 24);
            y += Q.CH * IN;
            var sw = Q.sw * IN, sh = Q.sh * IN, box = Math.min(9, sh * 0.42);
            doc.setLineDashPattern([2.5, 2.5], 0); doc.setLineWidth(0.6);
            C.check.forEach(function (t, i) {
              var x = b.x + (i % Q.sc) * sw, yy = y + Math.floor(i / Q.sc) * sh;
              P.stroke('line'); doc.rect(x, yy, sw, sh, 'S');
            });
            doc.setLineDashPattern([], 0);
            C.check.forEach(function (t, i) {
              var x = b.x + (i % Q.sc) * sw, yy = y + Math.floor(i / Q.sc) * sh;
              P.stroke('accent'); doc.setLineWidth(0.9); doc.rect(x + 5, yy + (sh - box) / 2, box, box, 'S');
              P.font('body', Q.spt).textColor('ink').text(t, x + box + 9, yy + sh / 2 + Q.spt * 0.35);
            });
            y += Q.r1 * sh + Q.GAP * IN;
          }
          if (parts.indexOf('order') >= 0) {
            P.font('display', 13).textColor('accent').text('Call in this order', b.x, y + 12);
            y += Q.OH * IN;
            var ow = Q.ow * IN, lh = Q.lh * IN;
            C.order.forEach(function (t, i) {
              var x = b.x + Math.floor(i / Q.r2) * ow, yy = y + (i % Q.r2) * lh + lh * 0.7;
              P.font('bold', Q.opt).textColor('accent').text((i + 1) + '.', x, yy);
              P.font('body', Q.opt).textColor('ink').text(t, x + P.width((i + 1) + '. ', Q.opt) + 1, yy);
            });
          }
        });
      }
    }
  };

  function uniqSquares(items) {
    var seen = {}, out = [];
    (items || []).forEach(function (it) { var k = it.sq.toLowerCase(); if (!seen[k]) { seen[k] = 1; out.push(it.sq); } });
    return out;
  }

  FD.bingo = { strip90: strip90, makeCard: makeCard, norm: norm, fit: fit, def: def };
  if (FD.tool && FD.tool.register) FD.tool.register(def);
})(window.FD = window.FD || {});
