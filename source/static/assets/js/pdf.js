/* Frog's Dream pdf.js: lazy jsPDF loader plus a small drawing helper for multi-page Letter/A4 PDFs.
   Usage (inside a tool's pdf hook):
     var P = await FD.pdf.create({ paper: 'letter', ink: false, stamp: true, title: 'My puzzle' });
     P.header('Christmas Word Scramble', 'Unscramble each word');   // returns y below the header
     P.doc.text('hello', P.box.x, 200);                             // raw jsPDF, unit = pt
     P.addPage();
     P.save('christmas-word-scramble.pdf');   // adds the credit line and frog stamp to every page
   Units are PostScript points (72 per inch). P.box is the printable area inside the 0.4in margin,
   minus a 0.3in band at the bottom reserved for the credit line. */
(function (FD) {
  'use strict';
  var SRC = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
  var FONT_URL = '/assets/fonts/fredoka-600.ttf';
  var loading = null, fontData = null;
  var COLORS = {
    ink: [31, 42, 36], accent: [47, 143, 91], accent2: [140, 203, 110], soft: [238, 246, 232],
    line: [154, 165, 158], muted: [110, 110, 110], highlight: [246, 196, 69], white: [255, 255, 255], credit: [128, 128, 128]
  };
  var GREY = { accent: [31, 31, 31], accent2: [138, 138, 138], soft: [241, 241, 241], line: [138, 138, 138], highlight: [189, 189, 189] };

  function load() {
    if (window.jspdf && window.jspdf.jsPDF) return Promise.resolve(window.jspdf.jsPDF);
    if (loading) return loading;
    loading = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = SRC; s.async = true; s.crossOrigin = 'anonymous';
      s.onload = function () { window.jspdf && window.jspdf.jsPDF ? resolve(window.jspdf.jsPDF) : reject(new Error('jsPDF missing')); };
      s.onerror = function () { loading = null; reject(new Error('Could not load the PDF library. Check your connection and try again, or use Print and choose Save as PDF.')); };
      document.head.appendChild(s);
    });
    return loading;
  }

  function loadFont() {
    if (fontData) return Promise.resolve(fontData);
    return fetch(FONT_URL).then(function (r) { if (!r.ok) throw new Error('font'); return r.arrayBuffer(); }).then(function (buf) {
      var b = new Uint8Array(buf), s = '';
      for (var i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
      fontData = btoa(s);
      return fontData;
    }).catch(function () { return null; });
  }

  /* Text safe for the built-in Helvetica (WinAnsi). Drops emoji and unsupported symbols. */
  function clean(t) {
    return String(t == null ? '' : t).replace(/[\u2018\u2019]/g, "'").replace(/[\u201C\u201D]/g, '"')
      .replace(/[\u2010-\u2015]/g, '-').replace(/\u2026/g, '...').replace(/[^\x09\x0A\x0D\x20-\x7E\xA0-\xFF]/g, '');
  }

  function create(opts) {
    opts = opts || {};
    return Promise.all([load(), loadFont()]).then(function (res) {
      var JsPDF = res[0], font = res[1];
      var paper = (FD.print && FD.print.PAPER[opts.paper]) || { wPt: 612, hPt: 792 };
      var doc = new JsPDF({ unit: 'pt', format: opts.paper === 'a4' ? 'a4' : 'letter', compress: true });
      var hasDisplay = false;
      if (font) {
        try { doc.addFileToVFS('Fredoka.ttf', font); doc.addFont('Fredoka.ttf', 'Fredoka', 'normal'); hasDisplay = true; } catch (e) { hasDisplay = false; }
      }
      var M = 28.8, BAND = 21.6;
      var P = {
        doc: doc, W: paper.wPt, H: paper.hPt, M: M, ink: !!opts.ink, stamp: opts.stamp !== false,
        box: { x: M, y: M, w: paper.wPt - 2 * M, h: paper.hPt - 2 * M - BAND },
        clean: clean,
        color: function (name) { return (P.ink && GREY[name]) || COLORS[name] || COLORS.ink; },
        fill: function (n) { var c = P.color(n); doc.setFillColor(c[0], c[1], c[2]); return P; },
        stroke: function (n) { var c = P.color(n); doc.setDrawColor(c[0], c[1], c[2]); return P; },
        textColor: function (n) { var c = P.color(n); doc.setTextColor(c[0], c[1], c[2]); return P; },
        /* font('display' | 'body' | 'bold' | 'italic', sizePt) */
        font: function (kind, size) {
          if (kind === 'display' && hasDisplay) doc.setFont('Fredoka', 'normal');
          else doc.setFont('helvetica', kind === 'bold' || kind === 'display' ? 'bold' : kind === 'italic' ? 'italic' : 'normal');
          if (size) doc.setFontSize(size);
          return P;
        },
        width: function (text, size) { return doc.getStringUnitWidth(clean(text)) * (size || doc.getFontSize()); },
        /* largest size <= max (and >= min) at which text fits maxW */
        fit: function (text, maxW, max, min) {
          var s = max;
          while (s > (min || 6) && P.width(text, s) > maxW) s -= 0.5;
          return s;
        },
        text: function (t, x, y, o) { doc.text(clean(t), x, y, o || {}); return P; },
        center: function (t, cx, y) { doc.text(clean(t), cx, y, { align: 'center' }); return P; },
        wrap: function (t, maxW) { return doc.splitTextToSize(clean(t), maxW); },
        roundRect: function (x, y, w, h, r, style) { doc.roundedRect(x, y, w, h, r, r, style || 'S'); return P; },
        addPage: function () { doc.addPage(); return P; },
        /* Standard sheet header matching the HTML .sh-head: title left, Name line right, rule below. Returns y below. */
        header: function (title, sub, opts2) {
          opts2 = opts2 || {};
          var b = P.box, nameW = opts2.noName ? 0 : 170;
          var size = P.fit(title, b.w - nameW - 18, 24, 12);
          P.font('display', size).textColor('accent').text(title, b.x, b.y + size * 0.95);
          if (!opts2.noName) {
            P.font('body', 10.5).textColor('ink');
            var lx = b.x + b.w - 122, ly = b.y + size * 0.95;
            P.text('Name', lx - 30, ly);
            doc.setLineWidth(0.75); P.stroke('line'); doc.line(lx, ly + 2, b.x + b.w, ly + 2);
          }
          var y = b.y + size * 1.15;
          if (sub) { P.font('body', 10).textColor('muted').text(sub, b.x, y + 10); y += 14; }
          if (opts2.key) {
            P.font('bold', 9); var kw = P.width('ANSWER KEY', 9) + 10;
            P.fill('highlight').roundRect(b.x + b.w - kw, y - 3, kw, 14, 3, 'F');
            P.textColor('ink').text('ANSWER KEY', b.x + b.w - kw + 5, y + 7.5);
            y += 6;
          }
          y += 6;
          doc.setLineWidth(2.2); P.stroke('accent'); doc.line(b.x, y, b.x + b.w, y);
          P.textColor('ink');
          return y + 14;
        },
        /* Simple vector frog (matches the mascot). x,y = top-left, s = size in pt. */
        frog: function (x, y, s) {
          var k = s / 200, g = P.ink;
          function c(hex, grey) { var v = g ? grey : hex; doc.setFillColor(v[0], v[1], v[2]); }
          function E(cx, cy, rx, ry) { doc.ellipse(x + cx * k, y + cy * k, rx * k, ry * k, 'F'); }
          c([47, 143, 91], [90, 90, 90]); E(52, 160, 30, 23); E(148, 160, 30, 23); E(42, 181, 22, 8); E(158, 181, 22, 8);
          c([93, 181, 114], [150, 150, 150]); E(100, 143, 56, 44);
          c([255, 249, 236], [245, 245, 245]); E(100, 152, 36, 30);
          c([47, 143, 91], [90, 90, 90]); E(74, 182, 15, 7); E(126, 182, 15, 7);
          c([93, 181, 114], [150, 150, 150]); E(100, 97, 68, 45); E(64, 60, 24, 24); E(136, 60, 24, 24);
          c([255, 255, 255], [255, 255, 255]); E(64, 60, 16, 16); E(136, 60, 16, 16);
          c([31, 42, 36], [31, 31, 31]); E(66, 62, 9, 9); E(138, 62, 9, 9);
          c([247, 190, 184], [215, 215, 215]); E(52, 106, 10, 6); E(148, 106, 10, 6);
          doc.setDrawColor(31, 42, 36); doc.setLineWidth(4.5 * k); doc.setLineCap('round');
          doc.lines([[13.33 * k, 10.67 * k, 26.67 * k, 10.67 * k, 40 * k, 0]], x + 80 * k, y + 110 * k, [1, 1], 'S', false);
          doc.setLineCap('butt');
          return P;
        },
        finish: function () {
          var n = doc.getNumberOfPages();
          for (var i = 1; i <= n; i++) {
            doc.setPage(i);
            P.font('body', 8); doc.setTextColor(128, 128, 128);
            doc.text('Made free at frogsdream.com', P.W / 2, P.H - M - 4, { align: 'center' });
            if (P.stamp) P.frog(P.W - M - 26, P.H - M - 26, 26);
          }
          doc.setProperties({ title: clean(opts.title || "Frog's Dream printable"), creator: "Frog's Dream (frogsdream.com)" });
          return P;
        },
        save: function (name) { P.finish(); doc.save(name || 'frogsdream.pdf'); },
        blob: function () { P.finish(); return doc.output('blob'); }
      };
      return P;
    });
  }

  FD.pdf = { SRC: SRC, load: load, create: create, clean: clean };
})(window.FD = window.FD || {});
