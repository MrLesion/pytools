## 1. Progress bar

- [x] 1.1 Change `fetch()` to read the response body in chunks and accumulate bytes, while capturing the total size from `Content-Length`
- [x] 1.2 Render a tty-aware progress bar on `stderr` (percentage when total is known, byte counter otherwise), guarding against unknown/zero size and non-interactive stdout/stderr
- [x] 1.3 Ensure the bar is cleared/finished with a newline so it never corrupts stdout output or error messages

## 2. Default save to output folder

- [x] 2.1 Add a helper that derives a filesystem-safe filename from the URL (host + sanitized path, `document` fallback) using `urllib.parse`
- [x] 2.2 When `-o` is omitted, create the `output/` directory (if missing) and save the formatted document to `output/<derived-name>.<detected-ext>`, while still printing to stdout

## 3. Extension auto-derive for `-o`

- [x] 3.1 When `-o <path>` is given with no extension, append `.xml` or `.json` per the detected type
- [x] 3.2 When `-o <path>` already has an extension, write to the path exactly as given

## 4. Output messaging & CLI

- [x] 4.1 Update `argparse` help text (`-o` extension behavior and default `output/` save) in `reader.py`
- [x] 4.2 Print an informative "saved to <path>" line to stderr when a file is written

## 5. Verification

- [x] 5.1 Run against a real XML URL: progress bar appears (if tty) or is cleanly skipped (non-tty), stdout shows XML, an `output/<name>.xml` file is created
- [x] 5.2 Run against a real JSON URL: an `output/<name>.json` file is created with valid JSON
- [x] 5.3 Run with `-o out` (no extension) for a JSON document: writes `out.json`; run with `-o out.custom`: writes `out.custom` unchanged
- [x] 5.4 Run `python reader.py --help` and confirm the CLI surface/help matches the updated behavior
