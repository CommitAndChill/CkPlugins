"""Reconcile batch-four source restoration, captured evidence, protected hashes and focused generation."""
import hashlib
import json
import math
from pathlib import Path
import re
from capture_batch4 import LOOKS


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
    proof = read('Batch4-LiveReloadProof.json')
    controls = read('Batch4-ControlProof.json')
    if not all(record.get('passed') is True and record.get('restored') is True for record in [proof, controls]):
        raise RuntimeError('Source/control proof is incomplete or not restored')
    if set(controls['materials']) != set(LOOKS):
        raise RuntimeError('Control evidence does not cover exactly the six batch-four materials')
    shader_hashes = proof['source_sha256']
    required_sources = {name + '.ush' for name in LOOKS} | {'LibrarySurface.ush'}
    if not required_sources <= {Path(path).name for path in shader_hashes}:
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
            if state['pid'] != proof['pid'] or current['same_mid'] is not True or current['same_master'] is not True:
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

    protected = read('Batch4-OpeningHashes.json')
    for path, expected in protected.items():
        if digest(ROOT / path) != expected:
            raise RuntimeError('Protected asset/source changed: ' + path)
    source = ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch4Textures'
    manifest = json.loads((source / 'Manifest.json').read_text(encoding='utf-8'))
    if {record['look_id'] for record in manifest['materials'].values()} != set(LOOKS):
        raise RuntimeError('Manifest roster differs from batch four')
    selected = {}
    for record in manifest['materials'].values():
        for info in record['maps'].values():
            path = (source / info['path']).resolve()
            path.relative_to(source.resolve())
            if digest(path) != info['sha256']:
                raise RuntimeError('Recorded source hash differs: ' + str(path))
            selected[str(path.relative_to(ROOT))] = info['sha256']
    preparation = read('Batch4Preparation.json')
    expected_textures = {f'/CkFoundation/CkUsf/Textures/Library/T_{name}_{channel}' for name in LOOKS
                         for channel in ['BaseColor', 'Normal', 'Roughness'] + (['TileMask'] if name == 'LibraryPorcelain' else [])}
    if {record['path'] for record in preparation['textures']} != expected_textures or len(preparation['textures']) != 19:
        raise RuntimeError('Preparation must cover exactly the 19 consumed texture assets')

    state = read('Batch4-FinalLiveState.json')['result']
    if state['preview_quality'] or state['diagnostic_light'] is not None:
        raise RuntimeError('Temporary quality/light settings remain active')
    if state['render_cvars']['r.AntiAliasingMethod'] != 0 or state['render_cvars']['r.ScreenPercentage'] != 87:
        raise RuntimeError('Baseline renderer settings were not restored')
    if not set(LOOKS) <= set(state['library']) or any(item['values']['DebugView'] != 0 for item in state['library'].values()):
        raise RuntimeError('Final library roster is incomplete or a debug view remains active')
    dedicated = {}
    for filename in ['Batch4-PlasticProof.json', 'Batch4-PorcelainProof.json']:
        record = read(filename)
        if record.get('passed') is not True or record.get('restored') is not True:
            raise RuntimeError('Required specialty proof is incomplete: ' + filename)
        for path, expected in record.get('source_sha256', {}).items():
            if digest(source_path(path)) != expected:
                raise RuntimeError('Specialty proof source hash differs: ' + path)
        dedicated[filename] = {'sha256': digest(OUTPUT / filename), 'scope': record.get('scope', 'See dedicated proof record'),
                               'capture_sha256': proof_capture_hashes(record, filename)}

    fill_filename = 'Batch4-FillProof.json'
    fill_proof = read(fill_filename)
    if (fill_proof.get('passed') is not True or fill_proof.get('restored') is not True
            or fill_proof.get('gc_retained') is not True):
        raise RuntimeError('Required local-fill proof is incomplete or not restored')
    bounds_filename = 'Batch4-FillBounds.json'
    bounds = read(bounds_filename)
    fill = bounds['fill']
    current_fills = [light for light in state['library']['LibraryTranslucentPlastic']['point_lights']
                     if 'Usf.TranslucentBodyFill' in light['tags']]
    if current_fills != [fill]:
        raise RuntimeError('Final plastic fill differs from the inspected bounds contract')
    radius = fill['radius']
    if (type(radius) not in (int, float) or not math.isfinite(radius) or radius <= 0
            or fill['intensity'] != 80 or 'CANDELAS' not in fill['units']
            or 'Usf.TranslucentBodyFill' not in fill['tags'] or fill['world_scale'] != [1, 1, 1]):
        raise RuntimeError('Local plastic fill does not match the recorded 80 cd unscaled light contract')
    others = set(bounds['state']['library']) - {'LibraryTranslucentPlastic'}
    distances = bounds['minimum_distance_to_other_mesh_aabb']
    if (set(bounds['state']['library']) != set(state['library']) or not others
            or set(distances) != others or bounds.get('outside_all_other_bounds') is not True):
        raise RuntimeError('Fill bounds do not cover every other recorded library specimen')
    if any(type(distance) not in (int, float) or not math.isfinite(distance) or distance <= radius
           for distance in distances.values()):
        raise RuntimeError('Another recorded library specimen intersects the plastic fill radius')
    fill_evidence = {'proof_sha256': digest(OUTPUT / fill_filename), 'bounds_sha256': digest(OUTPUT / bounds_filename),
                     'capture_sha256': proof_capture_hashes(fill_proof, fill_filename), 'fill': fill,
                     'other_library_specimens_outside_radius': len(others),
                     'scope': 'Recorded library specimen mesh AABBs; dedicated neighbor captures record rendered light isolation.'}

    gate = read('Batch4-Gate.exit.json')
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
    records = read('Batch4-LitCaptures.json')
    for prefix in ['Batch4', 'Batch4-Preview']:
        for name in LOOKS:
            for view in ['Close', 'Macro', 'Gameplay']:
                if view not in records[prefix + '-' + name]:
                    raise RuntimeError('Missing recorded comparison view: ' + prefix + '/' + name + '/' + view)
                filename = f'{prefix}-{name}-{view}.png'
                captures[filename] = image_hash(filename)
    report = {'passed': True, 'scope': 'Recorded six-material source/control/render evidence and focused generation; user artistic acceptance remains separate.',
              'source_shader_sha256': shader_hashes, 'selected_map_sha256': selected, 'new_asset_sha256': assets,
              'protected_hashes_unchanged': len(protected), 'source_capture_sha256': source_images,
              'lit_capture_sha256': captures, 'controls': list(controls['materials']), 'gate': gate,
              'specialty_proofs': dedicated, 'local_fill_evidence': fill_evidence,
              'retained_limits': ['Translucent plastic uses a thin-surface model; BodyCoverage covers transmission with lit body color, not thickness-aware volume scattering.',
                                  'Translucent plastic uses a local 80 cd Point fill; recorded other library specimen bounds lie outside its attenuation radius.',
                                  'Porcelain material composition follows recorded source identity; the name alone is not chemical or catalog verification.']}
    (OUTPUT / 'Batch4-Verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'passed': True, 'new_assets': len(assets), 'protected_hashes': len(protected), 'source_images': len(source_images)}))


if __name__ == '__main__':
    main()
