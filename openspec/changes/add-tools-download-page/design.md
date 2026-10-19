## Context

The repo currently ships two stdlib-only Python CLIs at the project root: `reader.py` (XML/JSON fetch, validate, and pretty-print) and `validate_xml.py` (well-formed XML check). Users have no way to fetch them remotely. The server serving the tools is Apache, and the operator wants a plain HTML page that links each tool for download.

## Goals / Non-Goals

**Goals:**
- A zero-dependency, static `index.html` listing the tools with download links.
- A simple, repeatable way to copy the current tool scripts into the served folder.
- Keep the page trivial to host under any Apache document root.

**Non-Goals:**
- No build tooling, templating, or framework.
- No dynamic/backend behavior — pure static files over Apache.
- Not packaging tools into zip/installers or explaining installation.

## Decisions

- **Serving layout**: A `downloads/` folder holds `index.html`, `reader.py`, and `validate_xml.py`. Apache serves this directory directly; links are relative (`reader.py`, `validate_xml.py`) so any sub-path works without reconfiguration.
- **Static page, no JS**: The page is plain HTML with an embedded `<style>` block. Download links are plain `<a href="...">` anchors, which are the most compatible with Apache's default directory behavior. No client-side scripting needed.
- **Copy, don't move**: The canonical scripts stay at the project root; a command in the README/docs copies them into `downloads/`. This keeps repo authors editing one copy and keeps the served files in sync without special redirects.
- **Why a separate folder vs. serving the repo root**: Keeping served artifacts in `downloads/` avoids exposing the whole repo (e.g. `openspec/`, `.github/`) through Apache and gives a clean document root.

## Risks / Trade-offs

- [Apache may serve `.py` as plain text] → Mitigation: that is what we want (source download); add a short note in the page/README to configure `AddType text/plain .py` if a browser offers to open rather than save.
- [Served files drift from the repo] → Mitigation: document (and make easy) the copy step; the spec ties the served files to the current versions.