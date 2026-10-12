# 浏览器提交与 Computer Use 接管

自动化有六种模式。`auto` 只选择确定性的 headless/extension/CDP；不会在点击提交后自动换引擎重试。

| 模式 | 实际执行方式 | 登录与边界 |
| --- | --- | --- |
| headless | Playwright 无头 Chromium | 无需登录的食谱 |
| cdp | Playwright 连接已有 Chrome | 复用登录态，完成后保留浏览器和任务页面 |
| extension | 本地 Chrome 扩展 | 新建并绑定任务标签页，切换标签不会影响任务；文件上传需接管 |
| browser-use | Browser Use Agent，DOM + 视觉 | 连接已有 Chrome，识别入口、多步骤表单与 Google 登录 |
| computer-use | 外部电脑控制执行器，或生成 Codex 接管任务 | 原生弹窗、文件选择器、邮箱验证码等；CLI 本身不内置桌面视觉模型 |
| manual | 按产品隔离的粘贴清单 | 人工处理 |

## 安装与使用

```bash
pip install -e '.[dev]'
python -m playwright install chromium
# 下载不可用时自动尝试本机已安装 Chrome 的临时独立配置
# 也可用 DIRSUBMIT_BROWSER_EXECUTABLE 指定浏览器可执行文件
# Browser Use 额外要求 Python >=3.11；已按 0.13.11 的真实接口验证
pip install -e '.[browser-use]'

# 发现提交入口、可见字段、Google 按钮；全程只读
# Google 按钮可见 ≠ 已验证登录可用
 dirsubmit scout https://directory.example/submit --cdp-url http://localhost:9222

# 检查填表结果，保留真实 Chrome 页面
 dirsubmit --product products/a.yaml submit --mode cdp --fill-only

# AI 处理选择器漂移、入口发现、多步骤表单；需要 OPENAI_API_KEY
# 可设置 OPENAI_BASE_URL 和 DIRSUBMIT_AGENT_MODEL
 dirsubmit --product products/a.yaml submit --mode browser-use --only altern --max-steps 60

# Codex/电脑控制接管：生成完整产品、文案、食谱、任务 ID
 dirsubmit --product products/a.yaml submit --mode computer-use --only altern

# 也可连接自己的执行器；任务 JSON 从 stdin 输入，结果 JSON 从 stdout 输出
# 不经 shell 展开；执行器超时或中断后不会自动重新提交
 dirsubmit --product products/a.yaml submit --mode computer-use --computer-command 'python /absolute/path/executor.py'

 dirsubmit --product products/a.yaml report --out reports/a.json
```

批量运行三个产品：

```bash
dirsubmit batch products/botstest.yaml products/warmquant.yaml products/weworkbuddy.yaml --mode computer-use --only altern
```

多个产品使用不同 YAML，通过同一数据库分别执行即可。数据库键是产品 URL + 目录 slug，文案和提交结果互不覆盖。旧数据库记录迁移到空产品作用域并保留；无法推断原产品，因而不会自动把旧记录归到任意新产品。

## Computer Use 执行协议

Codex 读取 `runs/<slug>-<id>.json`，使用 Browser Use/Computer Use 观察页面并操作；Google 登录可复用浏览器。邮箱验证应在用户授权的邮箱里仅查找当前目录对应的验证码。密码、验证码、cookie 不写入结果或任务文件。

完成后保存结果 JSON：

```json
{
  "task_id": "任务 JSON 中的 id",
  "product_url": "https://product.example/",
  "directory": "altern",
  "status": "submitted",
  "note": "已提交，等待审核",
  "evidence_text": "页面实际显示的审核确认文本",
  "live_url": "https://directory.example/products/product"
}
```

```bash
dirsubmit resume --task runs/altern-ID.json --result /absolute/path/result.json
```

导入时匹配任务 ID、产品 URL 和目录。`submitted` 必须有确认文本；只填表任务不允许报告已提交。执行器的观察是执行器提供的证据，CLI 不独立审核其真实性。可同时保留截图辅助核验。

