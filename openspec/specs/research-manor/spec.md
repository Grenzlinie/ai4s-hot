# research-manor Specification

## Purpose

为 AI4S Hot 提供原创 3D 动漫庄园风格的阅读页面，并将论文搜索、近期浏览和领域探索放在易找的位置，让读者在桌面和手机上都能快速定位研究。

## Requirements

### Requirement: Shared manor reading experience

The site SHALL provide a readable, responsive interface using original Blender rendered manor and character assets with ordinary accessible text controls.

#### Scenario: Mobile paper browsing
- **WHEN** a reader opens the reading site on a narrow display
- **THEN** the search and paper shortcuts are accessible before opening deeper filters, and the paper summaries remain usable at the current viewport.

### Requirement: Find papers from the reading page

The site SHALL support title, excerpt, author and identifier search, and expose paper and recent-paper shortcuts.

#### Scenario: Search with an identifier or phrase
- **WHEN** a reader submits combined keywords or a DOI
- **THEN** matching results honor active filters, prioritize title or identifier matches in the recommended view, and are reachable by keyboard.

### Requirement: Find papers within a landscape

The landscape SHALL allow a title query along with existing area, cluster and publication filters.

#### Scenario: Share a filtered view
- **WHEN** a reader reloads or opens a shared landscape link with a title query
- **THEN** the list and compatible charts reflect the restored selection.
