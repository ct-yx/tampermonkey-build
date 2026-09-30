# 浏览器 DevTools MCP 调试手册

本文面向需要调试 userscript 真实页面行为的任务，当前默认目标是 Edge；同时覆盖 Chromium 系列浏览器与 chrome-devtools-mcp。命令以 2026-09-22 本机核对的 chrome-devtools-mcp 1.9.0 为基线；版本、参数和工具集合会变化，开始任务时仍要重新执行 --version 和 --help。Edge 的实际 MCP 注册名、连接参数和页面控制扩展以当前环境为准，不写死为某个本地配置名。

## 1. DevTools MCP 与 userscript bridge 的职责边界

| 目标 | 自有 Userscript Bridge | 浏览器 DevTools MCP |
| --- | --- | --- |
| 读取、备份和写入 userscript | 负责 | 不负责 |
| 检查脚本 metadata 和版本 | 读取脚本后负责 | 只能从页面侧观察结果 |
| 页面 DOM、可访问性树、截图 | 不负责 | 负责 |
| Console、Network、Performance | 不负责 | 负责 |
| CPU/网络模拟 | 不负责 | 负责部分模拟 |
| JS 断点、单步、条件断点 | 不负责 | 当前没有直接通用命令 |
| Coverage、Layers、完整 Service Worker 面板 | 不负责 | 当前没有完整面板控制 |

两者不共享连接、权限或状态。DevTools MCP 能看到页面，并不代表它能修改已安装脚本；自有 bridge 能写脚本，也不代表写入后的页面已真实验证。官方 Tampermonkey MCP 和官方 Editors 不属于本调试流程。

## 2. 连接前能力核对

先确认客户端已经注册 DevTools MCP。不要因为后台进程存在就认为目标页面已经可控。

    chrome-devtools --version
    chrome-devtools --help
    chrome-devtools list_pages --output-format json

正常的最小证据链是：

    list_pages
    → 选择目标页面
    → 校验 URL
    → 无副作用 evaluate_script
    → take_snapshot
    → Console / Network / Performance 调试

chrome-devtools CLI 通常会在第一次实际调用时启动后台服务；不要在每次命令前重复执行 start、status 或 stop。只有需要改变启动参数、启用 Memory 或恢复异常服务时，才使用服务管理命令。

### 2.1 CDT/CDP 权限和浏览器扩展前置条件

这里的“CDT 权限”按 Chromium DevTools/CDP 远程调试权限记录，不是 Tampermonkey 权限，也不是一个固定的浏览器扩展。连接真实 Chrome/Edge 前，用户需要在目标浏览器和目标 profile 中允许远程调试：

- Chrome 常见入口：`chrome://inspect/#remote-debugging`。
- Edge 常见入口：`edge://inspect/#remote-debugging`。
- 企业策略、浏览器版本和实际页面可能不同；如果浏览器显示安全确认或策略限制，必须由用户确认或管理员放行，代理不得绕过。

如果任务要验证 userscript，用户还需要安装并启用目标 profile 中的 Tampermonkey；若要读取/写入已安装脚本，再按需使用自有 Userscript Bridge。扩展 ID 必须动态发现，不能把一个浏览器的安装状态推断为另一个浏览器已安装。

chrome-devtools-mcp 1.9.0 还提供可选的扩展工具，但必须显式启用并受连接模式限制：

```bash
chrome-devtools start --categoryExtensions=true
chrome-devtools list_extensions
```

`list_extensions` 能列出当前可见扩展；`install_extension <path>` 针对本地扩展目录，不能替代从商店安装 Tampermonkey，也不应在没有用户授权时自动安装第三方扩展。当前帮助还注明扩展能力主要依赖 pipe 连接，在 `--autoConnect`、`--browserUrl` 或 `--wsEndpoint` 场景不能默认可用。

## 3. Edge/Chrome 连接方式

### 3.1 连接已运行的浏览器

用户已经打开目标浏览器和 F12 时，优先连接已有可调试实例：

    chrome-devtools start --browserUrl http://127.0.0.1:9222

也可以使用 WebSocket endpoint：

    chrome-devtools start --wsEndpoint ws://127.0.0.1:9222/devtools/browser/<browser-id>

端口、WebSocket 地址和 Origin 必须来自当前浏览器实例。不要猜测端口，也不要把某次会话的 page id 当成永久 ID。

