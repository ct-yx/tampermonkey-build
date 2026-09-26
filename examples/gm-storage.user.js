// ==UserScript==
// @name         GM storage example
// @namespace    https://example.com/userscripts
// @version      1.0.0
// @description  Namespaced Promise-based settings with a menu command.
// @match        https://example.com/*
// @grant        GM.getValue
// @grant        GM.setValue
// @grant        GM.registerMenuCommand
// @noframes
// ==/UserScript==

(async function () {
  'use strict';

  const KEY = 'example.enabled';
  const enabled = await GM.getValue(KEY, true);
  GM.registerMenuCommand(`Example: ${enabled ? 'disable' : 'enable'}`, async () => {
    await GM.setValue(KEY, !enabled);
    location.reload();
  });
  if (!enabled) return;
  document.documentElement.dataset.exampleEnabled = '1';
})();
