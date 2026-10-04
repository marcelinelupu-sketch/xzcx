/* Shared drawing kit for scavenger.js, routine-chart.js and reward-chart.js.
   A tool's build() lays a page out once as a display list (K.page), in points inside the content box.
   render() turns it into one inline SVG and pdf() replays the same list with jsPDF, so the preview,
   the printout and the PDF match. Text is measured with font width tables (Fredoka for display text,
   Helvetica/Arial metrics for body text), so layouts are decided in build() and stay deterministic. */
var K = (function () {
  var WT = __WIDTHS__, IC = __ICONS__, LABELS = __LABELS__, FROGS = __FROGS__;
  var AREA = { letter: [554.4, 712.8], a4: [537.84, 762.5] };
  var FAM = { d: 'kd', r: 'kr', b: 'kb', i: 'ki' };
  var PFONT = { d: 'display', r: 'body', b: 'bold', i: 'body' };  /* italic is set directly below */

  function n2(v) { return Math.round(v * 100) / 100; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function tw(s, size, f) {
    var t = WT[f === 'd' || f === 'b' ? f : 'r'], w = 0, k;
    s = String(s);
    for (var i = 0; i < s.length; i++) { k = s.charCodeAt(i) - 32; w += (k >= 0 && k < 95 ? t.charCodeAt(k) - 35 : 46) * 12; }
    return w * size / 1000;
  }
  function wrap(s, maxW, size, f) {
    var lines = [], cur = '';
    String(s).split(/\s+/).filter(Boolean).forEach(function (w) {
      var t = cur ? cur + ' ' + w : w;
      if (cur && tw(t, size, f) > maxW) { lines.push(cur); cur = w; } else cur = t;
    });
    if (cur || !lines.length) lines.push(cur);
    return lines;
  }
  /* Largest size (max down to min, half-point steps) where s fits in maxLines lines of maxW and maxH tall. */
  function fit(s, maxW, maxH, max, min, f, maxLines) {
    maxLines = maxLines || 1;
    for (var z = max; z >= min; z -= 0.5) {
      var L = wrap(s, maxW, z, f), ok = L.length <= maxLines && L.length * z * 1.18 <= maxH + 0.01;
      for (var i = 0; ok && i < L.length; i++) ok = tw(L[i], z, f) <= maxW;
      if (ok) return { size: z, lines: L };
    }
    L = wrap(s, maxW, min, f);
    if (L.length > maxLines) { L = L.slice(0, maxLines); L[maxLines - 1] += '...'; }
    return { size: min, lines: L };
  }
  function grey(hex) {
    var v = parseInt(hex.slice(1), 16), g = Math.round(0.299 * (v >> 16) + 0.587 * (v >> 8 & 255) + 0.114 * (v & 255));
    g = g.toString(16); if (g.length < 2) g = '0' + g;
    return '#' + g + g + g;
  }
  function rgb(hex) { var v = parseInt(hex.slice(1), 16); return [v >> 16, v >> 8 & 255, v & 255]; }

  /* ---- display list ---- */
  function page(paper) {
    var a = AREA[paper] || AREA.letter, o = [];
    var pg = {
      W: a[0], H: a[1], o: o,
      rect: function (x, y, w, h, r, fill, stroke, lw, dash) { o.push(['R', x, y, w, h, r || 0, fill || null, stroke || null, lw || 1, dash || null]); return pg; },
      circ: function (cx, cy, r, fill, stroke, lw, dash) { o.push(['C', cx, cy, r, fill || null, stroke || null, lw || 1, dash || null]); return pg; },
      line: function (x1, y1, x2, y2, stroke, lw, dash) { o.push(['L', x1, y1, x2, y2, stroke, lw || 1, dash || null]); return pg; },
      /* anchor: 0 start, 1 middle, 2 end. y is the baseline. */
      text: function (x, y, s, size, f, color, anchor, maxW) { o.push(['T', x, y, String(s), size, f || 'r', color, anchor || 0, maxW || 0]); return pg; },
      /* lines of wrapped text, vertically centered on cy */
      block: function (x, cy, lines, size, f, color, anchor, maxW) {
        var lh = size * 1.18, y = cy - (lines.length * lh) / 2 + size * 0.8;
        lines.forEach(function (l, i) { pg.text(x, y + i * lh, l, size, f, color, anchor, maxW); });
        return pg;
      },
      /* icon (48 grid) or frog art (200 grid) with its top-left corner at x, y */
      icon: function (name, x, y, size, color, bg) { if (IC[name]) o.push(['A', name, x, y, size / 48, color, bg || '#FFFFFF', 0]); return pg; },
      frog: function (kind, x, y, size, ink) { if (FROGS[kind]) o.push(['A', kind, x, y, size / 200, null, '#FFFFFF', ink ? 2 : 1]); return pg; }
    };
    return pg;
  }

  var EL = /^(#[0-9A-Fa-f]{6})?(?:~([\d.]+))?([*+]?)\s*(.*)$/, artCache = {};
  function art(a) {
    var key = (a[7] ? 'f:' : 'i:') + a[1];
    if (!artCache[key]) artCache[key] = (a[7] ? FROGS : IC)[a[1]].map(function (e) {
      var m = EL.exec(e), b = m[4];
      return { c: m[1] || null, w: m[2] ? +m[2] : 2, m: m[3], k: b[0] === 'M' ? 'p' : b[0], d: b[0] === 'M' ? b : b.slice(1).trim().split(/\s+/).map(Number) };
    });
    return artCache[key];
  }

  /* ---- SVG ---- */
  function dash(d) { return d ? ' stroke-dasharray="' + d.join(' ') + '"' : ''; }
  function paint(fill, stroke, lw, d) {
    return ' fill="' + (fill || 'none') + '"' + (stroke ? ' stroke="' + stroke + '" stroke-width="' + n2(lw) + '"' + dash(d) : '');
  }
  function svg(pg, label) {
    var s = ['<svg xmlns="http://www.w3.org/2000/svg" class="dk-svg" viewBox="0 0 ' + pg.W + ' ' + pg.H + '" role="img" aria-label="' + esc(label || '') + '">'];
    pg.o.forEach(function (a) {
      if (a[0] === 'R') s.push('<rect x="' + n2(a[1]) + '" y="' + n2(a[2]) + '" width="' + n2(a[3]) + '" height="' + n2(a[4]) + '" rx="' + n2(a[5]) + '"' + paint(a[6], a[7], a[8], a[9]) + '/>');
      else if (a[0] === 'C') s.push('<circle cx="' + n2(a[1]) + '" cy="' + n2(a[2]) + '" r="' + n2(a[3]) + '"' + paint(a[4], a[5], a[6], a[7]) + '/>');
      else if (a[0] === 'L') s.push('<line x1="' + n2(a[1]) + '" y1="' + n2(a[2]) + '" x2="' + n2(a[3]) + '" y2="' + n2(a[4]) + '" stroke="' + a[5] + '" stroke-width="' + n2(a[6]) + '"' + dash(a[7]) + ' stroke-linecap="round"/>');
      else if (a[0] === 'T') s.push('<text x="' + n2(a[1]) + '" y="' + n2(a[2]) + '" class="' + FAM[a[5]] + '" font-size="' + n2(a[4]) + '" fill="' + a[6] + '"' +
        (a[7] ? ' text-anchor="' + (a[7] === 1 ? 'middle' : 'end') + '"' : '') + '>' + esc(a[3]) + '</text>');
      else if (a[0] === 'A') {
        var g = a[7] === 2;
        s.push('<g transform="translate(' + n2(a[2]) + ' ' + n2(a[3]) + ') scale(' + +a[4].toFixed(4) + ')" fill="none" stroke-linecap="round" stroke-linejoin="round">');
        art(a).forEach(function (e) {
          var col = e.c ? (g ? grey(e.c) : e.c) : a[5];
          var p = e.m === '*' ? ' fill="' + col + '"' : ' fill="' + (e.m === '+' ? a[6] : 'none') + '" stroke="' + col + '" stroke-width="' + e.w + '"';
          var d = e.d;
          if (e.k === 'p') s.push('<path d="' + d + '"' + p + '/>');
          else if (e.k === 'o') s.push('<circle cx="' + d[0] + '" cy="' + d[1] + '" r="' + d[2] + '"' + p + '/>');
          else if (e.k === 'e') s.push('<ellipse cx="' + d[0] + '" cy="' + d[1] + '" rx="' + d[2] + '" ry="' + d[3] + '"' + p + '/>');
          else if (e.k === 'r') s.push('<rect x="' + d[0] + '" y="' + d[1] + '" width="' + d[2] + '" height="' + d[3] + '" rx="' + d[4] + '"' + p + '/>');
        });
        s.push('</g>');
      }
    });
    s.push('</svg>');
    return s.join('');
  }

  /* ---- PDF (jsPDF via the FD.pdf helper P) ---- */
  function segs(d) {
    var t = d.match(/[a-zA-Z]|-?(?:\d*\.\d+|\d+)/g), i = 0, cmd = 'M', x = 0, y = 0, sx = 0, sy = 0, out = [];
    function n() { return +t[i++]; }
    while (i < t.length) {
      if (/[a-zA-Z]/.test(t[i])) cmd = t[i++];
      var C = cmd.toUpperCase(), rel = cmd !== C, dx = rel ? x : 0, dy = rel ? y : 0, a, b, c, e, qx, qy;
      if (C === 'Z') { out.push(['Z']); x = sx; y = sy; continue; }
      if (C === 'M') { x = n() + dx; y = n() + dy; sx = x; sy = y; out.push(['M', x, y]); cmd = rel ? 'l' : 'L'; }
      else if (C === 'L') { x = n() + dx; y = n() + dy; out.push(['L', x, y]); }
      else if (C === 'H') { x = n() + dx; out.push(['L', x, y]); }
      else if (C === 'V') { y = n() + dy; out.push(['L', x, y]); }
      else if (C === 'C') { a = n() + dx; b = n() + dy; c = n() + dx; e = n() + dy; x = n() + dx; y = n() + dy; out.push(['C', a, b, c, e, x, y]); }
      else if (C === 'Q') {
        qx = n() + dx; qy = n() + dy; a = n() + dx; b = n() + dy;
        out.push(['C', x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y), a + 2 / 3 * (qx - a), b + 2 / 3 * (qy - b), a, b]); x = a; y = b;
      } else i++;
    }
    return out;
  }
  function pdf(pg, P) {
    var doc = P.doc, X = P.box.x, Y = P.box.y;
    function fillC(h) { var c = rgb(h); doc.setFillColor(c[0], c[1], c[2]); }
    function strokeC(h) { var c = rgb(h); doc.setDrawColor(c[0], c[1], c[2]); }
    function style(fill, stroke) { if (fill) fillC(fill); if (stroke) strokeC(stroke); return fill && stroke ? 'FD' : fill ? 'F' : 'S'; }
    function lineStyle(lw, d) { doc.setLineWidth(lw); doc.setLineDashPattern(d || [], 0); }
    pg.o.forEach(function (a) {
      var st;
      if (a[0] === 'R') {
        if (!a[6] && !a[7]) return;
        lineStyle(a[8], a[9]); st = style(a[6], a[7]);
        if (a[5] > 0) doc.roundedRect(X + a[1], Y + a[2], a[3], a[4], a[5], a[5], st); else doc.rect(X + a[1], Y + a[2], a[3], a[4], st);
      } else if (a[0] === 'C') {
        if (!a[4] && !a[5]) return;
        lineStyle(a[6], a[7]); st = style(a[4], a[5]);
        doc.circle(X + a[1], Y + a[2], a[3], st);
      } else if (a[0] === 'L') {
        lineStyle(a[6], a[7]); strokeC(a[5]); doc.setLineCap('round');
        doc.line(X + a[1], Y + a[2], X + a[3], Y + a[4]); doc.setLineCap('butt');
      } else if (a[0] === 'T') {
        var size = a[4];
        P.font(PFONT[a[5]], size);
        if (a[8] && P.width(a[3], size) > a[8]) size = P.fit(a[3], a[8], size, 5);
        P.font(PFONT[a[5]], size);
        if (a[5] === 'i') doc.setFont('helvetica', 'italic');
        var c = rgb(a[6]); doc.setTextColor(c[0], c[1], c[2]);
        P.text(a[3], X + a[1], Y + a[2], a[7] ? { align: a[7] === 1 ? 'center' : 'right' } : null);
      } else if (a[0] === 'A') {
        var k = a[4], ox = X + a[2], oy = Y + a[3], g = a[7] === 2;
        doc.setLineDashPattern([], 0); doc.setLineCap('round'); doc.setLineJoin('round');
        art(a).forEach(function (e) {
          var col = e.c ? (g ? grey(e.c) : e.c) : a[5], d = e.d, mode;
          doc.setLineWidth(e.w * k);
          if (e.m === '*') { fillC(col); mode = 'F'; } else if (e.m === '+') { fillC(a[6]); strokeC(col); mode = 'FD'; } else { strokeC(col); mode = 'S'; }
          if (e.k === 'o') doc.circle(ox + d[0] * k, oy + d[1] * k, d[2] * k, mode);
          else if (e.k === 'e') doc.ellipse(ox + d[0] * k, oy + d[1] * k, d[2] * k, d[3] * k, mode);
          else if (e.k === 'r') doc.roundedRect(ox + d[0] * k, oy + d[1] * k, d[2] * k, d[3] * k, d[4] * k, d[4] * k, mode);
          else {
            if (!e.s) e.s = segs(d);
            e.s.forEach(function (q) {
              if (q[0] === 'M') doc.moveTo(ox + q[1] * k, oy + q[2] * k);
              else if (q[0] === 'L') doc.lineTo(ox + q[1] * k, oy + q[2] * k);
              else if (q[0] === 'C') doc.curveTo(ox + q[1] * k, oy + q[2] * k, ox + q[3] * k, oy + q[4] * k, ox + q[5] * k, oy + q[6] * k);
              else doc.close();
            });
            if (mode === 'F') doc.fill(); else if (mode === 'FD') doc.fillStroke(); else doc.stroke();
          }
        });
        doc.setLineCap('butt'); doc.setLineJoin('miter');
      }
    });
    doc.setLineDashPattern([], 0);
  }
  /* Draw every page of a model: render(model.pages) into sheets, pdf(model.pages) into jsPDF pages. */
  function render(pages, ctx, label) {
    pages.forEach(function (pg, i) {
      var body = ctx.sheet({ cls: 'dk-sheet', label: label + (pages.length > 1 ? ', page ' + (i + 1) : '') });
      body.innerHTML = svg(pg, label);
    });
  }
  function pdfAll(pages, P) { pages.forEach(function (pg, i) { if (i) P.addPage(); pdf(pg, P); }); }

  /* ---- palettes and picking an icon from a label ---- */
  var PAL = {
    mint: { dark: '#2C7A50', mid: '#8CCB6E', light: '#E3F2DA', tint: '#F4FAF0', pop: '#F6C445', ink: '#1F2A24' },
    sky: { dark: '#2A6496', mid: '#8EC1E8', light: '#DFEEFA', tint: '#F2F8FD', pop: '#F6C445', ink: '#1E2A36' },
    peach: { dark: '#B5553A', mid: '#F3A98E', light: '#FCE6DC', tint: '#FFF6F2', pop: '#8CCB6E', ink: '#33231E' },
    lavender: { dark: '#3B3A6B', mid: '#B4A9E3', light: '#ECE8FA', tint: '#F8F6FD', pop: '#F6C445', ink: '#24233F' },
    bw: { dark: '#1F1F1F', mid: '#8A8A8A', light: '#EDEDED', tint: '#FAFAFA', pop: '#BDBDBD', ink: '#1F1F1F' }
  };
  function pal(name, ink) { return PAL[ink ? 'bw' : name] || PAL.mint; }
  var PICK = [
    [/laundry|hamper|clothes in|dirty clothes/, 'laundry'], [/brush.*(teeth|tooth)|teeth|tooth|floss/, 'brush-teeth'], [/hair|comb/, 'hair-brush'],
    [/bath|shower|tub/, 'bath'], [/pajama|pj|jammies|nightgown|sleepwear/, 'pajamas'], [/potty|toilet|bathroom|\bpee|tries|\btry\b|wee/, 'potty'],
    [/wash|soap|hands/, 'wash-hands'], [/story|stories/, 'story'], [/read|library/, 'reading'], [/book/, 'book'], [/hug|kiss|cuddle|snuggle/, 'hug'],
    [/make.*bed|bed made|tidy.*bed/, 'make-bed'], [/plant|garden|flower/, 'plants'], [/bed|sleep|nap/, 'bed'], [/light|lamp/, 'lights-off'],
    [/breakfast|cereal|lunch|dinner|meal|eat/, 'breakfast'], [/snack|apple|fruit|veg/, 'snack'], [/water|drink|cup|milk/, 'water'],
    [/toy|tidy|clean up|pick up|playroom|room/, 'toys-away'], [/dress|clothes|uniform|outfit/, 'get-dressed'], [/shoe|boot|sock|coat|jacket/, 'shoes'],
    [/backpack|bag|pack/, 'backpack'], [/vitamin|medicine/, 'vitamins'], [/quiet|calm|breath|relax|pray|meditat|stretch|yoga/, 'quiet-time'],
    [/music|song|sing|lullaby|piano|instrument|practice/, 'music'], [/dish|table|plate/, 'dishes'], [/pet|dog|cat|fish|hamster/, 'feed-pet'],
    [/trash|garbage|recycl|\bbin\b/, 'trash'], [/homework|study|math|spelling|writ/, 'homework'], [/screen|tv|tablet|phone|video|game/, 'screen-off'],
    [/kind|nice|share|help|polite|listen|gentle|manners|sorry|thank/, 'kindness'], [/wake|morning|sun|rise/, 'sun'], [/night|moon/, 'moon'],
    [/sticker/, 'sticker'], [/success|win|prize|reward|trophy|dry/, 'trophy'], [/clock|on time|time/, 'clock']
  ];
  function pick(label) {
    var s = String(label).toLowerCase();
    for (var i = 0; i < PICK.length; i++) if (PICK[i][0].test(s) && IC[PICK[i][1]]) return PICK[i][1];
    return 'star';
  }
  /* "Brush teeth | brush-teeth | 7:30 PM" -> {label, icon, time, explicit} */
  function step(line) {
    var parts = String(line).split('|').map(function (x) { return x.trim(); }), r = { label: parts[0], icon: '', time: '' };
    parts.slice(1).forEach(function (p) {
      var k = p.toLowerCase().replace(/\s+/g, '-');
      if (IC[k]) r.icon = k; else if (/\d/.test(p) && !r.time) r.time = p.slice(0, 12);
    });
    r.head = /:$/.test(r.label);
    if (r.head) r.label = r.label.slice(0, -1).trim();
    if (!r.icon) r.icon = pick(r.label);
    return r;
  }
  function owner(name, title) {
    name = String(name || '').trim();
    if (!name) return title;
    return name + (/s$/i.test(name) ? "' " : "'s ") + title;
  }

  return { page: page, svg: svg, pdf: pdfAll, render: render, tw: tw, wrap: wrap, fit: fit, pal: pal, grey: grey, pick: pick, step: step, owner: owner, icons: IC, labels: LABELS };
})();
/* @editor */
/* Step editor for the chart tools: a picture library (checkbox grid) and a list of steps with
   label, optional time, and up/down/remove buttons. The textarea stays the source of truth;
   every change is written back to it and announced with an input event so the shell re-renders. */
function stepEditor(els, o) {
  var h = FD.h, list = document.getElementById(o.list), grid = document.getElementById(o.grid), ta = els.words, timesEl = o.times ? document.getElementById(o.times) : null;
  if (!list || !grid) return;
  function iconSvg(name) {
    return K.svg({ W: 48, H: 48, o: [['A', name, 0, 0, 1, 'currentColor', '#FFFFFF', 0]] }, '').replace('role="img" aria-label=""', 'aria-hidden="true" focusable="false"');
  }
  function read() { return ta.value.split(/\r?\n/).map(function (s) { return s.trim(); }).filter(Boolean).map(K.step); }
  function line(s) {
    if (s.head) return s.label + ':';
    var out = s.label;
    if (s.icon !== K.pick(s.label)) out += ' | ' + s.icon;
    if (s.time) out += ' | ' + s.time;
    return out;
  }
  function write(steps, keepList) {
    ta.value = steps.map(line).join('\n');
    ta.dispatchEvent(new Event('input', { bubbles: true }));
    if (!keepList) draw();
  }
  function draw() {
    var steps = read(), used = {}, showTimes = !timesEl || timesEl.checked;
    steps.forEach(function (s) { if (!s.head) used[s.icon] = 1; });
    list.textContent = '';
    steps.forEach(function (s, i) {
      var lab = h('input', { type: 'text', value: s.label, maxlength: '40', 'aria-label': 'Step ' + (i + 1) + ' label' });
      lab.addEventListener('input', function () { var st = read(); st[i].label = lab.value.replace(/\|/g, '') || st[i].label; write(st, true); });
      var tm = showTimes && !s.head ? h('input', { type: 'text', value: s.time, maxlength: '12', placeholder: 'Time', 'aria-label': 'Step ' + (i + 1) + ' time' }) : null;
      if (tm) tm.addEventListener('input', function () { var st = read(); st[i].time = tm.value.replace(/\|/g, '').trim(); write(st, true); });
      function btn(txt, name, fn, off) {
        var b = h('button', { type: 'button', cls: 'rt-b', 'aria-label': name + ' step ' + (i + 1), title: name, text: txt, disabled: off || null });
        b.addEventListener('click', fn); return b;
      }
      function move(d) { var st = read(), t = st[i]; st[i] = st[i + d]; st[i + d] = t; write(st); var q = list.children[i + d]; if (q) q.querySelector(d < 0 ? '.rt-b' : '.rt-b+.rt-b').focus(); }
      list.appendChild(h('li', { cls: 'rt-row' + (tm ? ' t' : '') }, h('span', { cls: 'rt-ic', html: s.head ? '' : iconSvg(s.icon) }), lab, tm,
        btn('↑', 'Move up', function () { move(-1); }, i === 0),
        btn('↓', 'Move down', function () { move(1); }, i === steps.length - 1),
        btn('×', 'Remove', function () { var st = read(); st.splice(i, 1); write(st); })));
    });
    FD.$$('input', grid).forEach(function (cb) { cb.checked = !!used[cb.value]; });
  }
  Object.keys(K.labels).forEach(function (name) {
    var cb = h('input', { type: 'checkbox', value: name, cls: 'vh' });
    cb.addEventListener('change', function () {
      var st = read();
      if (cb.checked) {
        if (st.length >= o.max) { cb.checked = false; FD.toast('A chart holds up to ' + o.max + ' ' + o.noun + '.'); return; }
        st.push({ label: K.labels[name], icon: name, time: '' });
      } else st = st.filter(function (s) { return s.icon !== name; });
      write(st);
    });
    grid.appendChild(h('label', { cls: 'rt-pic' }, cb, h('span', { html: iconSvg(name) }), h('small', { text: K.labels[name] })));
  });
  ta.addEventListener('input', function (e) { if (e.isTrusted) draw(); });
  if (timesEl) timesEl.addEventListener('change', draw);
  document.addEventListener('fd:rendered', function () { if (!list.contains(document.activeElement)) draw(); });
  draw();
}
