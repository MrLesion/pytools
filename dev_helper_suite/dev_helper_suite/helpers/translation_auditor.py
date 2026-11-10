"""Audit exported JSON/CSV/XML translations and optional Razor usage."""
import csv
import json
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
from common import main, report, issue
from dev_plugins_support import files
from razor_template_finder import PATTERNS


def flatten(obj, prefix=''):
    if not isinstance(obj, dict):
        raise ValueError('Each JSON language value must be a translation object')
    result = {}
    for key, value in obj.items():
        full = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            nested = flatten(value, full)
        else:
            nested = {full: value}
        if set(result) & set(nested):
            raise ValueError('Colliding flattened translation keys')
        result.update(nested)
    return result


def load(path, problems):
    translations = defaultdict(dict)
    def add(language, key, value):
        if not language or not key:
            problems.append(issue('Translation row missing language or key', path))
            return
        if key in translations[language]:
            problems.append(issue(f'Duplicate key: {key}', language))
        translations[language][key] = value
    path = Path(path)
    if path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if not {'language', 'key', 'value'}.issubset(reader.fieldnames or []):
                raise ValueError('CSV headers must include language,key,value')
            for row in reader:
                add(row['language'], row['key'], row['value'])
    elif path.suffix.lower() == '.xml':
        raw = path.read_bytes()
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper() or b'\x00' in raw:
            raise ValueError('XML translations must be UTF-8 without DTDs/entities')
        root = ET.fromstring(raw)
        # Explicit portable export format; not a version-specific Dynamicweb schema.
        for node in root.findall('.//translation'):
            add(node.get('language'), node.get('key'), node.text or '')
    else:
        def pairs(items):
            data = {}
            for key, value in items:
                if key in data:
                    problems.append(issue(f'Duplicate JSON key: {key}', path))
                data[key] = value
            return data
        obj = json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs)
        if not isinstance(obj, dict):
            raise ValueError('JSON must be {language: {key: value}}')
        for language, values in obj.items():
            for key, value in flatten(values).items():
                add(language, key, value)
    return translations


def run(p):
    """Compare exported translations across languages; optionally inspect template usage."""
    problems = []
    values = load(p['source'], problems)
    if not values:
        raise ValueError('No translations found')
    baseline = p.get('baseline_language', 'en')
    if baseline not in values:
        raise ValueError(f'Baseline language missing: {baseline}')
    all_keys = set().union(*(set(x) for x in values.values()))
    for language, entries in values.items():
        for key in sorted(all_keys):
            if key not in entries:
                problems.append(issue('Missing translation key', f'{language}:{key}'))
            elif not isinstance(entries[key], str) or not entries[key].strip():
                problems.append(issue('Translation must be a nonempty string', f'{language}:{key}'))
    used = set()
    if p.get('templates_root'):
        for path in files(p['templates_root'], ['*.cshtml', '*.razor', '*.html']):
            try:
                used.update(match.group(1) for match in PATTERNS['translations'].finditer(path.read_text(encoding='utf-8-sig')))
            except (OSError, UnicodeError) as exc:
                problems.append(issue(str(exc), path, 'warning'))
        for key in sorted(used - all_keys):
            problems.append(issue('Template references an unknown translation key', key))
        for key in sorted(all_keys - used):
            problems.append(issue('No literal template reference found; may be used dynamically', key, 'warning'))
    return report(f'Audited {len(all_keys)} keys across {len(values)} languages', problems,
                  {'languages': {lang: len(entries) for lang, entries in values.items()}, 'baseline_language': baseline,
                   'template_keys': sorted(used), 'scope': 'Portable exports; adapt Dynamicweb exports to the documented input format.'})


if __name__ == '__main__':
    raise SystemExit(main(run))
