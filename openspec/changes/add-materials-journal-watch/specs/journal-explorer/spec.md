## ADDED Requirements

### Requirement: Orthogonal journal selection
The interface SHALL expose searchable multi-select journal controls independently from research topics and source providers, including zero-result journals.

#### Scenario: Multiple journals and a topic
- **WHEN** visitors select two journals and one research topic
- **THEN** results belong to either selected journal and also satisfy the topic, with active filters visible and individually removable

#### Scenario: Navigation and reload
- **WHEN** visitors switch recommendation/latest/saved modes or reload a copied filter URL
- **THEN** journal selection remains active and empty intersections are explained

### Requirement: Pending review visibility
The default feed SHALL display relevant journal articles and provide an explicit path to inspect pending journal candidates with their screening reason.

#### Scenario: Default versus pending
- **WHEN** a candidate lacks evidence to establish relevance
- **THEN** it is hidden from the default recommendation flow and visible in the pending view

### Requirement: Compatible accessible browsing
Journal browsing SHALL work on desktop and mobile with keyboard-operable controls, and archives without journal metadata SHALL remain usable.

#### Scenario: Old archive
- **WHEN** no journal registry or article fields exist
- **THEN** existing topic, source, search and reading controls continue to operate

#### Scenario: Mobile and keyboard
- **WHEN** a visitor selects journals through the dialog on a narrow screen or using keyboard
- **THEN** selections, close/focus return and result updates remain usable without a native dropdown
