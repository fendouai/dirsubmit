# Channels

How `dirsubmit` distributes content across channels, the three-tier model, and how to get credentials for every channel.

## Three-tier model

| Tier | Method | Behavior | dirsubmit |
|------|--------|----------|-----------|
| `auto` | Official API + headless browser | Fully unattended | `distribute --tier auto` |
| `semi` | CDP browser (reuses your login) | Auto-fills forms; occasional captcha needs a human click | `distribute --tier semi --mode cdp` |
| `manual` | Draft / cheatsheet generation | Produces adapted copy for human publishing | `distribute --tier manual` |

## Channel list

### API channels (18 — `tier: auto`)

| Channel | Category | Credentials (env vars) |
|---------|----------|------------------------|
| DEV.to | blog | `DEVTO_API_KEY` |
| WordPress | blog | `WORDPRESS_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD` |
| Ghost | blog | `GHOST_ADMIN_URL`, `GHOST_ADMIN_KEY` |
| Hashnode | blog | `HASHNODE_TOKEN` (+ optional `HASHNODE_PUBLICATION_ID`) |
| X / Twitter | social | `X_ACCESS_TOKEN` |
| LinkedIn | social | `LINKEDIN_ACCESS_TOKEN` (+ optional `LINKEDIN_PERSON_ID`) |
| Facebook Page | social | `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN` |
| Threads | social | `THREADS_ACCESS_TOKEN`, `THREADS_USER_ID` |
| Bluesky | social | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` |
| Mastodon | social | `MASTODON_INSTANCE`, `MASTODON_ACCESS_TOKEN` |
| Telegram | social | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Discord | community | `DISCORD_WEBHOOK_URL` |
| Slack | community | `SLACK_WEBHOOK_URL` |
| Generic Webhook | social | `WEBHOOK_URL` |
| Instagram | social (image) | `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN` + `image_url` |
| Pinterest | social (image) | `PINTEREST_ACCESS_TOKEN`, `PINTEREST_BOARD_ID` + `image_url` |
| YouTube | video | `YOUTUBE_ACCESS_TOKEN` + `video_file` (upload pending) |
| TikTok | video | `TIKTOK_ACCESS_TOKEN`, `TIKTOK_OPEN_ID` + `video_file` (upload pending) |

### Browser channels (directories — from `recipes/*.json`)

Each directory recipe has a `tier`: `auto` (no-login form), `semi` (account needed, CDP), or `manual` (editorial review).

### Manual channels (8 — `tier: manual`, drafts only)

Reddit · Hacker News · Indie Hackers · Lobsters · Medium · Substack · Capterra · AppSumo.

## Credential detection

Every API channel declares its required env vars. Channels without them are **disabled** and skipped automatically:

```bash
dirsubmit channels          # shows enabled / disabled + missing vars
dirsubmit distribute --tier auto   # skips disabled channels
```

Fill in the credentials and the channel activates automatically — no code change.

## Getting credentials

### Zero-friction (direct key/token, no OAuth)

| Channel | Where | What you get |
|---------|-------|--------------|
| Telegram | chat with `@BotFather`, `/newbot` | bot token; then `@userinfobot` for chat id |
| Discord | Server Settings → Integrations → Webhooks | webhook URL |
| Slack | api.slack.com → Create App → Incoming Webhooks | webhook URL |
| DEV.to | dev.to/settings/extensions | API key |
| Bluesky | bsky.app → Settings → App Passwords | app password (NOT login password) |
| Mastodon | your instance → Preferences → Development → New app | access token (grant `write`) |
| WordPress | Users → Profile → Application Passwords | app password |
| Ghost | Settings → Integrations → Custom Integration | Admin API key (`id:secret`) |
| Hashnode | Settings → Developer | personal access token |

### OAuth (authorization flow, tokens expire)

| Channel | Portal | Flow / scopes |
|---------|--------|---------------|
| X / Twitter | developer.x.com | OAuth 2.0, `tweet.write tweet.read`; pay-per-use |
| LinkedIn | linkedin.com/developers | OAuth 2.0, `w_member_social` |
| Facebook | developers.facebook.com | Login + `pages_manage_posts` → Page access token |
| Instagram | developers.facebook.com → Instagram | Graph API + App Review (`content_publish_scope`) |
| Threads | developers.facebook.com → Threads | Threads API, authorization code |
| Pinterest | developers.pinterest.com | OAuth 2.0, `pins:write` |
| YouTube | console.cloud.google.com | OAuth 2.0, `youtube.upload` |
| TikTok | developers.tiktok.com | Content Posting API, `video.upload` |

Full step-by-step for each OAuth channel: [`channel-oauth-setup.md`](channel-oauth-setup.md).

> **Token expiry**: OAuth access tokens expire (YouTube ~1h, X ~2h, TikTok ~24h, LinkedIn/Facebook/Instagram/Threads ~60d). `dirsubmit` currently reads static tokens — re-authorize when they expire.

## Publishing matrix

```
              Internet Distribution
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
  Blog              Social             Video
 DEV/WordPress     X/LinkedIn         YouTube
 Ghost/Hashnode    Instagram          TikTok
                   Threads/Bluesky
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
 Communities       Directories        Launch
 Reddit/HN         Futurepedia        Product Hunt
 Indie Hackers     TAAFT/SaaSHub      BetaList
 GitHub            AlternativeTo      Microlaunch
```

## Adding a channel or directory

- **New API channel** — add an entry to `API_CHANNELS` in `src/dirsubmit/channels.py`, its credentials to `REQUIREMENTS` and a handler in `src/dirsubmit/api.py`.
- **New directory** — drop a JSON into `recipes/` (see [Configuration](configuration.md) for the recipe format).
- **New manual channel** — add an entry to `MANUAL_CHANNELS` in `channels.py`.
