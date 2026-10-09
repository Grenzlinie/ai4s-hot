# topic-explorer

## Purpose
记录当前网站树形主题目录、父类筛选与静态网站约束。当前目录数字统计全部归档，尚未实现筛选范围内数量、纠错工作流和可恢复的筛选 URL。

## Requirements

### Requirement: Hierarchical topic navigation
The system SHALL 根据公开主题树渲染层级导航，使父主题筛选包含子主题条目，并对结果按条目 ID 去重。

#### Scenario: Parent selection
- **WHEN** 选择一个含子主题的父主题
- **THEN** 展示直接属于父主题或任意后代的条目，每个条目只展示一次

### Requirement: Static browser state
The system SHALL 在静态 GitHub Pages 页面提供主题、时间、来源筛选和浏览器本地收藏，不要求前端拥有 Zotero 或 GitHub 凭据。

#### Scenario: Read without credentials
- **WHEN** 普通访客打开网站
- **THEN** 使用公开 JSON 浏览并在当前浏览器保存收藏，前端不加载私有 API key
