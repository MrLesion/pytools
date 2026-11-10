"""Pingdom-style HTTP sampling for Developer Helpers (requires helpers/common.py)."""
import math
import time
from datetime import datetime, timezone
from statistics import mean
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from common import issue, main, report

BODY_LIMIT = 1024 * 1024


def run(params):
    """Sample HTTP availability, status, response time and optional page content."""
    url = str(params.get('url', '')).strip()
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Provide a complete HTTP(S) URL.')
    attempts = int(params.get('attempts', 3))
    timeout = float(params.get('timeout', 15))
    interval = float(params.get('interval', 1))
    expected_status = int(params.get('expected_status', 200))
    max_response_ms = float(params.get('max_response_ms', 0))
    expected_text = str(params.get('expected_text') or '')
    if not 1 <= attempts <= 10:
        raise ValueError('Attempts must be between 1 and 10.')
    if not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise ValueError('Timeout must be greater than 0 and at most 30 seconds.')
    if not math.isfinite(interval) or not 0 <= interval <= 10:
        raise ValueError('Interval must be between 0 and 10 seconds.')
    if not 100 <= expected_status <= 599:
        raise ValueError('Expected HTTP status must be between 100 and 599.')
    if not math.isfinite(max_response_ms) or max_response_ms < 0:
        raise ValueError('Maximum response time must be nonnegative; 0 disables it.')

    samples, issues = [], []
    for index in range(attempts):
        if index:
            time.sleep(interval)
        sample = {'sample': index + 1,
                  'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                  'ok': False, 'status': None, 'response_ms': None,
                  'final_url': None, 'failures': []}
        start = time.perf_counter()
        try:
            request = Request(url, headers={'User-Agent': 'DevHelperSuite-Uptime/1.0',
                                           'Accept-Encoding': 'identity'})
            try:
                response = urlopen(request, timeout=timeout)
            except HTTPError as exc:
                # HTTP errors are responses too; inspect their status/body.
                response = exc
            with response:
                sample['headers_ms'] = round((time.perf_counter() - start) * 1000, 2)
                sample['status'] = response.code
                sample['final_url'] = response.geturl()
                raw = response.read(BODY_LIMIT + 1)
                sample['response_ms'] = round((time.perf_counter() - start) * 1000, 2)
                sample['body_truncated'] = len(raw) > BODY_LIMIT
                sample['bytes_inspected'] = min(len(raw), BODY_LIMIT)
                if expected_text:
                    body = raw[:BODY_LIMIT].decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
                    sample['text_found'] = expected_text in body
                    if not sample['text_found']:
                        sample['failures'].append('Expected text absent from first 1 MiB of response')
            if sample['status'] != expected_status:
                sample['failures'].append(f"Expected HTTP {expected_status}, received {sample['status']}")
            if max_response_ms and sample['response_ms'] > max_response_ms:
                sample['failures'].append(f"Response exceeded {max_response_ms:g} ms")
        except Exception as exc:
            sample['failures'].append(str(exc))
        sample['elapsed_ms'] = round((time.perf_counter() - start) * 1000, 2)
        sample['ok'] = not sample['failures']
        for failure in sample['failures']:
            issues.append(issue(failure, f'sample {index + 1}: {url}'))
        samples.append(sample)

    passed = sum(sample['ok'] for sample in samples)
    timings = [sample['response_ms'] for sample in samples if sample['response_ms'] is not None]
    data = {
        'url': url, 'samples': samples, 'passed': passed, 'failed': attempts - passed,
        'sample_success_percent': round(passed / attempts * 100, 2),
        'response_time_ms': {'min': min(timings), 'mean': round(mean(timings), 2),
                             'max': max(timings)} if timings else None,
        'timing_scope': 'Request through reading up to the first 1 MiB of the response body. Failed/incomplete reads are excluded from response-time aggregates; elapsed_ms includes failures.',
        'scope': 'HTTP GET samples from this computer; redirects followed and TLS verified. No ICMP, JavaScript execution, scheduling, alerts or historical uptime. Timeout applies to socket operations, not a total wall-clock deadline.'
    }
    return report(f'{passed}/{attempts} HTTP checks passed ({data["sample_success_percent"]:g}%)', issues, data)


if __name__ == '__main__':
    raise SystemExit(main(run))
