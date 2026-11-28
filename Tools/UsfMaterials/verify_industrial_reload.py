"""Real-renderer, same-instance source/recovery proof against the open studio session.

Run serially with no other shader-source writer. Both shader files are restored
byte-for-byte on every exit; outputs stay under Saved/UsfMaterialGallery.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
LOG = ROOT / 'Saved/Logs/CkPlugins.log'
COMMAND = ROOT / 'Tools/UsfMaterials/studio_command.py'
SHADERS = ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf'


def command(action, *args):
    completed = subprocess.run([sys.executable, str(COMMAND), action, *map(str, args)],
                               capture_output=True, text=True, cwd=ROOT)
    if completed.returncode:
        raise RuntimeError(completed.stdout + completed.stderr)
    return json.loads(completed.stdout)['result']


def wait_reload(offset):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        with LOG.open('rb') as stream:
            stream.seek(offset)
            text = stream.read().decode('utf-8', errors='replace')
        if 'CkUsf reload batch rejected:' in text:
            rejection = [line for line in text.splitlines() if 'CkUsf reload batch rejected:' in line][-1]
            raise RuntimeError(rejection)
        if 'CkUsf reload complete:' in text:
            completion = [line for line in text.splitlines() if 'CkUsf reload complete:' in line][-1]
            if '[0] failed' not in completion:
                raise RuntimeError(completion)
            return completion
        if 'Failed to compile Material' in text or 'error X' in text:
            raise RuntimeError(text[-3000:])
        time.sleep(0.1)
    raise RuntimeError('Source watcher did not report completion; inspect the existing editor')


def capture(stage):
    records = []
    for preset in range(4):
        name = f'Industrial-Proof-{stage}-{preset}.png'
        result = command('capture', '--preset', preset, '--name', name, '--debug', 0)
        state = result['state']
        assert all(item['same_mid'] and item['same_master'] for item in state['industrial']), state
        pixels = np.asarray(Image.open(OUTPUT / name).convert('RGB'), dtype=np.float64) / 255
        yy, xx = np.mgrid[:pixels.shape[0], :pixels.shape[1]]
        region = ((xx - 640) ** 2 + (yy - 350) ** 2 < 140 ** 2) & (xx < 660) & (yy > 220)
        mean = float((pixels[region] @ np.array([0.2126, 0.7152, 0.0722])).mean())
        if stage == 'baseline':
            deviation = float((pixels[region] @ np.array([0.2126, 0.7152, 0.0722])).std())
            assert deviation > 0.025 and mean < 0.6, ('Invalid specimen baseline', preset, mean, deviation)
        records.append({'image': name, 'mean_display_rgb': mean, 'state': state})
    return records


def main():
    targets = [SHADERS / 'Looks/IndustrialPaint.ush', SHADERS / 'IndustrialSurface.ush']
    originals = {path: path.read_bytes() for path in targets}
    owned_bytes = dict(originals)
    mutations = [
        (targets[0], b'O.BaseColor = Surface.rgb;', b'O.BaseColor = Surface.rgb * 0.15;'),
        (targets[1],
         b'return Paint * W.Paint + Primer * W.Primer + Steel * W.Steel + Rust * W.Rust + Dust * W.Dust;',
         b'return (Paint * W.Paint + Primer * W.Primer + Steel * W.Steel + Rust * W.Rust + Dust * W.Dust) * float4(0.15, 0.15, 0.15, 1.0);')]
    report = {'proof': 'same editor, same loaded master and four MIDs; automatic .ush source watcher',
              'stages': {}, 'reloads': [], 'restored': False}
    try:
        initial = command('proof_begin')
        report['pid'] = initial['pid']
        report['stages']['baseline'] = capture('baseline')
        for index, (path, needle, replacement) in enumerate(mutations):
            if originals[path].count(needle) != 1:
                raise RuntimeError('Live probe anchor must match exactly once: ' + str(path))
            if path.read_bytes() != originals[path]:
                raise RuntimeError('Concurrent source change preserved: ' + str(path))
            offset = LOG.stat().st_size
            owned_bytes[path] = originals[path].replace(needle, replacement)
            path.write_bytes(owned_bytes[path])
            report['reloads'].append(wait_reload(offset))
            report['stages'][f'edit{index}'] = capture(f'edit{index}')
            offset = LOG.stat().st_size
            if path.read_bytes() != owned_bytes[path]:
                raise RuntimeError('Concurrent source change preserved: ' + str(path))
            path.write_bytes(originals[path])
            owned_bytes[path] = originals[path]
            report['reloads'].append(wait_reload(offset))
            report['stages'][f'restore{index}'] = capture(f'restore{index}')
        baseline = report['stages']['baseline']
        for index in range(2):
            for preset in range(4):
                before = baseline[preset]['mean_display_rgb']
                edited = report['stages'][f'edit{index}'][preset]['mean_display_rgb']
                restored = report['stages'][f'restore{index}'][preset]['mean_display_rgb']
                assert edited < before * 0.85, (index, preset, before, edited)
                assert abs(restored - before) < 0.02, (index, preset, before, restored)
                for stage in (f'edit{index}', f'restore{index}'):
                    current = report['stages'][stage][preset]['state']
                    assert current['pid'] == initial['pid']
                    assert current['industrial'] == initial['industrial'], (stage, current, initial)
        report['passed'] = True
    finally:
        for path, original in originals.items():
            if path.read_bytes() != original:
                if path.read_bytes() != owned_bytes[path]:
                    report.setdefault('concurrent_changes_preserved', []).append(str(path))
                    continue
                offset = LOG.stat().st_size
                path.write_bytes(original)
                report['reloads'].append(wait_reload(offset))
        report['restored'] = all(path.read_bytes() == original for path, original in originals.items())
        if not report['restored']:
            report['passed'] = False
        report['source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(original).hexdigest()
                                   for path, original in originals.items()}
        (OUTPUT / 'Industrial-LiveReloadProof.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'passed': report.get('passed', False), 'pid': report['pid'],
                      'restored': report['restored'], 'images': sum(map(len, report['stages'].values()))}))
    if not report.get('passed', False):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
