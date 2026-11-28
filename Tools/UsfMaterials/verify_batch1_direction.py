"""Verify directional controls under a temporary compatible point light, then restore studio state."""
import json
import numpy as np
from PIL import Image
from verify_industrial_reload import command, OUTPUT


def main():
    initial = command('state')
    report = {'pid': initial['pid'], 'lighting_limit': 'Substrate Rect integration ignores anisotropy; diagnostic uses a local point at 60 cd', 'materials': {}}
    try:
        for name, rotation in [('LibrarySilk', 'FiberRotation'), ('LibraryAluminum', 'BrushRotation')]:
            before = initial['library'][name]['values']
            stages = {}
            for stage, anisotropy, angle in [('isotropic', 0, 0), ('axis0', 1.5, 0), ('axis90', 1.5, 90)]:
                filename = f'Batch1-Direction-{name}-{stage}.png'
                result = command('capture', '--look', name, '--name', filename, '--lighting', 'point', '--shot',
                    '--scalar', 'Anisotropy=' + str(anisotropy), '--scalar', rotation + '=' + str(angle),
                    '--scalar', 'NormalStrength=0', '--scalar', 'RoughnessScale=0', '--scalar', 'RoughnessBias=0.3')
                stages[stage] = {'image': filename, 'state': result['state']}
            arrays = [np.asarray(Image.open(OUTPUT / stages[stage]['image']).convert('RGB'), dtype=float) / 255
                      for stage in ['isotropic', 'axis0', 'axis90']]
            height, width = arrays[0].shape[:2]
            yy, xx = np.mgrid[:height, :width]
            region = ((xx / width - 0.48) ** 2 + (yy / height - 0.45) ** 2 < 0.17 ** 2)
            differences = {'isotropic_vs_axis0': float(np.abs(arrays[0][region] - arrays[1][region]).mean()),
                           'axis0_vs_axis90': float(np.abs(arrays[1][region] - arrays[2][region]).mean())}
            report['materials'][name] = {'captures': stages, 'mean_absolute_display_rgb': differences}
            if min(differences.values()) < 0.003:
                raise RuntimeError('Directional rendered response is too small: ' + name + '/' + str(differences))
            command('select', '--look', name, '--lighting', 'studio',
                    *sum((['--scalar', key + '=' + str(before[key])] for key in
                          ['Anisotropy', rotation, 'NormalStrength', 'RoughnessScale', 'RoughnessBias']), []))
        report['passed'] = True
    finally:
        for name, rotation in [('LibrarySilk', 'FiberRotation'), ('LibraryAluminum', 'BrushRotation')]:
            before = initial['library'][name]['values']
            command('select', '--look', name, '--lighting', 'studio',
                    *sum((['--scalar', key + '=' + str(before[key])] for key in
                          ['Anisotropy', rotation, 'NormalStrength', 'RoughnessScale', 'RoughnessBias']), []))
        final = command('state')
        report['restored'] = final['library'] == initial['library'] and final['diagnostic_light'] is None
        report['passed'] = report.get('passed', False) and report['restored']
        (OUTPUT / 'Batch1-DirectionalProof.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'passed': report['passed'], 'restored': report['restored'],
                      'differences': {name: item['mean_absolute_display_rgb'] for name, item in report['materials'].items()}}))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
