# Channel Credential Setup Guide

> How to get credentials for each channel and which env var to set (`.env`).
> Two categories: **zero-friction (direct key/token)** and **OAuth (authorization flow)**.
>
> ⚠️ Note: OAuth access tokens **expire** (1 hour to 60 days depending on platform).
> `dirsubmit` currently reads static tokens; re-authorize when they expire. Auto-refresh can be added later.

---

## Part 1 — Zero-friction channels (a few minutes, direct key/token)

### 1. Telegram
- Open Telegram, chat with `@BotFather` → `/newbot` → name it → get the **Bot Token**
- Send a message to your bot, then use `@userinfobot` or `getUpdates` to get the **Chat ID**
- `.env`:
  ```
  TELEGRAM_BOT_TOKEN=<bot token>
  TELEGRAM_CHAT_ID=<chat id>
  ```

### 2. Discord
- Server Settings → Integrations → Webhooks → **New Webhook** → pick a channel → copy the Webhook URL
- `.env`:
  ```
  DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
  ```

### 3. Slack
- [api.slack.com](https://api.slack.com) → Create App → From scratch
- Enable **Incoming Webhooks** → authorize a channel → copy the Webhook URL
- `.env`:
  ```
  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
  ```

### 4. DEV.to
- [dev.to/settings/extensions](https://dev.to/settings/extensions) → DEV Community API Keys → Generate
- `.env`:
  ```
  DEVTO_API_KEY=<api key>
  ```

### 5. Bluesky
- [bsky.app](https://bsky.app) → Settings → **App Passwords** → Add App Password (this is an **app password**, not your login password)
- `.env`:
  ```
  BLUESKY_HANDLE=yourhandle.bsky.social
  BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
  ```

### 6. Mastodon
- Your instance → Preferences → Development → New Application → check `write` scope → get the **Access Token**
- `.env`:
  ```
  MASTODON_INSTANCE=https://mastodon.social
  MASTODON_ACCESS_TOKEN=<access token>
  ```

### 7. WordPress
- WP admin → Users → Profile → scroll to "Application Passwords" → Add New
- `.env`:
  ```
  WORDPRESS_URL=https://yourblog.com
  WORDPRESS_USERNAME=admin
  WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx
  ```

### 8. Ghost
- Ghost admin → Settings → Integrations → Custom Integration → Add
- Get the **Admin API Key** (format `id:secret`)
- `.env`:
  ```
  GHOST_ADMIN_URL=https://yourblog.com
  GHOST_ADMIN_KEY=<id>:<secret>
  ```

### 9. Hashnode
- [hashnode.com](https://hashnode.com) → Settings → Developer → **Personal Access Token** → Generate
- `.env`:
  ```
  HASHNODE_TOKEN=<pat>
  HASHNODE_PUBLICATION_ID=<optional, target publication>
  ```

---

## Part 2 — OAuth channels (authorization flow, tokens expire)

### 1. X / Twitter

| Step | Description |
|------|-------------|
| 1. Register developer | [developer.x.com](https://developer.x.com) → create a project + App |
| 2. Choose auth | OAuth 2.0 (recommended; `/2/tweets` uses a Bearer token) |
| 3. Authorization code | Get `client_id`/`client_secret` → Authorization Code flow, scopes `tweet.write tweet.read users.read` |
| 4. Get token | access token (expires ~2h; needs refresh token) |

- **Note**: X API is commercialized (pay-per-use); the free tier is mostly read-only.
- `.env`: `X_ACCESS_TOKEN=<access token>`

### 2. LinkedIn

| Step | Description |
|------|-------------|
| 1. Create App | [linkedin.com/developers](https://www.linkedin.com/developers) → Create App |
| 2. Add product | Check **Share on LinkedIn** |
| 3. OAuth 2.0 | Authorization Code flow, scope `w_member_social` |
| 4. Get token | access token (valid 60 days) |

- `.env`: `LINKEDIN_ACCESS_TOKEN=<token>`, `LINKEDIN_PERSON_ID=<person URN, optional>`

### 3. Facebook Page

| Step | Description |
|------|-------------|
| 1. Create App | [developers.facebook.com](https://developers.facebook.com) → Create App |
| 2. Add Login | Facebook Login, permissions `pages_manage_posts`, `pages_read_engagement` |
| 3. Page token | Graph API Explorer or OAuth → pick target Page → get **Page Access Token** |
| 4. Page ID | the Page's id |

- `.env`: `FACEBOOK_PAGE_ID=<page id>`, `FACEBOOK_ACCESS_TOKEN=<page access token>`

### 4. Instagram

| Step | Description |
|------|-------------|
| 1. Create App | Facebook Developers → add **Instagram** product (Instagram Graph API) |
| 2. Account | needs an Instagram **Business/Creator** account linked to a Facebook Page |
| 3. Review | `content_publish_scope` requires **App Review** (advanced access) |
| 4. Token + ID | get access token and Instagram user ID |

- `.env`: `INSTAGRAM_USER_ID=<ig user id>`, `INSTAGRAM_ACCESS_TOKEN=<token>`
- Note: also needs `image_url` when distributing (text-only not supported)

### 5. Threads

| Step | Description |
|------|-------------|
| 1. Create App | Facebook Developers → add **Threads** product |
| 2. OAuth | Threads API (Instagram Graph API family), Authorization Code flow |
| 3. Token | access token (60 days, refreshable) + user ID |

- `.env`: `THREADS_ACCESS_TOKEN=<token>`, `THREADS_USER_ID=<user id>`

### 6. Pinterest

| Step | Description |
|------|-------------|
| 1. Create App | [developers.pinterest.com](https://developers.pinterest.com) → Create App |
| 2. OAuth 2.0 | Authorization Code flow, scopes `pins:write`, `boards:read` |
| 3. Token | access token + a Board ID |

- `.env`: `PINTEREST_ACCESS_TOKEN=<token>`, `PINTEREST_BOARD_ID=<board id>`
- Note: needs `image_url` (text-only not supported)

### 7. YouTube

| Step | Description |
|------|-------------|
| 1. Google Cloud | [console.cloud.google.com](https://console.cloud.google.com) → create project |
| 2. Enable API | enable **YouTube Data API v3** |
| 3. OAuth 2.0 | create OAuth client, scopes `youtube.upload`, `youtube.readonly` |
| 4. Token | access token (~1h) + refresh token (permanent, for refresh) |

- `.env`: `YOUTUBE_ACCESS_TOKEN=<token>`
- Note: needs `video_file`; upload is chunked and not yet implemented

### 8. TikTok

| Step | Description |
|------|-------------|
| 1. Create App | [developers.tiktok.com](https://developers.tiktok.com) → Create App |
| 2. Product | **Content Posting API** (requires approval) |
| 3. OAuth 2.0 | scopes `video.upload`, `user.info.basic` |
| 4. Token | access token + open_id |

- `.env`: `TIKTOK_ACCESS_TOKEN=<token>`, `TIKTOK_OPEN_ID=<open id>`
- Note: needs `video_file`; upload not yet implemented

---

## Part 3 — Using after configuration

```bash
# See which channels are enabled
dirsubmit channels

# Distribute to configured channels (unconfigured are skipped)
dirsubmit distribute --tier auto
```

## Part 4 — Token expiry

| Channel | Token lifetime | Notes |
|---------|----------------|-------|
| X | 2 hours | needs refresh token |
| LinkedIn | 60 days | manually refreshable |
| Facebook/Instagram/Threads | 60 days | long-lived tokens extendable |
| Pinterest | long-lived | — |
| YouTube | 1 hour | refresh token is permanent |
| TikTok | 24 hours | refreshable |

`dirsubmit` reads static tokens; re-authorize and update `.env` when they expire. A `refresh` command can be added later.
