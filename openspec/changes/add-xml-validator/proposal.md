## Why

Quickly verifying that a local XML file is well-formed currently requires opening an editor, a browser, or another tool. A tiny command-line validator that takes a relative file path and reports pass/fail with a clear exit code lets developers and scripts check XML files fast.

## What Changes

- Add a new single-file Python CLI, `validate_xml.py`, using **only the Python standard library**.
- It takes one required positional argument: a **relative path** to an XML file.
- It validates the file as well-formed XML:
  - Prints a success message and exits `0` when the file is well-formed.
  - Prints a clear error (with position, where available) and exits non-zero when it is not.
- Detects and reports missing/unreadable files and empty/whitespace-only files as errors.
- No format conversion, no fetching — purely local file validation.

## Capabilities

### New Capabilities
- `xml-validator`: Validates that an XML file at a given relative path is well-formed, reporting success or a clear error with a non-zero exit on failure.

### Modified Capabilities
<!-- No existing capabilities are changed. -->

## Impact

- Adds `validate_xml.py` at the project root.
- No new third-party dependencies; Python 3.x standard library only (`argparse`, `xml.etree.ElementTree`, `os`/`sys`).
- No changes to existing code, specs, or systems (`reader.py` is untouched).