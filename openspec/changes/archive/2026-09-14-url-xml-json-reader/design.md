## Context

See proposal.md - Why. This is a brand-new, standalone utility: a single-file Python script using only the standard library. There is no existing codebase, so the design is unconstrained by existing patterns. The externally observable behavior is fixed by `specs/xml-json-reader/spec.md` (fetch, detect, validate, pretty-print, output to stdout or `-o` file).

## Goals / Non-Goals

**Goals:**
- Keep it to a single Python file with zero third-party dependencies.
- Provide a small, predictable CLI: `reader.py <url>` and `reader.py <url> -o <file>`.
- Degrade to loud, non-zero-exit failures on bad URLs or malformed content.

**Non-Goals:**
- No format conversion (XML↔JSON). Output stays in the detected source format.
- No XPath/JSONPath querying, no piping into transforms, no retry/redirect policy beyond what `urllib` does by default.
- Not a general HTTP client; only GET of a single document.

## Decisions

**CLI: `argparse` with a positional URL and `-o` output option.**
`argparse` is stdlib and gives `--help`, error messages, and non-zero exit on bad usage for free. Nearest alternative (manual `sys.argv` parsing) adds parsing bugs for little gain. `url` positional; `-o/--output` optional; `--indent` omitted (fixed 2-space indent per spec, keeping the surface minimal).

**Fetching: `urllib.request` with `User-Agent` set.**
`urllib.request.urlopen` is stdlib. A dedicated `User-Agent` is included because some APIs reject the default `Python-urllib` UA. Alternatives considered: `requests` (third-party, violates the zero-dep goal) and `http.client` (lower-level, more boilerplate for no benefit).

**Type detection: `Content-Type` header first, then first-char sniffing.**
Read the response `Content-Type`; if it clearly indicates XML or JSON, use it. Otherwise inspect the first non-whitespace character: `<` → XML, `{`/`[` → JSON. This matches the spec ordering. Trade-off: a misleading header (e.g. `text/html` containing XML) falls through to sniffing, which is the pragmatic escape hatch.

**XML parsing/pretty-print: `xml.dom.minidom` `toprettyxml()` with 2-space indent.**
`xml.dom.minidom.parseString(...).toprettyxml(indent="  ")` is the smallest stdlib path to a well-formed, indented XML string and it *also* validates well-formedness (raising `xml.parsers.expat.ExpatError` on bad input). Output is text, so it prints/saves directly. Alternatives considered:
- `xml.etree.ElementTree` with a custom recursive pretty-printer → more code to reproduce indentation, no added value here.
- `lxml` → third-party, ruled out.
Known limitation (see Risks): `minidom.toprettyxml` does not preserve CDATA sections and is not a faithful round-trip of namespaces/comments. Acceptable for a scratch pretty-printer.

**JSON parse/print: `json.loads` then `json.dumps(indent=2)`.**
`json.loads` validates (raising `json.JSONDecodeError`), and `json.dumps(..., indent=2)` produces the 2-space pretty print the spec requires.

**Error handling: catch request and parse errors, print to stderr, `sys.exit(1)`.**
`urllib.error.URLError`/`HTTPError` → readable "could not fetch" message; `ExpatError`/`JSONDecodeError`/`ValueError` → "could not parse as <type>" message. Writing to `-o` failures are also surfaced. This satisfies the spec's non-zero-exit scenarios.

## Risks / Trade-offs

- [Writes a file that differs from the original XML (CDATA/namespace/comment loss via `minidom`)] → Acceptable for a pretty-printer; document the limitation in the tool's usage text. Redesign to a lossless printer only if faithful round-tripping becomes a requirement.
- [A wrong or missing `Content-Type` leads to a mis-detection] → First-char sniffing fallback and a clear "unsupported/unknown type" error covers most cases; user can infer the correct type from the error.
- [Network calls can hang] → Rely on `urllib`'s defaults for this minimal tool; a `--timeout` flag is a possible future extension, not in scope now.

## Migration Plan

Not applicable — this is a new standalone utility. Deployment is copying/serving `reader.py`. Rollback is deleting it; there is no integration with existing systems.

## Open Questions

None. Deferrable unknowns (e.g. a `--timeout` flag, output encoding options, an `--indent` flag, converting between formats) are future extensions that do not change the current specs, approach, or task breakdown.