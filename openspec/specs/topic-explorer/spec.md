# topic-explorer

## Purpose

定义静态网站中的四维主题树、筛选范围计数、可恢复 URL、手机交互、退役历史及本机纠错；普通访客无需私有凭据，阅读状态保存在浏览器。

## Requirements

### Requirement: Hierarchical topic navigation
The system SHALL 支持主题搜索、独立展开与选择控件、选中路径自动展开和可访问键盘操作。节点 SHALL 显示当前其他筛选范围内的去重数量及明确标注的全部归档数量。

#### Scenario: Counts with filters
- **WHEN** 用户改变日期、来源、关键词、收藏或未读范围
- **THEN** 节点当前数量随之更新，父节点按公开item ID并集计算，不因多标签重复计数

#### Scenario: Topic selection from card
- **WHEN** 用户点击条目的细分类标签
- **THEN** 选中该分类并展开其祖先，选择动作不依赖点击极小的折叠箭头

#### Scenario: Parent selection
- **WHEN** 用户选择一个含子类别的父主题
- **THEN** 返回直接属于父主题及其任意后代的条目，并按item ID去重

### Requirement: Static browser state
The system SHALL 在无后端账号及私有前端凭据的Pages页面保存可恢复的筛选URL，并保留浏览器本地收藏和已读；手机端 SHALL 提供可关闭且焦点正确的主题抽屉。

#### Scenario: Share and history
- **WHEN** 分享筛选URL或使用浏览器后退/前进
- **THEN** 恢复主题、时间、来源、查询及排序，旧主题ID通过alias处理，收藏内容仍由当前浏览器决定

#### Scenario: Mobile keyboard use
- **WHEN** 在390px宽屏幕打开并关闭主题抽屉或按Esc
- **THEN** 不出现水平溢出，焦点进入抽屉并返回触发按钮，展开和选择均可用键盘完成

#### Scenario: Read without credentials
- **WHEN** 普通访客打开Pages页面
- **THEN** 只读取公开归档，本机收藏和已读可用，不加载私有API key或GitHub写token

### Requirement: Facet combination and empty results
The system SHALL 将同一研究维度内选中的主题按OR组合、不同维度按AND组合，与其他筛选按AND组合；空结果 SHALL 展示生效条件及逐项清除入口。

#### Scenario: Two methods and one material
- **WHEN** 用户选择两个AI方法标签和一个材料标签
- **THEN** 返回属于该材料且至少满足一个所选AI方法的去重条目

### Requirement: Visible classification evidence
The system SHALL 区分网站领域标签与Zotero目录，展示推断状态、公开依据和本机纠错入口，不将相似度伪装为准确概率。

#### Scenario: Low confidence
- **WHEN** 条目被拒绝细分类或只有父主题
- **THEN** 显示具体原因及可用操作，而非统一显示无解释的待分类

### Requirement: Direct default version visibility
The system SHALL 在技术门禁通过后直接向访客展示v2分类并明确“准确率尚未量化”，不新增试用selector；旧URL、刷新和历史导航 SHALL 保持稳定ID迁移及本机收藏/已读状态。

#### Scenario: Direct visit and refresh
- **WHEN** 访客直接访问、刷新或打开旧主题URL
- **THEN** 默认使用v2，无需主动切换，未量化说明可见且已有阅读状态不丢失
