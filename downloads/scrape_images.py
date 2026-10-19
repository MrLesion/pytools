#!/usr/bin/env python3
"""Scrape the images on a web page, download them, and save them in a zip file.

Usage:
    python scrape_images.py <url> [-o FILE] [--max N] [--min-bytes N] [--timeout SECONDS]

The page's HTML is fetched, every <img> src is collected (relative URLs are
resolved against the page URL and duplicates are dropped), each image is
downloaded, and they are bundled into a zip archive named image_0001.ext, ... .
Without -o the archive is saved into the output/ folder using a name derived
from the URL (with a .zip extension). Uses only the Python standard library.

Options:
    -o, --output FILE     write the zip archive to FILE; if FILE has no
                          extension, .zip is appended
    --max N               stop after downloading at most N images
    --min-bytes N         skip any image whose body is smaller than N bytes
    --timeout SECONDS     request timeout in seconds (default: 30)
    --wait SECONDS        wait N seconds after the first fetch, then re-fetch the
                          page and merge any images it now reports (approximates a
                          delay for JS-rendered srcs; does NOT execute JavaScript)
"""

import argparse
import io
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

USER_AGENT = "xml-json-reader/1.0"
CHUNK_SIZE = 64 * 1024
OUTPUT_DIR = "output"
DEFAULT_TIMEOUT = 30.0

# Fallback extension when the URL path has none, keyed by image content type.
CONTENT_TYPE_EXTS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "image/avif": ".avif",
}


class ImageParser(HTMLParser):
    """Collect <img> srcs/srcsets, script/link srcs, and inline <script> bodies."""

    def __init__(self):
        super().__init__()
        self.images = []
        self.scripts = []      # src of external <script> tags
        self.stylesheets = []  # href of <link rel=stylesheet> tags
        self.inline_scripts = []
        self._in_script = 0

    @staticmethod
    def _get_attr(attrs, name):
        for key, value in attrs:
            if key.lower() == name and value:
                return value.strip()
        return None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "img":
            src = self._get_attr(attrs, "src")
            if src:
                self.images.append(src)
            srcset = self._get_attr(attrs, "srcset")
            if srcset:
                for part in srcset.split(","):
                    url = part.strip().split()
                    if url:
                        self.images.append(url[0])
        elif tag == "script":
            src = self._get_attr(attrs, "src")
            if src:
                self.scripts.append(src)
            self._in_script += 1
        elif tag == "link":
            rel = (self._get_attr(attrs, "rel") or "").lower().split()
            href = self._get_attr(attrs, "href")
            if href and "stylesheet" in rel:
                self.stylesheets.append(href)

    def handle_data(self, data):
        if self._in_script:
            self.inline_scripts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._in_script:
            self._in_script -= 1


# Matches a quoted string that looks like an image URL/path (ends with an image
# file extension), e.g. found inside JS or CSS. Relative and //-rooted paths are
# resolved later against the document/bundle URL.
IMAGE_URL_RE = re.compile(
    r"""["']((?:https?://|[^"'\s]+/)?[^"'\s]*?\.(?:jpe?g|png|webp|gif|avif|svg|bmp)(?:\?[^"'\s]*)?)["']""",
    re.IGNORECASE,
)


def _extract_image_urls(text):
    """Return candidate image URL strings referenced inside JS/CSS text."""
    return [m.group(1) for m in IMAGE_URL_RE.finditer(text)]


