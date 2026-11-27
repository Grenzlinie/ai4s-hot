## MODIFIED Requirements

### Requirement: Classification states and content facets

The system SHALL independently track research scope, topic assignment, content type, and the site's broad domains.

#### Scenario: Organization news

- **WHEN** public content describes an enterprise deployment or partnership without evidence of a scientific task
- **THEN** it can be browsed as organization or engineering news without an inferred scientific specialty.

#### Scenario: Missing abstract

- **WHEN** a title and available excerpt cannot support a fine topic
- **THEN** the public record receives a wide topic or a type classification with a low-confidence receipt, and retains its existing research scope.

## ADDED Requirements

### Requirement: Public topic coverage

Every record in the public archive SHALL have a topic or content classification.

#### Scenario: Build an archive with legacy records

- **WHEN** a legacy record has no current topic
- **THEN** the builder assigns a broad classification using available public evidence or content type, and leaves valid detailed assignments intact.

#### Scenario: Open an existing unclassified link

- **WHEN** a reader opens the former unclassified filter
- **THEN** the view offers the public broad classification and no longer presents an unclassified section.
