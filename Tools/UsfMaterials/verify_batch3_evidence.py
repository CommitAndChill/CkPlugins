"""Independently reconcile source, live-render and focused-gate evidence for batch three."""
import hashlib
import argparse
import json
from pathlib import Path
import re
from capture_batch3 import LOOKS

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate_summary(log, exit_code):
    summaries = list(re.finditer(
        r'Total:\s*(\d+)\s+Passed:\s*(\d+)\s+Failed:\s*(\d+)\s+Skipped:\s*(\d+)\s+Contaminated:\s*(\d+)', log))
    if not summaries:
        raise RuntimeError('Focused gate has no structured test summary')
    total, passed, failed, skipped, contaminated = map(int, summaries[-1].groups())
    if exit_code != 0 or total <= 0 or passed != total or failed != 0 or skipped != 0 or contaminated != 0:
        raise RuntimeError(f'Focused gate incomplete: exit={exit_code}, total={total}, passed={passed}, failed={failed}, skipped={skipped}, contaminated={contaminated}')
    return {'total': total, 'passed': passed, 'failed': failed, 'skipped': skipped, 'contaminated': contaminated}


def source_path(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def frost_evidence(path, required):
    """Descriptor convention matches make_batch3_gallery.py; never invent a pass."""
    if not path.exists():
        if required:
            raise RuntimeError('Required new pane evidence descriptor is missing: ' + str(path))
        return {'status': 'not_provided', 'scope': 'New SceneColor pane result not verified by this run'}
    descriptor = json.loads(path.read_text(encoding='utf-8-sig'))
    if not descriptor.get('proof') or not descriptor.get('captures'):
        raise RuntimeError('Pane descriptor requires a proof record and captures')
    proof_path = (OUTPUT / descriptor['proof']).resolve()
    proof_path.relative_to(OUTPUT.resolve())
    proof = json.loads(proof_path.read_text(encoding='utf-8-sig'))
    if not (proof.get('passed') is True and proof.get('restored') is True and proof.get('source_sha256')):
        raise RuntimeError('New pane proof is incomplete or does not establish restoration/source identity')
    checked_sources = {}
    for filename, expected in proof['source_sha256'].items():
        actual = source_path(filename)
        if digest(actual) != expected:
            raise RuntimeError('Pane proof source hash differs: ' + filename)
        checked_sources[actual.name] = expected
    if not {'SurfaceSceneColor.ush', 'LibraryFrostedGlass.ush'}.issubset(checked_sources):
        raise RuntimeError('Pane proof must identify the current SceneColor helper and frosted look')
    captures = {}
    for record in descriptor['captures']:
        capture = (OUTPUT / record['path']).resolve()
        capture.relative_to(OUTPUT.resolve())
        data = capture.read_bytes()
        if data[:8] != b'\x89PNG\r\n\x1a\n' or len(data) <= 1000:
            raise RuntimeError('Missing or invalid pane PNG: ' + str(capture))
        actual_hash = hashlib.sha256(data).hexdigest()
        if record.get('sha256') and record['sha256'] != actual_hash:
            raise RuntimeError('Pane capture hash differs: ' + str(capture))
        captures[capture.relative_to(OUTPUT).as_posix()] = actual_hash
    return {'status': 'verified_record', 'proof': proof_path.relative_to(OUTPUT).as_posix(),
            'proof_sha256': digest(proof_path), 'source_sha256': proof['source_sha256'], 'capture_sha256': captures,
            'scope': descriptor.get('scope', 'Recorded pane proof and source restoration; user visual acceptance remains separate')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frost-evidence', type=Path, default=OUTPUT / 'Batch3-FrostEvidence.json')
    args = parser.parse_args()
    proof = read('Batch3-LiveReloadProof.json')
    controls = read('Batch3-ControlProof.json')
    if not (proof['passed'] and proof['restored'] and controls['passed'] and controls['restored']):
        raise RuntimeError('Live source/control proof is incomplete')
    for path, expected in proof['source_sha256'].items():
        if digest(source_path(path)) != expected:
            raise RuntimeError('Shader restoration hash differs: ' + path)
    protected = read('Batch3-OpeningHashes.json')
    for path, expected in protected.items():
        if digest(ROOT / path) != expected:
            raise RuntimeError('Protected asset/source changed: ' + path)
    source = ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch3Textures'
    manifest = json.loads((source / 'Manifest.json').read_text())
    selected = {}
    for record in manifest['materials'].values():
        for info in record['maps'].values():
            path = source / info['path']
            if digest(path) != info['sha256']:
                raise RuntimeError('Recorded source hash differs: ' + str(path))
            selected[str(path.relative_to(ROOT))] = info['sha256']
    state = read('Batch3-FinalLiveState.json')['result']
    if state['preview_quality'] or state['diagnostic_light'] is not None:
        raise RuntimeError('Temporary renderer/light state remains active')
    if state['render_cvars']['r.AntiAliasingMethod'] != 0 or state['render_cvars']['r.ScreenPercentage'] != 87:
        raise RuntimeError('Preview renderer settings were not restored')
    if any(item['values']['DebugView'] != 0 for item in state['library'].values()):
        raise RuntimeError('A diagnostic material view remains active')
    gate = read('Batch3-Gate.exit.json')
    log = (ROOT / gate['log']).read_text(errors='replace')
    summary = gate_summary(log, gate['exit_code'])
    required_tests = ['SurfaceSceneColorContract', 'SurfaceSceneColorRejectsUnsupportedAndChangedLayouts',
                      'GeneratesUsableMasters', 'ShaderReloadUpdatesExistingMID', 'ToonAuthoringGeneratesNativeMaster']
    for name in required_tests:
        if not any('Test Completed.' in line and 'Result={Success}' in line and ('Name={'+name+'}') in line
                   for line in log.splitlines()):
            raise RuntimeError('Required fresh test has no passing completion: '+name)
    summary['required_passing_tests'] = required_tests

    if re.search(r'Assertion failed|Fatal error|Ensure condition failed|Script Compile Error|Failed to compile Material', log):
        raise RuntimeError('Fresh focused log contains a material/startup failure')
    assets = {}
    for name in LOOKS:
        master = ROOT / f'Plugins/CkFoundation/Content/CkUsf/GeneratedLooks/M_CkUsf_Look_{name}.uasset'
        assets[str(master.relative_to(ROOT))] = digest(master)
        for channel in (['Normal', 'Roughness'] if name == 'LibraryFrostedGlass' else ['BaseColor', 'Normal', 'Roughness']):
            texture = ROOT / f'Plugins/CkFoundation/Content/CkUsf/Textures/Library/T_{name}_{channel}.uasset'
            assets[str(texture.relative_to(ROOT))] = digest(texture)
    frost_path = args.frost_evidence if args.frost_evidence.is_absolute() else OUTPUT / args.frost_evidence
    # A new final reconciliation must include the SceneColor pane extension;
    # absence cannot be converted into a successful six-material acceptance.
    pane = frost_evidence(frost_path, True)
    report = {'passed': True, 'scope': 'recorded batch-three source/control evidence, source identity and focused gate; pane scope is reported separately, not repository-wide coverage or user artistic approval',
              'source_shader_sha256': proof['source_sha256'], 'selected_map_sha256': selected,
              'new_asset_sha256': assets, 'protected_hashes_unchanged': len(protected),
              'live_source_images': sum(len(stage) for stage in proof['stages'].values()),
              'controls': list(controls['materials']), 'gate': gate, 'gate_summary': summary,
              'frost_pane_evidence': pane,
              'retained_limits': ['Frosted glass uses 64 linear-HDR SceneColor taps for screen-space rough-transmission approximation, not physically thick optics.',
                                  'Its Normal/Roughness originate from clean matte Plastic010 finish data, not an optical glass scan.',
                                  'Historical HighResShot observations do not establish the current extension result; current referenced proof and captures determine this run.']}
    (OUTPUT / 'Batch3-Verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'passed': True, 'new_assets': len(assets), 'protected_hashes': len(protected), 'source_images': report['live_source_images']}))


if __name__ == '__main__':
    main()
