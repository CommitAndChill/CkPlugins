"""Offline reconciliation of environmental captures, source restoration and import receipts."""
import hashlib
import datetime
import json
import math
from pathlib import Path
import re
import struct
import numpy as np
from PIL import Image
from generate_environment_grid import build, DIRECTORY

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
STATIONS = {'pom', 'displacement'}
VIEWS = ['Oblique', 'Low', 'Near', 'Far', 'Opposite']
IDENTITY = ['actor', 'mid', 'parent', 'mesh', 'textures', 'scale', 'colors', 'rect_intensities']


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def asset_file(path):
    for mount, directory in [('/CkFoundation/', 'Plugins/CkFoundation/Content/'),
                             ('/CkTests/', 'Plugins/CkTests/Content/')]:
        if path.startswith(mount):
            return ROOT / (directory + path.removeprefix(mount) + '.uasset')
    raise RuntimeError('Unrecognized asset mount: ' + path)


def region(filename):
    data = np.asarray(Image.open(OUTPUT / filename).convert('RGB'), dtype=float) / 255.0
    height, width = data.shape[:2]
    return data[int(height * .39):int(height * .64), int(width * .40):int(width * .60)]


def compare(left, right):
    require(left.shape == right.shape, 'Compared capture dimensions differ')
    delta = np.abs(left - right)
    return {'mean_absolute_rgb': float(delta.mean()), 'max_rgb': float(delta.max()),
            'fraction_over_one_code': float(np.mean(np.any(delta > 1 / 255 + 1e-6, axis=2)))}


