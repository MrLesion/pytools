"""Audit JSON, CSV and XML feeds using configurable field names."""
import csv
import io
import json
import math
from collections import Counter
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from common import main, read_source, report, issue


def field(record, name):
    current = record
    for part in name.split('.'):
        current = current.get(part) if isinstance(current, dict) else None
    return current


def load_records(text, fmt, p):
    if fmt == 'csv':
        return list(csv.DictReader(io.StringIO(text), delimiter=p.get('delimiter', ',')))
    if fmt == 'xml':
        if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
            raise ValueError('XML document types/entities are not supported.')
        root = ET.fromstring(text)
        # Strip namespaces, supporting common RSS / Google Merchant feeds.
        for node in root.iter():
            node.tag = node.tag.split('}')[-1]
        records = []
        for node in root.iter(p.get('xml_item', 'item')):
            records.append({child.tag: ''.join(child.itertext()).strip() for child in node})
        return records
    data = json.loads(text)
    if p.get('items_path'):
        data = field(data, p['items_path'])
    if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
        raise ValueError('JSON must contain an array of objects. Set items_path for a nested array.')
    return data


def run(p):
    """Validate product IDs, names, prices, currencies and image URL syntax."""
    text = read_source(p['source'])
    fmt = p.get('format', 'auto')
    if fmt == 'auto':
        fmt = 'xml' if text.lstrip().startswith('<') else ('json' if text.lstrip().startswith(('[', '{')) else 'csv')
    records = load_records(text, fmt, p)
    names = {'id': p.get('id_field', 'id'), 'name': p.get('name_field', 'title'),
             'price': p.get('price_field', 'price'), 'image': p.get('image_field', 'image_link')}
    issues, ids = [], Counter()
    if not records:
        issues.append(issue('Feed contains no product records'))
    for number, record in enumerate(records, 1):
        if not isinstance(record, dict):
            issues.append(issue('Record is not an object', number))
            continue
        identity = field(record, names['id'])
        location = f'row {number} / {identity or "missing ID"}'
        for required in ('id', 'name'):
            value = field(record, names[required])
            if value is None or not str(value).strip():
                issues.append(issue(f'Missing {names[required]}', location))
        if identity is not None and str(identity).strip():
            ids[str(identity)] += 1
        price = field(record, names['price'])
        currency = field(record, p.get('currency_field', 'currency'))
        try:
            parts = str(price).strip().split()
            if len(parts) == 2:
                currency = parts[1]
            value = float(parts[0])
            if not math.isfinite(value) or value < 0 or isinstance(price, bool):
                raise ValueError()
            if value == 0:
                issues.append(issue('Zero price; verify this is intentional', location, 'warning'))
            if not currency or len(str(currency)) != 3 or not str(currency).isalpha():
                issues.append(issue('Missing or malformed three-letter currency', location, 'warning'))
        except (ValueError, IndexError):
            issues.append(issue(f'Missing or invalid {names["price"]}: {price}', location))
        image = field(record, names['image'])
        parsed = urlparse(str(image or ''))
        if parsed.scheme not in ('https', 'http') or not parsed.netloc:
            issues.append(issue('Missing or invalid absolute image URL', location, 'warning'))
    for identity, count in ids.items():
        if count > 1:
            issues.append(issue(f'Duplicate ID occurs {count} times', identity))
    return report(f'Audited {len(records)} products ({fmt})', issues,
                  {'records': len(records), 'unique_ids': len(ids), 'image_check': 'URL syntax only; no image downloads'})


if __name__ == '__main__':
    raise SystemExit(main(run))
