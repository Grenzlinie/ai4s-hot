## ADDED Requirements

### Requirement: Public topic coverage

Every record in the public archive SHALL have a topic or content classification.

#### Scenario: Build an archive with legacy records

- **WHEN** a legacy record has no current topic
- **THEN** the builder assigns a broad classification using available public evidence or content type, and leaves valid detailed assignments intact.

#### Scenario: Open an existing unclassified link

- **WHEN** a reader opens the former unclassified filter
- **THEN** the view offers the public broad classification and no longer presents an unclassified section.
