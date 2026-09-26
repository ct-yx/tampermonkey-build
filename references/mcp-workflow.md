# MCP 初始化与 Tampermonkey 工作流（可选桥接）

## 首次初始化：安装并注册全部技能 MCP

首次使用本技能或初始化新环境时，按环境配置检查并确保下列 MCP 服务器已安装并全局注册。它们是增强能力；即使 Tampermonkey MCP 未连接，也必须能够完成本地开发和内置浏览器回归：

| MCP 服务器 | 用途 | 上游来源 |
| --- | --- | --- |
| Tampermonkey MCP | 读取、备份和在授权后写入已安装 userscript | https://github.com/Tampermonkey/tampermonkey-mcp |
| Chrome/Edge DevTools MCP（chrome-devtools-mcp） | 检查 Chromium 页面、Console、Network 和 Performance | https://github.com/ChromeDevTools/chrome-devtools-mcp |
| Greasy Fork MCP（mcp-greasyfork-scripts） | 搜索公开 userscript 和获取源码上下文 | https://github.com/yigitkonur/mcp-greasyfork-scripts |

把本地 MCP 文件放入 Codex 全局目录 `~/.codex/mcp/`，并注册为全局 MCP；不要放进当前项目。先检查现有文件和全局注册状态，只安装缺失的服务器，避免重复安装或创建重复配置。各服务器的安装命令、参数、版本要求和注册入口会变化，按当前官方仓库文档及当前 Codex CLI/设置说明执行，不复制过时命令。

### 初始化前置检查（需要先告知用户）

第一次初始化必须先列出以下浏览器侧条件，并在记录中标明状态：

- **CDT/CDP 权限**：用户在目标 Chrome/Edge 中开启并允许远程调试。Chrome 常见入口为 `chrome://inspect/#remote-debugging`，Edge 常见入口为 `edge://inspect/#remote-debugging`；企业策略、版本和实际入口优先于示例。
- **Tampermonkey**：在实际运行脚本的浏览器 profile 中安装并启用。内置浏览器与用户 Edge 是不同上下文，不会自动共享扩展、Cookie 或脚本库。
- **Tampermonkey Editors 连接能力**：仅在任务需要管理已安装脚本时安装/启用；它的形态可能是 Tampermonkey 内部入口或配套编辑连接组件，不能预设某个商店条目或扩展 ID。
- **DevTools MCP**：安装/注册本地 MCP 后，使用 `list_pages` 和一次无副作用页面检查验证真实能力；不要把 MCP 注册当作 CDP 已授权。

代理可以检测和验证这些条件，但不得静默安装浏览器扩展、修改浏览器安全策略或绕过用户确认。无法满足时继续本地文件和内置浏览器的可用流程，并把真实浏览器验证标记为未完成。

初始化后分别记录服务器注册和实际能力：内置浏览器先验证能否列出/打开目标页面并完成无副作用回归；DevTools MCP 需要时再列出页面并取证；Greasy Fork MCP 按需搜索；Tampermonkey MCP 只在 Editors 桥接已经存在时测试脚本列表/读取。不要默认调用 `tampermonkey_get_connection_code`，更不能让用户为每轮测试输入连接码。没有桥接时记录“可选脚本桥接未连接”，继续内置浏览器流程。

这项初始化要求只覆盖上表所列的全部技能 MCP。Firefox 的原生 DevTools 不属于此 MCP 清单。Editors 的安装形态和浏览器支持以当前运行时为准；不要把 Chrome、Edge 和内置浏览器之间的扩展实例、脚本库或登录态混用。连接码测试失败只表示桥接不可用，不表示目标脚本不存在。

只有在装有受支持 Editors 扩展、且与目标 Tampermonkey 实例配对的浏览器上下文里，才执行连接码握手并验证脚本读写能力。若当前浏览器工具能控制工具栏或扩展弹窗，代理可以在首次初始化时自动完成一次连接码输入和 Connect 点击；如果工具栏不可控或扩展页被 URL policy 拦截，不得绕过策略，应把桥接记为未自动建立并继续本地/内置浏览器流程。若目标脚本仅存在于 Edge，而 Edge 没有该桥接扩展，就继续用本地文件和 Edge DevTools MCP；不能把另一浏览器中的 Tampermonkey 实例误当作 Edge 的脚本库。安装 MCP 不授予写入 userscript 的权限。

