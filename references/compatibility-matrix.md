# 跨浏览器和脚本管理器兼容矩阵

以下是设计时的风险矩阵，不是对所有版本的永久保证；发布前要在目标版本实测。

| 能力 | Tampermonkey Chromium | Tampermonkey Firefox | Violentmonkey | 处理方式 |
| --- | --- | --- | --- | --- |
| `@match`/`@include`/`@exclude` | 支持 | 支持 | 支持 | 以精确 `@match` 为主，实测边界 |
| `@run-at` | 支持 | 支持 | 支持 | 不把时机当成页面 bundle 顺序保证 |
| `@noframes` | 支持 | 支持 | 支持 | 用 iframe 场景验证 |
| `@grant none` | 支持 | 支持 | 支持 | 与 GM API 调用互斥 |
| legacy `GM_*` | 支持 | 支持 | 兼容度较高 | 需声明 grant，按目标版本测试 |
| modern `GM.*` | 支持程度随版本变化 | 支持程度随版本变化 | 支持程度随版本变化 | 以官方 API 文档和类型包核对 |
| `GM.xmlHttpRequest` | 支持，受 `@connect` 影响 | 支持，网络栈/权限可能不同 | 支持兼容 API | 测试重定向、超时、响应类型和 cookies |
| `@run-in` | Tampermonkey 5.3+ | Tampermonkey 5.3+，含 container 场景 | 不默认假设支持 | 不支持时拆分匹配或运行时判断 |
| `@sandbox` | Tampermonkey 4.18+ | 上下文差异更明显 | 语义不同或不完整 | 按 DOM/页面世界需求选择并实测 |
| `GM_webRequest` | 实验性；Chrome/MV3 TM 5.2+ 不可用 | 版本相关 | 不作为通用依赖 | 设计替代方案 |
| 浏览器扩展环境 | Chrome 与 Edge 同为 Chromium 但商店/策略不同 | WebExtensions sandbox/CSP 差异 | 管理器实现差异 | 至少验证实际交付浏览器 |

## 兼容实现策略

- 能力检测优先于 UA 判断：检测 `GM?.getValue`、`GM_getValue`、`GM?.xmlHttpRequest` 等可用接口。
- 将 API 适配包集中在一个模块，不让业务代码到处判断管理器。
- 对 `@sandbox`、页面世界和 `unsafeWindow` 设计明确 fallback；失败时禁用该功能，而不是破坏整页。
- 记录实际版本，例如 `GM_info?.version`、`GM_info?.script?.version` 和浏览器 user agent，但不要据此绕过权限。
- 类型包只用于开发期提示，不代表运行时支持。

## 最小测试组合

若声明全浏览器支持，至少做 Chrome/Edge 任选两个 Chromium 实测、Firefox 实测，并在 Tampermonkey 与 Violentmonkey 中验证 metadata、初始化、存储和网络；无法完成的组合必须在交付中明确列出。
