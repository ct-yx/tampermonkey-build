# 桥接与工具工作流（不使用官方 Tampermonkey MCP/Editors）

文件名保留 `mcp-workflow.md` 以兼容旧链接，但本技能已经放弃官方 Tampermonkey MCP 和官方 Editors 连接流程：不安装、不注册、不调用、不索要连接码，也不把它们作为初始化或开发前置条件。已安装的官方组件不会因为使用本技能而被自动卸载；本文件只规定后续工作流。

## 工具分工

| 工具 | 用途 | 默认状态 |
| --- | --- | --- |
| Edge 页面操作能力 | 在真实 Edge 中导航、交互、刷新和回归 | 按需使用；不要求为 userscript 开发安装特定扩展 |
| Edge DevTools MCP | 真实 Edge 的 DOM、Console、Network、Performance、Memory 取证 | 按问题启用 |
| Codex 内置浏览器 | DOM、快照、截图和可见布局观察 | 补充使用，不加载自有扩展 |
| Greasy Fork MCP 或网页检索 | 公开脚本和资料发现 | 按需启用 |
| 自有 Userscript Bridge 扩展 + 本地 host/CLI | 读取、备份、差异比较和授权写入已安装脚本 | 仅已安装同步需要 |

官方 Tampermonkey MCP 和官方 Editors 不在上表中。它们不能因为已经安装或曾经连接过，就改变本技能的工具选择。

## 初始化和降级

首次使用或切换到新环境时，只检查当前任务需要的工具：

1. 开发任务先检查本地源码、`validate_userscript.py`、Node 和 Edge 中的 Tampermonkey。只有需要代理自动操作页面时，才检查现有页面控制工具；缺少该工具不阻止本地开发或通过浏览器 UI 实测。
2. 需要真实 Edge 页面证据时，再检查 DevTools MCP、CDT/CDP 权限和目标页面；内置浏览器可同时用于 DOM/截图观察。
3. 需要公开脚本检索时，再启用 Greasy Fork MCP 或使用网页检索。
4. 需要管理已安装脚本时，再检查自有 bridge 扩展、Native Messaging host 和 CLI 状态。

MCP 文件和配置若确有需要，放在 Codex 全局目录 `~/.codex/mcp/`，不能写进项目目录。已存在的 DevTools/Greasy Fork 服务只复用，不重复注册。官方 Tampermonkey MCP 不得安装或注册；官方 Editors 不得作为本技能的安装目标。

初始化前记录浏览器侧条件，但不要把它们混成同一权限：

- Edge + Tampermonkey 的 userscript 实测可通过浏览器 UI 完成。代理自动操作页面时再使用当前可用的页面控制工具；只有需要 DevTools MCP 深层证据时才需要用户允许 CDT/CDP 远程调试。内置浏览器不等于用户 Edge。
- 真实 userscript 验证需要目标 Edge profile 已安装并启用 Tampermonkey；内置浏览器不会自动继承用户 Edge 的扩展、Cookie 或脚本库，只用于页面结构和可见结果观察。
- 自有 bridge 需要对应浏览器中已经安装用户自己的扩展版本，并且只为该扩展 ID 注册 Native Messaging host。
- 无法满足任一条件时，继续完成不依赖它的本地开发、Edge 手动验证或内置浏览器 DOM/可见观察，并在结果中标明缺失证据。

不能把“已注册 DevTools MCP”“已打开 F12”“bridge host 已启动”写成“脚本已经写入”或“真实页面已经验证”。

## 自有 Userscript Bridge

自有 bridge 由浏览器扩展、本地 Native Messaging host 和 CLI 组成。当前实现的典型入口如下，路径和参数以 bridge 项目自身的 `--help` 与实际安装结果为准：

```bash
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py status
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py list
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py get '<脚本 path>'
```

如果需要首次注册 host，由用户明确授权后执行一次；扩展 ID 必须从当前浏览器的已安装扩展详情或运行时 URL 动态读取，不能写进技能或源码：

```bash
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py install-host \
  --browser edge \
  --extension-id <当前实际扩展ID>
```

