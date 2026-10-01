# Tampermonkey Build

这是一个 Codex 技能，专门用于开发、调试、测试和发布浏览器 userscript。默认以本地 userscript 源码为唯一开发基准；只有用户明确要求迁移时，才启用独立的 Edge/Chrome Manifest V3 扩展适配流程。

## 工作模式

- 开发：本地编辑 userscript 源码，检查 metadata 和语法，运行项目行为测试，再在 Edge + Tampermonkey 中实测；需要时使用 Codex 内置浏览器观察 DOM 和布局。
- 下载/导入：保存并审查外部脚本，不自动执行或安装。
- 发布：从已验证的源码生成 userscript；使用 Raw 地址更新的项目在仓库根目录保留构建生成的 `.user.js`。
- 已安装脚本同步：在用户明确授权后，通过自有 Userscript Bridge 的 CLI 读取、备份和写入。
- 可选扩展迁移：仅在用户明确要求时分析本地 `.user.js` 并生成所需的最小扩展适配。

默认流程是：本地 userscript 源码 → metadata 检查 → `node --check` → userscript 专用测试 → Edge + Tampermonkey 实测 → 必要时用内置浏览器观察 DOM/布局 → 从源码生成项目根目录发布脚本。扩展代码、安装、Manifest 或扩展权限都不是默认开发前提；扩展迁移与 userscript 开发、测试和发布分别记录。

官方 Tampermonkey MCP 和官方 Editors 不属于本技能的连接流程。技能内置的自有 Userscript Bridge 扩展包和源码仅用于用户要求的已安装脚本同步，不是本地 userscript 开发前提；外部 Edge 页面控制扩展也不随技能打包。

## 安装

将本目录复制到 Codex 全局技能目录：

```text
~/.codex/skills/tampermonkey-build/
```

首次初始化时按技能文档检查当前任务需要的 Edge 页面控制扩展、Edge DevTools/CDT/CDP 权限、自有 bridge 和 Tampermonkey。技能不会自动安装官方 Tampermonkey MCP、官方 Editors、浏览器扩展、Tampermonkey 或用户脚本。

## 参考入口

- [SKILL.md](SKILL.md)：完整工作流和安全边界
- [开发与发布/下载分离](references/development-and-distribution.md)
- [userscript 架构、页面作用域和生命周期](references/architecture-and-lifecycle.md)
- [Codex 内置浏览器](references/browser-runtime.md)
- [浏览器 DevTools MCP](references/devtools-mcp.md)
- [桥接与工具工作流](references/mcp-workflow.md)
- [自有 Userscript Bridge](references/editors-native-bridge.md)
- [Edge 桥接扩展包与源码](assets/edge-userscript-bridge/README.md)
- [userscript 迁移为扩展](references/userscript-to-extension.md)

## 本地验证器

```bash
python3 <SKILL_DIR>/scripts/validate_userscript.py path/to/script.user.js
node --check path/to/script.user.js
```

验证器只读分析文件，不写入 Tampermonkey 环境。示例脚本位于 `examples/`，不包含用户站点凭据或安装数据。
