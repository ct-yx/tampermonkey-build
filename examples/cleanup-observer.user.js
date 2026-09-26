// ==UserScript==
// @name         Cleanup observer example
// @namespace    https://example.com/userscripts
// @version      1.0.0
// @description  Bounded child-list observation with idempotent rendering.
// @match        https://example.com/*
// @grant        none
// @run-at       document-end
// @noframes
// ==/UserScript==

(function () {
  'use strict';

  const root = document.querySelector('[data-example-list]');
  if (!root || root.dataset.exampleObserverInstalled) return;
  root.dataset.exampleObserverInstalled = '1';
  let frame = 0;

  const render = () => {
    frame = 0;
    for (const item of root.querySelectorAll('[data-example-item]')) {
      item.dataset.exampleSeen = '1';
    }
  };
  const observer = new MutationObserver(() => {
    if (frame) return;
    frame = requestAnimationFrame(render);
  });
  observer.observe(root, { childList: true });
  render();

  addEventListener('pagehide', () => {
    observer.disconnect();
    if (frame) cancelAnimationFrame(frame);
  }, { once: true });
})();
