"""Independently reconcile source, live-render and focused-gate evidence for batch two."""
import hashlib
import json
from pathlib import Path
import re
from capture_batch2 import LOOKS

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    proof = read('Batch2-LiveReloadProof.json')
    controls = read('Batch2-ControlProof.json')
    if not (proof['passed'] and proof['restored'] and controls['passed'] and controls['restored']):
        raise RuntimeError('Live source/control proof is incomplete')
    for path, expected in proof['source_sha256'].items():
        if digest(Path(path)) != expected:
            raise RuntimeError('Shader restoration hash differs: ' + path)
    protected = read('Batch2-OpeningHashes.json')
    for path, expected in protected.items():
        if digest(ROOT / path) != expected:
            raise RuntimeError('Protected asset/source changed: ' + path)
    source = ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch2Textures'
    manifest = json.loads((source / 'Manifest.json').read_text())
    selected = {}
    for record in manifest['materials'].values():
        for info in record['maps'].values():
            path = source / info['path']
            if digest(path) != info['sha256']:
                raise RuntimeError('Recorded source hash differs: ' + str(path))
            selected[str(path.relative_to(ROOT))] = info['sha256']
    state = read('Batch2-FinalLiveState.json')['result']
    if state['preview_quality'] or state['diagnostic_light'] is not None:
        raise RuntimeError('Temporary renderer/light state remains active')
    if state['render_cvars']['r.AntiAliasingMethod'] != 0 or state['render_cvars']['r.ScreenPercentage'] != 87:
        raise RuntimeError('Preview renderer settings were not restored')
    if any(item['values']['DebugView'] != 0 for item in state['library'].values()):
        raise RuntimeError('A diagnostic material view remains active')
    gate = read('Batch2-Gate.exit.json')
    log = (ROOT / gate['log']).read_text(errors='replace')
    if gate['exit_code'] != 0 or not re.search(r'Total: 1\s+Passed: 1\s+Failed: 0\s+Skipped: 0\s+Contaminated: 0', log):
        raise RuntimeError('Focused gate did not pass exactly 1/1')
    if re.search(r'Assertion failed|Fatal error|Ensure condition failed|Script Compile Error|Failed to compile Material', log):
        raise RuntimeError('Fresh focused log contains a material/startup failure')
    assets = {}
    for name in LOOKS:
        master = ROOT / f'Plugins/CkFoundation/Content/CkUsf/GeneratedLooks/M_CkUsf_Look_{name}.uasset'
        assets[str(master.relative_to(ROOT))] = digest(master)
        for channel in (['Normal', 'Roughness'] if name == 'LibraryGlass' else ['BaseColor', 'Normal', 'Roughness']):
            texture = ROOT / f'Plugins/CkFoundation/Content/CkUsf/Textures/Library/T_{name}_{channel}.uasset'
            assets[str(texture.relative_to(ROOT))] = digest(texture)
    report = {'passed': True, 'scope': 'six material source/control/render checks and focused generation, not repository-wide coverage or user artistic approval',
              'source_shader_sha256': proof['source_sha256'], 'selected_map_sha256': selected,
              'new_asset_sha256': assets, 'protected_hashes_unchanged': len(protected),
              'live_source_images': sum(len(stage) for stage in proof['stages'].values()),
              'controls': list(controls['materials']), 'gate': gate,
              'retained_limit': 'HighResShot glass shared-helper recovery failed; ordinary native viewport source proof passes. No renderer-readiness fix is claimed.'}
    (OUTPUT / 'Batch2-Verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'passed': True, 'new_assets': len(assets), 'protected_hashes': len(protected), 'source_images': report['live_source_images']}))


if __name__ == '__main__':
    main()
