"""Integration checks for the optional plugin pack; uses loopback and temporary data."""
import contextlib
import functools
import http.server
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'helpers'))
# Allows testing the unpacked plugin pack beside the original suite.
if not (ROOT / 'helpers/common.py').exists():
    sys.path.append(str(ROOT.parent / 'dev_helper_suite/helpers'))
from razor_template_finder import run as finder
from translation_auditor import run as translations
from deployment_config_checker import run as config
from link_asset_crawler import run as crawl
from webhook_inbox import run as inbox
from release_report_builder import run as release


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_HEAD(self):
        if self.path == '/asset.js':
            self.send_response(200)
        else:
            self.send_response(404)
        self.end_headers()

    def do_GET(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return
        if self.path == '/missing':
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        body = '''<!doctype html><html lang="en"><head><title>Test</title></head><body><main><h1>Demo</h1><label for="name">Name</label><input id="name"><button id="greet" onclick="document.querySelector('#result').textContent='Hello '+document.querySelector('#name').value">Greet</button><p id="result"></p><button id="unnamed"></button><a href="/missing">Broken</a><script src="/asset.js"></script><a href="https://example.org">External</a></main></body></html>'''
        self.wfile.write(body.encode())


@contextlib.contextmanager
def server():
    with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as srv:
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            yield f'http://127.0.0.1:{srv.server_port}'
        finally:
            srv.shutdown()
            thread.join()


class OfflinePlugins(unittest.TestCase):
    def test_entries_match_scripts_and_schema(self):
        entry_dir = ROOT / 'entries'
        if not entry_dir.exists():
            self.skipTest('Entry files not copied into test location')
        entries = json.loads((entry_dir / 'all-entries.json').read_text())
        self.assertEqual(len(entries), 9)
        self.assertEqual(len({e['id'] for e in entries}), 9)
        for entry in entries:
            self.assertTrue((ROOT / entry['script_path']).is_file())
            for key in ('description', 'example_use', 'code_example', 'fields'):
                self.assertTrue(entry[key])
            for path in entry['support_files']:
                self.assertTrue((ROOT / path).is_file(), path)

    def test_template_search_extract_and_exclusions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Product.cshtml').write_text('@Translate("Title", "Product")\n@Html.Partial("Shared/Header")\n@GetString("Ecom:Product.Name")\n')
            (root / 'node_modules').mkdir()
            (root / 'node_modules/skip.cshtml').write_text('@Translate("Skipped")')
            self.assertEqual(finder({'root': tmp, 'mode': 'translations'})['data']['matches'][0]['value'], 'Title')
            self.assertEqual(len(finder({'root': tmp, 'mode': 'translations'})['data']['matches']), 1)
            self.assertEqual(finder({'root': tmp, 'mode': 'includes'})['data']['matches'][0]['value'], 'Shared/Header')
            self.assertTrue(finder({'root': tmp, 'mode': 'search', 'query': 'product'})['data']['matches'])
            self.assertEqual(finder({'root': tmp, 'mode': 'fields'})['data']['matches'][0]['line'], 3)

    def test_translation_json_missing_blank_and_template_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'translations.json'
            source.write_text(json.dumps({'en': {'Product': {'Title': 'Product'}, 'Other': 'Other'}, 'da': {'Product': {'Title': ''}}}))
            (root / 'Page.cshtml').write_text('@Translate("Unknown")')
            result = translations({'source': str(source), 'templates_root': tmp})
            self.assertFalse(result['ok'])
            self.assertTrue(any('Missing translation' in x['message'] for x in result['issues']))
            self.assertTrue(any('unknown translation' in x['message'] for x in result['issues']))

    def test_translation_csv_xml_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'translation.csv'
            source.write_text('language,key,value\nen,Title,Product\nda,Title,Produkt\n')
            self.assertTrue(translations({'source': str(source)})['ok'])
            source.write_text('language,key,value\nen,Title,Product\nen,Title,Duplicate\n')
            self.assertFalse(translations({'source': str(source)})['ok'])
            source = root / 'translation.xml'
            source.write_text('<translations><translation language="en" key="Title">Product</translation></translations>')
            self.assertTrue(translations({'source': str(source)})['ok'])

    def test_config_rules_and_value_redaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'settings.json'
            path.write_text(json.dumps({'Debug': True, 'Api': {'Host': 'https://production'}, 'Secret': 'SENSITIVE'}))
            rules = [{'key': 'Debug', 'op': 'equals', 'value': False}, {'key': 'Api.Host', 'op': 'contains', 'value': 'https'}, {'key': 'Missing', 'op': 'not_equals', 'value': 'x'}, {'key': 'Secret', 'op': 'equals', 'value': 'other'}]
            result = config({'config_path': str(path), 'rules': rules})
            self.assertFalse(result['ok'])
            self.assertEqual(sum(x['passed'] for x in result['data']['checks']), 1)
            self.assertNotIn('SENSITIVE', json.dumps(result))

    def test_config_env_xml_and_rules_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '.env'
            path.write_text('export API_HOST="https://api.example.com"\n')
            rules = [{'key': 'API_HOST', 'op': 'regex', 'value': '^https://'}]
            self.assertTrue(config({'config_path': str(path), 'rules': rules})['ok'])
            path = Path(tmp) / 'web.config'
            path.write_text('<configuration><appSettings><add key="Mode" value="Production"/></appSettings></configuration>')
            rulepath = Path(tmp) / 'rules.json'
            rulepath.write_text(json.dumps([{'key': 'Mode', 'op': 'equals', 'value': 'Production'}]))
            self.assertTrue(config({'config_path': str(path), 'rules_path': str(rulepath)})['ok'])

    def test_crawler_status_assets_and_limits(self):
        with server() as url:
            result = crawl({'url': url, 'max_urls': 10})
            self.assertFalse(result['ok'])
            self.assertTrue(any(row.get('status') == 404 for row in result['data']['urls']))
            self.assertTrue(any(row['url'].endswith('/asset.js') and row['status'] == 200 for row in result['data']['urls']))
            self.assertGreater(result['data']['skipped_references'], 0)
            self.assertEqual(len(crawl({'url': url, 'max_urls': 1})['data']['urls']), 1)

    def test_webhook_capture_json_and_header_redaction(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        result = []
        thread = threading.Thread(target=lambda: result.append(inbox({'port': port, 'duration': 3, 'max_requests': 1})))
        thread.start()
        deadline = time.monotonic() + 2
        while True:
            try:
                with urlopen(Request(f'http://127.0.0.1:{port}/event', data=b'{"event":"test"}', headers={'Authorization': 'secret', 'Content-Type': 'application/json'}), timeout=1) as response:
                    self.assertEqual(response.status, 202)
                break
            except ConnectionRefusedError:
                if time.monotonic() > deadline: raise
                time.sleep(.02)
            except __import__('urllib.error', fromlist=['URLError']).URLError:
                if time.monotonic() > deadline: raise
                time.sleep(.02)
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        request = result[0]['data']['requests'][0]
        self.assertEqual(request['json']['event'], 'test')
        self.assertEqual(request['headers']['Authorization'], '[REDACTED]')

    def test_visual_pixel_threshold_and_dimension_changes(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow unavailable')
        from visual_regression_checker import compare_images
        with tempfile.TemporaryDirectory() as tmp:
            base, actual, diff = [Path(tmp) / (x + '.png') for x in ('baseline', 'actual', 'diff')]
            image = Image.new('RGB', (10, 10), (255, 255, 255))
            image.save(base)
            image.save(actual)
            self.assertTrue(compare_images(base, actual, diff, 16, .1)['ok'])
            image.putpixel((0, 0), (205, 255, 255))
            image.save(actual)
            result = compare_images(base, actual, diff, 16, .1)
            self.assertFalse(result['ok'])
            self.assertEqual(result['data']['difference_percent'], 1.0)
            self.assertEqual(result['data']['changed_pixels'], 1)
            self.assertTrue(compare_images(base, actual, diff, 50, .1)['ok'])
            Image.new('RGB', (20, 10)).save(actual)
            self.assertFalse(compare_images(base, actual, diff, 16, .1)['ok'])

    def test_release_report_real_git_and_failed_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.run(['git', '-C', tmp, *args], check=True, capture_output=True)
            git('init')
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.com')
            (root / 'app.txt').write_text('one')
            git('add', '.')
            git('commit', '-m', 'Initial')
            (root / 'app.txt').write_text('two')
            git('commit', '-am', 'Update app')
            check = root / 'check.json'
            check.write_text(json.dumps({'ok': False, 'summary': 'A check failed', 'issues': [{}]}))
            output = root / 'release.md'
            result = release({'repo_path': tmp, 'report_files': [str(check)], 'output_path': str(output)})
            self.assertFalse(result['ok'])
            self.assertIn('Update app', output.read_text())
            self.assertIn('FAIL', output.read_text())
            self.assertEqual(len(result['data']['commits']), 1)


class BrowserPlugins(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
            cache = Path(os.environ.get('PLAYWRIGHT_BROWSERS_PATH',
                         str(Path(os.environ.get('LOCALAPPDATA', Path.home() / '.cache')) / 'ms-playwright')))
            if sys.platform == 'darwin' and 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ:
                cache = Path.home() / 'Library/Caches/ms-playwright'
            if not cache.exists() or not list(cache.glob('chromium-*')):
                raise unittest.SkipTest('Chromium binary unavailable')
            with sync_playwright() as pw:
                instance = pw.chromium.launch(headless=True)
                instance.close()
        except ImportError:
            raise unittest.SkipTest('Playwright unavailable')

    def test_journey_interactions_and_failed_assertion(self):
        from browser_journey_runner import run
        with server() as url:
            result = run({'url': url, 'fail_on_page_errors': False, 'steps': [
                {'action': 'fill', 'selector': '#name', 'value': 'Dev'},
                {'action': 'click', 'selector': '#greet'},
                {'action': 'assert_text', 'selector': '#result', 'value': 'Hello Dev'}]})
            self.assertTrue(result['ok'], result)
            self.assertFalse(run({'url': url, 'timeout': .2, 'steps': [{'action': 'assert_count', 'selector': 'h1', 'value': 2}]})['ok'])

    def test_visual_baseline_compare_and_change(self):
        from visual_regression_checker import run
        with server() as url, tempfile.TemporaryDirectory() as tmp:
            params = {'url': url, 'output_dir': tmp, 'name': 'test', 'width': 800, 'height': 600}
            self.assertTrue(run(dict(params, mode='baseline'))['ok'])
            self.assertTrue(run(dict(params, mode='compare'))['ok'])
            from PIL import Image
            baseline = next(Path(tmp).glob('*baseline.png'))
            with Image.open(baseline) as original:
                changed = Image.new('RGB', original.size, (0, 0, 0))
                changed.save(baseline)
            self.assertFalse(run(dict(params, mode='compare'))['ok'])

    def test_accessibility_axe_violation_details(self):
        from accessibility_checker import run
        axe = ROOT / 'plugin_vendor/node_modules/axe-core/axe.min.js'
        if not axe.exists():
            self.skipTest('axe-core not installed')
        with server() as url:
            result = run({'url': url, 'axe_path': str(axe)})
            self.assertIn('engine', result['data'])
            self.assertIn('violations', result['data'])
            self.assertTrue(any(v['id'] == 'button-name' for v in result['data']['violations']))


if __name__ == '__main__':
    unittest.main()
