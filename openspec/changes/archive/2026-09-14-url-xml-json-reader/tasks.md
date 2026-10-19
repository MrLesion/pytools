## 1. Setup

- [x] 1.1 Create `reader.py` at the project root with an `argparse` CLI: positional `url` and optional `-o/--output` (`--help` works, bad usage exits non-zero)

## 2. Fetching

- [x] 2.1 Implement URL fetch with `urllib.request`, setting a non-default `User-Agent` header and reading the response body and `Content-Type`
- [x] 2.2 Handle request errors (`URLError`/`HTTPError`): print a clear message to stderr and exit non-zero

## 3. Detection

- [x] 3.1 Implement type detection: prefer `Content-Type` header (`xml`/`json`), else fall back to first non-whitespace char (`<` → XML, `{`/`[` → JSON); fail with a clear error if undetectable

## 4. Parsing & Pretty-print

- [x] 4.1 For XML: validate + pretty-print with `xml.dom.minidom` `toprettyxml(indent="  ")`; catch `ExpatError` → clear error, non-zero exit
- [x] 4.2 For JSON: validate + pretty-print with `json.loads` then `json.dumps(indent=2)`; catch `JSONDecodeError` → clear error, non-zero exit

## 5. Output

- [x] 5.1 Print the formatted document to stdout by default
- [x] 5.2 When `-o <file>` is given, write the formatted document to that file; surface write failures clearly

## 6. Verification

- [x] 6.1 Test against a real XML URL: prints/saves pretty-printed XML, exit 0
- [x] 6.2 Test against a real JSON URL: prints/saves pretty-printed JSON, exit 0
- [x] 6.3 Test error paths: 404, unreachable host, malformed XML body, invalid JSON body each print a clear message and exit non-zero
- [x] 6.4 Run `python reader.py --help` and confirm the CLI surface matches the spec