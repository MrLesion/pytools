## Why

Fetching and inspecting an XML or JSON document from a URL currently requires hopping between separate tools (a downloader, an editor, a parser). A small, dependency-free script that loads a URL, validates and pretty-prints its XML or JSON, and optionally saves the result to a file would turn this into a single command. It is useful as a scratch/testing utility.

## What Changes

- Add a new single-file Python tool (`reader.py`) using **only the Python standard library** (`urllib`, `xml`, `json`, `argparse`).
- Load a URL over HTTP(S) and fetch its body.
- Auto-detect whether the body is XML or JSON, trusting the HTTP `Content-Type` header first and falling back to snifing the first non-whitespace character (`<` → XML, `{`/`[` → JSON).
- Parse and validate the content, failing loudly (clear message, non-zero exit) on malformed XML/JSON or request errors (404, timeout, etc.).
- Pretty-print the document (2-space indent for both XML and JSON).
- Print the pretty-printed result to stdout, and/or write it to a file when `-o <file>` is given.
- No format conversion: output stays in the format it was fetched as.
- Support `python reader.py <url>` and `python reader.py <url> -o out.xml`.

## Capabilities

### New Capabilities
- `xml-json-reader`: Fetches a URL, auto-detects and parses XML or JSON, pretty-prints, and optionally saves to a file.

### Modified Capabilities
<!-- No existing capabilities are changed. -->

## Impact

- Adds `reader.py` at the project root (or a `tools/` directory).
- No new third-party dependencies; Python 3.x standard library only.
- No changes to existing code, specs, or systems.