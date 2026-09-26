# Metadata 与权限规范

## 基本结构

```javascript
// ==UserScript==
// @name         Example
// @namespace    https://example.com/userscripts
// @version      1.0.0
// @description  Short description
// @match        https://example.com/*
// @grant        GM_getValue
// @grant        GM_setValue
// @run-at       document-start
// @noframes
// ==/UserScript==
```

metadata block 应位于文件开头附近，使用注释形式。发布前检查名称、命名空间、版本、描述、匹配范围和权限是否与实际代码一致。

## URL 范围

- `@match` 是首选，精确到协议、主机和必要的路径；不要无理由使用 `*://*/*`。
- `@include` 是兼容旧脚本的宽松匹配方式，使用时说明原因。
- `@exclude` 覆盖匹配结果，尤其用于排除登录页、管理页或 iframe。
- `@noframes` 只在脚本不应运行于 iframe 时使用；站点内嵌播放器、跨域 frame 和同域 frame 要分别验证。
- 站点有多个子域时分别列出实际需要的域名，不要用模糊通配符掩盖范围。

## 注入时机和上下文

- `@run-at document-start`：尽早注入，但不是“必然早于所有页面脚本”。`@require` 下载慢时也可能延迟执行。
- `document-body`、`document-end`、`document-idle`：按 DOM 可用性和页面竞争关系选择；不用早期时机解决本应由生命周期管理解决的问题。
- `@run-in` 是 Tampermonkey 5.3+ 的上下文控制能力，可区分 normal/incognito tabs 或 Firefox container；使用前核对目标管理器支持。
- `@sandbox`：
  - `DOM`：只需要 DOM，适合不需要直接页面世界访问的脚本。
  - `JavaScript`：需要 `unsafeWindow` 等页面交互能力。
  - `raw`：兼容性优先、要求页面世界时使用，但要承认隔离和 CSP 风险。
- 页面世界、userscript world、isolated world 之间的对象不能默认互相透明；跨世界传递值时使用可序列化数据和明确桥接。

## grant 与 connect

`@grant` 是权限白名单，不是功能开关。只列出代码实际调用的权限，并在改代码后同步更新 metadata。

常见对应关系：

| 代码能力 | 典型声明 |
| --- | --- |
| `GM_getValue`/`GM_setValue`、`GM.getValue`/`GM.setValue` | 对应 legacy 或 modern API grant |
| `GM_xmlhttpRequest`/`GM.xmlHttpRequest` | 对应请求 grant，以及目标域名的 `@connect` |
| `GM_addStyle`、`GM_addElement` | 对应 API grant |
| `GM_registerMenuCommand` | 对应菜单 grant |
| `GM_download`、`GM_notification` | 对应下载/通知 grant |
| `GM_setClipboard` | 对应剪贴板 grant |
| `unsafeWindow` | `unsafeWindow` grant；必要时配合 `@sandbox JavaScript` |
| `window.close`、`window.focus`、`window.onurlchange` | 对应 `window.*` grant |

`@grant none` 表示禁用 GM 沙箱 API，不可与实际 GM API 调用混用；`GM_info` 的可见性按当前管理器文档核对，不要用它作为绕过权限的方式。

`@connect` 只写实际请求的主机，例如：

```text
// @connect api.example.com
// @connect cdn.example.com
```

`@connect *` 会扩大信任边界并可能引发授权提示，只在确实无法枚举目标且用户理解风险时使用。对重定向后的最终主机也要验证。

## 更新和分发字段

`@updateURL`、`@downloadURL`、`@supportURL`、`@homepage` 等字段要指向可信、可审计的发布位置。更新地址和下载地址不要在没有稳定发布流程时随意填写。版本号要遵守项目约定，并在构建产物中只保留一个有效 metadata block。

## 常见错误

- `@match` 漏掉实际子域，导致“脚本偶尔不运行”。
- 使用 GM API 却写了 `@grant none`。
- `GM_xmlhttpRequest` 有 `@grant` 却没有 `@connect`。
- 只测试顶层页面，忘记 `@noframes` 和 iframe。
- 把页面 `fetch` 的 CORS 问题误认为 `GM_xmlhttpRequest` 权限问题。
- 用 `@run-at document-start` 解决选择器竞态，却没有等待目标容器出现。
