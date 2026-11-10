"""Validate the trusted, local helper catalog."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_catalog(path=None):
    path = Path(path or ROOT / 'helpers.json').resolve()
    payload = json.loads(path.read_text(encoding='utf-8'))
    if payload.get('version') != 1:
        raise ValueError('Unsupported catalog version; expected 1.')
    helpers = payload.get('helpers', [])
    if not helpers:
        raise ValueError('Catalog contains no helpers.')
    seen = set()
    for item in helpers:
        for name in ('id', 'name', 'script_path', 'description', 'example_use', 'code_example', 'fields'):
            if name not in item:
                raise ValueError(f'Helper is missing {name}')
        if item['id'] in seen:
            raise ValueError(f'Duplicate helper ID: {item["id"]}')
        seen.add(item['id'])
        script = (path.parent / item['script_path']).resolve()
        if not script.is_relative_to(path.parent) or not script.is_file() or script.suffix != '.py':
            raise ValueError(f'Invalid script path: {item["script_path"]}')
        names = set()
        for field in item['fields']:
            if field['name'] in names:
                raise ValueError('Duplicate input field name')
            names.add(field['name'])
            if field.get('type', 'text') not in ('text', 'multiline', 'file', 'path', 'int', 'float', 'bool', 'select', 'json'):
                raise ValueError(f'Unsupported field type: {field["name"]}')
        item['_script'] = str(script)
    return helpers
