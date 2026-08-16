# dirsubmit

An open-source Python CLI that automates SaaS distribution end-to-end:

- **Directory submission** — auto/semi-auto submit your product to SaaS/AI directories.
- **Content distribution** — adapt one product description and publish it across blog / social / community / directory / launch channels.

Built on a **three-tier automation model**: fully-automatic (API + headless browser), semi-automatic (CDP session reuse), and manual (draft generation).

## Highlights

1. **AI-differentiated copy** — generates distinct tagline/description/category/tags per directory to avoid duplicate-content penalties.
2. **CDP dual-mode engine** — headless for no-login forms; `connect_over_cdp` reuses your real Chrome login state so account-required directories become automatable.
3. **Credential detection** — every API channel declares its required credentials; unconfigured channels are auto-disabled and activate as soon as you fill them in.
4. **Review-status tracking** — SQLite records every submission; `status --check` re-fetches directory pages to verify if your listing went live.

## Three-tier model

| Tier | Method | Behavior |
|------|--------|----------|
| `auto` | Official API + headless browser | Fully unattended |
| `semi` | CDP browser (reuses login) | Auto-fills forms, occasional captcha needs a human click |
| `manual` | Draft/cheatsheet generation | Produces adapted copy for human publishing |

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
