/*
 * wait-replay.js  (Design ↔ Engine page)
 * Job: replay the REAL step timings of three recorded engine answers (prototype/answers.json,
 *      AI preset, 19 Nov 2026) at 4× speed, the same way the prototype's waiting card does,
 *      and draw where the time went (AI writing vs database).
 * The numbers below are copied from that recording's timing_ms. Nothing is estimated.
 * Without this script: the page shows the same numbers in the table under the demo.
 */
(function () {
  var root = document.getElementById('wait-demo');
  if (!root) return;

  var RUNS = {
    hybrid: { label: 'Elena: 40 navy mesh chairs, under $350, Chicago in 3 days', total: 8968.2,
      steps: [['Reading your request (small AI model)', 8965.0], ['Checking stock, prices and delivery in 5 warehouses', 3.2]] },
    sql: { label: 'How many navy AeroTask chairs are in Indianapolis?', total: 6739.9,
      steps: [['Turning your question into a database query (small AI model)', 6738.8], ['Looking it up', 1.1]] },
    search: { label: 'Show me the navy shell', total: 10846.8,
      steps: [['Working out what kind of question this is (AI tie-breaker)', 7881.8], ['Searching the catalog by meaning and by keyword', 2965.0]] }
  };
  var SPEED = 4;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var picker = root.querySelector('.seg');
  var card = root.querySelector('.wait');
  var bar = root.querySelector('.bar-track');
  var timer = null, current = 'hybrid';

  function fmt(ms) {
    var s = Math.floor(ms / 1000);
    return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  }
  function fmtMs(ms) { return ms >= 1000 ? (ms / 1000).toFixed(1) + ' s' : ms.toFixed(1) + ' ms'; }

  function draw(run, real) {
    var acc = 0, idx = run.steps.length;
    for (var i = 0; i < run.steps.length; i++) { acc += run.steps[i][1]; if (real < acc) { idx = i; break; } }
    var done = real >= run.total;
    card.innerHTML =
      '<div class="row"><b>' + (done ? 'Answer ready' : 'Working on it') + '</b><span class="t" aria-hidden="true">' + fmt(Math.min(real, run.total)) + '</span></div>' +
      '<ol class="steps">' + run.steps.map(function (s, j) {
        var c = (done || j < idx) ? 'done' : (j === idx ? 'now' : '');
        return '<li><span class="m ' + c + '" aria-hidden="true"></span><span>' + s[0] + '</span><span class="ms">' + fmtMs(s[1]) + '</span></li>';
      }).join('') + '</ol>' +
      '<span style="font-size:13px;color:var(--muted)">Replayed at ' + SPEED + '× speed. The real engine took <b>' + (run.total / 1000).toFixed(1) + ' s</b> on a home PC.</span>';
  }
  function drawBar(run) {
    var ai = run.steps[0][1], db = run.total - ai;
    bar.innerHTML = '<span class="bar-ai" style="width:' + (ai / run.total * 100) + '%"></span><span class="bar-db" style="width:' + Math.max(db / run.total * 100, 0.6) + '%"></span>';
    bar.setAttribute('aria-label', 'AI ' + fmtMs(ai) + ', database and search ' + fmtMs(db));
  }
  function play(key) {
    current = key;
    var run = RUNS[key];
    picker.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.run === key)); });
    drawBar(run);
    clearInterval(timer);
    if (reduce) { draw(run, run.total); return; }
    var start = Date.now();
    draw(run, 0);
    timer = setInterval(function () {
      var real = (Date.now() - start) * SPEED;
      draw(run, real);
      if (real >= run.total) clearInterval(timer);
    }, 120);
  }

  picker.innerHTML = Object.keys(RUNS).map(function (k) {
    return '<button type="button" data-run="' + k + '" aria-pressed="false">' + RUNS[k].label + '</button>';
  }).join('');
  picker.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-run]');
    if (b) play(b.dataset.run);
  });
  root.querySelector('[data-replay]').addEventListener('click', function () { play(current); });
  root.hidden = false;
  play('hybrid');
})();
