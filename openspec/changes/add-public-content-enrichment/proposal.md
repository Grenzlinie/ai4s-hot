## Why
现有摘要主要依赖摘要或RSS摘录，缺少公开正文上下文。实测证明公开HTML与Bohrium LKM可提供不同层次的补充证据，需要正式连接到摘要流程。

## What Changes
- 公开HTML优先提取，失败后按DOI获取LKM结构化知识，保留来源区别。
- 本地配置开关、内容长度、超时和每日Bohrium调用上限；额度在持久分支记录，失败也消耗预算。
- 临时证据仅参与摘要，公开归档只包含来源标记、短摘要及统计。
- Actions固定版本安装CLI，凭据经Secret注入；缺凭据或额度时继续旧摘录。

## Capabilities
### New Capabilities
- `content-enrichment`: 公开证据提取、Bohrium回退、持久预算和摘要来源契约。
### Modified Capabilities
无。

## Impact
site/collect.py、site/topics_schema.py、新enrichment模块、配置脚本、Actions。仅对需要新摘要的公开记录生效，已有摘要不批量重写；不改变主题分类和排序。每日付费额度须由用户明确决定；未确认时为0。
