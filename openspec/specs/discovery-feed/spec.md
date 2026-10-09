# discovery-feed Specification

## Purpose
定义AI4S Hot跨来源科研阅读体验，把研究领域、内容类型、来源筛选与阅读方式放入同一信息流，保留论文以外的报告及模型发布，并让用户理解实际排序依据。

## Requirements

### Requirement: Unified reading modes
The system SHALL 提供综合推荐、最新及本机收藏阅读方式；切换方式 SHALL 保留查询、领域、类型、主题及来源条件，排序 SHALL 不隐式删除缺少推荐信号的条目。

#### Scenario: News without paper signals
- **WHEN** 研究报告没有Zotero相似度或alphaXiv排名，用户切换综合推荐和最新
- **THEN** 该报告在满足筛选时仍属于结果集，只有顺序改变

#### Scenario: Saved scope
- **WHEN** 用户切换收藏
- **THEN** 在现有条件内显示本机收藏；空结果可逐项清除条件或返回综合推荐

### Requirement: Visible multiple source selection
The system SHALL 展示常用来源按钮、已选来源及可搜索的全部来源面板，替代来源下拉；多来源 SHALL 按OR匹配并以公开item ID去重。来源数量 SHALL 在当前其他筛选范围内计算，显示含义明确的零结果状态。

#### Scenario: Overlapping sources
- **WHEN** 一篇论文同时来自HF Daily和alphaXiv，用户选择两者
- **THEN** 该论文只显示一次，查询、领域和推荐方式保持不变

#### Scenario: Empty source
- **WHEN** 选择当前无内容的已配置来源
- **THEN** 仍保留选择并显示空态及取消条件入口，不假称采集失败

### Requirement: Separate discovery axes
The system SHALL 分开展示领域、内容类型及研究主题，取消将论文、工具、前沿模型与科学领域混排的主导航。领域 SHALL 来源于公开领域标签，类型 SHALL 来源于内容类型；标签证据不足时 SHALL 不借来源品牌推断学科。

#### Scenario: Company report
- **WHEN** OpenAI报告只有通用AI领域标签
- **THEN** 能按OpenAI来源及报告类型找到，不能仅因其来源被归入材料研究

### Requirement: Explainable mixed ranking
The system SHALL 基于可用信号生成稳定的跨来源综合顺序，保留缺少信号的内容，并展示实际使用的推荐依据；SHALL 不把原始相似度与热榜排名直接相加或将结果标成已验证个人相关度。

#### Scenario: Missing signal and repeatability
- **WHEN** 相同快照及筛选重复计算，部分内容缺少推荐信号
- **THEN** 结果顺序稳定、缺信号内容未被排除、其依据仅显示已有信号

#### Scenario: No publication date
- **WHEN** 条目只有收录时间
- **THEN** 最新排序使用收录时间并明确标为收录，不能伪装成发布日期

### Requirement: Public website positioning
The system SHALL 面向一般读者使用独立AI4S Hot网站文案，导航和推荐说明使用“研究主题”“研究推荐”等名称，不展示“你的Zotero”、私人文献库或目录复用过程；技术来源ID SHALL 保持兼容。

#### Scenario: Reader facing labels
- **WHEN** 普通访客浏览首页、主题目录、来源选项及推荐依据
- **THEN** 看到通用科研进展站表达，没有个人Zotero依赖叙述；筛选和推荐逻辑保持一致
