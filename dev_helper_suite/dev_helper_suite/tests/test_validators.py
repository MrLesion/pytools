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
sys.path.insert(0, str(ROOT / 'helpers'))
from json_validator import run as validate_json
from xml_validator import run as validate_xml


class Documents(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = {'/ok.json': b'{"enabled":true,"items":[1,2]}',
                '/bad.json': b'{"id":}',
                '/ok.xml': '<?xml version="1.0" encoding="iso-8859-1"?><root>caf\xe9</root>'.encode('iso-8859-1'),
                '/bad.xml': b'<root><child></root>'}.get(self.path)
        self.send_response(200 if body else 404)
        self.end_headers()
        self.wfile.write(body or b'Not found')


class ValidatorsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Documents)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def test_pasted_json_and_precise_error(self):
        for text, root in [('null', 'null'), ('false', 'boolean'), ('42', 'number'), ('"a"', 'string'), ('[]', 'array'), ('{}', 'object')]:
            self.assertEqual(validate_json({'content': text})['data']['root_type'], root)
        bad = validate_json({'content': '{\n "id":\n}'})
        self.assertFalse(bad['ok'])
        self.assertEqual(bad['data']['line'], 3)
        self.assertGreater(bad['data']['column'], 0)

    def test_json_duplicates_constants_and_formatting(self):
        for text in ['{"a":1,"a":2}', '{"a":{"x":1,"x":2}}', 'NaN', 'Infinity', '1e999']:
            self.assertFalse(validate_json({'content': text})['ok'], text)
        result = validate_json({'content': '{"a":1}'})
        self.assertEqual(json.loads(result['data']['formatted_json']), {'a': 1})
        self.assertNotIn('formatted_json', validate_json({'content': '{}', 'format_output': False})['data'])
        self.assertTrue(validate_json({'content': '"\\ud800"'})['ok'])

    def test_pasted_xml_namespaces_and_error(self):
        good = validate_xml({'content': '<root xmlns:p="urn:demo"><p:item id="A">A &amp; B</p:item></root>'})
        self.assertTrue(good['ok'])
        self.assertEqual(good['data']['elements'], 2)
        self.assertEqual(good['data']['attributes'], 1)
        self.assertEqual(good['data']['max_depth'], 2)
        bad = validate_xml({'content': '<root>\n <item>\n</root>'})
        self.assertFalse(bad['ok'])
        self.assertEqual(bad['data']['line'], 3)
        self.assertFalse(validate_xml({'content': '<p:root/>'})['ok'])

    def test_xml_dtd_and_nesting(self):
        self.assertFalse(validate_xml({'content': '<!DOCTYPE root [<!ENTITY e "hello">]><root>&e;</root>'})['ok'])
        self.assertFalse(validate_xml({'content': '<x>' * 257 + '</x>' * 257})['ok'])
        self.assertTrue(validate_xml({'content': '<root><!-- <!DOCTYPE is only comment text -->ok</root>'})['ok'])

    def test_both_validators_by_http(self):
        for helper, suffix in [(validate_json, 'json'), (validate_xml, 'xml')]:
            with self.subTest(format=suffix):
                self.assertTrue(helper({'mode': 'url', 'url': self.url + '/ok.' + suffix, 'content': 'ignored'})['ok'])
                self.assertFalse(helper({'mode': 'url', 'url': self.url + '/bad.' + suffix})['ok'])
                with self.assertRaises(Exception):
                    helper({'mode': 'url', 'url': self.url + '/missing'})

    def test_files_encoding_and_input_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sample.json'
            path.write_bytes(b'\xef\xbb\xbf{"name":"test"}')
            self.assertTrue(validate_json({'mode': 'file', 'path': str(path)})['ok'])
            path.write_bytes(b'\xff\xfe' + '{"id":1}'.encode('utf-16-le'))
            self.assertTrue(validate_json({'mode': 'file', 'path': str(path)})['ok'])
            self.assertTrue(validate_xml({'content': '<?xml version="1.0" encoding="iso-8859-1"?><root>caf\xe9</root>'})['ok'])
        for helper in (validate_json, validate_xml):
            with self.assertRaises(ValueError):
                helper({'mode': 'url', 'url': 'file:///etc/passwd'})
            with self.assertRaises(ValueError):
                helper({'mode': 'input', 'content': ''})

    def test_invalid_documents_return_findings_exit_code(self):
        for helper in ('json_validator', 'xml_validator'):
            proc = subprocess.run([sys.executable, str(ROOT / 'helpers' / (helper + '.py'))], input=json.dumps({'content': 'invalid'}), text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(json.loads(proc.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
