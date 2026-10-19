## Context

See proposal.md - Why. This is a brand-new, minimal standalone utility: a single-file Python script using only the standard library that validates a local XML file given as a relative path. There is no existing code to integrate with. The externally observable behavior is fixed by `specs/xml-validator/spec.md` (accept one relative path → validate well-formedness → clear success/error + correct exit code).

## Goals / Non-Goals

**Goals:**
- Single stdlib-only file, `validate_xml.py`.
- Small, predictable CLI: `validate_xml.py <relative-path>`.
- Consistent exit codes (`0` valid, non-zero on any failure) for scripting.
- Clear, actionable error messages (path + position when available).

**Non-Goals:**
- No URL fetching, no auto-detection of format — it is a local-XML-only validator.
- No schema/DTD validation beyond well-formedness, no `xmllint`-style pretty output.
- Not a general-purpose XML toolkit; output is minimal by design.

## Decisions

**Parsing: `xml.etree.ElementTree.parse(path)` to validate.**
`ElementTree.parse` raises `xml.etree.ElementTree.ParseError` (which carries `position` as a `(line, col)` tuple) on malformed input and rejects empty/whitespace-only files with *"no element found"*. It also enforces a single root element, so it models "well-formed XML *document*" rather than a fragment. It reads and decodes the file per its XML declaration automatically. Alternatives considered:
- `xml.dom.minidom.parse` — validates too, but is heavier and its error messages are less compact.
- `xml.parsers.expat` — fastest and gives line/column, but does not enforce a single root, so it would accept text/`multi-root` fragments a validator should reject.

**CLI & errors: `argparse` positional `path` + `argparse.ArgumentTypeError`-style messages.**
`argparse` handles `--help` and the missing-argument error for free. The path is a plain positional. Missing/unreadable files are caught as `FileNotFoundError`/`OSError` and reported to stderr. `ParseError` is caught, and its `.position` (when present) and `.msg` are interpolated into a clear stderr line.

**Exit codes: `0` on valid, `1` on any invalid/unreadable input.**
A single non-zero code is enough for scripts and CI; no need to differentiate error classes with distinct codes.

## Risks / Trade-offs

- ["Valid XML" means well-formed only, not schema-valid] → State this clearly in usage text; schema validation is out of scope.
- [`ElementTree` expands external entities?] → Python's stdlib ElementTree does not fetch external entities by default (no XXE in the parser), so worst case is local well-formedness, not data exfiltration. Acceptable.
- [Large files] → ElementTree builds a tree in memory; fine for the sizes this scratch tool targets. A streaming expat variant is a future option if needed.

## Migration Plan

Not applicable — a new standalone script. Deployment is copying/serving `validate_xml.py`; rollback is deleting it. No integration with existing systems.

## Open Questions

None. Future extensions (DTD/schema validation, `--recover`, multiple files) do not change the specs, approach, or task breakdown.