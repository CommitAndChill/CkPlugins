"""Isolate aluminum normal, anisotropy and roughness contributions in the same fixed studio view."""
import json
from verify_industrial_reload import command, OUTPUT


def main():
    initial = command('state')
    baseline = initial['library']['LibraryAluminum']['values']
    keys = ['NormalStrength', 'Anisotropy', 'RoughnessScale', 'RoughnessBias']
    cases = {'Baseline': {}, 'FlatNormal': {'NormalStrength': 0}, 'Isotropic': {'Anisotropy': 0},
             'Rougher': {'RoughnessScale': 0, 'RoughnessBias': 0.55},
             'Neutral': {'NormalStrength': 0, 'Anisotropy': 0, 'RoughnessScale': 0, 'RoughnessBias': 0.55}}
    report = {'pid': initial['pid'], 'cases': {}}
    try:
        for name, changes in cases.items():
            values = {key: changes.get(key, baseline[key]) for key in keys}
            overrides = sum((['--scalar', key + '=' + str(value)] for key, value in values.items()), [])
            report['cases'][name] = command('capture', '--look', 'LibraryAluminum', '--lighting', 'studio',
                '--name', 'Aluminum-Diagnosis-' + name + '.png', '--shot', '--debug', 0, *overrides)
            print('Captured ' + name, flush=True)
    finally:
        overrides = sum((['--scalar', key + '=' + str(baseline[key])] for key in keys), [])
        restored = command('select', '--look', 'LibraryAluminum', '--lighting', 'studio', *overrides)
        report['restored'] = restored['library'] == initial['library']
        (OUTPUT / 'Aluminum-Diagnosis.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
