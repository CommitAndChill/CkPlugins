"""Offscreen production-pane proof: radius control and transitive .ush edit/recovery."""
import hashlib
import json
import numpy as np
from PIL import Image
from verify_industrial_reload import command, wait_reload, LOG, SHADERS, OUTPUT

LOOK = 'LibraryFrostedGlass'

def capture(label, distance=280, **values):
    arguments = sum((['--scalar', key + '=' + str(value)] for key, value in values.items()), [])
    filename = 'Batch3-Frost-' + label + '.png'
    record = command('capture', '--look', LOOK, '--name', filename, '--shot',
        '--distance', distance, '--height', 0, '--debug', 0,
        '--scalar', 'SpecularLevel=0', '--scalar', 'NormalStrength=0',
        '--scalar', 'TransmissionAmount=1', '--scalar', 'GlassCoverage=1',
        '--vector', 'TintColor=1,1,1,1', *arguments)
    return {'image': filename, 'state': record['state']}

def pixels(record):
    return np.asarray(Image.open(OUTPUT / record['image']).convert('RGB'), dtype=float) / 255

def main():
    original_state = command('state')
    values = original_state['library'][LOOK]['values']
    tint = original_state['library'][LOOK]['colors']['TintColor']
    path = SHADERS / 'SurfaceSceneColor.ush'
    original = path.read_bytes()
    owned = original
    report = {'passed': False, 'restored': False, 'stages': {}, 'reloads': [],
              'source_sha256': {str(path): hashlib.sha256(original).hexdigest(),
                 str(SHADERS/'Looks/LibraryFrostedGlass.ush'): hashlib.sha256((SHADERS/'Looks/LibraryFrostedGlass.ush').read_bytes()).hexdigest()},
              'capture_route': 'native PIE GameViewportClient Shot'}
    quality = False
    try:
        command('glass_pane_begin', '--look', LOOK)
        command('library_proof_begin')
        for preview in [False, True]:
            label = 'TAA' if preview else 'Native'
            if preview:
                command('preview_quality'); quality = True
            for view, distance in [('Close', 280), ('Gameplay', 480)]:
                for mode, radius in [('Control', 0), ('Blurred', 8)]:
                    key = label + '-' + view + '-' + mode
                    report['stages'][key] = capture(key, distance, BlurRadius=radius)
            if preview:
                command('restore_quality'); quality = False
        bypass = report['stages']['Native-Close-Bypass'] = capture('Native-Close-Bypass',
            BlurRadius=0, GlassCoverage=0, TransmissionAmount=0)
        report['pane_metrics'] = {}
        for quality_name in ['Native', 'TAA']:
            control = pixels(report['stages'][quality_name+'-Close-Control'])
            blurred = pixels(report['stages'][quality_name+'-Close-Blurred'])
            covered = np.s_[140:375, 265:345]
            uncovered = np.s_[140:375, 420:500]
            luminance = np.array([.2126, .7152, .0722])
            sharp_gradient = float(abs(np.diff(control[covered] @ luminance, axis=1)).mean())
            blur_gradient = float(abs(np.diff(blurred[covered] @ luminance, axis=1)).mean())
            ratio = blur_gradient / max(sharp_gradient, 1e-6)
            outside_change = float(abs(control[uncovered]-blurred[uncovered]).mean())
            report['pane_metrics'][quality_name] = {'covered_horizontal_gradient_ratio': ratio,
                'uncovered_mean_rgb_change': outside_change}
            if ratio >= .6 or outside_change >= .015:
                raise RuntimeError('Blur must suppress tile detail while uncovered reference stays stable')
        zero = pixels(report['stages']['Native-Close-Control'])
        no_pane = pixels(bypass)
        zero_error = float(abs(zero[covered]-no_pane[covered]).mean())
        report['zero_radius_vs_bypass_mean_rgb'] = zero_error
        if zero_error >= .015:
            raise RuntimeError('Zero-radius scene-copy equivalence differs: '+str(zero_error))
        # A transitive helper edit must change the existing pane without recreating its MID/master.
        baseline = report['stages']['Helper-Baseline'] = capture('Helper-Baseline', BlurRadius=8)
        needle = b'float Radius = clamp(RadiusPixels, 0.0, 12.0);'
        if original.count(needle) != 1 or path.read_bytes() != original:
            raise RuntimeError('Helper source anchor/concurrent writer differs')
        owned = original.replace(needle, b'float Radius = 0.0; // live edit proof')
        offset = LOG.stat().st_size; path.write_bytes(owned)
        report['reloads'].append(wait_reload(offset))
        edited = report['stages']['Helper-Edited'] = capture('Helper-Edited', BlurRadius=8)
        if path.read_bytes() != owned:
            raise RuntimeError('Concurrent helper edit preserved')
        offset = LOG.stat().st_size; path.write_bytes(original); owned = original
        report['reloads'].append(wait_reload(offset))
        recovered = report['stages']['Helper-Recovered'] = capture('Helper-Recovered', BlurRadius=8)
        before, changed, restored = map(pixels, [baseline, edited, recovered])
        h,w = before.shape[:2]
        roi = np.s_[int(h*.25):int(h*.68), int(w*.35):int(w*.45)]
        change = float(np.abs(before[roi]-changed[roi]).mean())
        recovery = float(np.abs(before[roi]-restored[roi]).mean())
        report['helper_difference'] = {'change_mean_rgb': change, 'recovery_mean_rgb': recovery}
        for record in report['stages'].values():
            current = record['state']
            if current['pid'] != original_state['pid'] or not current['library'][LOOK]['same_mid'] or not current['library'][LOOK]['same_master']:
                raise RuntimeError('Existing frost MID/master changed')
        if change < .002 or recovery > .015:
            raise RuntimeError('Expected visible helper edit and recovery: ' + str(report['helper_difference']))
        report['passed'] = True
    finally:
        if path.read_bytes() == owned and owned != original:
            offset = LOG.stat().st_size; path.write_bytes(original); report['reloads'].append(wait_reload(offset))
        if quality: command('restore_quality')
        command('glass_pane_end', '--look', LOOK)
        command('proof_end')
        args = sum((['--scalar', key+'='+str(value)] for key,value in values.items()), [])
        command('select', '--look', LOOK, '--vector', 'TintColor='+','.join(map(str,tint)), *args)
        final = command('state')
        report['restored'] = path.read_bytes() == original and final['library'] == original_state['library']
        report['passed'] = report['passed'] and report['restored']
        (OUTPUT/'Batch3-FrostProof.json').write_text(json.dumps(report,indent=2))
    if not report['passed']: raise SystemExit(1)

if __name__ == '__main__': main()
