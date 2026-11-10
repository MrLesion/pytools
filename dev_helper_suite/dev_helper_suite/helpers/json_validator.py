"""Validate JSON syntax from pasted content, a URL or a local file."""
import json
import math
from common import main, report, issue
from document_input import document_input


def run(params):
    """Strict JSON validation with line/column diagnostics and optional formatting."""
    payload, source = document_input(params)
    problems = []

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                problems.append(issue(f'Duplicate object key: {key}', source))
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f'{value} is not a valid JSON number')

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f'Number exceeds supported finite range: {value}')
        return number

    try:
        parsed = json.loads(payload, object_pairs_hook=pairs,
                            parse_constant=invalid_constant, parse_float=finite_float)
    except json.JSONDecodeError as exc:
        return report('Invalid JSON', [issue(exc.msg, f'{source}: line {exc.lineno}, column {exc.colno}')],
                      {'source': source, 'line': exc.lineno, 'column': exc.colno, 'offset': exc.pos})
    except (ValueError, UnicodeError, RecursionError) as exc:
        return report('Invalid or unsupported JSON', [issue(str(exc), source)])
    if problems:
        return report('JSON contains duplicate object keys', problems, {'source': source})
    root_type = 'null' if parsed is None else 'boolean' if isinstance(parsed, bool) else 'object' if isinstance(parsed, dict) else 'array' if isinstance(parsed, list) else 'string' if isinstance(parsed, str) else 'number'
    data = {'source': source, 'root_type': root_type}
    if isinstance(parsed, (dict, list)):
        data['root_entries'] = len(parsed)
    if params.get('format_output', True):
        # ASCII escaping preserves escaped lone surrogates without breaking UTF-8 stdout.
        data['formatted_json'] = json.dumps(parsed, indent=2, ensure_ascii=True, allow_nan=False)
    return report('Valid JSON', data=data)


if __name__ == '__main__':
    raise SystemExit(main(run))
