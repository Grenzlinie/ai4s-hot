## Why

AI4S Hot 目前缺少按顶级材料期刊连续发现论文的入口。通用来源每批截取12条，不能满足大期刊先完整发现候选、再筛选材料AI研究的需求。

## What Changes

- 用官方RSS和按ISSN限定的Crossref增量采集10本指定期刊，保留DOI、期刊与日期元数据。
- 将AI用于材料研究的相关候选纳入既有主题分类；证据不足的候选进入待确认，明确区分材料用于AI硬件。
- 增加独立期刊多选维度，与研究主题、来源、内容类型、推荐/最新/收藏组合。
- 使用可持续的候选状态、错误保留和有界请求；公开归档不包含秘密或个人库内容。

## Capabilities

### New Capabilities
- `journal-watch`: 10刊增量采集、相关性筛选、DOI去重和故障保留。
- `journal-explorer`: 独立期刊筛选与统一研究主题浏览。

### Modified Capabilities

无。已有分类、摘要和归档契约继续适用。

## Impact

涉及 site/journals.py、期刊配置、collect/schema、静态页面和Actions。复用已有Python依赖，后端仍在GitHub Actions运行、前端仍在Pages。新增筛选使用本地规则，准确率未校准；不引入额外LLM或Bohrium计费调用，相关条目的摘要沿用已有总预算。
