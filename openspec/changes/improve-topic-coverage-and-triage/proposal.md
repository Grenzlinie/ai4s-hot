## Why

2026-10-26线上2282条归档有1621条无研究主题，其中1511条为期刊相关性待确认候选。摘要硬门槛、acquisition歧义和统计混用造成真实漏分与阅读误导。

## What Changes

- 修正收购/采集语境规则，避免科研论文被误判机构动态。
- 标题强证据可独立分主题，弱证据只退回有直接依据的父主题，不强塞细标签。
- 拆开相关性待确认与研究主题待分类；研究目录外内容依靠论文/模型/机构等内容类型浏览。
- 有界补全有材料AI标题线索的公开摘要，使用现有候选状态持久退避，不新增LLM或Bohrium调用。
- v2.5规则版本使历史记录重新分类；现有人工覆盖、稳定ID、私有参考边界保持。

## Capabilities

### New Capabilities
- `classification-recovery`: 语境修复、标题分类、分流计数及候选摘要恢复。

### Modified Capabilities

无，补充已有本地分类和期刊契约。

## Impact

Python分类/期刊采集、静态前端、公开来源计数、Actions触发路径及OpenSpec。免费公开metadata有每次HTTP预算与持久失败退避。原付费模型/Bohrium预算不变，分类质量保持unmeasured。
