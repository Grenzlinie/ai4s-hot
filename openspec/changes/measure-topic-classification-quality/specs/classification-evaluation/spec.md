## ADDED Requirements

### Requirement: Human-confirmed gold provenance

评估系统 SHALL 只接受阅读公开材料并经人工独立复核的gold，保存reviewer、ISO时间、公开理由及冲突定稿记录；AI标签只能是候选。SHALL 标注研究范围、四研究维度、内容性质、通用领域、状态及可接受标签集合。fine_applicable=false SHALL 仅用于research+broad_only且有父类；非研究和必须拒判者fine_applicable=true、gold空集；证据不足、目录缺口和required_abstain SHALL 不带研究gold标签。

#### Scenario: User confirms later

- **WHEN** 用户2026-10-09选择稍后标注、当前候选尚未人工确认
- **THEN** gold数量保持真实值0，质量状态unmeasured，测量任务不得标完成，也不阻塞已授权默认v2技术发布

#### Scenario: Candidate cannot masquerade as gold

- **WHEN** 标签仅由AI生成或缺人工复核记录，或非研究条目试图排除fine计分
- **THEN** 质量验收拒绝该gold，不通过自动填充补齐

### Requirement: Frozen grouped holdout and leakage isolation

评估系统 SHALL 保留全部106条已审查dev，满足总公开样本≥148、dev≥88、未见holdout≥60，holdout四root各≥10阳性和非研究/组织动态≥20；SHALL 按标准DOI、显式arXiv、规范URL及标题别名归组，版本/转载同组，已用于audit/定义/回归组强制dev。SHALL 保存来源、seed、标签版本、支持和输入/gold hash；holdout身份 SHALL 在预测前从私有参考、exact和人工override排除且泄漏0违规。私有资料 SHALL 不出现在外部LLM、公开文件、日志或缓存。

#### Scenario: Reproducible split

- **WHEN** 使用冻结候选、seed和相同身份规则构造split
- **THEN** 同源组不跨split、全部已审查组为dev，并输出可复核manifest及支持统计；不把查询来源当gold支持

#### Scenario: Holdout consumed for tuning

- **WHEN** 分类作者读取holdout逐条错误并据此修改规则
- **THEN** 该组转为开发/回归资料，建立新的未见holdout，旧结果不能继续作为独立验收

### Requirement: Comparable baseline and development-only calibration

评估系统 SHALL 在同一公共输入、稳定目录及完整身份参考范围重跑v1/v2，先排除holdout参考/override；exact-seen SHALL 单独报告而不进unseen主分母。阈值、分差、置信度、lexical/semantic/fusion选择 SHALL 只使用dev，冻结代码、目录、定义、模型、override和配置版本后才独立验收holdout。

#### Scenario: Fair algorithm comparison

- **WHEN** 生成v1基线和v2候选预测
- **THEN** 两者使用同split、同排除范围及同评分规则，不能用旧archive的不同输入结果替代基线

#### Scenario: Calibration frozen before evaluation

- **WHEN** 独立评估开始
- **THEN** 调参者仅使用dev及预定支持汇总，holdout逐条材料和错误不用于改阈值

### Requirement: Explicit denominators and preserved quality targets

质量报告 SHALL 采用design中的固定分母和目标：root precision≥95%；fine micro P/R/F1≥90%/75%/80%；同split相对v1 F1提升≥5pp（基线≥95%时保持并修复强制反例）；支持root F1不得降>5pp；非研究误入≤5%且负例≥20；eligible coverage≥70%；content_kind macro F1≥90%；domain micro F1≥85%；broad_only过度细分≤5%。fine SHALL 移除展示祖先，父类预测不替代细类TP；冻结完整可接受集合以最高集合F1、并列ID字典序确定；非研究/拒判误标计FP，研究拒判计FN。root SHALL 每条每根一次，broad_only SHALL 排除fine并单报过度细分。SHALL 单报scope/status/kind/domain混淆、目录缺口/证据不足/域外支持、支持≥5类macro和所有低支持类、固定seed的item-group bootstrap CI；空分母为N/A。

#### Scenario: Coverage cannot replace precision

- **WHEN** 预测覆盖很多但包含非研究误标或只给父类
- **THEN** 对应FP/FN及独立分母仍计入，不能用覆盖率、自动标签数量或父类credit宣称细类精度通过

#### Scenario: Insufficient support

- **WHEN** 必要支持或分母不足
- **THEN** 对应结果N/A并且整体质量不能宣称通过，保留低支持类和缺口而不静默删类

### Requirement: Independent receipts and release separation

评估系统 SHALL 由独立评估者在冻结gold/配置后输出有效分母、支持、P/R/F1/CI、拒判/失败、基线比较、耗时及版本hash。私有排除确认 SHALL 同时绑定dataset和normalized predictions SHA256；缺gold/支持/证明 SHALL fail-closed。2026-10-09直接采用v2授权 SHALL 保持独立：质量未测量时标unmeasured，不宣称90%，测量不得自动改变生产配置，技术/browser/runtime/Pages通过不得冒充gold质量。

#### Scenario: Receipt reused for another prediction

- **WHEN** 排除证明的prediction hash与本次预测不符
- **THEN** 本次质量验收拒绝该证明并保持未通过

#### Scenario: Default v2 with deferred measurement

- **WHEN** 技术发布已通过而人工质量测量尚未完成
- **THEN** 网站可按用户选择默认v2，质量仍unmeasured，五项测量任务继续未勾且目标保留
