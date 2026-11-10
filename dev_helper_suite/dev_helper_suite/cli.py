"""Run any catalog helper from a command line."""
import argparse
import subprocess
import sys
from catalog import ROOT, load_catalog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('helper', nargs='?', help='Helper ID; omit to list available helpers')
    parser.add_argument('--input', help='Path to JSON parameters; omit to read stdin')
    args = parser.parse_args()
    catalog = load_catalog()
    if not args.helper:
        for item in catalog:
            print(f'{item["id"]:24} {item["description"]}')
        return 0
    item = next((x for x in catalog if x['id'] == args.helper), None)
    if not item:
        parser.error('Unknown helper ID')
    command = [sys.executable, item['_script']]
    if args.input:
        command += ['--input', str(__import__('pathlib').Path(args.input).resolve())]
    return subprocess.call(command, cwd=ROOT)


if __name__ == '__main__':
    raise SystemExit(main())
