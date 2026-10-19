#!/usr/bin/env python3
"""Validate that a JSON file (given as a relative path) is valid.

Usage:
    python validate_json.py <path>

Prints an "OK" message and exits 0 when the content is valid JSON; prints a
clear error to stderr (with line/column when available) and exits non-zero
otherwise. Uses only the Python standard library.
"""

import argparse
import json
import sys


def validate(path):
    """Parse path as JSON and return (ok, message)."""
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            json.load(fh)
    except json.JSONDecodeError as exc:
        line, col = exc.lineno, exc.colno
        reason = exc.msg or "not valid JSON"
        if line > 0:
            return False, f"{path}:{line}:{col}: {reason}"
        return False, f"{path}: {reason}"
    except OSError as exc:
        return False, f"{path}: {exc}"
    return True, ""


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate_json",
        description="Validate that a JSON file (relative path) is valid.",
    )
    parser.add_argument("path", help="relative path to the JSON file to validate")
    args = parser.parse_args(argv)

    ok, message = validate(args.path)
    if ok:
        print(f"OK: {args.path} is valid JSON")
        return 0
    print(f"error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())