所有配置了 `success` 的食谱都需要结构化 `confirmation`：记录 `before`、`after` 页面观察及 `submit_click_count: 1`。页面观察含 `url` 和 `elements`，每个元素记录 `selector`、`count`、`visible`、`text`。初始 URL 必须是任务提交页，回执不能在提交前已经存在。旧食谱仍按 OR 匹配回执，`success.all_of` 要求全部条件同时成立。只有“已提交”的文字、直接打开感谢页或复制预期值，都不能替代实际观察。旧执行器如果只返回说明文字，会得到 `unverified`，需补齐真实观察，不会自动重投。

带 `pre_submit_checks` 的食谱另外需要 `pre_submit_observations`，按食谱顺序记录每个守卫的 `selector`、`count: 1` 和最后点击前实际读到的 `value`。未配置 `success` 和守卫的人工任务保留确认文本协议；不要将这种结果等同于 CLI 独立核实。

## 食谱增强

```json
{
  "slug": "example",
  "name": "Example",
  "tier": "semi",
  "requires_auth": true,
  "submit_url": "https://directory.example/submit",
  "auth": {"logged_in_selector": "[data-account-menu]"},
  "steps": [{"action": "click", "selector": "button[data-new-product]"}],
  "success": {"text": "Your product is awaiting review"},
  "submit_selector": "button[data-submit-product]",
  "fields": [{"name": "name", "source": "name", "required": true, "selectors": ["input[name=name]"]}]
}
```

`steps` 支持 click/fill/wait。`success` 支持可见 selector、text、url_contains，任一命中即确认；应使用提交后的专属信号。未配置成功信号的旧食谱只报告 `unverified`，不会把按钮点击当作成功。必填字段缺失、下拉选项不匹配、必需文件未上传时停止提交。Playwright 保存截图与结果 JSON；截图可能包含账号信息，`runs/` 默认不进入 Git。

新的 [Unloc 食谱](../recipes/unloc.json) 使用精确分类/定价映射、字段长度与姓名词数校验，并在最后点击前核对免费入口、空反垃圾字段及全部七个产品字段。其 `success.all_of` 要求感谢页 URL 和同一个可见 `main` 中的两段回执同时成立。产品 YAML 的 `submitter_name` 必须是实际获授权提交者，不能拿产品名或推测的创始人代替。

这些守卫由 headless/CDP 直接读取执行；Browser Use/Computer Use 执行器必须返回上述实际观察。当前 extension 模式缺少守卫与组合回执能力，因此会在操作前报告 `blocked`。WarmQuant 与 WeWorkBuddy 已通过原生电脑控制提交到 Unloc；新食谱只完成受控离线浏览器验证，尚未对真实站点通过 CLI 复投。不要使用 `--force` 重复提交已有申请。

状态：`filled`、`needs_auth`、`needs_handoff`、`blocked`、`unverified`、`submitted`、`approved`、`failed`。`submitted`、`approved`、`unverified` 自动跳过；不确定结果必须先检查页面与目录记录，再决定是否使用 `--force`。`--dry-run` 不访问浏览器、不改提交状态。

Browser Use 可识别 Google 或 GitHub 登录按钮，但不保证所有 OAuth/Cloudflare 流程可自动完成。当前产品的免费注册、常规登录、任务专属邮箱验证和常规条款已有用户授权，按 [AGENTS.md](../AGENTS.md) 复用，不重复请求。仅有隐私/条款链接的非约束性说明不等于实际接受协议；若执行工具在实际接受有约束力的协议、完成人机验证或扩展敏感权限时强制要求具体确认，仍遵守该要求。新密码的设置须由用户接管。不得付费或宣称绕过验证。没有连接的电脑执行器时，computer-use 生成任务，返回 needs_handoff，不能宣称自动完成。

## 2026-10-10 原生 Chrome 实测

重启后，原生 Chrome 控制已恢复，浏览器扩展控制此前的超时不再靠新建页面重试。整个投稿过程复用同一工作标签页；临时 Resource.fyi 标签页已关闭并核验剩余四个原有标签页。未读取浏览器配置、提取登录 cookie 或自动重复最终提交。

