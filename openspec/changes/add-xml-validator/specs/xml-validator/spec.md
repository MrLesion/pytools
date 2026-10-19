## Purpose

Lets a user validate that a local XML file is well-formed by giving a relative file path, reporting either a success message or a clear parse error with a non-zero exit code for automation.

## ADDED Requirements

### Requirement: Validate an XML file at a relative path
The tool SHALL accept exactly one required positional argument — a relative path to a file — and SHALL validate that the file is well-formed XML.

#### Scenario: Well-formed XML file
- **WHEN** the user runs the tool with a relative path to a well-formed XML file
- **THEN** the tool reports the file is valid and exits with status 0

#### Scenario: Malformed XML file
- **WHEN** the user runs the tool with a relative path to a file that is not well-formed XML
- **THEN** the tool reports a clear error and exits with a non-zero status

#### Scenario: Empty file
- **WHEN** the user runs the tool with a relative path to an empty or whitespace-only file
- **THEN** the tool reports the file is not valid XML (no root element) and exits with a non-zero status

#### Scenario: Missing or unreadable file
- **WHEN** the user runs the tool with a relative path to a file that does not exist or cannot be read
- **THEN** the tool reports an error and exits with a non-zero status

### Requirement: Report a clear reason on failure
The tool SHALL include a human-readable description of the problem on standard error when validation fails, including the file path and, where available, the line/column of the error.

#### Scenario: Parse error includes a location
- **WHEN** the file is not well-formed
- **THEN** the reported error includes a description and the line/column where the problem occurred

#### Scenario: Non-XML content is rejected
- **WHEN** the file content is not an XML document (e.g. plain text or JSON)
- **THEN** the tool reports that the content is not valid XML and exits with a non-zero status