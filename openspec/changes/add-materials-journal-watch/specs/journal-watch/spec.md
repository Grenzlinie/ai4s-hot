## ADDED Requirements

### Requirement: Fixed journal discovery
The system SHALL discover all ten configured journals using official feeds and ISSN-scoped metadata, with bounded pagination and overlap windows.

#### Scenario: High-volume feed
- **WHEN** a relevant paper occurs after the first twelve feed entries
- **THEN** it is considered for screening before any presentation limit is applied

#### Scenario: Pagination or provider failure
- **WHEN** a provider fails or its configured page bound is reached
- **THEN** the journal reports error or partial coverage and preserves previous usable records while other journals continue

### Requirement: Traceable paper identity and dates
The system SHALL normalize DOI identities and preserve journal identity, online/print/indexed dates, and stable first-seen/bookmark identity.

#### Scenario: Repeat discovery
- **WHEN** RSS and Crossref return the same DOI or repeat it on a subsequent day
- **THEN** one archive article retains its original ID and first_seen and merges public journal metadata

#### Scenario: Old work reindexed
- **WHEN** an old article is recently indexed
- **THEN** its publication date is not replaced by the indexing date to make it appear newly published

### Requirement: Material research relevance boundary
The system SHALL distinguish AI methods applied to materials research from materials built for AI hardware and retain insufficient-evidence candidates as pending.

#### Scenario: AI used for materials
- **WHEN** public title or abstract provides evidence of an AI method applied to materials research
- **THEN** the article can enter the relevant feed with a public screening reason and existing research-topic classification

#### Scenario: Missing abstract or ambiguous title
- **WHEN** available metadata cannot establish relevance
- **THEN** the candidate remains pending, rather than being silently discarded or declared relevant

#### Scenario: Hardware or nonresearch content
- **WHEN** metadata clearly describes only materials for AI hardware or a correction/news item
- **THEN** it does not enter the relevant materials-AI research stream solely due to AI keywords

### Requirement: Durable public-only state and budget
The system SHALL persist only whitelisted public journal state after successful classification and validation, and pending candidates SHALL NOT consume summary/enrichment requests.

#### Scenario: Whole-update failure
- **WHEN** taxonomy/classification/validation fails
- **THEN** prior archive and journal cursor/state remain valid for retry

#### Scenario: Pending candidate
- **WHEN** a candidate is pending
- **THEN** it is browsable as pending and excluded from automatic summary/full-text enrichment candidates
