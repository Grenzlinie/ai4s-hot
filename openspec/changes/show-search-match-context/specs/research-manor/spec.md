## ADDED Requirements

### Requirement: Query-dependent search evidence

The reading page SHALL show where query text matched on the result card before users open its details.

#### Scenario: Author and identifier match

- **WHEN** a query matches an author or publication identifier
- **THEN** the result visibly shows the matching name or identifier as stored in the archive.

#### Scenario: Match in the abstract

- **WHEN** a query matches an excerpt or summary
- **THEN** the card can show a passage around that match and visually emphasize the matched text.

#### Scenario: Short name parts in unrelated content

- **WHEN** a name query only appears inside longer English words or across different authors
- **THEN** those records do not match solely on that evidence.
