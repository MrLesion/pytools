"""Bounded validator input, preserving XML's declared byte encoding."""
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from common import MAX_BYTES


def document_input(params):
    mode = params.get('mode', 'input')
    if mode == 'input':
        text = params.get('content', '')
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Paste document content into the Content field.')
        if len(text.encode('utf-8')) > MAX_BYTES:
            raise ValueError('Input exceeds 25 MiB limit.')
        return text, 'pasted input'
    if mode == 'url':
        url = params.get('url', '').strip()
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise ValueError('Provide a complete HTTP(S) URL.')
        timeout = float(params.get('timeout', 20))
        if not 0 < timeout <= 300:
            raise ValueError('Timeout must be greater than 0 and at most 300 seconds.')
        with urlopen(Request(url, headers={'User-Agent': 'DevHelperSuite/1.1'}), timeout=timeout) as response:
            payload = response.read(MAX_BYTES + 1)
        source = url
    elif mode == 'file':
        path = Path(params.get('path', '')).expanduser()
        with path.open('rb') as stream:
            payload = stream.read(MAX_BYTES + 1)
        source = str(path)
    else:
        raise ValueError('Input mode must be input, url or file.')
    if len(payload) > MAX_BYTES:
        raise ValueError('Input exceeds 25 MiB limit.')
    return payload, source
