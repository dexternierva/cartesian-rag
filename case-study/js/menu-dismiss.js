/*
 * menu-dismiss.js
 * Job: close the phone menu when the visitor presses Esc or taps outside the header,
 *      by unchecking #menu-toggle.
 * Does not: open the menu or show/hide anything. styles.css reads #menu-toggle:checked.
 */
(function () {
  var toggle = document.getElementById('menu-toggle');
  if (!toggle) return;
  var header = toggle.closest('header');

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && toggle.checked) {
      toggle.checked = false;
      toggle.focus();
    }
  });

  document.addEventListener('click', function (event) {
    if (toggle.checked && header && !header.contains(event.target)) toggle.checked = false;
  });
})();
