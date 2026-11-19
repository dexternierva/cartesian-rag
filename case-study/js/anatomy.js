/*
 * anatomy.js  (home page, "Anatomy of an answer")
 * Job: show one REAL engine ticket two ways, side by side: the data (left) and the screen
 *      the prototype draws from it (right). Pointing at a field on either side highlights
 *      its partner on the other side.
 * Data: four tickets recorded from the engine on 19 Nov 2026 (prototype/answers.json),
 *       trimmed by build.py and embedded in the page as #tickets. Nothing is hand-written.
 * Without this script: the static figure of the same answer stays visible instead.
 */
(function () {
  var root = document.getElementById('anatomy');
  var src = document.getElementById('tickets');
  if (!root || !src) return;
  var tickets = JSON.parse(src.textContent);

  var picker = root.querySelector('.seg');
  var json = root.querySelector('.json');
  var screen = root.querySelector('.screen');

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
  }
  function money(n) { return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  // Fields that have a partner on the screen. Everything else is shown plain.
  var LINKED = { message: 1, constraints: 1, relax: 1, subject: 1, table: 1, components: 1, citations: 1 };
  var REQ = {
    quantity: function (v) { return v + ' units'; }, category: String, color: String,
    material: function (v) { return v.charAt(0).toUpperCase() + v.slice(1); },
    armrests: function (v) { return v + ' armrests'; }, max_unit_price: function (v) { return 'Under ' + money(v).replace('.00', '') + ' each'; },
    destination_city: function (v) { return 'To ' + v; }, max_delivery_days: function (v) { return 'Within ' + v + ' days'; }
  };

  function drawJson(t) {
    var out = '{\n';
    Object.keys(t.ticket).forEach(function (k, i, all) {
      var body = JSON.stringify(t.ticket[k], null, 2).replace(/\n/g, '\n  ');
      var line = '  <b>"' + k + '"</b>: ' + esc(body) + (i < all.length - 1 ? ',' : '');
      out += LINKED[k]
        ? '<span class="jk" data-k="' + k + '" tabindex="0">' + line + '</span>'
        : '<span class="jk plain">' + line + '</span>';
    });
    json.innerHTML = out + '\n}';
  }

  function part(k, html) { return '<div class="ui" data-k="' + k + '" tabindex="0">' + html + '</div>'; }

  function drawScreen(t) {
    var tk = t.ticket, h = '<div class="u">' + esc(t.question) + '</div>';
    var c = tk.constraints || {};
    var chips = Object.keys(REQ).filter(function (k) { return c[k] != null; })
      .map(function (k) { return '<span class="req">' + esc(REQ[k](c[k])) + ' ×</span>'; }).join('');
    if (chips) h += part('constraints', '<div class="chips"><span class="mono" style="text-transform:none;letter-spacing:0">Looking for</span>' + chips + '</div>');

    if (tk.state === 'handoff') {
      h += part('components', '<div class="notice ho"><b>Connecting you to a specialist</b><span>They’ll see this conversation, so you won’t need to repeat anything.</span></div>');
    } else if (tk.state === 'no_results') {
      var ways = (tk.relax || []).map(function (o, i) {
        return '<span class="ds-btn' + (i === 0 ? ' s' : '') + '" style="align-self:flex-start">Show ' + o.matches + ' option' + (o.matches > 1 ? 's' : '') + ' without ' + esc(o.label) + '</span>';
      }).join('');
      h += part('message', '<b>Nothing matches everything you asked for right now.</b>');
      if (ways) h += part('relax', '<div class="notice" style="gap:6px">' + ways + '</div>');
    } else if (tk.subject) {
      var s = tk.subject, n = tk.table.rows[0][0];
      h += part('table', '<span class="fact-n">' + esc(n) + '</span>');
      h += part('subject', '<span>' + esc((s.color || '').toLowerCase() + ' ' + (s.product || '')) + ' available at <b>' + esc(s.depot || '') + '</b>.</span>');
      h += part('citations', '<span class="receipt"><span class="ck" aria-hidden="true">✓</span>Verified · see source <span class="mono">inventory · ' + esc(s.sku || '') + '</span></span>');
    } else {
      h += part('message', '<span>' + esc(tk.message) + '</span>');
      if (tk.relax && tk.relax.length) h += part('relax', '<span class="ds-btn s" style="align-self:flex-start">Also show options that ship from several warehouses</span>');
      var cards = (tk.components || []).filter(function (x) { return x.type === 'product_card'; }).map(function (x) {
        return '<div class="mcard"><div class="top"><span>' + esc(x.name) + ' — ' + esc(x.color) + '</span><span>' + money(x.unit_price) + '</span></div>' +
          '<span class="stock ok"><i></i><b>In stock</b><span class="w">· ' + x.stock.available + ' at ' + esc(x.stock.depot_name) + '</span></span>' +
          '<span class="receipt" data-k="citations"><span class="ck" aria-hidden="true">✓</span>Verified · see source <span class="mono">inventory · ' + esc(x.sku) + '</span></span></div>';
      }).join('');
      if (cards) h += part('components', cards);
    }
    screen.innerHTML = h;
  }

  function clear() { root.querySelectorAll('.hl').forEach(function (el) { el.classList.remove('hl'); }); }
  function light(k) {
    clear();
    if (!k) return;
    root.querySelectorAll('[data-k="' + k + '"]').forEach(function (el) { el.classList.add('hl'); });
  }
  ['mouseover', 'focusin'].forEach(function (ev) {
    root.addEventListener(ev, function (e) {
      var el = e.target.closest('[data-k]');
      light(el && root.contains(el) ? el.dataset.k : null);
    });
  });
  root.addEventListener('mouseleave', clear);

  function show(i) {
    picker.querySelectorAll('button').forEach(function (b, j) { b.setAttribute('aria-pressed', String(j === i)); });
    drawJson(tickets[i]);
    drawScreen(tickets[i]);
  }
  picker.innerHTML = tickets.map(function (t, i) { return '<button type="button" aria-pressed="false" data-i="' + i + '">' + esc(t.label) + '</button>'; }).join('');
  picker.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-i]');
    if (b) show(Number(b.dataset.i));
  });

  var fallback = document.getElementById('anatomy-fallback');
  if (fallback) fallback.hidden = true;
  root.hidden = false;
  show(0);
})();
