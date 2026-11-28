"""Measure unchanged-shot variance against algebraically equal POM endpoints."""
import json
import numpy as np
from PIL import Image
from verify_industrial_reload import command, OUTPUT
from trial_batch7_finishes import arguments


def main():
    initial = command('state')
    report = {'initial': initial, 'captures': {}, 'metrics': {}}
    images = {}
    before = initial['environment']['pom']
    try:
        for label, overrides in [
                ('Off-A', {'DebugView': 1, 'PomAmount': 0, 'ReliefCm': 6}),
                ('Off-B', {'DebugView': 1, 'PomAmount': 0, 'ReliefCm': 6}),
                ('Zero-A', {'DebugView': 1, 'PomAmount': 1, 'ReliefCm': 0}),
                ('Zero-B', {'DebugView': 1, 'PomAmount': 1, 'ReliefCm': 0})]:
            values = dict(before['values'])
            values.update(overrides)
            filename = 'Environment1-EndpointDiagnostic-' + label + '.png'
            report['captures'][label] = command('capture', '--environment', 'pom',
                '--name', filename, '--shot', '--distance', 260, '--height', 150,
                *arguments(values, before['colors']))
            images[label] = np.asarray(Image.open(OUTPUT / filename).convert('RGB'), dtype=float) / 255
        for name, ys, xs in [('original', (.39, .64), (.40, .60)),
                             ('interior', (.46, .61), (.43, .57))]:
            report['metrics'][name] = {}
            for left, right in [('Off-A', 'Off-B'), ('Zero-A', 'Zero-B'),
                                ('Off-A', 'Zero-A'), ('Off-B', 'Zero-B')]:
                height, width = images[left].shape[:2]
                delta = np.abs(images[left] - images[right])
                delta = delta[int(height * ys[0]):int(height * ys[1]), int(width * xs[0]):int(width * xs[1])]
                report['metrics'][name][left + '/' + right] = {
                    'mean': float(delta.mean()), 'max': float(delta.max()),
                    'fraction_gt_one_code': float(np.any(delta > 1 / 255 + 1e-6, axis=2).mean())}
    finally:
        command('select', '--environment', 'pom', *arguments(before['values'], before['colors']))
        report['final'] = command('state')
        report['restored'] = report['initial']['environment'] == report['final']['environment']
        (OUTPUT / 'Environment1-EndpointDiagnostic.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report['metrics'], indent=2))
    if not report['restored']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
