# Content Distribution Map (Publishing Map)

> One piece of content → auto-rewrite → auto-distribute across Blog / Social / Video / Community / Directory / Launch channels.
> Organized by automation level: **Automated (API + browser)** / **Semi-automated** / **Manual**.

---

## Three tiers at a glance

| Tier | Criteria | dirsubmit mode |
|------|----------|----------------|
| 🤖 **Automated** | Official API, or browser auto-fills forms with an account already logged in — fully unattended | `distribute --tier auto` |
| 🔧 **Semi-automated** | Auto-fills forms / generates content, but needs a human for captcha/confirm, or review | `distribute --tier semi` |
| 👤 **Manual** | Editorial review / community rules / paid / PR; content quality decides | `distribute --tier manual` (drafts + cheatsheets) |

---

## 1. 🤖 Automated tier (API + browser)

### A. API-native publishing (official API, 100% automated)

**Blog / long-form:**

| Platform | API | Notes |
|----------|-----|-------|
| DEV.to | ✅ Forem API | create/update/draft; top choice for developer cold-start |
| WordPress | ✅ REST API | universal, agent-friendly |
| Ghost | ✅ Admin API | nearly all admin capabilities exposed |
| Hashnode | ✅ GraphQL | developer community |
| Blogger | ✅ Blogger API | old but stable |
| Static (Hugo/Jekyll) | Git | `git commit` = publish |

**Social / messaging:**

| Platform | API | Content |
|----------|-----|---------|
| X / Twitter | ✅ `/2/tweets` | text/image/video/thread (pay-per-use) |
| LinkedIn | ✅ | post/image/video/part of Article |
| Facebook Page | ✅ | text/image/video/link |
| Instagram | ✅ Content Publishing | image/carousel/reel/story (needs review) |
| Threads | ✅ Meta Graph | text/image |
| Bluesky | ✅ AT Protocol | post/image/thread |
| Mastodon | ✅ | post/media |
| Pinterest | ✅ | pin |
| Telegram | ✅ Bot API | channel/group |
| Discord | ✅ Webhook/Bot | channel |
| Slack | ✅ Webhook | channel |

**Video:**

| Platform | API | Notes |
|----------|-----|-------|
| YouTube | ✅ `videos.insert` | upload + title + description + tags + scheduled |
| TikTok | ✅ (reviewed) | needs account type + OAuth |

### B. Browser agent (no public Submit API, CDP fills forms after login)

**AI directories:** Futurepedia, FutureTools, There's An AI For That, SaaSHub, AI Tool Hunt, OpenTools, AI Scout, AI Depot, etc.

**Launch platforms (forms auto-fill, some have review queues):** Uneed, Microlaunch, DevHunt, BetaPage, Launching Next, etc.

> ⚠️ Verified in practice: Toolify ($99) and TopAI.tools ($47/$229) moved to paid → manual tier. SaaSHub blocks disposable emails.

---

## 2. 🔧 Semi-automated tier (auto-fill forms + partial human)

| Platform | Bottleneck | How far it automates |
|----------|-----------|---------------------|
| Product Hunt | community rules + maker background + launch-day engagement | AI copy + pre-filled form, human decides publish |
| BetaList | editorial review queue | same |
| altern.ai | Google/GitHub OAuth | form auto-fills after login, occasional captcha |
| insidr.ai and similar | reCAPTCHA | form auto-fills, human clicks captcha once |
| Medium | legacy API (no new tokens) | browser automation + human confirm |
| Substack | no public publish API | browser automation + human confirm |
| heavy Cloudflare sites | occasional challenges | human takeover |

**Principle**: AI generates → human confirms → publish, rather than unattended mass-posting.

---

## 3. 👤 Manual tier (account won't help; content quality decides)

### Editorial review / content quality

| Platform | Notes |
|----------|-------|
| G2 / Capterra / GetApp | Gartner family, enterprise account + multi-step verification |
| SourceForge | description quality + review |
| AlternativeTo | community voting, description must be genuine |
| Crunchbase | company profile written by hand |
| StackShare | real engineering data required |
| Clutch | paid + client-interview verification |
| Trustpilot | domain/business verification |

### Paid / business

| Platform | Notes |
|----------|-------|
| AppSumo | $299+ + deal negotiation |
| Toolify / TopAI | $47–$229 paid listing |
| PitchGround / Dealify / StackSocial | lifetime-deal business deals |

### Community / anti-self-promotion

| Platform | Notes |
|----------|-------|
| Hacker News (Show HN) | anti-self-promotion, needs human judgment |
| Reddit | requires user authorization; mass-posting kills accounts |
| Indie Hackers | needs real posts + engagement |
| Lobsters | strict community rules |

### Media / PR

TechCrunch, The Verge, VentureBeat, Hackernoon, e27, etc. — contact editors, not self-serve.

---

## Distribution matrix

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

## Three publisher types

| Publisher | Coverage | Examples |
|-----------|----------|----------|
| **API Publisher** | official API channels | X, YouTube, DEV, Telegram |
| **Browser Agent** | directories/communities without API | Futurepedia, Product Hunt, SaaSHub |
| **Git Publisher** | static sites / open source | Hugo, Jekyll, GitHub |

---

## V1 priority — 25 channels

**API layer:** X, LinkedIn, DEV, WordPress, Ghost, YouTube, Bluesky, Telegram, Discord, Slack

**Browser layer:** Product Hunt, BetaList, Futurepedia, FutureTools, There's An AI For That, SaaSHub, AlternativeTo, Uneed, Microlaunch, rundown.ai

**Manual (drafts):** Reddit, Hacker News, Indie Hackers, G2, Capterra
