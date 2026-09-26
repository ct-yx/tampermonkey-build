// ==UserScript==
// @name         Cross-origin request example
// @namespace    https://example.com/userscripts
// @version      1.0.0
// @description  A bounded GM request with explicit host permission.
// @match        https://example.com/*
// @grant        GM.xmlHttpRequest
// @connect      api.example.com
// @noframes
// ==/UserScript==

(async function () {
  'use strict';

  const response = await GM.xmlHttpRequest({
    method: 'GET',
    url: 'https://api.example.com/status',
    responseType: 'json',
    timeout: 8000,
  });
  if (response.status < 200 || response.status >= 300) {
    throw new Error(`status=${response.status}`);
  }
  console.debug('[example-userscript] status', response.response);
})();
