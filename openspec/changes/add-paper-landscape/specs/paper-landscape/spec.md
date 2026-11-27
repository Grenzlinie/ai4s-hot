## ADDED Requirements

### Requirement: Stable research areas and text clusters

The site SHALL assign papers to broad browsing areas and derive separate groups from public titles and abstracts.

#### Scenario: Confirmed research in the archive
- **WHEN** the builder reads a public archive with research papers
- **THEN** each eligible paper appears once by archive ID, with a browsing area and a text cluster when available.

#### Scenario: Pending or sparse input
- **WHEN** relevance is pending, a date is missing or the corpus lacks enough shared text
- **THEN** pending journal records stay in their reading queue, missing dates stay empty, and eligible papers remain accessible in the domain and list views.

### Requirement: Coordinated landscape views

The page SHALL offer a paper map, area distribution, publication trends and an associated paper list.

#### Scenario: Explore a group
- **WHEN** a reader selects a time range, area, cluster or week
- **THEN** the views and list reflect the selection and the reader can open a paper.

#### Scenario: Unsupported or inaccessible data
- **WHEN** a selection is empty, a cluster link is stale or the dataset cannot be loaded
- **THEN** the page provides a clear recovery action and retains the main reading entry.
