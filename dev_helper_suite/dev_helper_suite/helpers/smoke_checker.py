"""Check HTTP status, content and elapsed time for a list of URLs."""
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from common import main, issue, report


def run(p):
    """HTTP smoke checks (server HTML, without executing JavaScript)."""
    urls = p.get('urls', [])
    if isinstance(urls, str):
        urls = [x.strip() for x in urls.splitlines() if x.strip()]
    if not urls:
        raise ValueError('Provide at least one URL.')
    expected = int(p.get('expected_status', 200))
    timeout = float(p.get('timeout', 15))
    issues, rows = [], []
    for url in urls:
        start = time.monotonic()
        row = {'url': url}
        try:
            if urlparse(url).scheme not in ('http', 'https'):
                raise ValueError('Only HTTP(S) URLs are supported.')
            try:
                response = urlopen(Request(url, headers={'User-Agent': 'DevHelperSuite/1.0'}), timeout=timeout)
            except HTTPError as exc:
                response = exc
            with response:
                row.update(status=response.code, final_url=response.geturl())
                raw = response.read(2 * 1024 * 1024 + 1)
                body = raw.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
            if row['status'] != expected:
                issues.append(issue(f"Expected {expected}, received {row['status']}", url))
            if p.get('expected_text') and p['expected_text'] not in body:
                issues.append(issue('Expected text absent from first 2 MiB of response', url))
            if len(raw) > 2 * 1024 * 1024:
                issues.append(issue('Body truncated at 2 MiB for text inspection', url, 'warning'))
        except Exception as exc:
            row['error'] = str(exc)
            issues.append(issue(str(exc), url))
        row['elapsed_ms'] = round((time.monotonic() - start) * 1000)
        rows.append(row)
    return report(f'Checked {len(rows)} URLs', issues, rows)


if __name__ == '__main__':
    raise SystemExit(main(run))
