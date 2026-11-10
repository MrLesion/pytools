# Developer Helpers

A minimal Python/Tkinter desktop toolbox for .NET and JavaScript development.
Eight working helpers, a JSON catalog, dynamic input forms, examples, JSON reports,
a command-line runner and cancellable background execution.

## Start

Requires Python 3.10+ with Tkinter. On Windows, use a Python installation with
Tcl/Tk support and double-click `start.bat`, or run:

```sh
python app.py
```

On Linux install your distribution's `python3-tk` package if needed, then run
`./start.sh`. On macOS use a Python build that includes Tkinter.
No pip dependencies are required for the desktop app or offline helpers.

For **live browser tracking capture** only:

```sh
python -m pip install -r requirements-browser.txt
python -m playwright install chromium
```

Linux browser hosts may also require Playwright's OS dependencies.

Select a helper, fill the form and click **Run helper**. See **Examples & code**
for usage and input JSON. **Load inputs** loads a parameter file; **Export result**
saves the complete JSON report. Browse selects a file; paste a directory into
Log investigator's path field to scan a folder. Relative paths resolve from
the application directory. Inputs are not persisted automatically.

Tracking defaults to the included saved-event example. Clear the Source field
to enable browser capture, enter a URL, and interact with the opened browser
within the capture period. A new browser profile is used each run: make any
consent selections yourself. The tool never automatically clicks consent or
checkout buttons. It observes the default `window.dataLayer` in the main page,
including pushes after reassignment and full-page navigation; custom layer names,
iframes, server-side tracking and GA4 receipt are outside its scope.

## Pip & setup

The desktop app includes a **Pip & setup** tab listing requirements and install
commands. The same instructions are in `SETUP.txt`.

| File | Purpose |
| --- | --- |
| `requirements.txt` | Core app and offline helpers; no pip dependencies |
| `requirements-browser.txt` | Optional Playwright dependency |
| `requirements-all.txt` | Both requirement sets |
| `install.bat` / `install.sh` | Create `.venv`, install core requirements, check Tkinter |
| `install.bat --browser` / `./install.sh --browser` | Also install Playwright and Chromium |

The start scripts automatically use `.venv` when present. Tkinter and venv
support must be provided by your Python/OS installation; pip cannot install
Tkinter. On Linux you may need `python3-tk` and `python3-venv` packages.

```bat
install.bat --browser
start.bat
```

```sh
./install.sh --browser
./start.sh
```

## XML and JSON validators

Select **input** mode to paste document content, **url** to fetch HTTP(S), or
**file** to browse a local document. Only the selected mode is read; changing
to URL mode ignores the sample pasted content. Requests use normal TLS checks
and a configurable timeout. All inputs have a 25 MiB limit.

The JSON validator reports syntax errors with line and column, rejects duplicate
keys and nonstandard NaN/Infinity values, and optionally returns formatted JSON.
Very large exponents outside Python's finite floating-point range and excessive
nesting are reported as unsupported. Standard scalar JSON roots are allowed.
JSON Schema validation is not included.

