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
    P.viewedChapters().forEach(function (n) {
      document.querySelectorAll('.ch-row[data-chap="' + n + '"]').forEach(function (a) { a.classList.add("rp-viewed"); });
    });
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
