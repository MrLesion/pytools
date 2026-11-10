"""Combine local Git history and exported helper summaries into a Markdown report."""
import json
from datetime import datetime, timezone
from pathlib import Path
from common import main, report, issue
from dev_plugins_support import git, json_value


def run(p):
    """Read a Git commit range and helper report files; optionally write Markdown."""
    root = Path(p['repo_path']).resolve()
    base, head = p.get('base_ref', 'HEAD~1'), p.get('head_ref', 'HEAD')
    for ref in (base, head):
        if not isinstance(ref, str) or not ref or ref.startswith('-'):
            raise ValueError('Provide valid Git refs, without leading dashes')
    # Resolve each ref first; only verified commit hashes reach revision expressions.
    base_hash = git(root, 'rev-parse', '--verify', base + '^{commit}').strip()
    head_hash = git(root, 'rev-parse', '--verify', head + '^{commit}').strip()
    log = git(root, 'log', '--format=%H%x1f%an%x1f%s', base_hash + '..' + head_hash, '--')
    commits = []
    for line in log.splitlines():
        parts = line.split('\x1f', 2)
        if len(parts) == 3:
            commits.append(dict(zip(('hash', 'author', 'subject'), parts)))
    changed = git(root, 'diff', '--name-status', base_hash, head_hash, '--').splitlines()
    sources = json_value(p.get('report_files'), [])
    if not isinstance(sources, list):
        raise ValueError('report_files must be an array of file paths')
    validation, problems = [], []
    for source in sources:
        try:
            document = json.loads(Path(source).read_text(encoding='utf-8'))
            if not isinstance(document, dict) or not isinstance(document.get('ok'), bool):
                raise ValueError('Expected an exported helper report with boolean ok')
            entry = {'file': str(source), 'ok': document['ok'], 'summary': document.get('summary', ''),
                     'issue_count': len(document.get('issues', []))}
            validation.append(entry)
            if not entry['ok']:
                problems.append(issue('Included validation report contains failures', source))
        except (ValueError, OSError) as exc:
            problems.append(issue(f'Could not read helper report: {exc}', source))
    title = str(p.get('title', 'Release report')).replace('\n', ' ')
    lines = [f'# {title}', '', f'Generated: {datetime.now(timezone.utc).isoformat(timespec="seconds")}',
             f'Range: `{base_hash[:12]}..{head_hash[:12]}`', '', '## Changes', '']
    lines += [f'- {x["hash"][:8]} {x["subject"]} ({x["author"]})' for x in commits] or ['No commits in range.']
    lines += ['', '## Files', ''] + [f'- {line}' for line in changed]
    lines += ['', '## Validation', '']
    lines += [f'- {"PASS" if x["ok"] else "FAIL"}: {x["file"]} — {x["summary"]} ({x["issue_count"]} issues)' for x in validation] or ['No validation reports supplied.']
    lines += ['', 'Only the supplied reports are summarized. Their freshness and coverage are not verified.', '']
    markdown = '\n'.join(lines)
    output = p.get('output_path', '')
    if output:
        path = Path(output).expanduser().resolve()
        if path.suffix.lower() != '.md':
            raise ValueError('Output path must end in .md')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding='utf-8')
        output = str(path)
    return report(f'Report built from {len(commits)} commits and {len(validation)} checks', problems,
                  {'markdown': markdown, 'output_path': output or None, 'commits': commits, 'files': changed, 'validation': validation})


if __name__ == '__main__':
    raise SystemExit(main(run))
