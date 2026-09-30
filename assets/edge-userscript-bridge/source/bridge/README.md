# Tampermonkey Editors 自动桥接

这是对官方 `Tampermonkey Editors` 的本地开发版扩展。它保留原有的连接码/WebSocket流程，同时增加 Native Messaging 自动桥接：扩展启动后连接本地 host，host 再提供带随机令牌的回环 HTTP 接口和 MCP stdio 代理。

## 安装一次

1. 构建扩展：

   ```bash
   npm install
   npm run build -- -v 1 -t chrome -h off -c off
   ```

2. 在 Chrome/Edge 的扩展管理页打开开发者模式，加载 `out/rel`。从扩展详情复制实际的 32 位扩展 ID。
3. 按实际浏览器注册 Native Host（扩展 ID 只在这一步传入，不写进源码）：

   ```bash
   python3 bridge/tm_bridge.py install-host \
     --browser edge \
     --extension-id <实际扩展ID>
   ```

4. 重新加载扩展。扩展后台会自动启动 host；不需要打开弹窗，也不需要输入连接码。

## CLI / MCP

```bash
python3 bridge/tm_bridge.py status
python3 bridge/tm_bridge.py list
python3 bridge/tm_bridge.py get '<脚本path>'
python3 bridge/tm_bridge.py mcp-stdio
```

`mcp-stdio` 是给 MCP 客户端注册的本地命令。它本身不启动第二个 Native Host，而是读取 host 的单实例状态文件并转发 JSON-RPC。可用工具为 `tampermonkey_list`、`tampermonkey_get`、`tampermonkey_patch`、`tampermonkey_put` 和 `tampermonkey_delete`。

状态文件位于 macOS 的 `~/Library/Application Support/Tampermonkey Bridge/state.json`，包含随机令牌并设置为仅当前用户可读。HTTP 只绑定 `127.0.0.1`，脚本读写仍必须经过扩展与 Tampermonkey 的通信链路。

## 当前边界

- 这是本地开发版，不自动覆盖商店版扩展，也不自动修改已有 userscript。
- Native Messaging Host 注册仍是一次性安装步骤；浏览器安全边界不能被完全绕过。
- 扩展 ID 必须从当前浏览器实际安装结果读取，不能使用固定 ID。
- 目标为 Chrome/Edge；Firefox 的 host 注册方式暂未纳入本原型。
- Native Host 与 HTTP/MCP 已实现单实例；如果发现旧 host 正在运行，新的 host 会拒绝启动。
