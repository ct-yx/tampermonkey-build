# 自有 Userscript Bridge（本地开发版）

这里记录的是本地自维护的 userscript bridge 分支，不要求安装官方商店 Editors 插件，也不使用官方 Tampermonkey MCP。bridge 与 Tampermonkey 之间仍使用浏览器扩展 API；本地 Native Messaging host 提供受限的 CLI/loopback 转发能力。当前发布 skill 已内置 Edge 扩展包和对应源代码，入口见 [`../assets/edge-userscript-bridge/README.md`](../assets/edge-userscript-bridge/README.md)。

```text
Codex / 本地 CLI
        ↓
tm_bridge.py（浏览器启动的单实例 Native Host）
        ↑ Native Messaging
自有 Userscript Bridge 扩展
        ↓ chrome.runtime.connect
Tampermonkey
```

扩展代码基于 Editors 项目代码维护，增加 Native Messaging 自动桥接。使用前查看本地项目 README、许可证、改动和构建版本；不要把“基于上游代码”描述成依赖官方商店版扩展。若当前使用的分支尚未加入此桥接能力，不能把这份流程当成已经可用。

## 安装和初始化

安装自有扩展及 Native Host 是一次性的 Edge 配置操作，不属于每次脚本开发流程。只有用户明确要求连接/同步已安装脚本时才设置：

1. 使用 skill 内置的 `assets/edge-userscript-bridge/userscript-bridge-edge.zip`，或从 `assets/edge-userscript-bridge/source/` 构建扩展，并在目标 Edge profile 加载输出目录。
2. 从浏览器扩展详情页动态读取当前安装的扩展 ID；不要在技能、CLI 或 Native Host manifest 中写死示例 ID。
3. 用户明确授权后，仅为当前浏览器 profile 注册 Native Host：

   ```bash
   python3 <BRIDGE_ROOT>/bridge/tm_bridge.py install-host \
     --browser edge \
     --extension-id <当前实际扩展ID>
   ```

4. 重新加载自有扩展，并检查 host 状态：

   ```bash
   python3 <BRIDGE_ROOT>/bridge/tm_bridge.py status
   ```

不同浏览器/profile 分别有安装状态和扩展 ID。当前 skill 默认只支持 Edge；不要跨 profile 复用 ID。若用户明确要求迁移到 Chrome，再按当前 host 注册器源码和 `--help` 重新核对；本地实现平台边界以源码为准。

## CLI

按本地 `bridge/tm_bridge.py --help` 为准。当前实现提供：

```bash
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py status
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py list
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py get '<path>'
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py patch --path '<path>' '<源码文本>'
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py patch --path '<path>' --last-modified <时间戳> --value-file '<文件路径>'
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py put --value-file '<文件路径>'
python3 <BRIDGE_ROOT>/bridge/tm_bridge.py delete '<path>'
```

`status/list/get` 用于检查和读取。`patch/put/delete` 会改变已安装脚本，不是常规开发动作，必须先备份、生成差异并取得当前任务明确授权。`put` 创建脚本前还要确认不会覆盖或产生同名冲突；`delete` 要单独确认并保留备份。

本地 `mcp-stdio` 与 `print-mcp-config` 是自有 CLI 的可选转发适配，不是官方 Tampermonkey MCP。只有当前确实需要 MCP 客户端入口且用户要求时才配置；转发器不得启动第二个 Native Host。通常直接用 CLI 更简单。

## 单实例与故障处理

- Native Host 通过锁文件限制为单实例；看到 `native bridge is already running` 时先运行 `status` 并复用，不启动另一个。
- 扩展断开或浏览器关闭时，先检查扩展的 Native Bridge 状态和 host `status`；不循环重启、不生成连接码。
- host 确认已经退出且原因明确后，才启动一个新实例并重新检查状态；不得自动杀掉未知进程。
- Native Host 令牌和动态 loopback 端口保存在用户状态目录；不要输出或复制令牌，不要硬编码端口。
- bridge 不可用时，回到本地文件、Edge 手动/DevTools 验证或 Codex 内置浏览器 DOM 观察；不切换到官方 Editors/MCP 作为静默后备。

## 写入后的验证边界

bridge 回读只能证明 Tampermonkey 收到了对应脚本文本；它不证明目标页面已经重新加载、metadata 已匹配或页面行为正确。写入后仍需在目标浏览器刷新/导航，并按任务验证运行结果。报告分别记录本地文件、bridge 写入、回读、真实页面回归的状态。
