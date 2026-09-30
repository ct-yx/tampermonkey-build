# Codex 内置浏览器与 Browser Runtime

本文说明 Codex 提供的内置浏览器或浏览器自动化连接器在 userscript 开发中的定位。当前它是页面 DOM、快照、截图和可见布局观察工具，不是默认的 userscript/扩展运行时，也不是 Tampermonkey 脚本管理器，更不等同于用户正在使用的 Edge F12。

## 1. 能力定位

内置浏览器适合完成：

- 打开目标 URL、选择或创建标签页；
- 点击、输入、悬停、滚动、刷新和返回等真实 UI 操作；
- 检查页面是否出现目标信息流、预览、按钮、菜单和错误排版；
- 复现首页、搜索页、播放页、SPA 切换、懒加载和悬停预览；
- 通过截图、可见文本和交互结果确认闪烁、错位、抖动、空白或加载顺序；
- 在隔离的浏览器上下文中观察临时测试的用户可见效果。

真实开发与运行以 Edge 为准：Edge 页面控制扩展负责交互，Edge DevTools/CDP 负责深层页面证据，Tampermonkey 和自有 Userscript Bridge 负责真实脚本链路。Codex 内置浏览器只补充 DOM、快照、截图和布局观察。

## 1.1 自主测试契约

内置浏览器的页面观察应尽量由代理连续完成：复用/创建标签页、导航、截图、快照、滚动、悬停和关键交互不应要求用户逐轮点击。开发时以本地文件为事实来源；真实脚本、扩展和 Tampermonkey 同步在 Edge 完成，细节见 `mcp-workflow.md` 与 `editors-native-bridge.md`。

真实 Edge/Chrome 页面取证前还需要用户解锁目标浏览器的 CDT/CDP 远程调试权限；内置浏览器自身不代表已经取得用户 Edge 的 CDP 权限。Tampermonkey 安装、自有 bridge 状态和 CDP 权限都必须按当前 profile 分开记录。

内置浏览器不应被默认描述为：

- 用户 Edge 的同一个浏览器进程、同一个用户目录或同一个 F12 窗口；
- 自动继承用户 Edge 的 Tampermonkey、Violentmonkey、登录态、Cookie、缓存、代理、扩展和权限；
- 能够无条件直接控制 `chrome-extension://` 页面或扩展弹窗；如果当前 URL policy 拒绝扩展页，不得用原始 CDP、替代 URL 或间接方式绕过；
- 完整的 Console、Network、Performance、Memory、断点、HAR、Coverage、Layers 或 Service Worker 调试器；
- 能够证明真实 Edge、真实 userscript 和真实 CDN 节点已经按预期工作。

在 Codex 官方修复扩展加载导致的宿主崩溃前，不要在内置浏览器安装或加载自有桥接扩展 ZIP；该路径标记为暂停，而不是开发失败。官方修复后才重新做最小空扩展测试，再决定是否恢复。

具体能力取决于当前连接器、浏览器类型、页面上下文和运行时文档。连接器能打开一个页面，不代表它能读取该页面的网络请求或 userscript 沙箱；但这不影响内置浏览器直接完成可见页面回归。

## 2. 运行时入口

当前 Codex 环境可能通过 unified-computer-use 的 cua_repl 暴露浏览器控制；有些环境会提供不同名称的浏览器工具。工具名称、动作方法和返回字段必须以当前工具列表和首次运行时文档为准，不要把本节示意代码当成所有环境的永久 API。

使用 CUA 时，首次调用或重置后先执行一个初始化入口，例如：

    await cua.getState()

然后根据目标选择已有标签页或创建内置浏览器标签页：

    let tab = await cua.createBrowserTab("iab", targetUrl, { visible: true })

或：

    let tab = await cua.getTab({ url: targetUrl })

如果用户明确要求操作某个已连接的 Chrome/Edge 浏览器，应先按工具文档选择对应浏览器和标签页；不要因为 URL 相同就假设它与 in-app browser 是同一上下文。

