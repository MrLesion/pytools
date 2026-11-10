"""Find template references, translations, includes and URLs without executing Razor."""
import re
from common import main, report, issue
from dev_plugins_support import files

PATTERNS = {
    'translations': re.compile(r'\b(?:Translate|TranslateString)\s*\(\s*"([^"\n]+)"'),
    'includes': re.compile(r'(?:@include\s*\(\s*|(?:RenderPartial|PartialAsync|Partial)\s*\(\s*|#include\s+file\s*=\s*)["\']([^"\'\n]+)', re.I),
    'urls': re.compile(r'https?://[^\s"\'<>\)]+'),
    'fields': re.compile(r'(?:GetString|GetValue|GetBoolean|GetInteger)\s*\(\s*"([^"\n]+)"')
}


def run(p):
    """Search templates and extract literal references (static heuristic, not a C# parser)."""
    mode = p.get('mode', 'search')
    if mode not in ('search', *PATTERNS):
        raise ValueError('Unknown search mode')
    query = str(p.get('query', ''))
    if mode == 'search' and not query:
        raise ValueError('Provide search text')
    extensions = [x.strip() for x in p.get('patterns', '*.cshtml,*.razor,*.html').split(',') if x.strip()]
    found, problems, scanned = [], [], 0
    for path in files(p['root'], extensions):
        scanned += 1
        try:
            for number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
                if mode == 'search':
                    matches = [query] if query.casefold() in line.casefold() else []
                else:
                    matches = [match.group(1) if match.lastindex else match.group(0) for match in PATTERNS[mode].finditer(line)]
                    if query:
                        matches = [x for x in matches if query.casefold() in x.casefold()]
                for match in matches:
                    found.append({'file': str(path), 'line': number, 'value': match, 'context': line.strip()[:1000]})
        except (OSError, UnicodeError) as exc:
            problems.append(issue(str(exc), path, 'warning'))
    return report(f'{len(found)} matches in {scanned} files', problems, {'matches': found, 'scope': 'Literal static references only; comments may match and computed references may be missed.'})


if __name__ == '__main__':
    raise SystemExit(main(run))