Codex 内置浏览器通过当前环境提供的浏览器工具控制，属于默认运行时工具而非独立 MCP 服务器，因此不加入服务器安装清单；如何在不依赖用户操作的情况下使用见 `browser-runtime.md`。

## 连接生命周期：最多一次握手

Tampermonkey MCP 0.0.5 的 Editors WebSocket、连接码、认证状态和连接对象保存在 MCP 进程的内存中。stdio 客户端每启动一个进程就会得到一份独立状态；因此多个 stdio 进程不能共享一次 Editors 连接，也不能保证后续任务继续使用第一次连接。

为了满足“最多连接一次，之后不再重复连接”，正式工作流必须使用**单个长驻 HTTP MCP 服务**：

```bash
tampermonkey-mcp --transport=http --port=4001
```

然后让 Codex 只注册这个 Streamable HTTP 端点 `http://localhost:4001/mcp`。当前 Codex CLI 可用 `codex mcp add <name> --url <url>` 注册 URL；实际迁移前先备份配置，并删除/停用同名 stdio 条目，不能两种传输同时注册。若本机已有该端口的服务，先复用，不要再启动第二个进程；可以只读检查：

```bash
lsof -nP -iTCP:4001 -sTCP:LISTEN
```

连接状态按下面的状态机处理：

```text
未知
  └─ 先调用 tampermonkey_list 探测
      ├─ 成功 → 已连接：后续只复用，不再请求连接码
      └─ 明确未连接 → 本服务生命周期内只调用一次 get_connection_code
                         → 等待用户完成一次 Editors 握手
                         → 反复用 tampermonkey_list 验证，不重新生成连接码
```

硬性规则：

1. `tampermonkey_get_connection_code` 不是健康检查，不能在每轮任务、刷新、重试或 `tampermonkey_list` 超时后调用。
2. 已经成功过一次 `tampermonkey_list` 后，默认认为桥接可复用；普通脚本读写失败先检查目标 path、版本和并发修改，不重新握手。
3. 等待 Editors 输入连接码时只能等待或降级，不能循环生成新码。
4. 服务进程真正重启后，内存连接状态会丢失；这属于新的服务生命周期。代理不得自动循环重启或自动重新索要连接码，必须报告“持久服务已重启，需要一次重新授权”，并等待用户决定。
5. 发现多个同路径 MCP 进程时先停止启动新实例、切换到本地/内置浏览器验证；不自动杀进程。清理旧实例必须在确认目标和影响后单独执行。

如果只能使用 stdio，必须把它标为“单任务临时桥接”，不能承诺跨任务一次连接；除非用户明确要求管理已安装脚本，否则优先不启动 Tampermonkey MCP。

## 与浏览器 DevTools MCP 的并行边界

Tampermonkey MCP 管理已安装的 userscript；浏览器 DevTools MCP 调试真实页面。两者不共享权限、连接或状态，不能互相替代。浏览器页面验证流程见 `devtools-mcp.md`。

推荐流程：

    本地文件编辑
    → userscript 静态验证
    → Codex 内置浏览器自主页面回归
    → 按需使用 DevTools MCP 取得性能/网络证据
    → 已有桥接且用户明确授权时才写入 Tampermonkey
    → 写入后重新读取并验证

内置浏览器回归不需要 Tampermonkey MCP 连接。若桥接不可用，停止在本地/临时验证即可，不要为了恢复测试自动弹出连接码或等待用户点击；只有用户明确要求管理已安装脚本时，才把连接问题报告为该子任务的阻塞。

## Tampermonkey MCP 组件和连接

官方仓库：`https://github.com/Tampermonkey/tampermonkey-mcp`。

README 当前给出的典型配置是安装 Tampermonkey、按需启用 Tampermonkey Editors，再运行。持久连接优先使用 HTTP 传输；stdio 仅作为没有长驻服务能力时的临时降级：

```bash
npm install -g tampermonkey-mcp@latest
```

HTTP 服务示例：

```bash
tampermonkey-mcp --transport=http --port=4001
```

注册 `http://localhost:4001/mcp` 后只保留这一种传输。若客户端不支持 Streamable HTTP，再在明确说明“一次连接仅限该 stdio 进程生命周期”的前提下使用原来的 stdio 配置：

