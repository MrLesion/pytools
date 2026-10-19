# XML Reader Tools

Small, single-file command-line tools that use only the Python standard library.

- `reader.py` — fetch a URL and pretty-print its XML or JSON, saving the result to a file.
- `validate_xml.py` — validate that an XML file (relative path) is well-formed.
- `validate_json.py` — validate that a JSON file (relative path) is valid.
- `scrape_images.py` — scrape the images on a web page, download them, and save them in a zip archive.

Run either with `python <tool>.py --help`.

## Downloads page

The `downloads/` folder is a self-contained static folder meant to be served
from an Apache web server. It contains `index.html` (the tools download page)
plus a copy of each tool script.

### Serve it with Apache

Point Apache's `DocumentRoot` (or an Alias) at this `downloads/` folder, for
example:

```apache
Alias /tools "C:/path/to/XML reader/downloads"
<Directory "C:/path/to/XML reader/downloads">
    Require all granted
</Directory>
```

Then open `http://your-server/tools/` in a browser. To make sure the `.py`
files are delivered as plain text (so the browser saves rather than opens
them), add this directive:

```apache
AddType text/plain .py
```

### Refresh the served copies

The canonical scripts live in the project root; `downloads/` holds copies. After
editing a tool, refresh the copies so what users download matches the repo:

```bash
Copy-Item reader.py downloads\reader.py
Copy-Item validate_xml.py downloads\validate_xml.py
Copy-Item validate_json.py downloads\validate_json.py
Copy-Item scrape_images.py downloads\scrape_images.py
```

(On Linux/macOS, replace `Copy-Item` with `cp` and backslashes with slashes.)