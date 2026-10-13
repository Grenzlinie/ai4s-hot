## Context

现有网站以公开元数据归档、私有本地主题分类、受限摘要和静态浏览工作。研究验证10/10官方RSS及Crossref可用，但30篇小样本中Crossref仅15篇有摘要；不能把缺摘要当作不相关。Nature、Science包含跨学科和非研究内容，硬件面向AI也不等于AI用于材料。

## Goals / Non-Goals

目标：指定10刊每日发现、按期刊浏览并纳入现有主题；可审查的相关/待确认状态、DOI稳定身份和单来源故障隔离。
非目标：全文订阅破解、穷尽全球材料期刊、重建个性化系统、声称分类准确率已测量。

## Decisions

1. site/journals.json 是公开期刊注册表：固定ID、规范标题、ISSNs、官方RSS。10刊包括 Nature Materials、Nature、Science、Nature Communications、Science Advances、Advanced Materials、Advanced Energy Materials、Advanced Functional Materials、Acta Materialia、Matter。
2. 官方RSS全部候选先读取，Crossref按ISSN与indexed overlap发现补充。初始14天、重叠3天，分页有界；达到上限公开partial而不宣称完整。发布日期用online优先、print次之；indexed和first_seen独立保存。
3. DOI规范化用于RSS/API重复合并；保留已有文章ID和首次发现时间。没有显式DOI关联时不按相似标题强合并arXiv。
4. 规则需要材料研究对象和AI方法/材料任务证据。明确材料用于AI硬件、社论/更正/新闻不直接进入相关流；缺摘要或歧义归pending。规则结果不等于人工准确率。独立测试覆盖边界和失效场景。
5. state保存公开候选元数据和计数；相关/待确认进入index。变为excluded的旧候选退出期刊流；其它来源已收录文章保留自身身份和来源。状态仅在整体分类与归档校验成功后持久化。单刊失败保留之前结果，其余期刊继续更新。
6. 新root journals，以及item journal_id/title/issns/publisher/doi/日期/journal_relevance均受公开schema约束。候选state不随Pages复制；所有外发摘要仍仅公开材料，待确认不消耗摘要/正文补全预算。
7. UI独立多选期刊chips+搜索对话框，期刊内OR、维度间AND。保留URL、推荐/最新/收藏与主题。默认隐藏待确认，显式入口可查看。旧归档无新字段仍兼容。保留现有视觉风格及无个人库叙述。

## Risks / Trade-offs

- 规则筛选可能漏召回或误判：待确认与公开理由保留可审查边界，后续可用独立标注量化；本次不宣称质量达标。
- 供应商阻断/延迟和分页上限：公开partial/error、日期溯源、缓存保留，独立期刊互不阻断。
- 初始候选较多：有界增量、DOI缓存，待确认默认隐藏且不摘要；无逐篇全文请求。

## Migration Plan

新字段全部向后兼容；先离线独立测试，再真实公开源采集、浏览器检验，推送main触发Actions并核验manifest及线上数据。回滚代码到上一提交、保留有效归档；旧UI忽略新增字段，已有书签ID保持。正式主spec同步在所有验收证据齐全后。

## Open Questions

无阻塞项。准确率测量和是否加入LLM歧义复核属于后续质量改进，本次使用可解释规则与待确认路径。
