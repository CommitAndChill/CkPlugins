"""Serial opt-in inspection-light proof; run only when the lead owns the studio bridge."""
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
from PIL import Image
from verify_industrial_reload import command, OUTPUT, ROOT

POINT_SETTINGS = {'ground': {'intensity': 40, 'source_radius': 6, 'attenuation_radius': 200},
                  'ball': {'intensity': 120, 'source_radius': 12, 'attenuation_radius': 260}}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def material_state(state):
    return {section: {key: {field: value for field, value in item.items() if field != 'rect_intensities'}
                      for key, item in state[section].items()} for section in ['library', 'environment']} | {'industrial': state['industrial']}


def angular_error(left, right):
    return abs((left-right+180) % 360-180)


def roi(path):
    data = np.asarray(Image.open(path).convert('RGB'), dtype=float)/255
    height, width = data.shape[:2]
    return data[int(height*.34):int(height*.67), int(width*.35):int(width*.65)]


def difference(a, b):
    require(a.shape == b.shape and a.size > 0, 'Capture ROI dimensions differ')
    delta = np.abs(a-b)
    return {'mean_absolute_rgb': float(delta.mean()), 'max_rgb': float(delta.max())}


def fit_orbit(states, radius, height, target_origin=None):
    points = np.array([state['inspection_orbit']['light_location'] for state in states], dtype=float)
    require(points.shape == (4, 3) and np.isfinite(points).all(), 'Four finite cardinal light positions required')
    center = points.mean(axis=0)
    offsets = np.array([[-radius, 0], [0, radius], [radius, 0], [0, -radius]])
    error = float(np.max(np.linalg.norm(points[:, :2]-center[:2]-offsets, axis=1)))
    require(error < .1 and float(np.ptp(points[:, 2])) < .01, 'Cardinal positions do not describe the declared horizontal orbit')
    result = {'fitted_light_center': center.tolist(), 'inferred_target_center': (center-np.array([0, 0, height])).tolist(),
              'max_cardinal_error_cm': error, 'height_spread_cm': float(np.ptp(points[:, 2])), 'radius_cm': radius, 'height_cm': height}
    if target_origin is not None:
        result['target_center_error_cm'] = float(np.linalg.norm(center-np.array(target_origin)-np.array([0, 0, height])))
        require(result['target_center_error_cm'] < .1, 'Ball orbit does not center on actual mesh bounds')
    return result


