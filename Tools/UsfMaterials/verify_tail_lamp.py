"""Serial real-RHI optical source/control/recovery proof. Never changes graph topology."""
from pathlib import Path
import hashlib
import json
import math
import traceback
import uuid
import sys
import numpy as np
from PIL import Image
from tail_lamp_command import submit
from verify_industrial_reload import wait_reload

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
SHADERS = ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf'
LOG = ROOT / 'Saved/Logs/CkPlugins.log'
LENS = 'OpticalTailLampLens'
LED = 'OpticalTailLampLED'


def main():
    initial = submit('state')['result']
    if len(initial['looks']) != 7 or initial['adaptive'] != 1:
        raise RuntimeError('Construct the dedicated optical scene first')
    paths = [SHADERS / 'Looks/OpticalTailLampLens.ush', SHADERS / 'TailLampOptics.ush']
    originals = {path: path.read_bytes() for path in paths}
    owned = dict(originals)
    report = dict(passed=False, restored=False, initial=initial, captures={}, reloads=[], metrics={}, cleanup_errors=[])
    cached = {}
    if '--resume-controls' in sys.argv:
        checkpoint_path = OUTPUT / 'TailLamp-RenderedProof.json'
        checkpoint_bytes = checkpoint_path.read_bytes()
        checkpoint = json.loads(checkpoint_bytes)
        required = {'Thin', 'Thick', 'Rough', 'Neutral', 'IorOne', 'DistortionNone', 'NormalFlat', 'neutral_pno_matches_refraction_disabled'}
        if (not checkpoint['restored'] or checkpoint['cleanup_errors'] or checkpoint['initial'] != initial
                or not required <= checkpoint['metrics'].keys()
                or 'LED control has no measurable rendered effect' not in checkpoint.get('failure', '')):
            raise RuntimeError('Only the restored same-editor controls checkpoint may resume here')
        if any(checkpoint['sources'].get(str(path.relative_to(ROOT))) != hashlib.sha256(data).hexdigest() for path, data in originals.items()):
            raise RuntimeError('Checkpoint shader source bytes differ')
        for label, record in checkpoint['captures'].items():
            if hashlib.sha256((OUTPUT / record['file']).read_bytes()).hexdigest() != record['sha256']:
                raise RuntimeError('Checkpoint frame differs: ' + label)
            if label not in ['LightsOff', 'LightsOn']:
                cached[label] = record
        report['resumed_controls'] = dict(checkpoint_sha256=hashlib.sha256(checkpoint_bytes).hexdigest(),
                                         same_editor_pid=initial['pid'], carried_capture_labels=list(cached))
    run_id = uuid.uuid4().hex[:12]
    report['run_id'] = run_id

    def capture(label, **values):
        if label in cached:
            record = cached[label]
            report['captures'][label] = record
            return np.asarray(Image.open(OUTPUT / record['file']).convert('RGB'), dtype=np.float32)[150:850, 200:1400] / 255
        filename = 'TailLampProof-' + run_id + '-' + label + '.png'
        path = OUTPUT / filename
        previous_stamp = path.stat().st_mtime_ns if path.exists() else None
        result = submit('capture', name=filename, **values)
        if not path.is_file() or path.stat().st_mtime_ns == previous_stamp:
            raise RuntimeError('Capture did not produce a fresh export: ' + filename)
        state = result['state']
        if state['pid'] != initial['pid']:
            raise RuntimeError('Editor identity changed')
        for name, record in initial['looks'].items():
            if any(state['looks'][name][key] != record[key] for key in ['master', 'mid', 'textures']):
                raise RuntimeError('Loaded material identity or texture binding changed: ' + name)
        lens = state['looks'][LENS]
        if lens['front'] != initial['looks'][LENS]['front'] or not lens['compiled']['valid'] or lens['compiled']['compile_errors'] or lens['compiled']['closure_count'] != 1:
            raise RuntimeError('Native lens topology/resource changed')
        image = Image.open(path).convert('RGB')
        if image.size != (1600, 1000):
            raise RuntimeError('Capture dimensions differ')
        report['captures'][label] = dict(file=filename, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), state=state)
        array = np.asarray(image, dtype=np.float32) / 255
        return array[150:850, 200:1400]

    def write_source(path, data):
        if path.read_bytes() != owned[path]:
            raise RuntimeError('Concurrent source edit preserved: ' + str(path))
        offset = LOG.stat().st_size
        path.write_bytes(data)
        owned[path] = data
        report['reloads'].append(dict(source=str(path.relative_to(ROOT)), completion=wait_reload(offset)))

    def difference(before, after):
        return float(np.abs(before - after).mean())

    failure = None
    try:
        baseline = capture('Close', camera=[49, -25, 19], phase=-30)
        repeated = capture('CloseRepeated', phase=-30)
        noise = difference(baseline, repeated)
        if float(baseline.std()) < .025 or float(baseline.mean()) < .01:
            raise RuntimeError('Unusable dark/flat optical capture')
        report['metrics']['capture_noise'] = noise
        capture('Front', camera=[58, 0, 10], phase=-30)
        capture('Opposite', camera=[49, 25, 19], phase=-30)
        capture('Macro', camera=[34, -16, 13], phase=-30)
        baseline = capture('CloseReset', camera=[49, -25, 19], phase=-30)
        defaults = initial['looks'][LENS]['scalars']
        # Predeclared directional transmission protocol: three captures per state,
        # a fixed RGB mean and within-state temporal range; no channel selection.
        for label, thickness, direction in [('Thin', .06, 1), ('Thick', .65, -1)]:
            groups = []
            for state_name, value in [('Baseline', defaults['ThicknessCm']), ('Endpoint', thickness), ('Recovered', defaults['ThicknessCm'])]:
                pixels = [capture(label + state_name + str(index), scalars={LENS: {'ThicknessCm': value}}, phase=-30) for index in range(3)]
                groups.append(pixels)
            means = [[float(frame.mean()) for frame in frames] for frames in groups]
            state_means = [float(np.mean(values)) for values in means]
            temporal_range = max(max(values) - min(values) for values in means)
            threshold = max(.001, temporal_range * 3)
            signed_change = state_means[1] - state_means[0]
            recovery = abs(state_means[2] - state_means[0])
            report['metrics'][label] = dict(protocol='three baseline / endpoint / recovered captures; fixed display-RGB mean',
                sample_means=means, channel_means=[[[float(frame[:, :, channel].mean()) for channel in range(3)] for frame in frames] for frames in groups],
                temporal_range=temporal_range, threshold=threshold, signed_change=signed_change, recovery=recovery)
            report['captures'][label] = report['captures'][label + 'Endpoint1']
            if direction * signed_change <= threshold or recovery > threshold:
                raise RuntimeError('Directional optical thickness response/recovery failed: ' + label)
        for label, control in [('Rough', {'RoughnessScale': 0, 'RoughnessBias': .3}),
                               ('Neutral', {'AbsorptionStrength': .001}),
                               ('IorOne', {'Ior': 1.0}), ('DistortionNone', {'DistortionStrength': 0}),
                               ('NormalFlat', {'NormalStrength': 0})]:
            lighting = {'source_radii': [1, 30, 1]} if label == 'IorOne' else {}
            reference = capture(label + 'Baseline', phase=-30, **lighting)
            edited = capture(label, scalars={LENS: control}, phase=-30)
            recovered = capture(label + 'Recovered', scalars={LENS: {key: defaults[key] for key in control}}, phase=-30)
            change, recovery = difference(reference, edited), difference(reference, recovered)
            report['metrics'][label] = dict(change=change, recovery=recovery)
            if change < max(.001, noise * 3) or recovery > max(.025, noise * 3):
                raise RuntimeError('Optical control/recovery failed: ' + label)
            if label == 'IorOne':
                report['metrics'][label]['lighting'] = 'Matched broad fill source radius30cm makes dielectric reflection observable; main rig restored afterward.'
                capture('IorRigRestored', source_radii=[item['source_radius'] for item in initial['rig']['lights']], phase=-30)
        refraction_off = capture('RefractionDisabledDiagnostic', refraction=False, phase=-30)
        neutral_pno = capture('PnoNeutralEndpoint', refraction=True, scalars={LENS: {'DistortionStrength': 0}}, phase=-30)
        report['metrics']['neutral_pno_matches_refraction_disabled'] = difference(refraction_off, neutral_pno)
        if report['metrics']['neutral_pno_matches_refraction_disabled'] > max(.01, noise * 3):
            raise RuntimeError('Neutral native PNO does not match distortion-off endpoint')
        capture('PnoRestored', scalars={LENS: {'DistortionStrength': defaults['DistortionStrength']}}, phase=-30)
        capture('Interior', hide_lens=True, phase=-30)
        capture('LensRestored', hide_lens=False, phase=-30)
        led_default = initial['looks'][LED]['scalars']['EmissionStrength']
        led_groups = []
        for state_name, value in [('Off', 0), ('On', led_default), ('OffRecovered', 0)]:
            led_groups.append([capture('LedAssay' + state_name + str(index), scalars={LED: {'EmissionStrength': value}},
                                      intensities=[3, 1, 2], sky_intensity=.1, exposure=4.2, phase=-30) for index in range(3)])
        led_means = [[float(frame.mean()) for frame in frames] for frames in led_groups]
        led_levels = [float(np.mean(values)) for values in led_means]
        led_noise = max(max(values) - min(values) for values in led_means)
        led_threshold = max(.001, led_noise * 3)
        report['metrics']['LED'] = dict(protocol='Separate low-light assay:3Off/3On/3OffRecovery;fixed RGB mean;3/1/2cd,sky.1,EV4.2',
                                      means=led_means, temporal_range=led_noise, threshold=led_threshold,
                                      signed_change=led_levels[1] - led_levels[0], recovery=abs(led_levels[2] - led_levels[0]))
        report['captures']['LightsOff'] = report['captures']['LedAssayOff1']
        report['captures']['LightsOn'] = report['captures']['LedAssayOn1']
        if led_levels[1] - led_levels[0] <= led_threshold or abs(led_levels[2] - led_levels[0]) > led_threshold:
            raise RuntimeError('Low-light LED emission response/recovery failed')
        baseline = capture('StudioRigRecovered', scalars={LED: {'EmissionStrength': led_default}},
                           intensities=[item['intensity'] for item in initial['rig']['lights']],
                           source_radii=[item['source_radius'] for item in initial['rig']['lights']],
                           sky_intensity=initial['rig']['sky_intensity'], exposure=initial['rig']['exposure'], phase=-30)
        for index, path in enumerate(paths):
            needle = b'    return O;' if index == 0 else b'return pow(clamp(Color, 0.001, 0.999), max(Strength, 0.0));'
            replacement = b'    O.TransmittanceColor = 0.001.xxx;\n' + needle if index == 0 else b'return 0.999.xxx;'
            if originals[path].count(needle) != 1:
                raise RuntimeError('Source probe anchor differs: ' + str(path))
            write_source(path, originals[path].replace(needle, replacement))
            edited = capture('SourceEdit' + str(index), phase=-30)
            write_source(path, originals[path])
            recovered = capture('SourceRecovery' + str(index), phase=-30)
            change, recovery = difference(baseline, edited), difference(baseline, recovered)
            report['metrics']['Source' + str(index)] = dict(change=change, recovery=recovery)
            if change < max(.005, noise * 3) or recovery > max(.025, noise * 3):
                raise RuntimeError('Automatic source edit/recovery failed')
        for index in range(24):
            capture('LightOrbit%02d' % index, phase=index * 15)
        for index in range(12):
            angle = math.radians(-35 + index * 70 / 11)
            capture('CameraOrbit%02d' % index, camera=[54 * math.cos(angle), 54 * math.sin(angle), 17], phase=-30)
        capture('Final', camera=[49, -25, 19], phase=-30)
        report['passed'] = True
    except Exception:
        failure = traceback.format_exc()
        report['failure'] = failure
    finally:
        for path in paths:
            try:
                if path.read_bytes() != originals[path]:
                    write_source(path, originals[path])
            except Exception:
                report['cleanup_errors'].append(traceback.format_exc())
        try:
            final = submit('capture', name='TailLampProof-' + run_id + '-Restored.png', camera=[49, -25, 19], phase=-30,
                           scalars={name: record['scalars'] for name, record in initial['looks'].items()},
                           vectors={name: record['vectors'] for name, record in initial['looks'].items()}, hide_lens=False, refraction=True,
                           intensities=[item['intensity'] for item in initial['rig']['lights']],
                           source_radii=[item['source_radius'] for item in initial['rig']['lights']],
                           sky_intensity=initial['rig']['sky_intensity'], exposure=initial['rig']['exposure'])['state']
            report['final'] = final
            report['restored'] = all(path.read_bytes() == originals[path] for path in paths) and all(
                all(abs(final['looks'][name]['scalars'][key] - value) < 1e-5 for key, value in record['scalars'].items())
                and final['looks'][name]['textures'] == record['textures'] and final['looks'][name]['mid'] == record['mid']
                for name, record in initial['looks'].items())
            report['restored'] = report['restored'] and final['rig'] == initial['rig']
        except Exception:
            report['cleanup_errors'].append(traceback.format_exc())
        report['sources'] = {str(path.relative_to(ROOT)): hashlib.sha256(data).hexdigest() for path, data in originals.items()}
        (OUTPUT / 'TailLamp-RenderedProof.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if failure or not report['restored'] or report['cleanup_errors']:
        raise RuntimeError(failure or str(report['cleanup_errors']) or 'Restoration failed')
    print(json.dumps(dict(passed=True, restored=True, captures=len(report['captures']), metrics=report['metrics']), indent=2))


if __name__ == '__main__':
    main()
