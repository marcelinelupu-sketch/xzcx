/* Frog's Dream bingo caller (custom shell, no toolkit). 75-ball, 90-ball and custom word games with a big display,
   called board, last 5 calls, undo, auto-call, optional speech (speechSynthesis), projector mode and a saved game
   (localStorage fd:caller). Markup lives in tools/caller.controls.html. */
(function (FD) {
  'use strict';
  var KEY = 'fd:caller', LET = ['B', 'I', 'N', 'G', 'O'];
  /* Traditional UK bingo calls, family-friendly selection. */
  var UK = ['', "Kelly's eye", 'One little duck', 'Cup of tea', 'Knock at the door', 'Man alive', 'Half a dozen', 'Lucky seven', 'Garden gate', "Doctor's orders",
    'A big fat hen', 'Legs eleven', 'One dozen', 'Unlucky for some', "Valentine's Day", 'Young and keen', 'Sweet sixteen', 'Dancing queen', 'Coming of age', 'Goodbye teens',
    'One score', 'Key of the door', 'Two little ducks', 'Thee and me', 'Two dozen', 'Duck and dive', 'Pick and mix', 'Gateway to heaven', 'In a state', 'Rise and shine',
    'Burlington Bertie', 'Get up and run', 'Buckle my shoe', 'All the threes', 'Ask for more', 'Jump and jive', 'Three dozen', 'A flea in heaven', 'Christmas cake', 'Thirty-nine steps',
    'Naughty forty', 'Time for fun', 'Forty-second Street', 'Down on your knees', 'Droopy drawers', 'Halfway there', 'Up to tricks', 'Four and seven', 'Four dozen', 'Nick nick',
    'Half a century', 'Tweak of the thumb', 'Deck of cards', 'Stuck in the tree', 'Clean the floor', 'Snakes alive', 'Pick up sticks', 'Five and seven', 'Make them wait', 'Brighton line',
    'Five dozen', "Baker's bun", 'Tickety-boo', 'Tickle me', 'Red raw', 'Stop work', 'Clickety click', 'Made in heaven', 'Saving grace', 'Either way up',
    'Three score and ten', 'Bang on the drum', 'Six dozen', 'Queen bee', 'Candy store', 'Strive and strive', 'Trombones', 'Sunset strip', 'Thirty-nine more steps', 'One more time',
    'Eight and blank', 'Stop and run', 'Straight on through', 'Time for tea', 'Seven dozen', 'Staying alive', 'Between the sticks', 'Torquay in Devon', 'Two snowmen', 'Nearly there',
    'Top of the shop'];
  var ONES = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'];
  var TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'];
  function words(n) { return n < 20 ? ONES[n] : TENS[Math.floor(n / 10)] + (n % 10 ? '-' + ONES[n % 10] : ''); }

  var $ = function (id) { return document.getElementById(id); };
  var el = {}, data = {}, st = null, items = [], timer = null, themes = null;

  function load() { try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { return null; } }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { /* storage is optional */ } }
  function seed() { return FD.rng && FD.rng.newSeed ? FD.rng.newSeed() : (Math.random() * 4294967296) >>> 0; }
  function listLines(text) { return String(text || '').split(/\r?\n/).map(function (s) { return s.trim(); }).filter(Boolean); }
  /* "12 | 7 + 5" calls the problem; "Pine cone | 3" (points) calls the item */
  function lineText(l) { var p = l.split('|'), c = (p[1] || '').trim(); return c && !/^\d+$/.test(c) ? c : p[0].trim(); }
  function itemText(i) { return typeof i === 'string' ? i : i.call || i.square || i.text || ''; }

  /* Items for a game: {k: board label, big: display, say: spoken text} */
  function makeItems(mode, list) {
    var out = [], n;
    if (mode === '75') for (n = 1; n <= 75; n++) out.push({ k: String(n), big: LET[Math.floor((n - 1) / 15)] + ' ' + n, say: LET[Math.floor((n - 1) / 15)] + ', ' + n });
    else if (mode === '90') for (n = 1; n <= 90; n++) out.push({ k: String(n), big: String(n), say: String(n), uk: UK[n] + ', ' + (n < 10 ? 'number ' : '') + words(n) });
    else {
      var seen = {};
      list.forEach(function (l) { var t = lineText(l), k = t.toLowerCase(); if (t && !seen[k]) { seen[k] = 1; out.push({ k: t, big: t, say: t }); } });
    }
    return out;
  }

  function newGame(quiet) {
    stopAuto();
    var mode = el.mode.value, list = listLines(el.list.value);
    var its = makeItems(mode, list);
    if (mode === 'words' && its.length < 2) { msg('Add at least 2 words to call, one per line.', 'err'); el.next.disabled = true; return false; }
    var order = its.map(function (_, i) { return i; });
    order = FD.rng.shuffle(order, FD.rng.create(seed()));
    st = { mode: mode, list: list, order: order, pos: 0, uk: el.uk.checked, voice: el.voice.checked, vname: el.vname.value, secs: +el.secs.value };
    items = its;
    if (!quiet) save(); /* a first visit stores nothing until the visitor does something */
    draw(true);
    if (!quiet) { msg('New game ready with ' + its.length + (mode === 'words' ? ' words.' : ' numbers.'), ''); announce('Ready', 'Press Call next or the space bar to start.'); }
    return true;
  }
  function msg(t, kind) { el.msg.textContent = t; el.msg.className = 'field-msg' + (kind ? ' ' + kind : ''); }
  function announce(big, say) {
    var n = String(big).split(/\s+/).reduce(function (m, w) { return Math.max(m, w.length); }, 3);
    el.big.style.setProperty('--n', n + 1); /* longest word sets the size so it never breaks mid-word */
    el.big.textContent = big; el.say.textContent = say || '';
  }
  function inGame() { return st && st.pos > 0 && st.pos < st.order.length; }

  function call() {
    if (!st || st.pos >= st.order.length || el.next.disabled) { stopAuto(); return; }
    st.pos++;
    save(); draw();
    var it = items[st.order[st.pos - 1]];
    if (st.voice) speak(st.mode === '90' && st.uk ? it.uk : it.say);
    if (st.pos >= st.order.length) { stopAuto(); msg('Every ' + (st.mode === 'words' ? 'word' : 'number') + ' has been called.', ''); }
  }
  function undo() {
    if (!st || !st.pos) return;
    stopAuto();
    st.pos--;
    save(); draw();
    if (!st.pos) announce('Ready', 'Press Call next or the space bar to start.');
  }

  function draw(rebuild) {
    if (rebuild || el.board.getAttribute('data-mode') !== st.mode) buildBoard();
    var called = {}, i;
    for (i = 0; i < st.pos; i++) called[st.order[i]] = 1;
    var cells = el.board.children;
    for (i = 0; i < cells.length; i++) {
      var idx = cells[i].getAttribute('data-i');
      if (idx === null) continue;
      cells[i].classList.toggle('on', !!called[idx]);
      cells[i].classList.toggle('now', st.pos > 0 && +idx === st.order[st.pos - 1]);
    }
    if (st.pos) {
      var it = items[st.order[st.pos - 1]];
      announce(it.big, st.mode === '90' && st.uk ? it.uk : '');
    }
    el.count.textContent = st.pos + ' of ' + items.length + ' called';
    el.last.textContent = '';
    for (i = st.pos - 1; i >= Math.max(0, st.pos - 5); i--) {
      var li = document.createElement('li'); li.textContent = items[st.order[i]].big; el.last.appendChild(li);
    }
    el.next.disabled = st.pos >= items.length;
    el.undo.disabled = !st.pos;
    el.root.setAttribute('data-cm', st.mode);
  }
  function buildBoard() {
    var b = el.board, frag = document.createDocumentFragment();
    b.textContent = '';
    b.setAttribute('data-mode', st.mode);
    items.forEach(function (it, i) {
      if (st.mode === '75' && i % 15 === 0) {
        var h = document.createElement('span'); h.className = 'cl-l'; h.textContent = LET[i / 15]; h.setAttribute('aria-hidden', 'true'); frag.appendChild(h);
      }
      var c = document.createElement('span');
      c.className = 'cl-c'; c.setAttribute('data-i', i); c.setAttribute('role', 'listitem'); c.textContent = st.mode === 'words' ? it.big : it.k;
      frag.appendChild(c);
    });
    b.appendChild(frag);
  }

  /* ---------- auto-call ---------- */
  function startAuto() {
    if (!st || st.pos >= items.length) return;
    stopAuto();
    timer = setInterval(call, Math.max(2, st.secs || 8) * 1000);
    el.auto.setAttribute('aria-pressed', 'true'); el.auto.textContent = 'Stop auto-call';
    call();
  }
  function stopAuto() {
    if (timer) clearInterval(timer);
    timer = null;
    el.auto.setAttribute('aria-pressed', 'false'); el.auto.textContent = 'Auto-call';
  }

  /* ---------- speech ---------- */
  var synth = window.speechSynthesis;
  function voices() {
    if (!synth) return [];
    return synth.getVoices().filter(function (v) { return /^en[-_](US|GB)/i.test(v.lang); });
  }
  function fillVoices() {
    var vs = voices(), cur = (st && st.vname) || el.vname.value;
    el.vname.length = 1;
    vs.forEach(function (v) { var o = document.createElement('option'); o.value = v.name; o.textContent = v.name + ' (' + v.lang.replace('_', '-') + ')'; el.vname.appendChild(o); });
    el.vname.value = cur;
    if (el.vname.value !== cur) el.vname.value = '';
  }
  function speak(text) {
    if (!synth || !text) return;
    try {
      synth.cancel();
      var u = new SpeechSynthesisUtterance(text), name = st.vname;
      var v = voices().filter(function (x) { return x.name === name; })[0] ||
        voices().filter(function (x) { return st.mode === '90' ? /GB/.test(x.lang) : /US/.test(x.lang); })[0];
      if (v) { u.voice = v; u.lang = v.lang; } else u.lang = st.mode === '90' ? 'en-GB' : 'en-US';
      u.rate = 0.92;
      synth.speak(u);
    } catch (e) { /* speech is optional */ }
  }

  /* ---------- themed lists ---------- */
  function loadThemes() {
    if (themes) return;
    themes = [];
    fetch('/assets/js/themes.json').then(function (r) { return r.json(); }).then(function (all) {
      var groups = {};
      all.filter(function (t) { return (t.items || []).length && typeof (t.items[0]) !== 'undefined'; }).forEach(function (t) {
        var g = t.section === 'bingo' ? 'Bingo themes' : t.section === 'word-search' ? 'Word search themes' : t.section === 'word-scramble' ? 'Word scramble themes' : '';
        if (!g) return;
        (groups[g] = groups[g] || []).push(t);
      });
      ['Bingo themes', 'Word search themes', 'Word scramble themes'].forEach(function (g) {
        if (!groups[g]) return;
        var og = document.createElement('optgroup'); og.label = g;
        groups[g].sort(function (a, b) { return a.title.localeCompare(b.title); }).forEach(function (t) {
          themes.push(t);
          var o = document.createElement('option'); o.value = String(themes.length - 1); o.textContent = t.title; og.appendChild(o);
        });
        el.theme.appendChild(og);
      });
    }).catch(function () { themes = null; msg('The themed lists could not load. You can still paste your own words.', 'warn'); });
  }

  /* ---------- projector mode ---------- */
  function fsEl() { return document.fullscreenElement || document.webkitFullscreenElement; }
  function toggleFull() {
    var r = el.root;
    if (fsEl()) { (document.exitFullscreen || document.webkitExitFullscreen).call(document); return; }
    if (r.classList.contains('cl-proj')) { r.classList.remove('cl-proj'); return; }
    var req = r.requestFullscreen || r.webkitRequestFullscreen;
    r.classList.add('cl-proj');
    if (req) { try { var p = req.call(r); if (p && p.catch) p.catch(function () {}); } catch (e) { /* fall back to the in-page view */ } }
  }
  function onFs() {
    var on = !!fsEl();
    el.root.classList.toggle('cl-proj', on);
    el.full.textContent = on ? 'Exit projector mode' : 'Projector mode';
  }

  function countWords() { var n = listLines(el.list.value).length; el.n.textContent = n + (n === 1 ? ' word' : ' words'); }
  function settingsChanged() {
    countWords();
    if (inGame()) { msg('Press "Start a new game with these settings" to switch. The current game stays until then.', 'warn'); return; }
    newGame(false);
  }

  function start() {
    el.root = $('tool');
    if (!el.root || !$('cl')) return;
    ['big', 'say', 'next', 'undo', 'auto', 'full', 'new', 'count', 'last', 'board', 'mode', 'secs', 'theme', 'list', 'n', 'uk', 'voice', 'vname', 'msg', 'apply']
      .forEach(function (k) { el[k] = $('cl-' + k); });
    try { data = JSON.parse(($('fd-data') || {}).textContent || '{}'); } catch (e) { data = {}; }
    var saved = load(), o = data.options || {};
    el.list.value = (data.lines || []).join('\n');
    el.mode.value = o.mode === '90' || o.mode === 'words' ? o.mode : '75';
    if (saved && saved.order && saved.order.length) {
      el.mode.value = saved.mode; el.list.value = (saved.list || []).join('\n');
      el.uk.checked = !!saved.uk; el.voice.checked = !!saved.voice; el.secs.value = String(saved.secs || 8);
      var its = makeItems(saved.mode, saved.list || []);
      if (its.length === saved.order.length) { st = saved; items = its; st.pos = Math.min(st.pos, items.length); }
    }
    if (st) { draw(true); if (st.pos) msg('Your last game is restored. ' + st.pos + ' already called.', ''); }
    else newGame(true);
    countWords();
    fillVoices();
    if (synth && 'onvoiceschanged' in synth) synth.addEventListener('voiceschanged', fillVoices);
    if (!synth) { el.voice.disabled = true; el.vname.disabled = true; el.voice.parentNode.title = 'Speech is not available in this browser'; }

    el.next.addEventListener('click', call);
    el.undo.addEventListener('click', undo);
    el.auto.addEventListener('click', function () { if (timer) stopAuto(); else startAuto(); });
    el.full.addEventListener('click', toggleFull);
    el.new.addEventListener('click', function () { if (!inGame() || window.confirm('Start a new game? The called list will be cleared.')) newGame(false); });
    el.apply.addEventListener('click', function () { if (!inGame() || window.confirm('Start a new game? The called list will be cleared.')) newGame(false); });
    el.mode.addEventListener('change', function () { el.root.setAttribute('data-sm', el.mode.value); if (el.mode.value === 'words') loadThemes(); settingsChanged(); });
    var lt; el.list.addEventListener('input', function () { countWords(); clearTimeout(lt); lt = setTimeout(function () { if (el.mode.value === 'words') settingsChanged(); }, 600); });
    el.theme.addEventListener('focus', loadThemes);
    el.theme.addEventListener('change', function () {
      var t = themes && themes[+el.theme.value];
      if (!t || el.theme.value === '') return;
      el.list.value = t.items.map(itemText).filter(Boolean).join('\n');
      settingsChanged();
    });
    el.secs.addEventListener('change', function () { st.secs = +el.secs.value; save(); if (timer) { stopAuto(); startAuto(); } });
    el.uk.addEventListener('change', function () { st.uk = el.uk.checked; save(); draw(); });
    el.voice.addEventListener('change', function () { st.voice = el.voice.checked; save(); if (st.voice) speak('Voice on'); });
    el.vname.addEventListener('change', function () { st.vname = el.vname.value; save(); if (st.voice) speak('Hello'); });
    document.addEventListener('fullscreenchange', onFs);
    document.addEventListener('webkitfullscreenchange', onFs);
    document.addEventListener('keydown', function (e) {
      var t = e.target, tag = t && t.tagName;
      if (e.key === 'Escape' && el.root.classList.contains('cl-proj') && !fsEl()) { el.root.classList.remove('cl-proj'); return; }
      if ((e.key !== ' ' && e.code !== 'Space') || e.ctrlKey || e.metaKey || e.altKey) return;
      if (/^(INPUT|TEXTAREA|SELECT|BUTTON|A|SUMMARY)$/.test(tag || '') || (t && t.isContentEditable)) return;
      e.preventDefault();
      call();
    });
    el.root.setAttribute('data-sm', el.mode.value);
    if (el.mode.value === 'words') loadThemes();
    [el.next, el.auto, el.full, el.new, el.apply].forEach(function (b) { b.disabled = false; });
    el.next.disabled = st.pos >= items.length;
  }

  FD.caller = { makeItems: makeItems, UK: UK, words: words };
  if (document.readyState !== 'loading') start(); else document.addEventListener('DOMContentLoaded', start);
})(window.FD = window.FD || {});
