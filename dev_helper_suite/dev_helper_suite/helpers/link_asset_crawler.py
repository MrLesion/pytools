"""Bounded same-origin HTML crawler and referenced URL checker."""
from collections import deque
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from common import main, report, issue
from dev_plugins_support import http_url


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.base = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'base' and not self.base:
            self.base = attrs.get('href')
        for attribute in (['href'] if tag in ('a', 'link') else ['src', 'poster'] if tag in ('img', 'script', 'video', 'audio', 'source', 'iframe') else []):
            if attrs.get(attribute):
                self.refs.append((attrs[attribute], 'page' if tag == 'a' else 'asset'))


def origin(url):
    parsed = urlparse(url)
    return parsed.scheme.lower(), parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80)


class SameOriginRedirect(HTTPRedirectHandler):
    def __init__(self, allowed):
        self.allowed = allowed

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if origin(newurl) != self.allowed:
            raise ValueError('Cross-origin redirect skipped')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def run(p):
    """Crawl same-origin pages/assets without JavaScript, CSS parsing or form submissions."""
    start = urldefrag(http_url(p['url']))[0]
    limit = int(p.get('max_urls', 50))
    timeout = float(p.get('timeout', 10))
    if not 1 <= limit <= 500 or not 0 < timeout <= 30:
        raise ValueError('max_urls must be 1–500; timeout must be >0 and <=30 seconds')
    allowed = origin(start)
    opener = build_opener(SameOriginRedirect(allowed))
    pending = deque([(start, 'page', None)])
    seen, queued, rows, problems = set(), {start}, [], []
    skipped = 0
    while pending and len(seen) < limit:
        url, kind, parent = pending.popleft()
        seen.add(url)
        row = {'url': url, 'kind': kind, 'found_on': parent}
        try:
            request = Request(url, method='GET' if kind == 'page' else 'HEAD', headers={'User-Agent': 'DevHelperSuite-Crawler/1.0'})
            try:
                response = opener.open(request, timeout=timeout)
            except HTTPError as exc:
                if kind == 'asset' and exc.code in (405, 501):
                    exc.close()
                    response = opener.open(Request(url, headers={'User-Agent': 'DevHelperSuite-Crawler/1.0'}), timeout=timeout)
                else:
                    response = exc
            with response:
                row.update(status=response.code, final_url=response.geturl())
                if response.code >= 400:
                    problems.append(issue(f'HTTP {response.code}', url))
                elif kind == 'page' and 'html' in response.headers.get_content_type():
                    raw = response.read(2 * 1024 * 1024 + 1)
                    parser = Links()
                    parser.feed(raw[:2*1024*1024].decode(response.headers.get_content_charset() or 'utf-8', errors='replace'))
                    base = urljoin(response.geturl(), parser.base or '')
                    for ref, target_kind in parser.refs:
                        target = urldefrag(urljoin(base, ref))[0]
                        if urlparse(target).scheme not in ('http', 'https'):
                            continue
                        if origin(target) != allowed:
                            skipped += 1
                            continue
                        if target not in queued:
                            if len(queued) >= limit:
                                skipped += 1
                                continue
                            queued.add(target)
                            pending.append((target, target_kind, url))
                    if len(raw) > 2*1024*1024:
                        problems.append(issue('HTML truncated at 2 MiB', url, 'warning'))
        except Exception as exc:
            row['error'] = str(exc)
            problems.append(issue(str(exc), url))
        rows.append(row)
    return report(f'Checked {len(rows)} same-origin URLs', problems,
                  {'urls': rows, 'skipped_references': skipped, 'limit': limit,
                   'scope': 'Only rendered server HTML href/src/poster references; excludes external origins, srcset, CSS URLs, JS routes, fragment IDs and authenticated sessions. Only crawl sites you intend to inspect: GET requests may have side effects on poorly designed routes.'})


if __name__ == '__main__':
    raise SystemExit(main(run))
