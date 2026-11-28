"""Matched temporary finish trials; restores every override without changing defaults."""
import json
from verify_industrial_reload import command, OUTPUT

TRIALS = {
    'LibraryNylon': ({'UVScale': 0.8}, {}),
    'LibraryCopper': ({'RoughnessBias': 0.18}, {'TintColor': [0.95, 0.45, 0.25, 1]}),
    'LibraryFiberglass': ({'UVScale': 4, 'NormalStrength': 0.12, 'ResinRoughness': 0.16}, {}),
}


def arguments(values, colors):
    result = sum((['--scalar', key + '=' + str(value)] for key, value in values.items()), [])
    return result + sum((['--vector', key + '=' + ','.join(map(str, value))] for key, value in colors.items()), [])


def main():
    initial = command('state')
    report = {'passed': False, 'restored': False, 'initial': initial, 'captures': {}}
    try:
        command('preview_quality')
        for name, (values, colors) in TRIALS.items():
            for view, distance, height in [('Close', 210, 35), ('Macro', 135, 20)]:
                report['captures'][name + '/' + view] = command('capture', '--look', name,
                    '--name', 'Batch7-FinishTrial-' + name + '-' + view + '.png',
                    '--distance', distance, '--height', height, '--shot', '--lighting', 'studio',
                    *arguments(values, colors))
            before = initial['library'][name]
            command('select', '--look', name, *arguments(before['values'], before['colors']))
        report['passed'] = True
    finally:
        for name in TRIALS:
            before = initial['library'][name]
            command('select', '--look', name, *arguments(before['values'], before['colors']))
        command('restore_quality')
        final = command('state')
        report['final'] = final
        report['restored'] = (initial['library'] == final['library'] and initial['environment'] == final['environment']
                              and initial['render_cvars'] == final['render_cvars']
                              and not final['preview_quality'] and final['diagnostic_light'] is None)
        report['passed'] = report['passed'] and report['restored']
        (OUTPUT / 'Batch7-FinishTrials.json').write_text(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
