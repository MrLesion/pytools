#!/usr/bin/env sh
set -eu
cd -- "$(dirname -- "$0")"
case "${1:-}" in
    ''|--browser) ;;
    *) echo 'Usage: ./install.sh [--browser]' >&2; exit 2 ;;
esac
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ is required"'
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
if [ "${1:-}" = '--browser' ]; then
    .venv/bin/python -m pip install -r requirements-browser.txt
    .venv/bin/python -m playwright install chromium
fi
.venv/bin/python -c 'import tkinter; print("Tkinter available")'
echo 'Setup complete. Run ./start.sh to open Developer Helpers.'
