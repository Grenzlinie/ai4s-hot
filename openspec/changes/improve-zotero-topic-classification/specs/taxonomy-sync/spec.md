> 2026-10-09 用户最新 annotation 选择：直接采用新版分类作为默认版本，不设置 opt-in/selector；取消大批人工 gold 的上线前置门槛。质量状态为 unmeasured，不宣称90%或其他准确率。人工标注、dev校准及holdout准确率保留为后续独立量化工作，不假称完成；技术、隐私、真实浏览器、runtime、原生Pages与回滚/HTTP验收仍须通过。

## MODIFIED Requirements

### Requirement: Collection projection
The system SHALL 将允许发布的 Zotero collections 投影为稳定公共主题身份，保留名称和父子层级，排除00待确认子树，且不得公开collection key或身份盐。重命名和移动 SHALL 保持公共ID不变。

#### Scenario: Rename and reparent
- **WHEN** 同一collection被重命名或移动到另一父目录
- **THEN** 公共ID保持不变，展示路径与父节点更新，原有条目标签和人工覆盖仍有效

#### Scenario: Unselected root appears
- **WHEN** 同步发现不在发布范围的新根目录
- **THEN** 不自动公开该根目录及其子树，现有已发布目录正常更新

#### Scenario: Nested collection projection
- **WHEN** 读取到允许发布的父子目录与00待确认子树
- **THEN** 保留允许目录的父子关系并排除待确认子树，公共树不包含collection key

### Requirement: Retain taxonomy on failure
The system SHALL 在读取失败、目录循环或身份映射冲突时保留最后有效目录和已有分类，公开标明stale及最近成功时间；不得将失效同步当作空目录覆盖归档。

#### Scenario: Invalid tree
- **WHEN** 新快照含循环关系或不可唯一迁移的身份
- **THEN** 受影响变更不进入正式目录，产生可复核报告并保留最后有效版本

#### Scenario: Read failure
- **WHEN** Zotero读取抛出异常且存在已发布目录
- **THEN** 保留旧目录和最近成功时间、显示stale，不公开异常原文

## ADDED Requirements

### Requirement: Topic identity migration
The system SHALL 为旧公共ID提供明确别名和迁移结果，保留删除节点的历史状态，保持公开条目ID及first_seen不变。

#### Scenario: Old URL and retired topic
- **WHEN** 用户访问旧主题ID或一个已删除的主题
- **THEN** 唯一旧ID映射到新ID；删除主题显示已归档状态及历史内容，不猜测另一个同名主题

### Requirement: Daily default taxonomy retention
The system SHALL 在默认v2每日更新中保留有效目录与分类快照，记录最近成功时间，并保持上一有效版本可恢复；新版直接采用不放宽私有身份边界。

#### Scenario: Daily sync failure after adoption
- **WHEN** 默认v2上线后的每日目录读取或迁移失败
- **THEN** 不把有效目录覆盖为空，最近有效快照继续可读且失败状态可辨识，collection key和身份盐仍不公开
