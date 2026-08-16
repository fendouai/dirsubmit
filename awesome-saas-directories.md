# Awesome SaaS Directories — 按自动化程度分类

> 一份按「提交自动化程度」分类的 SaaS / AI 产品目录清单。
> 数据来源：`mezmer90/saas-directories`（921 目录）、`xioanchin/awesome-launch-platforms`、
> 以及 `dirsubmit` 工具实测（headless + CDP + 邮箱）。

## 分类标准

| 档位 | 判据 | 对应工具模式 |
|------|------|-------------|
| 🤖 **全自动** | 无需登录/邮箱，纯表单；或 GitHub PR 可脚本化；无人工审核门槛 | `dirsubmit submit --tier auto`（headless） |
| 🔧 **半自动** | 需账号（邮箱/OAuth），但登录态可复用、表单可自动填；人只需登录一次+偶发验证码 | `dirsubmit submit --tier semi --mode cdp` |
| 👤 **全人工** | 编辑审核/付费/社区规则/媒体投稿，内容质量决定成败，无法脚本替代 | `dirsubmit gen` 生成文案 + 人工提交 |

> 实测提醒：2026 年「免费无登录」目录长尾大多已死/付费化；临时邮箱（如 mail.tm）被主流目录拉黑。
> 半自动档的可行前提是**复用你自己的真实账号登录态**，不是临时邮箱自动注册。

---

## 🤖 全自动（无需登录，脚本可完成）

| 目录 | DR | 链接 | 说明 |
|------|----|------|------|
| The Rundown / Supertools | 38 | https://www.rundown.ai/submit | ✅ 已实测：免费无登录 Tally 表单，可直接填表提交 |
| Open SaaS Directory | — | https://opensaas.directory | 开源目录，GitHub PR 即可，可脚本化 |
| Public APIs | 60 | https://publicapis.io | 开源 API 列表，GitHub PR |
| API List | — | https://apilist.fun | 开源 API 列表，GitHub PR |
| Open Alternative | 51 | https://openalternative.co | 开源替代品目录，GitHub PR |
| BuiltWith | — | https://builtwith.com | 自动探测站点技术栈，**无需提交** |

> 说明：真正的「全自动」极少。除 rundown.ai 外，其余都是 GitHub-PR 型开源目录（`dirsubmit` 可扩展 `git` 提交模式）。

---

## 🔧 半自动（需账号，CDP 复用登录态 + 自动填表）

### 高价值（DR ≥ 60，优先）

| 目录 | DR | 链接 | 提交/注册方式 |
|------|----|------|--------------|
| There's An AI For That | 77 | https://theresanaiforthat.com | 邮箱注册 + 表单 |
| SaaSHub | 76 | https://www.saashub.com/submit | 邮箱注册（实测临时邮箱被拉黑，需真实邮箱） |
| Toolpilot | 76 | https://www.toolpilot.ai | 邮箱注册 |
| BetaList | 74 | https://betalist.com/submit | 账号 + 审核（付费加急） |
| F6S | 73 | https://www.f6s.com | 邮箱注册 |
| Dang AI | 80 | https://dang.ai | 邮箱登录 |
| Twelve Tools | 79 | https://twelvetools.io | 表单 |
| Turbo0 | 78 | https://turbo0.com | 表单 |
| findly.tools | 75 | https://findly.tools | 表单 |
| Toolify.ai | 72 | https://www.toolify.ai/submit | 付费（$99） |
| Futurepedia | 69 | https://www.futurepedia.io/submit-tool | 邮箱+手机号注册 |
| Future Tools | 68 | https://futuretools.io | 邮箱提交 |
| PeerPush | 71 | https://peerpush.net | 账号 |
| Peerlist | 75 | https://peerlist.io | 账号 |
| Startup Stash | 65 | https://startupstash.com | 表单 |
| Software Suggest | 65 | https://www.softwaresuggest.com | 企业信息核实 |
| SaaSWorthy | 72 | https://saasworthy.com | 账号 + 审核 |

### 中长尾（DR 40–60，量大可批量）

