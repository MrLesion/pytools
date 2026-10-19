#!/usr/bin/env python3
"""Fetch a URL and pretty-print its XML or JSON, saving the result to a file.

Usage:
    python reader.py <url> [-o <file>]

By default the formatted document is printed to stdout and saved into the
output/ folder, named from the URL with an extension matching the detected
type (.xml or .json). With -o <file>, the document is written to that path;
if the path has no extension, the detected type extension is appended. A
download progress bar is shown on stderr while the body is being fetched.

Uses only the Python standard library. Auto-detects XML vs JSON from the HTTP
Content-Type header, falling back to sniffing the first non-whitespace
character ('<' for XML, '{' or '[' for JSON).

Note: XML pretty-printing relies on minidom, which does not preserve CDATA
sections and is not a faithful round-trip of namespaces/comments. This is
acceptable for a scratch pretty-printer.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse
from xml.dom import minidom
from xml.parsers import expat

USER_AGENT = "xml-json-reader/1.0"
INDENT = "  "
CHUNK_SIZE = 64 * 1024
OUTPUT_DIR = "output"
DEFAULT_TIMEOUT = 30.0


def _charset(content_type):
    """Extract an explicit charset from a Content-Type header, if any."""
    if not content_type:
        return None
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("charset="):
            value = part.split("=", 1)[1].strip().strip('"')
            return value or None
    return None


def detect_type(content_type, body_bytes):
    """Return 'xml', 'json', or None based on the header, else first-char sniffing."""
    if content_type:
        media = content_type.split(";")[0].strip().lower()
        if "xml" in media:
            return "xml"
        if "json" in media:
            return "json"
    leading = body_bytes.lstrip().decode("latin-1", errors="replace")[:1]
    if not leading:
        return None
    if leading == "<":
        return "xml"
    if leading in "{[":
        return "json"
    return None


def _show_progress(done, total):
    """Render a one-line progress indicator on stderr, if it is a terminal."""
    if not sys.stderr.isatty():
        return
    if total:
        percent = min(100.0, done * 100.0 / total)
        filled = int(percent // 2)
        bar = ("=" * filled + ">").ljust(50)
        sys.stderr.write(f"\r[{bar}] {percent:5.1f}% ({done}/{total} bytes)")
    else:
        sys.stderr.write(f"\rDownloaded {done} bytes")
    sys.stderr.flush()


def _derive_filename(url):
    """Return a filesystem-safe name derived from the URL (host + path)."""
    parsed = urlparse(url)
    base = (parsed.hostname or "") + (parsed.path or "")
    cleaned = "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in base)
    cleaned = cleaned.strip(".-")
    return cleaned or "document"


def _ensure_extension(path, doc_type):
    """Append '.' + doc_type to path when it has no usable extension."""
    base, ext = os.path.splitext(path)
    if not ext or ext == ".":
        return base + "." + doc_type
    return path


def fetch(url, timeout=None):
    """Fetch url with progress reporting and return (content_type, body_bytes)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type")
        raw_total = response.headers.get("Content-Length")
        total = None
        if raw_total:
            try:
                total = int(raw_total)
            except ValueError:
                total = None
        tty = sys.stderr.isatty()
        body = bytearray()
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            body.extend(chunk)
            if tty:
                _show_progress(len(body), total)
        if tty:
            sys.stderr.write("\n")
            sys.stderr.flush()
        return content_type, bytes(body)


def _decode_text(body_bytes, content_type):
    """Decode bytes to text, honoring the header charset with sane fallbacks."""
    charset = _charset(content_type)
    if charset:
        try:
            return body_bytes.decode(charset)
        except (LookupError, UnicodeDecodeError):
            pass
    for encoding in ("utf-8", "latin-1"):
        try:
            return body_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return body_bytes.decode("utf-8", errors="replace")


def pretty_print(doc_type, body_bytes, content_type):
    """Validate and pretty-print the body for the given detected type."""
    if doc_type == "xml":
        dom = minidom.parseString(body_bytes)
        return dom.toprettyxml(indent=INDENT)
    text = _decode_text(body_bytes, content_type)
    return json.dumps(json.loads(text), indent=2)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reader",
        description=(
            "Fetch a URL and pretty-print its XML or JSON, saving the result "
            "to a file."
        ),
        epilog=(
            "Note: without -o, the document is saved into the output/ folder "
            "using a name derived from the URL. XML pretty-printing does not "
            "preserve CDATA sections or exactly reproduce namespaces/comments."
        ),
    )
    parser.add_argument("url", help="URL of the XML or JSON document to fetch")
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help=(
            "write the formatted document to FILE; if FILE has no extension, "
            "the detected type extension (.xml/.json) is appended"
        ),
    )
    parser.add_argument(
        "--timeout",
        metavar="SECONDS",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"request timeout in seconds (default: {DEFAULT_TIMEOUT:g})",
    )
    args = parser.parse_args(argv)

    try:
        content_type, body_bytes = fetch(args.url, timeout=args.timeout)
    except urllib.error.HTTPError as exc:
        print(
            f"error: failed to fetch {args.url}: HTTP {exc.code} {exc.reason}",
            file=sys.stderr,
        )
        return 1
    except urllib.error.URLError as exc:
        print(f"error: failed to fetch {args.url}: {exc.reason}", file=sys.stderr)
        return 1
    except TimeoutError:
        print(f"error: timed out fetching {args.url}", file=sys.stderr)
        return 1

    doc_type = detect_type(content_type, body_bytes)
    if doc_type is None:
        print(
            "error: could not determine whether the content is XML or JSON; "
            "unsupported or empty body",
            file=sys.stderr,
        )
        return 1

    try:
        formatted = pretty_print(doc_type, body_bytes, content_type)
    except expat.ExpatError as exc:
        print(f"error: content is not well-formed XML: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: content is not valid JSON: {exc}", file=sys.stderr)
        return 1

    if args.output:
        out_path = _ensure_extension(args.output, doc_type)
    else:
        out_path = os.path.join(
            OUTPUT_DIR, _derive_filename(args.url) + "." + doc_type
        )
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(formatted)
    except OSError as exc:
        print(f"error: could not write to {out_path}: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(formatted)
    if not sys.stdout.isatty() and not formatted.endswith("\n"):
        sys.stdout.write("\n")
    print(f"saved to {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("error: interrupted by user", file=sys.stderr)
        sys.exit(130)