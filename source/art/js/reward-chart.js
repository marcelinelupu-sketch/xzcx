/* frogsdream reward chart maker (SPEC 3.6, TOOL-CONTRACT.md).
   Options (tools/reward.controls.html): days 7|14|30, mark sticker|tick, goal, name, palette, weekStart mon|sun.
   Each line is one task (row): "Make my bed" or "Make my bed | make-bed" to choose the picture.
   7 days show weekday names; 14 days print as two weeks; 30 days print as three blocks of 10 numbered days. */
(function (FD) {
  'use strict';
  var MAX = 14;

/* <kit> */
/* </kit> */

  var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  function banner(pg, m, c) {
    var W = pg.W, bh = 100, fw = 112;
    pg.rect(0, 0, W, bh, 20, c.light, null);
    [[W - fw - 58, 10, 18], [W - fw - 100, 66, 12], [10, 8, 13], [W - fw - 24, 52, 11]].forEach(function (s) {
      pg.icon('_star', s[0], s[1], s[2], c.pop, c.light);
    });
    pg.frog('happy', W - fw - 4, -4, fw, m.ink);
    var maxW = W - 34 - fw - 24, t = K.fit(m.title, maxW, 76, 38, 15, 'd', 2);
    pg.block(26, bh / 2 + 4, t.lines, t.size, 'd', c.dark, 0, maxW);
    return bh;
  }

  /* Goal box: "When I get ___ stickers, I earn:" plus the reward (or a blank line to write it on). */
  function goal(pg, m, c) {
    var W = pg.W, h = 78, y = pg.H - h - 4, word = m.mark === 'tick' ? 'ticks' : 'stickers';
    pg.rect(0, y, W - 40, h, 18, c.light, null);
    pg.circ(42, y + h / 2, 29, '#FFFFFF', null);
    pg.icon('trophy', 42 - 24, y + h / 2 - 24, 48, c.dark, '#FFFFFF');
    var x = 86, l1 = 'When I get', l2 = word + ', I earn:', s = 16, y1 = y + 30;
    pg.text(x, y1, l1, s, 'd', c.ink);
    var bx = x + K.tw(l1, s, 'd') + 8;
    pg.line(bx, y1 + 3, bx + 44, y1 + 3, c.dark, 1.2);
    pg.text(bx + 52, y1, l2, s, 'd', c.ink);
    var gx = x, gw = W - 40 - gx - 18;
    if (m.goal) {
      var t = K.fit(m.goal, gw, 26, 22, 11, 'd', 1);
      pg.text(gx, y + 62, t.lines[0], t.size, 'd', c.dark, 0, gw);
    } else pg.line(gx, y + 62, gx + gw, y + 62, c.dark, 1.2);
    return y;
  }

  function bandsFor(m) {
    if (m.days === 7) return [{ label: '', cols: m.dayNames }];
    var per = m.days === 14 ? 7 : 10, out = [];
    for (var s = 1; s <= m.days; s += per) {
      var cols = [];
      for (var d = s; d < s + per && d <= m.days; d++) cols.push(String(d));
      out.push({ label: m.days === 14 ? 'Week ' + (out.length + 1) : 'Days ' + s + ' to ' + (s + cols.length - 1), cols: cols });
    }
    return out;
  }

  function band(pg, m, b, top, rowH, c) {
    var W = pg.W, n = b.cols.length, Lw = Math.round(W * (n > 7 ? 0.3 : 0.34)), dw = (W - Lw) / n, hh = 28, y = top;
    if (b.label) { pg.text(0, y + 13, b.label, 15, 'd', c.dark); y += 20; }
    for (var d = 0; d < n; d++) {
      var dx = Lw + d * dw;
      pg.rect(dx + 2, y, dw - 4, hh - 4, 9, c.light, null);
      pg.text(dx + dw / 2, y + 17, b.cols[d], n > 7 ? 12 : 13, 'd', c.dark, 1);
    }
    y += hh;
    var gridTop = y;
    m.tasks.forEach(function (s, i) {
      var cy = y + rowH / 2, R = Math.min(rowH * 0.38, 22);
      if (i % 2 === 0) pg.rect(0, y, W, rowH, Math.min(12, rowH / 3), c.tint, null);
      pg.circ(6 + R, cy, R, c.light, null);
      pg.icon(s.icon, 6 + R - R * 0.74, cy - R * 0.74, R * 1.48, c.dark, c.light);
      var tx = 6 + 2 * R + 10, tw = Lw - tx - 8, f = K.fit(s.label, tw, rowH - 6, Math.min(17, rowH * 0.36), 8, 'd', 2);
      pg.block(tx, cy, f.lines, f.size, 'd', c.ink, 0, tw);
      var r = Math.min(dw * 0.4, rowH * 0.36);
      for (var k = 0; k < n; k++) {
        var cx = Lw + k * dw + dw / 2;
        if (m.mark === 'tick') pg.rect(cx - r * 0.85, cy - r * 0.85, r * 1.7, r * 1.7, r * 0.35, '#FFFFFF', c.mid, 1.5);
        else pg.circ(cx, cy, r, '#FFFFFF', c.mid, 1.4, [3, 2.5]);
      }
      y += rowH;
    });
    for (var v = 1; v < n; v++) pg.line(Lw + v * dw, gridTop, Lw + v * dw, y, c.light, 1);
    return y;
  }

  FD.tool.register({
    id: 'reward',
    noun: 'tasks',
    hint: 'One task per line. Each task becomes a row of sticker spots.',

    init: function (els, data) {
      stepEditor(els, { list: 'rw-steps', grid: 'rw-grid', max: MAX, noun: 'tasks' });
      /* Week start defaults from the visitor's region unless the page sets it. */
      if (data && data.options && !data.options.weekStart) {
        var l = (navigator.languages && navigator.languages[0]) || navigator.language || 'en-US';
        data.options.weekStart = /-(US|CA|MX|BR|JP|PH|IL)$/i.test(l) || /^en$/i.test(l) ? 'sun' : 'mon';
      }
    },

    parse: function (lines, state, ctx) {
      var tasks = lines.map(K.step).filter(function (s) { return s.label && !s.head; });
      if (tasks.length > MAX) { ctx.warn('A chart holds up to ' + MAX + ' tasks, so the first ' + MAX + ' are shown.'); tasks = tasks.slice(0, MAX); }
      if (!tasks.length) ctx.error('Add at least one task, one per line, or pick pictures from the library.');
      return tasks;
    },

    build: function (state, ctx) {
      var o = state.options, c = K.pal(o.palette || 'mint', state.ink), name = String(o.name || '').trim().slice(0, 24);
      var days = [7, 14, 30].indexOf(+o.days) >= 0 ? +o.days : 7, start = o.weekStart === 'sun' ? 0 : 1;
      var m = {
        title: K.owner(name, state.title || 'Reward Chart'), mark: o.mark === 'tick' ? 'tick' : 'sticker', goal: String(o.goal || '').trim().slice(0, 80),
        days: days, dayNames: DAYS.slice(start).concat(DAYS.slice(0, start)), tasks: ctx.items, ink: state.ink, pages: []
      };
      var bands = bandsFor(m), n = m.tasks.length, probe = K.page(state.paper);
      var avail = probe.H - 100 - 18 - 92;
      /* Fit as many bands per page as keep rows at least 26pt tall. */
      var per = bands.length;
      while (per > 1 && (avail - per * 64) / (per * n) < 26) per--;
      var rowH = Math.min(n <= 4 ? 90 : 76, (avail - per * 64) / (per * n));
      for (var i = 0; i < bands.length; i += per) {
        var pg = K.page(state.paper), set = bands.slice(i, i + per), y = banner(pg, m, c) + 18;
        var used = set.reduce(function (t, b) { return t + (b.label ? 20 : 0) + 28 + n * rowH + 16; }, 0);
        y += Math.max(0, Math.min(40, (avail - used) / 2));
        set.forEach(function (b) { y = band(pg, m, b, y, rowH, c) + 16; });
        goal(pg, m, c);
        m.pages.push(pg);
      }
      return m;
    },

    render: function (m, ctx) { K.render(m.pages, ctx, m.title); },
    pdf: function (m, P) { K.pdf(m.pages, P); }
  });
})(window.FD = window.FD || {});
