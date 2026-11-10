import contextlib
import http.server
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'helpers'))
from catalog import load_catalog
from api_comparer import compare
from feed_auditor import run as audit
from log_investigator import run as investigate
from test_data_generator import generate
from tracking_inspector import validate, run as inspect_tracking
from smoke_checker import run as smoke


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/ok')
            self.end_headers()
            return
        status = 404 if self.path == '/missing' else 200
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        body = '<html><body>Ready<script>window.dataLayer=[];dataLayer.push({event:"view_item",ecommerce:{items:[{item_id:"P1",price:12}]}});</script></body></html>'
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


class HelpersTest(unittest.TestCase):
    def test_catalog_and_all_offline_cli_examples(self):
        helpers = load_catalog()
        self.assertEqual(len(helpers), 8)
        for helper in helpers:
            if helper['id'] == 'smoke-checker':
                continue
            with self.subTest(helper=helper['id']):
                proc = subprocess.run([sys.executable, 'cli.py', helper['id'], '--input', f'examples/{helper["id"]}.json'], cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 1 if helper['id'] == 'api-comparer' else 0, proc.stderr + proc.stdout)
                self.assertIn('summary', json.loads(proc.stdout))

    def test_api_identity_ignore_and_types(self):
        self.assertEqual(compare([{'id': 1, 'date': 1}, {'id': 2}], [{'id': 2}, {'id': 1, 'date': 9}], ['date'], 'id'), [])
        self.assertTrue(compare(True, 1))
        self.assertEqual(compare(1, 1.01, tolerance=.02), [])
        self.assertTrue(compare({'x': None}, {}))
        with self.assertRaises(ValueError):
            compare([{'id': 1}, {'id': 1}], [], key='id')

    def test_feed_formats_and_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'feed.xml'
            source.write_text('<rss xmlns:g="urn:g"><channel><item><g:id>A</g:id><g:title>Shirt</g:title><g:price>12 DKK</g:price><g:image_link>https://example.com/a.jpg</g:image_link></item></channel></rss>')
            self.assertTrue(audit({'source': str(source)})['ok'])
            source.write_text('<rss><item><id>A</id><title>X</title><price>NaN</price></item><item><id>A</id><price>-1</price></item></rss>')
            result = audit({'source': str(source)})
            self.assertFalse(result['ok'])
            self.assertTrue(any('Duplicate' in x['message'] for x in result['issues']))
            source.write_text('id,title,price,currency,image_link\nA,Shirt,12,DKK,https://example.com/a.jpg\n')
            self.assertTrue(audit({'source': str(source), 'format': 'csv'})['ok'])
            source.write_text('{"data":{"products":[{"id":"A","title":"Shirt","price":12,"currency":"DKK","image_link":"https://example.com/a.jpg"}]}}')
            self.assertTrue(audit({'source': str(source), 'items_path': 'data.products'})['ok'])

    def test_tracking_invalid_numbers_and_purchase(self):
        issues, counts = validate([{'event': 'purchase', 'ecommerce': {'value': '12', 'items': [{'price': '0.00', 'quantity': 0}]}}])
        self.assertEqual(counts['purchase'], 1)
        self.assertGreaterEqual(len(issues), 5)
        self.assertFalse(any(x['severity'] == 'error' for x in validate([{'event': 'view_item', 'ecommerce': {'items': [{'item_id': 'A', 'price': 0}]}}])[0]))

    def test_log_stack_trace_and_normalized_groups(self):
        result = investigate({'path': str(ROOT / 'examples/sample.log')})
        self.assertEqual(result['data']['levels']['ERROR'], 2)
        top = result['data']['groups'][0]
        self.assertEqual(top['count'], 2)
        self.assertIn('Demo.Products.Load', top['samples'][0]['text'])

    def test_linked_test_data_reproducible_and_balanced(self):
        data = generate('orders', 20, 42)
        self.assertEqual(data, generate('orders', 20, 42))
        customer_ids = {x['id'] for x in data['customers']}
        product_ids = {x['id'] for x in data['products']}
        for order in data['orders']:
            self.assertIn(order['customerId'], customer_ids)
            self.assertTrue(all(line['productId'] in product_ids for line in order['lines']))
            self.assertAlmostEqual(order['total'], sum(x['quantity'] * x['unitPrice'] for x in order['lines']))

    def test_smoke_http_redirect_errors_and_content(self):
        with server() as url:
            result = smoke({'urls': [url + '/redirect', url + '/missing'], 'expected_text': 'Ready'})
            self.assertFalse(result['ok'])
            self.assertEqual(result['data'][0]['final_url'], url + '/ok')
            self.assertEqual(result['data'][1]['status'], 404)
            self.assertFalse(smoke({'urls': [url], 'expected_text': 'absent'})['ok'])
            self.assertTrue(smoke({'urls': [url], 'expected_text': 'Ready'})['ok'])

    def test_invalid_script_input_returns_json(self):
        proc = subprocess.run([sys.executable, str(ROOT / 'helpers/test_data_generator.py')], input='{"count":0}', capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(json.loads(proc.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
