# 内容分发地图（Publishing Map）

> 一份内容 → 自动改写 → 自动分发到 Blog / Social / Video / Community / Directory / Launch 平台。
> 按「自动化程度」分三层：**自动化层（API + 浏览器）** / **半自动化层** / **纯人工层**。

---

## 三层总览

| 层次 | 判据 | dirsubmit 模式 |
|------|------|---------------|
| 🤖 **自动化层** | 官方 API 直接发，或账号已登录后浏览器自动填表提交，全程无人值守 | `distribute --tier auto` |
| 🔧 **半自动化层** | 能自动填表单/生成内容，但提交时需人工点验证码/确认，或需人工审核 | `distribute --tier semi` |
| 👤 **纯人工层** | 编辑审核/社区规则/付费/PR，内容质量定成败，账号无用 | `distribute --tier manual`（生成草稿+清单） |

---

## 一、🤖 自动化层（API + 浏览器）

### A. API 原生发布（官方 API，100% 全自动）

**博客 / 长文：**

| 平台 | API | 说明 |
|------|-----|------|
| DEV.to | ✅ Forem API | 建/改/草稿全支持，开发者冷启动首选 |
| WordPress | ✅ REST API | 万能，Agent 直接发 |
| Ghost | ✅ Admin API | 后台能力几乎全暴露 |
| Hashnode | ✅ GraphQL | 开发者社区 |
| Blogger | ✅ Blogger API | 老但稳 |
| 静态站 (Hugo/Jekyll) | Git | `git commit` 即发布 |

**社交 / 消息：**

| 平台 | API | 内容 |
|------|-----|------|
| X / Twitter | ✅ `/2/tweets` | 文本/图/视频/thread（pay-per-use） |
| LinkedIn | ✅ | Post/图/视频/Article 部分 |
| Facebook Page | ✅ | 文本/图/视频/链接 |
| Instagram | ✅ Content Publishing | 图/carousel/reel/story（需权限审核） |
| Threads | ✅ Meta Graph | 文本/图 |
| Bluesky | ✅ AT Protocol | Post/图/thread |
| Mastodon | ✅ | Post/media |
| Pinterest | ✅ | Pin |
| Telegram | ✅ Bot API | Channel/Group |
| Discord | ✅ Webhook/Bot | Channel |
| Slack | ✅ Webhook | Channel |

**视频：**

| 平台 | API | 说明 |
|------|-----|------|
| YouTube | ✅ `videos.insert` | 上传+标题+描述+tags+定时 |
| TikTok | ✅（有审核） | 需账号类型+OAuth |

### B. 浏览器 Agent（无公开 Submit API，账号已登录后 CDP 填表）

**AI 目录：** Futurepedia、FutureTools、There's An AI For That、SaaSHub、AI Tool Hunt、OpenTools、AI Scout、AI Depot 等。

**Launch 平台（表单可自动填，部分有审核队列）：** Uneed、Microlaunch、DevHunt、BetaPage、Launching Next 等。

> ⚠️ 实测：Toolify（$99）、TopAI.tools（$47/$229）已转付费，归入纯人工层。SaaSHub 拉黑临时邮箱，需真实邮箱。

---

## 二、🔧 半自动化层（自动填表单 + 部分人工）

| 平台 | 卡点 | 自动化到什么程度 |
|------|------|-----------------|
| Product Hunt | 社区规则 + maker 背景 + 上线日互动 | AI 生成文案+预填表单，人拍板发布 |
| BetaList | 编辑审核队列 | 同上 |
| altern.ai | Google/GitHub OAuth | 登录后表单自动填，偶发验证码 |
| insidr.ai 等 | reCAPTCHA | 表单自动填，人点一次验证码 |
| Medium | Legacy API 不再发新 token | 需浏览器自动化 + 人工确认 |
| Substack | 无公开发布 API | 浏览器自动化 + 人工确认 |
| 强 Cloudflare 防护站 | 偶发人机校验 | 需人接管 |

**设计原则**：AI 生成 → 用户确认 → 发布，而不是无人值守狂发。

---

## 三、👤 纯人工层（账号无用，内容质量定成败）

### 编辑审核 / 内容质量

| 平台 | 说明 |
|------|------|
| G2 / Capterra / GetApp | Gartner 系，企业账号 + 多步核验 |
| SourceForge | 项目描述质量 + 审核 |
| AlternativeTo | 社区投票制，描述需真实 |
| Crunchbase | 公司档案人工撰写 |
| StackShare | 技术栈信息需真实工程数据 |
| Clutch | 付费 + 客户访谈验证 |
| Trustpilot | 域名/企业验证 |

### 付费 / 商务

| 平台 | 说明 |
|------|------|
| AppSumo | $299+ + 折扣方案谈判 |
| Toolify / TopAI | $47–$229 付费 listing |
| PitchGround / Dealify / StackSocial | 终身 deal 商务合作 |

### 社区 / 反自推广

| 平台 | 说明 |
|------|------|
| Hacker News (Show HN) | 反自推广，需真人判断 |
| Reddit | 强制用户授权，狂发废号 |
| Indie Hackers | 需真人发帖 + 互动 |
| Lobsters | 社区规则严格 |

### 媒体 / PR

TechCrunch、The Verge、VentureBeat、Hackernoon、e27 等——需联系编辑。

---

## 分发矩阵

```
                Internet Distribution
                        │
     ┌──────────────────┼──────────────────┐
     │                  │                  │
   Blog               Social             Video
  DEV/WordPress      X/LinkedIn         YouTube
  Ghost/Hashnode     Instagram          TikTok
                     Threads/Bluesky
                        │
     ┌──────────────────┼──────────────────┐
     │                  │                  │
 Communities        Directories         Launch
 Reddit/HN         Futurepedia          Product Hunt
 Indie Hackers     TAAFT/SaaSHub        BetaList
 GitHub            AlternativeTo        Microlaunch
```

## 三种发布器

| 发布器 | 覆盖 | 例子 |
|--------|------|------|
| **API Publisher** | 官方 API 渠道 | X、YouTube、DEV、Telegram |
| **Browser Agent** | 无 API 的目录/社区 | Futurepedia、Product Hunt、SaaSHub |
| **Git Publisher** | 静态站/开源 | Hugo、Jekyll、GitHub |

---

## V1 优先 25 渠道

**API 层**：X、LinkedIn、DEV、WordPress、Ghost、YouTube、Bluesky、Telegram、Discord、Slack

**浏览器层**：Product Hunt、BetaList、Futurepedia、FutureTools、There's An AI For That、SaaSHub、AlternativeTo、Uneed、Microlaunch、rundown.ai

**纯人工（生成草稿）**：Reddit、Hacker News、Indie Hackers、G2、Capterra
