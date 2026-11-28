"""Serial offscreen POM/WPO controls and same-object live shader proof. Run only on instruction."""
import hashlib
import json
import numpy as np
from PIL import Image
from verify_industrial_reload import command, wait_reload, OUTPUT, SHADERS, LOG

SOURCE = SHADERS / 'Looks/EnvironmentGravel.ush'
VIEWS = {'Oblique': (260, 0, 150), 'Low': (260, 0, 40), 'Near': (170, 0, 110),
         'Far': (500, 0, 250), 'Opposite': (-260, 0, 150)}
IDENTITY = ['actor', 'mid', 'parent', 'mesh', 'textures', 'scale', 'colors', 'rect_intensities']


def arguments(record):
    result = sum((['--scalar', key + '=' + str(value)] for key, value in record['values'].items()), [])
    for key, value in record['colors'].items():
        result += ['--vector', key + '=' + ','.join(map(str, value))]
    return result


def pixels(filename):
    data = np.asarray(Image.open(OUTPUT / filename).convert('RGB'), dtype=float) / 255
    h, w = data.shape[:2]
    return data[int(h * .39):int(h * .64), int(w * .40):int(w * .60)]


def difference(left, right):
    delta = np.abs(left - right)
    return {'mean_absolute_rgb': float(delta.mean()), 'max_rgb': float(delta.max()),
            'fraction_over_one_code': float(np.any(delta > 1.0 / 255 + 1e-6, axis=2).mean())}


