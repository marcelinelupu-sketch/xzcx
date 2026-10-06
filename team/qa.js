// Browser QA for the built book: node team/qa.js
// For every chapter: no script errors, vocabulary underlined, every exercise item answered
// correctly through the real interface, chapter completes, no horizontal scroll on a phone.
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const SITE = path.join(__dirname, "site");

(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" }).catch(() => chromium.launch());
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await ctx.route(/^https?:/, (r) => r.abort());           // no network: fonts are irrelevant here
  const page = await ctx.newPage();
  const files = fs.readdirSync(SITE).filter((f) => /^chapter-\d+\.html$/.test(f)).sort();
  const problems = [];
  let withEx = 0, items = 0, vocab = 0;
  for (const f of files) {
    const errs = [];
    const onErr = (e) => errs.push(e.message);
    page.on("pageerror", onErr);
    await page.goto("file://" + path.join(SITE, f));
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    const res = await page.evaluate(async () => {
      const out = { vocab: document.querySelectorAll(".v").length, items: 0, fail: [] };
      const EX = window.EXERCISES;
      const overflow = document.documentElement.scrollWidth > window.innerWidth + 2;
      if (overflow) out.fail.push("horizontal scroll on phone width");
      if (!EX) return out;
      const sets = document.querySelectorAll(".ex-set");
      EX.sets.forEach((s, si) => {
        (s.items || []).forEach((it, ii) => {
          out.items++;
          const box = sets[si] && sets[si].querySelectorAll(".ex-item")[ii];
          if (!box) { out.fail.push(`missing item s${si}i${ii}`); return; }
          const t = it.type || s.type;
          try {
            if (t === "choice") box.querySelectorAll(".ex-btn")[it.answer].click();
            else if (t === "gap") { const i = box.querySelector("input"); i.value = [].concat(it.answer)[0]; box.querySelector(".ex-btn").click(); }
            else if (t === "error") box.querySelectorAll(".ex-seg")[it.answer].click();
            else if (t === "order") {
              const want = [].concat(it.answer)[0].split(" ");
              for (const w of want) {
                const b = [...box.querySelectorAll(".ex-opts .ex-btn")].find((x) => x.textContent === w);
                if (!b) throw new Error("word chip missing: " + w);
                b.click();
              }
            }
          } catch (e) { out.fail.push(`s${si}i${ii} ${t}: ${e.message}`); }
          if (!box.classList.contains("done")) out.fail.push(`s${si}i${ii} ${t}: correct answer not accepted`);
        });
      });
      const c = window.RhymeProgress.chapter(window.CHAPTER);
      if (!c.complete) out.fail.push(`not complete after all correct answers (score ${c.score})`);
      return out;
    });
    page.off("pageerror", onErr);
    vocab += res.vocab; items += res.items; if (res.items) withEx++;
    if (!res.vocab) res.fail.push("no underlined words");
    const fails = res.fail.concat(errs.map((e) => "script error: " + e));
    if (fails.length) problems.push({ chapter: f, problems: fails });
  }
  // the TOC
  await page.goto("file://" + path.join(SITE, "toc.html"));
  await page.evaluate(() => { const s = document.getElementById("ls"); s.value = "pl"; proceed(); });
  await page.waitForTimeout(800);
  const toc = await page.evaluate(() => ({ underlined: document.querySelectorAll(".ch-row .v").length,
    checkmarks: typeof completed !== "undefined" ? completed.size : -1, rows: document.querySelectorAll(".ch-row").length }));
  const report = { chapters: files.length, chapters_with_exercises: withEx, exercise_items: items, underlined_words: vocab, toc, problems };
  fs.writeFileSync(path.join(__dirname, "state", "qa-report.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ...report, problems: problems.length }, null, 2));
  if (problems.length) console.log(JSON.stringify(problems.slice(0, 15), null, 2));
  await browser.close();
})();
