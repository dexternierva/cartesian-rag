/*
 * lightbox.js
 * Job: open a screenshot full size when its figure is clicked or activated with Enter/Space,
 *      and close it with Esc, the Close button or a click on the dark backdrop.
 * Without this script: figures stay their normal size; nothing is lost.
 */
(function () {
  var frames = document.querySelectorAll('figure .frame img');
  if (!frames.length) return;

  var box = document.createElement('div');
  box.className = 'lb';
  box.hidden = true;
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.setAttribute('aria-label', 'Enlarged screenshot');
  box.innerHTML = '<img alt=""><button type="button">Close</button>';
  document.body.appendChild(box);
  var big = box.querySelector('img');
  var close = box.querySelector('button');
  var opener = null;

  function open(img) {
    opener = img.parentNode;
    big.src = img.currentSrc || img.src;
    big.alt = img.alt;
    box.hidden = false;
    close.focus();
  }
  function shut() {
    box.hidden = true;
    big.removeAttribute('src');
    if (opener) opener.focus();
  }

  frames.forEach(function (img) {
    var frame = img.parentNode;
    frame.classList.add('zoom');
    frame.setAttribute('tabindex', '0');
    frame.setAttribute('role', 'button');
    frame.setAttribute('aria-label', 'Enlarge: ' + img.alt);
    frame.addEventListener('click', function () { open(img); });
    frame.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(img); }
    });
  });
  close.addEventListener('click', shut);
  box.addEventListener('click', function (e) { if (e.target === box) shut(); });
  document.addEventListener('keydown', function (e) {
    if (box.hidden) return;
    if (e.key === 'Escape') shut();
    if (e.key === 'Tab') { e.preventDefault(); close.focus(); }   // the Close button is the only control inside
  });
})();
