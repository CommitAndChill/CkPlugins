"""Exercise batch-six material controls in the existing studio and restore every override."""
import json
import numpy as np
from PIL import Image
from capture_batch6 import LOOKS
from verify_industrial_reload import command, OUTPUT


SPECIAL = {
    'LibraryLinen': {'FuzzWeight': 0.0},
    'LibrarySmoothLeather': {'GrainContrast': 1.8},
    'LibraryMosaic': {'GlazeWeight': 0.0},
    'LibraryPine': {'FinishWeight': 0.0},
    'LibraryLimestone': {'PoreContrast': 2.5},
    'LibraryGalvanizedSteel': {'SpangleContrast': 0.0},
}


def main():
    if set(SPECIAL) != set(LOOKS) or any(not value for value in SPECIAL.values()):
        raise RuntimeError('Batch-five specialty controls require the approved scalar mapping')
    initial = command('state')
    report = {'passed': False, 'restored': False, 'materials': {}, 'pid': initial['pid'],
              'initial_library': initial['library'], 'captures': {}}
    try:
        for name in LOOKS:
            original = initial['library'][name]['values']
            inspection_strength = max(original['NormalStrength'], 2.0)
            stages = {'lit': {}, 'special': SPECIAL[name],
                      'normal': {'DebugView': 2, 'NormalStrength': inspection_strength},
                      'flat-normal': {'DebugView': 2, 'NormalStrength': 0},
                      'rotated': {'DebugView': 2, 'NormalStrength': inspection_strength,
                                  'UVRotation': 45, 'UVScale': original['UVScale'] * .73},
                      'roughness': {'DebugView': 3},
                      'roughness-high': {'DebugView': 3, 'RoughnessScale': 0, 'RoughnessBias': .9}}
            images = {}
            for stage, overrides in stages.items():
                values = dict(original)
                values.update(overrides)
                arguments = sum((['--scalar', key + '=' + str(value)] for key, value in values.items()), [])
                filename = f'Batch6-Control-{name}-{stage}.png'
                state = command('capture', '--look', name, '--name', filename, '--shot', '--lighting', 'studio', *arguments)['state']
                if state['pid'] != initial['pid'] or set(state['library']) != set(initial['library']):
                    raise RuntimeError('Control capture changed the editor/library roster: ' + name)
                for look, original_look in initial['library'].items():
                    if any(state['library'][look][key] != original_look[key] for key in ['mid', 'parent', 'textures']):
                        raise RuntimeError('Control capture changed a MID/master/texture binding: ' + look)
                report['captures'][name + '/' + stage] = {'image': filename, 'state': state}
                pixels = np.asarray(Image.open(OUTPUT / filename).convert('RGB'), dtype=float) / 255
                height, width = pixels.shape[:2]
                images[stage] = pixels[int(height * .32):int(height * .65), int(width * .395):int(width * .5)]
            diffs = {}
            for left, right in [('lit', 'special'), ('normal', 'flat-normal'),
                                ('normal', 'rotated'), ('roughness', 'roughness-high')]:
                difference = np.abs(images[left] - images[right])
                diffs[left + '/' + right] = {'mean_absolute_rgb': float(difference.mean()),
                                              'max_rgb': float(difference.max())}
                if not difference.max() > .003:
                    raise RuntimeError('No visible control response: ' + name + '/' + left + '/' + right)
            report['materials'][name] = {'normal_inspection_strength': inspection_strength,
                                        'special_lighting': 'studio', 'differences': diffs}
            restore = sum((['--scalar', key + '=' + str(value)] for key, value in original.items()), [])
            command('select', '--look', name, '--lighting', 'studio', *restore)
            print('Controls exercised ' + name, flush=True)
        report['passed'] = True
    finally:
        for name in LOOKS:
            original = initial['library'][name]['values']
            restore = sum((['--scalar', key + '=' + str(value)] for key, value in original.items()), [])
            command('select', '--look', name, '--lighting', 'studio', *restore)
        final = command('state')
        report['final_library'] = final['library']
        report['restored'] = (initial['pid'] == final['pid'] and initial['library'] == final['library']
                              and final['diagnostic_light'] is None and not final['preview_quality'])
        report['passed'] = report['passed'] and report['restored']
        (OUTPUT / 'Batch6-ControlProof.json').write_text(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
