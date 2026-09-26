// ==UserScript==
// @name         CDN probe example
// @namespace    https://example.com/userscripts
// @version      1.0.0
// @description  Opt-in, bounded image-node probe; disabled by default.
// @match        https://example.com/*
// @grant        none
// @run-at       document-idle
// @noframes
// ==/UserScript==

(function () {
  'use strict';

  const ENABLE_PROBE = false;
  const CANDIDATES = ['https://img-a.example.com/pixel.gif', 'https://img-b.example.com/pixel.gif'];
  if (!ENABLE_PROBE || !CANDIDATES.length) return;

  const probe = (url) => new Promise((resolve) => {
    const image = new Image();
    const started = performance.now();
    let settled = false;
    const finish = (ok) => {
      if (settled) return;
      settled = true;
      resolve({ url, ok, ms: Math.round(performance.now() - started) });
    };
    image.onload = () => finish(true);
    image.onerror = () => finish(false);
    setTimeout(() => finish(false), 1500);
    image.src = `${url}?probe=${Date.now()}`;
  });

  Promise.all(CANDIDATES.map(probe)).then((results) => {
    console.debug('[example-userscript][cdn-probe]', results);
  });
})();
