# classification-recovery Specification

## Purpose

恢复因词义歧义和缺摘要门槛而遗漏的有据研究分类，分开相关性确认与研究主题分类队列，并以身份验证、请求预算和持久退避补充公开摘要；提高覆盖时保留不确定性、人工优先及私密参考边界。

## Requirements

### Requirement: Contextual scope detection
The system SHALL distinguish scientific acquisition terminology from corporate events.

#### Scenario: Scientific acquisition
- **WHEN** a research paper describes acquisition functions, data acquisition or information acquisition
- **THEN** that phrase alone does not mark the paper as organization policy or non-research

#### Scenario: Real corporate event
- **WHEN** public content explicitly describes a company acquisition, appointment or partnership
- **THEN** it retains the appropriate organization content type without fabricated research topics

### Requirement: Title evidence and coverage
The system SHALL use explicit public title evidence for topics when abstracts are missing, allowing supported broad fallback while preserving uncertainty and manual precedence.

#### Scenario: Clear title without abstract
- **WHEN** a title directly identifies a material and AI method using defined phrases
- **THEN** applicable labels may be assigned with a title-only explanation despite missing abstract

#### Scenario: Weak title
- **WHEN** neither title nor abstract supports a specific topic
- **THEN** no unsupported leaf label is fabricated and the content remains browsable by content type

#### Scenario: Ambiguous scientific words
- **WHEN** a materials title uses next-generation, optimization or chemical robustness without explicit AI/model-evaluation context
- **THEN** these generic words alone do not produce generative-model, AI-training or benchmark-robustness labels

### Requirement: Separate triage queues
The interface SHALL distinguish relevance-pending journal candidates, research-topic-unclassified records, and non-research content types in matching counts and filters.

#### Scenario: Candidate without research labels
- **WHEN** a journal item has pending relevance
- **THEN** it belongs to relevance review independently of any inferred research label and does not inflate research-topic-unclassified counts

#### Scenario: Non-research and legacy URL
- **WHEN** a model/organization record has no research label or a visitor opens an old unclassified URL
- **THEN** content types remain visible, non-research is not queued for research topics, and legacy filters resolve without contradictory relevance conditions

### Requirement: Bounded candidate metadata recovery
The system SHALL prioritize missing public abstracts with AI/material title clues using identity-verified public sources, bounded requests and durable retry backoff.

#### Scenario: Metadata recovered
- **WHEN** an exact DOI response or verified publisher abstract is available
- **THEN** the public abstract updates candidate evidence before relevance and topic classification without changing the item identity

#### Scenario: Failure or identity mismatch
- **WHEN** a request fails, returns challenge text or a different paper
- **THEN** no abstract is invented, retries respect persisted backoff, and no billable model/Bohrium request is made

### Requirement: Safe historical migration
The system SHALL invalidate old classification caches for rule changes and publish new candidate state only with a validated complete archive.

#### Scenario: New rules
- **WHEN** v2.5 rules process an old item
- **THEN** classification is reconsidered while stable ID, first_seen and manual corrections remain intact

#### Scenario: Classification failure
- **WHEN** subsequent classification or validation fails after metadata recovery
- **THEN** the previous persisted archive and candidate state remain usable and unchanged