连接策略是单个 DevTools MCP daemon 复用：先调用 `list_pages`，不要每个页面或每次刷新都 `start` 一个新 daemon。需要改变启动参数时才重启，并在重启后重新枚举页面、校验 URL 和执行无副作用 `evaluate_script`。

### 3.2 自动连接现有 Chromium 会话

较新的 Chromium 支持自动连接发现本地浏览器，但需要浏览器侧开启远程调试：

    chrome-devtools start --autoConnect --channel stable

当前用户数据目录、浏览器通道和远程调试开关必须匹配。Edge 的实际路径和策略可能与 Chrome 不同，不能仅因为二者都使用 Chromium 就直接复用配置。

### 3.3 启动隔离浏览器

不需要用户登录态时，使用隔离 profile 做可重复实验：

    chrome-devtools start --isolated --headless=false

需要保留调试数据时，显式指定一个可写的临时用户目录。不要把用户正在使用的 profile 当作临时目录，也不要为了排错删除整个浏览器 profile。

## 4. 页面选择和无副作用检查

列出页面后，选择与目标 URL、frame 类型和窗口对应的 page id：

    chrome-devtools list_pages --output-format json
    chrome-devtools select_page <PAGE_ID> --bringToFront true

先检查 URL 和页面状态：

    chrome-devtools evaluate_script \
      '() => ({ href: location.href, ready: document.readyState, title: document.title })' \
      --pageId <PAGE_ID> \
      --waitForStableDom false \
      --output-format json

只读采样应关闭 waitForStableDom，避免调试工具等待页面稳定而改变时序。返回值必须是可 JSON 序列化的数据；不要把页面节点、循环引用对象或敏感 Cookie 直接返回。

## 5. DOM、快照和页面脚本

获取可访问性快照并使用最新的 UID：

    chrome-devtools take_snapshot <PAGE_ID>
    chrome-devtools take_snapshot <PAGE_ID> --verbose true --filePath /tmp/page-snapshot.txt

针对 UID 读取页面信息：

    chrome-devtools evaluate_script \
      '(element) => ({ text: element.innerText, tag: element.tagName })' \
      --pageId <PAGE_ID> \
      --args <UID> \
      --waitForStableDom false

基本原则：

- 快照用于定位可访问性节点和 UID，不等于完整 DOM。
- evaluate_script 用于可复现的页面侧采样，不等于 userscript 沙箱中的 GM API。
- 截图只证明可见结果，不能替代 DOM、Network 或 Performance 证据。
- 每次页面导航后重新获取快照；旧 UID 可能失效。
- 真实站点调试前先记录 URL、登录状态、窗口尺寸和脚本版本。

## 6. Console 调试与错误归因

读取最近一次导航后的 Console：

    chrome-devtools list_console_messages <PAGE_ID> \
      --types error --types warning \
      --includeStackTraces true \
      --pageSize 100

读取保留的最近导航日志：

    chrome-devtools list_console_messages <PAGE_ID> \
      --includePreservedMessages true \
      --pageSize 100

读取单条消息：

    chrome-devtools get_console_message <PAGE_ID> <MESSAGE_ID>

归因时分开记录：

1. userscript 文件名、版本和行号。
2. 站点 bundle 或页面脚本异常。
3. ERR_BLOCKED_BY_CLIENT 等广告拦截、隐私扩展或浏览器扩展异常。
4. Network 请求状态、响应体和重定向。
5. DOM mutation、几何变化和最终视觉表现。

调试日志应使用唯一前缀，例如 `[Userscript][debug]`，并在生产脚本中由设置开关控制或移除。不要因为 Console 有错误就直接归因给 userscript。

## 7. Network 调试

列出最近请求：

    chrome-devtools list_network_requests <PAGE_ID> \
      --pageSize 100 \
      --pageIdx 0

只看特定资源类型：

    chrome-devtools list_network_requests <PAGE_ID> \
      --resourceTypes Fetch \
      --resourceTypes Image \
      --includePreservedRequests true

查看单个请求及响应：

    chrome-devtools get_network_request <PAGE_ID> \
      --reqid <REQUEST_ID> \
      --requestFilePath /tmp/request.network-request \
      --responseFilePath /tmp/response.network-response

每次性能比较至少记录：

- URL、请求类型和发起者。
- 状态码、重定向链和失败原因。
- DNS/TCP/TLS/TTFB/下载耗时（工具或页面侧能提供什么就记录什么）。
- 请求优先级、缓存命中/未命中和响应大小。
- 图片、视频、信息流 API 的请求数量和失败率。
- 脚本改写前后的原始 URL、最终 URL 和回退结果。

