"""Group .NET/plain-text and JSON log errors with multiline stack traces."""
import json
import re
from collections import Counter
from pathlib import Path
from common import main, issue, report

LEVEL = re.compile(r'\b(FATAL|CRITICAL|ERROR|ERR|WARNING|WARN|WRN)\b', re.I)
START = re.compile(r'^\[?\d{4}-\d\d-\d\d|^\[?\d\d:\d\d:\d\d')


def normalize(text):
    text = re.sub(r'\b[0-9a-f]{8}-[0-9a-f-]{27,}\b', '<guid>', text, flags=re.I)
    text = re.sub(r'0x[0-9a-f]+|\b\d+\b', '<n>', text, flags=re.I)
    return text.strip()


def run(p):
    """Read one log file or a directory of .log/.txt/.jsonl files."""
    source = Path(p['path']).expanduser()
    if not source.exists():
        raise ValueError('Log path does not exist.')
    files = sorted(x for x in source.rglob('*') if x.suffix.lower() in ('.log', '.txt', '.jsonl')) if source.is_dir() else [source]
    if not files:
        raise ValueError('No .log, .txt or .jsonl files found.')
    groups, levels, issues = {}, Counter(), []
    records = 0
    def consume(lines, location):
        nonlocal records
        if not lines:
            return
        text = '\n'.join(lines)
        match = LEVEL.search(lines[0])
        message = lines[0]
        level = match.group(1).upper() if match else ''
        try:
            obj = json.loads(lines[0])
            if isinstance(obj, dict):
                level = str(obj.get('Level', obj.get('level', obj.get('@l', level)))).upper()
                message = str(obj.get('RenderedMessage', obj.get('Message', obj.get('message', obj.get('@mt', message)))))
                text = json.dumps(obj, ensure_ascii=False)
        except ValueError:
            pass
        aliases = {'ERR': 'ERROR', 'WRN': 'WARNING', 'WARN': 'WARNING'}
        level = aliases.get(level, level)
        if level not in ('ERROR', 'FATAL', 'CRITICAL', 'WARNING'):
            return
        records += 1
        levels[level] += 1
        # Remove leading timestamp/level prefixes before grouping.
        signature = normalize(re.sub(r'^.*?\b(?:ERROR|ERR|FATAL|CRITICAL|WARNING|WARN|WRN)\b[\]\s:|-]*', '', message, flags=re.I))
        key = level + ': ' + signature
        entry = groups.setdefault(key, {'level': level, 'signature': signature, 'count': 0, 'samples': []})
        entry['count'] += 1
        if len(entry['samples']) < 3:
            entry['samples'].append({'location': location, 'text': text[:12000]})
    for path in files:
        try:
            block, location = [], ''
            with path.open(encoding='utf-8-sig', errors='replace') as stream:
                for number, line in enumerate(stream, 1):
                    line = line.rstrip('\n')
                    if START.match(line) or line.lstrip().startswith('{') or LEVEL.search(line[:100]):
                        consume(block, location)
                        block, location = [], f'{path}:{number}'
                    if not block:
                        location = f'{path}:{number}'
                    block.append(line)
                consume(block, location)
        except OSError as exc:
            issues.append(issue(str(exc), path))
    return report(f'Found {records} warning/error records across {len(files)} files', issues,
                  {'levels': dict(levels), 'groups': sorted(groups.values(), key=lambda x: -x['count'])})


if __name__ == '__main__':
    raise SystemExit(main(run))
