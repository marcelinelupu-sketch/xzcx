/* Frog's Dream toolkit.js: the shared generator shell. A tool file calls FD.tool.register({...});
   this file wires the standard controls (title, list, paper, ink saver, frog stamp, seed), the buttons
   (Generate, Print, Download PDF, Copy share link, Reset), share links, localStorage and preview scaling.
   See source/TOOL-CONTRACT.md for the full contract. */
(function (FD) {
  'use strict';
  var def = null, started = false, dirty = false, clamped = [], data = {}, els = {}, model = null, cur = null, defaults = null, timer = null, formDefaults = {};
  var $ = function (id) { return document.getElementById(id); };

  /* ---------- tiny DOM builder: FD.h('div', {class: 'x', style: 'y'}, child, 'text', [more]) ---------- */
  FD.h = function (tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (attrs[k] == null || attrs[k] === false) continue;
      if (k === 'text') el.textContent = attrs[k];
      else if (k === 'html') el.innerHTML = attrs[k];
      else el.setAttribute(k === 'cls' ? 'class' : k, attrs[k] === true ? '' : attrs[k]);
    }
    (function add(list) {
      for (var i = 0; i < list.length; i++) {
        var c = list[i];
        if (c == null || c === false) continue;
        if (Array.isArray(c)) add(c); else el.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)));
      }
    })(Array.prototype.slice.call(arguments, 2));
    return el;
  };
  /* Small mascot SVG (for printed sheets, FREE squares, etc.). */
  FD.frogSVG = function (cls) {
    return '<svg class="' + (cls || '') + '" viewBox="0 0 200 200" aria-hidden="true"><ellipse cx="52" cy="160" rx="30" ry="23" fill="#2F8F5B"/><ellipse cx="148" cy="160" rx="30" ry="23" fill="#2F8F5B"/><ellipse cx="42" cy="181" rx="22" ry="8" fill="#2F8F5B"/><ellipse cx="158" cy="181" rx="22" ry="8" fill="#2F8F5B"/><ellipse cx="100" cy="143" rx="56" ry="44" fill="#5DB572"/><ellipse cx="100" cy="152" rx="36" ry="30" fill="#FFF9EC"/><ellipse cx="74" cy="182" rx="15" ry="7" fill="#2F8F5B"/><ellipse cx="126" cy="182" rx="15" ry="7" fill="#2F8F5B"/><ellipse cx="100" cy="97" rx="68" ry="45" fill="#5DB572"/><circle cx="64" cy="60" r="24" fill="#5DB572"/><circle cx="136" cy="60" r="24" fill="#5DB572"/><circle cx="64" cy="60" r="16" fill="#fff"/><circle cx="136" cy="60" r="16" fill="#fff"/><circle cx="66" cy="62" r="9" fill="#1F2A24"/><circle cx="138" cy="62" r="9" fill="#1F2A24"/><circle cx="69" cy="58" r="3" fill="#fff"/><circle cx="141" cy="58" r="3" fill="#fff"/><ellipse cx="52" cy="106" rx="10" ry="6" fill="#F4A09A"/><ellipse cx="148" cy="106" rx="10" ry="6" fill="#F4A09A"/><path d="M80 110q20 16 40 0" fill="none" stroke="#1F2A24" stroke-width="4.5" stroke-linecap="round"/></svg>';
  };

  /* ---------- share-link encoding: base64url(JSON) ---------- */
  function b64e(obj) {
    var s = unescape(encodeURIComponent(JSON.stringify(obj)));
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function b64d(str) {
    str = str.replace(/-/g, '+').replace(/_/g, '/');
    while (str.length % 4) str += '=';
    return JSON.parse(decodeURIComponent(escape(atob(str))));
  }
  FD.share = { encode: b64e, decode: b64d };

  function store(key, val) {
    try { if (val === undefined) return JSON.parse(localStorage.getItem(key) || 'null'); localStorage.setItem(key, JSON.stringify(val)); } catch (e) { return null; }
    return null;
  }

  /* ---------- form <-> state ---------- */
  function lines() { return els.words.value.split(/\r?\n/).map(function (s) { return s.trim(); }).filter(Boolean); }
  function optFields() { return els.partial ? FD.$$('[name]', els.partial) : []; }
  function readOptions() {
    var o = {};
    optFields().forEach(function (el) {
      if (el.type === 'radio') { if (el.checked) o[el.name] = el.value; }
      else if (el.type === 'checkbox') o[el.name] = el.checked;
      else if (el.type === 'number' || el.type === 'range') {
        var v = parseFloat(el.value), lo = parseFloat(el.min), hi = parseFloat(el.max);
        if (isNaN(v)) v = parseFloat(el.defaultValue) || 0;
        var raw = v;
        if (!isNaN(lo)) v = Math.max(lo, v);
        if (!isNaN(hi)) v = Math.min(hi, v);
        if (v !== raw && el.value !== '') {  /* say so honestly instead of clamping silently */
          el.value = v;
          var lab = el.id && document.querySelector('label[for="' + el.id + '"]');
          clamped.push(el.name === 'cards' && hi === 30 ? 'The free generator makes up to 30 cards at a time.' :
            ((lab ? lab.textContent.trim() : el.name) + ' can be from ' + lo + ' to ' + hi + ', so it is set to ' + v + '.'));
        }
        o[el.name] = v;
      } else o[el.name] = el.value;
    });
    return o;
  }
  function writeOptions(o) {
    optFields().forEach(function (el) {
      if (!o || !(el.name in o)) return;
      var v = o[el.name];
      if (el.type === 'radio') el.checked = String(el.value) === String(v);
      else if (el.type === 'checkbox') el.checked = !!v;
      else el.value = v;
    });
  }
  function readState() {
    return {
      title: els.title.value.trim(), words: lines(), options: readOptions(),
      paper: els.paper.value, ink: els.ink.checked, stamp: els.stamp.checked, seed: (+els.seed.value) >>> 0
    };
  }
  function writeState(s) {
    els.title.value = s.title || '';
    els.words.value = (s.words || []).join('\n');
    writeOptions(Object.assign({}, formDefaults, s.options || {}));
    els.paper.value = s.paper === 'a4' ? 'a4' : 'letter';
    els.ink.checked = !!s.ink;
    els.stamp.checked = s.stamp !== false;
    els.seed.value = String((s.seed >>> 0) || FD.rng.newSeed());
  }

  /* ---------- context handed to build/render ---------- */
  function makeCtx(state) {
    var ctx = {
      state: state, seed: state.seed, rand: FD.rng.create(state.seed), paper: state.paper, ink: state.ink, stamp: state.stamp,
      data: data, warnings: [], errors: [],
      warn: function (m) { ctx.warnings.push(m); }, error: function (m) { ctx.errors.push(m); },
      /* Seeded sub-stream, e.g. ctx.sub('puzzle', 2) gives the same numbers for puzzle 2 every time. */
      sub: function () { return FD.rng.create(FD.rng.derive.apply(null, [state.seed].concat([].slice.call(arguments)))); },
      /* Append a page. Returns the .sheet-body element to fill. opts.key=true marks an answer key page. */
      sheet: function (opts) {
        opts = opts || {};
        var body = FD.h('div', { cls: 'sheet-body' });
        var sheet = FD.h('div', { cls: 'sheet' + (opts.cls ? ' ' + opts.cls : '') + (opts.key ? ' sheet-key' : ''), 'aria-label': opts.label || null }, body,
          FD.h('div', { cls: 'sheet-credit', text: 'Made free at frogsdream.com' }));
        if (state.stamp) sheet.insertAdjacentHTML('beforeend', FD.frogSVG('sheet-stamp'));
        els.sheets.appendChild(FD.h('div', { cls: 'sheet-frame' }, sheet));
        return body;
      },
      /* Standard header: big title, optional subtitle, Name line, ANSWER KEY badge */
      header: function (body, title, sub, o) {
        o = o || {};
        var left = FD.h('div', null, FD.h('h2', { cls: 'sh-title' }, title, o.key ? FD.h('span', { cls: 'sh-key', text: 'Answer key' }) : null),
          sub ? FD.h('p', { cls: 'sh-sub', text: sub }) : null);
        var right = o.noName ? null : FD.h('div', { cls: 'sh-name' }, 'Name', FD.h('span'));
        body.appendChild(FD.h('div', { cls: 'sh-head' }, left, right));
      }
    };
    return ctx;
  }

  function setMsg(text, kind) {
    els.msg.textContent = text || '';
    els.msg.className = 'field-msg' + (kind ? ' ' + kind : '');
  }
  function updateCount(n, bad) {
    var noun = def.noun || data.noun || 'items';
    els.count.textContent = n + ' ' + (n === 1 ? noun.replace(/s$/, '') : noun);
    els.count.classList.toggle('bad', !!bad);
  }

  /* ---------- the main pipeline ---------- */
  function generate(newSeed) {
    if (newSeed) els.seed.value = String(FD.rng.newSeed());
    clamped = [];
    var state = readState();
    cur = state;
    var ctx = makeCtx(state);
    clamped.forEach(ctx.warn);
    var parsed = def.parse ? def.parse(state.words, state, ctx) : state.words;
    ctx.items = parsed;
    updateCount(parsed.length, ctx.errors.length > 0);
    els.sheets.setAttribute('data-paper', state.paper);
    els.sheets.classList.toggle('ink', state.ink);
    if (ctx.errors.length) {  /* never leave old sheets printable when they no longer match the list */
      setMsg(ctx.errors.join(' '), 'err');
      model = null;
      els.sheets.textContent = '';
      els.status.textContent = 'Fix the list above to see a preview.';
      return;
    }
    model = def.build(state, ctx);
    els.sheets.textContent = '';
    def.render(model, ctx);
    var pages = els.sheets.children.length;
    setMsg(ctx.warnings.join(' ') || (def.hint || 'One per line. Edit, add or remove anything you like.'), ctx.warnings.length ? 'warn' : '');
    els.status.textContent = pages + (pages === 1 ? ' page' : ' pages') + ' ready \u00B7 ' + FD.print.PAPER[state.paper].label + (state.ink ? ' \u00B7 ink saver' : '');
    FD.print.setPage(state.paper);
    FD.print.fit(els.sheets);
    /* remember the list only after the visitor changed something, and never inside someone else's page (embed) */
    if (dirty && !data.embed) store('fd:' + def.id, { title: state.title, words: state.words, options: state.options });
    document.dispatchEvent(new CustomEvent('fd:rendered', { detail: { pages: pages, seed: state.seed } }));
  }
  function later() { clearTimeout(timer); timer = setTimeout(function () { generate(false); }, 250); }

  function downloadPdf() {
    if (!model || !def.pdf) return;
    var btn = els.pdfBtn, label = btn.textContent;
    btn.setAttribute('aria-busy', 'true'); btn.disabled = true; btn.textContent = 'Preparing PDF...';
    var state = cur, ctx = makeCtx(state);
    FD.pdf.create({ paper: state.paper, ink: state.ink, stamp: state.stamp, title: state.title }).then(function (P) {
      return Promise.resolve(def.pdf(model, P, ctx)).then(function () {
        var name = (state.title || def.id).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'frogsdream';
        P.save(name + '.pdf');
        FD.toast('PDF downloaded');
      });
    }).catch(function (e) { FD.toast(e && e.message ? e.message : 'PDF failed. Try Print, then Save as PDF.'); if (window.console) console.error(e); })
      .then(function () { btn.removeAttribute('aria-busy'); btn.disabled = false; btn.textContent = label; });
  }

  function shareLink() {
    var s = readState();
    var payload = { t: s.title, w: s.words, o: s.options, p: s.paper, i: s.ink ? 1 : 0, f: s.stamp ? 1 : 0, s: s.seed };
    var base = data.embed ? data.toolUrl : (data.url || location.href.split('#')[0].split('?')[0]);
    var url = base + '#s=' + b64e(payload);
    FD.copy(url).then(function () { FD.toast('Share link copied. Anyone who opens it gets these exact sheets.'); },
      function () { window.prompt('Copy this link:', url); });
  }

  function initialState() {
    var paper = FD.print.defaultPaper();
    defaults = { title: data.title || '', words: (data.lines || []).slice(), options: Object.assign({}, formDefaults, data.options || {}), paper: paper, ink: false, stamp: true, seed: 0 };
    var s = JSON.parse(JSON.stringify(defaults)), m = /[#&]s=([A-Za-z0-9_-]+)/.exec(location.hash), q = /[?&]seed=(\d+)/.exec(location.search);
    if (m) {
      try {
        var p = b64d(m[1]);
        s = { title: String(p.t || ''), words: (p.w || []).map(String), options: Object.assign({}, s.options, p.o || {}), paper: p.p || paper, ink: !!p.i, stamp: p.f !== 0, seed: p.s >>> 0 };
      } catch (e) { FD.toast('That share link looks broken, so the default list is shown.'); }
    } else if (!data.theme) {
      var saved = store('fd:' + def.id);
      if (saved && saved.words && saved.words.length) s = Object.assign(s, { title: saved.title || s.title, words: saved.words, options: Object.assign({}, s.options, saved.options || {}) });
    }
    if (q) s.seed = parseInt(q[1], 10) >>> 0;
    if (!s.seed) s.seed = FD.rng.newSeed();
    return s;
  }

  function start() {
    if (started || !def) return;
    var root = $('tool');
    if (!root) return;
    started = true;
    try { data = JSON.parse(($('fd-data') || {}).textContent || '{}'); } catch (e) { data = {}; }
    els = {
      root: root, form: $('fd-form'), title: $('fd-title'), words: $('fd-words'), count: $('fd-count'), msg: $('fd-msg'),
      partial: root.querySelector('[data-tool-partial]'), paper: $('fd-paper'), ink: $('fd-ink'), stamp: $('fd-stamp'), seed: $('fd-seed'),
      sheets: $('fd-sheets'), status: $('fd-status'), pdfBtn: $('fd-pdf')
    };
    formDefaults = readOptions();
    if (def.init) def.init(els, data);
    writeState(initialState());
    els.form.addEventListener('submit', function (e) { e.preventDefault(); generate(true); });
    els.form.addEventListener('input', function (e) { dirty = true; if (e.target === els.ink) return generate(false); later(); });
    els.form.addEventListener('change', function () { dirty = true; later(); });
    $('fd-print').addEventListener('click', function () { generate(false); if (!model) { FD.toast('Fix the list first, then print.'); return; } FD.print.print(cur.paper); });
    els.pdfBtn.addEventListener('click', downloadPdf);
    var sh = $('fd-share'); if (sh) sh.addEventListener('click', shareLink);
    var rs = $('fd-reset'); if (rs) rs.addEventListener('click', function () {
      var s = JSON.parse(JSON.stringify(defaults)); s.paper = els.paper.value; s.seed = FD.rng.newSeed();
      writeState(s);
      dirty = false;
      if (location.hash) history.replaceState(null, '', location.pathname + location.search);
      generate(false);
      FD.toast('Back to the original list');
    });
    var rt; window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(function () { FD.print.fit(els.sheets); }, 100); });
    generate(false);
  }

  FD.tool = {
    register: function (d) { def = d; if (document.readyState !== 'loading') start(); else document.addEventListener('DOMContentLoaded', start); },
    generate: function () { generate(true); },
    state: function () { return cur; },
    model: function () { return model; },
    pdf: downloadPdf
  };
})(window.FD = window.FD || {});
