/*
 * theme.js
 * Job: switch between the design system's two themes, Daylight and Campfire night,
 *      and remember the choice in this browser. With no choice saved, the page follows
 *      the device setting (styles.css reads prefers-color-scheme).
 * Without this script: the page still follows the device setting; only the switch is missing.
 */
(function () {
  var root = document.documentElement;
  var buttons = document.querySelectorAll('[data-theme-toggle]');
  if (!buttons.length) return;

  function current() {
    var set = root.getAttribute('data-theme');
    if (set) return set;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function paint() {
    var dark = current() === 'dark';
    buttons.forEach(function (b) {
      b.textContent = dark ? 'Daylight' : 'Night';
      b.setAttribute('aria-label', dark ? 'Switch to the Daylight theme' : 'Switch to the Campfire night theme');
    });
  }
  buttons.forEach(function (b) {
    b.hidden = false;
    b.addEventListener('click', function () {
      var next = current() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('crcs-theme', next); } catch (e) { /* private mode: just don't remember */ }
      paint();
    });
  });
  paint();
})();
