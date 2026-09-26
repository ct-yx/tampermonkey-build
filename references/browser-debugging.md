# 浏览器调试与真实页面联调

需要使用浏览器 DevTools MCP 时，先阅读 [devtools-mcp.md](devtools-mcp.md)；需要使用 Codex 内置浏览器复现页面行为时，先阅读 [browser-runtime.md](browser-runtime.md)。本文保留跨浏览器的调试原则和证据要求。

## 调试顺序

1. 确认脚本 metadata 匹配当前 URL，读取 `GM_info` 或脚本面板确认版本。
2. 优先在 Codex 内置浏览器中自动完成加载、刷新、滚动、悬停、SPA 导航、回退和再次进入，先固定用户可见症状。
3. 在 Console 记录脚本初始化标记、错误和关键统计对象。
4. 在 Elements/DOM 中确认目标节点、父子关系、Shadow DOM、iframe 和页面重绘来源。
5. 在 Network 中确认请求 URL、优先级、状态、重定向、缓存、响应时间和失败节点。
6. 用 Performance/Performance Insights 录制用户实际操作，检查长任务、布局抖动、重复请求和 CLS。

内置浏览器的自主回归不能依赖用户每轮连接 Tampermonkey Editors。已有桥接就复用，未连接就继续本地文件、临时注入或隔离页面验证；只有需要确认已安装脚本内容或执行已授权同步时，才调用 Tampermonkey MCP。

## Chrome/Edge

Chromium DevTools MCP 可用于列页面、取 snapshot、evaluate、读取 console/network、截屏、模拟 CPU/网络和性能 trace。连接成功不等于目标可控；先确认 `list_pages`、目标 URL 和一次无副作用 evaluation 均成功。

常用能力对照：

| 调试证据 | Codex 内置浏览器 | DevTools MCP | 仍需真实 DevTools/专用 CDP |
| --- | --- | --- | --- |
| 页面打开、选择标签页、UI 操作 | 主要工具 | 按版本支持 | - |
| 截图和可见结果 | 主要工具 | 支持 | - |
| 页面列表、快照、页面侧采样 | 不默认提供完整接口 | 支持 | - |
| Console 和 Network 列表 | 不默认保证 | 支持 | - |
| Performance trace、CPU/网络模拟 | 不默认保证 | 支持 | 复杂面板交互 |
| Heap snapshot | 不默认保证 | 需启用 Memory 能力 | 深入图形化分析 |
| Lighthouse | 不默认保证 | 支持导航/快照审计 | - |
| JS 断点、条件断点、单步 | 不默认提供 | 不直接支持 | 支持 |
| HAR、Coverage、Layers | 不默认提供 | 不提供完整直接接口 | 支持 |
| Service Worker Application 面板 | 不默认提供 | 仅部分页面/脚本能力 | 支持 |
| userscript 读取/写入 | 不负责 | 不负责 | Tampermonkey MCP |

内置浏览器适合验证“用户看到了什么、操作能否完成、问题是否能稳定复现”。它不自动继承 Edge 的 Tampermonkey、登录态、扩展、缓存和 F12 状态；需要真实 userscript、CDN、Console 或网络证据时，必须切换到目标 Edge/Chrome 的 DevTools MCP。详细的上下文选择、临时注入和记录模板见 [browser-runtime.md](browser-runtime.md)。

推荐最短路径：

    list_pages
    → 选择目标页面
    → take_snapshot
    → evaluate_script
    → list_console_messages
    → list_network_requests
    → performance trace
    → 回归验证

`take_snapshot`、`evaluate_script` 和截图不能互相替代：快照用于结构/UID，evaluate 用于可复现页面采样，截图只用于可见结果核对。

内置浏览器的截图和交互结果也不能替代 `take_snapshot`、`evaluate_script` 或 Network/Performance 证据。对于闪烁、信息流缺失、CDN 慢和布局抖动，应先用内置浏览器复现可见症状，再用 DevTools MCP 确定 DOM、请求和性能原因。

可以临时注入本地构建产物进行隔离验证，但临时注入不是安装和发布：

- 使用单独浏览器上下文或独立页面。
- 记录注入版本和启动时间。
- 验证后关闭隔离页或刷新恢复页面。
- 不通过浏览器编辑器修改源码；源码只在文件系统中编辑。

## Firefox

使用 WebExtension/Firefox DevTools 检查脚本的 sandbox、container、frame 和 CSP 行为。不要把 Chrome 的页面世界、`@sandbox` 或 `GM.*` 结果直接推断到 Firefox；至少验证顶层页面、iframe、容器和跨域请求。

本文中的 Chromium MCP 命令不作为 Firefox MCP 能力承诺；Firefox 需要根据当前 WebExtension/DevTools 连接工具重新核对。

## 观测样本

```javascript
(() => {
  const key = '__USERSCRIPT_DEBUG__';
  const stat = window[key] ||= { started: performance.now(), events: [] };
  stat.events.push({
    type: 'sample',
    at: Math.round(performance.now() - stat.started),
    ready: document.readyState,
    href: location.href,
    cards: document.querySelectorAll('[data-target-card]').length,
  });
  return structuredClone(stat);
})();
```

只读取信息时关闭 `waitForStableDom` 或使用等价的无副作用模式，避免调试工具本身等待页面稳定而改变时序。

## 错误归因

分别收集：

- userscript 文件名/行号的异常；
- 页面 bundle 的异常；
- `ERR_BLOCKED_BY_CLIENT` 等扩展或广告拦截异常；
- 网络请求状态/响应体异常；
- 视觉变化对应的 DOM mutation 和几何采样。

截图只能证明可见结果，不能替代 DOM、Network 或性能证据。未连接真实浏览器时要明确标注“未实测”。
