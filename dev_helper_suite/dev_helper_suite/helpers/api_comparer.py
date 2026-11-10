"""Compare JSON documents from local files or HTTP GET endpoints."""
import json
import math
from common import main, read_source, report, issue


def compare(left, right, ignore=(), key='', tolerance=0, path='$'):
    changes = []
    def add(kind, a=None, b=None, at=path):
        changes.append({'path': at, 'kind': kind, 'left': a, 'right': b})
    if isinstance(left, dict) and isinstance(right, dict):
        for name in sorted(set(left) | set(right)):
            at = f'{path}.{name}'
            if name in ignore or at in ignore:
                continue
            if name not in left:
                add('added', b=right[name], at=at)
            elif name not in right:
                add('removed', a=left[name], at=at)
            else:
                changes.extend(compare(left[name], right[name], ignore, key, tolerance, at))
    elif isinstance(left, list) and isinstance(right, list):
        if key and all(isinstance(x, dict) and key in x for x in left + right):
            def index(items):
                result = {}
                for x in items:
                    identity = json.dumps(x[key], sort_keys=True)
                    if identity in result:
                        raise ValueError(f'Duplicate array key {key}={identity} at {path}')
                    result[identity] = x
                return result
            a, b = index(left), index(right)
            for identity in sorted(set(a) | set(b)):
                at = f'{path}[{key}={identity}]'
                if identity not in a:
                    add('added', b=b[identity], at=at)
                elif identity not in b:
                    add('removed', a=a[identity], at=at)
                else:
                    changes.extend(compare(a[identity], b[identity], ignore, key, tolerance, at))
        else:
            for i in range(max(len(left), len(right))):
                at = f'{path}[{i}]'
                if i >= len(left):
                    add('added', b=right[i], at=at)
                elif i >= len(right):
                    add('removed', a=left[i], at=at)
                else:
                    changes.extend(compare(left[i], right[i], ignore, key, tolerance, at))
    elif isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(right, (int, float)) and not isinstance(right, bool):
        if not math.isclose(left, right, abs_tol=tolerance, rel_tol=0):
            add('changed', left, right)
    elif type(left) is not type(right) or left != right:
        add('changed', left, right)
    return changes


def run(p):
    """Compare JSON, optionally matching array objects by key and ignoring fields."""
    headers = p.get('headers') or {}
    left, right = [json.loads(read_source(p[k], headers=headers)) for k in ('left', 'right')]
    ignore = p.get('ignore', [])
    if isinstance(ignore, str):
        ignore = [x.strip() for x in ignore.split(',') if x.strip()]
    tolerance = float(p.get('tolerance', 0))
    if tolerance < 0:
        raise ValueError('Tolerance must be nonnegative.')
    changes = compare(left, right, ignore, p.get('array_key', ''), tolerance)
    return report(f'{len(changes)} differences found', [issue('JSON documents differ')] if changes else [], changes)


if __name__ == '__main__':
    raise SystemExit(main(run))
