## Context

基线code431b938、2026-10-26公开archive869d4c。1621条无topic包含1526信息不足、56低置信度、39scope_rule无主题。14篇type=paper因acquisition科学用法被误判。相关性pending与主题标签独立，目录外机构/模型信息不该加入研究待分队列。

## Decisions

1. Contextual organization evidence: acquisition function/data acquisition/information acquisition不等于企业收购。paper身份优先，除非明确机构事件语境；保留真实收购/合作/任命识别。
2. 缺摘要也评估标题直接命中的公开定义短语；只接受title命中的主题，不借私有相似度猜测。叶不足可在公开材料/AI等根主题有明确依据时回退。理由注明依据标题。普通弱标题仍保留证据不足，不把未量化当已准确。
3. 分类器版本v2.5重算历史；不修改参考库、身份盐、书签ID或人工覆盖。每条content_kind供基础浏览，研究主题是独立、更细维度。
4. 相关性待确认入口只看journal.pending；研究主题待分类排除journal.pending与non_research，用有效主题标签判断。current/all使用相同队列定义并各自应用相应筛选，旧URL兼容并避免互相矛盾条件。
5. 新journal_metadata模块只补缺摘要、有材料AI线索的候选：公开Crossref单DOI/OpenAlex DOI查询/白名单出版社公开摘要，验证DOI与文章身份，拒反爬和元信息冒充摘要。有界20 HTTP请求/10候选每次，成功归档后当日累计最多20请求；失败重跑仍受单轮20限制但可能重复免费请求。失败退避1/3/7天，state内记录尝试时间和来源。不用LLM/Bohrium。
6. 补全在分类和首次index校验之前，之后重做相关性判定/计数，再统一分类。整体成功才写state/index；已有relevant不因暂时没有正文掉回pending。
7. UI不把机构动态显示为待分类；展示真实content_kind。补全文本仅公开摘要，不复制网页全文、密钥或账户信息；候选缓存仍不发Pages。

## Validation and release

独立agent单测、旧回归、相同冻结公开快照前后分类变化/样本检查、免费实时补全、真实本机/线上Chrome和Actions manifest。数量提升只证明覆盖变化，不证明人工准确率。发布失败保留有效快照。回滚上一code+有效archive，现有schema2字段保持兼容。
