## Purpose
为AI4S Hot的新摘要提供公开正文与Bohrium结构化补充，明确原文和推导知识之间的差别。通过持久预算、输入边界及故障降级，使每日自动采集可审计且不依赖单个提取服务。

## ADDED Requirements
### Requirement: Public first evidence
The system SHALL 对需要新摘要的公开记录优先提取正文；仅在公开提取失败、有明确DOI且配置允许时查询Bohrium，匹配DOI后保留节点类型；失败 SHALL 使用原始摘录继续运行。
#### Scenario: Direct success
- **WHEN** 公开HTML可提取
- **THEN** 摘要使用有界正文证据且不调用Bohrium
#### Scenario: Missing or failed fallback
- **WHEN** 无DOI、无凭据、无预算或Bohrium失败
- **THEN** 保留原摘录，摘要和归档流程继续

### Requirement: Persistent daily call limit
The system SHALL 在计费查询之前持久预留当日额度，跨同一天多次运行共享日上限；失败及未使用预留 SHALL 消耗额度，损坏预算 SHALL 禁止计费；额度未确认 SHALL 为0。
#### Scenario: Repeated failed requests
- **WHEN** 当天已达到配置上限或预算文件损坏
- **THEN** 后续运行不再执行任何Bohrium查询

### Requirement: Temporary evidence boundary
The system SHALL 仅把公开记录和提取证据传给摘要模型；公开归档 SHALL 只含短摘要与来源元数据，不包含全文、CLI账户信息、私密参考或认证信息。
#### Scenario: Graph summary
- **WHEN** 输入为Bohrium知识图谱
- **THEN** 模型收到图谱来源标记和节点类型，公开条目只保存摘要及依据标记

### Requirement: Configurable cloud execution
The system SHALL 支持本地YAML配置、Secret注入Bohrium凭据、固定CLI版本和公开提取运行上限；补充功能 SHALL 可关闭且不改变既有摘要、排序与分类。
#### Scenario: Disabled and retained summaries
- **WHEN** 关闭补充或条目已有摘要
- **THEN** 不发起补充查询且既有摘要保持不变
