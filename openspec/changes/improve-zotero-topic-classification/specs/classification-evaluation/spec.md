## Purpose
定义主题分类发布前必须具备的人工标签质量、无泄漏评估、性能与真实运行证据，确保目录匹配覆盖、代码执行成功和分类准确性不会混为一个指标，并支持后续变更比较和回滚。

## ADDED Requirements

### Requirement: Frozen labeled evaluation
The system SHALL 使用冻结的公开真实条目人工标签集评估自动分类，按canonical item identity隔离开发和留出集，并将留出条目从参考示例、人工override与规则调参输入中排除；审查过或用于定义/回归的样本及其同源组 SHALL 固定为开发资料。

#### Scenario: Duplicate across sources
- **WHEN** 同一论文由arXiv与alphaXiv重复出现或已有Zotero收藏
- **THEN** 标准身份只进入一个split，exact-seen样本单独报告，不进入unseen自动分类主指标

### Requirement: Faceted quality receipt
The system SHALL 报告有效分母、支持数、逐维度precision/recall/F1、研究范围误入率、合格内容覆盖、拒判原因及不确定性，未标注样本不能当作预测正确或错误。细类计分 SHALL 排除展示祖先，明确仅父类样本与可接受替代集合的计分，并独立验收内容性质和网站领域标签。

#### Scenario: No gold labels
- **WHEN** 只有88条运行记录而尚无冻结人工标签
- **THEN** 只能报告56条匹配和32条未分类，不能给出分类准确率或宣称达到质量门槛

### Requirement: Release gates
The system SHALL 根据冻结evaluation-plan的质量、隐私、迁移、可访问性及runner性能门槛决定是否发布，失败时保持现有正式版本，不能只凭单元测试成功切换分类器。

#### Scenario: High coverage with wrong labels
- **WHEN** 新分类器提高覆盖但precision低于门槛或组织新闻误入率超限
- **THEN** 不切为默认，并保存失败指标和diff用于下一轮修订

### Requirement: Reproducible runtime and rollback
The system SHALL 保存模型/配置/代码与archive版本、runner环境、冷启动与更新耗时、RSS和真实Pages读回证据，并能恢复兼容上一版及用户本机状态。

#### Scenario: Runtime or deployment failure
- **WHEN** 语义后端超预算或新归档部署失败
- **THEN** 不宣称该模式已通过，保留上一版并展示degraded状态或执行回滚
