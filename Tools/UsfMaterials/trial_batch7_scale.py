"""One bounded source-density trial, with exact scalar/color/quality restoration."""
import json
from verify_industrial_reload import command, OUTPUT
from trial_batch7_finishes import arguments


def main():
    initial = command('state')
    report = {'passed': False, 'restored': False, 'initial': initial, 'captures': {}}
    subjects = [
        ('--look', 'LibraryFiberglass', 'library', {'UVScale': 6},
         [('Close', 210, 35), ('Macro', 135, 20)]),
        ('--environment', 'pom', 'environment', {'UVScale': .5, 'ReliefCm': 12},
         [('Oblique', 260, 150), ('Near', 170, 110)]),
        ('--environment', 'displacement', 'environment', {'UVScale': .5, 'ReliefCm': 12},
         [('Oblique', 260, 150), ('Near', 170, 110)])]
    try:
        command('preview_quality')
        for selector, name, collection, overrides, views in subjects:
            for view, distance, height in views:
                report['captures'][name + '/' + view] = command('capture', selector, name,
                    '--name', 'Batch7-ScaleTrial-' + name + '-' + view + '.png',
                    '--distance', distance, '--height', height, '--shot',
                    *arguments(overrides, {}))
            before = initial[collection][name]
            command('select', selector, name, *arguments(before['values'], before['colors']))
        report['passed'] = True
    finally:
        for selector, name, collection, overrides, views in subjects:
            before = initial[collection][name]
            command('select', selector, name, *arguments(before['values'], before['colors']))
        command('restore_quality')
        final = command('state')
        report['final'] = final
        report['restored'] = (initial['library'] == final['library'] and initial['environment'] == final['environment']
                              and initial['render_cvars'] == final['render_cvars']
                              and not final['preview_quality'] and final['diagnostic_light'] is None)
        report['passed'] = report['passed'] and report['restored']
        (OUTPUT / 'Batch7-ScaleTrials.json').write_text(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
