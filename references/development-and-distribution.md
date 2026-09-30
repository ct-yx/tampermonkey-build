# 开发、下载/导入与发布

开发、下载/导入、已安装同步、迁移和发布是不同的工作范围，但不需要人为制造流程障碍。请求明确包含多个范围时可以连续完成，只要保留源码、审查副本、安装环境和发布 staging 的边界，并在结果中说明实际做到了哪一步。

| 范围 | 主要输入 | 典型结果 | 默认不做的隐式动作 |
| --- | --- | --- | --- |
| 开发 | 本地源码或需求 | 修改后的本地源码和验证证据 | 不因开发请求自动发布或覆盖安装版本 |
| 下载/导入 | URL、仓库、版本或文件 | 审查副本和来源记录 | 不自动执行、安装或覆盖源码 |
| 已安装同步 | 已确认的脚本目标 | 备份、差异、回读和页面复测 | 不把同步结果直接当发布产物 |
| 迁移 | 本地 `.user.js` | MV3 扩展目录、ZIP、迁移报告 | 不自动安装或发布商店 |
| 发布 | 已验证的本地产物 | 可分发文件或外部发布结果 | 不把未验证下载内容直接推送 |

## 开发

本地文件通常是源码事实来源。当前真实开发与 userscript 运行环境为 Edge；Codex 内置浏览器只补充 DOM/快照/截图和可见布局观察。根据改动风险选择检查：

```text
读取项目和 metadata
→ 本地编辑
→ 适合当前改动的静态检查
→ Edge 页面控制扩展 + Tampermonkey 真实回归
→ Edge DevTools 取 Console/Network/Performance 证据
→ 需要时用内置浏览器补充 DOM/快照/截图观察
```

小型语法或 metadata 改动可能只需要验证器和 `node --check`；DOM/交互改动适合增加页面回归；CDN、图片、视频、信息流或预加载改动应使用同口径 Network/性能数据。不要为了完成固定清单而采集与问题无关的面板。

开发默认不写入 Tampermonkey。若用户明确希望直接测试已安装脚本，可以切换到已安装同步，或在 Edge 使用临时/隔离注入，并说明两者不是同一个运行环境。不要把自有扩展加载到 Codex 内置浏览器；该路径等待官方修复宿主崩溃后再评估。

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

## 迁移

对本地 `.user.js` 做源码级盘点：metadata、匹配范围、实际使用的 GM API、页面世界、网络请求、远程依赖、存储和生命周期。按实际需要生成 content script、service worker、页面世界辅助代码和权限。

纯 DOM 脚本可以直接迁移；使用 Tampermonkey 特有能力或存在无法等价转换的行为时，生成待修复骨架与 `MIGRATION_REPORT.md`，明确缺失行为和后续方案，不把骨架标为可用扩展。成功包仍应通过 manifest、脚本语法、ZIP 内容和目标浏览器加载检查。

## 发布

发布只处理已完成必要验证的本地产物。建议使用干净 staging：

```text
staging/
├── script.user.js
├── extension/
├── SHA256SUMS
└── RELEASE_NOTES.md
```

检查与当前发布目标相关的项目：版本号、metadata、权限、更新/下载地址、许可证和第三方归属、绝对路径、bridge 令牌、调试开关、临时 URL、密钥、用户数据和测试日志。ZIP 只包含计划分发的文件，并能复现校验摘要。

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