def fetch(url, timeout=None):
    """Fetch url and return the raw response bytes."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    response = urllib.request.urlopen(request, timeout=timeout)
    return response.read()


def _derive_filename(url):
    """Return a filesystem-safe name derived from the URL (host + path)."""
    parsed = urlparse(url)
    base = (parsed.hostname or "") + (parsed.path or "")
    cleaned = "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in base)
    cleaned = cleaned.strip(".-")
    return cleaned or "document"


def _ensure_extension(path, ext="zip"):
    """Append '.' + ext to path when it has no usable extension."""
    base, current = os.path.splitext(path)
    if not current or current == ".":
        return base + "." + ext
    return path


def _ext_for(url, content_type):
    """Pick a filename extension for an image, from its URL path or content type."""
    path_ext = os.path.splitext(urlparse(url).path)[1]
    if path_ext and (path_ext == "." or len(path_ext) > 1):
        return path_ext
    if content_type:
        media = content_type.split(";")[0].strip().lower()
        return CONTENT_TYPE_EXTS.get(media, "")
    return ""


def _download(url, timeout):
    """Download url, returning (data, content_type). Raises on network errors."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        data = io.BytesIO()
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            data.write(chunk)
        return data.getvalue(), content_type
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="scrape_images",
        description="Scrape the images on a web page, download them, and save "
        "them in a zip file.",
        epilog=(
            "Note: without -o, the archive is saved into the output/ folder "
            "using a name derived from the URL."
        ),
    )
    parser.add_argument("url", help="URL of the web page to scrape images from")
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help=(
            "write the zip archive to FILE; if FILE has no extension, .zip is "
            "appended"
        ),
    )
    parser.add_argument(
        "--max",
        metavar="N",
        type=int,
        default=0,
        help="stop after downloading at most N images (default: no limit)",
    )
    parser.add_argument(
        "--min-bytes",
        metavar="N",
        type=int,
        default=0,
        help="skip any image whose body is smaller than N bytes (default: 0)",
    )
    parser.add_argument(
        "--timeout",
        metavar="SECONDS",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"request timeout in seconds (default: {DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument(
        "--wait",
        metavar="SECONDS",
        type=float,
        default=0.0,
        help=(
            "wait N seconds after the first fetch, then re-fetch the page and "
            "merge any images it now reports, to pick up dynamically loaded "
            "srcs; does NOT execute JavaScript"
        ),
    )
    args = parser.parse_args(argv)

    if args.max < 0 or args.min_bytes < 0:
        print("error: --max and --min-bytes must not be negative", file=sys.stderr)
        return 1
    if args.wait < 0:
        print("error: --wait must not be negative", file=sys.stderr)
        return 1

    try:
        html = fetch(args.url, timeout=args.timeout)
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

    if args.wait > 0:
        print(
            f"waiting {args.wait:g}s then re-fetching to pick up dynamic images...",
            file=sys.stderr,
        )
        time.sleep(args.wait)
        try:
            more_html = fetch(args.url, timeout=args.timeout)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            print("warning: re-fetch after --wait failed; using first response", file=sys.stderr)
        else:
            html += b"\n" + more_html

    html_parser = ImageParser()
    html_parser.feed(html.decode("utf-8", errors="replace"))

    seen = set()
    targets = []

    def add_image(reference, base):
        try:
            absolute = urljoin(base or args.url, reference)
        except ValueError:
            return
        if urlparse(absolute).scheme.lower() not in ("http", "https"):
            return
        if absolute not in seen:
            seen.add(absolute)
            targets.append(absolute)

    # 1) <img> src/srcset attributes.
    for src in html_parser.images:
        add_image(src, args.url)

    # 2) Inline <script> bodies (may build image URLs directly in the page).
    for body in html_parser.inline_scripts:
        for ref in _extract_image_urls(body):
            add_image(ref, args.url)

    # 3) External JS bundles referenced by <script src>.
    for script_src in html_parser.scripts:
        bundle_ref = urljoin(args.url, script_src)
        try:
            code = fetch(bundle_ref, timeout=args.timeout)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            print(f"warning: could not fetch script {bundle_ref}", file=sys.stderr)
            continue
        refs = _extract_image_urls(code.decode("utf-8", errors="replace"))
        print(
            f"scanned {bundle_ref}: {len(refs)} image reference(s)",
            file=sys.stderr,
        )
        for ref in refs:
            add_image(ref, bundle_ref)

    # 4) External stylesheets (background-image / content-image URL()).
    for css_href in html_parser.stylesheets:
        css_ref = urljoin(args.url, css_href)
        try:
            css_bytes = fetch(css_ref, timeout=args.timeout)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            print(f"warning: could not fetch stylesheet {css_ref}", file=sys.stderr)
            continue
        refs = _extract_image_urls(css_bytes.decode("utf-8", errors="replace"))
        print(
            f"scanned {css_ref}: {len(refs)} image reference(s)",
            file=sys.stderr,
        )
        for ref in refs:
            add_image(ref, css_ref)

    if not targets:
        print(
            f"error: no images found on {args.url} (no <img> tags, and no image "
            "references found in scripts or stylesheets)",
            file=sys.stderr,
        )
        return 1
    if args.max:
        targets = targets[: args.max]

    if args.output:
        out_path = _ensure_extension(args.output, "zip")
    else:
        out_path = os.path.join(OUTPUT_DIR, _derive_filename(args.url) + ".zip")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    saved = 0
    skipped = 0
    failed = 0
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for index, image_url in enumerate(targets, start=1):
                try:
                    data, content_type = _download(image_url, args.timeout)
                except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
                    print(f"warning: could not download {image_url}", file=sys.stderr)
                    failed += 1
                    continue
                if args.min_bytes and len(data) < args.min_bytes:
                    print(
                        f"skip {image_url}: too small ({len(data)} bytes)",
                        file=sys.stderr,
                    )
                    skipped += 1
                    continue
                ext = _ext_for(image_url, content_type)
                entry = f"image_{index:04d}{ext}"
                zf.writestr(entry, data)
                print(
                    f"added {entry} from {image_url} ({len(data)} bytes)",
                    file=sys.stderr,
                )
                saved += 1
    except OSError as exc:
        print(f"error: could not write to {out_path}: {exc}", file=sys.stderr)
        return 1

    if saved == 0:
        print(
            f"error: no images could be downloaded from {args.url}",
            file=sys.stderr,
        )
        try:
            os.remove(out_path)
        except OSError:
            pass
        return 1

    print(
        f"saved {saved} image(s) ({skipped} skipped, {failed} failed) to {out_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("error: interrupted by user", file=sys.stderr)
        sys.exit(130)