重新加载自有扩展后，用 `status` 验证。Native Messaging host 的状态文件、随机令牌和 loopback 端口由 bridge 管理；代理不应复制令牌、猜测端口或把某个浏览器的扩展 ID 复用到另一个浏览器。

### 单实例规则

- 同一浏览器 profile 最多运行一个自有 Native host；发现已有实例时复用，不再启动第二个。
- 自有 bridge 的 `mcp-stdio` 若启用，只能读取已有 host 的状态并转发请求，不得自行启动第二个 host。
- 刷新页面、编辑本地文件、重复测试和普通请求超时都不需要重启 host。
- host 真正退出后，先运行 `status` 并检查退出原因；不自动循环重启。可安全恢复时只启动一个新实例，并重新验证扩展 ID、状态和目标脚本。
- 不自动杀掉未知进程。清理重复实例属于独立操作，必须先确认 PID、路径和影响。

### 已安装脚本同步

只有用户明确要求同步已安装脚本时才执行：

```text
bridge status
→ bridge list
→ 精确选择 path
→ bridge get
→ 本地备份和静态检查
→ 展示差异并确认写入授权
→ bridge patch/put/delete
→ bridge get 回读
→ 回到真实页面复测
```

`patch`、`put` 和 `delete` 不是开发默认动作。写入前保留原文、时间戳和目标信息；尽可能使用 `lastModified` 或 bridge 提供的等价版本检查，防止覆盖用户刚刚的修改。`delete` 需要单独确认并保留可恢复备份。

自有 bridge 的可选 MCP 适配器可以把 `list/get/patch/put/delete` 暴露给 MCP 客户端，但它仍然只是本地 bridge 的转发层，不是官方 Tampermonkey MCP，也不允许省略备份、差异、授权和回读。

## 开发和浏览器验证

userscript 默认开发与验证路径：

```text
本地 userscript 源码
→ metadata 检查
→ node --check
→ userscript 专用测试
→ Edge + Tampermonkey 实测
→ 必要时用 Codex 内置浏览器观察 DOM 和布局
→ 从源码生成项目根目录发布 .user.js
```

DevTools MCP、某个 Edge 页面控制扩展和自有 Userscript Bridge 都不是编辑 userscript 的前置条件。真实页面行为在 Edge + Tampermonkey 验证；具体交互可用当前可用的浏览器 UI 或自动化能力，DevTools 证据按问题需要采集。Codex 内置浏览器只补充 DOM、快照、截图和布局观察，不替代真实 userscript 运行。用户明确要求扩展迁移时，才进入独立迁移参考流程；此前在内置浏览器加载自有桥接扩展曾触发宿主崩溃，因此不把该加载方式作为 userscript 开发方案。

DevTools MCP 和自有 bridge 不共享权限、页面 ID、Cookie、扩展状态或脚本状态：DevTools MCP 能观察页面，不代表能写 userscript；自有 bridge 能写脚本，也不代表页面已重新加载或行为已验证。

## 调试证据入口

页面问题按需读取：

- Codex 内置浏览器操作：`browser-runtime.md`
- Chromium DevTools MCP：`devtools-mcp.md`
- 通用 DOM/Console/Network/Performance 顺序：`browser-debugging.md`

DevTools MCP 的版本、参数和可用工具必须以当前运行时的 `--version`、`--help`、`list_pages` 和无副作用 `evaluate_script` 为准。不得把自有 bridge 的 CLI 命令冒充 DevTools 命令，也不得把 DevTools 取证冒充 userscript 写入。

## 失败处理和交付记录

按实际原因区分：

- 本地脚本语法或 metadata 问题；
- Edge 页面控制扩展、Edge 页面或交互问题；
- Codex 内置浏览器仅用于 DOM/可见结果观察，扩展加载暂不作为验证路径；
- DevTools MCP/CDP/页面 ID 问题；
- 自有 bridge 扩展、Native Messaging host 或目标脚本问题；
- 站点、网络、广告拦截或代理问题。

不要记录 Cookie、token、密码或不必要的完整请求体。最终报告至少区分：

```text
local_file_checked: yes | no
built_in_browser_verified: yes | no
devtools_evidence: yes | no
bridge_status: available | unavailable | not_needed
written_to_tampermonkey: yes | no
read_back_after_write: yes | no
known_limits:
```
