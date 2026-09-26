# 架构、生命周期与清理

## 分层

推荐划分为：

1. metadata 与能力检测。
2. 页面/路由适配器。
3. 纯函数核心逻辑。
4. DOM 渲染和事件绑定。
5. 网络和缓存适配器。
6. 调试统计与 cleanup。

站点选择器集中管理；纯函数不依赖实时 DOM，便于静态测试和回归。每个功能模块暴露 `install()`/`dispose()` 或等价生命周期。

## 幂等入口

```javascript
const STATE = Symbol.for('example.userscript.state');
function install() {
  if (window[STATE]?.installed) return window[STATE].dispose;
  const cleanups = [];
  const dispose = () => {
    while (cleanups.length) cleanups.pop()();
  };
  window[STATE] = { installed: true, dispose };
  return dispose;
}
```

实际项目可以使用更简单的命名空间标记，但必须能判断重复注入。事件监听、计时器、Observer、属性 patch、样式节点和缓存任务都要登记 cleanup。

## SPA 和路由

- 监听 `popstate`、`hashchange`、站点路由事件或受控的 history patch。
- 路由变化时先 dispose 当前页面实例，再按目标 URL 安装。
- 只在需要时监听容器替换；不要对 `document.body` 开启全树高频属性观察。
- 页面节点异步出现时优先使用一次性容器/直接子节点观察或受限的 MutationObserver。
- 观察器 callback 中不要立即进行多次 `getComputedStyle`/`getBoundingClientRect`；批量到一个 `requestAnimationFrame`，并限制元素数量。

## MutationObserver 和布局

监听范围按问题最小化：

- 只关心新增卡片：`childList` + 目标容器。
- 只关心资源属性：指定节点 + 指定 `attributeFilter`。
- 不要把 `class`、`style`、`src` 和整棵子树无条件组合在一起。

如果脚本写入的 class/style 会触发站点框架重绘，容易形成“脚本修改 -> 页面重绘 -> Observer 再修改”的反馈回路。使用不会被站点重写的命名空间 data 属性、CSS 规则或内部 WeakMap，并让写入操作幂等。

## 页面世界、sandbox 和 Shadow DOM

需要包装页面 `fetch`/XHR 或读取页面私有对象时，明确选择页面世界/`@sandbox`，并验证 Chromium 与 Firefox 的对象边界。只操作 DOM 时优先使用隔离上下文，减少页面污染。

Shadow DOM 需要在宿主出现后进入 shadow root；不能假设 `document.querySelector` 能找到 shadow 内部元素。跨域 iframe 不可直接读取，使用页面公开消息或放宽 metadata 后在目标 frame 中运行。

## 资源和网络清理

AbortController、GM 请求返回的 abort、定时器和事件监听都要在 dispose 中处理。缓存必须有 TTL、版本键和失败回退；重试次数、间隔和并发数必须有上限。页面卸载时不要继续创建请求或写入状态。
