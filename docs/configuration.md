# Configuration

`dirsubmit` is configured via three files: `product.yaml`, `.env` (or environment variables), and `recipes/*.json`.

## 1. `product.yaml` — your product profile

The single source of truth for both AI copy and form-filling.

```yaml
name: My SaaS            # product name
url: https://example.com # product URL
tagline: One-line pitch
description: |
  2-4 sentences: what it does, who it's for, what problem it solves.
features:                # bullet points
  - Feature 1
  - Feature 2
pricing: Free            # pricing model (also used for "Price" form fields)
categories:              # candidate categories; AI picks the best per directory
  - Productivity
  - AI
keywords:                # used for tags/hashtags
  - automation
  - saas
logo_url: https://example.com/logo.png
email: you@example.com   # some directories require an email
twitter: yourhandle
```

| Field | Used for |
|-------|----------|
| `name`, `url` | form fields, AI copy, tracking |
| `tagline`, `description`, `features` | AI copy generation |
| `pricing` | "Price" form fields |
| `categories`, `keywords` | category/tag form fields + AI copy |
| `logo_url` | image upload fields |
| `email` | directory + channel submissions |

## 2. Environment variables (`.env`)

Copy `.env.example` → `.env`, then fill in what you need.

### LLM providers (pick one)

| Variable | Purpose |
|----------|---------|
| `DIRSUBMIT_LLM` | Default provider: `openai` \| `deepseek` \| `gemini` \| `ollama` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI (default model `gpt-4o-mini`) |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` | DeepSeek (default `deepseek-chat`) |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Gemini (default `gemini-2.0-flash`) |
| `OLLAMA_MODEL` | Ollama (default `llama3.2`), local server |

### CDP

| Variable | Purpose |
|----------|---------|
| `DIRSUBMIT_CDP_URL` | CDP endpoint (default `http://localhost:9222`) |

### Channel credentials

Each API channel requires its own credentials; unset channels are auto-disabled. The full list is in [Channels](channels.md). See `.env.example` for every variable name.

## 3. Recipe format (`recipes/*.json`)

One JSON per directory. Adding a directory = adding a JSON file.

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

### Recipe fields

| Field | Meaning |
|-------|---------|
| `slug` | unique id (defaults to filename) |
| `name` | display name |
| `submit_url` | the form URL |
| `homepage` | site homepage |
| `dr` | domain rating (for sorting) |
| `tier` | `auto` \| `semi` \| `manual` |
| `requires_auth` | whether an account is needed |
| `wait_ms` | wait after page load (for async/iframe forms) |
| `submit_selector` | CSS selector for the submit button |
| `verify` | how `status --check` verifies: `{"type":"search","url":"...{name}..."}` or `{"type":"url","url":"..."}` |
| `fields[]` | form fields to fill |

### Field spec

| Field | Meaning |
|-------|---------|
| `name` | internal key |
| `type` | `text` \| `textarea` \| `select` \| `url` \| `email` \| `checkbox` \| `file` |
| `required` | required flag |
| `source` | where the value comes from: product field (`name`, `url`, `email`, `pricing`, …) or AI field (`ai.tagline`, `ai.description`, `ai.category`, `ai.tags`) |
| `selectors` | CSS selectors, tried in order (supports cross-iframe) |
| `file_path` | for `type: file`: local file to upload |

> **Note**: CSS selectors break when sites redesign. The recipe system is intentionally a "add a JSON, submit a PR" model so the community can keep selectors fresh.

## 4. SQLite database (`dirsubmit.db`)

Two tables, auto-created:

- `submissions` — directory/channel, tier, status, timestamps, note.
- `copies` — generated copy per directory.

Status values: `pending` · `submitted` · `approved` · `rejected` · `failed` · `manual` · `disabled` · `dry-run`.

## 5. Global CLI flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--product` | `product.yaml` | product profile path |
| `--recipes` | `recipes` | recipes directory |
| `--db` | `dirsubmit.db` | SQLite path |
