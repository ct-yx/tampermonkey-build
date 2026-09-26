// ==UserScript==
// @name         Minimal userscript example
// @namespace    https://example.com/userscripts
// @version      1.0.0
// @description  A deliberately small DOM enhancement.
// @match        https://example.com/*
// @grant        none
// @run-at       document-end
// @noframes
// ==/UserScript==

(function () {
  'use strict';

  const marker = 'example-userscript-installed';
  if (document.documentElement.dataset[marker]) return;
  document.documentElement.dataset[marker] = '1';
  document.documentElement.dataset.exampleUserscriptAt = new Date().toISOString();
})();
