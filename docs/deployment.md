# Deployment

How to install and run `dirsubmit`.

## Prerequisites

- **Python 3.9+** (`python3 --version`)
- `pip` (comes with Python)
- **Google Chrome** — only needed for the `semi` tier (CDP session reuse)

No Node.js is required.

## Install

```bash
cd dirsubmit

# 1. Install the package (editable, so `dirsubmit` is available globally)
pip install -e .

# 2. Install the Playwright Chromium browser (headless engine)
python -m playwright install chromium
```

Verify the install:

```bash
dirsubmit --help
# should print the 8 subcommands: init gen submit status list recipes distribute channels
```

## First run

```bash
dirsubmit init          # creates product.yaml
# edit product.yaml with your product info
dirsubmit channels      # see all channels + which are enabled
```

## Set up CDP (for the `semi` tier)

The `semi` tier reuses your real Chrome login state. Launch Chrome with a debugging port and a persistent profile:

**macOS:**

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/dirsubmit-chrome \
  --no-first-run
```

**Linux:**

```bash
google-chrome --remote-debugging-port=9222 \
  --user-data-dir=/tmp/dirsubmit-chrome --no-first-run
```

**Windows:**

```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%TEMP%\dirsubmit-chrome
```

Then, in that Chrome window, log in to the directories you want to submit to (Google/GitHub OAuth, etc.). After that:

```bash
dirsubmit submit --tier semi --mode cdp
dirsubmit distribute --tier semi --mode cdp
```

> `--cdp-url` defaults to `http://localhost:9222`; override with `--cdp-url` or `DIRSUBMIT_CDP_URL`.

## Set up an LLM (optional but recommended)

`gen` / `distribute` fall back to template copy without an LLM key, but an LLM produces far better, differentiated content. Pick any provider:

```bash
export DEEPSEEK_API_KEY=sk-...        # or OPENAI_API_KEY / GEMINI_API_KEY
export DIRSUBMIT_LLM=deepseek         # openai | deepseek | gemini | ollama
```

See [Configuration](configuration.md) for all providers and channel credentials.

## Directory layout after first run

```
product.yaml          # your product profile (created by `dirsubmit init`)
recipes/*.json        # directory recipes
dirsubmit.db          # SQLite (submissions + copies), auto-created
cheatsheets/*.md      # manual-tier paste lists (auto-created)
drafts/*.md           # manual-channel drafts (auto-created)
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: playwright` | `pip install -e .` didn't run; or `pip install playwright` |
| `Executable doesn't exist ... chrome` | Run `python -m playwright install chromium` |
| `connect ECONNREFUSED 127.0.0.1:9222` | Chrome isn't running with the debug port; see CDP setup above |
| `未找到 product.yaml` | Run `dirsubmit init` first |
| `生成 0 个目录` | `recipes/` is empty — add recipe JSON files |
| `[disabled] <channel>` | That channel's credentials aren't set — see [Channels](channels.md) |
| `[warn] 未定位到字段 ...` | The recipe's CSS selectors no longer match the site (sites change) — update the recipe |

## Uninstall

```bash
pip uninstall dirsubmit
```
