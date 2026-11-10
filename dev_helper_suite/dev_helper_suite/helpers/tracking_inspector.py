"""Capture dataLayer in Chromium or inspect a saved JSON event array."""
import json
import math
from urllib.parse import urlparse
from common import main, read_source, issue, report

ECOMMERCE = {'view_item', 'view_item_list', 'select_item', 'add_to_cart', 'remove_from_cart',
             'view_cart', 'begin_checkout', 'add_shipping_info', 'add_payment_info', 'purchase', 'refund'}


def validate(events):
    issues = []
    counts = {}
    for n, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        name = event.get('event')
        if name not in ECOMMERCE:
            continue
        counts[name] = counts.get(name, 0) + 1
        at = f'event {n + 1} ({name})'
        ecommerce = event.get('ecommerce')
        if not isinstance(ecommerce, dict):
            issues.append(issue('Missing ecommerce object', at))
            continue
        def number(value):
            return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        if 'value' in ecommerce:
            if not number(ecommerce['value']):
                issues.append(issue('value must be a finite number', at))
            currency = ecommerce.get('currency')
            if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
                issues.append(issue('A three-letter currency is required with value', at))
        items = ecommerce.get('items')
        if not isinstance(items, list) or not items:
            issues.append(issue('Missing or empty ecommerce.items', at))
            continue
        for i, item in enumerate(items):
            loc = f'{at}.items[{i}]'
            if not isinstance(item, dict):
                issues.append(issue('Item must be an object', loc))
                continue
            if not item.get('item_id') and not item.get('item_name'):
                issues.append(issue('Provide item_id or item_name', loc))
            elif not item.get('item_id'):
                issues.append(issue('Missing item_id; use stable IDs for reliable matching', loc, 'warning'))
            if 'price' in item and (not number(item['price']) or item['price'] < 0):
                issues.append(issue('price must be a nonnegative finite number', loc))
            if 'quantity' in item and (not number(item['quantity']) or item['quantity'] <= 0):
                issues.append(issue('quantity must be a positive number', loc))
        if name == 'purchase' and not ecommerce.get('transaction_id'):
            issues.append(issue('purchase is missing transaction_id', at))
    if counts.get('view_item', 0) > 1:
        issues.append(issue('Multiple view_item events captured; check whether navigation explains them', severity='warning'))
    if not counts:
        issues.append(issue('No ecommerce events captured; trigger an action or inspect another recording', severity='warning'))
    return issues, counts


def capture(p):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ValueError('Install browser support: pip install playwright && python -m playwright install chromium')
    if urlparse(p['url']).scheme not in ('http', 'https'):
        raise ValueError('Provide an HTTP(S) URL.')
    seconds = float(p.get('capture_seconds', 20))
    if not 1 <= seconds <= 300:
        raise ValueError('Capture duration must be 1–300 seconds.')
    events = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not p.get('show_browser', True))
        try:
            context = browser.new_context()
            page = context.new_page()
            page.expose_function('__devHelperRecord', lambda value: events.append(value))
            page.add_init_script('''(() => {
                const observed = new WeakSet();
                const attach = value => {
                    const arr = Array.isArray(value) ? value : [];
                    if (observed.has(arr)) return arr;
                    observed.add(arr);
                    const record = item => { try {
                        Promise.resolve(window.__devHelperRecord(JSON.parse(JSON.stringify(item)))).catch(() => {});
                    } catch (_) {} };
                    arr.forEach(record);
                    const push = arr.push;
                    arr.push = function(...items) { items.forEach(record); return push.apply(this, items); };
                    return arr;
                };
                let current = attach(window.dataLayer);
                Object.defineProperty(window, 'dataLayer', { configurable: true,
                    get: () => current, set: value => { current = attach(value); } });
            })();''')
            page.goto(p['url'], wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(seconds * 1000)
        finally:
            browser.close()
    return events


def run(p):
    """Validate a saved dataLayer array, or capture events in a fresh browser session."""
    if p.get('source'):
        events = json.loads(read_source(p['source']))
        if not isinstance(events, list):
            raise ValueError('Saved tracking input must be a JSON array.')
    else:
        events = capture(p)
    issues, counts = validate(events)
    return report(f'Inspected {len(events)} dataLayer entries', issues,
                  {'event_counts': counts, 'events': events,
                   'scope': 'dataLayer structure only; does not confirm network delivery, GA4 receipt or consent compliance'})


if __name__ == '__main__':
    raise SystemExit(main(run))
