## Why

Fetching a large document currently gives no feedback on download progress, and saving to disk requires the user to pass an explicit `-o <path>`. Add a live download progress bar and make saving to the project's `output/` folder the effortless default, with the file extension derived from the detected format.

## What Changes

- Add a byte-based download progress bar while the body is being fetched (bytes downloaded vs. total size, when the server reports it).
- When `-o <path>` is given without an extension, append the detected type's extension (`.xml` or `.json`) automatically, so the user never has to guess.
- When `-o` is omitted, still print the formatted document to stdout **and** save a copy into the `output/` folder using a name derived from the URL + the correct extension.
- Keep the existing CLI (`reader.py <url>` and `reader.py <url> -o <file>`) backward compatible; no flags are removed or renamed.

## Capabilities

### New Capabilities
<!-- None. The progress bar and default-save behavior extend the existing capability. -->

### Modified Capabilities
- `xml-json-reader`: The "Fetch a document from a URL" requirement gains a download progress indicator; the "Output the result" requirement gains auto-derived extensions and a default save into the `output/` folder.

## Impact

- Edits `reader.py` (fetch loop, output handling, argument validation, file naming).
- Adds an `output/` directory (already present at the project root) as the default save location.
- Still uses only the Python standard library (`urllib`, `xml`, `json`, `argparse`, `os`).
- No change to HTTP request semantics, type detection, parsing, or pretty-printing.