## Purpose

Lets a user load an XML or JSON document from a URL, have it validated and pretty-printed, and optionally save the formatted result to a file using only the Python standard library.

## Requirements

### Requirement: Fetch a document from a URL
The tool SHALL accept one URL argument and retrieve the document body over HTTP(S), following the returned content.

#### Scenario: Successful fetch of XML
- **WHEN** the user runs the tool with a URL that returns an XML document
- **THEN** the tool retrieves the document body

#### Scenario: Successful fetch of JSON
- **WHEN** the user runs the tool with a URL that returns a JSON document
- **THEN** the tool retrieves the document body

#### Scenario: URL returns an error status
- **WHEN** the URL responds with an HTTP error status (e.g. 404)
- **THEN** the tool reports an error and exits with a non-zero status

#### Scenario: URL is unreachable
- **WHEN** the URL cannot be reached (e.g. DNS failure or timeout)
- **THEN** the tool reports an error and exits with a non-zero status

### Requirement: Auto-detect document type
The tool SHALL determine whether the retrieved body is XML or JSON, preferring the HTTP `Content-Type` header when present and otherwise inferring the type from the first non-whitespace character (`<` for XML; `{` or `[` for JSON).

#### Scenario: Type detected from Content-Type header
- **WHEN** the response includes a `Content-Type` header indicating `application/xml`
- **THEN** the tool treats the body as XML

#### Scenario: Type detected from content sniffing
- **WHEN** the response has no usable `Content-Type` header and the body starts with `<`
- **THEN** the tool treats the body as XML

#### Scenario: JSON detected from content sniffing
- **WHEN** the body starts with `{` and no XML Content-Type is present
- **THEN** the tool treats the body as JSON

### Requirement: Parse and validate content
The tool SHALL parse the retrieved body as the detected type and SHALL reject malformed content.

#### Scenario: Well-formed XML
- **WHEN** the body is well-formed XML
- **THEN** the tool parses it successfully

#### Scenario: Malformed XML
- **WHEN** the body is detected as XML but is not well-formed
- **THEN** the tool reports a parse error and exits with a non-zero status

#### Scenario: Valid JSON
- **WHEN** the body is valid JSON
- **THEN** the tool parses it successfully

#### Scenario: Invalid JSON
- **WHEN** the body is detected as JSON but is invalid
- **THEN** the tool reports a parse error and exits with a non-zero status

### Requirement: Pretty-print output
The tool SHALL format the parsed document with a 2-space indent before output.

#### Scenario: Pretty-printed XML
- **WHEN** a well-formed XML document is fetched
- **THEN** the tool produces an indented XML representation

#### Scenario: Pretty-printed JSON
- **WHEN** a valid JSON document is fetched
- **THEN** the tool produces an indented JSON representation

### Requirement: Output the result
The tool SHALL print the formatted document to standard output by default, and SHALL write it to a file when an output path is provided via `-o`.

#### Scenario: Print to stdout
- **WHEN** the user runs the tool with only a URL and no `-o` option
- **THEN** the formatted document is printed to standard output

#### Scenario: Save to a file
- **WHEN** the user runs the tool with a URL and `-o <file>`
- **THEN** the formatted document is written to that file