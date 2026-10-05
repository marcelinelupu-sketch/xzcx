/* frogsdream site.js: config-driven bits (ads, Mega Pack, tip, email), In season reordering,
   embed modal, toast, clipboard and footer year. Loaded with defer on every page. */
(function (FD) {
  'use strict';
  var cfg = FD.cfg = window.FD_CONFIG || {};
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  FD.$$ = $$;

  /* ---------- small helpers other scripts use ---------- */
  FD.esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; });
  };
  var toastEl, toastTimer;
  FD.toast = function (msg) {
    if (!toastEl) { toastEl = document.createElement('div'); toastEl.className = 'toast'; toastEl.setAttribute('role', 'status'); document.body.appendChild(toastEl); }
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('show'); }, 2600);
  };
  FD.copy = function (text) {
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      return ok ? Promise.resolve() : Promise.reject(new Error('copy'));
    }
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text).catch(fallback);
    return fallback();
  };
  /* FD.modal(title, bodyHtml) opens a native <dialog>; returns the dialog element. */
  FD.modal = function (title, bodyHtml) {
    var d = document.getElementById('fd-modal');
    if (!d) {
      d = document.createElement('dialog');
      d.id = 'fd-modal'; d.className = 'modal'; d.setAttribute('aria-labelledby', 'fd-modal-h');
      document.body.appendChild(d);
      d.addEventListener('click', function (e) { if (e.target === d || e.target.hasAttribute('data-close')) d.close(); });
    }
    d.innerHTML = '<h2 id="fd-modal-h">' + FD.esc(title) + '</h2>' + bodyHtml +
      '<div class="btns"><button type="button" class="btn btn-quiet" data-close>Close</button></div>';
    if (d.showModal) d.showModal(); else d.setAttribute('open', '');
    return d;
  };

  /* ---------- embed modal ---------- */
  function openEmbed(btn) {
    var src = btn.getAttribute('data-embed-src'), link = btn.getAttribute('data-embed-link'), name = btn.getAttribute('data-embed-name');
    var code = '<iframe src="' + src + '" width="100%" height="900" style="border:0;max-width:100%" title="' + name +
      ' by frogsdream" loading="lazy"></iframe>\n<p><a href="' + link + '">' + name + ' by frogsdream</a></p>';
    var d = FD.modal('Embed this tool', '<p>Paste this code into your blog, class page or website. The tool runs inside your page and stays free to use.</p>' +
      '<label class="vh" for="fd-embed-code">Embed code</label><textarea id="fd-embed-code" readonly>' + FD.esc(code) + '</textarea>' +
      '<div class="btns"><button type="button" class="btn btn-primary" id="fd-embed-copy">Copy code</button></div>');
    d.querySelector('#fd-embed-copy').addEventListener('click', function () {
      FD.copy(code).then(function () { FD.toast('Embed code copied'); }, function () { d.querySelector('textarea').select(); });
    });
  }

  /* ---------- In season now ---------- */
  function dayOfYear(m, d, y) { return Math.round((Date.UTC(y, m - 1, d) - Date.UTC(y, 0, 1)) / 864e5); }
  FD.seasonScore = function (mmdd, tail, now) {
    now = now || new Date();
    var y = now.getFullYear(), p = mmdd.split('-');
    var today = dayOfYear(now.getMonth() + 1, now.getDate(), y);
    var diff = dayOfYear(+p[0], +p[1], y) - today;
    if (diff < -tail) diff += 365;           /* already over this year: next year's date */
    if (diff <= 0) return tail <= 10 ? diff * 0.01 - 1 : 46 - diff * 0.001; /* today or just now: first; a running season: after the next 45 days of events */
    return diff <= 45 ? diff : 1000 + diff;
  };
  function reorderSeasons() {
    $$('.season-list').forEach(function (ul) {
      var items = $$('li.season', ul);
      items.sort(function (a, b) {
        return FD.seasonScore(a.getAttribute('data-date'), +a.getAttribute('data-tail') || 1) -
          FD.seasonScore(b.getAttribute('data-date'), +b.getAttribute('data-tail') || 1);
      });
      items.forEach(function (li, i) { li.classList.toggle('next', i === 0); ul.appendChild(li); });
      if (items.length > 6 && !ul.hasAttribute('data-more')) {
        ul.setAttribute('data-more', '');
        ul.classList.add('collapsed');
        var b = document.createElement('button');
        b.type = 'button'; b.className = 'btn btn-quiet btn-sm'; b.setAttribute('data-season-more', '');
        b.setAttribute('aria-expanded', 'false');
        b.textContent = 'Show all ' + items.length + ' seasons';
        b.addEventListener('click', function () {
          var open = ul.classList.toggle('collapsed');
          b.setAttribute('aria-expanded', String(!open));
          b.textContent = open ? 'Show all ' + items.length + ' seasons' : 'Show fewer';
        });
        ul.parentNode.insertBefore(b, ul.nextSibling);
      }
    });
  }

  /* ---------- AdSense (only when configured, never on no-ads pages) ---------- */
  function noAds() { return document.body.hasAttribute('data-no-ads'); }
  function openChoices() {
    var fc = window.googlefc = window.googlefc || {};
    fc.callbackQueue = fc.callbackQueue || [];
    fc.callbackQueue.push({ CONSENT_API_READY: function () { window.googlefc.showRevocationMessage(); } });
  }
  function loadAds() {
    var client = (cfg.ADSENSE_CLIENT || '').trim();
    if (!client || document.body.hasAttribute('data-no-ads')) return;
    if (!document.querySelector('script[data-fd-adsense]')) {
      var s = document.createElement('script');
      s.async = true; s.crossOrigin = 'anonymous'; s.setAttribute('data-fd-adsense', '');
      s.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + encodeURIComponent(client);
      document.head.appendChild(s);
      /* If Auto ads shows a bottom anchor ad, stop the Generate/Print bar from sticking to the bottom edge
         so the ad never sits on top of or right next to the buttons. */
      var n = 0, t = setInterval(function () {
        var a = document.querySelector('ins.adsbygoogle[data-anchor-status="displayed"],ins.adsbygoogle[data-anchor-shown="true"]');
        if (a) document.body.classList.add('fd-anchor');
        if (a || ++n > 60) clearInterval(t);
      }, 1000);
    }
    var slot = (cfg.AD_SLOT_IN_ARTICLE || '').trim();
    if (!slot) return;
    $$('.ad-slot').forEach(function (box) {
      if (box.closest('.tool,.no-ads')) return;
      box.classList.add('on');
      var ins = document.createElement('ins');
      ins.className = 'adsbygoogle';
      ins.style.display = 'block'; ins.style.textAlign = 'center';
      ins.setAttribute('data-ad-client', client); ins.setAttribute('data-ad-slot', slot);
      ins.setAttribute('data-ad-format', 'fluid'); ins.setAttribute('data-ad-layout', 'in-article');
      box.appendChild(ins);
      try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (e) { /* ignore */ }
    });
  }

  function init() {
    /* Older versions kept tool input in localStorage. Remove those leftovers; tools now use sessionStorage only. */
    try { for (var i = localStorage.length - 1; i >= 0; i--) { var k = localStorage.key(i); if (k && k.indexOf('fd:') === 0) localStorage.removeItem(k); } } catch (e) { /* storage blocked */ }
    $$('[data-year]').forEach(function (el) { el.textContent = new Date().getFullYear(); });
    var pack = (cfg.PACK_URL || '').trim();
    var price = cfg.PACK_PRICE || '$7';
    $$('[data-pack-price]').forEach(function (el) { el.textContent = price; });
    if (pack) $$('[data-pack]').forEach(function (el) { el.hidden = false; });
    $$('[data-pack-buy]').forEach(function (a) {
      if (pack) { a.href = pack; a.removeAttribute('aria-disabled'); a.textContent = a.getAttribute('data-label') || ('Get the Mega Pack for ' + price); }
      else { a.removeAttribute('href'); a.setAttribute('aria-disabled', 'true'); a.textContent = 'Coming soon'; }
    });
    if (cfg.TIP_URL) $$('[data-tip]').forEach(function (a) { a.href = cfg.TIP_URL; a.rel = 'noopener'; a.hidden = a.parentNode.hidden = false; });
    /* the contact address must always be visible (privacy law), so fall back to the default mailbox */
    var mail = String(cfg.CONTACT_EMAIL || '').trim() || ('hello' + '@' + 'frogsdream.com');
    $$('[data-email]').forEach(function (el) {
      var a = document.createElement('a'); a.href = 'mailto:' + mail; a.textContent = mail;
      el.textContent = ''; el.appendChild(a);
    });
    /* Privacy choices: Google's consent tool only exists on pages that load AdSense. On ad pages, queue the
       revocation message; on no-ads pages, send the visitor to the home page, which opens it there. */
    var adsOn = !!String(cfg.ADSENSE_CLIENT || '').trim();
    $$('[data-privacy-choices]').forEach(function (a) {
      if (adsOn && noAds()) a.href = '/#privacy-choices';
      a.addEventListener('click', function (e) {
        if (adsOn && !noAds()) { e.preventDefault(); openChoices(); }
      });
    });
    document.addEventListener('click', function (e) {
      var b = e.target.closest && e.target.closest('[data-embed-open]');
      if (b) { e.preventDefault(); openEmbed(b); }
    });
    reorderSeasons();
    loadAds();
    if (adsOn && !noAds() && location.hash === '#privacy-choices') openChoices();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})(window.FD = window.FD || {});
