## Why

The project has two command-line tools (`reader.py`, `validate_xml.py`), but they live only in the repo. There is no easy way to distribute them to users. A small HTML download page lets users fetch each tool directly from an Apache web server in the browser.

## What Changes

- Add a self-contained static HTML page (`index.html` in a `downloads/` folder) that lists the available tools and provides a working download link for each.
- The page is served from Apache so each link points to the corresponding `.py` file placed alongside the page.
- Provide an extraction step that copies the current tool scripts into the download folder, so the served files stay in sync with the repo.

## Capabilities

### New Capabilities
- `tools-download-page`: A static HTML page listing the project's tools, each with a download link that lets a browser retrieve the tool script from the Apache-served folder.

### Modified Capabilities
<!-- No existing capabilities are changed. -->

## Impact

- Adds `downloads/index.html` (new static page) and copies `reader.py` / `validate_xml.py` into `downloads/`.
- No new third-party dependencies; the page is plain HTML/CSS with no build step.
- No changes to existing tool behavior or specs (`reader.py` and `validate_xml.py` stay in the project root and are copied, not moved).