def measure_uv_orientation(regions):
    flat = regions['UV-Basis']
    height, width = flat.shape[:2]
    basis = {'red_far_minus_near': float(flat[:height // 3, :, 0].mean() - flat[-height // 3:, :, 0].mean()),
             'green_right_minus_left': float(flat[:, -width // 3:, 1].mean() - flat[:, :width // 3, 1].mean())}
    direction = {'forward_red_shift': float((regions['UV-Forward-POM'] - regions['UV-Forward-Flat'])[:, :, 0].mean()),
                 'reverse_red_shift': float((regions['UV-Reverse-POM'] - regions['UV-Reverse-Flat'])[:, :, 0].mean())}
    return {'imported_uv_basis': basis, 'opposing_pom_ray_direction': direction}


def metric_matches(recorded, measured):
    if isinstance(measured, dict):
        return (isinstance(recorded, dict) and set(recorded) == set(measured)
                and all(metric_matches(recorded[key], value) for key, value in measured.items()))
    return isinstance(recorded, (int, float)) and math.isclose(recorded, measured, rel_tol=1e-10, abs_tol=1e-12)


def validate_grid_sections(grid):
    slots = grid['slots']
    require(slots.count('Specimen') == 1 and slots.count('CoreBase') == 1,
            'Ground requires unique named Specimen/CoreBase slots')
    sections = grid['section_material_indices']
    require(isinstance(sections, dict) and bool(sections), 'Ground requires recorded sections for every LOD')
    used = set()
    for lod, indices in sections.items():
        require(isinstance(indices, list) and len(indices) == 2
                and all(type(index) is int and 0 <= index < len(slots) for index in indices),
                'Invalid ground section material indices: LOD ' + str(lod))
        require({slots[index] for index in indices} == {'Specimen', 'CoreBase'},
                'Ground LOD sections must use exactly Specimen/CoreBase: ' + str(lod))
        used.update(indices)
    unused = [name for index, name in enumerate(slots) if index not in used]
    require(unused in [[], ['defaultMat']] and grid['unused_slots'] == unused,
            'Only one accurately recorded unused defaultMat slot may remain')


def main():
    proof = read('Environment1-Proof.json')
    require(proof.get('passed') is True and proof.get('restored') is True, 'Environment proof did not pass and restore')
    initial, final = proof['initial_state'], proof['final_state']
    require(initial['pid'] == final['pid'] == proof['pid'], 'Environment proof changed its editor')
    require(len(initial['library']) == 42 and initial['library'] == final['library'], 'The 42-material library was not preserved')
    require(set(initial['environment']) == STATIONS and initial['environment'] == final['environment'], 'Both ground stations were not restored')
    require(len({item['mid'] for item in initial['environment'].values()}) == 2, 'Expected two distinct retained ground MIDs')
    require(initial['environment']['pom']['values']['DisplacementAmount'] == 0
            and initial['environment']['pom']['values']['PomAmount'] == 1
            and initial['environment']['displacement']['values']['DisplacementAmount'] == 1
            and initial['environment']['displacement']['values']['PomAmount'] == 0, 'Ground mode baselines differ')
    require(not initial['preview_quality'] and not final['preview_quality'] and final['diagnostic_light'] is None
            and initial['diagnostic_light'] is None, 'Temporary quality/lighting state remains')
    require(initial['render_cvars'] == final['render_cvars'] and final['render_cvars']['r.AntiAliasingMethod'] == 0
            and final['render_cvars']['r.ScreenPercentage'] == 87, 'Baseline renderer settings were not restored')
    require(not proof['cleanup_errors'] and len(proof['reloads']) == 4
            and all('CkUsf reload complete:' in line and '[0] failed' in line for line in proof['reloads']), 'Four successful source reloads required')
    shader = ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/EnvironmentGravel.ush'
    require(proof['source_sha256'] == {str(shader): digest(shader)}, 'Current environment source does not match recovered proof source')

    labels = {f'{quality}-{station}-{view}' for quality in ['Native', 'TAA'] for station in STATIONS for view in VIEWS}
    labels |= {'POM-Off-BC', 'POM-ZeroRelief-BC', 'POM-On-BC', 'POM-Off-Depth', 'POM-On-Depth',
               'WPO-ZeroRelief-Depth', 'WPO-SixCm-Depth', 'WPO-GeometricNormals',
               'Bounds-pom-MaxReliefFar', 'Bounds-displacement-MaxReliefFar',
               'UV-Basis', 'UV-Forward-Flat', 'UV-Forward-POM', 'UV-Reverse-Flat', 'UV-Reverse-POM',
               'VS-Before-Depth', 'VS-Edited-Depth', 'VS-Recovered-Depth'}
    labels |= {f'Source-{stage}-{station}' for stage in ['Before', 'Edited', 'Recovered'] for station in STATIONS}
    require(len(labels) == 44 and set(proof['captures']) == labels, 'Environment proof must cover all 44 distinct capture stages')
    images, regions = {}, {}
    for label, record in proof['captures'].items():
        filename = 'Environment1-' + label + '.png'
        require(record['image'] == filename, 'Unexpected capture reference: ' + label)
        path = OUTPUT / filename
        data = path.read_bytes()
        require(data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) > 1000, 'Invalid PNG: ' + filename)
        images[filename] = digest(path)
        require(images[filename] == record['sha256'], 'Capture hash differs: ' + filename)
        regions[label] = region(filename)
        state = record['state']
        require(state['pid'] == proof['pid'] and state['library'] == initial['library'], 'Capture changed editor/library: ' + label)
        require(set(state['environment']) == STATIONS and record['station'] in STATIONS, 'Capture ground roster differs')
        for station, before in initial['environment'].items():
            current = state['environment'][station]
            require(current['same_mid'] is True and current['same_master'] is True
                    and all(current[key] == before[key] for key in IDENTITY)
                    and current['scale'] == [1, 1, 1], 'Capture changed ground identity/bindings: ' + label + '/' + station)
            expected_values = record['overrides'] if record['station'] == station else before['values']
            require(current['values'] == expected_values, 'Capture parameters differ from recorded controls: ' + label)
        taa = label.startswith('TAA-')
        require(state['render_cvars']['r.AntiAliasingMethod'] == (2 if taa else 0)
                and state['render_cvars']['r.ScreenPercentage'] == (100 if taa else 87), 'Capture quality pass differs: ' + label)

    metrics = {}
    def check(name, left, right, predicate):
        result = compare(regions[left], regions[right])
        require(predicate(result), 'Recomputed image control failed: ' + name)
        metrics[name] = result
    check('pom_off_equals_zero_relief', 'POM-Off-BC', 'POM-ZeroRelief-BC', lambda d: d['max_rgb'] <= 1 / 255 + 1e-6)
    check('pom_changes_apparent_uv', 'POM-On-BC', 'POM-Off-BC', lambda d: d['mean_absolute_rgb'] > .001 and d['max_rgb'] > .02)
    check('pom_preserves_raster_depth', 'POM-Off-Depth', 'POM-On-Depth', lambda d: d['max_rgb'] <= 1 / 255 + 1e-6)
    check('wpo_changes_actual_raster_depth', 'WPO-ZeroRelief-Depth', 'WPO-SixCm-Depth', lambda d: d['fraction_over_one_code'] > .005)
    check('vertex_source_changes_geometry', 'VS-Before-Depth', 'VS-Edited-Depth', lambda d: d['fraction_over_one_code'] > .005)
    check('vertex_zero_equals_flat_geometry', 'WPO-ZeroRelief-Depth', 'VS-Edited-Depth', lambda d: d['max_rgb'] <= 2 / 255 + 1e-6)
    check('vertex_source_recovers_geometry', 'VS-Before-Depth', 'VS-Recovered-Depth', lambda d: d['max_rgb'] <= 2 / 255 + 1e-6)
    for station in STATIONS:
        before, edited, recovered = [regions[f'Source-{stage}-{station}'] for stage in ['Before', 'Edited', 'Recovered']]
        base = float(before.mean())
        result = {'baseline_mean': base, 'edited_mean': float(edited.mean()), 'recovery_difference': compare(before, recovered)}
        require(base >= .002 and result['edited_mean'] < base * .85
                and result['recovery_difference']['mean_absolute_rgb'] < max(.0008, min(.02, base * .12)), 'Recomputed source edit/recovery failed: ' + station)
        metrics['pixel_source_edit_recovery_' + station] = result
    metrics.update(measure_uv_orientation(regions))
    basis = metrics['imported_uv_basis']
    require(basis['red_far_minus_near'] > .01 and basis['green_right_minus_left'] > .01,
            'Recomputed imported mesh UV orientation failed')
    direction = metrics['opposing_pom_ray_direction']
    require(direction['forward_red_shift'] > .001 and direction['reverse_red_shift'] < -.001,
            'Recomputed opposing POM ray direction failed')
    require(set(metrics) == set(proof['metrics']), 'Proof metric coverage differs from independent image checks')
    require(metric_matches(proof['metrics'], metrics), 'Recorded proof metrics differ from recomputed PNG metrics')
    # These controls distinguish actual depth from height/albedo visualization.
    controls = {'POM-Off-BC': {'DebugView': 1, 'PomAmount': 0, 'ReliefCm': 6},
                'POM-ZeroRelief-BC': {'DebugView': 1, 'PomAmount': 1, 'ReliefCm': 0},
                'POM-On-BC': {'DebugView': 1, 'PomAmount': 1, 'ReliefCm': 6},
                'WPO-ZeroRelief-Depth': {'DebugView': 6, 'DisplacementAmount': 1, 'ReliefCm': 0},
                'WPO-SixCm-Depth': {'DebugView': 6, 'DisplacementAmount': 1, 'ReliefCm': 6},
                'WPO-GeometricNormals': {'DebugView': 2, 'NormalStrength': 0, 'DisplacementAmount': 1, 'ReliefCm': 6},
                'UV-Basis': {'DebugView': 7, 'PomAmount': 0, 'ReliefCm': 6},
                'UV-Forward-Flat': {'DebugView': 8, 'PomAmount': 0, 'ReliefCm': 6},
                'UV-Forward-POM': {'DebugView': 8, 'PomAmount': 1, 'ReliefCm': 6},
                'UV-Reverse-Flat': {'DebugView': 8, 'PomAmount': 0, 'ReliefCm': 6},
                'UV-Reverse-POM': {'DebugView': 8, 'PomAmount': 1, 'ReliefCm': 6}}
    for label, values in controls.items():
        require(all(proof['captures'][label]['overrides'][key] == value for key, value in values.items()), 'Required control override differs: ' + label)
    for label in ['UV-Basis', 'UV-Forward-Flat', 'UV-Forward-POM', 'UV-Reverse-Flat', 'UV-Reverse-POM']:
        capture = proof['captures'][label]
        require(capture['station'] == 'pom' and capture['view'] == ('Opposite' if 'Reverse' in label else 'Oblique'),
                'UV orientation capture station/view differs: ' + label)
    for station in STATIONS:
        require(proof['captures'][f'Bounds-{station}-MaxReliefFar']['overrides']['ReliefCm'] == 12, 'Maximum relief far view missing')

    manifest_path = ROOT / 'Plugins/CkTests/Resources/CkUsf/Environment2Textures/Manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    require(set(manifest['materials']) == {'gravel'}, 'Unexpected environment source roster')
    material = manifest['materials']['gravel']
    require(material['look_id'] == 'EnvironmentGravel', 'Environment look ID differs')
    channels = {'BaseColor', 'Normal', 'Roughness', 'Height', 'AO'}
    require(channels <= set(material['maps']), 'All five environment texture channels are required')
    preparation = read('Environment1Preparation.json')
    expected = {}
    for channel in channels:
        name = 'T_EnvironmentGravelV2_' + channel
        require(material['maps'][channel]['runtime_name'] == name, 'Unexpected selected environment texture runtime family: ' + channel)
        expected['/CkFoundation/CkUsf/Textures/Environment/' + name] = channel
    require(len(preparation['textures']) == 5 and {item['path'] for item in preparation['textures']} == set(expected), 'Exactly five imported environment textures required')
    sources, assets = {}, {}
    for texture in preparation['textures']:
        channel = expected[texture['path']]
        info = material['maps'][channel]
        path = (manifest_path.parent / info['path']).resolve()
        path.relative_to(manifest_path.parent.resolve())
        require(digest(path) == info['sha256'] == texture['sha256'], 'Environment source hash differs: ' + channel)
        data = path.read_bytes()
        size = [info['width'], info['height']]
        require(data[:8] == b'\x89PNG\r\n\x1a\n' and list(struct.unpack('>II', data[16:24])) == size, 'Source PNG dimensions differ: ' + channel)
        require(channel != 'Height' or data[24] == 16, 'Height must retain its 16-bit source')
        require(channel != 'Normal' or str(info.get('normal_convention', '')).startswith('DirectX'), 'Normal source convention differs')
        resize = any(dimension & (dimension - 1) for dimension in size)
        require(texture['source_size'] == size and texture['runtime_size'] == ([1024, 1024] if resize else size)
                and texture['source_png_bit_depth'] == data[24] and texture['runtime_resize_for_streaming'] == resize
                and texture['runtime_aspect_changed'] == (resize and size[0] != size[1])
                and texture['settings_verified_after_save'] is True, 'Imported size/precision receipt differs: ' + channel)
        compression = {'BaseColor': 'TC_DEFAULT', 'Normal': 'TC_NORMALMAP', 'Height': 'TC_GRAYSCALE', 'Roughness': 'TC_MASKS', 'AO': 'TC_MASKS'}[channel]
        group = 'TEXTUREGROUP_WORLD' if channel == 'BaseColor' else 'TEXTUREGROUP_WORLD_NORMAL_MAP' if channel == 'Normal' else 'TEXTUREGROUP_WORLD_SPECULAR'
        settings = texture['saved_settings']
        require(settings['srgb'] == (channel == 'BaseColor') and '.' + compression + ':' in settings['compression_settings']
                and '.' + group + ':' in settings['lod_group'] and '.TA_WRAP:' in settings['address_x']
                and '.TA_WRAP:' in settings['address_y'] and '.TMGS_SIMPLE_AVERAGE:' in settings['mip_gen_settings']
                and settings['flip_green_channel'] is False
                and ('.RESIZE_TO_SPECIFIC_RESOLUTION:' if resize else '.NONE:') in settings['power_of_two_mode'], 'Saved environment texture semantics differ: ' + channel)
        sources[str(path.relative_to(ROOT))] = digest(path)
        assets[str(asset_file(texture['path']).relative_to(ROOT))] = digest(asset_file(texture['path']))
        for station in STATIONS:
            require(initial['environment'][station]['textures'][channel + 'Map'] == texture['path'] + '.' + texture['path'].rsplit('/', 1)[-1], 'Ground texture binding differs: ' + station + '/' + channel)

    obj_bytes, canonical = build()
    grid = preparation['grid']
    require(grid['path'] == '/CkTests/CkUsf/Showcase/SM_UsfGroundGrid', 'Unexpected owned ground mesh destination')
    obj = DIRECTORY / canonical['obj_file']
    mtl = DIRECTORY / canonical['mtl_file']
    canonical_file = obj.with_suffix('.json')
    require(obj.read_bytes() == obj_bytes and digest(obj) == canonical['sha256']
            and digest(mtl) == canonical['mtl_sha256'] and json.loads(canonical_file.read_text()) == canonical
            and grid['source_receipt'] == canonical and Path(grid['source']).resolve() == obj.resolve(), 'Grid source/canonical OBJ/MTL receipt differs')
    require(canonical['cells'] == [256, 256] and canonical['width_cm'] == 230 and canonical['height_mip'] == 2
            and canonical['slab_top_cm'] == -12.5 and canonical['slab_bottom_cm'] == -16
            and canonical['top_triangles'] == 131072 and canonical['import_scale'] == 1
            and canonical['import_axes'] == 'KEEP_XYZ_AXES', 'Canonical grid topology/basis/relief contract differs')
    validate_grid_sections(grid)
    require(grid['nanite'] is False
            and grid['positive_bounds_extension'] == [0, 0, 12] and grid['negative_bounds_extension'] == [0, 0, 12], 'Ground slot/displacement bounds contract differs')
    mesh = asset_file(grid['path'])
    require(digest(mesh) == grid['asset_sha256'], 'Saved ground mesh hash differs from preparation')
    assets[str(mesh.relative_to(ROOT))] = digest(mesh)
    master_path = '/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_EnvironmentGravel'
    master = asset_file(master_path)
    assets[str(master.relative_to(ROOT))] = digest(master)
    for station in STATIONS:
        record = initial['environment'][station]
        require(record['parent'] == master_path + '.M_CkUsf_Look_EnvironmentGravel'
                and record['mesh'] == grid['path'] + '.' + grid['path'].rsplit('/', 1)[-1]
                and record['values']['TileSizeCm'] == 230 and record['values']['HeightMip'] == 2, 'Ground master/mesh/physical scale differs')

    protected = read('Batch7-OpeningHashes.json')
    require(len(protected) == 350, 'Expected the protected 350-file opening baseline')
    for path, expected_hash in protected.items():
        require(digest(ROOT / path) == expected_hash, 'Protected source/asset changed: ' + path)
    gate = read('Batch7-Gate.exit.json')
    log_path = Path(gate['log'])
    log_path = log_path if log_path.is_absolute() else ROOT / log_path
    require(log_path.resolve() == (ROOT / 'Saved/Logs/UsfLibrary-Batch7.log').resolve(), 'Environment requires the shared Batch7 gate log')
    log = log_path.read_text(errors='replace')
    completed = datetime.datetime.fromisoformat(gate['completed_utc'].replace('Z', '+00:00')).timestamp()
    require(completed >= max((OUTPUT / 'Environment1-Proof.json').stat().st_mtime,
                             (OUTPUT / 'Environment1Preparation.json').stat().st_mtime)
            and log_path.stat().st_mtime >= (OUTPUT / 'Environment1-Proof.json').stat().st_mtime,
            'Shared generation gate must follow the restored environment proof and preparation')
    summaries = list(re.finditer(r'Total:\s*(\d+)\s+Passed:\s*(\d+)\s+Failed:\s*(\d+)\s+Skipped:\s*(\d+)\s+Contaminated:\s*(\d+)', log))
    require(gate['exit_code'] == 0 and bool(summaries) and tuple(map(int, summaries[-1].groups())) == (1, 1, 0, 0, 0)
            and any('Test Completed.' in line and 'Result={Success}' in line and 'Name={GeneratesUsableMasters}' in line for line in log.splitlines()), 'Shared focused generation gate did not pass 1/1')
    require(not re.search(r'Assertion failed|Fatal error|Ensure condition failed|Script Compile Error|Failed to compile Material', log), 'Shared gate log contains a material/startup failure')
    report = {'passed': True, 'scope': proof['scope'], 'recomputed_metrics': metrics, 'capture_sha256': images,
              'source_shader_sha256': proof['source_sha256'], 'source_map_sha256': sources, 'new_asset_sha256': assets,
              'protected_hashes_unchanged': len(protected), 'preserved_library_pairs': 42, 'preserved_environment_pairs': 2,
              'proof_sha256': digest(OUTPUT / 'Environment1-Proof.json'), 'preparation_sha256': digest(OUTPUT / 'Environment1Preparation.json'),
              'manifest_sha256': digest(manifest_path), 'grid_obj_sha256': digest(obj), 'grid_mtl_sha256': digest(mtl),
              'grid_receipt_sha256': digest(canonical_file), 'gate': gate, 'gate_log_sha256': digest(log_path), 'retained_limits': proof['limits']}
    (OUTPUT / 'Environment1-Verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'captures': len(images), 'new_assets': len(assets), 'protected': len(protected)}))


if __name__ == '__main__':
    main()
