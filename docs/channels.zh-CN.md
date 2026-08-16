# 渠道

`dirsubmit` 如何把内容分发到各渠道、三层模型，以及每个渠道的凭证获取方式。

## 三层模型

| 层次 | 方法 | 行为 | dirsubmit |
|------|------|------|-----------|
| `auto` | 官方 API + 无头浏览器 | 全自动，无人值守 | `distribute --tier auto` |
| `semi` | CDP 浏览器（复用登录态） | 自动填表，偶发验证码需人工点一下 | `distribute --tier semi --mode cdp` |
| `manual` | 草稿/清单生成 | 生成适配文案，人肉发布 | `distribute --tier manual` |

## 渠道清单

### API 渠道（18 个 — `tier: auto`）

| 渠道 | 分类 | 凭证（环境变量） |
|------|------|-----------------|
| DEV.to | 博客 | `DEVTO_API_KEY` |
| WordPress | 博客 | `WORDPRESS_URL`、`WORDPRESS_USERNAME`、`WORDPRESS_APP_PASSWORD` |
| Ghost | 博客 | `GHOST_ADMIN_URL`、`GHOST_ADMIN_KEY` |
| Hashnode | 博客 | `HASHNODE_TOKEN`（+ 可选 `HASHNODE_PUBLICATION_ID`） |
| X / Twitter | 社交 | `X_ACCESS_TOKEN` |
| LinkedIn | 社交 | `LINKEDIN_ACCESS_TOKEN`（+ 可选 `LINKEDIN_PERSON_ID`） |
| Facebook Page | 社交 | `FACEBOOK_PAGE_ID`、`FACEBOOK_ACCESS_TOKEN` |
| Threads | 社交 | `THREADS_ACCESS_TOKEN`、`THREADS_USER_ID` |
| Bluesky | 社交 | `BLUESKY_HANDLE`、`BLUESKY_APP_PASSWORD` |
| Mastodon | 社交 | `MASTODON_INSTANCE`、`MASTODON_ACCESS_TOKEN` |
| Telegram | 社交 | `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` |
| Discord | 社区 | `DISCORD_WEBHOOK_URL` |
| Slack | 社区 | `SLACK_WEBHOOK_URL` |
| 通用 Webhook | 社交 | `WEBHOOK_URL` |
| Instagram | 社交（图片） | `INSTAGRAM_USER_ID`、`INSTAGRAM_ACCESS_TOKEN` + `image_url` |
| Pinterest | 社交（图片） | `PINTEREST_ACCESS_TOKEN`、`PINTEREST_BOARD_ID` + `image_url` |
| YouTube | 视频 | `YOUTUBE_ACCESS_TOKEN` + `video_file`（上传待实现） |
| TikTok | 视频 | `TIKTOK_ACCESS_TOKEN`、`TIKTOK_OPEN_ID` + `video_file`（上传待实现） |

### 浏览器渠道（目录 — 来自 `recipes/*.json`）

每个目录食谱有 `tier`：`auto`（无登录表单）、`semi`（需账号，CDP）、`manual`（编辑审核）。

### 纯人工渠道（8 个 — `tier: manual`，仅生成草稿）

Reddit · Hacker News · Indie Hackers · Lobsters · Medium · Substack · Capterra · AppSumo。

## 凭证检测

每个 API 渠道声明必需的 env 变量。没配的渠道**自动禁用**并被跳过：

```bash
dirsubmit channels              # 显示启用/禁用 + 缺哪些变量
dirsubmit distribute --tier auto   # 自动跳过禁用渠道
```

填好凭证即自动启用，无需改代码。

## 获取凭证

### 零门槛（直接拿 key/token，无需 OAuth）

| 渠道 | 去哪 | 拿到什么 |
|------|------|---------|
| Telegram | 找 `@BotFather` 发 `/newbot` | bot token；再用 `@userinfobot` 拿 chat id |
| Discord | 服务器设置 → 整合 → Webhooks | webhook URL |
| Slack | api.slack.com → Create App → Incoming Webhooks | webhook URL |
| DEV.to | dev.to/settings/extensions | API key |
| Bluesky | bsky.app → 设置 → App Passwords | 应用密码（**不是**登录密码） |
| Mastodon | 你的实例 → 偏好 → 开发 → 新建应用 | access token（勾 `write`） |
| WordPress | 用户 → 个人资料 → 应用程序密码 | app password |
| Ghost | 设置 → 集成 → 自定义集成 | Admin API Key（`id:secret`） |
| Hashnode | 设置 → Developer | personal access token |

### OAuth（需授权流程，token 会过期）

| 渠道 | 门户 | 流程 / scope |
|------|------|-------------|
| X / Twitter | developer.x.com | OAuth 2.0，`tweet.write tweet.read`；已商业化 |
| LinkedIn | linkedin.com/developers | OAuth 2.0，`w_member_social` |
| Facebook | developers.facebook.com | Login + `pages_manage_posts` → Page access token |
| Instagram | developers.facebook.com → Instagram | Graph API + App Review（`content_publish_scope`） |
| Threads | developers.facebook.com → Threads | Threads API，授权码 |
| Pinterest | developers.pinterest.com | OAuth 2.0，`pins:write` |
| YouTube | console.cloud.google.com | OAuth 2.0，`youtube.upload` |
| TikTok | developers.tiktok.com | Content Posting API，`video.upload` |

每个 OAuth 渠道的逐步申请步骤：见 [`channel-oauth-setup.zh-CN.md`](channel-oauth-setup.zh-CN.md)。

> **token 过期**：OAuth access token 会过期（YouTube ~1 小时、X ~2 小时、TikTok ~24 小时、LinkedIn/Facebook/Instagram/Threads ~60 天）。`dirsubmit` 当前读静态 token，过期后需重新授权。

## 分发矩阵

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

## 添加渠道或目录

- **新增 API 渠道** — 在 `src/dirsubmit/channels.py` 的 `API_CHANNELS` 加条目，在 `api.py` 的 `REQUIREMENTS` 加凭证声明并写一个 handler。
- **新增目录** — 往 `recipes/` 丢一个 JSON（格式见 [配置](configuration.zh-CN.md)）。
- **新增纯人工渠道** — 在 `channels.py` 的 `MANUAL_CHANNELS` 加条目。
