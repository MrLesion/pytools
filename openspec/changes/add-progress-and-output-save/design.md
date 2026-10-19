## Context

See proposal.md - Why. `reader.py` is a single-file, stdlib-only CLI. It fetches a URL, auto-detects XML vs. JSON, validates, pretty-prints, and prints to stdout or writes to the `-o` path. This change adds a download progress bar and makes saving to the `output/` folder the default, with extensions derived from the detected type. A related change (`url-xml-json-reader`) defines the existing `xml-json-reader` capability but is not yet archived, so there is no base spec in `openspec/specs/` yet; that change should be archived before/after this one lands so the MODIFIED delta has a base to merge against.

## Goals / Non-Goals

**Goals:**
- Live, byte-based progress feedback while downloading, using only stdlib.
- Default to saving into the `output/` folder so a plain `reader.py <url>` call persists a file.
- Auto-append `.xml`/`.json` to `-o` paths that lack an extension.
- Preserve the existing CLI surface and stdout-by-default behavior.

**Non-Goals:**
- No GUI/rich-dependency progress; a simple tty-aware bar (falls back cleanly when stdout is not a terminal or when total size is unknown).
- No format conversion; extensions only reflect the detected source format.
- No resume/abort handling, no multi-URL downloads.

## Decisions

**Progress bar: manual `\r`-based bar on stderr, gated by total-size availability and tty detection.**
The original fetch reads the whole body at once via `response.read()`. To show progress, read in chunks (`iter(lambda: response.read(65536), b"")`) and accumulate bytes; when a `Content-Length` is present, print a percentage bar (`\r` + spaces to clear), otherwise print a byte counter or nothing extra. Printed to `stderr` so progress never pollutes the formatted output on `stdout`. Use `sys.stderr.isatty()` to enable the live bar only when interactive, and guard against `Content-Length: 0` / division by zero. Alternatives considered: the third-party `tqdm` (violates zero-dep goal) — rejected.

**Default save path: `output/` folder at the project root, derived from the URL host/path.**
When `-o` is omitted, the tool constructs a filename from the URL (host + sanitized path), falls back to `document`, appends the detected extension, and writes it inside `output/`. The directory is created if missing (`os.makedirs(..., exist_ok=True)`). This implements "save to the output folder as xml/json" without extra CLI flags. Alternatives: deriving only from the host (too generic) — rejected in favor of host+path for uniqueness.

**Extension auto-derive: split the `-o` value on the last dot; `os.path.splitext` informs whether an extension exists, append detected type otherwise.**
Simpler than a regex: if the provided `-o` path has no recognized suffix (no dot, or an empty/trailing-dot name), append `.xml` or `.json` per `doc_type`. If it already has any extension, leave it untouched (spec: "Existing extension is preserved"). Trade-off: an explicit `-o out.txt` is kept as `out.txt` even though it won't match the detected type; that is user intent and documented.

**Filename sanitization from URL: strip scheme, take host and path, replace punctuation with `-`.**
`urllib.parse.urlparse(url)` gives `.hostname` and `.path`; combine them, collapse non `[A-Za-z0-9._-]` to `-`, trim runs/dashes, and fall back to `document` if empty. Ensures the derived name is filesystem-safe. Alternative: hashing the URL — opaque, less useful — rejected.

## Risks / Trade-offs

- [Progress bar output interleaves with stderr error messages] → Progress uses `\r` on the same stderr stream and ends with a newline; errors print on the next line. Acceptable.
- [Server reports no/compressed `Content-Length`, so no percentage] → Fall back to a bytes-downloaded counter, still gated on tty; never fail.
- [Auto-save dependency on a base-captured spec (unarchived `url-xml-json-reader`)] → Archive that change first; the delta format is unaffected and merges cleanly.
- [Derived default filename collides across similar URLs] → host+path yields distinct names; overwrites are accepted for a scratch tool and noted to the user in an "saved to" line.

## Migration Plan

Not applicable — incremental change to an existing standalone script. Rollback is reverting `reader.py` to the previous version; the `output/` folder is additive.

## Open Questions

None. Deferrable unknowns (e.g. a `--no-save` flag, custom output dir, colors) are future extensions that do not change the specs, approach, or task breakdown.