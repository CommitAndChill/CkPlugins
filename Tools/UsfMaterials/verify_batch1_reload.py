"""Serial same-instance proof for all six texture-backed looks and their shared sampling helper.

Debug base-color captures isolate source response from coat/specular highlights.
Artistic acceptance uses separate lit captures. Run with no concurrent shader writer.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image
from verify_industrial_reload import command, wait_reload, ROOT, OUTPUT, LOG, SHADERS

LOOKS = ['LibrarySilk', 'LibraryLeather', 'LibraryTile', 'LibraryOak', 'LibraryAluminum', 'LibraryPlastic']


def capture(stage, names, initial):
    records = {}
    for name in names:
        filename = f'Batch1-Proof-{stage}-{name}.png'
        result = command('capture', '--look', name, '--name', filename, '--debug', 1)
        state = result['state']
        if state['pid'] != initial['pid'] or state['library'] != initial['library']:
            raise RuntimeError('Library objects or overrides changed during source proof')
        pixels = np.asarray(Image.open(OUTPUT / filename).convert('RGB'), dtype=np.float64) / 255
        yy, xx = np.mgrid[:pixels.shape[0], :pixels.shape[1]]
        region = ((xx - 640) ** 2 + (yy - 350) ** 2 < 140 ** 2) & (xx < 660) & (yy > 220)
        values = pixels[region] @ np.array([0.2126, 0.7152, 0.0722])
        mean = float(values.mean())
        # Clean leather/polymer can have nearly uniform albedo; their detail lives in normal/roughness.
        # Reject empty frames here, then require the actual source mutation/recovery to change specimen pixels.
        if stage == 'baseline' and (mean < 0.01 or float(pixels.std()) < 0.03):
            raise RuntimeError('Invalid specimen baseline: ' + name)
        records[name] = {'image': filename, 'mean_display_rgb': mean, 'surface_color_deviation': float(values.std()), 'state': state}
    return records


def main():
    targets = [SHADERS / 'Looks' / (name + '.ush') for name in LOOKS] + [SHADERS / 'LibrarySurface.ush']
    originals = {path: path.read_bytes() for path in targets}
    owned = dict(originals)
    mutations = []
    for name, path in zip(LOOKS, targets):
        mutations.append((name, path, b'return CkUsf_LibraryInspect(O, DebugView);',
                          b'O.BaseColor *= 0.1; return CkUsf_LibraryInspect(O, DebugView);', [name]))
    mutations.append(('shared', targets[-1], b'O.BaseColor = saturate(Color.rgb * max(Tint, 0.0));',
                      b'O.BaseColor = saturate(Color.rgb * max(Tint, 0.0)) * 0.1;', LOOKS))
    report = {'proof': 'same editor, six masters and six MIDs; automatic source watcher',
              'stages': {}, 'reloads': [], 'restored': False, 'passed': False}
    try:
        for name in LOOKS:
            command('select', '--look', name, '--debug', 1)
        initial = command('library_proof_begin')
        report['pid'] = initial['pid']
        baseline = report['stages']['baseline'] = capture('baseline', LOOKS, initial)
        for label, path, needle, replacement, names in mutations:
            if originals[path].count(needle) != 1 or path.read_bytes() != originals[path]:
                raise RuntimeError('Probe anchor or concurrent source differs: ' + str(path))
            offset = LOG.stat().st_size
            owned[path] = originals[path].replace(needle, replacement)
            path.write_bytes(owned[path])
            report['reloads'].append(wait_reload(offset))
            edited = report['stages'][label + '-edited'] = capture(label + '-edited', names, initial)
            if path.read_bytes() != owned[path]:
                raise RuntimeError('Concurrent source change preserved: ' + str(path))
            offset = LOG.stat().st_size
            path.write_bytes(originals[path])
            owned[path] = originals[path]
            report['reloads'].append(wait_reload(offset))
            restored = report['stages'][label + '-restored'] = capture(label + '-restored', names, initial)
            for name in names:
                before = baseline[name]['mean_display_rgb']
                if edited[name]['mean_display_rgb'] >= before * 0.85:
                    raise RuntimeError('Expected visible source response: ' + label + '/' + name)
                if abs(restored[name]['mean_display_rgb'] - before) >= 0.02:
                    raise RuntimeError('Expected pixel recovery: ' + label + '/' + name)
        report['passed'] = True
    finally:
        for path, original in originals.items():
            current = path.read_bytes()
            if current != original:
                if current != owned[path]:
                    report.setdefault('concurrent_changes_preserved', []).append(str(path))
                    continue
                offset = LOG.stat().st_size
                path.write_bytes(original)
                report['reloads'].append(wait_reload(offset))
        report['restored'] = all(path.read_bytes() == original for path, original in originals.items())
        report['passed'] = report['passed'] and report['restored']
        report['source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(original).hexdigest() for path, original in originals.items()}
        (OUTPUT / 'Batch1-LiveReloadProof.json').write_text(json.dumps(report, indent=2))
        command('proof_end')
        for name in LOOKS:
            command('select', '--look', name, '--debug', 0)
    print(json.dumps({'passed': report['passed'], 'restored': report['restored'],
                      'pid': report.get('pid'), 'images': sum(map(len, report['stages'].values()))}))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
