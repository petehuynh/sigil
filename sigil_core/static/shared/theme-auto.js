/* ============================================================================
 * theme-auto.js — portfolio-wide light/dark for the marketing/landing surfaces.
 *
 * Two behaviours, matching the Bojio footer switch:
 *   1) AUTO (default, no manual choice): resolve by local time of day —
 *      daytime is light, night is dark — so the pages aren't blinding in the
 *      morning. Re-checks periodically so an open tab flips at dawn/dusk.
 *   2) MANUAL: a footer "☀ Light · ☾ Dark" switch. A click is an explicit
 *      override, persisted in localStorage, and wins over the clock forever
 *      after (until the user picks the other one).
 *
 * Light mode is the unqualified `.theme--light` token block each brand defines;
 * we toggle it on <html> so its custom properties cascade to the whole page —
 * AND on <body>, because the per-brand overrides are compound selectors on the
 * body element: `body[data-brand="lyd"].theme--light` (lit/tokens.css). With
 * the class on <html> only, that block never matches and `:root[data-brand]`
 * dark defaults win, so a reader in light mode on LYD saw every Bojio/Sonar/
 * Podcast page flip DARK (19.S04). bojio-app.js has always toggled both; this
 * file is the server-rendered pages' leg of the same theme and did not.
 *
 * The body half cannot happen at pre-paint: this script is blocking in <head>,
 * where `document.body` does not exist yet. It is applied the moment the body
 * element appears rather than at DOMContentLoaded, so the no-flash guarantee
 * below holds for the brand overrides too — waiting for DOMContentLoaded would
 * paint every non-bojio brand dark first and then correct it.
 *
 * Loaded as a BLOCKING <script> in <head> (no defer/async) so the resolved
 * theme is applied before first paint — no flash. The footer wiring/mount runs
 * later, on DOMContentLoaded.
 * ========================================================================== */
(function () {
  'use strict';

  var KEY = 'bojio.theme';          // 'light' | 'dark' | 'auto' | (absent)
  var DAY_START = 7;                // [07:00, 19:00) → light, else dark
  var DAY_END = 19;
  var html = document.documentElement;

  function read() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function write(v) {
    try { localStorage.setItem(KEY, v); } catch (e) { /* storage blocked */ }
  }
  function isOverride(v) { return v === 'light' || v === 'dark'; }

  function byClock() {
    var h = new Date().getHours();
    return (h >= DAY_START && h < DAY_END) ? 'light' : 'dark';
  }
  function resolve() {
    var s = read();
    return isOverride(s) ? s : byClock();
  }

  function buttons() {
    return document.querySelectorAll(
      '.theme-switch button[data-theme], .c-footer__theme button[data-theme]'
    );
  }
  //: Apply the theme class to <body>, or arrange for it the instant <body>
  //  exists. Returns nothing; safe to call before the body is parsed.
  var pendingBodyTheme = null;
  var bodyWatcher = null;

  function paintBody(theme) {
    if (document.body) {
      document.body.classList.toggle('theme--light', theme === 'light');
      // A later paint() beats a watcher armed earlier — disarm it so it
      // cannot fire again with a theme this call has already superseded.
      if (bodyWatcher) { bodyWatcher.disconnect(); bodyWatcher = null; }
      pendingBodyTheme = null;
      return;
    }
    // Still inside <head>. Remember the latest answer and watch for <body>.
    pendingBodyTheme = theme;
    if (bodyWatcher || typeof MutationObserver !== 'function') return;
    bodyWatcher = new MutationObserver(function () {
      if (!document.body) return;
      document.body.classList.toggle('theme--light', pendingBodyTheme === 'light');
      bodyWatcher.disconnect();
      bodyWatcher = null;
    });
    bodyWatcher.observe(html, { childList: true });
  }

  function paint(theme) {
    html.classList.toggle('theme--light', theme === 'light');
    // Mirror onto <body>: the per-brand light overrides are compound
    // selectors on the body element (see the header). 19.S04.
    paintBody(theme);
    var b = buttons();
    for (var i = 0; i < b.length; i++) {
      b[i].setAttribute(
        'data-active', b[i].getAttribute('data-theme') === theme ? 'true' : 'false'
      );
    }
  }

  // 1) Pre-paint — runs synchronously while still in <head>.
  paint(resolve());

  // 2) Periodic re-check so a tab left open flips at the dawn/dusk boundary,
  //    but only while still in auto mode (no manual override stored).
  setInterval(function () {
    if (!isOverride(read())) paint(byClock());
  }, 10 * 60 * 1000);

  // 3) Footer switch: mount one if the page has none, then wire clicks.
  function onReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  function mountIfNeeded() {
    // Bojio's own pages ship a native .c-footer__theme switch — reuse it.
    if (document.querySelector('.theme-switch, .c-footer__theme')) return;
    var foot = document.querySelector('footer');
    if (!foot) return;
    var sw = document.createElement('div');
    sw.className = 'theme-switch';
    sw.setAttribute('role', 'group');
    sw.setAttribute('aria-label', 'Theme');
    sw.innerHTML =
      '<button type="button" data-theme="light" data-active="false">☀ Light</button>'
      + '<span aria-hidden="true">·</span>'
      + '<button type="button" data-theme="dark" data-active="false">☾ Dark</button>';
    foot.appendChild(sw);
  }

  onReady(function () {
    mountIfNeeded();
    paint(resolve());
    var b = buttons();
    for (var i = 0; i < b.length; i++) {
      b[i].addEventListener('click', function () {
        var t = this.getAttribute('data-theme');
        if (!isOverride(t)) return;
        write(t);
        paint(t);
      });
    }
  });

  // Cross-tab sync: respect a choice (or its clearing) made in another tab.
  window.addEventListener('storage', function (e) {
    if (e.key === KEY) paint(resolve());
  });
})();
