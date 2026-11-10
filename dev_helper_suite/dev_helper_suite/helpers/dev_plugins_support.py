"""Shared support for the optional Developer Helpers plugin pack."""
import fnmatch
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse

EXCLUDED = {'.git', '.venv', 'node_modules', 'bin', 'obj', '__pycache__', 'plugin_vendor'}


def files(root, patterns):
    root = Path(root).expanduser().resolve()
    if not root.exists():
        raise ValueError(f'Path does not exist: {root}')
    candidates = [root] if root.is_file() else root.rglob('*')
    for path in candidates:
        if path.is_file() and not any(part in EXCLUDED for part in path.relative_to(root.parent if root.is_file() else root).parts):
            if any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns):
                yield path


def json_value(value, default):
    if value is None or value == '':
        return default
    return json.loads(value) if isinstance(value, str) else value


def http_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Provide a complete HTTP(S) URL.')
    return url


def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ValueError('Install requirements-plugins.txt and run: python -m playwright install chromium')
    return sync_playwright()


def page_setup(browser_instance, p):
    context = browser_instance.new_context(viewport={'width': int(p.get('width', 1440)), 'height': int(p.get('height', 900))},
                                          device_scale_factor=1, reduced_motion='reduce', locale='en-US', timezone_id='UTC')
    context.set_default_timeout(float(p.get('timeout', 15)) * 1000)
    return context, context.new_page()


def navigate(page, p):
    page.goto(http_url(p['url']), wait_until='load')
    page.evaluate('document.fonts.ready')
    if p.get('ready_selector'):
        page.locator(p['ready_selector']).first.wait_for(state='visible')


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'Git command failed')
    return result.stdout
