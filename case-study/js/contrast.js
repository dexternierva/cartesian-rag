/*
 * contrast.js  (Design System page)
 * Job: work out the WCAG 2 contrast ratio for every swatch that names a text colour
 *      (data-fg) and a ground (data-bg), and print it with a pass or fail against the
 *      minimum its role needs (data-min: 4.5 for text, 3 for borders and large text).
 * The ratios are calculated in the browser from the hex values, not typed in.
 * Without this script: the swatches still show their colours, names and hex values.
 */
(function () {
  function lum(hex) {
    var h = hex.replace('#', '');
    var rgb = [0, 2, 4].map(function (i) { return parseInt(h.substr(i, 2), 16) / 255; });
    var lin = rgb.map(function (c) { return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); });
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
  }
  function ratio(a, b) {
    var x = lum(a), y = lum(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  }
  var passed = 0, total = 0;
  document.querySelectorAll('[data-fg][data-bg]').forEach(function (el) {
    var r = ratio(el.dataset.fg, el.dataset.bg), min = parseFloat(el.dataset.min || '4.5');
    var out = el.querySelector('.cr');
    if (!out) return;
    total++;
    var ok = r >= min;
    if (ok) passed++;
    out.textContent = r.toFixed(2) + ':1 · ' + (ok ? 'passes' : 'fails') + ' ' + min + ':1';
    out.className = 'cr ' + (ok ? 'pass' : 'fail');
  });
  var sum = document.getElementById('contrast-sum');
  if (sum && total) sum.textContent = passed + ' of ' + total + ' pairs on this page pass, worked out in your browser just now.';
})();
