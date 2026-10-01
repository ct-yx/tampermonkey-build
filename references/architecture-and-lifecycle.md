# 架构、生命周期与清理

## 项目结构与分层

单文件脚本适合小功能。大型 userscript 可逐步形成清晰结构，而不是一次性重构：

```text
src/
  entry/       入口、生命周期和模块注册
  modules/     按页面功能拆分的模块
  core/        不依赖 DOM 的纯逻辑和可测试逻辑
  adapters/    Tampermonkey API 与浏览器能力适配
tests/         行为测试
build/         构建脚本
generated/     构建产物和生成说明
<repo-root>/<name>.user.js  # 需要 Raw 更新时，由源码生成的发布文件
```

结构可以按项目实际情况调整。站点选择器集中管理；纯逻辑尽量不依赖实时 DOM，便于单元测试。大型项目逐步减少通过 `indexOf`/`slice` 等字符串位置截取源码函数来测试的做法，改为导出纯函数或从模块边界调用行为。

功能模块应声明适用页面/路由，并提供 `install()`/`dispose()` 或等价生命周期。小型 Adapter 可封装 `GM_xmlhttpRequest`、`GM_download`、通知、存储等 userscript API；这仍是 userscript 运行时适配，不要求默认支持扩展。只有存在第二个实际运行环境时，才引入真正的跨环境接口。

## 页面作用域

先判断目标网站的页面/路由类型，再挂载对应模块；不要因脚本全局启用就让每项功能运行在所有页面。页面类型按站点实际结构定义，可包括首页、搜索、详情、列表/合集、个人页面、抽屉/弹层和 iframe。模块的 `@match` 范围与运行时路由判断共同确定作用域。

当不同页面族有不同的数据结构、接口语义或交互生命周期时，使用独立的解析器和请求处理逻辑；例如某站点的标准内容与分集内容接口并不相同时，不要假设两者可以互换。SPA 路由切换时先清理旧页面的监听器、未完成请求、定时器和页面级缓存，再安装新路由模块，避免无关页面被影响。

测试应包含与项目相关的作用域边界：目标模块只在声明的页面类型运行；不同页面族调用各自的数据处理逻辑；路由离开后旧模块不再响应事件、发起请求或写入状态。

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
