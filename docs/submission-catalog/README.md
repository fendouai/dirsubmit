# 三类产品提交清单

[打开本地筛选页](index.html)。可按类别、产品、S/A/B/C/D/U 级别和名称筛选；默认每页 100 个目标，也可以显示全部。不需要安装依赖、启动服务或联网加载数据。

更新于 2026-10-20T07:45:53.372152+00:00。三类结果独立统计：

- 目录：1837 个候选，208 份已确认申请，其中 32 个公开条目已核实。
- GitHub：80 个仓库，46 个独立 PR，覆盖 60 条产品记录；公开合并条目 6。
- 投稿：83 个候选，实际邮件投递 27 份，官方周刊 Issue 投稿 6 份，编辑确认回复 0，公开刊登 0。

邮件发出或周刊 Issue 创建仅证明已投递，不表示编辑确认收到、不表示采用，也不表示公开刊登。公开可读的自荐 Issue 是稿件回执，不能算周刊刊发。目录审核收件、PR 创建与稿件投递不能混成同一种编辑确认。

| 类别 | 完整列表 | 机器可读记录 |
|---|---|---|
| 目录站与导航站 | [directories.md](directories.md) | [directories.json](directories.json) |
| GitHub awesome 仓库 | [awesome-repositories.md](awesome-repositories.md) | [awesome-repositories.json](awesome-repositories.json) |
| 博客、网站与新闻投稿 | [editorial-outlets.md](editorial-outlets.md) | [editorial-outlets.json](editorial-outlets.json) |

每个目标分别记录 Botstest、WarmQuant、WeWorkBuddy 的状态、原因、证据、来源、回执链接和下一动作。U 不代表已尝试；B 不代表已提交；A 表示已确认提交、投递或开放 PR，审核与采用待定；S 表示已核实公开结果。发出提示、任务查询和唯一任务行数量为最小邮件凭证，不复制邮箱正文或预览。

## 更新真实结果

三个原始来源文件保留在 `runs/category{1,2,3}-*-universe-2026-10-10.json`。基础预期目标数保持：目录站与导航站 1835、GitHub awesome 仓库 70、博客、网站与新闻投稿 66。生成器先验证基础快照数量及身份，再读取独立增量来源 [additional-targets.json](additional-targets.json)，追加已保留官方证据和调查文件哈希的新目标；本次增量：目录站与导航站 2、GitHub awesome 仓库 10、博客、网站与新闻投稿 17。类别必须有效、同一类别的目标身份不能重复、每个目标必须提供三个产品结果。不要为扩大清单或更新状态修改原始快照和基础预期数量。

基础来源、增量来源及其 SHA-256 分开记录在输出 JSON 和 [generation-validation.json](generation-validation.json) 中；基础预期与合并后的实际数量分别校验。目标合并后再依次应用 [actual-result-overrides.json](actual-result-overrides.json) 的 `overrides` 数组。增量文件中的 B/C 是准备或条件状态，实际投递仍须取得回执后逐产品覆写为 A/S。

覆写记录示例：

```json
{
  "category": "awesome-repositories",
  "target_key": "techiediaries/awesome-technical-writing-blogging-resources",
  "product": "warmquant",
  "grade": "A",
  "state": "confirmed_open_PR",
  "reason": "已创建并通过官方公开 API 核实；等待维护者审核。",
  "receipt_links": ["https://github.com/techiediaries/Awesome-Technical-Writing-Blogging-Resources/pull/1"],
  "evidence": ["runs/github-techiediaries-warmquant-public-confirmation-2026-10-10.json"],
  "next_action": "等待审核，不重复提交。"
}
```

`category` 取三个列表的文件名，`target_key` 取对应 JSON 中的键，`product` 取 `botstest`、`warmquant`、`weworkbuddy`。同一产品目标追加多条记录时，后面的字段依次生效，已有回执和证据去重保留；其他产品不受影响。只有实际提交、投递、开放 PR 或公开结果可以升级至 A/S。不要保存验证码、凭证或无关邮件内容。

在仓库根目录执行：

```sh
python3 docs/submission-catalog/generate_catalog.py
```

脚本只使用 Python 标准库，输出三个 JSON、三个 Markdown、嵌入数据的 `index.html`、本说明和 [generation-validation.json](generation-validation.json)。已存在的真实结果覆写文件不会被重置，Store、主报告、AGENTS.md 和三个原始快照不会被修改。
