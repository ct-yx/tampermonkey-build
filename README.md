# Tampermonkey Build

这是一个 Codex 技能，用于开发、调试、回归和发布浏览器 userscript，也支持将本地 Tampermonkey 脚本按需迁移为 Edge/Chrome Manifest V3 扩展。

## 工作模式

- 开发：本地编辑源码，以 Edge 作为真实 userscript/扩展开发与回归环境；Codex 内置浏览器用于 DOM、快照、截图和可见布局观察。
- 下载/导入：保存并审查外部脚本，不自动执行或安装。
- 发布：只处理已经验证的本地产物，生成可分发 userscript/扩展包。
- 已安装脚本同步：在用户明确授权后，通过自有 Userscript Bridge 的 CLI 读取、备份和写入。
- 迁移：分析本地 `.user.js`，按实际使用的能力生成最小 MV3 扩展。

开发与发布/下载可以分开，也可以在用户明确要求时连续完成；源码、审查副本、安装环境和发布产物保持边界即可。当前开发链路为 Edge 页面控制扩展 + Edge DevTools/CDP + 自有 Userscript Bridge CLI；官方 Tampermonkey MCP 与官方 Editors 不属于本技能流程。skill 内置的是自有 Userscript Bridge 扩展包，不包含外部 Edge 页面控制/GPT 扩展。Codex 内置浏览器只承担 DOM/快照/截图/可见布局观察，不加载自有桥接扩展；待 Codex 官方修复扩展加载崩溃后再重新评估。

## 安装

将本目录复制到 Codex 全局技能目录：

```text
~/.codex/skills/tampermonkey-build/
```

首次初始化时按技能文档检查当前任务需要的 Edge 页面控制扩展、Edge DevTools/CDT/CDP 权限、自有 bridge 和 Tampermonkey。技能不会自动安装官方 Tampermonkey MCP、官方 Editors、浏览器扩展、Tampermonkey 或用户脚本。

## 参考入口

- [SKILL.md](SKILL.md)：完整工作流和安全边界
- [开发与发布/下载分离](references/development-and-distribution.md)
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
