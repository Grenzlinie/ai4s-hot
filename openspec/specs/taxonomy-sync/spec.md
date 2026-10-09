# taxonomy-sync

## Purpose
记录现有 Zotero 目录读取、公开目录投影与同步失败时保留数据的行为；这是当前实现基线，不代表未来稳定身份和迁移机制已经完成。

## Requirements

### Requirement: Collection projection
The system SHALL 只读获取 Zotero collection 名称和父子关系，生成公开主题树，排除名称以 `00 ` 开头的目录及其后代，不在公开树中包含 collection key。

#### Scenario: Nested collection projection
- **WHEN** 读取到父、子和 `00 待确认` 目录
- **THEN** 展示父子层级并排除待确认子树，公开 ID 由当前路径哈希生成

### Requirement: Retain taxonomy on failure
The system SHALL 在 Zotero 同步失败时保留上一版公开目录、最近成功时间及有效标签，并报告同步状态。

#### Scenario: Read failure
- **WHEN** Zotero 读取抛出异常且已有目录归档
- **THEN** 使用旧目录并标为 stale，公开输出只包含错误类型而不包含异常原文
