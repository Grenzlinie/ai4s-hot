> 2026-10-09 用户最新 annotation 选择：直接采用新版分类作为默认版本，不设置 opt-in/selector；取消大批人工 gold 的上线前置门槛。质量状态为 unmeasured，不宣称90%或其他准确率。人工标注、dev校准及holdout准确率保留为后续独立量化工作，不假称完成；技术、隐私、真实浏览器、runtime、原生Pages与回滚/HTTP验收仍须通过。

## Purpose
定义如何维护公开类别说明和人工纠错，使分类能够持续改善，同时保持静态网站、私有Zotero资料与普通访客之间的读写边界，避免把本机修正伪装为已同步到全站。

## ADDED Requirements

### Requirement: Topic definitions and provenance
The system SHALL 为可发布主题维护定义、同义词、纳入/排除规则、维度和定义版本，区分Zotero目录与网站扩展领域；不得自动修改Zotero结构。

#### Scenario: New topic definition
- **WHEN** 新增目录或维护者补充类别定义
- **THEN** 类别可被候选匹配，界面与收据能辨识其定义版本及来源

### Requirement: Local correction and reviewed import
The system SHALL 允许访客在本机纠正主题并导出仅含公开条目及主题ID的JSON，维护者可校验后提交为全站覆盖；前端不得获得GitHub/Zotero写凭据。

#### Scenario: Correction scope
- **WHEN** 普通访客保存一条修正
- **THEN** 立即在本机生效并明确本机范围，全站数据仅在维护者导入提交并发布后改变

#### Scenario: Invalid import
- **WHEN** 导入包含未知item/topic ID、冲突覆盖或私有字段
- **THEN** 拒绝该记录并报告原因，不静默加入正式覆盖文件

### Requirement: Override precedence and retention
The system SHALL 在自动重分类时保留有效人工覆盖，并对已删除主题或冲突定义产生待复核状态及历史记录。

#### Scenario: Reclassification after manual edit
- **WHEN** 自动模型重跑或目录节点被删除
- **THEN** 有效人工选择不被覆盖，删除目标的覆盖转为待复核而非静默丢失

### Requirement: Corrections are not accuracy certification
The system SHALL 在默认v2上线及维护者回滚时保留有效人工覆盖和本机纠错，并区分纠错记录与后续人工gold；本次直接采用新版不表示人工标注量化已完成。

#### Scenario: Correction during unmeasured deployment
- **WHEN** 用户在质量unmeasured的默认新版上纠错或维护者恢复上一版本
- **THEN** 明确本机和全站覆盖范围，保留可兼容纠错历史，不将修正数量当作分类准确率
