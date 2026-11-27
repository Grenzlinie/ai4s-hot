## MODIFIED Requirements

### Requirement: Fixed journal discovery

The system SHALL discover all configured journals using official feeds and ISSN-scoped metadata, with bounded pagination and overlap windows.

#### Scenario: High-volume feed

- **WHEN** a relevant paper occurs after the first twelve feed entries
- **THEN** it is considered for screening before any presentation limit is applied.

#### Scenario: Pagination or provider failure

- **WHEN** a provider fails or its configured page bound is reached
- **THEN** the journal reports error or partial coverage and preserves previous usable records while other journals continue.

## ADDED Requirements

### Requirement: Daily source directory

The site SHALL link to the official recent articles for watched journals and the latest listings on arXiv and alphaXiv, and SHALL watch Nature Machine Intelligence and Nature Computational Science.

#### Scenario: Read a journal's newest articles

- **WHEN** readers open the source directory and choose a journal
- **THEN** they can open either the journal's official latest articles or its filtered collection on AI4S Hot.
