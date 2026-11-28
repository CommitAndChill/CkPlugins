"""Reconcile batch-seven source restoration, captured evidence, protected hashes and focused generation."""
import hashlib
import json
from pathlib import Path
import re
from capture_batch7 import LOOKS


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
    proof = read('Batch7-LiveReloadProof.json')
    controls = read('Batch7-ControlProof.json')
    if not all(record.get('passed') is True and record.get('restored') is True for record in [proof, controls]):
        raise RuntimeError('Source/control proof is incomplete or not restored')
    if set(controls['materials']) != set(LOOKS):
        raise RuntimeError('Control evidence does not cover exactly the six batch-seven materials')
    initial_library = proof['initial_library']
    if len(initial_library) != 42 or not set(LOOKS) <= set(initial_library):
        raise RuntimeError('Source proof must retain all 42 library MID/master pairs')
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
    if len(source_images) != 30:
        raise RuntimeError('Source proof must identify 30 distinct captured PNGs')
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
    if (len(controls['initial_library']) != 42 or controls['initial_library'] != controls['final_library']
            or set(controls['initial_library']) != set(initial_library)):
        raise RuntimeError('Control proof did not restore all 42 library specimens')
    control_images = proof_capture_hashes(controls, 'Batch7-ControlProof.json')
    if len(control_images) != 42:
        raise RuntimeError('Control proof must identify 42 distinct captured PNGs')
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

    protected = read('Batch7-OpeningHashes.json')
    for path, expected in protected.items():
        if digest(ROOT / path) != expected:
            raise RuntimeError('Protected asset/source changed: ' + path)
    source = ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch7Textures'
    manifest_file = source / 'Manifest-v2.json'
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    original_manifest = json.loads((source / 'Manifest.json').read_text(encoding='utf-8'))
    if {record['look_id'] for record in manifest['materials'].values()} != set(LOOKS):
        raise RuntimeError('Manifest roster differs from batch seven')
    selected = {}
    for record in manifest['materials'].values():
        for info in record['maps'].values():
            path = (source / info['path']).resolve()
            path.relative_to(source.resolve())
            if digest(path) != info['sha256']:
                raise RuntimeError('Recorded source hash differs: ' + str(path))
            selected[str(path.relative_to(ROOT))] = info['sha256']
    preparation = read('Batch7Preparation.json')
    expected_looks = dict(zip(['nylon', 'slate', 'copper', 'glossy_plastic', 'wax', 'fiberglass'], LOOKS))
    if set(manifest['materials']) != set(expected_looks):
        raise RuntimeError('Selected manifest must retain the exact six approved material keys')
    consumed_maps, texture_manifests, texture_looks = {}, {}, {}
    for key, look_id in expected_looks.items():
        record = manifest['materials'][key]
        if record['look_id'] != look_id:
            raise RuntimeError('Selected manifest look identity differs: ' + key)
        family = 'LibraryFiberglassV2' if key == 'fiberglass' else look_id
        tag = 'CkTests/Resources/CkUsf/Batch7Textures/' + ('Manifest-v2.json' if key == 'fiberglass' else 'Manifest.json')
        for channel in ['BaseColor', 'Normal', 'Roughness']:
            info = record['maps'][channel]
            name = 'T_' + family + '_' + channel
            if info['runtime_name'] != name:
                raise RuntimeError('Unexpected selected texture runtime family: ' + key + '/' + channel)
            if key != 'fiberglass' and any(info[field] != original_manifest['materials'][key]['maps'][channel][field]
                                            for field in ['path', 'sha256', 'runtime_name', 'width', 'height']):
                raise RuntimeError('One of the fifteen original-map identities changed: ' + key + '/' + channel)
            path = '/CkFoundation/CkUsf/Textures/Library/' + name
            consumed_maps[path] = info
            texture_manifests[path] = tag
            texture_looks[path] = (look_id, channel)
    expected_textures = set(consumed_maps)
    if ({record['path'] for record in preparation['textures']} != expected_textures
            or len(preparation['textures']) != 18):
        raise RuntimeError('Preparation must cover exactly the 18 consumed BC/N/R textures')
    for texture in preparation['textures']:
        if texture['manifest'] != texture_manifests[texture['path']]:
            raise RuntimeError('Selected texture manifest ownership differs: ' + texture['path'])
        look_id, binding = texture_looks[texture['path']]
        expected_binding = texture['path'] + '.' + texture['path'].rsplit('/', 1)[-1]
        if initial_library[look_id]['textures'][binding + 'Map'] != expected_binding:
            raise RuntimeError('Live look does not bind its selected texture family: ' + look_id + '/' + binding)
        channel = texture['path'].rsplit('_', 1)[-1]
        compression = {'BaseColor': 'TC_DEFAULT', 'Normal': 'TC_NORMALMAP',
                       'Roughness': 'TC_MASKS'}[channel]
        group = ('TEXTUREGROUP_WORLD' if channel == 'BaseColor' else
                 'TEXTUREGROUP_WORLD_NORMAL_MAP' if channel == 'Normal' else 'TEXTUREGROUP_WORLD_SPECULAR')
        if (texture['srgb'] != (channel == 'BaseColor')
                or '.' + compression + ':' not in texture['compression']
                or '.' + group + ':' not in texture['lod_group']
                or texture['settings_verified_after_save'] is not True):
            raise RuntimeError('Saved channel color/compression/group contract differs: ' + texture['path'])
        info = consumed_maps[texture['path']]
        source_size = [info['width'], info['height']]
        resize = any(dimension & (dimension - 1) for dimension in source_size)
        runtime_size = [1024, 1024] if resize else source_size
        if (texture['sha256'] != info['sha256'] or texture['source_size'] != source_size
                or texture['runtime_size'] != runtime_size or texture['runtime_resize_for_streaming'] != resize
                or texture['runtime_aspect_changed'] != (resize and source_size[0] != source_size[1])):
            raise RuntimeError('Imported source identity/dimensions differ: ' + texture['path'])
        settings = texture['saved_settings']
        required_settings = {'srgb', 'compression_settings', 'lod_group', 'address_x', 'address_y',
                             'mip_gen_settings', 'flip_green_channel', 'power_of_two_mode'}
        if (set(settings) != required_settings or settings['srgb'] != (channel == 'BaseColor')
                or '.' + compression + ':' not in settings['compression_settings']
                or '.' + group + ':' not in settings['lod_group']
                or '.TA_WRAP:' not in settings['address_x'] or '.TA_WRAP:' not in settings['address_y']
                or '.TMGS_SIMPLE_AVERAGE:' not in settings['mip_gen_settings']
                or settings['flip_green_channel'] is not False
                or ('.RESIZE_TO_SPECIFIC_RESOLUTION:' if resize else '.NONE:') not in settings['power_of_two_mode']):
            raise RuntimeError('Saved mip/wrap/normal/resize contract differs: ' + texture['path'])

    state = read('Batch7-FinalWarmState.json')
    if state['preview_quality'] or state['diagnostic_light'] is not None:
        raise RuntimeError('Temporary quality/light settings remain active')
    if state['render_cvars']['r.AntiAliasingMethod'] != 0 or state['render_cvars']['r.ScreenPercentage'] != 87:
        raise RuntimeError('Baseline renderer settings were not restored')
    if set(state['library']) != set(initial_library) or any(item['values']['DebugView'] != 0 for item in state['library'].values()):
        raise RuntimeError('Final library roster is incomplete or a debug view remains active')
    for name, restored in controls['final_library'].items():
        if any(state['library'][name][key] != restored[key] for key in ['mid', 'parent', 'textures', 'values', 'colors']):
            raise RuntimeError('Final state differs from the restored library controls/bindings: ' + name)
    gate = read('Batch7-Gate.exit.json')
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
    records = read('Batch7-LitCaptures.json')
    for prefix in ['Batch7', 'Batch7-Preview']:
        for name in LOOKS:
            for view in ['Close', 'Macro', 'Gameplay']:
                if view not in records[prefix + '-' + name]:
                    raise RuntimeError('Missing recorded comparison view: ' + prefix + '/' + name + '/' + view)
                filename = f'{prefix}-{name}-{view}.png'
                captures[filename] = image_hash(filename)
    report = {'passed': True, 'scope': 'Recorded six-material source/control/render evidence and focused generation; user artistic acceptance remains separate.',
              'selected_manifest_sha256': digest(manifest_file), 'texture_manifest_ownership': texture_manifests,
              'source_shader_sha256': shader_hashes, 'selected_map_sha256': selected, 'new_asset_sha256': assets,
              'protected_hashes_unchanged': len(protected), 'source_capture_sha256': source_images,
              'lit_capture_sha256': captures, 'control_capture_sha256': control_images,
              'controls': list(controls['materials']), 'preserved_library_mid_master_pairs': len(initial_library), 'gate': gate,
              'retained_limits': ['Rendered controls and texture-backed surface responses do not establish measured optical properties or user artistic acceptance.']}
    (OUTPUT / 'Batch7-Verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'passed': True, 'new_assets': len(assets), 'protected_hashes': len(protected), 'source_images': len(source_images)}))


if __name__ == '__main__':
    main()
