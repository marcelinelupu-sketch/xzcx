/* frogsdream word scramble maker (reference tool for TOOL-CONTRACT.md).
   Options (names in tools/scramble.controls.html): puzzles 1-10, case upper|lower, hint, bank, key, shuffle. */
(function (FD) {
  'use strict';
  var MAX_WORDS = 60;
  var AREA = { letter: { w: 7.7, h: 9.9 }, a4: { w: 7.47, h: 10.59 } }; /* inches inside margins, minus credit band */

  function lettersOf(s) { return s.replace(/[^A-Za-z]/g, ''); }
  function partsOf(word) { return word.split(/\s+/).map(lettersOf).filter(Boolean); }

  /* Scramble one word with a seeded rand. Each part of a phrase is mixed on its own; the result never equals the original. */
  function scramble(word, rand) {
    var parts = partsOf(word), out, tries = 0;
    do {
      out = parts.map(function (p) {
        if (p.length < 2 || new Set(p.toLowerCase()).size < 2) return p;
        var s, n = 0;
        do { s = FD.rng.shuffle(p.split(''), rand).join(''); } while (s.toLowerCase() === p.toLowerCase() && ++n < 40);
        return s;
      });
    } while (out.join(' ').toLowerCase() === parts.join(' ').toLowerCase() && ++tries < 40);
    return out;
  }

  /* Geometry shared by the HTML preview and the PDF so both look the same. All values in inches. */
  function layout(n, maxUnits, paper, o) {
    var a = AREA[paper] || AREA.letter;
    var cols = n > 10 ? 2 : 1, rows = Math.ceil(n / cols), gap = 0.3;
    var colW = (a.w - gap * (cols - 1)) / cols;
    var avail = a.h - 1.3 - (o.bank ? 1.5 : 0);
    var rowH = Math.min(1.1, avail / Math.max(rows, 1));
    var t = Math.min(0.36, (colW - 0.42) / (maxUnits * 1.14), (rowH - 0.2) / 2.2);
    return { cols: cols, rows: rows, gap: gap, colW: colW, rowH: rowH, t: Math.max(0.12, t) };
  }
  function units(e) { return e.letters.length + (e.parts.length - 1) * 0.5; }
  function fmt(s, o) { return o.case === 'lower' ? s.toLowerCase() : s.toUpperCase(); }

  FD.tool.register({
    id: 'scramble',
    noun: 'words',
    hint: 'One word or short phrase per line. Words need at least 3 letters.',

    parse: function (lines, state, ctx) {
      var items = [], skipped = [];
      lines.forEach(function (line) {
        var w = line.split('|')[0].trim(), L = lettersOf(w);
        if (L.length < 3 || new Set(L.toLowerCase()).size < 2) skipped.push(w); else items.push(w);
      });
      if (skipped.length) ctx.warn('Skipped ' + skipped.map(function (s) { return '"' + s + '"'; }).join(', ') + ' (needs 3 or more different letters).');
      if (items.length > MAX_WORDS) { ctx.warn('Using the first ' + MAX_WORDS + ' words.'); items = items.slice(0, MAX_WORDS); }
      if (!items.length) ctx.error('Add at least one word with 3 or more letters.');
      return items;
    },

    build: function (state, ctx) {
      var o = state.options, n = Math.max(1, Math.min(10, o.puzzles || 1)), per = o.bank ? 20 : 24, puzzles = [];
      for (var p = 0; p < n; p++) {
        var r = ctx.sub('puzzle', p);
        var order = o.shuffle ? FD.rng.shuffle(ctx.items, r) : ctx.items.slice();
        var entries = order.map(function (w, i) {
          var parts = scramble(w, r);
          return { n: i + 1, answer: w, parts: parts, letters: parts.join(''), answerParts: partsOf(w) };
        });
        var pages = [];
        var size = Math.ceil(entries.length / Math.ceil(entries.length / per)); /* balance pages: 24 words become 12 + 12, not 20 + 4 */
        for (var i = 0; i < entries.length; i += size) pages.push(entries.slice(i, i + size));
        var maxU = Math.max.apply(null, entries.map(units));
        puzzles.push({ index: p, entries: entries, pages: pages, maxUnits: maxU });
      }
      return { title: state.title || 'Word Scramble', opts: o, paper: state.paper, puzzles: puzzles, multi: n > 1 };
    },

    render: function (m, ctx) {
      var h = FD.h, o = m.opts;
      m.puzzles.forEach(function (pz) {
        pz.pages.forEach(function (entries, pi) {
          var body = ctx.sheet({ label: m.title + ' puzzle ' + (pz.index + 1) });
          var sub = (m.multi ? 'Puzzle ' + (pz.index + 1) : '') + (pz.pages.length > 1 ? (m.multi ? ', page ' : 'Page ') + (pi + 1) + ' of ' + pz.pages.length : '');
          ctx.header(body, m.title, sub);
          body.appendChild(h('p', { cls: 'sc-how', text: 'Unscramble each word and write it on the lines.' + (o.hint ? ' The first letter is there to help you.' : '') }));
          var L = layout(entries.length, pz.maxUnits, m.paper, o);
          var list = h('ol', { cls: 'sc-list', style: '--cols:' + L.cols + ';--rows:' + L.rows + ';--t:' + L.t.toFixed(3) + 'in;--rh:' + L.rowH.toFixed(3) + 'in' });
          entries.forEach(function (e) {
            var tiles = h('div', { cls: 'sc-tiles' }), blanks = h('div', { cls: 'sc-blanks' });
            e.parts.forEach(function (part, k) {
              if (k) { tiles.appendChild(h('span', { cls: 'sc-gap' })); blanks.appendChild(h('span', { cls: 'sc-gap' })); }
              part.split('').forEach(function (c) { tiles.appendChild(h('span', { cls: 'sc-tile', text: fmt(c, o) })); });
              e.answerParts[k].split('').forEach(function (c, j) {
                blanks.appendChild(h('span', { cls: 'sc-blank', text: o.hint && k === 0 && j === 0 ? fmt(c, o) : '' }));
              });
            });
            list.appendChild(h('li', { cls: 'sc-item' }, h('span', { cls: 'sc-num', text: e.n + '.' }), h('div', null, tiles, blanks)));
          });
          body.appendChild(list);
          if (o.bank) {
            var words = entries.map(function (e) { return e.answer; }).sort(function (a, b) { return a.localeCompare(b); });
            body.appendChild(h('div', { cls: 'sc-bank' }, h('b', { text: 'Word bank' }),
              h('ul', null, words.map(function (w) { return h('li', { text: fmt(w, o) }); }))));
          }
        });
        if (o.key) {
          var body = ctx.sheet({ key: true, label: m.title + ' answer key' });
          ctx.header(body, m.title, m.multi ? 'Puzzle ' + (pz.index + 1) : '', { key: true, noName: true });
          var key = h('ol', { cls: 'sc-key' + (pz.entries.length > 30 ? ' small' : '') });
          pz.entries.forEach(function (e) {
            key.appendChild(h('li', null, h('span', { cls: 'sc-num', text: e.n + '.' }), h('span', { cls: 'sc-mixed', text: fmt(e.parts.join(' '), o) }), h('b', { text: e.answer })));
          });
          body.appendChild(key);
        }
      });
    },

    pdf: function (m, P) {
      var doc = P.doc, o = m.opts, b = P.box, IN = 72, first = true;
      function page() { if (!first) P.addPage(); first = false; }
      m.puzzles.forEach(function (pz) {
        pz.pages.forEach(function (entries, pi) {
          page();
          var sub = (m.multi ? 'Puzzle ' + (pz.index + 1) : '') + (pz.pages.length > 1 ? (m.multi ? ', page ' : 'Page ') + (pi + 1) + ' of ' + pz.pages.length : '');
          var y = P.header(m.title, sub);
          P.font('body', 11).textColor('ink').text('Unscramble each word and write it on the lines.' + (o.hint ? ' The first letter is there to help you.' : ''), b.x, y);
          y += 18;
          var L = layout(entries.length, pz.maxUnits, m.paper, o), t = L.t * IN, g = t * 0.12;
          entries.forEach(function (e, i) {
            var col = Math.floor(i / L.rows), row = i % L.rows;
            var x0 = b.x + col * (L.colW + L.gap) * IN, y0 = y + row * L.rowH * IN;
            P.font('bold', Math.max(8, t * 0.5)).textColor('accent').text(e.n + '.', x0, y0 + t * 0.68);
            var x = x0 + 0.42 * IN;
            e.parts.forEach(function (part, k) {
              if (k) x += t * 0.5;
              part.split('').forEach(function (c) {
                P.fill('soft').stroke('accent2'); doc.setLineWidth(1.1);
                P.roundRect(x, y0, t, t, t * 0.18, 'FD');
                P.font('display', t * 0.62).textColor('ink').center(fmt(c, o), x + t / 2, y0 + t * 0.73);
                x += t + g;
              });
            });
            var bx = x0 + 0.42 * IN, by = y0 + t * 2.15;
            doc.setLineWidth(1.1); P.stroke('ink');
            e.answerParts.forEach(function (part, k) {
              if (k) bx += t * 0.5;
              part.split('').forEach(function (c, j) {
                doc.line(bx, by, bx + t, by);
                if (o.hint && k === 0 && j === 0) P.font('display', t * 0.62).textColor('muted').center(fmt(c, o), bx + t / 2, by - t * 0.18);
                bx += t + g;
              });
            });
          });
          if (o.bank) {
            var words = entries.map(function (e) { return fmt(e.answer, o); }).sort(function (a, c) { return a.localeCompare(c); });
            var bh = 1.3 * IN, top = b.y + b.h - bh - 4;
            doc.setLineWidth(1.5); P.stroke('accent2'); doc.setLineDashPattern([4, 3], 0);
            P.roundRect(b.x, top, b.w, bh, 10, 'S'); doc.setLineDashPattern([], 0);
            P.font('display', 13).textColor('accent').text('Word bank', b.x + 14, top + 20);
            var size = 11, wx = b.x + 14, wy = top + 40;
            P.font('body', size).textColor('ink');
            words.forEach(function (w) {
              var ww = P.width(w, size) + 18;
              if (wx + ww > b.x + b.w - 10) { wx = b.x + 14; wy += size * 1.55; }
              P.text(w, wx, wy); wx += ww;
            });
          }
        });
        if (o.key) {
          page();
          var y = P.header(m.title, m.multi ? 'Puzzle ' + (pz.index + 1) : '', { key: true, noName: true });
          var n = pz.entries.length, cols = n > 15 ? 2 : 1, rows = Math.ceil(n / cols), colW = b.w / cols;
          var lh = Math.min(26, (b.h - (y - b.y) - 10) / rows), fs = Math.min(12, lh * 0.55);
          pz.entries.forEach(function (e, i) {
            var cx = b.x + Math.floor(i / rows) * colW, cy = y + (i % rows) * lh + fs;
            P.font('bold', fs).textColor('accent').text(e.n + '.', cx, cy);
            P.font('body', fs * 0.92).textColor('muted').text(fmt(e.parts.join(' '), o), cx + fs * 2.2, cy);
            P.font('bold', fs).textColor('ink').text(e.answer, cx + colW * 0.5, cy);
          });
        }
      });
    }
  });
})(window.FD = window.FD || {});
