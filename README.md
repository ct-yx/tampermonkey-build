# Tampermonkey Build

这是一个 Codex 技能，用于开发、调试、回归和发布浏览器 userscript，也支持将本地 Tampermonkey 脚本按需迁移为 Edge/Chrome Manifest V3 扩展。

## 工作模式

- 开发：本地编辑源码，优先使用 Codex 内置浏览器自动调试和回归。
- 下载/导入：保存并审查外部脚本，不自动执行或安装。
- 发布：只处理已经验证的本地产物，生成可分发 userscript/扩展包。
- 已安装脚本同步：在用户明确授权后，通过现有 Tampermonkey 桥接读取、备份和写入。
- 迁移：分析本地 `.user.js`，按实际使用的能力生成最小 MV3 扩展。

开发与发布/下载流程默认分离。Tampermonkey MCP 不是开发或发布的硬性依赖；只有管理已安装脚本时才需要它。浏览器 DevTools MCP 和 Codex 内置浏览器分别用于真实页面取证和自主回归，具体能力以运行时为准。

## 安装

将本目录复制到 Codex 全局技能目录：

```text
~/.codex/skills/tampermonkey-build/
```

首次初始化时按技能文档检查可选 MCP、CDT/CDP 权限和目标浏览器条件。技能不会自动安装浏览器扩展、Tampermonkey、Editors 或用户脚本。

## 参考入口

- [SKILL.md](SKILL.md)：完整工作流和安全边界
- [开发与发布/下载分离](references/development-and-distribution.md)
- [Codex 内置浏览器](references/browser-runtime.md)
- [浏览器 DevTools MCP](references/devtools-mcp.md)
- [Tampermonkey MCP](references/mcp-workflow.md)
- [userscript 迁移为扩展](references/userscript-to-extension.md)

## 本地验证器

```bash
python3 <SKILL_DIR>/scripts/validate_userscript.py path/to/script.user.js
node --check path/to/script.user.js
```

验证器只读分析文件，不写入 Tampermonkey 环境。示例脚本位于 `examples/`，不包含用户站点凭据或安装数据。
