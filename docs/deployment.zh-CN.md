# 部署

如何安装和运行 `dirsubmit`。

## 前置条件

- **Python 3.9+**（`python3 --version`）
- `pip`（随 Python 自带）
- **Google Chrome** — 仅 `semi` 层（CDP 复用登录态）需要

无需 Node.js。

## 安装

```bash
cd dirsubmit

# 1. 安装包（editable 模式，`dirsubmit` 命令全局可用）
pip install -e .

# 2. 安装 Playwright 的 Chromium 浏览器（无头引擎）
python -m playwright install chromium
```

验证安装：

```bash
dirsubmit --help
# 应打印 8 个子命令：init gen submit status list recipes distribute channels
```

## 首次运行

```bash
dirsubmit init          # 生成 product.yaml
# 编辑 product.yaml，填入产品信息
dirsubmit channels      # 查看所有渠道及启用状态
```

## 配置 CDP（`semi` 层需要）

`semi` 层复用你真实 Chrome 的登录态。用调试端口 + 持久 profile 启动 Chrome：

**macOS：**

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/dirsubmit-chrome \
  --no-first-run
```

**Linux：**

```bash
google-chrome --remote-debugging-port=9222 \
  --user-data-dir=/tmp/dirsubmit-chrome --no-first-run
```

**Windows：**

```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%TEMP%\dirsubmit-chrome
```

然后在该 Chrome 窗口里登录你要提交的目录站（Google/GitHub OAuth 等），之后：

```bash
dirsubmit submit --tier semi --mode cdp
dirsubmit distribute --tier semi --mode cdp
```

> `--cdp-url` 默认 `http://localhost:9222`，可用 `--cdp-url` 或 `DIRSUBMIT_CDP_URL` 覆盖。

## 配置 LLM（可选但推荐）

没有 LLM key 时 `gen`/`distribute` 会退化为模板文案；配了 LLM 能产出更优质、更差异化的内容。任选一个后端：

```bash
export DEEPSEEK_API_KEY=sk-...        # 或 OPENAI_API_KEY / GEMINI_API_KEY
export DIRSUBMIT_LLM=deepseek         # openai | deepseek | gemini | ollama
```

所有后端与渠道凭证见 [配置](configuration.zh-CN.md)。

## 首次运行后的目录结构

```
product.yaml          # 产品档案（dirsubmit init 生成）
recipes/*.json        # 目录食谱
dirsubmit.db          # SQLite（提交记录 + 文案），自动创建
cheatsheets/*.md      # manual 层粘贴清单，自动创建
drafts/*.md           # manual 渠道草稿，自动创建
```

## 排障

| 问题 | 解决 |
|------|------|
| `ModuleNotFoundError: playwright` | 没跑 `pip install -e .`；或 `pip install playwright` |
| `Executable doesn't exist ... chrome` | 跑 `python -m playwright install chromium` |
| `connect ECONNREFUSED 127.0.0.1:9222` | Chrome 没带调试端口启动，见上方 CDP 配置 |
| `未找到 product.yaml` | 先跑 `dirsubmit init` |
| `生成 0 个目录` | `recipes/` 为空 — 添加食谱 JSON |
| `[disabled] <渠道>` | 该渠道凭证未配置 — 见 [渠道](channels.zh-CN.md) |
| `[warn] 未定位到字段 ...` | 食谱里的 CSS 选择器已不匹配（站点改版）— 更新食谱 |

## 卸载

```bash
pip uninstall dirsubmit
```
