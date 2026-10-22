# dirsubmit

[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Test](https://github.com/fendouai/dirsubmit/actions/workflows/test.yml/badge.svg)](https://github.com/fendouai/dirsubmit/actions/workflows/test.yml)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev)

开源 Python CLI，一站式自动化 SaaS 分发：

- **目录提交** — 自动/半自动把你的产品提交到 SaaS/AI 目录站。
- **内容分发** — 一份产品介绍，自动改写并分发到博客 / 社交 / 社区 / 目录 / Launch 平台。

基于**三层自动化模型**：全自动（API + 无头浏览器）、半自动（CDP 复用登录态）、纯人工（草稿生成）。

![dirsubmit demo](assets/screenshot.png)

<!-- submission-results:start -->
## 当前提交结果（2026-10-20 整理）

[查看全部成功、待审核及未成功明细](docs/submission-records/README.md)。覆盖 Botstest、WarmQuant、WeWorkBuddy，按目录、GitHub 和文章投稿三类逐产品列出原因及下一步。

| 当前结果 | 产品目标记录数 |
|---|---:|
| S：已公开收录或合并 | 38 |
| A：申请已接收、开放 PR 或稿件已投递，待审核 | 266 |
| B：可执行但未发送 | 0 |
| C：条件、人工步骤或实际回执未解决 | 2545 |
| D：不适配、仅付费、关闭、拒绝等 | 1104 |
| U：未实测或证据不足 | 2047 |

**已确认提交共 304 条，其中真正公开或合并 38 条；待审核不等于收录成功。** 这些是产品与目标的独立记录，不是 304 个站点。已知清单共 2,000 个目标，不能当作全部已经尝试。100 个新增站点专项为 **5/100**，尚未完成。

本次汇总现有证据，没有重新联网核验所有结果；具体核验时间、结果链接与失败原因见[完整记录](docs/submission-records/README.md)。
<!-- submission-results:end -->


## 亮点

1. **AI 差异化文案** — 为每个目录生成不同的 tagline/简介/分类/标签，避免复制粘贴被降权。
2. **CDP 双模式引擎** — 无头模式跑无登录表单；通过 CDP 或**轻量 Chrome 扩展**（无需启动参数）复用你真实 Chrome 登录态，把「需账号」的目录也自动化。
3. **凭证检测** — 每个 API 渠道声明必需凭证；没配的渠道自动禁用，配好即自动启用。
4. **审核状态跟踪** — SQLite 记录每次提交；`status --check` 重抓目录页验证是否已上线。

## 三层模型

| 层次 | 方法 | 行为 |
|------|------|------|
| `auto` | 官方 API + 无头浏览器 | 全自动，无人值守 |
| `semi` | CDP 或 Chrome 扩展（复用登录态） | 自动填表，偶发验证码需人工点一下 |
| `manual` | 草稿/清单生成 | 生成适配文案，人肉发布 |

`semi` 层默认自动选模式（`--mode auto`）：装了 Chrome 扩展就走扩展，检测到调试端口就走 CDP，都没有则提示你配置。也可用 `--mode headless|cdp|extension` 强制指定。

## 快速开始

```bash
# 1. 安装
pip install -e .
python -m playwright install chromium

# 2. 创建产品档案
dirsubmit init
# 编辑 product.yaml

# 3. 生成每个目录的差异化文案（无 LLM key 时自动退化模板）
dirsubmit gen --provider deepseek

# 4. 查看可用目录 / 渠道
dirsubmit list
dirsubmit channels

# 5. 提交目录（auto 用无头，manual 生成清单）
dirsubmit submit --mode headless

# 6. 统一分发（API + 浏览器 + 手动渠道）
dirsubmit distribute --dry-run
dirsubmit distribute --tier auto

# 7. 核验审核状态
dirsubmit status --check
```

## 文档

| 文档 | 内容 |
|------|------|
| [部署](docs/deployment.zh-CN.md) | 安装、依赖、CDP 配置、排障 |
| [配置](docs/configuration.zh-CN.md) | `product.yaml`、`.env`、食谱格式、LLM 后端 |
| [渠道](docs/channels.zh-CN.md) | 渠道清单、三层模型、OAuth 申请、分发地图 |
| [三类提交清单](docs/submission-catalog/README.md) | 目录导航站、GitHub awesome 仓库和文章投稿渠道；逐产品等级、实际回执、待办与离线筛选页 |

## 命令

| 命令 | 用途 |
|------|------|
| `init` | 生成 `product.yaml` 模板 |
| `gen` | 生成每个目录的差异化 AI 文案 |
| `submit` | 按 tier 提交目录 |
| `status` | 查看 / 核验提交状态 |
| `list` | 列出目录食谱（按 DR/tier） |
| `recipes` | 列出所有食谱 slug |
| `distribute` | 统一分发（API + 浏览器 + 手动） |
| `channels` | 列出所有渠道及启用状态 |

## 项目结构

```
src/dirsubmit/
├── cli.py        # CLI 入口：8 个子命令
├── config.py     # product.yaml + 环境变量加载
├── models.py     # Product / Recipe / FieldSpec / Submission
├── llm.py        # 多后端 LLM（OpenAI/DeepSeek/Gemini/Ollama）
├── copywriter.py # 按目录/按渠道生成文案
├── recipes.py    # 食谱加载/校验
├── store.py      # SQLite（提交记录 + 文案）
├── engine.py     # Playwright：headless + CDP、跨 iframe、文件上传
├── tracker.py    # 审核状态核验
├── api.py        # 18 个 API 渠道（凭证门控）
└── channels.py   # 统一渠道注册表（API + 浏览器 + 手动）
recipes/*.json    # 目录食谱（每加一个目录 = 加一个 JSON）
```

## 许可

MIT。

## Browser Use / Computer Use

支持 Browser Use 视觉与 DOM Agent、Computer Use 执行器/接管任务、只读入口发现、填表预览、提交证据、按产品隔离及防重复提交。详见 [浏览器自动化](docs/browser-automation.zh-CN.md)。

## 免费目录 API

CurlShip 支持仅发送产品 HTTPS 首页与显式 `submitter_email` 的匿名免费提交；这项邮箱配置与产品业务联系 `email` 分开。先运行只读演练：

```bash
dirsubmit --product product.yaml distribute --only curlship.com --dry-run
```

仅选择该目录 API 时不启动 LLM 或 Chrome。真实执行有产品隔离、防重复及单次 POST 保护；A 表示接收，S 另需公开验证。已记录的三个产品不会复投。配置、查重范围与状态说明见 [CurlShip 免费目录 API](docs/browser-automation.zh-CN.md#curlship-免费目录-api)。