Resource.fyi 和 WhatLaunched.Today 分别通过现有 Chrome Google 会话完成一次登录，均只涉及姓名、头像和邮箱。两个站点分别复用登录完成三个产品的免费投稿。Resource.fyi 的三个账户条目及匿名公开产品页已核实批准；WhatLaunched.Today 的三个账户条目均为待审核。这是原生 CUA 现场执行结果，不代表已有通用 CLI 食谱能无人值守完成这两个站点。

WhatLaunched.Today 的实际路径是：选择 `Free Launch $0` → 填写产品信息 → 核对素材 → `Submit Product` 打开日期窗口 → 选择实际显示的免费日期 → 在第二个方案窗口核对 `$0` → 单次点击 `Continue — Free`。本次实际免费日期为 2026-12-09。素材页的 `Free for users` 表示产品有免费方案，不能据此判断目录投稿免费；WarmQuant 的描述同时说明每天十次免费生成及可选付费升级。

`/dashboard/submit/success?free=1` 和 `Launch submitted!` 都不足以单独确认投稿。点击最终按钮后进入 `My Products`，等待 `Fetching your launches…` 消失，再核对新增条目的产品名、tagline、独立编辑回执 UUID、审核状态和排期。三个产品依次使 `All` 和 `Pending` 从 0 增至 1、2、3，`Drafts` 始终为 0；因此计为三份已接收申请，不计为三份已批准收录。完整记录见 `runs/whatlaunched-native-confirmations-2026-10-10.json`，账户截图见 `runs/whatlaunched-three-native-proof-2026-10-10.jpg`。

原生下拉框或链接的 AX 点击有时只改变焦点。观察最新 AX 或截图后，使用键盘展开、激活链接，或点击截图里实际可见的按钮；不要沿用重置前的索引。素材预览也需要等待加载。WeWorkBuddy 的 PNG 经原生文件选择器上传，随后只读打开已提交条目的编辑页，确认正确图标、官方封面及正文确已保存；退出预览时未保存任何额外修改。最终提交响应不确定时保留发送记录并核验，不通过多次点击来试探。

macOS 原生文件选择器应分阶段操作：先用 `⌘⇧G` 打开 Go To，再读取新的 AX，定位实际 `PathTextField`，用 `setValue` 设置目标文件的完整路径。重新读取 AX，确认该字段的实际路径完全正确，才按 Return 进入文件选择。随后再次观察，核对选中的文件名及预览内容，再点击 Open 或按用于确认文件的 Return；返回网页后还要确认上传预览。本轮连续发送快捷键、粘贴和 Return 曾保持旧截图选择，最终通过分阶段 `setValue` 修正，未上传错误文件。

最终提交动作已发送后，按钮显示 `Saving…` 或 `Create` 进入 disabled 状态时，应等待并读取实际回执或新增账户记录。等待期间不得重复点击；响应仍不确定时保留已发送状态，先核验再决定后续处理。

关闭不用的临时标签页前，先读取当前页面，确认它确实空白或没有未提交的表单、草稿及上传内容；不要把等待回执的提交页当作空白页关闭。关闭后重新核对剩余标签页，只有观察确认后才记录清理完成。

DevHunt 也已通过现有 Google 会话登录，普通账户设置只补充了必填的公开 GitHub 资料链接。投稿前账户显示 `No launches yet`，站内名称和域名查询均未找到 Botstest。表单选择实际的 `Free` 产品定价、`AI` 与 `Helpers` 分类，上传官方图标和原生 Chrome 捕获的真实首页截图；第一条评论明确说明获得产品所有者授权，没有沿用默认创建者身份文案。

DevHunt 的 `Submit and pick a launch date` 只完成产品记录创建，随后仍有付费推介页。选择 `Keep my free spot`，等待账户列表加载，再核对新条目的名称、口号、分类、独立记录 ID 和排期。本次 Botstest 记录为 `33469716`，实际免费排期为 **2030-08-06**；不能沿用历史页面的预计等待时间。产品链接当时返回 404，匿名复核也为 404，但账户记录和只读编辑页均确认文案、图标与截图已保存。因此仅记录免费排队投稿，不宣称公开批准或有效公开外链。证据见 `runs/devhunt-botstest-native-confirmation-2026-10-10.json`。

