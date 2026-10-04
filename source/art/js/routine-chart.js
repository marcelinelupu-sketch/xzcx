/* frogsdream bedtime routine chart (SPEC 3.5, TOOL-CONTRACT.md).
   Options (tools/routine.controls.html): layout strip|grid|weekly, palette mint|sky|peach|lavender|bw, name, times, mascot.
   Each line is one step: "Brush teeth", "Brush teeth | 7:30 PM", or with a picture name, "Teeth time | brush-teeth | 7:30 PM".
   A line ending in a colon ("Morning:") starts a group heading. Pictures come from the icon library in the kit below. */
(function (FD) {
  'use strict';
  var MAX = 14;

/* <kit> */
/* </kit> */

  var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  function mood(title) {
    var t = title.toLowerCase();
    if (/bed|night|sleep|evening|nap/.test(t)) return 'night';
    if (/morning|wake|school/.test(t)) return 'day';
    return 'any';
  }

  function banner(pg, m, c) {
    var W = pg.W, bh = 100, fw = m.mascot ? 118 : 0;
    pg.rect(0, 0, W, bh, 20, c.light, null);
    var night = m.mood !== 'day';
    /* a few fixed sparkles: stars at night, small suns by day */
    [[W - fw - 58, 10, 18], [W - fw - 100, 66, 12], [10, 8, 13], [W - fw - 24, 52, 11]].forEach(function (s, i) {
      pg.icon(night || i % 2 ? '_star' : 'sun', s[0], s[1], s[2], c.pop, c.light);
    });
    if (m.mascot) pg.frog(night ? 'sleep' : 'happy', W - fw - 2, -2, fw, m.ink);
    else pg.icon(night ? 'moon' : 'sun', W - 74, 20, 60, c.mid);
    var maxW = W - 34 - (m.mascot ? fw + 24 : 84), t = K.fit(m.title, maxW, 76, 38, 15, 'd', 2);
    pg.block(26, bh / 2 + 4, t.lines, t.size, 'd', c.dark, 0, maxW);
    return bh;
  }

  function footer(pg, m, c) {
    var msg = m.mood === 'night' ? 'Sweet dreams' : m.mood === 'day' ? 'Have a great day' : 'You did it';
    msg += m.name ? ', ' + m.name + '!' : '!';
    var w = K.tw(msg, 17, 'd'), cx = pg.W / 2, y = pg.H - 8;
    pg.text(cx, y, msg, 17, 'd', c.dark, 1);
    pg.icon('_star', cx - w / 2 - 26, y - 17, 18, c.pop).icon('_star', cx + w / 2 + 8, y - 17, 18, c.pop);
  }

  function badge(pg, cx, cy, r, n, c) {
    pg.circ(cx, cy, r, c.dark, null);
    pg.text(cx, cy + r * 0.38, String(n), r * 1.05, 'b', '#FFFFFF', 1);
  }
  function picture(pg, s, cx, cy, R, c) {
    pg.circ(cx, cy, R, c.light, null);
    pg.icon(s.icon, cx - R * 0.74, cy - R * 0.74, R * 1.48, c.dark, c.light);
  }
  function timePill(pg, x, cy, w, time, c) {
    pg.rect(x, cy - 12, w, 24, 12, '#FFFFFF', c.mid, 1);
    if (time) pg.text(x + w / 2, cy + 4.5, time, 12, 'b', c.ink, 1, w - 10);
    else pg.line(x + 14, cy + 6, x + w - 14, cy + 6, c.mid, 0.8);
  }
  function heading(pg, x, y, w, h, label, c) {
    var size = Math.min(18, h * 0.62);
    pg.text(x + 4, y + h / 2 + size * 0.36, label, size, 'd', c.dark, 0, w * 0.6);
    var lx = x + 14 + K.tw(label, size, 'd');
    if (lx < x + w - 10) pg.line(lx, y + h / 2, x + w, y + h / 2, c.mid, 1.5, [0.1, 5]);
  }

  /* A star to color in when the step is done. */
  function done(pg, cx, cy, r, c) { pg.icon('star', cx - r * 1.25, cy - r * 1.3, r * 2.5, c.mid, '#FFFFFF'); }

  /* A step card. Wide cards put the picture on the left; tall ones stack it above the label. */
  function card(pg, s, x, y, w, h, m, c, tall) {
    pg.rect(x, y, w, h, Math.min(18, h * 0.22), c.tint, c.mid, 1.3);
    var br = Math.max(8, Math.min(13, h * 0.16)), ring = Math.max(8, Math.min(17, h * 0.2));
    if (tall) {
      badge(pg, x + 20, y + 20, br, s.n, c);
      done(pg, x + w - 24, y + 23, 14, c);
      var timeH = m.times ? 28 : 0, labH = Math.min(64, Math.max(30, h * 0.24)), R = Math.max(14, Math.min((h - labH - timeH - 26) / 2, w * 0.3));
      picture(pg, s, x + w / 2, y + 14 + R, R, c);
      var t = K.fit(s.label, w - 28, labH, Math.min(28, labH * 0.5), 10, 'd', 2);
      pg.block(x + w / 2, y + 18 + 2 * R + labH / 2, t.lines, t.size, 'd', c.ink, 1, w - 28);
      if (m.times) timePill(pg, x + w / 2 - 44, y + h - 22, 88, s.time, c);
      return;
    }
    var cy = y + h / 2, R2 = Math.min(h * 0.4, 46), bx = x + 12 + br;
    badge(pg, bx, cy, br, s.n, c);
    var px = bx + br + 10 + R2;
    picture(pg, s, px, cy, R2, c);
    var right = x + w - 16 - ring * 2, tx = px + R2 + 14;
    done(pg, right + ring, cy, ring, c);
    right -= 12;
    if (m.times) { var pw = Math.min(86, (right - tx) * 0.4); timePill(pg, right - pw, cy, pw, s.time, c); right -= pw + 10; }
    var f = K.fit(s.label, right - tx, h - 8, Math.min(30, h * 0.36), 9, 'd', 2);
    pg.block(tx, cy, f.lines, f.size, 'd', c.ink, 0, right - tx);
  }

  function strip(pg, m, top, bottom, c) {
    var units = 0, gap = 8;
    m.steps.forEach(function (s) { units += s.head ? 0.42 : 1; });
    var unit = Math.min(104, (bottom - top - gap * (m.steps.length - 1)) / units), y = top;
    m.steps.forEach(function (s) {
      var h = s.head ? unit * 0.42 : unit;
      if (s.head) heading(pg, 0, y, pg.W, h, s.label, c); else card(pg, s, 0, y, pg.W, h, m, c);
      y += h + gap;
    });
  }

  function grid(pg, m, top, bottom, c) {
    var rows = [], cur = [], gap = 12;
    m.steps.forEach(function (s) {
      if (s.head) { if (cur.length) rows.push(cur); rows.push([s]); cur = []; return; }
      cur.push(s); if (cur.length === 2) { rows.push(cur); cur = []; }
    });
    if (cur.length) rows.push(cur);
    var units = 0;
    rows.forEach(function (r) { units += r[0].head ? 0.3 : 1; });
    var unit = Math.min(230, (bottom - top - gap * (rows.length - 1)) / units), y = top, cw = (pg.W - gap) / 2;
    rows.forEach(function (r) {
      var h = r[0].head ? unit * 0.3 : unit;
      if (r[0].head) heading(pg, 0, y, pg.W, Math.max(h, 22), r[0].label, c);
      else r.forEach(function (s, i) { card(pg, s, r.length === 1 ? (pg.W - cw) / 2 : i * (cw + gap), y, cw, h, m, c, h >= 118); });
      y += h + gap;
    });
  }

  function weekly(pg, m, top, bottom, c) {
    var W = pg.W, Lw = Math.round(W * 0.37), dw = (W - Lw) / 7, hh = 30;
    var label = 'Week of', lx = W - 200;
    pg.text(lx, top + 2, label, 11, 'b', c.ink);
    pg.line(lx + K.tw(label, 11, 'b') + 8, top + 4, W, top + 4, c.mid, 0.9);
    top += 18;
    var units = 0;
    m.steps.forEach(function (s) { units += s.head ? 0.5 : 1; });
    var rowH = Math.min(80, (bottom - top - hh - 6) / units), days = m.days;
    for (var d = 0; d < 7; d++) {
      var dx = Lw + d * dw;
      pg.rect(dx + 3, top, dw - 6, hh - 4, 9, c.light, null);
      pg.text(dx + dw / 2, top + 18, days[d], 13, 'd', c.dark, 1);
    }
    var y = top + hh, i = 0;
    m.steps.forEach(function (s) {
      var h = s.head ? rowH * 0.5 : rowH, cy = y + h / 2;
      if (s.head) { heading(pg, 0, y, W, h, s.label, c); y += h; return; }
      if (i++ % 2 === 0) pg.rect(0, y, W, h, Math.min(12, h / 3), c.tint, null);
      var R = Math.min(h * 0.38, 24);
      picture(pg, s, 6 + R, cy, R, c);
      var tx = 6 + 2 * R + 10, tw = Lw - tx - 8, lab = s.label;
      if (m.times && s.time) lab += ' (' + s.time + ')';
      var f = K.fit(lab, tw, h - 6, Math.min(17, h * 0.34), 8, 'd', 2);
      pg.block(tx, cy, f.lines, f.size, 'd', c.ink, 0, tw);
      var r = Math.min(dw, h) * 0.3;
      for (var k = 0; k < 7; k++) pg.circ(Lw + k * dw + dw / 2, cy, r, '#FFFFFF', c.mid, 1.5);
      y += h;
    });
    for (var v = 1; v < 7; v++) pg.line(Lw + v * dw, top + hh, Lw + v * dw, y, c.light, 1);
  }

  FD.tool.register({
    id: 'routine',
    noun: 'steps',
    hint: 'One step per line, in order. Add a time after a bar, like Bath | 7:00 PM.',

    init: function (els) { stepEditor(els, { list: 'rt-steps', grid: 'rt-grid', times: 'rt-times', max: MAX, noun: 'steps' }); },

    parse: function (lines, state, ctx) {
      var steps = lines.map(K.step).filter(function (s) { return s.label; }), n = 0, out = [];
      steps.forEach(function (s) { if (!s.head) { if (n < MAX) { s.n = ++n; out.push(s); } } else out.push(s); });
      while (out.length && out[out.length - 1].head) out.pop();
      if (n >= MAX && steps.filter(function (s) { return !s.head; }).length > MAX) ctx.warn('A chart holds up to ' + MAX + ' steps, so the first ' + MAX + ' are shown.');
      if (!n) ctx.error('Add at least one step, one per line, or pick pictures from the library.');
      return out;
    },

    build: function (state, ctx) {
      var o = state.options, c = K.pal(o.palette || 'lavender', state.ink), name = String(o.name || '').trim().slice(0, 24);
      var base = state.title || 'Bedtime Routine';
      var start = state.paper === 'a4' ? 1 : 0; /* Monday first on A4, Sunday first on US Letter */
      var m = {
        title: K.owner(name, base), name: name, mood: mood(base), mascot: o.mascot !== false, times: !!o.times, ink: state.ink,
        steps: ctx.items, days: DAYS.slice(start).concat(DAYS.slice(0, start)), pages: []
      };
      var pg = K.page(state.paper), top = banner(pg, m, c) + 18, bottom = pg.H - 34;
      if (o.layout === 'grid') grid(pg, m, top, bottom, c);
      else if (o.layout === 'weekly') weekly(pg, m, top, bottom, c);
      else strip(pg, m, top, bottom, c);
      footer(pg, m, c);
      m.pages.push(pg);
      return m;
    },

    render: function (m, ctx) { K.render(m.pages, ctx, m.title); },
    pdf: function (m, P) { K.pdf(m.pages, P); }
  });
})(window.FD = window.FD || {});
