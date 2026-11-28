"""Controlled native-versus-suppressed quantization experiment; execute only when the bridge is idle."""
import hashlib
import itertools
import json
import numpy as np
from PIL import Image
from verify_industrial_reload import command, OUTPUT

CVAR = 'r.BackbufferQuantizationDitheringOverride'
REGIONS = {'proof': [.39, .64, .40, .60], 'interior': [.46, .58, .44, .56]}


def arguments(record):
    args = sum((['--scalar', key + '=' + str(value)] for key, value in record['values'].items()), [])
    for key, values in record['colors'].items():
        args += ['--vector', key + '=' + ','.join(map(str, values))]
    return args


def compare(left, right):
    difference = np.abs(left - right)
    return {'mean_absolute_rgb': float(difference.mean()), 'max_rgb': float(difference.max()),
            'fraction_over_one_code': float(np.any(difference > 1 / 255 + 1e-6, axis=2).mean())}


def main():
    initial = command('state')
    if (initial['diagnostic_quantization'] or initial['preview_quality'] or initial['diagnostic_light'] is not None
            or initial['render_cvars']['r.AntiAliasingMethod'] != 0):
        raise RuntimeError('The diagnostic requires idle quantization/quality/light state and native AA0')
    if set(initial['environment']) != {'pom', 'displacement'} or len(initial['library']) != 42:
        raise RuntimeError('Both environment stations and all 42 library materials are required')
    if any(item['same_mid'] is not None or item['same_master'] is not None
           for item in list(initial['environment'].values()) + list(initial['library'].values()) + initial['industrial']):
        raise RuntimeError('Finish the active object/source proof before starting the dither diagnostic')
    test = {'values': dict(initial['environment']['pom']['values']), 'colors': initial['environment']['pom']['colors']}
    test['values'].update({'DebugView': 1, 'PomAmount': 1, 'ReliefCm': 0, 'DisplacementAmount': 0})
    report = {'completed': False, 'restored': False, 'initial_state': initial, 'captures': {},
              'regions': REGIONS, 'pairwise_metrics': {}, 'cvar': CVAR, 'suppressed_value': 32,
              'source_attribution': {'parameter_selection': 'PostProcessTonemap.cpp:843-864',
                                     'frame_seed': 'PostProcessTonemap.cpp:705-712',
                                     'additive_dither': 'PostProcessTonemap.usf:569-601',
                                     'formula': 'amplitude=1/(2^override-1); override32 nearly suppresses frame-dependent quantization dither'},
              'scope': 'Eight identical native-AA0 Zero-BC captures; only quantization override changes between four-capture phases.'}
    arrays = {}
    try:
        command('environment_proof_begin')
        # Set the endpoint once, then repeat exactly the same uniforms without intervening restoration.
        command('select', '--environment', 'pom', '--distance', 260, '--height', 150, *arguments(test))
        for phase in ['Native', 'Suppressed']:
            if phase == 'Suppressed':
                command('environment_dither_begin')
            expected_cvars = dict(initial['render_cvars'])
            expected_cvars[CVAR] = 32 if phase == 'Suppressed' else initial['render_cvars'][CVAR]
            for index in range(4):
                label = phase + '-' + str(index + 1)
                filename = 'Environment1-Dither-' + label + '.png'
                state = command('capture', '--environment', 'pom', '--name', filename, '--shot',
                                '--distance', 260, '--height', 150, *arguments(test))['state']
                if (state['pid'] != initial['pid'] or state['library'] != initial['library']
                        or state['industrial'] != initial['industrial'] or state['render_cvars'] != expected_cvars
                        or state['diagnostic_quantization'] != (phase == 'Suppressed')
                        or state['preview_quality'] != initial['preview_quality'] or state['diagnostic_light'] is not None):
                    raise RuntimeError('Capture changed unrelated state/cvars: ' + label)
                for station, before in initial['environment'].items():
                    current = state['environment'][station]
                    keys = ['actor', 'mid', 'parent', 'mesh', 'textures', 'scale', 'colors', 'rect_intensities']
                    expected_values = test['values'] if station == 'pom' else before['values']
                    if (any(current[key] != before[key] for key in keys) or current['values'] != expected_values
                            or current['same_mid'] is not True or current['same_master'] is not True):
                        raise RuntimeError('Ground state/bindings changed: ' + label + '/' + station)
                report['captures'][label] = {'image': filename, 'state': state,
                                             'quantization_value': state['render_cvars'][CVAR],
                                             'sha256': hashlib.sha256((OUTPUT / filename).read_bytes()).hexdigest()}
                arrays[label] = np.asarray(Image.open(OUTPUT / filename).convert('RGB'), dtype=float) / 255
        for region, (top, bottom, left, right) in REGIONS.items():
            crops = {}
            for label, image in arrays.items():
                height, width = image.shape[:2]
                crops[label] = image[int(height * top):int(height * bottom), int(width * left):int(width * right)]
            pairs = {a + '/' + b: compare(crops[a], crops[b]) for a, b in itertools.combinations(crops, 2)}
            report['pairwise_metrics'][region] = pairs
            summary = {}
            for phase in ['Native', 'Suppressed']:
                within = [value for key, value in pairs.items() if all(item.startswith(phase + '-') for item in key.split('/'))]
                summary[phase] = {'pair_count': len(within),
                                  'average_pairwise_mean': float(np.mean([item['mean_absolute_rgb'] for item in within])),
                                  'largest_pairwise_max': max(item['max_rgb'] for item in within)}
            native, suppressed = [summary[key]['average_pairwise_mean'] for key in ['Native', 'Suppressed']]
            summary['suppressed_to_native_mean_ratio'] = suppressed / native if native > 0 else None
            summary['interpretation'] = ('Native repeats were identical; this run cannot quantify suppression benefit.' if native == 0 else
                                         'Compare the recorded reduction against baseline variation; no proof tolerance has been changed.')
            report.setdefault('summary', {})[region] = summary
        report['completed'] = True
    except Exception as error:
        report['error'] = str(error)
    finally:
        errors = []
        for operation in [lambda: command('environment_dither_end'),
                          lambda: command('select', '--environment', 'pom', *arguments(initial['environment']['pom'])),
                          lambda: command('select', '--environment', 'displacement', *arguments(initial['environment']['displacement'])),
                          lambda: command('proof_end')]:
            try:
                operation()
            except Exception as error:
                errors.append(str(error))
        try:
            final = command('state')
            report['final_state'] = final
            report['restored'] = (not errors and final['pid'] == initial['pid']
                                  and all(final[key] == initial[key] for key in ['environment', 'library', 'industrial',
                                           'render_cvars', 'preview_quality', 'diagnostic_quantization', 'diagnostic_light']))
        except Exception as error:
            errors.append(str(error))
        report['cleanup_errors'] = errors
        (OUTPUT / 'Environment1-DitherDiagnostic.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not report['completed'] or not report['restored']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
