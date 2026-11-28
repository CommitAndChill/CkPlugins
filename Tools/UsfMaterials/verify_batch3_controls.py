"""Exercise actual material controls and restore every override in the same studio."""
import json
import numpy as np
from PIL import Image
from capture_batch3 import LOOKS
from verify_industrial_reload import command, OUTPUT

SPECIAL = {
    'LibraryVelvet': {'FuzzWeight': 0.0},
    'LibraryWalnut': {'FinishWeight': 0.0},
    'LibraryGranite': {'Polish': 0.0},
    'LibraryBrass': {'Anisotropy': 0.0},
    'LibraryFrostedGlass': {'BlurRadius': 0.0},
    'LibraryCarbonFiber': {'CoatWeight': 0.0}}


def main():
    initial = command('state')
    report = {'passed': False, 'restored': False, 'materials': {}}
    try:
        for name in LOOKS:
            original = initial['library'][name]['values']
            inspection_strength = max(original['NormalStrength'], 2.0)
            stages = {'lit': {}, 'special': SPECIAL[name], 'normal': {'DebugView': 2, 'NormalStrength': inspection_strength},
                      'flat-normal': {'DebugView': 2, 'NormalStrength': 0},
                      'rotated': {'DebugView': 2, 'NormalStrength': inspection_strength, 'UVRotation': 45, 'UVScale': original['UVScale'] * .73},
                      'roughness': {'DebugView': 3},
                      'roughness-high': {'DebugView': 3, 'RoughnessScale': 0, 'RoughnessBias': .9}}
            images = {}
            for stage, overrides in stages.items():
                values = dict(original)
                values.update(overrides)
                arguments = sum((['--scalar', key + '=' + str(value)] for key, value in values.items()), [])
                filename = f'Batch3-Control-{name}-{stage}.png'
                command('capture', '--look', name, '--name', filename, '--shot',
                    '--lighting', 'point' if name == 'LibraryBrass' and stage in ['lit', 'special'] else 'studio', *arguments)
                pixels = np.asarray(Image.open(OUTPUT / filename).convert('RGB'), dtype=float) / 255
                height, width = pixels.shape[:2]
                images[stage] = pixels[int(height * .32):int(height * .65), int(width * .395):int(width * .5)]
            diffs = {}
            for left, right in [('lit', 'special'), ('normal', 'flat-normal'), ('normal', 'rotated'), ('roughness', 'roughness-high')]:
                difference = np.abs(images[left] - images[right])
                diffs[left + '/' + right] = {'mean_absolute_rgb': float(difference.mean()),
                                              'max_rgb': float(difference.max())}
                if not difference.max() > .003:
                    raise RuntimeError('No visible control response: ' + name + '/' + left + '/' + right)
            report['materials'][name] = {'normal_inspection_strength': inspection_strength, 'special_lighting': 'compatible point' if name == 'LibraryBrass' else 'studio', 'differences': diffs}
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
        report['restored'] = initial['library'] == final['library'] and final['diagnostic_light'] is None
        report['passed'] = report['passed'] and report['restored']
        (OUTPUT / 'Batch3-ControlProof.json').write_text(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
