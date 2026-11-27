# paper-landscape Specification

## Purpose

让读者从本站论文归档了解主要领域、相近工作与近期发表趋势。领域用于长期浏览，研究簇随归档文本生成。图表共享筛选条件，并链接到论文原文和阅读页。

## Requirements

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

### Requirement: Recover broad areas from reading topics

The site's landscape SHALL use corroborated, specific reading topics and unambiguous title phrases to recover a broad area for previously unmapped papers.

#### Scenario: Specific research context
- **WHEN** an unmapped paper has an applicable active reading label supported by research context or a clear title phrase such as video editing
- **THEN** the paper is placed in the corresponding existing broad area, taking account of whether the signal describes the subject or a supporting method.

#### Scenario: Insufficient evidence or conflicting signals
- **WHEN** an unmapped paper has only generic terms, an unsupported inferred label or unresolved competing areas
- **THEN** it remains in the other and unassigned group and can be browsed in the landscape.
