"""Real-RHI amber geometry, optical controls and source reload/recovery proof."""
from pathlib import Path
import hashlib
import json
import math
import traceback
import uuid
import numpy as np
from PIL import Image
from amber_specimen_command import submit
from verify_industrial_reload import wait_reload

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
SHADERS = ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = OUTPUT / 'Amber-Proof.json'
    if destination.exists():
        raise RuntimeError('Preserve the existing amber proof before another run')
    initial = submit('state')['result']
    if initial['adaptive'] != 1 or set(initial['looks']) != {'Body', 'Botanical', 'Seed', 'Stem', 'Backing'}:
        raise RuntimeError('Create the owned amber studio before proof')
    paths = [SHADERS / 'Looks/AmberSpecimen.ush', SHADERS / 'TailLampOptics.ush', SHADERS / 'Looks/AmberInclusion.ush']
    originals = {path: path.read_bytes() for path in paths}
    owned = dict(originals)
    old_proof = json.loads((OUTPUT / 'TailLamp-RefinedProof.json').read_text())
    preserved = dict(old_proof['preserved_originals'])
    for record in [old_proof, json.loads((OUTPUT / 'TailLamp-RenderedProof.json').read_text())]:
        preserved.update(record['sources'])
    for folder, pattern in [('Plugins/CkFoundation/Content/CkUsf/GeneratedLooks', '*OpticalTailLampRefined*.uasset'),
                            ('Plugins/CkFoundation/Content/CkUsf/Looks/Optical', '*OpticalTailLampRefined*.uasset'),
                            ('Plugins/CkFoundation/Content/CkUsf/Textures/Optical/Refined', '*.uasset')]:
        preserved.update({str(path.relative_to(ROOT)): sha(path) for path in (ROOT / folder).glob(pattern)})
    if any(sha(ROOT / path) != pin for path, pin in preserved.items()):
        raise RuntimeError('Prior optical assets/sources differ before amber proof')
    run_id = uuid.uuid4().hex[:12]
    report = dict(passed=False, restored=False, captures={}, metrics={}, reloads=[], cleanup_errors=[],
                  initial=initial, run_id=run_id, preserved_originals=preserved)
    defaults = dict(scalars={role: data['scalars'] for role, data in initial['looks'].items()},
                    vectors={role: data['vectors'] for role, data in initial['looks'].items()})
    rig = dict(camera=[29, -10, 12], phase=-38, exposure=4.8, source_radii=[.8, 1.2, 1], intensities=[18, 7, 14], sky=1.4)
    visible = {role: True for role in initial['looks']}

    def capture(label, **values):
        path = OUTPUT / ('AmberProof-' + run_id + '-' + label + '.png')
        if path.exists():
            raise RuntimeError('Preserve existing amber capture')
        data = submit('capture', name=path.name, **values)
        state = data['state']
        if state['pid'] != initial['pid']:
            raise RuntimeError('Owned editor changed')
        for role, record in initial['looks'].items():
            if any(state['looks'][role][key] != record[key] for key in ['master', 'mid', 'textures']):
                raise RuntimeError('Amber identity/texture binding changed')
        body = state['looks']['Body']
        if body['front'] != initial['looks']['Body']['front'] or not body['compiled']['valid'] or body['compiled']['compile_errors'] or body['compiled']['closure_count'] != 1:
            raise RuntimeError('Amber native topology or shader resource differs')
        image = Image.open(path).convert('RGB')
        if image.size != (1600, 1200):
            raise RuntimeError('Amber image dimensions differ')
        report['captures'][label] = dict(file=path.name, sha256=sha(path), state=state)
        return np.asarray(image, dtype=np.float32)[170:1030, 240:1360] / 255

    def difference(a, b):
        return float(np.abs(a - b).mean())

    def source(path, data):
        if path.read_bytes() != owned[path]:
            raise RuntimeError('Concurrent optical source edit preserved')
        offset = (ROOT / 'Saved/Logs/CkPlugins.log').stat().st_size
        path.write_bytes(data)
        owned[path] = data
        report['reloads'].append(dict(source=str(path.relative_to(ROOT)), completion=wait_reload(offset)))

    failure = None
    try:
        capture('Settling0', **rig, **defaults, visible=visible)
        baseline = capture('Settling1', **rig)
        hero = capture('Hero', **rig)
        noise = difference(baseline, hero)
        report['metrics']['noise'] = noise
        if noise > .005 or float(hero.std()) < .025:
            raise RuntimeError('Amber starting image is unstable/flat')
        capture('Front', camera=[31, 0, 8])
        capture('Left', camera=[28, -13, 10])
        capture('Right', camera=[28, 13, 10])
        capture('Macro', camera=[22, -6, 8.5])
        capture('Interior', **rig, visible={'Body': False})
        capture('NoInclusions', visible={'Body': True, 'Botanical': False, 'Seed': False, 'Stem': False})
        capture('AssemblyRestored', **rig, visible=visible)
        threshold = max(.001, noise * 3)
        for label, control, direction in [('Thin', {'ThicknessCm': .18, 'EdgeThicknessCm': .18}, 1),
                                           ('Thick', {'ThicknessCm': 4.5, 'EdgeThicknessCm': 4.5}, -1),
                                           ('Rough', {'RoughnessScale': 0, 'RoughnessBias': .38}, 0),
                                           ('Clear', {'AbsorptionStrength': .001}, 0)]:
            before = capture(label + 'Baseline')
            capture(label + 'Settling', scalars={'Body': control})
            endpoint = capture(label, scalars={'Body': control})
            capture(label + 'RecoverySettling', **defaults)
            recovered = capture(label + 'Recovered', **defaults)
            change = difference(before, endpoint)
            signed = float(endpoint.mean() - before.mean())
            recovery = difference(before, recovered)
            report['metrics'][label] = dict(change=change, signed_change=signed, recovery=recovery, threshold=threshold)
            if (direction and direction * signed <= threshold) or (not direction and change <= threshold) or recovery > max(.02, noise * 4):
                raise RuntimeError('Amber optical control/recovery failed: ' + label)
        baseline = capture('SourceBaseline')
        for index, (path, label) in enumerate(zip(paths, ['Source', 'Helper', 'Inclusion'])):
            needle = b'    return O;' if index != 1 else b'return pow(clamp(Color, 0.001, 0.999), max(Strength, 0.0));'
            replacement = (b'    O.TransmittanceColor = 0.001.xxx;\n' + needle) if index == 0 else b'return 0.999.xxx;' if index == 1 else b'    O.BaseColor = 0.9.xxx;\n' + needle
            if originals[path].count(needle) != 1:
                raise RuntimeError('Amber source probe anchor differs')
            source(path, originals[path].replace(needle, replacement))
            capture(label + 'EditSettling')
            edited = capture(label + 'Edit')
            source(path, originals[path])
            capture(label + 'RecoverySettling')
            recovered = capture(label + 'Recovered')
            change, recovery = difference(baseline, edited), difference(baseline, recovered)
            report['metrics'][label] = dict(change=change, recovery=recovery, recovery_bound=max(.02, noise * 4))
            if change < max(.005, noise * 3) or recovery > max(.02, noise * 4):
                raise RuntimeError('Amber .ush edit/recovery failed: ' + label)
        for index in range(24):
            capture('LightOrbit%02d' % index, phase=index * 15)
        for index in range(12):
            angle = math.radians(-25 + index * 50 / 11)
            capture('CameraOrbit%02d' % index, camera=[31 * math.cos(angle), 31 * math.sin(angle), 10], phase=-38)
        capture('FinalSettling', **rig, **defaults, visible=visible)
        capture('Final', **rig, **defaults, visible=visible)
        report['passed'] = True
    except Exception:
        failure = traceback.format_exc()
        report['failure'] = failure
    finally:
        for path, data in originals.items():
            try:
                if path.read_bytes() != data:
                    source(path, data)
            except Exception:
                report['cleanup_errors'].append(traceback.format_exc())
        try:
            capture('Restored', **rig, **defaults, visible=visible)
            restored = report['captures']['Restored']['state']
            report['original_files_unchanged'] = all(sha(ROOT / path) == pin for path, pin in preserved.items())
            report['restored'] = report['original_files_unchanged'] and all(path.read_bytes() == data for path, data in originals.items()) and all(
                restored['looks'][role]['scalars'] == record['scalars'] and restored['looks'][role]['vectors'] == record['vectors']
                for role, record in initial['looks'].items()) and restored['visible'] == visible
        except Exception:
            report['cleanup_errors'].append(traceback.format_exc())
        report['sources'] = {str(path.relative_to(ROOT)): hashlib.sha256(data).hexdigest() for path, data in originals.items()}
        destination.write_text(json.dumps(report, indent=2))
    if failure or not report['restored'] or report['cleanup_errors']:
        raise RuntimeError(failure or str(report['cleanup_errors']) or 'Amber restoration failed')
    print(json.dumps(dict(passed=True, restored=True, captures=len(report['captures']), metrics=report['metrics']), indent=2))


if __name__ == '__main__':
    main()
