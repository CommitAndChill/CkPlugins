"""Same-instance Adaptive hero capture, closure evidence and source/recovery proof."""
import hashlib
import json
import math
from pathlib import Path
import time
import traceback
import numpy as np
from PIL import Image
from adaptive_bsdf_command import submit
from adaptive_bsdf_settings import LOOKS
from verify_industrial_reload import wait_reload

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
SHADERS = ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf'
LOG = ROOT / 'Saved/Logs/CkPlugins.log'


def _same_rig(first, second):
    """Actor transform round trips can differ below a micrometer in UE doubles."""
    if isinstance(first, dict) and isinstance(second, dict):
        return first.keys() == second.keys() and all(_same_rig(first[key], second[key]) for key in first)
    if isinstance(first, list) and isinstance(second, list):
        return len(first) == len(second) and all(_same_rig(a, b) for a, b in zip(first, second))
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        return math.isclose(first, second, rel_tol=1e-9, abs_tol=1e-6)
    return first == second


def _pixels(path):
    image = Image.open(path)
    if image.size != (1280, 960):
        raise RuntimeError('Unexpected capture dimensions: ' + str(image.size))
    pixels = np.asarray(image.convert('RGB'), dtype=np.float64) / 255
    h, w = pixels.shape[:2]
    return pixels[int(h*.23):int(h*.77), int(w*.28):int(w*.72)]