The XML validator checks well-formedness, including namespace bindings, and
reports the root, element/attribute counts and maximum depth. URL/file input
preserves XML byte encoding. Error columns are reported using one-based indexing
(the parser's native error message may also contain its zero-based column).
DTDs/entity declarations and nesting beyond 256 levels are rejected; XSD/DTD
schema validation is not included. Built-in entities such as `&amp;` work.

```sh
python cli.py json-validator --input examples/json-validator.json
python cli.py xml-validator --input examples/xml-validator.json
```

URL parameter example (save as a JSON file and pass it with `--input`):

```json
{"mode": "url", "url": "https://example.com/data.json", "timeout": 20}
```

## Command line

Run commands from this directory:

```sh
python cli.py
python cli.py log-investigator --input examples/log-investigator.json
python cli.py feed-auditor --input examples/feed-auditor.json
python cli.py tracking-inspector --input examples/tracking-inspector.json
python cli.py test-data-generator --input examples/test-data-generator.json
python cli.py api-comparer --input examples/api-comparer.json
python cli.py smoke-checker --input examples/smoke-checker.json
```

Parameters can also be supplied as JSON on stdin. Standalone scripts accept the
same `--input` switch: `python helpers/feed_auditor.py --input params.json`.
Exit codes: **0** completed without error findings, **1** completed with error
findings, **2** invalid input or execution failure. Warnings alone do not fail.
The report has `summary`, `ok`, `issues` and `data`. Data generator output is
inside `data`; order mode returns customers, products and orders together.
The included API comparison intentionally finds a changed price (exit 1).

## Add a helper

1. Create a Python script under `helpers/`.
2. Add an entry to `helpers.json`.
3. Click **Reload catalog**; no desktop app changes are needed.

```json
{
  "id": "my-helper",
  "name": "My helper",
  "script_path": "helpers/my_helper.py",
  "description": "What this helper does.",
  "example_use": "When and how to use it.",
  "code_example": "python cli.py my-helper --input params.json",
  "fields": [
    {"name": "message", "label": "Message", "type": "text", "default": "Hello", "required": true}
  ]
}
```

```python
from common import main, report


def run(params):
    return report("Finished", data={"message": params["message"]})


if __name__ == "__main__":
    raise SystemExit(main(run))
```

Scripts receive one JSON object on stdin and must print exactly one JSON report
on stdout. Write diagnostic logging to stderr. Helpers are executed using the
same Python interpreter as the app; subprocesses do not use a command shell.
Catalogs/scripts are trusted executable local code, not a sandbox for untrusted
add-ons. Script paths must stay under the catalog directory.

Field types: `text`, `multiline`, `file`, `path`, `int`, `float`, `bool`, `select`,
`json`. Select fields use `options`; any field may specify `required` and
`default`. Use JSON fields for structured inputs such as HTTP headers.

## Helper scope

- **Smoke checker:** HTTP GET, follows redirects, validates final status and
  expected server HTML text, reports elapsed milliseconds. Content check is
  limited to the first 2 MiB. No JavaScript, authentication UI or console checks.
- **Log investigator:** scans `.log`, `.txt`, `.jsonl`; recognizes common .NET
  plain text, Serilog compact JSON and JSON records with level/message fields.
  Groups normalized warning/error text and retains up to three stack-trace
  samples per group. Grouping is heuristic, not a full structured log parser.
- **Tracking inspector:** validates ecommerce event structure, numeric prices,
  quantities, value/currency, purchase transaction IDs and potential repeated
  `view_item`. A structural pass does not prove correct consent or GA4 delivery.
- **Feed auditor:** JSON arrays (including dotted `items_path`), CSV, XML item
  records including namespace-stripped Google-style feeds. Field mappings use
  dotted paths for JSON. Image checks validate URL syntax only. Prices support
  JSON numbers, decimal strings and `149.95 DKK` notation. XML is flat per item;
  repeated/nested XML fields and locale comma prices need preprocessing.
- **Test data:** deterministic synthetic products/customers or linked orders;
  does not connect to a database. It produces normal sample data, not a complete
  suite of checkout edge cases. Emails use example.com.
- **API comparer:** JSON from files or HTTP GET; field names or full dotted paths
  may be ignored. Object arrays use the configured identity field when all
  members have it; other arrays compare positionally. Duplicate IDs fail instead
  of silently overwriting records. Numeric tolerance is absolute; booleans remain
  distinct from numbers. Headers apply to both endpoints.

HTTP inputs have a 25 MiB limit (smoke content inspection uses 2 MiB). Network
helpers retain normal TLS certificate checks. Large local logs are streamed,
although unique groups and retained samples consume memory. Desktop runs have
a 10-minute limit; split large inputs if necessary. Results may contain source
payloads or logs: review them before sharing exported files.

## Development checks

```sh
python -m unittest discover -s tests -v
python -m compileall -q .
```
