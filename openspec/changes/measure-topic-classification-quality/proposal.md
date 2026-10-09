# Why

2026-10-09用户明确选择“直接采用新版”，并选择稍后确认人工标注。默认v2的技术发布与真实分类质量量化因此分开验收：已有标注、预测和评分工具，但人工gold仍为0，当前质量必须保持unmeasured。将原改进change的Deferred measurement 8.1–8.5交给独立change，保留可审计的数据、分母和目标，防止延期工作随技术发布归档而丢失。

# What Changes

- 独立承接人工gold、冻结分组split/泄漏审查、同输入v1基线、仅dev校准和独立holdout验收五项工作；所有执行任务保持未勾选。
- 固定现有106条dev和122条未见holdout候选的来源与hash，候选标签不算gold；先由用户稍后组织人工阅读、复核和确认，再运行真实质量验收。
- 保留根precision、细类P/R/F1、相对基线改进、非研究误入、覆盖率、内容性质/领域和父类过度细分的独立分母与目标。
- 保留隐私、标准身份排除、配置冻结、预测收据绑定和留出错误隔离。质量目标不追溯成为默认v2发布硬门槛，不自动修改生产阈值或模型。

# Capabilities

## New Capabilities

无。

## Modified Capabilities

- `classification-evaluation`: 在已实现的评估工具和发布契约上，增加独立人工gold、分组冻结、基线校准及留出质量测量的具体验收要求；delta只ADDED新增要求，不覆盖已有技术发布规则。

# Impact

依赖[原分类改进change](../archive/2026-10-09-improve-zotero-topic-classification/proposal.md)及其[evaluation-plan](../archive/2026-10-09-improve-zotero-topic-classification/evaluation-plan.md)。使用现有`site/topics/evaluation/`和`scripts/{prepare_annotation,review_annotation,predict_evaluation,run_evaluation}.py`，本次仅建立规划，不改代码、不运行真实holdout预测、不标注或宣称测得质量。原change任务8继续未完成并链接本change；本change的全部测量任务需要后续人工gold及独立评估执行。
