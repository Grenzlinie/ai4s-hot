# topic-assignment

## Purpose
记录现有精确标题与 TF-IDF 相似度分类及私有数据边界；现有阈值属于实现基线，尚无人工质量验收，不能宣称已达到准确率要求。

## Requirements

### Requirement: Local topic assignment
The system SHALL 在采集进程内使用库内分类文献的标题和摘要建立 TF-IDF 主题特征，以规范化标题匹配或相似度给公开条目附加主题及祖先。

#### Scenario: Similarity prediction
- **WHEN** 公开条目有可匹配的主题参考特征
- **THEN** 选取相似度至少为 max(0.15, 最佳分数×0.85) 的至多三个候选主题并附加祖先

### Requirement: Private reference boundary
The system SHALL 将库内条目、collection key 和参考向量保留在进程内存，公开归档仅包含允许公开的目录及公开条目的匹配结果。

#### Scenario: Serialization
- **WHEN** 写入网站 index.json
- **THEN** 不包含私有参考文献、词表或参考向量，原有摘要服务只接收公开标题和摘录
