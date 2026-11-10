"""Capture HTTP requests on loopback for a bounded development session."""
import base64
import json
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from common import main, report

MAX_BODY = 1024 * 1024
SENSITIVE = {'authorization', 'proxy-authorization', 'cookie', 'set-cookie', 'x-api-key', 'api-key'}


def run(p):
    """Listen locally for requests; response is 202. Bodies may contain sensitive data."""
    port = int(p.get('port', 8765))
    duration = float(p.get('duration', 30))
    max_requests = int(p.get('max_requests', 10))
    if not 1 <= port <= 65535 or not 1 <= duration <= 300 or not 1 <= max_requests <= 100:
        raise ValueError('Port: 1–65535; duration: 1–300 seconds; requests: 1–100')
    records = []
    deadline = time.monotonic() + duration

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(2)

        def log_message(self, *args):
            pass

        def capture(self):
            if self.headers.get('Transfer-Encoding'):
                self.send_error(501, 'Chunked requests are not supported; send Content-Length')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                self.send_error(400, 'Invalid Content-Length')
                return
            if not 0 <= length <= MAX_BODY:
                self.send_error(413, 'Request body exceeds 1 MiB')
                return
            try:
                body = self.rfile.read(length)
            except (TimeoutError, OSError):
                self.send_error(408, 'Request body timeout')
                return
            if len(body) != length:
                self.send_error(400, 'Incomplete request body')
                return
            headers = {key: '[REDACTED]' if key.lower() in SENSITIVE else value for key, value in self.headers.items()}
            record = {'received_at': datetime.now(timezone.utc).isoformat(), 'method': self.command,
                      'path': self.path, 'headers': headers, 'body_bytes': len(body)}
            try:
                record['body'] = body.decode('utf-8')
                try:
                    record['json'] = json.loads(record['body'])
                except ValueError:
                    pass
            except UnicodeError:
                record['body_base64'] = base64.b64encode(body).decode('ascii')
            records.append(record)
            payload = b'{"received":true}'
            self.send_response(202)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(payload)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = capture

    with HTTPServer(('127.0.0.1', port), Handler) as server:
        server.timeout = .25
        while time.monotonic() < deadline and len(records) < max_requests:
            server.handle_request()
    return report(f'Captured {len(records)} webhook requests', data={
        'listen_url': f'http://127.0.0.1:{port}', 'requests': records,
        'scope': 'Local capture only. Remote senders require your own tunnel. Common credential headers are redacted; bodies, URL queries and custom headers may contain secrets. No requests are replayed.'})


if __name__ == '__main__':
    raise SystemExit(main(run))
