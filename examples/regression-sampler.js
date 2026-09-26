// 在 DevTools Console 中运行：只读采样目标容器的几何变化和 mutation。
// 将 SELECTOR 替换为实际容器；不要直接复制为生产 userscript。
(() => {
  const SELECTOR = '[data-target-feed]';
  const root = document.querySelector(SELECTOR);
  if (!root) throw new Error(`missing ${SELECTOR}`);
  const cards = [...root.children];
  const previous = new Map(cards.map((element) => {
    const rect = element.getBoundingClientRect();
    return [element, { top: rect.top, left: rect.left, height: rect.height }];
  }));
  const result = { started: performance.now(), geometryChanges: 0, mutations: 0 };
  const observer = new MutationObserver((records) => {
    result.mutations += records.length;
  });
  observer.observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style'] });
  const timer = setInterval(() => {
    for (const element of cards) {
      const before = previous.get(element);
      const rect = element.getBoundingClientRect();
      if (before && (Math.abs(before.top - rect.top) > 1 || Math.abs(before.left - rect.left) > 1 || Math.abs(before.height - rect.height) > 1)) {
        result.geometryChanges += 1;
      }
      previous.set(element, { top: rect.top, left: rect.left, height: rect.height });
    }
  }, 100);
  window.__USERSCRIPT_REGRESSION_SAMPLE__ = result;
  window.stopUserscriptRegressionSample = () => {
    clearInterval(timer);
    observer.disconnect();
    return { ...result, elapsedMs: Math.round(performance.now() - result.started) };
  };
  return result;
})();
