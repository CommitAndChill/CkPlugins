"""Serial source/sampling edit proof in existing batch-five masters and MIDs."""
import argparse
import hashlib
import json
import numpy as np
from PIL import Image
from capture_batch5 import LOOKS
from verify_industrial_reload import command, wait_reload, LOG, SHADERS, OUTPUT


def capture(stage, names, initial):
    records = {}
    for name in names:
        filename = f'Batch5-Proof-{stage}-{name}.png'
        debug = 1
        state = command('capture', '--look', name, '--name', filename, '--debug', debug, '--shot')['state']
        if state['pid'] != initial['pid'] or state['library'] != initial['library']:
            raise RuntimeError('Master/MID, parameters or texture bindings changed: ' + name)
        pixels = np.asarray(Image.open(OUTPUT / filename).convert('RGB'), dtype=np.float64) / 255
        yy, xx = np.mgrid[:pixels.shape[0], :pixels.shape[1]]
        height, width = pixels.shape[:2]
        region = (((xx - width * .5) / (width * .11)) ** 2 +
                  ((yy - height * .486) / (height * .194)) ** 2 < 1) & (xx < width * .516) & (yy > height * .306)
        mean = float((pixels[region] @ np.array([.2126, .7152, .0722])).mean())
        if stage == 'baseline' and mean < .002:
            raise RuntimeError('Empty/dark debug specimen: ' + name)
        records[name] = {'image': filename, 'mean_display_rgb': mean, 'state': state}
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shared-only', action='store_true')
    args = parser.parse_args()
    targets = [SHADERS / 'Looks' / (name + '.ush') for name in LOOKS] + [SHADERS / 'LibrarySurface.ush']
    originals = {path: path.read_bytes() for path in targets}
    owned = dict(originals)
    mutations = [(name, path, b'return CkUsf_LibraryInspect(O, DebugView);',
                  b'O.BaseColor *= 0.1; return CkUsf_LibraryInspect(O, DebugView);', [name])
                 for name, path in zip(LOOKS, targets)]
    # The common debug inspection is consumed by all six texture-backed surfaces.
    mutations.append(('shared', targets[-1], b'O.EmissiveColor = Color;', b'O.EmissiveColor = Color * 0.1;', LOOKS))
    if args.shared_only:
        mutations = mutations[-1:]
    report = {'passed': False, 'restored': False, 'capture_route': 'native PIE GameViewportClient Shot', 'entrypoint_edit': 'UV sampling scale multiplied by 1.37; BaseColor multiplied by 0.1', 'debug_channels': {name: 1 for name in LOOKS}, 'stages': {}, 'reloads': []}
    try:
        for name in LOOKS:
            command('select', '--look', name, '--debug', 1)
        initial = command('library_proof_begin')
        report['pid'] = initial['pid']
        report['initial_library'] = initial['library']
        baseline = report['stages']['baseline'] = capture('baseline', LOOKS, initial)
        for label, path, needle, replacement, names in mutations:
            if originals[path].count(needle) != 1 or path.read_bytes() != originals[path]:
                raise RuntimeError('Source anchor/concurrent writer differs: ' + str(path))
            offset = LOG.stat().st_size
            owned[path] = originals[path].replace(needle, replacement)
            if path.parent.name == 'Looks':
                uv_anchor = b'CkUsf_LibraryUV(In.UV, UVScale, UVRotation)'
                if owned[path].count(uv_anchor) != 1:
                    raise RuntimeError('Unique texture-sampling UV anchor required: '+str(path))
                owned[path] = owned[path].replace(uv_anchor, b'CkUsf_LibraryUV(In.UV, UVScale * 1.37, UVRotation)')
            path.write_bytes(owned[path])
            report['reloads'].append(wait_reload(offset))
            changed = report['stages'][label + '-edited'] = capture(label + '-edited', names, initial)
            if path.read_bytes() != owned[path]:
                raise RuntimeError('Concurrent source change preserved: ' + str(path))
            offset = LOG.stat().st_size
            path.write_bytes(originals[path])
            owned[path] = originals[path]
            report['reloads'].append(wait_reload(offset))
            recovered = report['stages'][label + '-recovered'] = capture(label + '-recovered', names, initial)
            for name in names:
                before = baseline[name]['mean_display_rgb']
                if changed[name]['mean_display_rgb'] >= before * .85 or abs(recovered[name]['mean_display_rgb'] - before) >= min(.02, max(.0008, before * .12)):
                    raise RuntimeError('Expected rendered edit/recovery: ' + label + '/' + name)
            print('Proved ' + label, flush=True)
        report['passed'] = True
    finally:
        for path, original in originals.items():
            if path.read_bytes() == owned[path] and path.read_bytes() != original:
                offset = LOG.stat().st_size
                path.write_bytes(original)
                report['reloads'].append(wait_reload(offset))
        report['restored'] = all(path.read_bytes() == original for path, original in originals.items())
        report['passed'] = report['passed'] and report['restored']
        report['source_sha256'] = {str(path): hashlib.sha256(original).hexdigest() for path, original in originals.items()}
        filename = 'Batch5-SharedNativeProof.json' if args.shared_only else 'Batch5-LiveReloadProof.json'
        (OUTPUT / filename).write_text(json.dumps(report, indent=2))
        command('proof_end')
        for name in LOOKS:
            command('select', '--look', name, '--debug', 0)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
