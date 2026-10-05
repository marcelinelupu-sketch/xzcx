#!/usr/bin/env bash
# frogsdream full QA run (SPEC section 13). From the repo root:
#   bash source/qa/run_all.sh            build public_html, run every check, zip for upload if all pass
#   QUICK=1 bash source/qa/run_all.sh    skip the slow bingo uniqueness test and the all-themes browser pass
#   OUT=/tmp/site bash source/qa/run_all.sh   build and test somewhere else (no zip)
# Needs python3 (Pillow), node 22, Playwright with Chromium, poppler-utils (pdftotext, pdfinfo).
# Lighthouse is installed into source/qa/node_modules on first run (skipped if npm is offline).
# Reports go to source/qa/reports/. Exit code 1 if any step fails.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QA="$ROOT/source/qa"
OUT="${OUT:-$ROOT/public_html}"
REP="$QA/reports"
mkdir -p "$REP"
cd "$ROOT" || exit 2
declare -a NAMES STATUS
FAILED=0

step() {  # step "name" command...
  local name="$1"; shift
  local log="$REP/$(echo "$name" | tr -c 'a-zA-Z0-9' '_' | tr -s '_').log"
  printf '\n=== %s\n' "$name"
  "$@" >"$log" 2>&1
  local rc=$?
  tail -n 4 "$log"
  NAMES+=("$name")
  if [ $rc -eq 0 ]; then STATUS+=("PASS"); elif [ $rc -eq 3 ]; then STATUS+=("SKIP"); else STATUS+=("FAIL"); FAILED=1; grep -E '^(FAIL|error|ERROR)' "$log" | head -n 15; fi
}

# jsPDF 2.5.1 is self-hosted in source/static/assets/js/vendor/, so the browser tests need no network
# and fail on any request to another host.

step "Content validator (all files)" python3 source/validate_content.py --all
step "Build (strict) into $OUT" python3 source/build.py --out "$OUT" --strict --force
step "Static site QA" python3 "$QA/qa_static.py" "$OUT" --json "$REP/static.json"
step "Unit: 90-ball strip validity" node source/tests/test_bingo_90ball.cjs
if [ -z "${QUICK:-}" ]; then step "Unit: bingo card uniqueness" node source/tests/test_bingo_unique.cjs; fi
step "Unit: word search placement (200 seeds per list)" node source/tests/test_wordsearch.mjs
step "Browser: bingo generator and caller" node source/tests/browser_bingo.cjs "$OUT"
if [ -z "${QUICK:-}" ]; then
  step "Browser: tools, embeds, themed pages (360/1280, all themes)" node "$QA/qa_browser.cjs" "$OUT" --all-themes --json "$REP/browser.json"
else
  step "Browser: tools, embeds, 15 themed pages (360/1280)" node "$QA/qa_browser.cjs" "$OUT" --json "$REP/browser.json"
fi
step "Browser: empty and dummy config behavior" node "$QA/qa_config.cjs" "$OUT" --json "$REP/config.json"

LH_DIR="${LH_DIR:-$QA}"
if [ ! -d "$LH_DIR/node_modules/lighthouse" ]; then
  (cd "$QA" && npm install --no-audit --no-fund --silent lighthouse@13 >/dev/null 2>&1) || true
fi
step "Lighthouse mobile (95+ in all four categories)" env LH_DIR="$LH_DIR" node "$QA/qa_lighthouse.mjs" "$OUT" --json "$REP/lighthouse.json"

printf '\n=========== QA SUMMARY ===========\n'
for i in "${!NAMES[@]}"; do printf '%-4s  %s\n' "${STATUS[$i]}" "${NAMES[$i]}"; done
printf 'Logs and JSON reports: %s\n' "$REP"
# Owner reminders that do not fail the run (for example the operator name still missing in site.json)
cat "$REP"/*.log 2>/dev/null | grep -h '^WARNING' | sort -u

if [ $FAILED -eq 0 ] && [ "$OUT" = "$ROOT/public_html" ]; then
  mkdir -p "$ROOT/deliverables"
  ZIP="$ROOT/deliverables/frogsdream-public_html.zip"
  rm -f "$ZIP"
  (cd "$OUT" && python3 -c "
import os, sys, zipfile
with zipfile.ZipFile(sys.argv[1], 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for d, _, fs in os.walk('.'):
        for f in sorted(fs):
            p = os.path.join(d, f)[2:]
            z.write(p, p)
" "$ZIP") && printf 'Upload zip (folder contents at the zip root): %s\n' "$ZIP"
fi
exit $FAILED
