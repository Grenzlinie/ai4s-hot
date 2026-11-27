## ADDED Requirements

### Requirement: Interactive research manor

The site SHALL display the original 3D manor with user-controlled camera, an animated scholar, and direct links from landmarks to research content.

#### Scenario: Visit a landmark

- **WHEN** a reader taps the library or telescope in the model or activates its text link
- **THEN** the library opens the paper list, and the telescope opens the paper landscape.

#### Scenario: Explore on a mobile display

- **WHEN** a reader uses a touch display
- **THEN** they can drag the camera horizontally, tap an interaction, and scroll the page vertically while retaining a direct path to search and reading.

#### Scenario: Graphics unavailable

- **WHEN** WebGL or the model is unavailable
- **THEN** the illustration, search and reading links remain available.
