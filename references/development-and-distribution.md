# 开发、下载/导入与发布分离

本技能把 userscript 的生命周期拆成独立模式。任务开始时先选模式；除非用户明确切换，不在一次流程中自动跨模式。

| 模式 | 输入 | 主要动作 | 默认结果 | 禁止的隐式动作 |
| --- | --- | --- | --- | --- |
| 开发 | 本地源码或用户明确提供的需求 | 编辑、静态检查、内置浏览器调试、回归 | 本地源码和证据 | 发布、下载第三方脚本、写入已安装脚本 |
| 下载/导入 | URL、仓库、版本或本地导入文件 | 保存来源、核对许可证、检查 metadata/权限/语法 | 本地审查副本和报告 | 自动执行、安装、覆盖开发源码 |
| 发布 | 已完成验证的本地产物 | 版本检查、打包、生成校验摘要和发布说明 | 可分发文件或待用户授权的发布变更 | 修改源码、把未验证文件直接推送 |
| 已安装脚本同步 | 已确认的 Tampermonkey 脚本目标 | 读取、备份、生成差异、经授权写入、回读验证 | 安装环境同步结果 | 把同步结果当作发布或开发源码 |
| 迁移 | 本地 `.user.js` | 源码级分析并生成 MV3 扩展 | 扩展目录、ZIP、迁移报告 | 自动安装扩展或发布商店 |

## 开发模式

开发模式的唯一事实来源是本地工作文件。推荐流程：

```text
确认站点和运行上下文
→ 读取 metadata 与现有版本
→ 编辑本地源码
→ metadata/权限/语法检查
→ Codex 内置浏览器复现和回归
→ 按需用 DevTools MCP 取得 Console/Network/Performance 证据
→ 保存差异、测试记录和已知限制
```

开发模式默认不需要 Tampermonkey MCP。需要已安装脚本行为时，可以使用隔离页面或临时注入验证，但必须标明临时注入不会改变 Tampermonkey 安装版本。只有用户明确授权同步时，才切换到“已安装脚本同步”模式。

完成标准至少包括：

- metadata、权限和 Node 语法检查通过；
- 首次加载、刷新、SPA 导航、滚动、悬停和重复注入完成回归；
- 记录脚本错误与页面错误的区分依据；
- 性能修改有同口径的修改前/后数据；
- 本地源码、测试产物和发布产物边界清楚。

## 下载/导入模式

下载/导入模式处理外部来源，不把来源当作可信代码。对每个来源保存以下信息：

```text
source_url
source_type          # 官方仓库、发布页、Greasy Fork 或本地文件
version_or_commit
retrieved_at
license
sha256
```

审查顺序：

1. 将文件保存到单独的本地审查目录，不覆盖开发目录或已安装脚本。
2. 阅读完整 metadata，检查 `@match`、`@grant`、`@connect`、`@require`、更新地址和许可证。
3. 用验证器检查权限/API 一致性，并运行 `node --check` 或构建检查。
4. 检查远程依赖、动态代码、网络请求、存储和写文件行为；第三方代码只在许可证允许且行为可审计时借鉴。
5. 生成审查报告后，等待用户明确决定是否进入开发、安装或发布流程。

下载/导入模式不自动运行脚本、不自动拖入 Tampermonkey、不自动加载扩展，也不因用户提供了 URL 就获得外部写入授权。

## 发布模式

发布模式只接受已经在开发模式中验证过的本地产物。发布前创建干净 staging 目录，只复制需要分发的文件：

```text
staging/
├── script.user.js          # userscript 单文件产物
├── extension/              # 如适用，MV3 扩展目录
├── SHA256SUMS
└── RELEASE_NOTES.md
```

发布检查：

- 版本号递增且与源码/构建配置一致；
- 只有一个有效 metadata block；
- `@updateURL`、`@downloadURL`、主页和支持地址指向稳定、可审计的位置；
- `@match`、`@grant`、`@connect` 只保留实际需要的最小集合；
- 无本机绝对路径、连接码、调试开关、临时 URL、密钥、用户数据或测试日志；
- 第三方代码、资源和许可证归属完整；
- userscript 可通过静态检查，扩展 `manifest.json` 和脚本可解析；
- ZIP 只包含计划发布的文件，并能从 ZIP 中复现同一校验摘要。

GitHub、Greasy Fork 或其他平台的推送属于外部状态变更。只有用户明确要求发布，并确认目标仓库/平台、可见性和要上传的 staging 内容后才执行。技能不因完成开发自动创建仓库或推送。

## 已安装脚本同步模式

这个模式才使用 Tampermonkey MCP/Editors：

```text
确认目标脚本
→ 读取当前内容、版本和最后修改时间
→ 保存本地备份
→ 生成并审查差异
→ 用户在即将写入前明确授权
→ 使用乐观锁 patch/put
→ 回读并在真实页面复测
```

连接、备份、授权和回滚规则以 [mcp-workflow.md](mcp-workflow.md) 为准。同步不等于发布；如果用户还要求发布，必须明确切换到发布模式并重新执行发布检查。

## 模式切换记录

在最终报告中明确写出：

```text
mode: development | download-import | release | installed-sync | migration
source_of_truth: local-file | reviewed-download | installed-backup
written_to_tampermonkey: yes | no
published_externally: yes | no
browser_evidence: built-in | devtools-mcp | real-devtools | none
```

这样可以避免把“本地验证”“已安装”“可下载”和“已发布”混成同一个状态。
