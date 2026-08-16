# Dirsubmit — 设计文档

日期：2026-08-14

## 目标

一个开源 Python CLI 工具，帮助 SaaS 开发者把产品提交到各类目录/导航站，核心差异化是：

1. **AI 差异化文案**：为每个目录生成不同的 tagline / 简介 / 分类 / 标签，避免复制粘贴被降权。
2. **CDP 双模式引擎**：headless 跑无账号目录；`connect_over_cdp` 复用用户真实 Chrome 登录态，把「需账号」目录也自动化。
3. **分级自动化**：每个目录标记 `auto / semi / manual`，决定用哪种方式提交。
4. **审核状态跟踪**：SQLite 记录每次提交，`status` 命令重抓目录页验证是否已上线/审核中/被拒。

## 形态与技术栈

- Python 3.9+，CLI（argparse），依赖：`playwright`、`pyyaml`、`requests`。
- LLM 多后端可插拔：OpenAI / DeepSeek / Gemini / Ollama，环境变量切换；无 key 时退化为模板文案。

## 架构与组件

```
dirsubmit
├── cli.py        # 命令行入口：init / gen / submit / status / list / recipes
├── config.py     # 加载 product.yaml 与环境变量
├── models.py     # dataclass：Product / Recipe / FieldSpec / Submission
├── llm.py        # LLMClient（多后端）+ 模板回退
├── copywriter.py # 由 Product 生成每个目录的差异化文案
├── recipes.py    # 加载/校验 recipes/*.json
├── store.py      # SQLite：submissions、copies 两张表
├── engine.py     # Playwright：headless + CDP 双模式，按 tier 提交
└── tracker.py    # status：重抓目录页验证收录状态
```

数据文件：

- `product.yaml`：产品信息（名称/URL/tagline/简介/功能/定价/分类/关键词）。
- `recipes/*.json`：每个目录一个「食谱」，描述提交 URL、表单字段、选择器、DR、tier、验证方式。

## 数据流

1. `init` → 生成 `product.yaml` 模板。
2. `gen` → copywriter 读取 Product + 全部 recipes，逐目录生成文案，写入 SQLite `copies`。
3. `submit [--mode headless|cdp] [--tier auto,semi,manual] [--only slug]` →
   engine 读取 recipe + 文案：
   - `auto`：headless 浏览器填表提交；
   - `semi`：CDP 连真实 Chrome 复用登录态提交（无登录态则提示先登录）；
   - `manual`：生成「字段已填好的粘贴清单」（markdown），人肉去贴。
   结果写入 SQLite `submissions`。
4. `status` → tracker 对 `submitted` 状态的目录，用 `verify_url`（或站内搜索）检查产品名/URL 是否出现，
   更新为 `approved / pending / rejected`。

## 目录食谱（Recipe）结构

```json
{
  "name": "Altern",
  "slug": "altern",
  "submit_url": "https://altern.ai/submit",
  "homepage": "https://altern.ai",
  "dr": 45,
  "tier": "auto",
  "requires_auth": false,
  "verify": { "type": "search", "url": "https://altern.ai/?search={name}" },
  "fields": [
    {"name": "name", "type": "text", "required": true, "source": "name",
     "selectors": ["input[name='name']", "#name"]},
    {"name": "description", "type": "textarea", "required": true,
     "source": "ai.description", "selectors": ["textarea[name='description']"]}
  ]
}
```

字段 `source` 支持两类：

- 产品字段：`name / url / tagline / description / email / pricing / logo_url`
- AI 字段：`ai.tagline / ai.description / ai.category / ai.tags`

## 错误处理

- LLM 调用失败 → 回退到模板文案，继续执行，不中断批量。
- Playwright 定位不到选择器 → 记录 warning，该目录标记 `failed`，跳到下一个。
- CDP 连不上（Chrome 未以调试端口启动）→ 打印启动命令提示，退出该模式。
- 所有提交结果幂等写入 SQLite，`submit` 可重复跑，已提交的跳过（除非 `--force`）。

## 测试策略

- 单元测试：recipe 加载/校验、copywriter 模板回退、store 读写、tracker 的 HTML 匹配逻辑。
- 冒烟测试：`init` → `gen`（无 key，模板回退）→ `list` → `status` 全链路跑通。
- 引擎的浏览器部分用手动冒烟（真实站点反爬/改版频繁，不做脆弱 e2e）。
