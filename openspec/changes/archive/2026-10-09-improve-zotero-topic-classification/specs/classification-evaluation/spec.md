> 2026-10-09 用户最新 annotation 选择：直接采用新版分类作为默认版本，不设置 opt-in/selector；取消大批人工 gold 的上线前置门槛。质量状态为 unmeasured，不宣称90%或其他准确率。人工标注、dev校准及holdout准确率保留为后续独立量化工作，不假称完成；技术、隐私、真实浏览器、runtime、原生Pages与回滚/HTTP验收仍须通过。

## Purpose
定义默认新版发布所需的技术、隐私、性能与真实运行证据，并保留后续独立人工标签质量和无泄漏评估，确保目录匹配覆盖、代码执行成功和分类准确性不会混为一个指标，并支持后续变更比较和回滚。

## ADDED Requirements

### Requirement: Frozen labeled evaluation
The system SHALL 保留人工标签与冻结评估工具，在后续独立量化工作使用冻结的公开真实条目人工标签集评估自动分类；人工gold完成不作为2026-10-09用户选择的默认v2发布前置条件。量化评估 SHALL 按canonical item identity隔离开发和留出集，并将留出条目从参考示例、人工override与规则调参输入中排除；审查过或用于定义/回归的样本及其同源组 SHALL 固定为开发资料。

#### Scenario: Duplicate across sources
- **WHEN** 同一论文由arXiv与alphaXiv重复出现或已有Zotero收藏
- **THEN** 标准身份只进入一个split，exact-seen样本单独报告，不进入unseen自动分类主指标

### Requirement: Faceted quality receipt
The system SHALL 报告有效分母、支持数、逐维度precision/recall/F1、研究范围误入率、合格内容覆盖、拒判原因及不确定性，未标注样本不能当作预测正确或错误。细类计分 SHALL 排除展示祖先，明确仅父类样本与可接受替代集合的计分，并独立验收内容性质和网站领域标签。

#### Scenario: No gold labels
- **WHEN** 默认v2已通过技术门禁但尚无冻结人工标签
- **THEN** 可以依用户选择发布默认新版，但质量标为unmeasured，只报告运行与匹配统计，不能给出真实准确率或宣称90%等质量目标已满足

### Requirement: Release gates
The system SHALL 依2026-10-09用户最新annotation直接采用默认v2，并以隐私、迁移、公开契约、独立逻辑回归、真实浏览器、所启用后端runner性能、原生Pages及回滚/HTTP门禁决定上线；缺失技术证据时保留最后有效版本，不只凭单元测试发布。人工gold、dev校准和holdout精度为后续独立量化，不阻塞本次上线，不设置opt-in selector。

#### Scenario: Default adoption without measured accuracy
- **WHEN** 技术门禁已通过而人工质量尚未量化
- **THEN** 默认页面直接使用v2并显示未量化说明，保留回滚版本，不将覆盖率当作precision

#### Scenario: Later quality target failure
- **WHEN** 后续独立量化发现precision或组织新闻误入率未达到目标
- **THEN** 如实记录失败指标和diff用于修订，不宣称目标已满足；是否调整或回滚由维护者依据证据决定

### Requirement: Reproducible runtime and rollback
The system SHALL 保存模型/配置/代码与archive版本、runner环境、冷启动与更新耗时、RSS和真实Pages读回证据，并能恢复兼容上一版及用户本机状态。

#### Scenario: Runtime or deployment failure
- **WHEN** 语义后端超预算或新归档部署失败
- **THEN** 不宣称该模式已通过，保留上一版并展示degraded状态或执行回滚

### Requirement: Daily update failure retention
The system SHALL 每日更新默认v2分类，失败时保留最后有效公开快照与最近成功时间；维护者 SHALL 能恢复兼容上一版而不重新生成付费摘要或丢失本机阅读状态。

#### Scenario: Failed daily classification
- **WHEN** 每日分类、目录同步或构建失败且已有有效快照
- **THEN** 不覆盖为空数据，公开可辨识stale/最近成功时间，最后有效版本保持可读并可维护者回滚
