"""Reconcile batch-six source restoration, captured evidence, protected hashes and focused generation."""
import hashlib
import json
from pathlib import Path
import re
from capture_batch6 import LOOKS


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_path(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def image_hash(filename):
    path = (OUTPUT / filename).resolve()
    path.relative_to(OUTPUT.resolve())
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n' or len(data) <= 1000:
        raise RuntimeError('Missing or invalid captured PNG: ' + filename)
    return hashlib.sha256(data).hexdigest()


def proof_capture_hashes(record, filename):
    captures = record.get('captures', {})
    if not captures:
        raise RuntimeError('Required proof has no captured images: ' + filename)
    hashes = {}
    for label, capture in captures.items():
        reference = capture.get('image', capture.get('capture'))
        if not isinstance(reference, str):
            raise RuntimeError('Missing proof PNG reference: ' + filename + '/' + label)
        path = (OUTPUT / reference).resolve()
        relative = str(path.relative_to(OUTPUT.resolve()))
        hashes[relative] = image_hash(reference)
    return hashes


def main():
    proof = read('Batch6-LiveReloadProof.json')
    controls = read('Batch6-ControlProof.json')
    if not all(record.get('passed') is True and record.get('restored') is True for record in [proof, controls]):
        raise RuntimeError('Source/control proof is incomplete or not restored')
    if set(controls['materials']) != set(LOOKS):
        raise RuntimeError('Control evidence does not cover exactly the six batch-six materials')
    initial_library = proof['initial_library']
    if len(initial_library) != 36 or not set(LOOKS) <= set(initial_library):
        raise RuntimeError('Source proof must retain all 36 library MID/master pairs')
    if len(proof['reloads']) != 14:
        raise RuntimeError('Complete source proof must record all 14 edit/recovery reloads')
    shader_hashes = proof['source_sha256']
    required_sources = {name + '.ush' for name in LOOKS} | {'LibrarySurface.ush'}
    if required_sources != {Path(path).name for path in shader_hashes} or len(shader_hashes) != 7:
        raise RuntimeError('Source proof does not identify every entrypoint and shared library')
    for path, expected in shader_hashes.items():
        if digest(source_path(path)) != expected:
            raise RuntimeError('Shader restoration hash differs: ' + path)
    source_images = {}
    required_stages = {'baseline': LOOKS, 'shared-edited': LOOKS, 'shared-recovered': LOOKS}
    for name in LOOKS:
        required_stages[name + '-edited'] = [name]
        required_stages[name + '-recovered'] = [name]
    for stage, names in required_stages.items():
        records = proof['stages'][stage]
        if set(records) != set(names):
            raise RuntimeError('Incorrect source proof stage coverage: ' + stage)
        for name, record in records.items():
            state = record['state']
            current = state['library'][name]
            if (state['pid'] != proof['pid'] or state['library'] != initial_library
                    or current['same_mid'] is not True or current['same_master'] is not True):
                raise RuntimeError('Source proof does not preserve the editor/master/MID: ' + stage + '/' + name)
            source_images[record['image']] = image_hash(record['image'])
    for name in LOOKS:
        before = proof['stages']['baseline'][name]['mean_display_rgb']
        if before < .002:
            raise RuntimeError('Source proof has an empty/dark baseline: ' + name)
        for label in [name, 'shared']:
            edited = proof['stages'][label + '-edited'][name]['mean_display_rgb']
            recovered = proof['stages'][label + '-recovered'][name]['mean_display_rgb']
            if edited >= before * .85 or abs(recovered - before) >= min(.02, max(.0008, before * .12)):
                raise RuntimeError('Source edit/recovery metrics failed reconciliation: ' + label + '/' + name)

    stages = ['lit', 'special', 'normal', 'flat-normal', 'rotated', 'roughness', 'roughness-high']
    expected_controls = {name + '/' + stage for name in LOOKS for stage in stages}
    if set(controls['captures']) != expected_controls:
        raise RuntimeError('Control proof must record all 42 captures')
    if (len(controls['initial_library']) != 36 or controls['initial_library'] != controls['final_library']
            or set(controls['initial_library']) != set(initial_library)):
        raise RuntimeError('Control proof did not restore all 36 library specimens')
    control_images = proof_capture_hashes(controls, 'Batch6-ControlProof.json')
    for label, record in controls['captures'].items():
        state = record['state']
        if state['pid'] != controls['pid'] or set(state['library']) != set(initial_library):
            raise RuntimeError('Control capture changed its editor or library roster: ' + label)
        for look, before in controls['initial_library'].items():
            if any(state['library'][look][key] != before[key] for key in ['mid', 'parent', 'textures']):
                raise RuntimeError('Control capture changed MID/master/texture bindings: ' + label + '/' + look)
    for name, record in controls['materials'].items():
        expected_pairs = {'lit/special', 'normal/flat-normal', 'normal/rotated', 'roughness/roughness-high'}
        if set(record['differences']) != expected_pairs or any(not item['max_rgb'] > .003 for item in record['differences'].values()):
            raise RuntimeError('Control response metrics failed reconciliation: ' + name)

    protected = read('Batch6-OpeningHashes.json')
    for path, expected in protected.items():
        if digest(ROOT / path) != expected:
            raise RuntimeError('Protected asset/source changed: ' + path)
    source = ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch6Textures'
    manifest = json.loads((source / 'Manifest.json').read_text(encoding='utf-8'))
    if {record['look_id'] for record in manifest['materials'].values()} != set(LOOKS):
        raise RuntimeError('Manifest roster differs from batch six')
    selected = {}
    for record in manifest['materials'].values():
        for info in record['maps'].values():
            path = (source / info['path']).resolve()
            path.relative_to(source.resolve())
            if digest(path) != info['sha256']:
                raise RuntimeError('Recorded source hash differs: ' + str(path))
            selected[str(path.relative_to(ROOT))] = info['sha256']
    preparation = read('Batch6Preparation.json')
    expected_textures = {f'/CkFoundation/CkUsf/Textures/Library/T_{name}_{channel}' for name in LOOKS
                         for channel in ['BaseColor', 'Normal', 'Roughness']}
    mosaic = manifest['materials']['mosaic']
    if 'TileMask' not in mosaic['maps']:
        raise RuntimeError('Mosaic requires its source-aligned TileMask')
    expected_textures.add('/CkFoundation/CkUsf/Textures/Library/T_LibraryMosaic_TileMask')
    if ({record['path'] for record in preparation['textures']} != expected_textures
            or len(preparation['textures']) != 19):
        raise RuntimeError('Preparation must cover exactly 19 textures: BC/N/R plus the required mosaic TileMask')
    for texture in preparation['textures']:
        channel = texture['path'].rsplit('_', 1)[-1]
        compression = {'BaseColor': 'TC_DEFAULT', 'Normal': 'TC_NORMALMAP',
                       'Roughness': 'TC_MASKS', 'TileMask': 'TC_MASKS'}[channel]
        group = ('TEXTUREGROUP_WORLD' if channel == 'BaseColor' else
                 'TEXTUREGROUP_WORLD_NORMAL_MAP' if channel == 'Normal' else 'TEXTUREGROUP_WORLD_SPECULAR')
        if (texture['srgb'] != (channel == 'BaseColor')
                or '.' + compression + ':' not in texture['compression']
                or '.' + group + ':' not in texture['lod_group']
                or texture['settings_verified_after_save'] is not True):
            raise RuntimeError('Saved channel color/compression/group contract differs: ' + texture['path'])

    mosaic_filename = 'Batch6-MosaicProof.json'
    mosaic_proof = read(mosaic_filename)
    if mosaic_proof.get('passed') is not True or mosaic_proof.get('restored') is not True:
        raise RuntimeError('Required mosaic glaze/grout proof is incomplete or not restored')
    mosaic_hashes = mosaic_proof.get('source_sha256', {})
    if 'LibraryMosaic.ush' not in {Path(path).name for path in mosaic_hashes}:
        raise RuntimeError('Mosaic proof must identify its shader source hash')
    for path, expected in mosaic_hashes.items():
        if digest(source_path(path)) != expected:
            raise RuntimeError('Mosaic proof source restoration hash differs: ' + path)
    mosaic_evidence = {'sha256': digest(OUTPUT / mosaic_filename), 'source_sha256': mosaic_hashes,
                       'capture_sha256': proof_capture_hashes(mosaic_proof, mosaic_filename),
                       'scope': mosaic_proof.get('scope', 'Dedicated mosaic glaze/grout separation proof')}

    state = read('Batch6-FinalLiveState.json')['result']
    if state['preview_quality'] or state['diagnostic_light'] is not None:
        raise RuntimeError('Temporary quality/light settings remain active')
    if state['render_cvars']['r.AntiAliasingMethod'] != 0 or state['render_cvars']['r.ScreenPercentage'] != 87:
        raise RuntimeError('Baseline renderer settings were not restored')
    if set(state['library']) != set(initial_library) or any(item['values']['DebugView'] != 0 for item in state['library'].values()):
        raise RuntimeError('Final library roster is incomplete or a debug view remains active')
    for name, restored in controls['final_library'].items():
        if any(state['library'][name][key] != restored[key] for key in ['mid', 'parent', 'textures', 'values', 'colors']):
            raise RuntimeError('Final state differs from the restored library controls/bindings: ' + name)
    gate = read('Batch6-Gate.exit.json')
    log = source_path(gate['log']).read_text(errors='replace')
    summaries = list(re.finditer(r'Total:\s*(\d+)\s+Passed:\s*(\d+)\s+Failed:\s*(\d+)\s+Skipped:\s*(\d+)\s+Contaminated:\s*(\d+)', log))
    if gate['exit_code'] != 0 or not summaries or tuple(map(int, summaries[-1].groups())) != (1, 1, 0, 0, 0):
        raise RuntimeError('Focused generation gate did not pass exactly 1/1')
    if not any('Test Completed.' in line and 'Result={Success}' in line and 'Name={GeneratesUsableMasters}' in line for line in log.splitlines()):
        raise RuntimeError('The fresh log has no successful GeneratesUsableMasters completion')
    if re.search(r'Assertion failed|Fatal error|Ensure condition failed|Script Compile Error|Failed to compile Material', log):
        raise RuntimeError('The fresh log contains a material/startup failure')
    assets = {}
    for name in LOOKS:
        master = ROOT / f'Plugins/CkFoundation/Content/CkUsf/GeneratedLooks/M_CkUsf_Look_{name}.uasset'
        assets[str(master.relative_to(ROOT))] = digest(master)
    for path in sorted(expected_textures):
        texture = ROOT / 'Plugins/CkFoundation/Content' / (path.removeprefix('/CkFoundation/') + '.uasset')
        assets[str(texture.relative_to(ROOT))] = digest(texture)
    captures = {}
    records = read('Batch6-LitCaptures.json')
    for prefix in ['Batch6', 'Batch6-Preview']:
        for name in LOOKS:
            for view in ['Close', 'Macro', 'Gameplay']:
                if view not in records[prefix + '-' + name]:
                    raise RuntimeError('Missing recorded comparison view: ' + prefix + '/' + name + '/' + view)
                filename = f'{prefix}-{name}-{view}.png'
                captures[filename] = image_hash(filename)
    report = {'passed': True, 'scope': 'Recorded six-material source/control/render evidence and focused generation; user artistic acceptance remains separate.',
              'source_shader_sha256': shader_hashes, 'selected_map_sha256': selected, 'new_asset_sha256': assets,
              'protected_hashes_unchanged': len(protected), 'source_capture_sha256': source_images,
              'lit_capture_sha256': captures, 'control_capture_sha256': control_images,
              'controls': list(controls['materials']), 'preserved_library_mid_master_pairs': len(initial_library), 'gate': gate,
              'mosaic_proof': mosaic_evidence,
              'retained_limits': ['Rendered controls and texture-backed surface responses do not establish measured optical properties or user artistic acceptance.']}
    (OUTPUT / 'Batch6-Verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'passed': True, 'new_assets': len(assets), 'protected_hashes': len(protected), 'source_images': len(source_images)}))


if __name__ == '__main__':
    main()
