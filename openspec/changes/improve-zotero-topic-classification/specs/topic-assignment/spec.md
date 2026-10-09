## MODIFIED Requirements

### Requirement: Local topic assignment
The system SHALL 分别评估材料对象、AI方法、数据评测及科研软件维度，允许跨维度多标签，使用类别定义及有效参考证据，并为不确定内容拒绝细分类。无参考样本的已定义主题 SHALL 有冷启动候选路径及相应置信度标记。

#### Scenario: Independent facets
- **WHEN** 一篇公开摘要明确讨论MOF材料和机器学习势函数
- **THEN** 可同时得到材料对象及AI方法标签，一个维度的高分不挤掉另一个正确维度

#### Scenario: Empty collection examples
- **WHEN** 某主题定义明确但没有私有参考文献
- **THEN** 仍可从定义生成候选并标为definition-only，不能自动声明为已验证的高置信度分类

#### Scenario: Ambiguous leaf
- **WHEN** 父主题证据足够但多个子类无法可靠区分
- **THEN** 保留父主题并标为broad_only，不强行选子类

#### Scenario: Similarity prediction
- **WHEN** 公开条目有有效类别定义及参考证据
- **THEN** 分研究维度生成候选、按校准标准接受或拒绝细类，并生成有效祖先，不沿用旧版全局top-3阈值作为质量保证

### Requirement: Private reference boundary
The system SHALL 仅在受控采集进程内使用私有库文献和参考特征；不得将其写入公开归档、Actions artifacts、共享cache、日志或外部模型请求。公开解释 SHALL 仅来自公开输入和公开类别定义。

#### Scenario: Explain prediction
- **WHEN** 展示一条分类理由或导出运行收据
- **THEN** 不出现私有文献标题、collection key、词表或参考向量

#### Scenario: Serialization
- **WHEN** 写入公开index.json或构建artifact
- **THEN** 只序列化公开目录和公开条目的分类记录，禁止包含私有文献、collection key、词表或向量

## ADDED Requirements

### Requirement: Classification states and content facets
The system SHALL 独立记录研究范围、分类状态、内容性质和网站通用领域，并明确区分pending、低置信度、证据不足、目录缺口、父类回退及研究目录外。

#### Scenario: Organization news
- **WHEN** 内容仅描述银行部署Claude或企业合作而无科研任务证据
- **THEN** 可显示组织/工程动态标签，不能只凭agentic措辞标为自主科研系统

#### Scenario: Missing abstract
- **WHEN** 公开条目标题不足以细分类且摘要不可获取
- **THEN** 显示insufficient_evidence，保留原条目，区别于已判断为研究目录外

### Requirement: Versioned classification and precedence
The system SHALL 按人工覆盖、可信标准标识匹配、无冲突标题匹配、自动分类的优先级生成结果；影响分类的输入、配置、模型或规则变化 SHALL 触发可审计的重分类。

#### Scenario: Threshold or rule change
- **WHEN** 阈值、规范化规则、类别定义或模型revision改变
- **THEN** 受影响条目不能继续被旧缓存标为无需处理，diff可追溯到变更版本

#### Scenario: Conflicting exact identity
- **WHEN** 规范化标题相同但DOI/arXiv身份冲突
- **THEN** 不自动复制库内标签为可信精确匹配

### Requirement: Atomic classification publication
The system SHALL 在迁移或批量重分类失败时保留有效上一版，并保留公开条目身份、first_seen和人工修改。

#### Scenario: Invalid batch output
- **WHEN** 新归档含未知topic ID或迁移未完成
- **THEN** 不覆盖正式归档，可回滚到兼容的上一版manifest