navigate_page --ignoreCache true 只表示这次 reload 忽略缓存，不等价于 DevTools Network 面板中的 Disable cache 持续开关。需要持续禁用缓存时使用真实 DevTools 面板或具备对应 CDP 能力的工具，并在报告中写清楚实验条件。

## 8. Performance、CPU 和网络条件

自动 reload 并记录一次导航 trace：

    chrome-devtools performance_start_trace <PAGE_ID> \
      --reload true \
      --autoStop true \
      --filePath /tmp/userscript-navigation.json.gz

手动执行刷新、滚动或悬停后再停止：

    chrome-devtools performance_start_trace <PAGE_ID> \
      --reload false \
      --autoStop false
    # 在这里执行固定的用户操作
    chrome-devtools performance_stop_trace <PAGE_ID> \
      --filePath /tmp/userscript-interaction.json.gz

查看具体 Performance Insight：

    chrome-devtools performance_analyze_insight <PAGE_ID> <INSIGHT_SET_ID> <INSIGHT_NAME>

模拟 CPU 和网络：

    chrome-devtools emulate <PAGE_ID> --cpuThrottlingRate 4
    chrome-devtools emulate <PAGE_ID> --networkConditions 'Fast 3G'
    # 结束模拟
    chrome-devtools emulate <PAGE_ID> --cpuThrottlingRate 1
    chrome-devtools emulate <PAGE_ID>

性能比较必须固定浏览器、窗口尺寸、登录状态、缓存状态、网络条件和操作步骤；至少比较中位数，而不是只比较一次结果。userscript 优化重点观察 LCP、INP、CLS、长任务、重复请求、图片解码、信息流后续批次和布局几何变化。

## 9. Memory 和 Heap snapshot

Memory 工具需要在 MCP 服务启动时启用：

    chrome-devtools start --memoryDebugging=true

捕获快照：

    chrome-devtools take_heapsnapshot <PAGE_ID> /tmp/before.heapsnapshot

交互一段时间后再次捕获：

    chrome-devtools take_heapsnapshot <PAGE_ID> /tmp/after.heapsnapshot
    chrome-devtools compare_heapsnapshots /tmp/before.heapsnapshot /tmp/after.heapsnapshot

进一步分析：

    chrome-devtools get_heapsnapshot_summary /tmp/after.heapsnapshot
    chrome-devtools get_heapsnapshot_class_nodes /tmp/after.heapsnapshot Array
    chrome-devtools get_heapsnapshot_object_details /tmp/after.heapsnapshot <NODE_ID>
    chrome-devtools get_heapsnapshot_retainers /tmp/after.heapsnapshot <NODE_ID>
    chrome-devtools get_heapsnapshot_retaining_paths /tmp/after.heapsnapshot <NODE_ID>
    chrome-devtools close_heapsnapshot /tmp/after.heapsnapshot

Heap snapshot 可能包含页面中的敏感文本和对象引用。只保存到受控临时目录，报告中不要复制 Cookie、token 或用户内容。快照差异只能说明对象保留变化，不能单独证明 userscript 是唯一原因。

## 10. Lighthouse

执行导航审计：

    chrome-devtools lighthouse_audit <PAGE_ID> \
      --mode navigation \
      --device desktop \
      --outputDirPath /tmp/lighthouse-report

对当前页面状态审计：

    chrome-devtools lighthouse_audit <PAGE_ID> \
      --mode snapshot \
      --device desktop

Lighthouse 的结果用于辅助观察可访问性、SEO、最佳实践和页面状态；当前工具说明中，性能问题应通过 Performance trace 分析，不能把 Lighthouse 分数当成唯一性能结论。

## 11. Service Worker、断点和其他面板边界

### Service Worker

list_pages 在支持的版本中可以返回扩展或 Service Worker 页面；evaluate_script 也支持通过 --serviceWorkerId 对 Service Worker 执行可序列化脚本。它不等于完整的 Service Worker DevTools 面板控制，注册、生命周期、Cache Storage 和 push 调试仍使用真实 DevTools 的 Application 面板或专用 CDP 工具。

### JavaScript 断点

当前 chrome-devtools-mcp 1.9.0 CLI 没有通用的“添加断点、条件断点、单步、继续、查看调用栈”命令。需要断点时：