原生控制短暂断开时，重新绑定当前 Chrome 应用并读取实际页面，表单仍完整；未新建标签页恢复连接。提交按钮响应延迟时，下一次观察才出现创建结果，期间没有重复点击。空文本框仍可能显示创建者占位提示；应核对实际 `Value`，或输入真实授权关系后再提交。自动审查拒绝的按钮操作没有执行，不能计为一次已发送投稿。

AlternativeTo 的 Google 和 GitHub 身份验证均可正常走完，权限分别为邮箱/公开资料、只读邮箱/资料，但两次站内返回均为 `account_not_linked`：邮箱已有账户，尚未关联这两种登录方式。不能将 OAuth 身份验证完成算成站内登录成功，更不能算成产品投稿。当前保留原账户登录页；没有输入密码、重置密码或提交产品。其免费审核及 WeWorkBuddy 的产品适配仍需进入真实投稿表单后核验，Botstest 和 WarmQuant 没有在此站尝试投稿。

Dynamite 的正常表单在一次 `Next` 后，只有官方客户端收到成功响应才进入 `Choose your plan` 并显示 `Your tool is in`。保存这个产品专属的状态，再激活 `Free $0` 的 `Continue for free`，核对最终回执；不能直接访问通用 `/success` 后计数。Botstest 和 WeWorkBuddy 本轮均已接收，公开目录暂未找到对应条目，仍记待审核。产品本身的价格与目录提交费用分别核对；WeWorkBuddy 有免费 Explorer 和尚未开放正式收费的 Creator 测试档，不能声称已有正式付费订阅。

Phyco 在 `Submit for review` 后先显示邮件确认要求，此时尚未进入审核队列。完成本次任务邮件中的确认后，实际页面显示 `Submission confirmed` 才记录审核队列已接收。如果用户在控制期间自行完成了邮件链接，先读取实际结果，避免再次发送表单或重复验证。邮箱只检索本次目的站和产品对应的邮件；保存前只提取本次回执文本，不保存完整收件箱或验证页 AX、邮箱截图、验证码或验证链接。地址栏显示可能省略参数，不能据此判断完整 AX 没有验证令牌。

2026-10-10 第 16 轮，WarmQuant 和 WeWorkBuddy 均通过这条原生流程完成任务邮件验证，实际进入 Phyco 审核队列。两份申请在最后步骤合并取得工具要求的具体条款确认；没有创建新账户或付款。产品定价字段按实际情况填写：WarmQuant 每天十次免费生成，WeWorkBuddy 的 Explorer 免费、Creator 尚处测试阶段。

WarmQuant 首次上传约 1.99 MB 的 PNG 素材后返回服务器错误。先检查本次产品邮件，确认未见回执；随后将原图无损编码为 WebP，总体积降至 915,204 字节，并逐像素核对解码后的 RGBA 完全一致。没有裁剪、缩放或修改截图内容。一次针对性重试获得邮件确认，最终仅计一份成功申请。这个实测不能证明服务器错误的具体原因，也不能把页面标注的单个文件上限当作整个请求的上限。错误、超时和等待邮件都是独立状态，不能当作成功或在原按钮仍禁用时重复发送。素材和尝试记录见 `runs/phyco-warmquant-native-intent-round16-2026-10-10.json`。

原生下拉框打开后的焦点或菜单高亮未必就是已提交的值。每次选择后重新读取实际 `Value`，核对分类、产品定价和受众，再进入下一步。标签输入须确认出现对应的删除标签按钮，表示标签已经提交，不能只核对仍留在输入框中的文本。