操作 tab 的点击、输入、悬停、滚动、截图和等待方法以运行时返回的文档为准。不要凭经验臆造未列出的 API。需要读取页面脚本变量、Console、Network 或性能 trace 时，应切换到浏览器 DevTools MCP 或真实 DevTools。

### 扩展 ID 动态发现

不要把 Tampermonkey 或自有 bridge 的扩展 ID 写入技能。需要识别扩展时，从目标 Edge 的标签页、扩展清单或运行时返回的 URL 中匹配 `chrome-extension://<id>/`，再根据实际观察到的 ID 识别目标扩展页。ID 只保存在当前运行记录中，不作为跨会话常量；不同浏览器、不同 profile 和不同安装实例可能不同。Codex 内置浏览器不作为扩展安装或扩展页控制入口。

如果当前工具只能看到 `vscode.dev` 或目标站点，直接使用这些 HTTPS 页面完成开发和测试；扩展 ID 动态发现失败不应阻塞自主回归。

## 3. 与其他工具的职责边界

| 工作 | Codex 内置浏览器 | Edge/Chrome DevTools MCP | 自有 Userscript Bridge |
| --- | --- | --- | --- |
| 打开页面和选择标签页 | 补充观察 | Edge 页面控制扩展/按版本支持 | 不负责 |
| 点击、输入、滚动、悬停 | 补充观察 | Edge 页面控制扩展 | 不负责 |
| 截图和可见结果 | 主要工具 | Edge 页面控制扩展/DevTools | 不负责 |
| DOM 快照和页面侧采样 | 主要工具 | Edge DevTools MCP | 不负责 |
| Console、Network、Performance | 不默认保证 | Edge DevTools MCP | 不负责 |
| 断点、Coverage、Layers、Service Worker 面板 | 不默认提供 | 复杂场景用真实 DevTools 或专用 CDP 工具 | 不负责 |
| 读取、备份和写入 userscript | 不负责 | 不负责 | 仅在用户要求且获授权时使用 |
| 真实 Edge + 已安装管理器验证 | 不保证 | 负责页面证据 | 提供脚本同步，不代替页面验证 |

三者可以并行使用，但连接、权限、Cookie、页面 ID 和脚本状态不共享。内置浏览器只作结构/可见观察；Edge 才作真实 userscript 和扩展回归。一个工具成功不能替另一个工具作出结论。

## 4. 面向 userscript 的标准流程

### A. 用内置浏览器观察页面结构和用户症状

1. 打开目标页面并记录最终 URL、浏览器上下文和标签页标识。
2. 观察初始页面、刷新、SPA 导航、滚动、悬停和再次进入。
3. 用截图或可见文本记录信息流数量、图片/视频预览、排版位置和闪烁时机。
4. 重复同一动作若干次，区分稳定问题、偶发问题和只在特定上下文出现的问题。

内置浏览器适合回答“页面结构是什么、用户看到了什么、布局是否抖动”。它不能单独回答“哪个 userscript 是否实际运行”“哪个请求慢”“哪个脚本抛错”或“该节点是否来自某个 CDN”；这些结论回到 Edge。

### B. 在 Edge 完成真实开发回归

1. 通过 Edge 页面控制扩展连接目标标签页并执行刷新、滚动、悬停和 SPA 操作。
2. 确认 Edge profile 的 Tampermonkey 正在运行本地脚本。
3. 通过自有 Userscript Bridge CLI 读取/写入已安装脚本（仅在用户要求并授权时）。
4. 通过 Edge DevTools MCP 或真实 F12 取得 Console、Network 和 Performance 证据。

### C. 再用 Edge DevTools MCP 获取证据

在需要确定原因时切换到真实 Edge 的 DevTools MCP：

    list_pages
    → 校验目标 URL
    → take_snapshot
    → evaluate_script
    → list_console_messages
    → list_network_requests
    → performance trace

