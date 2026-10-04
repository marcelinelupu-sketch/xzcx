/* Frog's Dream scavenger hunt generator (SPEC 3.3, TOOL-CONTRACT.md).
   Options (tools/scavenger.controls.html): layout checklist|two-column|photo|team, names, timeLimit, copies 1-30, shuffle, ageNote.
   Items are "Thing to find" or "Thing to find | 3" (points). Pages are laid out once in build() with the
   drawing kit below, then drawn as SVG for the preview and print, and with jsPDF for the download. */
(function (FD) {
  'use strict';
  var MAX = 60;

/* <kit> */
/* </kit> */

  function colors(ink) {
    return ink ? { a: '#1F1F1F', a2: '#8A8A8A', soft: '#F1F1F1', k: '#1F1F1F', mu: '#666666', ln: '#BDBDBD', w: '#FFFFFF' }
      : { a: '#2F8F5B', a2: '#8CCB6E', soft: '#EEF6E8', k: '#1F2A24', mu: '#5E6A63', ln: '#CFD9D2', w: '#FFFFFF' };
  }
  var HOW = {
    checklist: 'Find each thing on the list and tick its box.',
    'two-column': 'Find each thing on the list and tick its box.',
    photo: 'Tick the box when you find it. Snap a photo, then tick the camera box too.',
    team: 'Tick each find, then write its points in the score column. Highest total wins.'
  };

  /* A labelled write-in line: "Team ________". Returns the x after it. */
  function field(pg, x, y, label, w, c) {
    pg.text(x, y, label, 10.5, 'b', c.k);
    var lx = x + K.tw(label, 10.5, 'b') + 6;
    pg.line(lx, y + 2, x + w, y + 2, c.mu, 0.75);
    return x + w;
  }

  function header(pg, m, copy, c) {
    var W = pg.W, o = m.opts, nameW = o.names ? 0 : 190;
    pg.icon('search', 0, -2, 30, c.a);
    var t = K.fit(m.title, W - 40 - nameW, 30, 26, 13, 'd', 1);
    pg.text(38, 22, t.lines[0], t.size, 'd', c.a, 0, W - 40 - nameW);
    if (!o.names) field(pg, W - 180, 22, 'Name', 180, c);
    var sub = [];
    if (o.ageNote) sub.push(String(o.ageNote).slice(0, 80));
    if (m.copies > 1) sub.push('Copy ' + (copy + 1) + ' of ' + m.copies);
    var y = 34;
    if (sub.length) { pg.text(38, y + 8, sub.join('   ·   '), 10, 'r', c.mu, 0, W - 40); y += 14; }
    y += 6;
    pg.line(0, y, W, y, c.a, 2.2);
    y += 22;
    if (o.names) {
      field(pg, 0, y, 'Team', W * 0.36, c);
      field(pg, W * 0.36 + 18, y, 'Players', W - W * 0.36 - 18, c);
      y += 24;
    }
    if (o.timeLimit) {
      var third = (W - 36) / 3;
      field(pg, 0, y, 'Time limit', third, c);
      field(pg, third + 18, y, 'Start', third, c);
      field(pg, 2 * third + 36, y, 'Finish', third, c);
      y += 24;
    }
    pg.text(0, y + (o.names || o.timeLimit ? 2 : -2), HOW[o.layout] || HOW.checklist, 11, 'i', c.k, 0, W);
    return y + 14;
  }

  function pill(pg, xr, cy, pts, c) {
    var s = pts + (pts === 1 ? ' pt' : ' pts'), w = K.tw(s, 8.5, 'b') + 10;
    pg.rect(xr - w, cy - 7, w, 14, 7, c.soft, c.a2, 0.75);
    pg.text(xr - w / 2, cy + 3, s, 8.5, 'b', c.a, 1);
    return w;
  }

  function listPage(pg, m, items, top, c) {
    var W = pg.W, o = m.opts, photo = o.layout === 'photo', n = items.length;
    var bottom = pg.H - (m.points ? 40 : 6), headH = photo ? 18 : 0, avail = bottom - top - headH;
    var cols = o.layout === 'two-column' || avail / n < (photo ? 30 : 25) ? 2 : 1;
    var rows = Math.ceil(n / cols), rowH = Math.min(photo ? 48 : 42, avail / rows), gap = 22, colW = (W - gap * (cols - 1)) / cols;
    var b = Math.max(9, Math.min(rowH * 0.6, 19)), fs = Math.max(8, Math.min(15, rowH * 0.46)), camW = photo ? Math.max(30, b * 1.6 + 14) : 0;
    for (var col = 0; col < cols && photo; col++) {
      var hx = col * (colW + gap);
      pg.text(hx, top + 10, 'Found', 8, 'b', c.mu);
      pg.text(hx + colW - camW / 2, top + 10, 'Snap it', 8, 'b', c.mu, 1);
    }
    top += headH;
    items.forEach(function (it, i) {
      var x0 = Math.floor(i / rows) * (colW + gap), y0 = top + (i % rows) * rowH, cy = y0 + rowH / 2, xr = x0 + colW;
      pg.rect(x0, cy - b / 2, b, b, b * 0.22, c.w, c.a, 1.5);
      if (photo) {
        var cb = b * 0.85, ci = Math.min(b * 1.1, 20);
        pg.icon('camera', xr - camW + 2, cy - ci / 2, ci, c.a);
        pg.rect(xr - cb, cy - cb / 2, cb, cb, cb * 0.22, c.w, c.a2, 1.2);
        xr -= camW + 4;
      }
      if (it.pts) xr -= pill(pg, xr, cy, it.pts, c) + 6;
      var tx = x0 + b + 9, t = K.fit(it.text, xr - tx, rowH - 3, fs, 7, 'r', 2);
      pg.block(tx, cy, t.lines, t.size, 'r', c.k, 0, xr - tx);
      if (i % rows !== rows - 1 && i !== n - 1) pg.line(tx, y0 + rowH, x0 + colW, y0 + rowH, c.ln, 0.9, [0.1, 3.2]);
    });
    var end = top + rows * rowH + 10;
    if (bottom - end > 110) {
      pg.rect(0, end + 6, W, bottom - end - 12, 12, null, c.a2, 1.4, [5, 4]);
      pg.text(14, end + 26, 'Draw or write about your favorite find', 11, 'd', c.a, 0, W - 28);
    }
    if (m.points) {
      var bx = W - 200;
      pg.rect(bx, pg.H - 34, 200, 28, 8, c.soft, c.a2, 1);
      pg.text(bx + 12, pg.H - 15.5, 'Total points', 11, 'd', c.a);
      pg.line(bx + 100, pg.H - 13, W - 14, pg.H - 13, c.k, 0.9);
    }
  }

  function teamPage(pg, m, items, top, c) {
    var W = pg.W, n = items.length, headH = 22, totH = 30, avail = pg.H - top - headH - totH - 6;
    var rowH = Math.max(11, Math.min(30, avail / n)), fs = Math.max(7, Math.min(12, rowH * 0.52));
    var cw = [26, 0, 50, 48, 64]; cw[1] = W - cw[0] - cw[2] - cw[3] - cw[4];
    var xs = [0]; cw.forEach(function (w, i) { xs[i + 1] = xs[i] + w; });
    var tableH = headH + n * rowH + totH;
    pg.rect(0, top, W, tableH, 8, c.w, null);
    pg.rect(0, top, W, headH, 8, c.a, null).rect(0, top + headH - 8, W, 8, 0, c.a, null);
    ['#', 'Item to find', 'Points', 'Found', 'Score'].forEach(function (h, i) {
      pg.text(i === 1 ? xs[1] + 8 : xs[i] + cw[i] / 2, top + 15, h, 10, 'b', c.w, i === 1 ? 0 : 1);
    });
    var y = top + headH;
    items.forEach(function (it, i) {
      var cy = y + rowH / 2;
      if (i % 2) pg.rect(0, y, W, rowH, 0, c.soft, null);
      pg.text(xs[0] + cw[0] / 2, cy + fs * 0.35, String(i + 1), fs * 0.9, 'b', c.a, 1);
      var t = K.fit(it.text, cw[1] - 14, rowH - 2, fs, 6.5, 'r', 2);
      pg.block(xs[1] + 8, cy, t.lines, t.size, 'r', c.k, 0, cw[1] - 14);
      pg.text(xs[2] + cw[2] / 2, cy + fs * 0.35, String(it.pts || 1), fs, 'b', c.k, 1);
      var b = Math.min(rowH - 5, 13);
      pg.rect(xs[3] + (cw[3] - b) / 2, cy - b / 2, b, b, b * 0.22, c.w, c.a, 1.2);
      y += rowH;
    });
    pg.rect(0, y, W, totH, 0, c.soft, null).line(0, y, W, y, c.a, 1.5);
    pg.text(xs[4] - 12, y + 19.5, 'Total score', 12, 'd', c.a, 2);
    pg.rect(xs[4] + 6, y + 5, cw[4] - 12, totH - 10, 5, c.w, c.a, 1.2);
    for (var k = 2; k < 5; k++) pg.line(xs[k], top + headH, xs[k], top + headH + n * rowH, c.ln, 0.75);
    pg.rect(0, top, W, tableH, 8, null, c.a2, 1.4);
  }

  FD.tool.register({
    id: 'scavenger',
    noun: 'items',
    hint: 'One thing to find per line. Add points after a bar, like Animal tracks | 3.',

    parse: function (lines, state, ctx) {
      var items = [], bad = [];
      lines.forEach(function (line) {
        var p = line.split('|'), text = p[0].trim(), pts = p.length > 1 ? p[1].trim() : '';
        if (!text) return;
        if (pts && !/^\d{1,3}$/.test(pts)) { bad.push(text); pts = ''; }
        items.push({ text: text.slice(0, 90), pts: pts ? Math.max(1, parseInt(pts, 10)) : 0 });
      });
      if (bad.length) ctx.warn('Points must be a whole number, so they were left off for ' + bad.map(function (s) { return '"' + s + '"'; }).join(', ') + '.');
      if (items.length > MAX) { ctx.warn('Using the first ' + MAX + ' items. Long lists fit best as two hunts.'); items = items.slice(0, MAX); }
      if (!items.length) ctx.error('Add at least one thing to find, one per line.');
      return items;
    },

    build: function (state, ctx) {
      var o = Object.assign({}, state.options), copies = Math.max(1, Math.min(30, o.copies || 1)), c = colors(state.ink);
      if (!HOW[o.layout]) o.layout = 'checklist';
      var m = { title: state.title || 'Scavenger Hunt', opts: o, copies: copies, points: ctx.items.some(function (it) { return it.pts; }) && o.layout !== 'team', pages: [] };
      for (var i = 0; i < copies; i++) {
        var items = o.shuffle ? FD.rng.shuffle(ctx.items, ctx.sub('copy', i)) : ctx.items.slice();
        var pg = K.page(state.paper), top = header(pg, m, i, c) + 6;
        if (o.layout === 'team') teamPage(pg, m, items, top, c); else listPage(pg, m, items, top, c);
        m.pages.push(pg);
      }
      return m;
    },

    render: function (m, ctx) { K.render(m.pages, ctx, m.title); },
    pdf: function (m, P) { K.pdf(m.pages, P); }
  });
})(window.FD = window.FD || {});
