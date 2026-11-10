"""Compare Playwright screenshots with explicit baselines using Pillow."""
import hashlib
import re
from pathlib import Path
from common import main, report, issue
from dev_plugins_support import browser, page_setup, navigate, json_value


def run(p):
    """Capture, compare and save pixel differences. Baselines change only in baseline mode."""
    mode = p.get('mode', 'compare')
    if mode not in ('baseline', 'compare'):
        raise ValueError('Mode must be baseline or compare')
    threshold = int(p.get('pixel_threshold', 16))
    allowed = float(p.get('allowed_difference_percent', .1))
    if not 0 <= threshold <= 255 or not 0 <= allowed <= 100:
        raise ValueError('Threshold must be 0–255; allowed percentage must be 0–100')
    directory = Path(p.get('output_dir', 'plugin_reports/visual')).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    identity = re.sub(r'[^a-zA-Z0-9_-]', '_', p.get('name', 'page'))
    digest = hashlib.sha256(p['url'].encode()).hexdigest()[:10]
    stem = f'{identity}-{digest}-{p.get("width",1440)}x{p.get("height",900)}'
    baseline, actual, diffpath = [directory / f'{stem}-{suffix}.png' for suffix in ('baseline', 'actual', 'diff')]
    masks = json_value(p.get('mask_selectors'), [])
    with browser() as pw:
        instance = pw.chromium.launch(headless=True)
        try:
            context, page = page_setup(instance, p)
            navigate(page, p)
            page.screenshot(path=str(baseline if mode == 'baseline' else actual), full_page=True,
                            animations='disabled', mask=[page.locator(x) for x in masks])
        finally:
            instance.close()
    if mode == 'baseline':
        return report('Baseline saved', data={'baseline': str(baseline)})
    if not baseline.exists():
        return report('Baseline missing; run baseline mode first', [issue('No baseline file', baseline)], {'actual': str(actual)})
    return compare_images(baseline, actual, diffpath, threshold, allowed)


def compare_images(baseline, actual, diffpath, threshold, allowed):
    """Compare RGB images by per-pixel maximum channel difference."""
    from PIL import Image, ImageChops
    with Image.open(baseline) as a, Image.open(actual) as b:
        a, b = a.convert('RGB'), b.convert('RGB')
        if a.size != b.size:
            return report('Screenshot dimensions changed', [issue('Baseline and actual dimensions differ')],
                          {'baseline': str(baseline), 'actual': str(actual), 'baseline_size': a.size, 'actual_size': b.size})
        diff = ImageChops.difference(a, b)
        diff.save(diffpath)
        channels = diff.split()
        max_channel = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
        histogram = max_channel.histogram()
        changed = sum(histogram[threshold + 1:])
        percent = changed / (a.width * a.height) * 100
    return report(f'{percent:.4f}% of pixels exceed threshold',
                  [issue('Visual difference exceeds allowed percentage')] if percent > allowed else [],
                  {'difference_percent': percent, 'changed_pixels': changed, 'baseline': str(baseline),
                   'actual': str(actual), 'diff': str(diffpath)})


if __name__ == '__main__':
    raise SystemExit(main(run))
