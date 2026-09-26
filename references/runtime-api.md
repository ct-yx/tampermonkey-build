# GM Runtime API 使用边界

## API 选择

优先使用管理器同时支持的现代 `GM.*` Promise API；需要兼容旧脚本时才使用 legacy `GM_*` 回调/同步 API。不要在同一模块中无规则混搭两套错误处理方式。

常用能力：

- 存储：`GM.getValue`、`GM.setValue`、`GM.deleteValue`、`GM.listValues`、值变更监听。
- 网络：`GM.xmlHttpRequest`，跨域请求不依赖目标站点 CORS，但必须最小化 `@connect`。
- 页面资源：`GM.getResourceText`、`GM.getResourceURL`，配合 `@resource`。
- UI：`GM.addStyle`、`GM.addElement`、`GM.registerMenuCommand`、`GM.notification`。
- 文件与剪贴板：`GM.download`、`GM.setClipboard`，仅在确有需求时申请。
- 标签页：`GM.openInTab`，不要用它绕过用户明确的导航意图。

## 存储

```javascript
const enabled = await GM.getValue('enabled', true);
await GM.setValue('enabled', !enabled);
```

存储值必须可序列化、键名带项目命名空间，并考虑版本迁移。读取失败时使用明确默认值；不要把 token、密码或完整 Cookie 写入 userscript 存储。跨标签同步要用变更监听或显式刷新，不要用高频轮询。

## 跨域请求

```javascript
const response = await GM.xmlHttpRequest({
  method: 'GET',
  url: 'https://api.example.com/data',
  responseType: 'json',
  timeout: 8000,
});
```

实现时必须处理：超时、abort、非 2xx、解析失败、重定向、网络断开和用户拒绝。请求 URL 不得由不可信页面文本直接拼接；限制协议、主机、方法和响应大小。`GM_xmlhttpRequest` 在 Tampermonkey 背景上下文发出，代理和证书行为遵循浏览器/系统网络栈，不要宣称它自带代理或绕过 TLS 验证。

`GM_webRequest` 是实验性 API。官方文档说明 Chrome 及衍生浏览器的 Manifest V3 Tampermonkey 5.2+ 已不再提供它；需要改写请求时应优先评估页面 fetch/XHR 包装、站点公开 API 或浏览器扩展级方案，并在目标版本真实验证。

## DOM、样式和菜单

- 通过 `GM.addStyle` 注入带命名空间的 CSS，避免覆盖站点全局选择器。
- 通过 `GM.addElement` 处理 CSP 场景，但仍需清理和防重复挂载。
- 菜单命令回调中读取最新设置，不要捕获过期闭包。
- 添加的节点、监听器和菜单在页面卸载前可追踪；SPA 切换时不要重复添加。

## 错误和权限

权限错误、用户拒绝、网络错误和业务错误使用不同错误码/日志标签。生产默认不刷屏；调试日志应带唯一前缀并在交付前移除或受设置开关控制。任何需要 `unsafeWindow`、cookie、下载或通知的功能，都要说明数据边界和失败行为。
