/* RhymeProgress: the one place where the grammar book records what a learner has done.
 *
 * Every page (TOC and chapters) loads this file. It keeps the state in localStorage so the
 * book works on its own, and it exposes ONE plug for a server:
 *
 *   1. Set an endpoint in the page (or globally before this script loads):
 *        window.RHYME_PROGRESS_ENDPOINT = "/api/grammar-progress";
 *      GET  <endpoint>            -> returns the saved state JSON for the logged in user
 *      POST <endpoint>  {event, state} -> saves; sent after every change
 *      Requests use credentials: "include", so the user's session cookie identifies them.
 *
 *   2. Or install a custom adapter (takes priority over the endpoint):
 *        window.RhymeProgressAdapter = {
 *          load: async () => state | null,
 *          save: async (state, event) => {}
 *        };
 *
 * Events are also broadcast in the page as  window "rhyme-progress"  CustomEvents, so a
 * dashboard script can listen without touching this file. See HANDOFF.md for the schema.
 */
(function () {
  "use strict";
  var KEY = "rhymeGrammarProgress";
  var VERSION = 1;
  var PASS = 0.8; // share of exercise items that must be right on the first attempt

  function empty() { return { version: VERSION, updatedAt: null, chapters: {} }; }

  function read() {
    try {
      var s = JSON.parse(localStorage.getItem(KEY) || "null");
      if (s && s.version === VERSION && s.chapters) return s;
    } catch (e) {}
    return empty();
  }

  var state = read();

  function write() {
    state.updatedAt = new Date().toISOString();
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }

  function chapter(n) {
    var k = String(n);
    if (!state.chapters[k]) state.chapters[k] = { viewedAt: null, items: {}, total: 0, complete: false, completedAt: null, score: null };
    return state.chapters[k];
  }

  function remote(event) {
    var adapter = window.RhymeProgressAdapter;
    var url = window.RHYME_PROGRESS_ENDPOINT;
    try {
      if (adapter && adapter.save) return Promise.resolve(adapter.save(state, event)).catch(function () {});
      if (url) return fetch(url, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event: event, state: state }) }).catch(function () {});
    } catch (e) {}
    return Promise.resolve();
  }

  function emit(type, data) {
    var event = Object.assign({ type: type, at: new Date().toISOString() }, data);
    write();
    try { window.dispatchEvent(new CustomEvent("rhyme-progress", { detail: { event: event, state: state } })); } catch (e) {}
    remote(event);
    return event;
  }

  /* Merge a server state into the local one: a chapter that is complete anywhere stays complete,
     the earliest view and first attempts win, so nothing a learner did is ever lost. */
  function merge(server) {
    if (!server || !server.chapters) return;
    Object.keys(server.chapters).forEach(function (k) {
      var a = chapter(k), b = server.chapters[k];
      if (b.viewedAt && (!a.viewedAt || b.viewedAt < a.viewedAt)) a.viewedAt = b.viewedAt;
      Object.keys(b.items || {}).forEach(function (id) { if (!a.items[id]) a.items[id] = b.items[id]; });
      a.total = Math.max(a.total || 0, b.total || 0);
      if (b.complete && !a.complete) { a.complete = true; a.completedAt = b.completedAt; a.score = b.score; }
    });
    write();
  }

  function evaluate(n) {
    var c = chapter(n);
    var ids = Object.keys(c.items);
    if (!c.total || ids.length < c.total) return c;
    var right = ids.filter(function (id) { return c.items[id].firstCorrect; }).length;
    c.score = Math.round((right / c.total) * 100) / 100;
    if (!c.complete && c.score >= PASS) {
      c.complete = true;
      c.completedAt = new Date().toISOString();
      emit("chapter_completed", { chapter: Number(n), score: c.score });
    }
    return c;
  }

  var api = {
    PASS: PASS,
    state: function () { return state; },
    chapter: function (n) { return chapter(n); },

    /* call once when a chapter page opens; total = number of exercise items on it (0 if none) */
    viewed: function (n, total) {
      var c = chapter(n);
      c.total = total || 0;
      var first = !c.viewedAt;
      if (first) c.viewedAt = new Date().toISOString();
      emit("lesson_viewed", { chapter: Number(n), first: first });
      if (!c.total && !c.complete) { // chapters without exercises are complete once read
        c.complete = true; c.completedAt = c.viewedAt; c.score = null;
        emit("chapter_completed", { chapter: Number(n), score: null });
      }
      return c;
    },

    /* call on every answer; only the first attempt counts for the score */
    answered: function (n, itemId, correct) {
      var c = chapter(n);
      var it = c.items[itemId];
      if (!it) { it = c.items[itemId] = { firstCorrect: !!correct, attempts: 0, solved: false }; }
      it.attempts += 1;
      if (correct) it.solved = true;
      emit("exercise_answered", { chapter: Number(n), item: itemId, correct: !!correct, firstAttempt: it.attempts === 1 });
      return evaluate(n);
    },

    /* forget one chapter's exercise answers so the learner can practise again (completion stays) */
    resetExercises: function (n) {
      var c = chapter(n); c.items = {}; c.score = c.complete ? c.score : null;
      emit("exercises_reset", { chapter: Number(n) });
    },

    completedChapters: function () {
      return Object.keys(state.chapters).filter(function (k) { return state.chapters[k].complete; }).map(Number);
    },
    viewedChapters: function () {
      return Object.keys(state.chapters).filter(function (k) { return state.chapters[k].viewedAt; }).map(Number);
    },

    /* pulls the server copy (if any) and merges it; resolves when done */
    sync: function () {
      var adapter = window.RhymeProgressAdapter, url = window.RHYME_PROGRESS_ENDPOINT, p;
      if (adapter && adapter.load) p = Promise.resolve(adapter.load());
      else if (url) p = fetch(url, { credentials: "include" }).then(function (r) { return r.ok ? r.json() : null; });
      else return Promise.resolve(state);
      return p.then(function (s) { merge(s); window.dispatchEvent(new CustomEvent("rhyme-progress", { detail: { event: { type: "synced" }, state: state } })); return state; })
              .catch(function () { return state; });
    }
  };

  window.RhymeProgress = api;
})();