def main():
    original = SOURCE.read_bytes()
    owned = original
    initial = command('state')
    report = {'passed': False, 'restored': False, 'pid': initial['pid'], 'captures': {}, 'metrics': {},
              'initial_state': initial, 'reloads': [], 'source_sha256': {str(SOURCE): hashlib.sha256(original).hexdigest()},
              'scope': 'Two ground MIDs: UV-only POM versus actual WPO raster geometry; serial automatic source reload.',
              'limits': ['POM does not alter raster depth, silhouette or native shadows.',
                         'WPO is vertex displacement, with unchanged CPU collision; open patch perimeter is intentional.',
                         'Sampled views do not establish motion, temporal stability, shadow correctness or performance.']}
    if set(initial['environment']) != {'pom', 'displacement'} or len(initial['library']) != 42:
        raise RuntimeError('Expected two ground stations and the unchanged 42-material library')
    if initial['preview_quality'] or initial['diagnostic_light'] is not None:
        raise RuntimeError('Restore baseline quality/diagnostic lighting before environment proof')
    if (initial['render_cvars']['r.AntiAliasingMethod'] != 0
            or any(item['scale'] != [1, 1, 1] for item in initial['environment'].values())):
        raise RuntimeError('Environment proof requires baseline AA0 and unit-scale ground actors')

    def restore_station(key):
        command('select', '--environment', key, *arguments(initial['environment'][key]))

    def capture(label, station, overrides=None, view='Oblique'):
        values = dict(initial['environment'][station]['values'])
        values.update(overrides or {})
        distance, side, height = VIEWS[view]
        filename = 'Environment1-' + label + '.png'
        args = sum((['--scalar', key + '=' + str(value)] for key, value in values.items()), [])
        state = command('capture', '--environment', station, '--name', filename, '--shot',
                        '--distance', distance, '--side', side, '--height', height, *args)['state']
        if state['pid'] != initial['pid'] or state['library'] != initial['library']:
            raise RuntimeError('Capture changed editor/library state: ' + label)
        for key, before in initial['environment'].items():
            current = state['environment'][key]
            if (any(current[field] != before[field] for field in IDENTITY)
                    or current['same_mid'] is not True or current['same_master'] is not True):
                raise RuntimeError('Ground MID/master/binding changed: ' + label + '/' + key)
        report['captures'][label] = {'image': filename, 'station': station, 'view': view,
                                     'overrides': values, 'state': state,
                                     'sha256': hashlib.sha256((OUTPUT / filename).read_bytes()).hexdigest()}
        result = pixels(filename)
        restore_station(station)
        print('Environment capture ' + label, flush=True)
        return result

    def require(name, condition, metrics):
        report['metrics'][name] = metrics
        if not condition:
            raise RuntimeError('Environment control failed: ' + name)

    def mutate(data):
        nonlocal owned
        if SOURCE.read_bytes() != owned:
            raise RuntimeError('Concurrent shader edit preserved; stop this proof')
        offset = LOG.stat().st_size
        owned = data
        SOURCE.write_bytes(owned)
        report['reloads'].append(wait_reload(offset))

    try:
        command('environment_proof_begin')
        for preview in [False, True]:
            prefix = 'TAA' if preview else 'Native'
            if preview:
                command('preview_quality')
            try:
                for station in ['pom', 'displacement']:
                    for view in VIEWS:
                        capture(prefix + '-' + station + '-' + view, station, {'DebugView': 0}, view)
            finally:
                if preview:
                    command('restore_quality')
        pom_off = capture('POM-Off-BC', 'pom', {'DebugView': 1, 'PomAmount': 0, 'ReliefCm': 6})
        zero = capture('POM-ZeroRelief-BC', 'pom', {'DebugView': 1, 'PomAmount': 1, 'ReliefCm': 0})
        pom_on = capture('POM-On-BC', 'pom', {'DebugView': 1, 'PomAmount': 1, 'ReliefCm': 6})
        d = difference(pom_off, zero)
        require('pom_off_equals_zero_relief', d['max_rgb'] <= 1.0 / 255 + 1e-6, d)
        d = difference(pom_on, pom_off)
        require('pom_changes_apparent_uv', d['mean_absolute_rgb'] > .001 and d['max_rgb'] > .02, d)
        depth_off = capture('POM-Off-Depth', 'pom', {'DebugView': 6, 'PomAmount': 0, 'ReliefCm': 6})
        depth_on = capture('POM-On-Depth', 'pom', {'DebugView': 6, 'PomAmount': 1, 'ReliefCm': 6})
        d = difference(depth_off, depth_on)
        require('pom_preserves_raster_depth', d['max_rgb'] <= 1.0 / 255 + 1e-6, d)
        flat = capture('WPO-ZeroRelief-Depth', 'displacement', {'DebugView': 6, 'DisplacementAmount': 1, 'ReliefCm': 0})
        displaced = capture('WPO-SixCm-Depth', 'displacement', {'DebugView': 6, 'DisplacementAmount': 1, 'ReliefCm': 6})
        d = difference(flat, displaced)
        require('wpo_changes_actual_raster_depth', d['fraction_over_one_code'] > .005, d)
        capture('WPO-GeometricNormals', 'displacement', {'DebugView': 2, 'NormalStrength': 0, 'DisplacementAmount': 1, 'ReliefCm': 6})
        for station in ['pom', 'displacement']:
            capture('Bounds-' + station + '-MaxReliefFar', station, {'DebugView': 0, 'ReliefCm': 12}, 'Far')
        # Asymmetric UV coordinates make the imported grid's basis and ray direction observable.
        uv_flat = capture('UV-Basis', 'pom', {'DebugView': 7, 'PomAmount': 0, 'ReliefCm': 6})
        uv_forward = capture('UV-Forward-Flat', 'pom', {'DebugView': 8, 'PomAmount': 0, 'ReliefCm': 6})
        uv_forward_pom = capture('UV-Forward-POM', 'pom', {'DebugView': 8, 'PomAmount': 1, 'ReliefCm': 6})
        uv_reverse = capture('UV-Reverse-Flat', 'pom', {'DebugView': 8, 'PomAmount': 0, 'ReliefCm': 6}, 'Opposite')
        uv_reverse_pom = capture('UV-Reverse-POM', 'pom', {'DebugView': 8, 'PomAmount': 1, 'ReliefCm': 6}, 'Opposite')
        h, w = uv_flat.shape[:2]
        basis = {'red_far_minus_near': float(uv_flat[:h // 3, :, 0].mean() - uv_flat[-h // 3:, :, 0].mean()),
                 'green_right_minus_left': float(uv_flat[:, -w // 3:, 1].mean() - uv_flat[:, :w // 3, 1].mean())}
        require('imported_uv_basis', basis['red_far_minus_near'] > .01 and basis['green_right_minus_left'] > .01, basis)
        direction = {'forward_red_shift': float((uv_forward_pom - uv_forward)[:, :, 0].mean()),
                     'reverse_red_shift': float((uv_reverse_pom - uv_reverse)[:, :, 0].mean())}
        require('opposing_pom_ray_direction', direction['forward_red_shift'] > .001
                and direction['reverse_red_shift'] < -.001, direction)

        # Pixel response plus both texture sampling paths; exactly one writer/one source at a time.
        uv = b'CkUsf_LibraryUV(In.UV, UVScale, UVRotation)'
        ret = b'return CkUsf_LibraryInspect(O, DebugView);'
        wpo = b'(Height - 1.0)'
        if original.count(uv) != 2 or original.count(ret) != 1 or original.count(wpo) != 1:
            raise RuntimeError('Environment source anchors are not unique in the expected pixel/VS paths')
        before = {key: capture('Source-Before-' + key, key, {'DebugView': 1}) for key in initial['environment']}
        changed_source = original.replace(uv, b'CkUsf_LibraryUV(In.UV, UVScale * 1.25, UVRotation)')
        changed_source = changed_source.replace(ret, b'O.BaseColor *= 0.1; return CkUsf_LibraryInspect(O, DebugView);')
        mutate(changed_source)
        changed = {key: capture('Source-Edited-' + key, key, {'DebugView': 1}) for key in initial['environment']}
        mutate(original)
        for key in initial['environment']:
            recovered = capture('Source-Recovered-' + key, key, {'DebugView': 1})
            base = float(before[key].mean())
            metrics = {'baseline_mean': base, 'edited_mean': float(changed[key].mean()),
                       'recovery_difference': difference(before[key], recovered)}
            require('pixel_source_edit_recovery_' + key,
                    base >= .002 and metrics['edited_mean'] < base * .85
                    and metrics['recovery_difference']['mean_absolute_rgb'] < max(.0008, min(.02, base * .12)), metrics)
        vs_before = capture('VS-Before-Depth', 'displacement', {'DebugView': 6, 'DisplacementAmount': 1, 'ReliefCm': 6})
        mutate(original.replace(wpo, b'((Height - 1.0) * 0.0)'))
        vs_off = capture('VS-Edited-Depth', 'displacement', {'DebugView': 6, 'DisplacementAmount': 1, 'ReliefCm': 6})
        d = difference(vs_before, vs_off)
        require('vertex_source_changes_geometry', d['fraction_over_one_code'] > .005, d)
        d = difference(flat, vs_off)
        require('vertex_zero_equals_flat_geometry', d['max_rgb'] <= 2.0 / 255 + 1e-6, d)
        mutate(original)
        vs_recovered = capture('VS-Recovered-Depth', 'displacement', {'DebugView': 6, 'DisplacementAmount': 1, 'ReliefCm': 6})
        d = difference(vs_before, vs_recovered)
        require('vertex_source_recovers_geometry', d['max_rgb'] <= 2.0 / 255 + 1e-6, d)
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
    finally:
        cleanup_errors = []
        for operation in [lambda: mutate(original) if SOURCE.read_bytes() == owned and owned != original else None,
                          lambda: command('restore_quality'), lambda: restore_station('pom'),
                          lambda: restore_station('displacement'), lambda: command('proof_end')]:
            try:
                operation()
            except Exception as error:
                cleanup_errors.append(str(error))
        try:
            final = command('state')
            report['final_state'] = final
            report['restored'] = (not cleanup_errors and SOURCE.read_bytes() == original
                                  and final['pid'] == initial['pid'] and final['library'] == initial['library']
                                  and final['environment'] == initial['environment']
                                  and final['preview_quality'] == initial['preview_quality']
                                  and final['diagnostic_light'] == initial['diagnostic_light']
                                  and final['render_cvars'] == initial['render_cvars'])
        except Exception as error:
            cleanup_errors.append(str(error))
        report['cleanup_errors'] = cleanup_errors
        report['passed'] = report['passed'] and report['restored']
        (OUTPUT / 'Environment1-Proof.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