具体工具名和参数以 devtools-mcp.md 及运行时帮助为准。先做无副作用页面检查，再做 DOM、Console、Network 和性能采样。

### C. 可选地同步已安装脚本

本地文件是源码事实来源。自有 Userscript Bridge 只在用户要求管理已安装脚本并明确授权后用于读取、备份、生成差异和写入；它不是内置浏览器回归的前置条件：

1. 读取目标脚本和版本；
2. 本地备份并完成 metadata、语法和回归检查；
3. 在即将写入前重新确认目标和授权范围；
4. 写入后重新读取；
5. 回到真实浏览器复测。

bridge 不可用时继续使用本地/隔离验证，并在结果中标记“未同步到 Tampermonkey”。内置浏览器中的临时结果不得表述为“已写入 Tampermonkey”。

## 5. 用户脚本验证清单

针对首页或信息流性能优化，至少记录：

- 首屏是否出现目标卡片，以及出现几行；
- 后续滚动是否继续加载，是否重复、缺失或顺序错误；
- 图片、视频和 hover 预览是否出现空白、闪烁、抖动或错位；
- 刷新、返回、SPA 切换和重复进入后是否重复注入；
- 交互期间是否能点击稍后再看、播放、关注等原有控件；
- 同一页面重复测试时，问题出现的次数和上下文；
- 内置浏览器是否有登录态、扩展和脚本管理器，不能猜测；
- 哪些结论来自截图/可见文本，哪些结论来自 DevTools Network/Console/Performance。

如果只在内置浏览器复现了视觉问题，交付记录应写“内置浏览器 DOM/视觉观察”；如果没有在真实 Edge 中验证 userscript，不得写成“Edge 已验证”。

## 6. 临时注入和源码边界

内置浏览器不是源码编辑器。源码、构建产物和 metadata 只在本地文件中维护，不通过浏览器页面的编辑器长期修改。

若需要隔离比较：

- 优先使用独立页面或独立浏览器上下文；
- 记录临时注入的文件版本、时间和注入方式；
- 只注入最小测试逻辑，并设置明确的停止条件；
- 关闭页面或刷新后确认临时改动消失；
- 不把临时注入结果当作已安装版本结果；
- 不因内置浏览器缺少 Tampermonkey 而自动安装扩展或覆盖用户脚本；自有 bridge 不可用时回到 Edge 手动/DevTools 验证和内置浏览器 DOM 观察。

页面侧的临时 evaluate、脚本管理器中的临时注入和 userscript 沙箱不是同一执行环境；它们的权限、世界、时机和生命周期必须分别记录。

## 7. 失败归因、隐私和记录

把问题拆成以下类别：

- 浏览器连接器无法创建或选择标签页；
- 页面加载、站点自身脚本或登录状态问题；
- userscript 未匹配、未运行或运行时报错；
- DevTools MCP 连接、页面 ID、远程调试端口或权限问题；
- 广告拦截、隐私扩展、网络节点或代理问题；
- 仅有视觉差异但缺少 DOM/Network/性能证据。

诊断记录只保留复现所需信息。不要记录 Cookie、token、密码、完整个人页面内容或不必要的请求头；Network 证据应脱敏 URL 参数和响应体中的身份信息。

推荐记录模板：

    浏览器/上下文：
    浏览器版本：
    页面 URL：
    标签页或页面 ID：
    userscript 名称与版本：
    管理器及版本：
    是否临时注入：
    内置浏览器复现步骤：
    可见结果/截图：
    DevTools Console 证据：
    DevTools Network 证据：
    DevTools Performance 证据：
    是否写入 Tampermonkey：
    未验证的边界：

最终报告必须区分“内置浏览器已观察”“DevTools MCP 已取证”“真实 DevTools 面板已验证”和“Tampermonkey 已写入并复测”。
