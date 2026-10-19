## MODIFIED Requirements

### Requirement: Fetch a document from a URL
The tool SHALL accept one URL argument and retrieve the document body over HTTP(S), following the returned content, and SHALL display a download progress indicator (bytes downloaded vs. total size) while the body is being retrieved.

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

#### Scenario: Progress shown while downloading
- **WHEN** the response reports its total size (e.g. a `Content-Length`)
- **THEN** the tool renders a progress bar updating with the number of bytes downloaded

#### Scenario: Progress hidden when size is unknown
- **WHEN** the response does not report a total size
- **THEN** the tool does not render a percentage progress bar (and does not fail)

## MODIFIED Requirements

### Requirement: Output the result
The tool SHALL print the formatted document to standard output, SHALL write it to the file given by `-o` when that option is provided, and SHALL otherwise save a copy into the project's `output/` folder. The output file extension SHALL be derived from the detected document type (`.xml` or `.json`), appended automatically when `-o` is provided without an extension.

#### Scenario: Print to stdout
- **WHEN** the user runs the tool with only a URL and no `-o` option
- **THEN** the formatted document is printed to standard output and a copy is saved into the `output/` folder with the detected-type extension

#### Scenario: Save to a file
- **WHEN** the user runs the tool with a URL and `-o <file>`
- **THEN** the formatted document is written to that file

#### Scenario: Extension derived from detected type
- **WHEN** the user runs the tool with `-o <file>` where `<file>` has no extension and the body is detected as XML
- **THEN** the tool writes to `<file>.xml`

#### Scenario: Extension derived from detected type (JSON)
- **WHEN** the user runs the tool with `-o <file>` where `<file>` has no extension and the body is detected as JSON
- **THEN** the tool writes to `<file>.json`

#### Scenario: Existing extension is preserved
- **WHEN** the `-o` path already has an extension
- **THEN** the tool writes to the path exactly as provided

#### Scenario: Automatic save names the file from the URL
- **WHEN** the user runs the tool with no `-o` option
- **THEN** the file saved to `output/` is named after the requested URL, with the detected-type extension