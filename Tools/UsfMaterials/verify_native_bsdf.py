"""Rendered same-instance native BSDF proof using the existing offscreen studio bridge.

Restores shader bytes and temporary lighting/quality settings. Run serially.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import traceback
import numpy as np
from PIL import Image
from verify_industrial_reload import command, wait_reload, ROOT, OUTPUT, LOG, SHADERS

LOOKS = ['NativePorcelainSlab', 'NativeCeramicToon']


def roi(path):
    image = np.asarray(Image.open(path).convert('RGB'), dtype=np.float64) / 255
    h, w = image.shape[:2]
    return image[int(h*.35):int(h*.65), int(w*.38):int(w*.62)]


def material_state(state):
    """Compare operative bindings/overrides without proof-only identity flags."""
    def record(value):
        return {key: item for key, item in value.items() if key not in ['same_mid', 'same_master']}
    return {'library': {name: record(value) for name, value in state['library'].items()},
            'environment': {name: record(value) for name, value in state['environment'].items()},
            'industrial': [record(value) for value in state['industrial']]}


def main(prefix='NativeBsdf', advanced=False, orbit_frames=24):
    looks = LOOKS
    if advanced:
        from advanced_bsdf_settings import LOOKS as recipes
        looks = list(recipes)
    initial = command('state')
    if not set(looks).issubset(initial['native_bsdf']):
        raise RuntimeError('Prepare and open the requested native BSDF specimens first')
    if initial['preview_quality'] or initial['inspection_orbit']['enabled']:
        raise RuntimeError('Start with preview-quality and orbit diagnostics restored')
    if initial['inspection_orbit']['target'] is not None or initial['inspection_orbit']['intensity'] != 0:
        raise RuntimeError('Disabled inspection light must have no target and zero intensity')
    if initial['diagnostic_light'] is not None:
        raise RuntimeError('Restore the existing diagnostic light before native capture')
    if any(initial['library'][name]['values']['DebugView'] != 0 for name in looks):
        raise RuntimeError('Both native specimens must start with DebugView zero')
    records = (list(initial['library'].values()) + list(initial['environment'].values())
               + initial['industrial'])
    if any(value.get('same_mid') is not None for value in records):
        raise RuntimeError('End the existing identity proof before starting this proof')
    originals = {name: (SHADERS / 'Looks' / (name + '.ush')).read_bytes() for name in looks}
    owned = dict(originals)
    report = {'passed': False, 'restored': False, 'pid': initial['pid'], 'captures': {},
              'reloads': [], 'metrics': {}, 'native_nodes': initial['native_bsdf'], 'initial_state': initial,
              'scope': 'Native UE5.8 BSDF expressions, same textured ball and existing studio rig. '
                       'Orbit videos encode paused native Point-light phases, not real-time or performance footage.'}
    quality = False
    proof = False
    orbit_touched = False
    failure = None
    cleanup_errors = []

    def cleanup(label, operation):
        try:
            return operation()
        except Exception as error:
            cleanup_errors.append({'operation': label, 'error': repr(error)})
            return None

    def capture(name, label, distance=210, height=35, parameters=None):
        filename = f'{prefix}-{name}-{label}.png'
        overrides = []
        for key, value in (parameters or {}).items():
            overrides += ['--scalar', f'{key}={value}']
        result = command('capture', '--look', name, '--name', filename, '--distance', distance,
                         '--height', height, '--debug', 0, '--lighting', 'studio', '--shot', *overrides)
        state = result['state']
        if state['pid'] != initial['pid'] or state['native_bsdf'] != initial['native_bsdf']:
            raise RuntimeError('Native node/profile or editor identity changed')
        if proof and not all(state['library'][look]['same_mid'] and state['library'][look]['same_master'] for look in looks):
            raise RuntimeError('Native master or MID identity changed')
        record = {'file': filename, 'sha256': hashlib.sha256((OUTPUT/filename).read_bytes()).hexdigest(), 'state': state}
        report['captures'][name + '-' + label] = record
        return roi(OUTPUT/filename)

    try:
        quality = True
        command('preview_quality')
        proof = True
        command('library_proof_begin')
        for name in looks:
            before = capture(name, 'Close')
            capture(name, 'Macro', 135, 20)
            capture(name, 'Gameplay', 440, 260)
            path = SHADERS / 'Looks' / (name + '.ush')
            needle = b'O.DiffuseAlbedo = Albedo;' if name == LOOKS[0] else b'O.BaseColor = Albedo;'
            replacement = (b'O.DiffuseAlbedo = Albedo * 0.15; O.F0 *= 0.15;' if name == LOOKS[0]
                           else b'O.BaseColor = Albedo * 0.15;')
            if not advanced and (originals[name].count(needle) != 1 or path.read_bytes() != originals[name]):
                raise RuntimeError('Probe anchor or shader ownership changed: ' + name)
            probe = originals[name].replace(needle, replacement)
            if name == LOOKS[1]:
                specular = b'O.Specular = 0.5;'
                if originals[name].count(specular) != 1:
                    raise RuntimeError('Toon specular assignment must match exactly once')
                probe = probe.replace(specular, b'O.Specular = 0.5 * 0.15;')
            if advanced:
                needle = b'return O;'
                extra = b' O.FuzzAmount *= 0.15;' if recipes[name]['slab_fuzz'] else b''
                if recipes[name]['surface_graph'] == 3:
                    extra += b' O.CoatCoverage *= 0.15;'
                replacement = b'O.DiffuseAlbedo *= 0.15; O.F0 *= 0.15;' + extra + b' return O;'
                if originals[name].count(needle) != 1 or path.read_bytes() != originals[name]:
                    raise RuntimeError('Advanced probe anchor or shader ownership changed: ' + name)
                probe = originals[name].replace(needle, replacement)
            offset = LOG.stat().st_size
            owned[name] = probe
            path.write_bytes(owned[name])
            report['reloads'].append(wait_reload(offset))
            edited = capture(name, 'Edited')
            if path.read_bytes() != owned[name]:
                raise RuntimeError('Concurrent shader edit preserved: ' + name)
            offset = LOG.stat().st_size
            path.write_bytes(originals[name])
            owned[name] = originals[name]
            report['reloads'].append(wait_reload(offset))
            restored = capture(name, 'Restored')
            change = float(np.abs(before-edited).mean())
            recovery = float(np.abs(before-restored).mean())
            report['metrics'][name] = {'edited_mean_absolute_rgb': change, 'restored_mean_absolute_rgb': recovery}
            if change < .01 or recovery > .035:
                raise RuntimeError('Rendered source/recovery difference did not meet the native proof: ' + name)
            if advanced:
                feature = {}
                defaults = initial['library'][name]['values']
                if recipes[name]['slab_fuzz']:
                    disabled = capture(name, 'FuzzOff', parameters={'FuzzWeight': 0})
                    feature['fuzz_on_vs_off'] = float(np.abs(restored-disabled).mean())
                if recipes[name]['surface_graph'] == 3:
                    disabled = capture(name, 'CoatOff', parameters={'CoatWeight': 0})
                    feature['coat_on_vs_off'] = float(np.abs(restored-disabled).mean())
                    rough = capture(name, 'CoatRough', parameters={'CoatWeight': defaults['CoatWeight'], 'CoatRoughness': .65})
                    feature['coat_smooth_vs_rough'] = float(np.abs(restored-rough).mean())
                if feature:
                    capture(name, 'FeatureRestored', parameters=defaults)
                    report.setdefault('feature_metrics', {})[name] = feature
                    if any(value < .0007 for value in feature.values()):
                        raise RuntimeError('Native feature contrast is too small: ' + name)
        command('proof_end')
        proof = False
        for name in looks:
            command('select', '--look', name, '--distance', 210, '--height', 35)
            frames = []
            try:
                orbit_touched = True
                command('orbit_on')
                command('orbit_pause')
                for index in range(orbit_frames):
                    phase = index*360/orbit_frames
                    state = command('orbit_phase', '--phase', phase)
                    if state['native_bsdf'] != initial['native_bsdf']:
                        raise RuntimeError('Native node/profile changed during orbit')
                    filename = f'{prefix}-{name}-Orbit-{index:03d}.png'
                    result = command('capture', '--look', name, '--name', filename,
                                     '--distance', 210, '--height', 35, '--debug', 0, '--shot')
                    frames.append({'file': filename, 'sha256': hashlib.sha256((OUTPUT/filename).read_bytes()).hexdigest(),
                                   'light': result['state']['inspection_orbit']})
            finally:
                cleanup('disable orbit after ' + name, lambda: command('orbit_off'))
            destination = OUTPUT/f'{prefix}-{name}-Orbit.mp4'
            if destination.exists():
                raise RuntimeError('Preserve the existing native preview before encoding another')
            subprocess.run(['ffmpeg', '-v', 'error', '-n', '-framerate', '4', '-i',
                            str(OUTPUT/f'{prefix}-{name}-Orbit-%03d.png'), '-frames:v', str(orbit_frames),
                            '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(destination)], check=True)
            report.setdefault('orbits', {})[name] = {'file': destination.name, 'fps': 4, 'frames': frames,
                                                   'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
        report['passed'] = True
    except Exception as error:
        failure = error
        report['error'] = traceback.format_exc()
    finally:
        if advanced:
            for name in looks:
                def restore_parameters(name=name):
                    args = []
                    for key, value in initial['library'][name]['values'].items():
                        args += ['--scalar', f'{key}={value}']
                    return command('select', '--look', name, *args)
                cleanup('restore material parameters ' + name, restore_parameters)
        if orbit_touched:
            cleanup('disable orbit', lambda: command('orbit_off'))
            cleanup('restore orbit phase', lambda: command('orbit_phase', '--phase', initial['inspection_orbit']['phase']))
            cleanup('restore orbit pause', lambda: command('orbit_pause' if initial['inspection_orbit']['paused'] else 'orbit_resume'))
        for name, original in originals.items():
            def restore_source(name=name, original=original):
                path = SHADERS/'Looks'/(name+'.ush')
                current = path.read_bytes()
                if current == original:
                    return
                if current != owned[name]:
                    report.setdefault('concurrent_edits_preserved', []).append(name)
                    raise RuntimeError('Concurrent shader edit preserved: ' + name)
                # A missing log must not prevent recovery of owned source bytes.
                offset = cleanup('read reload log for ' + name, lambda: LOG.stat().st_size)
                path.write_bytes(original)
                owned[name] = original
                if offset is not None:
                    report['reloads'].append(wait_reload(offset))
            cleanup('restore source ' + name, restore_source)
        if proof:
            cleanup('release proof objects', lambda: command('proof_end'))
        if quality:
            cleanup('restore quality', lambda: command('restore_quality'))
        final = cleanup('read final state', lambda: command('state'))
        def restored_contract():
            orbit = final['inspection_orbit']
            previous = initial['inspection_orbit']
            phase_error = abs((orbit['phase'] - previous['phase'] + 180) % 360 - 180)
            return (all((SHADERS/'Looks'/(name+'.ush')).read_bytes() == original for name, original in originals.items())
                    and final['pid'] == initial['pid'] and final['native_bsdf'] == initial['native_bsdf']
                    and not final['preview_quality'] and final['render_cvars'] == initial['render_cvars']
                    and final['diagnostic_light'] == initial['diagnostic_light']
                    and final['diagnostic_quantization'] == initial['diagnostic_quantization']
                    and not orbit['enabled'] and orbit['target'] is None and orbit['intensity'] == 0
                    and orbit['actor'] == previous['actor'] and orbit['paused'] == previous['paused']
                    and phase_error < 1e-4 and orbit['rigs'] == previous['rigs']
                    and material_state(final) == material_state(initial))
        restored = cleanup('verify restoration contract', restored_contract) if final is not None else False
        report['restored'] = bool(restored and not cleanup_errors)
        report['cleanup_errors'] = cleanup_errors
        report['final_state'] = final
        report['passed'] = report['passed'] and report['restored']
        (OUTPUT/(prefix+'-RenderedProof.json')).write_text(json.dumps(report, indent=2))
    print(json.dumps({'passed': report['passed'], 'restored': report['restored'], 'pid': report['pid']}))
    if failure is not None:
        raise RuntimeError('Native BSDF proof failed; inspect its restoration receipt') from failure
    if not report['passed']:
        raise RuntimeError('Native BSDF cleanup or restoration contract failed; inspect its receipt')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', default='NativeBsdf')
    parser.add_argument('--advanced', action='store_true')
    parser.add_argument('--orbit-frames', type=int, choices=[12, 24], default=24)
    args = parser.parse_args()
    if not args.prefix.replace('-', '').isalnum():
        parser.error('Prefix must contain only letters, numbers and hyphens')
    main(args.prefix, args.advanced, args.orbit_frames)
