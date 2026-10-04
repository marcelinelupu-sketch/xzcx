/* guide-patterns.js: interactive bingo pattern gallery and custom pattern board for /guides/bingo-patterns/. Owner: guides. */
(function () {
  "use strict";
  var gal = document.getElementById("bp-gallery");
  if (!gal) return;
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };
  var pathFor = function (cells) {
    return cells.map(function (i) {
      return "M" + (i % 5 * 10 + 1) + " " + (Math.floor(i / 5) * 10 + 1) + "h8v8h-8z";
    }).join("");
  };

  // Step through the other winning positions of a pattern.
  each(gal.querySelectorAll(".bp"), function (li) {
    var ways = (li.getAttribute("data-v") || "").split("|");
    var btn = li.querySelector("button");
    var p = li.querySelector("path");
    if (ways.length < 2 || !btn || !p) return;
    var n = 0;
    var label = function () { btn.textContent = "Show another (" + (n + 1) + "/" + ways.length + ")"; };
    btn.hidden = false;
    label();
    btn.addEventListener("click", function () {
      n = (n + 1) % ways.length;
      p.setAttribute("d", pathFor(ways[n].split(",").map(Number)));
      label();
    });
  });

  // Category filter.
  var bar = document.getElementById("bp-filter");
  if (bar) {
    bar.hidden = false;
    bar.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-f]");
      if (!b) return;
      var f = b.getAttribute("data-f");
      each(bar.querySelectorAll("button"), function (x) { x.setAttribute("aria-pressed", String(x === b)); });
      each(gal.children, function (li) { li.hidden = f !== "all" && li.getAttribute("data-cat") !== f; });
    });
  }

  // Custom pattern board.
  var make = document.getElementById("bp-make");
  var pad = document.getElementById("bp-pad");
  if (!make || !pad) return;
  var out = document.getElementById("bp-n");
  var cols = "BINGO";
  var count = function () {
    out.textContent = pad.querySelectorAll('[aria-pressed="true"]').length;
  };
  for (var i = 0; i < 25; i++) {
    var b = document.createElement("button");
    b.type = "button";
    b.setAttribute("aria-pressed", "false");
    b.setAttribute("aria-label", cols[i % 5] + " column, row " + (Math.floor(i / 5) + 1) + (i === 12 ? ", free space" : ""));
    if (i === 12) b.className = "free";
    pad.appendChild(b);
  }
  pad.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (!b) return;
    b.setAttribute("aria-pressed", String(b.getAttribute("aria-pressed") !== "true"));
    count();
  });
  document.getElementById("bp-clear").addEventListener("click", function () {
    each(pad.children, function (b) { b.setAttribute("aria-pressed", "false"); });
    count();
  });
  var full = document.getElementById("bp-full");
  if (!pad.requestFullscreen) full.hidden = true;
  full.addEventListener("click", function () {
    try { pad.requestFullscreen(); } catch (e) { /* not supported */ }
  });
  make.hidden = false;
})();
