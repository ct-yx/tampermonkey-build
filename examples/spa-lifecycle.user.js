// ==UserScript==
// @name         SPA lifecycle example
// @namespace    https://example.com/userscripts
// @version      1.0.0
// @description  Idempotent route-aware initialization with cleanup.
// @match        https://example.com/*
// @grant        none
// @run-at       document-start
// @noframes
// ==/UserScript==

(function () {
  'use strict';

  const stateKey = Symbol.for('example.userscript.spa');
  const state = window[stateKey] || (window[stateKey] = {
    installed: false,
    route: '',
    dispose: null,
  });
  if (state.installed) return;
  state.installed = true;

  function currentRoute() {
    return `${location.pathname}${location.search}${location.hash}`;
  }

  let pageDispose = null;
  function mount(route) {
    pageDispose?.();
    const badge = document.createElement('div');
    badge.dataset.exampleSpaBadge = '1';
    badge.textContent = `Userscript route: ${route}`;
    badge.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:2147483647;padding:4px 8px;background:#2563eb;color:white;font:12px system-ui;border-radius:6px';
    (document.body || document.documentElement).append(badge);
    pageDispose = () => badge.remove();
    state.route = route;
  }

  function ensure() {
    if (!document.body) return;
    const route = currentRoute();
    if (route !== state.route) mount(route);
  }

  const nativePushState = history.pushState;
  history.pushState = function (...args) {
    const result = nativePushState.apply(this, args);
    queueMicrotask(ensure);
    return result;
  };
  const onRoute = () => queueMicrotask(ensure);
  const onReady = () => ensure();
  addEventListener('popstate', onRoute);
  addEventListener('hashchange', onRoute);
  addEventListener('DOMContentLoaded', onReady, { once: true });

  state.dispose = () => {
    pageDispose?.();
    pageDispose = null;
    history.pushState = nativePushState;
    removeEventListener('popstate', onRoute);
    removeEventListener('hashchange', onRoute);
    removeEventListener('DOMContentLoaded', onReady);
    state.route = '';
    state.installed = false;
    state.dispose = null;
  };
  addEventListener('pagehide', state.dispose, { once: true });
})();
