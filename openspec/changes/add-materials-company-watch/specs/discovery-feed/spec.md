## ADDED Requirements

### Requirement: Materials AI company updates

The system SHALL collect materials-related technical updates from configured official company sources and expose them in a dedicated directory group.

#### Scenario: Official technical report

- **WHEN** a watched company publishes a materials model, dataset, simulation, synthesis, characterization or relevant engineering report
- **THEN** the site can index the public report under the company's source with its official URL and known publication date.

#### Scenario: Nontechnical company news

- **WHEN** the official index includes financing, hiring or general AI product news without a materials research contribution
- **THEN** that candidate is excluded before insertion and summarization.

#### Scenario: Browse by company

- **WHEN** a reader chooses Materials AI Companies in Daily Sources
- **THEN** each company has an official update link and a link to its collected items.
