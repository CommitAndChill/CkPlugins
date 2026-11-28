"""Fresh real-RHI additive finish comparison and same-instance .ush recovery proof."""
from pathlib import Path
import hashlib
import json
import math
import traceback
import uuid
import numpy as np
from PIL import Image
from tail_lamp_command import submit
from verify_industrial_reload import wait_reload

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
SHADERS = ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf'
LENS, LED = 'OpticalTailLampLens', 'OpticalTailLampLED'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report_path = OUTPUT / 'TailLamp-RefinedProof.json'
    if report_path.exists():
        raise RuntimeError('Preserve the existing refined proof before running again')
    first = submit('state')['result']
    if not first['looks'] or first['adaptive'] != 1:
        raise RuntimeError('Construct a refined-capable owned studio first')
    paths = [SHADERS / 'Looks/OpticalTailLampLensRefined.ush', SHADERS / 'TailLampOptics.ush']
    originals = {path: path.read_bytes() for path in paths}
    owned = dict(originals)
    # Exact immutable source files, original definitions/masters and original texture assets.
    preserved_paths = list((ROOT / 'Plugins/CkTests/Resources/CkUsf/TailLampV1').rglob('*'))
    for role in ['Lens', 'Reflector', 'Housing', 'LED', 'Gasket', 'Fastener', 'LEDPackage']:
        for folder, prefix in [('Looks/Optical', 'DA_'), ('GeneratedLooks', 'M_CkUsf_Look_')]:
            preserved_paths.append(ROOT / 'Plugins/CkFoundation/Content/CkUsf' / folder / (prefix + 'OpticalTailLamp' + role + '.uasset'))
    preserved_paths += list((ROOT / 'Plugins/CkFoundation/Content/CkUsf/Textures/Optical').glob('T_TailLamp_*.uasset'))
    preserved_paths += [SHADERS / 'Looks/OpticalTailLampLens.ush', SHADERS / 'Looks/OpticalTailLampHardware.ush']
    if any(not path.is_file() for path in preserved_paths if path.suffix == '.uasset'):
        raise RuntimeError('An original asset is missing')
    preserved = {str(path.relative_to(ROOT)): digest(path) for path in preserved_paths if path.is_file()}
    run_id = uuid.uuid4().hex[:12]
    report = dict(passed=False, restored=False, run_id=run_id, editor_pid=first['pid'], captures={}, metrics={},
                  reloads=[], cleanup_errors=[], preserved_originals=preserved)
    identities, defaults = {}, {}

    def capture(label, variant='refined', **values):
        filename = 'TailLampRefined-' + run_id + '-' + label + '.png'
        path = OUTPUT / filename
        if path.exists():
            raise RuntimeError('Preserve existing capture')
        result = submit('capture', name=filename, variant=variant, **values)
        state = result['state']
        if state['pid'] != first['pid'] or state['variant'] != variant:
            raise RuntimeError('Capture editor/variant differs')
        if variant not in identities:
            identities[variant] = state
            defaults[variant] = {name: {key: record[key] for key in ['scalars', 'vectors']} for name, record in state['looks'].items()}
        initial = identities[variant]
        for name, record in initial['looks'].items():
            if any(state['looks'][name][key] != record[key] for key in ['master', 'mid', 'textures']):
                raise RuntimeError('Variant object identity or texture binding changed')
        lens = state['looks'][LENS]
        if (not lens['compiled']['valid'] or lens['compiled']['compile_errors'] or lens['compiled']['closure_count'] != 1
                or lens['front'] != initial['looks'][LENS]['front']):
            raise RuntimeError('Incomplete or changed native resource')
        image = Image.open(path).convert('RGB')
        if image.size != (1600, 1000):
            raise RuntimeError('Capture dimensions differ')
        report['captures'][label] = dict(file=filename, sha256=digest(path), state=state)
        return np.asarray(image, dtype=np.float32)[150:850, 200:1400] / 255

    def change(a, b):
        return float(np.abs(a - b).mean())

    def reset(variant):
        return dict(scalars={name: values['scalars'] for name, values in defaults[variant].items()},
                    vectors={name: values['vectors'] for name, values in defaults[variant].items()})

    def source(path, data):
        if path.read_bytes() != owned[path]:
            raise RuntimeError('Concurrent source edit preserved')
        offset = (ROOT / 'Saved/Logs/CkPlugins.log').stat().st_size
        path.write_bytes(data)
        owned[path] = data
        report['reloads'].append(dict(source=str(path.relative_to(ROOT)), completion=wait_reload(offset)))

    failure = None
    rig = dict(camera=[49, -25, 19], phase=-30, source_radii=[1, 30, 1], intensities=[35, 12, 25], sky_intensity=3, exposure=4.2)
    try:
        # Finish switches can invalidate reflection history. Record one settling
        # capture, then require two matching-state captures within a fixed bound.
        # Retain all frames, including settling frames; no best-frame selection.
        stable_ranges = []
        def settled(label, variant):
            capture(label + 'Settling', variant=variant, **rig)
            before = capture(label + 'StabilityProbe', variant=variant, **rig)
            after = capture(label, variant=variant, **rig)
            delta = change(before, after)
            stable_ranges.append(delta)
            if delta > .005:
                raise RuntimeError('Finish comparison capture remains unstable: ' + label)
            return after
        original = settled('Original', 'original')
        refined = settled('Refined', 'refined')
        original_recovered = settled('OriginalRecovered', 'original')
        reference = settled('RefinedRepeated', 'refined')
        noise = max(change(refined, reference), *stable_ranges)
        report['metrics']['comparison'] = dict(change=change(original, refined), baseline_recovery=change(original, original_recovered), temporal_noise=noise)
        report['metrics']['comparison']['stability_pair_deltas'] = stable_ranges
        if change(original, refined) < max(.005, noise * 3) or change(original, original_recovered) > .02:
            raise RuntimeError('Matched finish comparison/recovery not established')
        if identities['original']['looks'][LED]['mid'] == identities['refined']['looks'][LED]['mid']:
            raise RuntimeError('Variants must have independent LED MIDs')
        capture('Front', camera=[58, 0, 10])
        capture('Opposite', camera=[49, 25, 19])
        capture('Macro', camera=[34, -16, 13])
        capture('Interior', camera=[49, -25, 19], hide_lens=True)
        capture('CoverRestored', hide_lens=False)
        for label, controls in [('Rough', {'RoughnessScale': 0, 'RoughnessBias': .32}), ('Flat', {'NormalStrength': 0})]:
            before = capture(label + 'Baseline')
            endpoint = capture(label, scalars={LENS: controls})
            recovered = capture(label + 'Recovered', **reset('refined'))
            report['metrics'][label] = dict(change=change(before, endpoint), recovery=change(before, recovered))
            if change(before, endpoint) < .001 or change(before, recovered) > .025:
                raise RuntimeError('Refined material control did not change/recover: ' + label)
        groups = []
        for label, value in [('Off', 0), ('On', defaults['refined'][LED]['scalars']['EmissionStrength']), ('OffRecovered', 0)]:
            frames = [capture('Led' + label + str(index), scalars={LED: {'EmissionStrength': value}}, intensities=[3, 1, 2], sky_intensity=.1) for index in range(3)]
            groups.append([float(frame.mean()) for frame in frames])
            if label in ['Off', 'On']:
                report['captures']['Led' + label] = report['captures']['Led' + label + '1']
        means = list(map(np.mean, groups))
        threshold = max(.001, 3 * max(max(values) - min(values) for values in groups))
        report['metrics']['LED'] = dict(sample_means=groups, signed_change=float(means[1] - means[0]), recovery=float(abs(means[2] - means[0])), threshold=threshold,
                                       protocol='3Off/3On/3OffRecovered, fixed RGB mean, same low-light3/1/2cd sky.1 EV4.2')
        if means[1] - means[0] <= threshold or abs(means[2] - means[0]) > threshold:
            raise RuntimeError('Low-light LED assay failed')
        baseline = capture('StudioRestored', **rig, **reset('refined'))
        for index, path in enumerate(paths):
            needle = b'    return O;' if index == 0 else b'return pow(clamp(Color, 0.001, 0.999), max(Strength, 0.0));'
            replacement = b'    O.TransmittanceColor = 0.001.xxx;\n' + needle if index == 0 else b'return 0.999.xxx;'
            if originals[path].count(needle) != 1:
                raise RuntimeError('Source probe anchor differs')
            source(path, originals[path].replace(needle, replacement))
            edited = capture('SourceEdit' if index == 0 else 'HelperEdit')
            source(path, originals[path])
            recovered = capture('SourceRecovered' if index == 0 else 'HelperRecovered')
            report['metrics']['Source' + str(index)] = dict(change=change(baseline, edited), recovery=change(baseline, recovered))
            if change(baseline, edited) < max(.005, noise * 3) or change(baseline, recovered) > .025:
                raise RuntimeError('Live source edit/recovery failed')
        for index in range(24):
            capture('LightOrbit%02d' % index, phase=index * 15)
        for index in range(12):
            angle = math.radians(-35 + index * 70 / 11)
            capture('CameraOrbit%02d' % index, camera=[54 * math.cos(angle), 54 * math.sin(angle), 17], phase=-30)
        capture('Final', **rig)
        report['passed'] = True
    except Exception:
        failure = traceback.format_exc()
        report['failure'] = failure
    finally:
        for path in paths:
            try:
                if path.read_bytes() != originals[path]:
                    source(path, originals[path])
            except Exception:
                report['cleanup_errors'].append(traceback.format_exc())
        try:
            for variant in defaults:
                capture('Restored-' + variant, variant=variant, hide_lens=False, **reset(variant), **rig)
            report['original_assets_unchanged'] = all(digest(ROOT / path) == pin for path, pin in preserved.items())
            report['restored'] = report['original_assets_unchanged'] and all(path.read_bytes() == data for path, data in originals.items())
            for variant in defaults:
                state = report['captures']['Restored-' + variant]['state']
                for name, record in defaults[variant].items():
                    if any(abs(state['looks'][name]['scalars'][key] - value) > 1e-5 for key, value in record['scalars'].items()):
                        report['restored'] = False
        except Exception:
            report['cleanup_errors'].append(traceback.format_exc())
        report['sources'] = {str(path.relative_to(ROOT)): hashlib.sha256(data).hexdigest() for path, data in originals.items()}
        report['variants'] = identities
        report_path.write_text(json.dumps(report, indent=2))
    if failure or not report['restored'] or report['cleanup_errors']:
        raise RuntimeError(failure or str(report['cleanup_errors']) or 'Source/asset restoration failed')
    print(json.dumps(dict(passed=True, restored=True, captures=len(report['captures']), metrics=report['metrics']), indent=2))


if __name__ == '__main__':
    main()
