# dirsubmit

[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Test](https://github.com/fendouai/dirsubmit/actions/workflows/test.yml/badge.svg)](https://github.com/fendouai/dirsubmit/actions/workflows/test.yml)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev)

An open-source Python CLI that automates SaaS distribution end-to-end:

- **Directory submission** — auto/semi-auto submit your product to SaaS/AI directories.
- **Content distribution** — adapt one product description and publish it across blog / social / community / directory / launch channels.

Built on a **three-tier automation model**: fully-automatic (API + headless browser), semi-automatic (CDP session reuse), and manual (draft generation).

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


## Highlights

1. **AI-differentiated copy** — generates distinct tagline/description/category/tags per directory to avoid duplicate-content penalties.
2. **CDP dual-mode engine** — headless for no-login forms; reuse your real Chrome login state via CDP or a **lightweight Chrome extension** (no launch flags) so account-required directories become automatable.
3. **Credential detection** — every API channel declares its required credentials; unconfigured channels are auto-disabled and activate as soon as you fill them in.
4. **Review-status tracking** — SQLite records every submission; `status --check` re-fetches directory pages to verify if your listing went live.

## Three-tier model

| Tier | Method | Behavior |
|------|--------|----------|
| `auto` | Official API + headless browser | Fully unattended |
| `semi` | CDP or Chrome extension (reuses login) | Auto-fills forms, occasional captcha needs a human click |
| `manual` | Draft/cheatsheet generation | Produces adapted copy for human publishing |

For the `semi` tier, `dirsubmit` auto-picks the mode (default `--mode auto`): it uses the Chrome extension if installed, falls back to CDP if a debug port is up, and otherwise asks you to set one up. You can still force a specific mode with `--mode headless|cdp|extension`.

## Quick start

```bash
# 1. Install
pip install -e .
python -m playwright install chromium

# 2. Create your product profile
dirsubmit init
# edit product.yaml

# 3. Generate per-directory copy (falls back to templates without an LLM key)
dirsubmit gen --provider deepseek

# 4. See available directories / channels
dirsubmit list
dirsubmit channels

# 5. Submit to directories (auto via headless, manual via cheatsheet)
dirsubmit submit --mode headless

# 6. Distribute across API + browser + manual channels
dirsubmit distribute --dry-run
dirsubmit distribute --tier auto

# 7. Verify review status
dirsubmit status --check
```

## Documentation

| Doc | Covers |
|-----|--------|
| [Deployment](docs/deployment.md) | Install, prerequisites, CDP setup, troubleshooting |
| [Configuration](docs/configuration.md) | `product.yaml`, `.env`, recipe format, LLM providers |
| [Channels](docs/channels.md) | Full channel list, three tiers, OAuth setup, publishing map |
| [Submission catalog](docs/submission-catalog/README.md) | Directory listings, GitHub awesome repositories, and editorial outlets; per-product grades, actual receipts, pending work, and an offline filter page |

## Commands

| Command | Purpose |
|---------|---------|
| `init` | Generate `product.yaml` template |
| `gen` | Generate per-directory AI copy |
| `submit` | Submit to directories by tier |
| `status` | View / verify submission status |
| `list` | List directory recipes (by DR/tier) |
| `recipes` | List all recipe slugs |
| `distribute` | Unified distribution (API + browser + manual) |
| `channels` | List all channels and their enabled/disabled status |

## Project layout

```
src/dirsubmit/
├── cli.py        # CLI entry: all 8 subcommands
├── config.py     # product.yaml + env loader
├── models.py     # Product / Recipe / FieldSpec / Submission
├── llm.py        # multi-provider LLM (OpenAI/DeepSeek/Gemini/Ollama)
├── copywriter.py # per-directory + per-channel copy generation
├── recipes.py    # recipe loader/validator
├── store.py      # SQLite (submissions + copies)
├── engine.py     # Playwright: headless + CDP, cross-iframe, file upload
├── tracker.py    # review-status verification
├── api.py        # 18 API channels (credential-gated)
└── channels.py   # unified channel registry (API + browser + manual)
recipes/*.json    # directory recipes (add one JSON per directory)
```

## License

MIT.

## Browser Use / Computer Use

支持 Browser Use 视觉与 DOM Agent、Computer Use 执行器/接管任务、只读入口发现、填表预览、提交证据、按产品隔离及防重复提交。详见 [浏览器自动化](docs/browser-automation.zh-CN.md)。
