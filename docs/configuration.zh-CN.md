# 配置

`dirsubmit` 通过三类文件配置：`product.yaml`、`.env`（或环境变量）、`recipes/*.json`。

## 1. `product.yaml` — 产品档案

AI 文案与表单填充的唯一数据源。

```yaml
name: My SaaS            # 产品名
url: https://example.com # 产品 URL
tagline: 一句话卖点
description: |
  2-4 句：做什么、给谁用、解决什么问题。
features:                # 功能点
  - 功能 1
  - 功能 2
pricing: Free            # 定价模型（同时用于 "Price" 表单字段）
categories:              # 候选分类，AI 按目录挑选最贴切的一个
  - Productivity
  - AI
keywords:                # 用于标签 / hashtag
  - automation
  - saas
logo_url: https://example.com/logo.png
email: you@example.com   # 部分目录需要邮箱
twitter: yourhandle
```

| 字段 | 用途 |
|------|------|
| `name`、`url` | 表单字段、AI 文案、状态跟踪 |
| `tagline`、`description`、`features` | AI 文案生成 |
| `pricing` | "Price" 表单字段 |
| `categories`、`keywords` | 分类/标签字段 + AI 文案 |
| `logo_url` | 图片上传字段 |
| `email` | 目录 + 渠道提交 |

## 2. 环境变量（`.env`）

复制 `.env.example` → `.env`，按需填写。

### LLM 后端（任选其一）

| 变量 | 用途 |
|------|------|
| `DIRSUBMIT_LLM` | 默认后端：`openai` \| `deepseek` \| `gemini` \| `ollama` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI（默认 `gpt-4o-mini`） |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` | DeepSeek（默认 `deepseek-chat`） |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Gemini（默认 `gemini-2.0-flash`） |
| `OLLAMA_MODEL` | Ollama（默认 `llama3.2`），本地服务 |

### CDP

| 变量 | 用途 |
|------|---------|
| `DIRSUBMIT_CDP_URL` | CDP 端点（默认 `http://localhost:9222`） |

### 渠道凭证

每个 API 渠道需各自凭证；未配置的渠道自动禁用。完整清单见 [渠道](channels.zh-CN.md)，变量名见 `.env.example`。

## 3. 食谱格式（`recipes/*.json`）

每个目录一个 JSON。加一个目录 = 加一个 JSON 文件。

```json
{
  "name": "Altern",
  "slug": "altern",
  "submit_url": "https://altern.ai/submit",
  "homepage": "https://altern.ai",
  "dr": 45,
  "tier": "semi",
  "requires_auth": true,
  "wait_ms": 0,
  "submit_selector": "button[type='submit']",
  "verify": { "type": "search", "url": "https://altern.ai/?search={name}" },
  "fields": [
    { "name": "name", "type": "text", "required": true, "source": "name",
      "selectors": ["input[name='name']", "#name"] },
    { "name": "description", "type": "textarea", "required": true,
      "source": "ai.description", "selectors": ["textarea[name='description']"] },
    { "name": "logo", "type": "file", "source": "",
      "file_path": "/path/to/logo.png", "selectors": ["input[type='file']"] }
  ]
}
```

### 食谱字段

| 字段 | 含义 |
|------|------|
| `slug` | 唯一 id（默认取文件名） |
| `name` | 显示名 |
| `submit_url` | 表单 URL |
| `homepage` | 站点首页 |
| `dr` | 域名权威度（用于排序） |
| `tier` | `auto` \| `semi` \| `manual` |
| `requires_auth` | 是否需账号 |
| `wait_ms` | 页面加载后等待毫秒（用于异步/iframe 表单） |
| `submit_selector` | 提交按钮的 CSS 选择器 |
| `verify` | `status --check` 核验方式：`{"type":"search","url":"...{name}..."}` 或 `{"type":"url","url":"..."}` |
| `fields[]` | 要填的表单字段 |

### 字段 spec

| 字段 | 含义 |
|------|------|
| `name` | 内部键 |
| `type` | `text` \| `textarea` \| `select` \| `url` \| `email` \| `checkbox` \| `file` |
| `required` | 是否必填 |
| `source` | 取值来源：产品字段（`name`/`url`/`email`/`pricing`…）或 AI 字段（`ai.tagline`/`ai.description`/`ai.category`/`ai.tags`） |
| `selectors` | CSS 选择器，按顺序尝试（支持跨 iframe） |
| `file_path` | `type: file` 时：要上传的本地文件路径 |

> **注意**：站点改版会导致 CSS 选择器失效。食谱系统刻意设计成「加一个 JSON、提一个 PR」的模式，让社区持续维护选择器。

## 4. SQLite 数据库（`dirsubmit.db`）

自动创建两张表：

- `submissions` — 目录/渠道、tier、状态、时间戳、备注。
- `copies` — 每个目录生成的文案。

状态值：`pending` · `submitted` · `approved` · `rejected` · `failed` · `manual` · `disabled` · `dry-run`。

## 5. 全局 CLI 参数

| 参数 | 默认 | 用途 |
|------|------|------|
| `--product` | `product.yaml` | 产品档案路径 |
| `--recipes` | `recipes` | 食谱目录 |
| `--db` | `dirsubmit.db` | SQLite 路径 |
