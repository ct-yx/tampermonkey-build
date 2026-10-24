# js-reverse-mcp（可选的 JavaScript 逆向调试）

本文只在用户明确需要混淆代码分析、运行时断点、调用栈或请求来源追踪时读取。它是 `tampermonkey-build` 的可选调试后端，不改变 userscript 的默认开发、测试和发布流程。

## 定位

`js-reverse-mcp` 是独立的 MCP Server，不是几份辅助 Markdown，也不是 `chrome-devtools-mcp` 的文档层。它使用 MCP SDK 注册实际工具，并提供自己的浏览器控制和 CDP 调试实现。调查时核对到 npm `4.0.5`、Apache-2.0、Node.js `^20.19.0 || ^22.12.0 || >=23`；版本和工具集合在使用前仍须重新核对。

项目来源：

- GitHub：<https://github.com/zhizhuodemao/js-reverse-mcp>
- npm：<https://www.npmjs.com/package/js-reverse-mcp>

## 何时使用

只有普通页面调试证据不足时才启用，例如：

- 定位混淆脚本中的加密、签名或参数生成函数；
- 需要在压缩脚本文本处设置断点；
- 需要暂停后的调用栈、作用域变量和单步执行；
- 需要追踪 XHR/Fetch 的触发位置；
- 需要分析 WebSocket 消息或导出较完整的网络材料。

DOM、Console、普通 Network、Performance、Lighthouse、Memory 和常规页面交互仍优先使用 `chrome-devtools-mcp` 或真实 Edge DevTools。

## 实际 MCP 工具

当前项目 README 列出的 24 个工具分为：

| 类别 | 工具 |
| --- | --- |
| 页面 | `select_page`、`new_page`、`navigate_page`、`select_frame`、`click_element`、`take_screenshot` |
| 脚本 | `list_scripts`、`get_script_source`、`save_script_source`、`search_in_sources` |
| 断点 | `set_breakpoint_on_text`、`break_on_xhr`、`remove_breakpoint`、`list_breakpoints`、`get_paused_info`、`pause_or_resume`、`step` |
| 网络 | `list_network_requests`、`clear_network_requests`、`get_request_initiator`、`get_websocket_messages` |
| 页面状态 | `clear_site_data` |
| 页面执行/Console | `evaluate_script`、`list_console_messages` |

这些是可调用的 MCP 工具，不是文档示例。工具名称、参数和返回结构必须以当前版本的 `tools/list` 和运行时帮助为准。

## 和 chrome-devtools-mcp 的关系

两者有部分重叠，但不是替代关系：

| 能力 | `js-reverse-mcp` | `chrome-devtools-mcp` |
| --- | --- | --- |
| 页面选择、导航、截图、页面执行 | 支持 | 支持 |
| Console、Network | 支持 | 支持，页面取证更完整 |
| 加载脚本检索、源码保存 | 强项 | 非主要能力 |
| 文本断点、XHR/Fetch 断点 | 强项 | 当前没有直接通用工具 |
| 调用栈、作用域、单步 | 强项 | 当前没有直接通用工具 |
| DOM 快照、UID、可访问性树 | 非主要能力 | 强项 |
| 点击、输入、拖拽、上传、等待 | 部分支持 | 更完整 |
| Performance Trace、Lighthouse | 不提供同等工具 | 强项 |
| CPU/网络模拟、Heap Snapshot | 不提供同等工具 | 强项或按能力开关启用 |
| 扩展、PWA、Screencast、WebMCP | 不提供同等工具 | 提供相应工具 |

因此：

- 不要因为安装了 `js-reverse-mcp` 就删除 `chrome-devtools-mcp`；
- 只做 JS 逆向时可以单独使用 `js-reverse-mcp`；
- 一般 userscript 开发和性能/页面调试仍保留 `chrome-devtools-mcp`；
- 两个 MCP 不要同时控制同一个页面的 Debugger 或 Network 状态。需要切换时先停止当前调试器、重新选择页面并重新采样。

## Edge/CDP 连接

`js-reverse-mcp` 默认会启动自己的 Chrome profile。要验证 Edge + Tampermonkey，必须连接一个已开启 CDP 的 Edge 实例：

```bash
curl http://127.0.0.1:<端口>/json/version
```

返回包含 `webSocketDebuggerUrl` 的 JSON 后，才可以使用：

```bash
npx --yes js-reverse-mcp@4.0.5 \
  --browserUrl http://127.0.0.1:<端口> \
  --allowedRoots /绝对路径/专用分析目录
```

`4.0.5` 是本次调查核对的版本示例；如果 `npm view` 返回了新版本，先重新核对参数和工具集合，再更新锁定版本。不要长期使用未锁定的 `latest`。

连接前应使用独立 Edge profile，避免把日常 Cookie、扩展和登录态暴露给 MCP；该 profile 需要单独安装并启用 Tampermonkey。连接验证顺序为：

```text
/json/version
→ 启动单个 js-reverse MCP 实例
→ list_pages/select_page
→ 校验目标 URL
→ 无副作用 evaluate_script
→ 再设置断点或采集 Network
```

`--browserUrl` 只能连接 CDP HTTP 端点，不接受厂商私有管理 API。Edge 的端口、Origin 限制和远程调试策略必须以当前实例为准，不写死端口或页面 ID。

`--cloak` 会启动独立的 CloakBrowser，并且与 `--browserUrl` 冲突；它不是 Edge + Tampermonkey 实测的默认方案。只在用户明确需要独立浏览器环境且接受其差异时考虑。

## 安全和权限边界

该 MCP 可以读取或修改页面数据，读取 Cookie、请求/响应和脚本源码，也能读写本地文件并清理站点状态。使用时：

- 只在用户授权的页面和逆向分析场景中使用；
- 优先指定 `--allowedRoots` 到专用目录；
- 不在包含密码、支付信息或重要登录态的页面上运行；
- 不把完整 Cookie、token、请求体或响应体写入聊天记录或仓库；
- 不使用 `DEBUG=*`，避免协议日志泄露页面材料；
- 不把 `--no-usage-statistics` 从 Chrome DevTools MCP 配置复制过来；当前核对的 `js-reverse-mcp 4.0.5` CLI 没有该参数。

安装或注册 MCP 不是 userscript 开发的默认初始化动作。只有用户明确要求启用 JS 逆向能力时，才按当前版本重新核对 npm 包、CLI 帮助、Edge CDP 状态和全局配置；不要自动注册第二个浏览器调试 daemon。

## 记录结果

报告中单独记录：

```text
js_reverse_mcp: not_needed | unavailable | used
js_reverse_version: <实际核对版本>
browser_backend: edge-cdp | managed-chrome | unknown
target_page: <脱敏后的 URL 或页面说明>
breakpoint_evidence: yes | no
network_evidence: yes | no
chrome_devtools_mcp_used: yes | no
known_limits: <未覆盖的 DevTools 能力>
```
