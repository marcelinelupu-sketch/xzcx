/* frogsdream print.js: paper sizes, @page injection and preview scaling. */
(function (FD) {
  'use strict';
  var PAPER = {
    letter: { css: 'letter', label: 'US Letter', wIn: 8.5, hIn: 11, wPt: 612, hPt: 792 },
    a4: { css: 'A4', label: 'A4', wIn: 8.2677, hIn: 11.6929, wPt: 595.28, hPt: 841.89 }
  };
  var current = 'letter';
  function defaultPaper() {
    var l = (navigator.languages && navigator.languages[0]) || navigator.language || 'en-US';
    return /-US$/i.test(l) || /^en$/i.test(l) ? 'letter' : 'a4';
  }
  function setPage(paper) {
    current = PAPER[paper] ? paper : 'letter';
    var st = document.getElementById('fd-page');
    if (!st) { st = document.createElement('style'); st.id = 'fd-page'; document.head.appendChild(st); }
    st.textContent = '@page{size:' + PAPER[current].css + ';margin:.4in}';
  }
  function print(paper) { setPage(paper || current); window.print(); }
  /* Scale fixed-size .sheet elements to the width of their container. */
  function fit(sheets) {
    if (!sheets) return;
    var paper = PAPER[sheets.getAttribute('data-paper')] || PAPER.letter;
    var avail = sheets.clientWidth || sheets.parentNode.clientWidth;
    var s = Math.min(1, avail / (paper.wIn * 96));
    sheets.style.setProperty('--s', s.toFixed(4));
  }
  window.addEventListener('beforeprint', function () { setPage(current); });
  FD.print = { PAPER: PAPER, defaultPaper: defaultPaper, setPage: setPage, print: print, fit: fit, get current() { return current; } };
})(window.FD = window.FD || {});