| 目录 | DR | 链接 |
|------|----|------|
| MicroLaunch | 58 | https://microlaunch.net |
| BetaPage | 58 | https://betapage.co |
| altern.ai | 45 | https://altern.ai/submit（Google/GitHub OAuth） |
| Launching Next | 50 | https://www.launchingnext.com |
| SideProjectors | 69 | https://www.sideprojectors.com |
| StartupBase | 39 | https://startupbase.io |
| Fazier | 80 | https://fazier.com |
| Killer Startups | 62 | https://www.killerstartups.com |
| Aura++ | 62 | https://auraplusplus.com |
| TinyLaunch | 71 | https://tinylaunch.com |
| magicbox.tools | 72 | https://magicbox.tools |
| SubmitAiTools | 73 | https://submitaitools.com |
| DevHunt | 59 | https://devhunt.org |
| Openhunts | 50 | https://openhunts.com |
| Open Launch | 60 | https://openlaunch.io |
| Launch Vault | 45 | https://launchvault.com |
| StartupLister | 34 | https://startuplister.com |
| Prefundia | 42 | https://prefundia.com |
| SaaSList | 38 | https://saaslist.com |
| SaaSpo | 42 | https://saaspo.com |
| Huzzler | 46 | https://huzzler.com |
| IndieHub | 39 | https://indiehub.io |
| SaaS Place | 25 | https://saasplace.com |
| SaaS Projects | 28 | https://saasprojects.io |

---

## 👤 全人工（编辑审核 / 付费 / 社区 / 媒体）

### 必做高价值（DR 高，值得手写文案）

| 目录 | DR | 链接 | 为什么必须人工 |
|------|----|------|---------------|
| Product Hunt | 91 | https://www.producthunt.com | 社区强规则、maker 背景、独特文案 |
| Hacker News (Show HN) | 91 | https://news.ycombinator.com | 反自推广、需真人判断内容价值 |
| Reddit (r/SaaS 等) | 95 | https://www.reddit.com | 社区规则严格，纯推广会被删 |
| Indie Hackers | 80 | https://www.indiehackers.com | 社区、需真人发帖互动 |
| G2 | 65 | https://www.g2.com | 企业账号 + 产品核实 + 审核 |
| Capterra | 90 | https://www.capterra.com | 同 G2（Gartner 系） |
| GetApp | 76 | https://www.getapp.com | 同 G2 系 |
| SourceForge | 92 | https://sourceforge.net | 项目描述 + 审核 |
| AlternativeTo | 79 | https://alternativeto.net | 社区投票、需真实描述 |
| Trustpilot | 93 | https://www.trustpilot.com | 域名/企业验证 |
| Crunchbase | 89 | https://www.crunchbase.com | 企业档案需人工撰写 |
| Clutch | 79 | https://clutch.co | 付费 + 客户验证 + 访谈 |
| AppSumo | 76 | https://appsumo.com | 付费 $299+ + 商务谈判 |
| AngelList / Wellfound | 87 | https://wellfound.com | 面向投资人，高质量档案 |

### 媒体 / PR（需联系编辑，非自助提交）

| 媒体 | DR |
|------|----|
| TechCrunch | 92 |
| The Verge | 92 |
| CNET / Mashable / Business Insider | 92 |
| VentureBeat / Fast Company / PC Mag | 89–91 |
| Hackernoon / DEV Community | 82–90 |
| Slashdot / GeekWire / The Next Web | 82–89 |
| e27 / Tech In Asia / EU-Startups | 72–75 |

### 其它需人工的目录

| 目录 | DR | 说明 |
|------|----|------|
| StackShare | 80 | 技术栈展示，需真实工程信息 |
| GoodFirms | — | 企业信息核实 |
| CrozDesk | 55 | B2B 审核 |
| FinancesOnline | 82 | 编辑评测 |
| Software Advice / Trust Radius | 79/76 | B2B 审核 |
| StartupBlink | — | 需审核 |
| Land-book | 63 | 编辑精选画廊 |
| Techjury | — | 编辑写评测文章 |
| Starter Story | 71 | 需真实创业故事投稿 |
| IndieProducts.io | — | 社区投稿 |

---

## 使用建议

1. **先跑全自动**（rundown.ai + 开源目录 PR），半小时拿到第一批外链。
2. **半自动批量**：用 `dirsubmit` + CDP 复用真实账号，从高 DR 目录（There's An AI、SaaSHub、BetaList）开始。
3. **全人工重点投入**：Product Hunt、G2、Capterra、AppSumo 这 4 个值得手写差异化文案。
4. **媒体/PR**：产品有新闻点（融资、里程碑）时再联系，冷启动阶段 ROI 低。

## 数据出处

- [mezmer90/saas-directories](https://github.com/mezmer90/saas-directories) — 921 目录 + DR
- [xioanchin/awesome-launch-platforms](https://github.com/xioanchin/awesome-launch-platforms) — 100+ 平台详情
- [dirsubmit](https://github.com/fendouai/submit-saas-directories) — 本仓库实测分类