- 使用 Edge/Chrome DevTools Sources 面板完成交互式单步。
- 使用 debugger 语句或页面侧临时 instrumentation 做最小复现。
- 将断点前后的状态通过 evaluate_script 或 Console 采样保存。
- 不把 evaluate_script 伪装成断点调试，也不在生产 userscript 中残留 debugger。

### HAR、Coverage 和 Layers

当前 MCP 没有标准 HAR 导出/导入、Coverage 面板或 Layers 面板的完整直接接口。需要这些证据时使用真实 DevTools 对应面板或专门 CDP 客户端；MCP 可以辅助导航、触发场景、读取 Network 列表和保存部分请求/响应，但不能替代完整面板导出。

## 12. 实验能力

以下能力必须显式开启，并不作为普通 userscript 调试依赖：

    chrome-devtools start --experimentalVision=true
    chrome-devtools start --experimentalScreencast=true
    chrome-devtools start --categoryExperimentalWebmcp=true
    chrome-devtools start --categoryExperimentalThirdParty=true

- Vision 坐标操作需要可靠的截图理解，优先使用快照 UID。
- Screencast 需要 ffmpeg，并可能增加 CPU、内存和磁盘开销。
- WebMCP 和第三方开发者工具由页面暴露时才有意义，不能默认信任页面提供的工具。
- 实验工具应在隔离页面中使用，完成后恢复普通配置。

## 13. 常见连接故障

### 后台服务在运行，但 list_pages 失败

按顺序检查：

1. MCP 客户端实际使用的服务器名称和命令。
2. chrome-devtools --version、--help 与服务端版本。
3. 目标浏览器是否允许远程调试。
4. browserUrl/wsEndpoint 是否来自当前实例。
5. 是否需要重新执行 list_pages 获取新 page id。

服务进程存在不代表 DevTools target 已连接；必须通过页面枚举和无副作用 evaluate_script 验证。

### TargetCloseError 或 page id 失效

页面刷新、关闭、浏览器重启和 SPA 导航都可能使旧 target 失效。重新执行 list_pages，按 URL、标题和类型选择新 page id，再重新执行最小验证。不要反复对旧 id 重试。

### EPERM、用户目录不可写或 profile 冲突

使用明确、可写、范围最小的临时 profile；不要删除用户 profile，不要把工作区根目录作为递归清理目标。已有 Edge 会话应优先使用连接模式；隔离测试才创建临时 profile。

### Origin/端口连接拒绝

确认浏览器实际监听端口和允许的调试 Origin。/json/version、WebSocket endpoint 和 MCP 启动参数必须来自同一个浏览器实例。不要把一次会话的端口、Origin 或 endpoint 永久写入技能。无法确认时切换到官方支持的 --autoConnect 或 --browserUrl 路径，并重新验证。

### --executablePath 导致目标立即关闭

不要把指定可执行文件路径当作默认修复。先确认浏览器通道、profile、远程调试模式和权限；只有明确需要独立浏览器二进制时才使用该参数，并在隔离 profile 中验证。

## 14. 临时注入与写入边界

临时 DevTools 注入只用于隔离验证：

1. 记录本地文件路径、版本和注入时间。
2. 使用独立页面或可恢复上下文。
3. 验证 DOM、Network、Console 和性能指标。
4. 刷新或关闭隔离页恢复页面。
5. 分别报告“本地文件已修改”“临时注入已验证”“Tampermonkey 已写入”三种状态。

DevTools MCP 不授权修改 Tampermonkey；任何已安装脚本写入仍遵循 `mcp-workflow.md` 的自有 bridge、用户明确授权、备份、差异和乐观锁流程。

## 15. Userscript 调试记录模板

    ## 调试记录

    - 日期：
    - 浏览器/版本：
    - 脚本管理器/版本：
    - userscript 名称/版本：
    - 页面 URL：
    - DevTools MCP/CLI 版本：
    - 连接方式：autoConnect / browserUrl / wsEndpoint / 隔离浏览器
    - page id：
    - 登录、隐私和缓存状态：
    - 固定窗口尺寸与网络条件：
    - 复现步骤：
    - DOM/快照证据：
    - Console 错误与归因：
    - Network 请求、状态和耗时：
    - Performance/LCP/INP/CLS/几何变化：
    - Memory snapshot（如有）：
    - 是否临时注入：
    - 是否写入 Tampermonkey：
    - 尚未验证的浏览器、管理器或场景：

只有静态检查、页面证据、性能证据和写入状态都分别记录，才可以称为完成调试。