Forward Future 第 16 轮的正常表单只有收到服务端 `response.success` 才显示 `Tool submitted. We'll review it shortly.` 和 `Your submission is now under review.` 并清空表单。当前部署的公开 Server Action ID 已变，复用旧请求不可替代正常表单；本轮重新读取当前客户端后，通过原生九组字段表单提交 Botstest，并核实两条成功提示。实时预览卡、点击动作和原页面 URL 均不能单独计数。Botstest 按资源目录真实描述，适配依据是官方已经收录的同类发现目录，没有声称它自身执行模型推理。

原生工具报告用户切换了 Chrome 时，先重新观察实际活动页面，再决定操作。不要继续使用旧索引；可以在同一次调用中观察目标标签、切换、重新观察并定位按钮。浏览器扩展连接已超时则复用原生控制，不靠新建标签或窗口重试。关闭完成的页面前核对未发送内容，随后读取实际剩余标签。

较早一轮检查并关闭了已不用、没有未提交表单的 GitHub 插件说明页，当时原生 AX 核实 Chrome 工作窗口剩三个原有标签页。这个历史观察不能代表后续用户自行打开页面后的当前数量。第 16 轮只新增并复用一个工作标签，完成验证后核实关闭临时回执页和邮件工作页；最终当前窗口实际剩五个原有或用户页面：AlternativeTo 登录、Google Analytics、CherryQuant、Your Repositories、X。证据见 `runs/chrome-round16-cleanup-2026-10-10.json`，不据此推断其他 Chrome 窗口的页面数量。

## 已核验的公开匿名接口

电脑或浏览器连接不可用时，可对已经完成规则、字段、分类、查重和公开联系人审查的匿名表单，使用其官方页面客户端实际调用的公开提交接口。执行前重新读取当前表单配置，绑定产品、字段分组 ID、接口地址和完整请求；要求登录、验证码、未知字段、付款或新的明确协议确认时，保留任务等待对应条件满足。

AI Marketing Directory 的公开 Tally 表单已通过此流程提交 WarmQuant 和 WeWorkBuddy。执行脚本见 `runs/aimarketing-directory-official-api-submitter.py`，审计见 `runs/aimarketing-directory-official-api-workflow-audit.json`。使用官网公布的业务邮箱和公开 GitHub 专业展示名；每份请求为 `isCompleted: true`，服务端 HTTP 200 分别返回独立的 `submissionId` 和 `respondentId`，据此记录申请已接收、等待审核。该结果只证明接口接收申请。

脚本在请求前创建产品专属的发送记录，每个产品只发一次 POST。已有发送记录、超时或无法确认的响应都保留防重复状态。两个真实回执保存在 `runs/aimarketing-directory-confirmations.json`，并已同步到按产品隔离的数据库和主报告。这个站点专用流程没有接入通用 CLI 食谱，也不代表其他 Tally 表单已验证。自动审批拒绝的动作，应补充真实公开来源证据并交由同一审批重新审查，不能通过更换执行器绕过拒绝。

## CurlShip 免费目录 API

CurlShip 已接入 `distribute` 的目录 API 渠道，不使用浏览器食谱。注册目录 API 的同名旧浏览器食谱会从分发渠道中排除，避免重复执行或覆盖已有收录状态。产品 YAML 必须显式填写 `submitter_email`，其含义是已核实且获授权的提交邮箱；原有 `email` 仍是产品业务联系方式，不会作为替代值。此匿名接口无需 API key 或 Google/GitHub 登录，发送字段只有产品 HTTPS 首页 `url` 和提交邮箱 `email`，不提交付费档位或 AI 文案。

```yaml
email: support@product.example  # 产品业务联系方式
submitter_email: you@example.com  # 改为已核实且获授权的提交邮箱
```

先检查配置：

```bash
dirsubmit --product product.yaml distribute --only curlship.com --dry-run
```

这条仅选择目录 API 的命令不启动 LLM、Chrome 或扩展桥接器；`--dry-run` 不发网络请求、不写回执、不改提交记录。`--fill-only` 对所有 API 渠道也只返回预览，不发布、发送请求或覆盖已有记录；仅选择 API 预览时不启动 LLM 或桥接器。确认规则、授权、邮箱和查重条件后，移除 `--dry-run` 才执行真实免费提交：