def main():
    initial = submit('state')['result']
    if set(initial['looks']) != set(LOOKS):
        raise RuntimeError('Create the dedicated Adaptive scene first')
    for name, value in initial['looks'].items():
        if not value['compiled']['valid'] or value['compiled']['closure_count'] != 2 or value['compiled']['compile_errors']:
            raise RuntimeError('Both hero assets must retain two compiled closures: ' + name + ': ' + str(value))
    paths = [SHADERS / 'Looks' / (name + '.ush') for name in LOOKS] + [SHADERS / 'AdaptiveSurface.ush']
    originals = {path: path.read_bytes() for path in paths}
    owned = dict(originals)
    report = {'passed': False, 'restored': False, 'initial': initial, 'captures': {}, 'reloads': [], 'metrics': {},
              'presentation': 'Offscreen transient editor scene, approved logo-free shader ball. Orbit videos are fixed-light-phase captures, not performance measurements.'}
    cleanup_errors = []

    def capture(name, label, **values):
        filename = 'AdaptiveBsdf-' + name + '-' + label + '.png'
        result = submit('capture', look=name, name=filename, **values)
        state = result['state']
        if state['pid'] != initial['pid']:
            raise RuntimeError('Editor identity changed')
        for look in LOOKS:
            for key in ['master', 'mid', 'front_node', 'front_class']:
                if state['looks'][look][key] != initial['looks'][look][key]:
                    raise RuntimeError('Native object identity changed: ' + look + '/' + key)
            if not state['looks'][look]['compiled']['valid'] or state['looks'][look]['compiled']['closure_count'] != 2:
                raise RuntimeError('Retained closure evidence changed: ' + look)
        path = OUTPUT / filename
        report['captures'][name + '-' + label] = {'file': filename, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'state': state}
        return _pixels(path)

    def write_probe(path, value):
        if path.read_bytes() != owned[path]:
            raise RuntimeError('Concurrent source edit preserved: ' + str(path))
        offset = LOG.stat().st_size
        path.write_bytes(value)
        owned[path] = value
        report['reloads'].append({'source': str(path.relative_to(ROOT)), 'completion': wait_reload(offset)})

    failure = None
    try:
        for name, recipe in LOOKS.items():
            before = capture(name, 'Close', phase=0)
            repeated = capture(name, 'CloseRepeated', phase=0)
            noise = float(np.abs(repeated-before).mean())
            report['metrics'][name + '-capture-noise'] = noise
            if float(before.std()) < .02 or float(before.mean()) < .015:
                raise RuntimeError('Unusable dark/flat hero capture: ' + name)
            capture(name, 'Macro', distance=3.0, phase=0)
            capture(name, 'Gameplay', distance=8.5, phase=0)
            path = SHADERS / 'Looks' / (name + '.ush')
            needle = b'    return O;'
            if originals[path].count(needle) != 1:
                raise RuntimeError('Entrypoint proof anchor differs: ' + name)
            replacement = b'    O.ADiffuseAlbedo *= 0.15; O.BDiffuseAlbedo *= 0.15; O.AF0 *= 0.15; O.BF0 *= 0.15;\n' + needle
            write_probe(path, originals[path].replace(needle, replacement))
            edited = capture(name, 'SourceEdited', phase=0)
            write_probe(path, originals[path])
            recovered = capture(name, 'SourceRecovered', phase=0)
            edit_delta = float(np.abs(edited-before).mean())
            recovery_delta = float(np.abs(recovered-before).mean())
            report['metrics'][name + '-source'] = {'edit_mean_abs_rgb': edit_delta, 'recovery_mean_abs_rgb': recovery_delta}
            if edit_delta < .005 or recovery_delta > .025:
                raise RuntimeError('Entrypoint edit/recovery visual proof failed: ' + name)
            controls = ({'CoatRough': {'TopRoughnessScale': 0, 'TopRoughnessBias': .6},
                         'ThinDye': {'ThicknessCm': .0002}}
                        if name == 'AdaptiveCandyPaint' else
                        {'LobeAOnly': {'LobeWeight': 1, 'SlubWeightVariation': 0},
                         'LobeBOnly': {'LobeWeight': 0, 'SlubWeightVariation': 0}})
            defaults = initial['looks'][name]['scalars']
            for label, values in controls.items():
                control = capture(name, label, phase=0, scalars=values)
                delta = float(np.abs(control-before).mean())
                restored = capture(name, label + 'Restored', phase=0, scalars={key: defaults[key] for key in values})
                recovery = float(np.abs(restored-before).mean())
                report['metrics'][name + '-' + label] = {'edit_mean_abs_rgb': delta, 'recovery_mean_abs_rgb': recovery}
                if delta < max(.003, noise*3) or recovery > max(.025, noise*3):
                    raise RuntimeError('Independent control/recovery proof failed: ' + name + '/' + label)
            for index in range(24):
                capture(name, 'Orbit%02d' % index, phase=index*15)
            capture(name, 'Final', phase=0)
        before = {name: capture(name, 'HelperBaseline', phase=0) for name in LOOKS}
        path = SHADERS / 'AdaptiveSurface.ush'
        needle = b'return InColor;'
        if originals[path].count(needle) != 1:
            raise RuntimeError('Shared helper probe anchor differs')
        write_probe(path, originals[path].replace(needle, b'return InColor * 0.15;'))
        for name in LOOKS:
            edited = capture(name, 'HelperEdited', phase=0)
            delta = float(np.abs(edited-before[name]).mean())
            report['metrics'][name + '-helper-edit'] = delta
            if delta < .005:
                raise RuntimeError('Shared helper produced no meaningful change: ' + name)
        write_probe(path, originals[path])
        for name in LOOKS:
            recovered = capture(name, 'HelperRecovered', phase=0)
            delta = float(np.abs(recovered-before[name]).mean())
            report['metrics'][name + '-helper-recovery'] = delta
            if delta > .025:
                raise RuntimeError('Shared helper recovery differs: ' + name)
        report['passed'] = True
    except Exception:
        failure = traceback.format_exc()
        report['error'] = failure
    finally:
        for path, original in originals.items():
            try:
                if path.read_bytes() != owned[path]:
                    raise RuntimeError('Concurrent source change; refusing to overwrite ' + str(path))
                if owned[path] != original:
                    try:
                        offset = LOG.stat().st_size
                    except Exception as error:
                        cleanup_errors.append('Recovery log unavailable: ' + str(error))
                        offset = None
                    path.write_bytes(original)
                    owned[path] = original
                    if offset is not None:
                        report['reloads'].append({'source': str(path.relative_to(ROOT)), 'completion': wait_reload(offset)})
            except Exception as error:
                cleanup_errors.append(str(error))
        for name, recipe in LOOKS.items():
            try:
                capture(name, 'CleanupRestored', phase=0, scalars=initial['looks'][name]['scalars'])
            except Exception as error:
                cleanup_errors.append(str(error))
        try:
            first = next(name for name in LOOKS if initial['looks'][name]['mid'] == initial['selected_mid'])
            capture(first, 'SelectionRestored', phase=0)
            report['final'] = submit('state')['result']
            for name in LOOKS:
                for key in ['scalars', 'vectors', 'textures', 'master', 'mid', 'front_node', 'front_class']:
                    if report['final']['looks'][name][key] != initial['looks'][name][key]:
                        cleanup_errors.append('Final binding differs: ' + name + '/' + key)
            if not _same_rig(report['final']['rig'], initial['rig']):
                cleanup_errors.append('Final scene state differs: rig')
            for key in ['cvars', 'selected_mid']:
                if report['final'][key] != initial[key]:
                    cleanup_errors.append('Final scene state differs: ' + key)
        except Exception as error:
            cleanup_errors.append('Final state: ' + str(error))
        report['cleanup_errors'] = cleanup_errors
        try:
            source_restored = all(path.read_bytes() == value for path, value in originals.items())
        except Exception as error:
            cleanup_errors.append('Final source check: ' + str(error))
            source_restored = False
        report['restored'] = not cleanup_errors and source_restored
        report['passed'] = report['passed'] and report['restored']
        report['original_source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(value).hexdigest() for path, value in originals.items()}
        report['final_source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.is_file()}
        (OUTPUT / 'AdaptiveBsdf-RenderedProof.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if failure or not report['passed']:
        raise RuntimeError(failure or str(cleanup_errors))
    print(json.dumps({'passed': True, 'restored': report['restored'], 'captures': len(report['captures']), 'metrics': report['metrics']}, indent=2))


if __name__ == '__main__':
    main()