```json
{
  "mcpServers": {
    "tampermonkey": {
      "command": "npx",
      "args": ["-y", "tampermonkey-mcp@latest"]
    }
  }
}
```

首次环境初始化按上文安装 MCP 服务；日常任务先复用已注册的单实例服务。Tampermonkey Editors 是 Tampermonkey 生态提供的编辑连接入口，不应被固定描述成某个浏览器必有的独立扩展；它在不同浏览器中可能表现为 Tampermonkey 内部入口或配套编辑连接组件，以当前环境实际提供的入口为准。没有它或没有桥接时，继续可独立完成的本地和内置浏览器工作。

## 能力探测

仅在用户明确要求启用 Tampermonkey MCP，或当前任务确实需要读取/同步已安装脚本时，才执行以下一次性握手；先调用 `tampermonkey_list` 探测已存在的持久连接，只有明确返回未连接时才请求连接码：

1. 调用 `tampermonkey_get_connection_code`，将连接码交由用户在 Editors 扩展中输入。
2. 调用 `tampermonkey_list`，用返回的 path 精确选择脚本。
3. 调用 `tampermonkey_get` 读取内容和 `lastModified`。
4. 判断可用操作：`list/get/patch` 与 `put/delete` 的版本要求可能不同。
5. 把当前内容写入本地备份，生成差异和静态检查结果。

连接成功后复用现有桥接，不要在每次测试、刷新或迭代时重新请求连接码。连接丢失或 HTTP 服务重启时，先回退到内置浏览器和本地验证；若必须继续管理已安装脚本，只向用户报告需要一次新的服务生命周期授权，不自动重试或循环生成连接码。

当前官方仓库 README 说明的工具包括：

- `tampermonkey_get_connection_code`
- `tampermonkey_list`
- `tampermonkey_get`
- `tampermonkey_patch`
- `tampermonkey_put`
- `tampermonkey_delete`

DevTools MCP 的命令集合不由本服务器提供；必须以当前客户端的 `chrome-devtools --help`、页面枚举和实际调用结果为准。不要把 DevTools MCP 的页面调试能力写入 Tampermonkey MCP 的工具假设中。

README 标注 `put/delete` 需要 Tampermonkey Editors 1.0.6+ 与 Tampermonkey 5.6+。截至 2026-09-22 官方 Changelog 页面显示稳定版为 5.5.0，因此必须以实际连接能力和版本为准，不能默认 `put/delete` 可用。

## 写入授权和并发安全

用户明确授权后，且仅在即将执行写入前：

1. 再次展示目标脚本名称、namespace/path、版本、变更摘要和写入动作。
2. 使用 `lastModified` 或等价的乐观锁，防止覆盖用户刚刚的编辑。
3. `patch` 只提交已经在本地通过验证的完整内容或明确补丁结果。
4. `put` 前确认不会与现有 namespace/name 冲突。
5. `delete` 是破坏性操作，必须明确说明目标并在执行前再次确认；先保留备份。
6. 写入后重新 `get`，核对版本和内容，再用真实浏览器验证。

授权不包括自动安装扩展、删除其他脚本、修改浏览器设置或向第三方发送源码。

## Greasy Fork MCP 使用

`mcp-greasyfork-scripts` 适合公开脚本搜索和源码上下文，不等于 Tampermonkey 写入接口。第三方源码仍须核对许可证、恶意行为、权限和更新时间；不能把搜索结果当作官方推荐实现。

## 初始化受阻或服务不可用时

如果某项 MCP 因平台、网络或外部依赖无法安装/注册/连接，记录服务名和具体缺项；继续完成不依赖它的部分：

- 继续使用本地 userscript 文件、`validate_userscript.py` 和浏览器 DevTools。
- 让用户手动安装/更新时提供完整文件和验证命令。
- 不伪造“已写入”“已安装”或“已验证”的结果。

DevTools MCP 不可用时，仍可完成本地静态分析；但不能把离线检查说成真实页面验证。Tampermonkey MCP 未连接时，仍可通过本地文件和 DevTools MCP 调试；但不能把临时页面注入说成已写入 Tampermonkey。Greasy Fork MCP 不可用时可改用官方资料和人工网页检索，并继续核对来源与许可证。

版本、参数和可用命令必须在运行时重新核对。当前本机曾配置名为 `edge-devtools` 的服务器，仅作为本机示例，不应写死为所有环境都存在的服务器名称或连接方式。
