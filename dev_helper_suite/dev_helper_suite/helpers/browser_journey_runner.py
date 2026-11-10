"""Run explicit browser interactions and assertions from JSON steps."""
import time
from common import main, report, issue
from dev_plugins_support import browser, page_setup, http_url, json_value


def run(p):
    """Run an allowlisted sequence; clicks/submissions can change the target system."""
    steps = json_value(p.get('steps'), [])
    if not isinstance(steps, list) or not 1 <= len(steps) <= 100:
        raise ValueError('Provide 1–100 journey steps')
    allowed = {'goto', 'click', 'fill', 'select', 'check', 'uncheck', 'press', 'wait_visible', 'assert_text', 'assert_count', 'assert_url'}
    for step in steps:
        if step.get('action') not in allowed:
            raise ValueError(f'Unsupported action: {step.get("action")}')
    outcomes, problems, console = [], [], []
    with browser() as pw:
        instance = pw.chromium.launch(headless=not p.get('show_browser', False))
        try:
            context, page = page_setup(instance, p)
            page.on('pageerror', lambda exc: console.append(str(exc)))
            if p.get('url'):
                page.goto(http_url(p['url']), wait_until='load')
            for index, step in enumerate(steps):
                action = step['action']
                start = time.perf_counter()
                row = {'step': index + 1, 'action': action, 'selector': step.get('selector'), 'ok': False}
                try:
                    if action == 'goto':
                        response = page.goto(http_url(step['url']), wait_until='load')
                        if response and response.status >= 400:
                            raise ValueError(f'Navigation returned HTTP {response.status}')
                    elif action == 'assert_url':
                        if str(step['value']) not in page.url:
                            raise ValueError('Current URL did not contain expected text')
                    else:
                        target = page.locator(step['selector'])
                        if action == 'click': target.click()
                        elif action == 'fill': target.fill(str(step.get('value', '')))
                        elif action == 'select': target.select_option(str(step['value']))
                        elif action == 'check': target.check()
                        elif action == 'uncheck': target.uncheck()
                        elif action == 'press': target.press(str(step['value']))
                        elif action == 'wait_visible': target.wait_for(state='visible')
                        elif action == 'assert_text':
                            from playwright.sync_api import expect
                            expect(target).to_contain_text(str(step['value']), timeout=float(p.get('timeout', 15)) * 1000)
                        elif action == 'assert_count':
                            from playwright.sync_api import expect
                            expect(target).to_have_count(int(step['value']), timeout=float(p.get('timeout', 15)) * 1000)
                    row['ok'] = True
                except Exception as exc:
                    # Avoid echoing fill values (passwords / customer data) in exceptions.
                    row['error'] = str(exc)[:1500] if action not in ('fill', 'press') else 'Input action failed; details omitted'
                    problems.append(issue(row['error'], f'step {index + 1}'))
                row['elapsed_ms'] = round((time.perf_counter() - start) * 1000)
                outcomes.append(row)
                if not row['ok']:
                    break
        finally:
            instance.close()
    if p.get('fail_on_page_errors', True):
        problems.extend(issue(error, 'browser page error') for error in console)
    return report(f'{sum(x["ok"] for x in outcomes)}/{len(steps)} journey steps passed', problems,
                  {'steps': outcomes, 'page_errors': console, 'skipped_steps': len(steps) - len(outcomes)})


if __name__ == '__main__':
    raise SystemExit(main(run))
