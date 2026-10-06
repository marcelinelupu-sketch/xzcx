/* Connects the TOC to RhymeProgress: chapters a learner completed (all exercises done, 80% right
 * on the first attempt) get their checkmark; chapters they opened get a small gold dot. */
(function () {
  "use strict";
  function apply() {
    var P = window.RhymeProgress;
    if (!P) return;
    try {
      if (typeof completed !== "undefined") {
        P.completedChapters().forEach(function (n) { completed.add(n); });
        if (typeof saveProgress === "function") saveProgress();
        if (typeof updateBadges === "function") updateBadges();
        if (typeof layoutGutters === "function") layoutGutters();
      }
    } catch (e) {}
    vocab();
    P.viewedChapters().forEach(function (n) {
      document.querySelectorAll('.ch-row[data-chap="' + n + '"]').forEach(function (a) { a.classList.add("rp-viewed"); });
    });
  }
  /* underline every word with meaning in chapter titles and descriptions (glossary from toc-vocab.js) */
  function vocab() {
    var map = window.TOCVOCAB;
    if (!map) return;
    document.querySelectorAll(".ch-row[data-chap]:not([data-vocab])").forEach(function (row) {
      row.dataset.vocab = "1";
      var words = map[row.dataset.chap];
      if (!words) return;
      row.querySelectorAll(".ch-title, .ch-desc").forEach(function (el) {
        var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
          acceptNode: function (t) { return t.parentNode.closest(".term, .term-title, .v, .ch-num, .star, .placeholder") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; }
        });
        var nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach(function (t) {
          var html = t.nodeValue.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/[A-Za-z]+(?:['’][A-Za-z]+)?/g, function (w) {
            var sid = words[w.toLowerCase().replace("’", "'")];
            return sid ? '<span class="v" data-id="' + sid + '">' + w + "</span>" : w;
          });
          if (html === t.nodeValue) return;
          var tmp = document.createElement("span");
          tmp.innerHTML = html;
          while (tmp.firstChild) t.parentNode.insertBefore(tmp.firstChild, t);
          t.parentNode.removeChild(t);
        });
      });
    });
    if (window.BookVocab) window.BookVocab.bind(document);
  }

  if (typeof window.renderTOC === "function") {
    var original = window.renderTOC;
    window.renderTOC = function () { var r = original.apply(this, arguments); apply(); return r; };
  }
  window.addEventListener("rhyme-progress", apply);
  window.addEventListener("pageshow", apply);
  document.addEventListener("DOMContentLoaded", apply);
  setTimeout(apply, 300);
  if (window.RhymeProgress) window.RhymeProgress.sync();
})();
