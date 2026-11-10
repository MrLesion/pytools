"""Shared JSON stdin/stdout protocol and bounded HTTP/file input."""
import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse

MAX_BYTES = 25 * 1024 * 1024


def read_source(source, timeout=20, headers=None):
    if urlparse(str(source)).scheme in ('http', 'https'):
        with urlopen(Request(source, headers=headers or {}), timeout=timeout) as response:
            data = response.read(MAX_BYTES + 1)
    else:
        with Path(source).expanduser().open('rb') as stream:
            data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Input exceeds 25 MiB limit; split the input first.')
    return data.decode('utf-8-sig')


def report(summary, issues=None, data=None):
    issues = issues or []
    return {'summary': summary, 'ok': not any(i.get('severity') == 'error' for i in issues),
            'issues': issues, 'data': data if data is not None else {}}


def issue(message, location='', severity='error'):
    return {'severity': severity, 'location': str(location), 'message': message}


def main(run):
    parser = argparse.ArgumentParser(description=run.__doc__)
    parser.add_argument('--input', help='JSON parameters file; otherwise read JSON from stdin')
    args = parser.parse_args()
    try:
        params = json.loads(Path(args.input).read_text(encoding='utf-8') if args.input else sys.stdin.read())
        result = run(params)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0 if result.get('ok', True) else 1
    except Exception as exc:
        print(json.dumps(report('Helper failed', [issue(str(exc))]), ensure_ascii=False))
        return 2
