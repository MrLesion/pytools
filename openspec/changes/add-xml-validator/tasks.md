## 1. Setup

- [x] 1.1 Create `validate_xml.py` at the project root with an `argparse` CLI: one required positional `path` (relative) and a working `--help`

## 2. Validation

- [x] 2.1 Use `xml.etree.ElementTree.parse(path)` to parse the file; on success print a clear message (e.g. `OK: <path> is well-formed XML`) and exit 0
- [x] 2.2 Catch `xml.etree.ElementTree.ParseError`, print the reason and `position` (line/column) to stderr, and exit non-zero

## 3. Error handling

- [x] 3.1 Catch missing/unreadable files (`OSError`/`FileNotFoundError`), print a clear message to stderr, exit non-zero
- [x] 3.2 Ensure empty/whitespace-only files are reported as invalid (ElementTree's "no element found") and exit non-zero

## 4. Verification

- [x] 4.1 Validate a well-formed XML file: prints success, exit 0
- [x] 4.2 Validate a malformed XML file: prints an error with line/column, exit non-zero
- [x] 4.3 Validate an empty file and a missing path: each prints a clear error and exits non-zero
- [x] 4.4 Run `python validate_xml.py --help` and confirm the CLI surface matches the spec