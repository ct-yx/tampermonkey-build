# 开发、下载/导入与发布

开发、下载/导入、已安装同步、迁移和发布是不同的工作范围，但不需要人为制造流程障碍。请求明确包含多个范围时可以连续完成，只要保留源码、审查副本、安装环境和发布 staging 的边界，并在结果中说明实际做到了哪一步。

| 范围 | 主要输入 | 典型结果 | 默认不做的隐式动作 |
| --- | --- | --- | --- |
| 开发 | 本地源码或需求 | 修改后的本地源码和验证证据 | 不因开发请求自动发布或覆盖安装版本 |
| 下载/导入 | URL、仓库、版本或文件 | 审查副本和来源记录 | 不自动执行、安装或覆盖源码 |
| 已安装同步 | 已确认的脚本目标 | 备份、差异、回读和页面复测 | 不把同步结果直接当发布产物 |
| 迁移 | 本地 `.user.js` | MV3 扩展目录、ZIP、迁移报告 | 不自动安装或发布商店 |
| 发布 | 已验证的 userscript 源码 | 根目录 `.user.js` 或其他明确的 userscript 发布文件 | 不把未验证下载内容直接推送 |

## 开发

本地 userscript 源码是唯一开发基准。默认流程为：

```text
本地 userscript 源码
→ metadata 检查
→ node --check
→ userscript 专用测试
→ Edge + Tampermonkey 实测
→ 必要时用 Codex 内置浏览器观察 DOM 和布局
→ 从源码生成项目根目录发布 .user.js
```

测试和页面观察深度根据改动选择，但面向用户的行为改动应使用 Edge + Tampermonkey 做真实脚本验证。DevTools 的 Console/Network/Performance 和 Codex 内置浏览器只在问题需要时补充证据；页面操作由当前可用方式完成，不要求预装某个控制扩展或 MCP。

单文件脚本可直接以项目根目录的 `.user.js` 作为源码和发布文件。多模块项目从源码构建根目录发布 `.user.js`，不要手动改生成物。需要 Raw 地址更新的脚本必须保持有效的 `@updateURL` 与 `@downloadURL`。开发过程中不默认同步/覆盖用户已安装版本；若用户明确要求测试已安装脚本，按“已安装脚本同步”单独备份、展示差异并授权写入。

## 下载/导入

外部脚本先保存到单独的审查位置，不覆盖开发目录：

```text
source_url
source_type
version_or_commit
retrieved_at
license
sha256
```

根据风险查看 metadata、`@match`、`@grant`、`@connect`、`@require`、更新地址、动态代码、网络请求、存储和文件操作。第三方源码只作为参考；许可证和行为不清楚时不要直接复制、执行或安装。

## 已安装脚本同步

该范围才需要自有 Userscript Bridge：

```text
确认目标脚本
→ list/get 读取内容和修改时间
→ 本地备份并生成差异
→ 在即将写入时确认授权
→ patch/put/delete
→ 回读并在目标页面复测
```

连接、动态 ID 和单实例问题见 [mcp-workflow.md](mcp-workflow.md) 与 [editors-native-bridge.md](editors-native-bridge.md)。自有 bridge 不可用时交付本地差异即可，不要声称已同步。

## 可选扩展迁移

只有用户明确要求把 userscript 迁移为 Edge/Chrome 扩展时，才执行 [userscript-to-extension.md](userscript-to-extension.md)。先完成 userscript 功能和 Edge + Tampermonkey 验证，再分析能力差异并按需生成扩展适配。扩展不另存一套业务逻辑；Manifest、权限、MAIN/ISOLATED world、Bridge、Service Worker 和下载能力另行检查。

扩展构建或加载结果与 userscript 实测分开报告；扩展构建通过不代表 Edge + Tampermonkey userscript 实测通过。不要自动安装扩展或修改 Tampermonkey。

## 发布

userscript 发布只处理已完成必要验证的本地产物。对需要 Raw 更新的项目，编译后的 `.user.js` 保留在仓库根目录。构建产物必须从源码生成，不能手动编辑。建议 staging 只放本次 userscript 发布所需文件：

```text
staging/
├── script.user.js
├── SHA256SUMS
└── RELEASE_NOTES.md
```

发布前运行 metadata 检查、`node --check`、项目测试和 `git diff --check`。检查版本号、`@match`/`@grant`/`@connect`、有效的 `@updateURL`/`@downloadURL`、许可证和第三方归属、绝对路径、bridge 令牌、调试开关、临时 URL、密钥、用户数据和测试日志。ZIP 只包含计划分发的 userscript 文件，并能复现校验摘要。

推送 GitHub、Greasy Fork 或其他外部平台属于外部状态变更，需要用户明确提出目标和上传内容后再执行。执行后报告远端、分支、提交和发布状态；没有执行就不要暗示已发布。

## 状态记录

按需要记录，不必每次填写完整模板：

```text
scope: development | download-import | installed-sync | migration | release
source_of_truth: local-file | reviewed-download | installed-backup
written_to_tampermonkey: yes | no
published_externally: yes | no
browser_evidence: edge-control | edge-devtools-mcp | real-devtools | built-in-dom | none
known_limits:
```

重点是避免把“本地检查”“临时注入”“已安装”“可下载”和“已发布”混为一谈，而不是强制所有任务执行相同数量的步骤。
