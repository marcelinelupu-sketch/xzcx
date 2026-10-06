/* Grammar book page behaviour: vocabulary popups and the exercise engine.
 * Reads window.CHAPTER (number), window.VOCAB ({id: {def, tr: {lang: text}}}) and
 * window.EXERCISES ({sets: [...]}) which the build writes into each page.
 * Records progress through window.RhymeProgress (progress.js). */
(function () {
  "use strict";
  var N = window.CHAPTER;
  function lang() { try { return localStorage.getItem("bLang") || ""; } catch (e) { return ""; } }
  var P = window.RhymeProgress;

  /* ---------- vocabulary ---------- */
  var tip = document.createElement("div");
  tip.id = "vtip";
  document.body.appendChild(tip);
  var hoverable = window.matchMedia("(hover:hover)").matches;

  function place(el, target) {
    var r = target.getBoundingClientRect();
    el.style.top = (r.bottom + window.scrollY + 8) + "px";
    var left = r.left + window.scrollX + r.width / 2;
    el.style.left = Math.min(Math.max(left, 140), window.scrollX + document.documentElement.clientWidth - 140) + "px";
    el.style.transform = "translateX(-50%)";
  }
  function entry(span) { return (window.VOCAB || {})[span.dataset.id] || null; }
  function translation(span) {
    var v = entry(span), l = lang();
    return v && v.tr && l && v.tr[l] ? v.tr[l] : null;
  }
  function show(span, mode) {
    var v = entry(span), tr = translation(span);
    if (mode === "tr" && tr) { tip.textContent = tr; span.classList.add("translated"); }
    else {
      tip.textContent = (v && v.def) || span.dataset.def || "";
      if (tr) { var s = document.createElement("small"); s.textContent = hoverable ? "click for translation" : "tap again for translation"; tip.appendChild(s); }
    }
    span.dataset.mode = mode;
    place(tip, span);
    tip.classList.add("show");
  }
  function hide() { tip.classList.remove("show"); }

  function bind(root) {
    (root || document).querySelectorAll(".v:not([data-bound])").forEach(function (span) {
      span.dataset.bound = "1";
      if (hoverable) {
        span.addEventListener("mouseenter", function () { show(span, span.classList.contains("translated") ? "tr" : "def"); });
        span.addEventListener("mouseleave", hide);
        span.addEventListener("click", function (e) { e.preventDefault(); e.stopPropagation(); show(span, "tr"); });
      } else {
        span.addEventListener("click", function (e) {
          e.preventDefault(); e.stopPropagation();
          var open = tip.classList.contains("show") && tip._for === span;
          show(span, open && span.dataset.mode === "def" ? "tr" : "def");
          tip._for = span;
        });
      }
    });
  }
  window.BookVocab = { bind: bind };
  bind(document);
  document.addEventListener("click", hide);
  window.addEventListener("scroll", function () { if (!hoverable) hide(); }, { passive: true });

  /* ---------- exercises ---------- */
  var EX = window.EXERCISES;
  var root = document.getElementById("exercises");
  var total = 0;
  if (EX && EX.sets && root) EX.sets.forEach(function (s) { total += (s.items || []).length; });

  if (P && N) P.viewed(N, total);
  if (!total || !root) return;

  var answered = 0, firstRight = 0;
  var scoreEl = document.createElement("p");
  scoreEl.className = "ex-score";
  var doneEl = document.createElement("div");
  doneEl.className = "ex-done";

  function norm(s) { return String(s).toLowerCase().replace(/[’']/g, "'").replace(/[.!?,;:]+$/g, "").replace(/\s+/g, " ").trim(); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }

  function refresh() {
    scoreEl.textContent = answered + " of " + total + " answered";
    if (answered < total) return;
    var c = P ? P.chapter(N) : null;
    var score = total ? firstRight / total : 1;
    if (c && c.score != null) score = c.score;
    var pct = Math.round(score * 100);
    if (score >= (P ? P.PASS : 0.8)) {
      doneEl.className = "ex-done show";
      doneEl.textContent = "Chapter complete · " + pct + "% right the first time";
    } else {
      doneEl.className = "ex-done show retry";
      doneEl.innerHTML = pct + "% right the first time. You need 80% to complete this chapter.<br>";
      var again = el("button", "ex-btn", "Try the exercises again");
      again.onclick = function () { if (P) P.resetExercises(N); location.reload(); };
      doneEl.appendChild(again);
    }
  }

  function makeItem(item, id) {
    var box = el("div", "ex-item");
    var first = true;
    function result(ok) {
      if (P) P.answered(N, id, ok);
      if (first) { if (ok) firstRight++; }
      if (ok) { box.classList.add("done"); answered++; refresh(); }
      first = false;
      return ok;
    }
    var why = el("p", "ex-why", item.why || "");
    var type = item.type;

    if (type === "choice") {
      box.appendChild(el("p", "ex-q", item.q));
      var opts = el("div", "ex-opts");
      item.options.forEach(function (o, i) {
        var b = el("button", "ex-btn", o);
        b.onclick = function () {
          if (box.classList.contains("done")) return;
          var ok = i === item.answer;
          b.classList.remove("no"); void b.offsetWidth;
          b.classList.add(ok ? "ok" : "no");
          if (result(ok)) opts.querySelectorAll("button").forEach(function (x) { x.disabled = true; });
        };
        opts.appendChild(b);
      });
      box.appendChild(opts);
    } else if (type === "gap") {
      var parts = String(item.q).split("___");
      var q = el("p", "ex-q");
      var input = el("input", "ex-in");
      input.setAttribute("aria-label", "answer");
      q.innerHTML = parts[0];
      q.appendChild(input);
      q.insertAdjacentHTML("beforeend", parts.slice(1).join("___"));
      box.appendChild(q);
      var check = el("button", "ex-btn", "Check");
      var accepted = (Array.isArray(item.answer) ? item.answer : [item.answer]).map(norm);
      function go() {
        if (box.classList.contains("done") || !input.value.trim()) return;
        var ok = accepted.indexOf(norm(input.value)) !== -1;
        input.classList.remove("no"); void input.offsetWidth;
        input.classList.add(ok ? "ok" : "no");
        if (result(ok)) { input.disabled = true; check.disabled = true; }
      }
      check.onclick = go;
      input.addEventListener("keydown", function (e) { if (e.key === "Enter") go(); });
      box.appendChild(el("div", "ex-opts")).appendChild(check);
    } else if (type === "order") {
      if (item.q) box.appendChild(el("p", "ex-q", item.q));
      var built = el("div", "ex-built");
      var pool = el("div", "ex-opts");
      var words = item.words.slice();
      // stable shuffle so the order is never the answer itself
      words = words.map(function (w, i) { return { w: w, k: (i * 7 + 3) % words.length }; }).sort(function (a, b) { return a.k - b.k; }).map(function (x) { return x.w; });
      if (words.join(" ") === item.words.join(" ") && words.length > 1) words.push(words.shift());
      words.forEach(function (w) {
        var b = el("button", "ex-btn", w);
        b.onclick = function () {
          if (box.classList.contains("done")) return;
          if (b.parentNode === pool) built.appendChild(b); else pool.appendChild(b);
          if (!pool.children.length) {
            var said = [].map.call(built.children, function (x) { return x.textContent; }).join(" ");
            var answers = (Array.isArray(item.answer) ? item.answer : [item.answer]).map(norm);
            var ok = answers.indexOf(norm(said)) !== -1;
            built.querySelectorAll("button").forEach(function (x) { x.classList.remove("no"); void x.offsetWidth; x.classList.add(ok ? "ok" : "no"); });
            if (result(ok)) built.querySelectorAll("button").forEach(function (x) { x.disabled = true; });
            else setTimeout(function () { [].slice.call(built.children).forEach(function (x) { x.classList.remove("no"); pool.appendChild(x); }); }, 700);
          }
        };
        pool.appendChild(b);
      });
      box.appendChild(built);
      box.appendChild(pool);
    } else if (type === "error") {
      if (item.q) box.appendChild(el("p", "ex-inst", item.q));
      var line = el("p", "ex-q");
      item.segments.forEach(function (seg, i) {
        var sp = el("span", "ex-seg", seg);
        sp.onclick = function () {
          if (box.classList.contains("done")) return;
          var ok = i === item.answer;
          sp.classList.remove("no"); void sp.offsetWidth;
          sp.classList.add(ok ? "ok" : "no");
          if (ok && item.fix) sp.innerHTML = seg + " → <strong>" + item.fix + "</strong>";
          result(ok);
        };
        line.appendChild(sp);
        line.appendChild(document.createTextNode(" "));
      });
      box.appendChild(line);
    }
    box.appendChild(why);
    return box;
  }

  var head = el("div", "ex-head");
  head.appendChild(el("h2", "", "Practice"));
  head.appendChild(scoreEl);
  root.appendChild(head);
  EX.sets.forEach(function (s, si) {
    var set = el("section", "ex-set");
    set.appendChild(el("h3", "", s.title || ("Exercise " + (si + 1))));
    if (s.instruction) set.appendChild(el("p", "ex-inst", s.instruction));
    (s.items || []).forEach(function (item, ii) {
      if (!item.type) item.type = s.type;
      set.appendChild(makeItem(item, "s" + si + "i" + ii));
    });
    root.appendChild(set);
  });
  root.appendChild(doneEl);
  bind(root);

  // restore solved items from earlier visits
  if (P) {
    var c = P.chapter(N);
    var solved = Object.keys(c.items || {}).filter(function (k) { return c.items[k].solved; });
    firstRight = Object.keys(c.items || {}).filter(function (k) { return c.items[k].firstCorrect; }).length;
    answered = solved.length;
    solved.forEach(function (k) {
      var m = /^s(\d+)i(\d+)$/.exec(k); if (!m) return;
      var set = root.querySelectorAll(".ex-set")[+m[1]]; if (!set) return;
      var it = set.querySelectorAll(".ex-item")[+m[2]]; if (!it) return;
      it.classList.add("done");
      it.querySelectorAll("button,input").forEach(function (x) { x.disabled = true; });
      var item = EX.sets[+m[1]].items[+m[2]];
      if (item.type === "choice") { var b = it.querySelectorAll(".ex-btn")[item.answer]; if (b) b.classList.add("ok"); }
      if (item.type === "gap") { var inp = it.querySelector("input"); if (inp) { inp.value = [].concat(item.answer)[0]; inp.classList.add("ok"); } }
      if (item.type === "error") { var sg = it.querySelectorAll(".ex-seg")[item.answer]; if (sg) { sg.classList.add("ok"); if (item.fix) sg.innerHTML += " → <strong>" + item.fix + "</strong>"; } }
      if (item.type === "order") { var pl = it.querySelector(".ex-opts"); if (pl) pl.innerHTML = ""; var bl = it.querySelector(".ex-built"); bl.innerHTML = ""; [].concat(item.answer)[0].split(" ").forEach(function (w) { var x = el("button", "ex-btn ok", w); x.disabled = true; bl.appendChild(x); }); }
    });
  }
  refresh();
  if (P) P.sync();
})();