def main():
    initial = command('state')
    orbit = initial['inspection_orbit']
    require(isinstance(orbit, dict) and not orbit['enabled'] and orbit['intensity'] == 0 and orbit['target'] is None, 'Start with the single owned orbit light off')
    require(len(initial['library']) == 42 and set(initial['environment']) == {'pom', 'displacement'}
            and len(initial['industrial']) == 4, 'The complete material gym must be active')
    require(not initial['preview_quality'] and not initial['diagnostic_quantization'] and initial['diagnostic_light'] is None,
            'Restore temporary renderer and lighting diagnostics before orbit proof')
    require(initial['render_cvars']['r.AntiAliasingMethod'] == 0 and initial['render_cvars']['r.ScreenPercentage'] == 87,
            'Orbit proof requires native baseline AA0 / 87 percent')
    for item in [*initial['library'].values(), *initial['environment'].values(), *initial['industrial']]:
        require(item['same_mid'] is None and item['same_master'] is None, 'End existing source-object proofs first')
    baseline_materials = material_state(initial)
    baseline_rigs = orbit['rigs']
    require(len(baseline_rigs) >= 54, 'Expected the full studio-rig roster')
    sources = [ROOT/'Plugins/CkTests/Script/CkUsf'/name for name in ['CkUsfGym_InspectionLight.as', 'CkUsfGym_PlayerController.as']]
    source_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    report = {'passed': False, 'restored': False, 'initial_state': initial, 'states': [], 'captures': {}, 'metrics': {},
              'source_sha256': source_hashes, 'expected_point_settings': POINT_SETTINGS,
              'limits': ['Phase-sampled preview is not real-time footage or a frame-rate/performance measurement.',
              '36 paused samples at 10-degree increments, encoded externally at 4 fps, play in 9 seconds: twice the nominal 20 degrees/second orbit speed.',
              'Inspection uses a native Point light; point-source rotation is not a meaningful illumination control.',
              'Visible silk/aluminum response does not independently isolate anisotropy from their other surface controls.',
              'Neighbor rig intensities and exclusion of their actual bounds from the light attenuation sphere are checked; EndPlay/respawn cleanup is separate.',
              'Camera and controller selection intentionally follow the inspected stations; material values and original rig intensities are restored.']}

    def validate(state, label):
        current = state['inspection_orbit']
        require(state['pid'] == initial['pid'] and current['actor'] == orbit['actor'], 'Editor or inspection actor changed: '+label)
        require(current['light_class'] == 'PointLightComponent' and '.CANDELAS:' in current['intensity_units'],
                'Inspection must use the native Point light in candela units: '+label)
        require(material_state(state) == baseline_materials, 'Material identities/bindings/values changed: '+label)
        require(state['render_cvars'] == initial['render_cvars'] and not state['preview_quality']
                and not state['diagnostic_quantization'] and state['diagnostic_light'] is None, 'Renderer diagnostic state changed: '+label)
        require(set(current['rigs']) == set(baseline_rigs), 'Studio rig roster changed: '+label)
        for actor, expected in baseline_rigs.items():
            values = current['rigs'][actor]
            if current['enabled'] and actor == current['target']:
                require(len(values) == 3 and all(math.isclose(a, b, abs_tol=1e-4, rel_tol=1e-7)
                        for a, b in zip(values, [0, expected[1]*.15, 0])), 'Selected rig was not dimmed as declared: '+label)
            else:
                require(values == expected, 'A nonselected rig was changed or did not restore: '+label)
        if current['enabled']:
            position=np.array(current['light_location'],dtype=float)
            for actor,bounds in current['rig_bounds'].items():
                if actor==current['target']: continue
                origin=np.array(bounds['origin'],dtype=float);extent=np.array(bounds['extent'],dtype=float)
                distance=float(np.linalg.norm(np.maximum(np.abs(position-origin)-extent,0)))
                require(distance>current['attenuation_radius'], 'Inspection light reaches another station bounds: '+label+'/'+actor)
        if current['enabled']:
            ground = current['target'] in {item['actor'] for item in initial['environment'].values()}
            settings = POINT_SETTINGS['ground' if ground else 'ball']
            require(current['target'] in baseline_rigs and all(current[key] == value for key, value in settings.items())
                    and current['speed'] == 20, 'Active Point orbit contract differs: '+label)
        else:
            require(current['target'] is None and current['intensity'] == 0, 'Off orbit still targets or emits light: '+label)
        report['states'].append({'label': label, 'world_time': state['world_time'], 'state': state})
        return state

    def action(name, *args):
        return validate(command(name, *args), name)

    def capture(label, selector, phase):
        state = action('orbit_phase', '--phase', phase)
        require(state['inspection_orbit']['enabled'] and state['inspection_orbit']['paused'], 'Capture must use a paused active orbit')
        require(angular_error(state['inspection_orbit']['phase'], phase) < 1e-4, 'Explicit phase was not applied')
        filename = 'OrbitLight-'+label+'.png'
        camera = ['--distance', 65, '--height', 45] if selector[0] == '--environment' else ['--distance', 210, '--height', 35]
        state = validate(command('capture', *selector, '--name', filename, '--shot', *camera)['state'], label)
        require(state['inspection_orbit']['paused'] and angular_error(state['inspection_orbit']['phase'], phase) < 1e-4,
                'Orbit drifted during paused capture')
        path = OUTPUT/filename
        require(path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n', 'Capture is not a PNG')
        report['captures'][label] = {'image': filename, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                     'phase_degrees': phase, 'world_time': state['world_time'], 'state': state}
        print('Orbit capture '+label, flush=True)
        return state, roi(path)

    def target_required(state, target, radius, height):
        current = state['inspection_orbit']
        require(current['enabled'] and current['target'] == target and current['radius'] == radius and current['height'] == height,
                'Selection did not retarget the reusable orbit')

    def response(name, baseline, repeat, opposite):
        noise = difference(baseline, repeat)
        effect = difference(baseline, opposite)
        threshold = max(.001, 3*noise['mean_absolute_rgb'])
        require(effect['mean_absolute_rgb'] > threshold, 'Opposing light response does not exceed repeat noise: '+name)
        report['metrics'][name+' light response'] = {'same_phase_repeat': noise, 'phase0_vs180': effect, 'required_mean_above_noise': threshold}

    try:
        validate(initial, 'initial Point-light contract')
        selector = ['--environment', 'displacement']
        action('select', *selector)
        action('orbit_pause')
        state = action('orbit_on')
        target_required(state, initial['environment']['displacement']['actor'], 100, 70)
        cardinal, phase_pixels = {}, {}
        frames = []
        for index in range(36):
            phase = index*10
            state, pixels = capture(f'Phase-{index:03d}', selector, phase)
            frames.append({'index': index, 'phase_degrees': phase, 'image': f'OrbitLight-Phase-{index:03d}.png'})
            if phase in [0, 90, 180, 270]:
                cardinal[phase], phase_pixels[phase] = state, pixels
            if index == 0:
                _, repeat = capture('Ground-Phase0-Repeat', selector, 0)
        report['metrics']['ground orbit geometry'] = fit_orbit([cardinal[phase] for phase in [0, 90, 180, 270]], 100, 70)
        response('ground', phase_pixels[0], repeat, phase_pixels[180])
        report['phase_preview'] = {'frames': frames, 'frame_count': 36, 'phase_increment_degrees': 10,
                                   'suggested_fps': 4, 'duration_seconds': 9, 'playback_speed_relative_to_nominal': 2,
                                   'label': 'Paused phase-sampled inspection preview, 2x nominal orbit speed; not real-time footage'}

        action('orbit_reset')
        require(angular_error(report['states'][-1]['state']['inspection_orbit']['phase'], 0) < 1e-4, 'Reset did not return to phase zero')
        running_start = action('orbit_resume')
        time.sleep(1.25)
        running_end = action('state')
        elapsed = running_end['world_time']-running_start['world_time']
        phase_delta = (running_end['inspection_orbit']['phase']-running_start['inspection_orbit']['phase']) % 360
        require(0 < elapsed < 8 and angular_error(phase_delta, 20*elapsed) <= 2 and phase_delta > 1,
                'Actual tick motion does not match 20 degrees/second of world time')
        require(np.linalg.norm(np.array(running_end['inspection_orbit']['light_location'])-running_start['inspection_orbit']['light_location']) > 1,
                'Phase advanced without moving the actual light')
        report['metrics']['actual tick motion'] = {'world_elapsed_seconds': elapsed, 'phase_delta_degrees': phase_delta,
                                                  'expected_phase_delta_degrees': 20*elapsed, 'tolerance_degrees': 2}
        paused_start = action('orbit_pause')
        time.sleep(.35)
        paused_end = action('state')
        require(paused_start['inspection_orbit']['paused'] and paused_end['world_time'] > paused_start['world_time']
                and angular_error(paused_start['inspection_orbit']['phase'], paused_end['inspection_orbit']['phase']) < 1e-5
                and paused_start['inspection_orbit']['light_location'] == paused_end['inspection_orbit']['light_location'], 'Pause did not halt light movement while the world advanced')
        report['metrics']['paused motion'] = {'world_elapsed_seconds': paused_end['world_time']-paused_start['world_time'],
                                             'phase_error_degrees': angular_error(paused_start['inspection_orbit']['phase'], paused_end['inspection_orbit']['phase'])}
        for name in ['LibraryAluminum', 'LibrarySilk']:
            selector = ['--look', name]
            state = action('select', *selector)
            target_required(state, initial['library'][name]['actor'], 210, 90)
            states, pixels_by_phase = [], {}
            for phase in [0, 90, 180, 270]:
                state, pixels_by_phase[phase] = capture(name+f'-Phase{phase}', selector, phase)
                states.append(state)
                if phase == 0:
                    _, repeat = capture(name+'-Phase0-Repeat', selector, 0)
            report['metrics'][name+' orbit geometry'] = fit_orbit(states, 210, 90, initial['library'][name]['mesh_bounds']['origin'])
            response(name, pixels_by_phase[0], repeat, pixels_by_phase[180])
        action('orbit_off')
        report['passed'] = True
    except BaseException as error:
        report['error'] = str(error)
        raise
    finally:
        errors = []
        def cleanup(label, operation):
            try:
                return operation()
            except BaseException as error:
                errors.append(label+': '+str(error))
        # Turn off first, then restore the owned diagnostic's numeric state independently.
        cleanup('orbit off', lambda: command('orbit_off'))
        cleanup('phase', lambda: command('orbit_phase', '--phase', orbit['phase']))
        cleanup('paused', lambda: command('orbit_pause' if orbit['paused'] else 'orbit_resume'))
        final = cleanup('final state', lambda: command('state'))
        if final is not None:
            cleanup('final contract', lambda: validate(final, 'restored'))
        def restored_contract():
            source_restored = all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected for path, expected in source_hashes.items())
            final_orbit = final['inspection_orbit']
            return (source_restored and material_state(final) == baseline_materials
                    and final_orbit['rigs'] == baseline_rigs and not final_orbit['enabled'] and final_orbit['intensity'] == 0
                    and final_orbit['target'] is None and final_orbit['paused'] == orbit['paused']
                    and angular_error(final_orbit['phase'], orbit['phase']) < 1e-4)
        restored = cleanup('restoration contract', restored_contract) if final is not None else False
        report['restored'] = bool(not errors and restored)
        report['final_state'], report['cleanup_errors'] = final, errors
        report['passed'] = report['passed'] and report['restored']
        (OUTPUT/'OrbitLight-Proof.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
