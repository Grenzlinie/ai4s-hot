## MODIFIED Requirements

### Requirement: Static browser state
The system SHALL 在无后端账号及私有前端凭据的Pages页面保存可恢复的筛选URL，并保留浏览器本地收藏和已读；URL SHALL 表达多来源、领域、类型及阅读方式，手机端 SHALL 提供可关闭且焦点正确的主题与来源面板。

#### Scenario: Share and history
- **WHEN** 分享筛选URL或使用浏览器后退/前进
- **THEN** 恢复主题、时间、多来源、领域、类型、查询及阅读方式，旧主题ID通过alias处理，收藏内容仍由当前浏览器决定

#### Scenario: Legacy filters
- **WHEN** 打开旧单来源、channel或alpha/zotero排序URL
- **THEN** 单来源迁移为单元素来源集合；旧channel及有隐式范围的排序通过显式兼容条件保留原结果含义，并显示迁移说明及清除入口

#### Scenario: Mobile keyboard use
- **WHEN** 在390px宽屏幕打开并关闭主题或来源面板或按Esc
- **THEN** 不出现页面水平溢出，焦点进入面板并返回触发按钮，展开、选择、多来源切换均可用键盘完成

#### Scenario: Read without credentials
- **WHEN** 普通访客打开Pages页面
- **THEN** 只读取公开归档，本机收藏和已读可用，不加载私有API key或GitHub写token

## ADDED Requirements

### Requirement: Contextual research topic presentation
The system SHALL 在统一阅读流保留四维目录、主题搜索、退役历史、公开依据及本机纠错，卡片显示简短主题名并允许查看完整路径；目录原始层级与稳定ID SHALL 不因展示改版而修改。

#### Scenario: Short label and full path
- **WHEN** 用户在卡片选择细主题或查看完整路径
- **THEN** 同一信息流应用该主题，目录展开其祖先，完整路径可用；来源、领域、类型和阅读方式不被重置
