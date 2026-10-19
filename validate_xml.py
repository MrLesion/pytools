#!/usr/bin/env python3
"""Validate that an XML file (given as a relative path) is well-formed.

Usage:
    python validate_xml.py <path>

Prints an "OK" message and exits 0 when the file is well-formed XML; prints a
clear error to stderr (with line/column when available) and exits non-zero
otherwise. Uses only the Python standard library.
"""

import argparse
import sys
from xml.etree import ElementTree


def validate(path):
    """Parse path as XML and return (ok, message)."""
    try:
        ElementTree.parse(path)
    except ElementTree.ParseError as exc:
        line, col = exc.position if exc.position else (0, 0)
        reason = exc.msg or "not well-formed XML"
        if line > 0:
            return False, f"{path}:{line}:{col}: {reason}"
        return False, f"{path}: {reason}"
    except OSError as exc:
        return False, f"{path}: {exc}"
    return True, ""


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate_xml",
        description="Validate that an XML file (relative path) is well-formed.",
    )
    parser.add_argument("path", help="relative path to the XML file to validate")
    args = parser.parse_args(argv)

    ok, message = validate(args.path)
    if ok:
        print(f"OK: {args.path} is well-formed XML")
        return 0
    print(f"error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())