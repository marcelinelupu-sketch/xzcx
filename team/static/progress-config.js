/* Server connection for learner progress. Leave empty to keep progress in the browser only.
 * To connect your platform, set the endpoint (see HANDOFF.md), for example:
 *   window.RHYME_PROGRESS_ENDPOINT = "/api/grammar-progress";
 * or define window.RhymeProgressAdapter = { load, save } in this file. */
window.RHYME_PROGRESS_ENDPOINT = window.RHYME_PROGRESS_ENDPOINT || "";
