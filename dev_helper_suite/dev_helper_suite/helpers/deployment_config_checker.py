"""Validate local configuration against explicit environment rules; never print values."""
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from common import main, report, issue
from dev_plugins_support import json_value

MISSING = object()


def load_config(path):
    path = Path(path)
    text = path.read_text(encoding='utf-8-sig')
    if path.suffix.lower() in ('.xml', '.config'):
        if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
            raise ValueError('DTDs/entities are not supported')
        root = ET.fromstring(text)
        return {node.attrib['key']: node.get('value', '') for node in root.findall('.//appSettings/add') if 'key' in node.attrib} | {
            'connectionStrings.' + node.attrib['name']: node.get('connectionString', '') for node in root.findall('.//connectionStrings/add') if 'name' in node.attrib}
    if path.suffix.lower() == '.json':
        return json.loads(text)
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:]
        key, separator, value = line.partition('=')
        if not separator:
            raise ValueError('Unsupported .env line; expected KEY=value')
        values[key.strip()] = value.strip().strip('\"\'')
    return values


def lookup(data, key):
    if isinstance(data, dict) and key in data:
        return data[key]
    current = data
    for part in key.split('.'):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def run(p):
    """Check JSON, simple .env or XML appSettings with user-defined rules."""
    config = load_config(p['config_path'])
    rules = json_value(p.get('rules'), None)
    if rules is None and p.get('rules_path'):
        rules = json.loads(Path(p['rules_path']).read_text(encoding='utf-8'))
    if not isinstance(rules, list) or not rules:
        raise ValueError('Provide a nonempty rules array or rules_path')
    problems, checks = [], []
    supported = {'required', 'equals', 'not_equals', 'contains', 'not_contains', 'regex'}
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict) or not isinstance(rule.get('key'), str):
            raise ValueError('Each rule must contain a string key')
        if rule.get('severity', 'error') not in ('warning', 'error'):
            raise ValueError('Rule severity must be error or warning')
        key = rule['key']
        operation = rule.get('op', 'required')
        if operation not in supported:
            raise ValueError(f'Unsupported rule operation: {operation}')
        if operation != 'required' and 'value' not in rule:
            raise ValueError('Rules other than required must include value')
        value = lookup(config, key)
        wanted = rule.get('value')
        if operation == 'required':
            passed = value is not MISSING and value is not None and value != ''
        elif value is MISSING:
            passed = False
        elif operation in ('equals', 'not_equals'):
            equal = type(value) is type(wanted) and value == wanted
            passed = equal if operation == 'equals' else not equal
        elif operation == 'contains':
            passed = str(wanted) in str(value)
        elif operation == 'not_contains':
            passed = str(wanted) not in str(value)
        else:
            passed = re.search(str(wanted), str(value)) is not None
        checks.append({'key': key, 'operation': operation, 'passed': passed})
        if not passed:
            problems.append(issue('Configuration rule failed (values omitted)', f'rule {index + 1}: {key}', rule.get('severity', 'error')))
    return report(f'{sum(x["passed"] for x in checks)}/{len(checks)} configuration rules passed', problems,
                  {'environment': p.get('environment', ''), 'checks': checks,
                   'scope': 'Checks this file only; does not resolve .NET environment overrides, secrets, transforms or runtime configuration.'})


if __name__ == '__main__':
    raise SystemExit(main(run))
