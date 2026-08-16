# 各渠道凭证配置指南

> 每个渠道怎么拿凭证、填到哪个环境变量（`.env`）。
> 分两类：**零门槛（直接拿 key/token）** 和 **OAuth（需走授权流程）**。
>
> ⚠️ 重要：OAuth 渠道的 access token 大多**会过期**（短则 1 小时，长则 60 天）。
> `dirsubmit` 当前直接读静态 token；过期后需重新授权刷新。后面可加 token 自动刷新。

---

## 一、零门槛渠道（几分钟搞定，直接拿 key/token）

### 1. Telegram
- 打开 Telegram，搜索 `@BotFather` → 发 `/newbot` → 起名 → 得到 **Bot Token**
- 给你的 bot 发一条消息，然后用 `@userinfobot` 或调用 `getUpdates` 拿到 **Chat ID**
- `.env`：
  ```
  TELEGRAM_BOT_TOKEN=<bot token>
  TELEGRAM_CHAT_ID=<chat id>
  ```

### 2. Discord
- 服务器设置 → 整合（Integrations）→ Webhooks → **New Webhook** → 选频道 → 复制 Webhook URL
- `.env`：
  ```
  DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
  ```

### 3. Slack
- [api.slack.com](https://api.slack.com) → Create App → From scratch
- 打开 **Incoming Webhooks** → 授权到目标频道 → 复制 Webhook URL
- `.env`：
  ```
  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
  ```

### 4. DEV.to
- [dev.to/settings/extensions](https://dev.to/settings/extensions) → DEV Community API Keys → Generate
- `.env`：
  ```
  DEVTO_API_KEY=<api key>
  ```

### 5. Bluesky
- [bsky.app](https://bsky.app) → 设置 → **App Passwords** → Add App Password（生成「应用密码」，**不是**登录密码）
- `.env`：
  ```
  BLUESKY_HANDLE=yourhandle.bsky.social
  BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
  ```

### 6. Mastodon
- 你的实例 → 偏好设置 → 开发（Development）→ 新建应用 → 勾选 `write` 权限 → 得到 **Access Token**
- `.env`：
  ```
  MASTODON_INSTANCE=https://mastodon.social
  MASTODON_ACCESS_TOKEN=<access token>
  ```

### 7. WordPress
- WP 后台 → 用户 → 个人资料 → 拉到「应用程序密码（Application Passwords）」→ 添加新密码
- `.env`：
  ```
  WORDPRESS_URL=https://yourblog.com
  WORDPRESS_USERNAME=admin
  WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx
  ```

### 8. Ghost
- Ghost 后台 → 设置 → 集成 → 自定义集成（Custom Integration）→ 添加
- 得到 **Admin API Key**（格式 `id:secret`）
- `.env`：
  ```
  GHOST_ADMIN_URL=https://yourblog.com
  GHOST_ADMIN_KEY=<id>:<secret>
  ```

### 9. Hashnode
- [hashnode.com](https://hashnode.com) → 设置 → Developer → **Personal Access Token** → Generate
- `.env`：
  ```
  HASHNODE_TOKEN=<pat>
  HASHNODE_PUBLICATION_ID=<可选，指定 publication>
  ```

---

## 二、OAuth 渠道（需走授权流程，token 会过期）

### 1. X / Twitter

| 步骤 | 说明 |
|------|------|
| 1. 注册开发者 | [developer.x.com](https://developer.x.com) → 创建项目 + App |
| 2. 选认证方式 | OAuth 2.0（推荐，`/2/tweets` 用 Bearer token） |
| 3. 授权码流程 | 拿 `client_id`/`client_secret` → 走 Authorization Code flow，scope 用 `tweet.write tweet.read users.read` |
| 4. 拿 token | 得到 access token（默认 2 小时过期，需 refresh token） |

- **注意**：X API 已商业化（pay-per-use），免费档基本只能读，发帖需付费订阅。
- `.env`：`X_ACCESS_TOKEN=<access token>`

### 2. LinkedIn

| 步骤 | 说明 |
|------|------|
| 1. 创建 App | [linkedin.com/developers](https://www.linkedin.com/developers) → Create App |
| 2. 加 Product | 勾选 **Share on LinkedIn** |
| 3. OAuth 2.0 | Authorization Code flow，scope `w_member_social` |
| 4. 拿 token | access token（60 天有效） |

- `.env`：`LINKEDIN_ACCESS_TOKEN=<token>`、`LINKEDIN_PERSON_ID=<你的 person URN，可选>`

### 3. Facebook Page

| 步骤 | 说明 |
|------|------|
| 1. 创建 App | [developers.facebook.com](https://developers.facebook.com) → Create App |
| 2. 加 Login | 添加 Facebook Login，权限 `pages_manage_posts`、`pages_read_engagement` |
| 3. 拿 Page Token | Graph API Explorer 或 OAuth 流程，选目标 Page → 得到 **Page Access Token** |
| 4. 拿 Page ID | Page 的 id |

- `.env`：`FACEBOOK_PAGE_ID=<page id>`、`FACEBOOK_ACCESS_TOKEN=<page access token>`

### 4. Instagram

| 步骤 | 说明 |
|------|------|
| 1. 创建 App | Facebook Developers → 添加 **Instagram** 产品（Instagram Graph API） |
| 2. 账号要求 | 需 Instagram **Business/Creator** 账号，并关联 Facebook Page |
| 3. 权限审核 | `content_publish_scope` 需 **App Review** 通过（advanced access） |
| 4. 拿 token + ID | 得到 access token 和 Instagram 用户 ID |

- `.env`：`INSTAGRAM_USER_ID=<ig user id>`、`INSTAGRAM_ACCESS_TOKEN=<token>`
- 注意：还需在 `distribute` 时提供 `image_url`（纯文本不支持）

### 5. Threads

| 步骤 | 说明 |
|------|------|
| 1. 创建 App | Facebook Developers → 添加 **Threads** 产品 |
| 2. OAuth | Threads API（Instagram Graph API 家族），Authorization Code flow |
| 3. 拿 token | access token（60 天，可刷新）+ user ID |

- `.env`：`THREADS_ACCESS_TOKEN=<token>`、`THREADS_USER_ID=<user id>`

### 6. Pinterest

| 步骤 | 说明 |
|------|------|
| 1. 创建 App | [developers.pinterest.com](https://developers.pinterest.com) → Create App |
| 2. OAuth 2.0 | Authorization Code flow，scope `pins:write`、`boards:read` |
| 3. 拿 token | access token + 选一个 Board ID |

- `.env`：`PINTEREST_ACCESS_TOKEN=<token>`、`PINTEREST_BOARD_ID=<board id>`
- 注意：需提供 `image_url`（纯文本不支持）

### 7. YouTube

| 步骤 | 说明 |
|------|------|
| 1. Google Cloud | [console.cloud.google.com](https://console.cloud.google.com) → 创建项目 |
| 2. 启用 API | 启用 **YouTube Data API v3** |
| 3. OAuth 2.0 | 创建 OAuth 客户端，scope `youtube.upload`、`youtube.readonly` |
| 4. 拿 token | access token（1 小时）+ refresh token（永久，用于刷新） |

- `.env`：`YOUTUBE_ACCESS_TOKEN=<token>`
- 注意：需提供 `video_file`；且上传要分块，`dirsubmit` 当前待实现

### 8. TikTok

| 步骤 | 说明 |
|------|------|
| 1. 创建 App | [developers.tiktok.com](https://developers.tiktok.com) → Create App |
| 2. 选产品 | **Content Posting API**（需提交审核） |
| 3. OAuth 2.0 | scope `video.upload`、`user.info.basic` |
| 4. 拿 token | access token + open_id |

- `.env`：`TIKTOK_ACCESS_TOKEN=<token>`、`TIKTOK_OPEN_ID=<open id>`
- 注意：需提供 `video_file`；上传待实现

---

## 三、配置后的使用

```bash
# 查看哪些渠道已启用
dirsubmit channels

# 分发到已配置的渠道（未配置的自动跳过）
dirsubmit distribute --tier auto
```

## 四、关于 token 过期

| 渠道 | token 有效期 | 说明 |
|------|-------------|------|
| X | 2 小时 | 需 refresh token |
| LinkedIn | 60 天 | 可手动刷新 |
| Facebook/Instagram/Threads | 60 天 | 长生命周期 token 可续 |
| Pinterest | 长期 | — |
| YouTube | 1 小时 | refresh token 永久 |
| TikTok | 24 小时 | 可刷新 |

`dirsubmit` 当前读静态 token，过期后需重新授权并更新 `.env`。后续可加 `refresh` 命令自动续期。