```bash
dirsubmit --product product.yaml distribute --only curlship.com
```

真实提交先检查当前产品及主机大小写、前导 `www.` 别名的本地状态，再读取公开列表查重。别名保护会在数据库事务里再次核对，两个执行器即使都通过公开预检也只允许一次发送；原始产品 URL 和原有数据库记录保持不变。公开查重只匹配相同 hostname，并将一个前导 `www.` 视为同名；它不覆盖私有审核队列、同一注册根域下的其他子域或完整 eTLD 判断。公开列表不可完整核实时停止，不发送 POST。已存在公开匹配也只记录阻止重复，不声称本次新建成功。

发送前保存产品专属的防重复记录，每次最多一次 POST，不跟随重定向或自动重试。已有 `submitted`、`approved`、`unverified` 或持久化尝试回执都会跳过，`--force` 不绕过这个渠道的保护。超时、未知响应、HTTP 200/409 均不能代替新建回执；先核验已有记录，不通过重发探测结果。

精确 HTTP 201、独立正整数 ID、正确产品 URL 和免费档位只确认申请接收：数据库 `submitted`，清单等级 A。另一次匿名公开 GET 必须匹配同一 ID、产品 URL、免费档位及创建时的标题/描述，才记录 `approved`、等级 S。公开验证或回执保存失败时保留已确认接收和防重复状态，不再次 POST。回执只保存必要字段、响应哈希和核验结果，不保存邮箱值、验证码、登录凭证或原始响应正文。

2026-10-12，Botstest、WarmQuant 和 WeWorkBuddy 的三个实际 CurlShip 公开记录已单独核实并入库；对这三个产品再次运行真实命令会直接跳过，不能复投。可复用实现及验证见 [目录 API](../src/dirsubmit/directory_api.py) 与 `runs/round23-curlship-reusable-feature-root-applied-validation-2026-10-12.json`。CurlShip 返回的站点元数据不代表已上传人工稿件或图片。

已保存的产品状态可用 `dirsubmit --product product.yaml status --only curlship.com` 查看。对该 API 加 `--check` 仍只展示已有状态，并明确提示本次未重新核验、未请求 HTTP；不会调用通用浏览器食谱或创建新申请。

## 原生富文本与表单校验

富文本编辑器先关闭遮挡弹窗，确认目标正文获得焦点，再使用正常粘贴；进入 `Next` 前核对可见正文，随后观察正常校验结果。AX 设置值或预览变化可能没有同步到编辑器提交状态，不能仅凭这些变化宣称填写完成。

正常提交若明确返回 CSRF 校验拒绝，先核对当前登录状态，在同一会话重新打开官方表单，再从本地已审阅稿件恢复字段并按正常流程操作；不能仅凭拒绝提示推断具体原因。不要读取、修改隐藏令牌或直接拼请求绕过表单。按钮等待中或响应不确定时先核验回执，避免重复提交。

## 验证

测试包含真实 Chromium 的本地目录页面：必填项缺失、仅填表、单次提交、无确认提示和只读入口发现。扩展测试覆盖任务标签页固定、导航完成等待和仅点击一个 iframe；数据库覆盖旧记录迁移与产品隔离。

```bash
pytest -q
node tests/test_extension.cjs
```

审核状态核验要求明确配置 `search` 或 `url`，并在预期官方目录的公开页面找到产品的实际链接；相对链接按最终页面地址解析。`manual`、缺失和未知类型不请求页面。搜索框回显产品名、开放 PR、账户或登录页、提交回执，以及跳转产品自身主页，都不能作为批准证据。GitHub 的判断依据目录 slug 和实际 URL，不能依据执行 `tier`。

未发现合格公开链接时，`status --check` 保留原来的 `submitted` 或 `unverified`，不会改成可自动重提的状态，也不会改写原提交时间。这个通用检查只核实公开目录链接；GitHub 合并、产品页面的独立审核状态和历史发布总数仍需各站点单独核验。核验跳转到其他官方子域名时也会保留待核验状态，需要修正食谱或人工检查。
