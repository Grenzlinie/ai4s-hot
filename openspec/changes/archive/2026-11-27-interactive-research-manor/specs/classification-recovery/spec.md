## MODIFIED Requirements

### Requirement: Separate triage queues

The interface SHALL keep journal relevance review independent of a record's research topic or content classification.

#### Scenario: Candidate without research labels

- **WHEN** a journal item has a valid broad topic and pending relevance
- **THEN** it remains browsable in the relevance review view and excluded from the default materials-AI stream.

#### Scenario: Non-research and legacy URL

- **WHEN** a model or organization record has a content classification or a reader opens an old unclassified URL
- **THEN** the content category is browsable and the prior filter resolves to the broad categories.
