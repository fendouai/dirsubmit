# dirsubmit Bridge — Chrome 扩展

一个轻量 Chrome 扩展，让 `dirsubmit` 直接控制你的日常 Chrome（复用登录态），无需用调试端口启动 Chrome。

## 安装（加载未打包扩展）

1. 打开 Chrome，访问 `chrome://extensions`
2. 打开右上角「开发者模式」
3. 点「加载已解压的扩展程序」
4. 选择本目录（`extension/`）

安装后，扩展会在后台连接 `ws://127.0.0.1:8721`（dirsubmit 的本地 WebSocket 服务器）。

## 使用

```bash
# semi 层目录提交（复用 Chrome 登录态）
dirsubmit submit --tier semi --mode extension

# 统一分发（浏览器目录走扩展）
dirsubmit distribute --tier semi --mode extension
```

**注意**：Chrome 的 MV3 service worker 空闲后可能休眠。如果 `dirsubmit` 提示「扩展未连接」，点一下扩展图标（或 `chrome://extensions` 里点「重新加载」）唤醒即可。

## 工作原理

```
dirsubmit (Python)                 Chrome 扩展
     │                                 │
     │  ── navigate/fill/click ──►  WebSocket ◄── 连入
     │  ◄── 结果 (JSON) ────────►  background.js
     │                                 │
     │                        chrome.scripting.executeScript
     │                                 │
     │                          页面 DOM（填表/点击）
```

- `background.js`：连接 WS、接收命令、用 `chrome.scripting.executeScript`（`allFrames: true`）在页面里执行填表/点击。
- 支持跨 iframe（`allFrames` 自动覆盖子 frame）。
- 填表用原生 value setter + `input`/`change` 事件，兼容 React/Vue 等框架。

## 权限说明

| 权限 | 用途 |
|------|------|
| `tabs` | 定位当前标签页 |
| `scripting` | 在页面里执行填表/点击脚本 |
| `host_permissions: <all_urls>` | 允许在任意目录站页面执行 |

## 限制

- 暂不支持文件上传（`type: file` 字段会跳过）。
- 仅控制「当前活动标签页」，多标签并发未实现。
- 端口固定 `8721`（可用 `--ext-port` / `DIRSUBMIT_EXT_PORT` 覆盖）。
