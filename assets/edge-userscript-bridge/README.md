# Edge Userscript Bridge 资产

这里同时保留两份交付物：

- `userscript-bridge-edge.zip`：当前构建好的 Chromium MV3 扩展包，可在 Edge 的“加载已解压的扩展”流程中使用其解压目录，或作为归档保存。
- `source/`：自有桥接扩展与 Native Messaging CLI 的完整源代码。

这里只内置 Tampermonkey userscript bridge；Edge 页面控制/GPT 扩展和 Edge DevTools MCP 属于用户的浏览器环境，不打包进本 skill。

## 设计定位

该扩展用于 Edge 中的真实 userscript 开发链路：

```text
Edge 页面控制扩展
        ↓
Edge + Tampermonkey
        ↓
自有 Userscript Bridge 扩展
        ↓ Native Messaging
tm_bridge.py / CLI / 可选 MCP 转发
```

Codex 内置浏览器暂不加载这个扩展。此前在内置浏览器加载 MV3 扩展会触发 Codex 宿主的 Chromium/V8 崩溃；内置浏览器仍可用于 DOM、快照、截图和页面布局观察，真实扩展与 Tampermonkey 联调在 Edge 完成。

## 构建与安装

从 `source/` 构建源码：

```bash
npm install
npm run build -- -v 1 -t chrome -h off -c off
```

构建生成的 `out/rel/` 是可加载的扩展目录。Native Messaging host 的注册、Edge 中实际扩展 ID 的读取和单实例规则见：

- [`source/bridge/README.md`](source/bridge/README.md)
- [`../../references/editors-native-bridge.md`](../../references/editors-native-bridge.md)

扩展 ID 只在当前 Edge 安装时动态读取，不能从 ZIP、文档或历史会话中复制固定值。

## 隐私与构建说明

- skill 资产不包含用户 profile、Cookie、令牌、日志或本机绝对路径。
- 上游仓库中的打包测试私钥 `build_sys/tme_test.pem` 已排除；skill 只保留公开 manifest 中的公钥和无私钥的源代码。
- 重新打包时不应把私钥加入 skill 或公开仓库；使用 Edge 加载 `out/rel/`，或在不签名的情况下生成普通 ZIP。
- 该包未自动安装到任何浏览器，也未写入 Tampermonkey。
