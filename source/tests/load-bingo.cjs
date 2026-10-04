/* Loads rng.js and bingo.js into a sandbox (no browser needed) and returns FD. Used by the bingo tests. */
const fs = require('fs'), path = require('path'), vm = require('vm');
module.exports = function load() {
  const js = path.join(__dirname, '..', 'static', 'assets', 'js');
  const win = {};
  win.window = win;
  const ctx = vm.createContext(win);
  for (const f of ['rng.js', 'bingo.js']) vm.runInContext(fs.readFileSync(path.join(js, f), 'utf8'), ctx, { filename: f });
  return win.FD;
};
