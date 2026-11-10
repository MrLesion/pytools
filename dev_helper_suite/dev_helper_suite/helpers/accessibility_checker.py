"""Run locally installed axe-core in Chromium through Playwright."""
from pathlib import Path
from common import main, report, issue
from dev_plugins_support import browser, page_setup, navigate, json_value


def run(p):
    """Report axe violations and manual-review items; automated checks are partial."""
    axe = Path(p.get('axe_path', 'plugin_vendor/node_modules/axe-core/axe.min.js')).resolve()
    if not axe.is_file():
        raise ValueError('axe.min.js missing. Run: npm install --prefix plugin_vendor --ignore-scripts --no-audit --no-fund axe-core@4')
    tags = json_value(p.get('tags'), ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    if not isinstance(tags, list) or not tags:
        raise ValueError('Provide a nonempty array of axe tags')
    with browser() as pw:
        instance = pw.chromium.launch(headless=True)
        try:
            context, page = page_setup(instance, p)
            navigate(page, p)
            page.add_script_tag(path=str(axe))
            result = page.evaluate('''async (tags) => {
                const r = await axe.run(document, {runOnly: {type: 'tag', values: tags}});
                return {violations:r.violations, incomplete:r.incomplete, passes:r.passes.length,
                        inapplicable:r.inapplicable.length, engine:r.testEngine};
            }''', tags)
        finally:
            instance.close()
    problems = [issue(f'{v["id"]}: {v["help"]}', ', '.join(str(n['target']) for n in v['nodes'])) for v in result['violations']]
    if result['incomplete']:
        problems.append(issue(f'{len(result["incomplete"])} checks require manual review', severity='warning'))
    result['scope'] = 'Automated checks of the loaded page state only; not a WCAG conformance certification.'
    return report(f'{len(result["violations"])} accessibility violations', problems, result)


if __name__ == '__main__':
    raise SystemExit(main(run))
