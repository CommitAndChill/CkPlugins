"""Offline reconciliation only; never imports Unreal or talks to the studio bridge."""
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import struct

import numpy as np
from PIL import Image
from generate_woodland_grid import build, DIRECTORY

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
MANIFEST = ROOT / 'Plugins/CkTests/Resources/CkUsf/PebbleReferenceV1/Manifest-runtime-v2.json'
SHADER = ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/EnvironmentRiverPebbles.ush'
STATIONS = {'pom', 'displacement'}
IDENTITY = ['actor', 'mid', 'parent', 'mesh', 'textures', 'scale', 'colors', 'rect_intensities']


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding='utf-8-sig'))


def owned_file(base, relative):
    path = (base / relative).resolve()
    require(path.is_relative_to(base.resolve()), 'Source path escapes its owner')
    return path


def asset_file(path):
    for mount, directory in [('/CkFoundation/', 'Plugins/CkFoundation/Content'), ('/CkTests/', 'Plugins/CkTests/Content')]:
        if path.startswith(mount):
            return owned_file(ROOT / directory, path.removeprefix(mount) + '.uasset')
    raise RuntimeError('Unknown asset mount: ' + path)


def region(path):
    data = np.asarray(Image.open(path).convert('RGB'), dtype=float) / 255
    h, w = data.shape[:2]
    return data[int(h*.34):int(h*.67), int(w*.35):int(w*.65)]


def metric(a, b):
    require(a.shape == b.shape and a.size > 0, 'Capture ROI dimensions differ')
    delta = np.abs(a-b)
    return {'mean_absolute_rgb': float(delta.mean()), 'max_rgb': float(delta.max())}


def orbit_off(state):
    orbit=state.get('inspection_orbit')
    return isinstance(orbit,dict) and orbit.get('enabled') is False and orbit.get('intensity')==0 and orbit.get('target') is None


def main():
    proof, preparation = read('RiverPebbles-Proof.json'), read('RiverPebblesPreparation.json')
    require(proof.get('passed') is True and proof.get('restored') is True and not proof.get('cleanup_errors'), 'River-pebble proof did not pass and restore')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    material = manifest['materials']['pebbles']
    maps = material['maps']
    require(material['look_id'] == 'EnvironmentRiverPebbles' and manifest['schema_version'] == 1
            and set(maps) == {'BaseColor','Normal','Roughness','Height','AO'}, 'Selected river-pebble source contract differs')
    require(proof['manifest_sha256'] == preparation['manifest_sha256'] == digest(MANIFEST)
            and preparation['selected_source'] == 'PebbleReferenceV1'
            and preparation['physical_size_cm'] == [80,80] and preparation['height_mip_initial'] == 0, 'Selected preparation provenance differs')
    relief = preparation['height']['authored_relief_cm']
    require(math.isfinite(relief) and 0 < relief <= 6 and abs(relief-5.48848)<1e-5
            and abs(proof['authored_relief_cm']-relief)<1e-5, 'Authored river-pebble height differs')
    require(proof['preparation_sha256'] == digest(OUTPUT/'RiverPebblesPreparation.json'), 'Preparation changed after live proof')
    orbit_proof = read('OrbitLight-Proof.json')
    require(orbit_proof.get('passed') is True and orbit_proof.get('restored') is True
            and not orbit_proof.get('cleanup_errors'), 'Orbit-light proof must pass and restore')
    lifecycle = read('OrbitLight-LifecycleProof.json')
    require(lifecycle.get('passed') is True and lifecycle.get('restored') is True
            and not lifecycle.get('cleanup_error'), 'Actual respawn and EndPlay proof must pass and restore')
    require(proof['source_sha256'] == digest(SHADER), 'Recovered shader bytes differ')
    require(len(proof['reloads']) == 4 and all('CkUsf reload complete:' in line and '[0] failed' in line for line in proof['reloads']), 'Four successful same-object source reloads required')
    initial, final = proof['initial_state'], proof['final_state']
    require(initial['pid'] == final['pid'] and len(initial['library']) == 42 and initial['library'] == final['library'], 'Library/editor restoration differs')
    require(set(initial['environment']) == STATIONS and initial['environment'] == final['environment']
            and len({v['mid'] for v in initial['environment'].values()}) == 2, 'Two river-pebble MIDs were not restored')
    for state in [initial, final]:
        require(orbit_off(state) and state['inspection_orbit']==initial['inspection_orbit'], 'Inspection orbit did not remain disabled/restored')
        require(not state['preview_quality'] and not state['diagnostic_quantization'] and state['diagnostic_light'] is None
                and state['render_cvars']['r.AntiAliasingMethod'] == 0 and state['render_cvars']['r.ScreenPercentage'] == 87, 'Temporary presentation state remains')
    require(initial['render_cvars'] == final['render_cvars'], 'Renderer settings were not restored')

    sources, binaries = {}, {}
    def checked(path, expected):
        actual = digest(path)
        require(actual == expected, 'Source hash differs: ' + str(path))
        sources[str(path.relative_to(ROOT))] = actual
    provenance = {}
    original_path = MANIFEST.parent/'Manifest.json'
    original = json.loads(original_path.read_text())
    require(digest(original_path)==manifest['source_manifest']['sha256'], 'Original source manifest differs')
    checked(original_path, manifest['source_manifest']['sha256'])
    require(original['generator_sha256']==manifest['generator_sha256'] and original['generator_source']==manifest['generator_source'], 'Original generator provenance was replaced')
    records = list(manifest['licenses'])
    for values in manifest['metadata'].values(): records.extend(values.values())
    records.extend(material['originals'].values())
    for info in records:
        path=owned_file(MANIFEST.parent,info['path']);checked(path,info['sha256'])
        provenance[str(path.relative_to(ROOT))]=info['sha256']
    for key,hashkey in [('generator_source','generator_sha256'),('required_helper','required_helper_sha256')]:
        path=owned_file(ROOT/'Tools/UsfMaterials',Path(manifest[key]).relative_to('Tools/UsfMaterials'))
        checked(path,manifest[hashkey]);provenance[str(path.relative_to(ROOT))]=manifest[hashkey]
    derivation=manifest['runtime_color_derivation']
    recipe=owned_file(ROOT/'Tools/UsfMaterials',Path(derivation['recipe_source']).relative_to('Tools/UsfMaterials'))
    checked(recipe,derivation['recipe_sha256']);provenance[str(recipe.relative_to(ROOT))]=derivation['recipe_sha256']
    checked(owned_file(MANIFEST.parent,derivation['source_path']),derivation['source_sha256'])
    require(derivation['source_bit_depth']==16 and derivation['runtime_bit_depth']==8
            and derivation['gamma_transform'] is False and derivation['resize'] is False
            and derivation['max_encoded_error']<=.5/255, 'BC quantization contract differs')
    for channel in ['Normal','Roughness','Height','AO']:
        require(maps[channel]==original['materials']['pebbles']['maps'][channel], 'Unchanged source channel record differs: '+channel)
    require(provenance == preparation['source_provenance_sha256'], 'Preparation provenance receipt differs')
    textures = {item['path']: item for item in preparation['textures']}
    require(len(textures) == len(preparation['textures']) == 5, 'Exactly five imported textures required')
    bindings = {}
    for channel, info in maps.items():
        name = 'T_EnvironmentRiverPebblesBC8_BaseColor' if channel=='BaseColor' else 'T_EnvironmentRiverPebbles_'+channel
        require(info['runtime_name'] == name, 'Unexpected texture family')
        source = owned_file(MANIFEST.parent, info['path'])
        checked(source, info['sha256'])
        data = source.read_bytes()
        size = [info['width'], info['height']]
        require(data[:8] == b'\x89PNG\r\n\x1a\n' and list(struct.unpack('>II', data[16:24])) == size
                and size == [2048,2048] and data[24] == info['bit_depth']
                and (channel not in ['Height','Normal'] or data[24] == 16)
                and (channel != 'BaseColor' or data[24] == 8), 'Source PNG precision/dimensions differ')
        require(info['color_space'] == ('sRGB' if channel == 'BaseColor' else 'linear'), 'Source color space differs')
        path = '/CkFoundation/CkUsf/Textures/Environment/' + name
        item = textures[path]
        require(item['sha256'] == info['sha256'] and item['source_size'] == item['runtime_size'] == size
                and item['source_png_bit_depth'] == data[24] and item['settings_verified_after_save'] is True
                and item['manifest'] == ('CkTests/Resources/CkUsf/PebbleReferenceV1/Manifest-runtime-v2.json' if channel=='BaseColor' else 'CkTests/Resources/CkUsf/PebbleReferenceV1/Manifest.json'), 'Imported texture receipt differs')
        settings = item['saved_settings']
        compression = {'BaseColor': 'TC_DEFAULT', 'Normal': 'TC_NORMALMAP', 'Height': 'TC_GRAYSCALE', 'Roughness': 'TC_MASKS', 'AO': 'TC_MASKS'}[channel]
        group = 'TEXTUREGROUP_WORLD' if channel == 'BaseColor' else 'TEXTUREGROUP_WORLD_NORMAL_MAP' if channel == 'Normal' else 'TEXTUREGROUP_WORLD_SPECULAR'
        require(settings['srgb'] == (channel == 'BaseColor') and '.'+compression+':' in settings['compression_settings']
                and '.'+group+':' in settings['lod_group'] and '.TA_CLAMP:' in settings['address_x'] and '.TA_CLAMP:' in settings['address_y']
                and '.TMGS_SIMPLE_AVERAGE:' in settings['mip_gen_settings'] and '.NONE:' in settings['power_of_two_mode']
                and settings['flip_green_channel'] is False, 'Saved texture settings differ')
        binary = asset_file(path)
        binaries[str(binary.relative_to(ROOT))] = digest(binary)
        bindings[channel+'Map'] = path+'.'+name
    require(str(maps['Normal']['normal_convention']).startswith('DirectX'), 'Normal convention differs')

    obj_bytes, canonical = build()
    reused = preparation['grid']
    grid = read('WoodlandPreparation.json')['grid']
    require(reused.get('reused_without_resave') is True
            and all(reused[key] == grid[key] for key in ['path', 'source_receipt', 'asset_sha256']),
            'Reused grid must match the original imported grid receipt exactly')
    obj, mtl = DIRECTORY / canonical['obj_file'], DIRECTORY / canonical['mtl_file']
    require(obj.read_bytes() == obj_bytes and digest(obj) == canonical['sha256'] and digest(mtl) == canonical['mtl_sha256']
            and json.loads(obj.with_suffix('.json').read_text()) == canonical and grid['source_receipt'] == canonical
            and Path(grid['source']).resolve() == obj.resolve(), 'Canonical grid source differs')
    require(canonical['width_cm'] == 80 and canonical['cells'] == [256, 256] and canonical['top_triangles'] == 131072
            and canonical['slab_top_cm'] == -6.5 and canonical['slab_bottom_cm'] == -9 and canonical['import_scale'] == 1, 'Woodland grid physical contract differs')
    slots, used = grid['slots'], set()
    require(slots.count('Specimen') == slots.count('CoreBase') == 1 and bool(grid['section_material_indices']), 'Named grid sections missing')
    for indices in grid['section_material_indices'].values():
        require(len(indices) == 2 and all(type(i) is int and 0 <= i < len(slots) for i in indices)
                and {slots[i] for i in indices} == {'Specimen', 'CoreBase'}, 'Invalid LOD section material bindings')
        used.update(indices)
    unused = [name for i, name in enumerate(slots) if i not in used]
    require(unused in [[], ['defaultMat']] and grid['unused_slots'] == unused and grid['nanite'] is False
            and grid['positive_bounds_extension'] == grid['negative_bounds_extension'] == [0, 0, 6], 'Grid slot/bounds settings differ')
    require(grid['path'] == '/CkTests/CkUsf/Showcase/SM_UsfWoodlandGrid', 'Unexpected woodland grid asset')
    mesh = asset_file(grid['path'])
    require(digest(mesh) == grid['asset_sha256'], 'Saved grid binary differs')
    shared_grid_hash = digest(mesh)
    master = '/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_EnvironmentRiverPebbles'
    binary = asset_file(master)
    binaries[str(binary.relative_to(ROOT))] = digest(binary)
    for key, station in initial['environment'].items():
        values = station['values']
        require(station['parent'] == master+'.M_CkUsf_Look_EnvironmentRiverPebbles' and station['textures'] == bindings
                and station['mesh'] == grid['path']+'.SM_UsfWoodlandGrid' and station['scale'] == [1, 1, 1]
                and values['TileSizeCm'] == 80 and values['HeightMip'] == 0 and values['UVScale'] == 1
                and abs(values['ReliefCm']-relief) < 1e-5 and values['NormalStrength']==1 and values['StepCount']==64 and values['PomAmount'] == (1 if key == 'pom' else 0)
                and values['DisplacementAmount'] == (1 if key == 'displacement' else 0), 'Initial river-pebble bindings/defaults differ')

    labels = {f'{quality}-{station}-{view}' for quality in ['Native', 'TAA'] for station in STATIONS for view in ['Oblique', 'Low', 'Top']}
    labels |= {'Inspect-'+name for name in ['BaseColor', 'Normal', 'Roughness', 'Height']}
    labels |= {'POM-Off-UV', 'POM-Off-UV-Repeat', 'POM-On-UV', 'WPO-Flat-Depth', 'WPO-Flat-Depth-Repeat', 'WPO-On-Depth', 'Source-pom-Repeat', 'Vertex-Baseline', 'Vertex-Edited', 'Vertex-Recovered'}
    labels |= {f'Source-{station}-{stage}' for station in STATIONS for stage in ['Baseline', 'Edited', 'Recovered']}
    require(set(proof['captures']) == labels, 'River-pebble capture stages differ')
    images, regions = {}, {}
    current_values = {key: dict(value['values']) for key, value in initial['environment'].items()}
    for label, capture in proof['captures'].items():
        filename = 'RiverPebbles-'+label+'.png'
        require(capture['image'] == filename, 'Unexpected capture path')
        path = OUTPUT / filename
        require(path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n' and digest(path) == capture['sha256'], 'Capture bytes/hash differ: '+label)
        images[filename], regions[label] = digest(path), region(path)
        state = capture['state']
        require(orbit_off(state) and state['inspection_orbit']==initial['inspection_orbit'], 'Capture changed inspection orbit')
        require(state['pid'] == initial['pid'] and state['library'] == initial['library'] and set(state['environment']) == STATIONS, 'Capture changed library/editor')
        for key, before in initial['environment'].items():
            now = state['environment'][key]
            require(now['same_mid'] is True and now['same_master'] is True and all(now[field] == before[field] for field in IDENTITY), 'Capture changed river-pebble identity')
        taa = label.startswith('TAA-')
        require(state['render_cvars']['r.AntiAliasingMethod'] == (2 if taa else 0)
                and state['render_cvars']['r.ScreenPercentage'] == (100 if taa else 87), 'Capture quality differs')
        station = 'displacement' if label.startswith(('WPO-', 'Vertex-')) or '-displacement-' in label else 'pom'
        expected = dict(initial['environment'][station]['values'])
        if label.startswith('Inspect-'):
            expected['DebugView'] = {'BaseColor': 1, 'Normal': 2, 'Roughness': 3, 'Height': 5}[label.removeprefix('Inspect-')]
        elif label.startswith('POM-'):
            expected.update(DebugView=8, PomAmount=1 if label == 'POM-On-UV' else 0)
        elif label.startswith('WPO-'):
            expected.update(DebugView=6, DisplacementAmount=1 if label == 'WPO-On-Depth' else 0)
        elif label.startswith('Source-'):
            expected['DebugView'] = 1
        elif label.startswith('Vertex-'):
            expected['DebugView'] = 6
        current_values[station] = expected
        require(all(state['environment'][key]['values'] == values for key, values in current_values.items()),
                'Capture did not apply its required controls or changed the other station: '+label)

    metrics = {}
    def measured(name, left, right):
        result = metric(regions[left], regions[right])
        metrics[name] = result
        return result['mean_absolute_rgb']
    uv_noise = measured('UV repeat noise', 'POM-Off-UV', 'POM-Off-UV-Repeat')
    depth_noise = measured('Depth repeat noise', 'WPO-Flat-Depth', 'WPO-Flat-Depth-Repeat')
    bc_noise = measured('unchanged native repeat noise', 'Source-pom-Baseline', 'Source-pom-Repeat')
    def response(name, left, right, minimum, noise):
        effect = measured(name, left, right)
        metrics[name]['required_mean_above_repeat_noise'] = max(minimum, 3*noise)
        require(effect > max(minimum, 3*noise), 'Recomputed response below noise: '+name)
        return effect
    response('POM moves sampled UVs', 'POM-Off-UV', 'POM-On-UV', .001, uv_noise)
    response('WPO changes raster depth', 'WPO-Flat-Depth', 'WPO-On-Depth', .0005, depth_noise)
    for station in STATIONS:
        effect = response('USH sampling/color '+station, f'Source-{station}-Baseline', f'Source-{station}-Edited', .01, bc_noise)
        recovery = measured('source recovery display difference '+station, f'Source-{station}-Baseline', f'Source-{station}-Recovered')
        require(recovery < max(3*bc_noise, effect*.25), 'Pixel source recovery failed')
    effect = response('USH vertex height', 'Vertex-Baseline', 'Vertex-Edited', .0005, depth_noise)
    require(metric(regions['WPO-Flat-Depth'], regions['Vertex-Edited'])['mean_absolute_rgb'] < max(3*depth_noise, effect*.25), 'Vertex edit did not flatten geometry')
    recovery = measured('vertex recovery display difference', 'Vertex-Baseline', 'Vertex-Recovered')
    require(recovery < max(3*depth_noise, effect*.25), 'Vertex source recovery failed')
    require(set(metrics) == set(proof['metrics']) and all(set(value) == set(proof['metrics'][name])
            and all(math.isclose(v, proof['metrics'][name][k], rel_tol=1e-10, abs_tol=1e-12) for k, v in value.items())
            for name, value in metrics.items()), 'Recorded metrics differ from actual PNGs')

    protected = read('RiverPebbles-OpeningHashes.json')
    require(len(protected) == 389, 'Expected protected 389-file baseline')
    for relative, expected in protected.items():
        require(digest(owned_file(ROOT, relative)) == expected, 'Protected file changed: '+relative)
    require(len(binaries)==6, 'Exactly six active river-pebble binaries required, excluding preserved shared grid')
    require(protected.get(str(mesh.relative_to(ROOT)))==shared_grid_hash, 'Shared grid opening hash changed')
    gate = read('RiverPebbles-Gate.exit.json')
    log_path = ROOT / 'Saved/Logs/UsfLibrary-RiverPebbles.log'
    require((ROOT / gate['log']).resolve() == log_path.resolve(), 'Wrong focused gate log')
    log = log_path.read_text(errors='replace')
    completed = datetime.datetime.fromisoformat(gate['completed_utc'].replace('Z', '+00:00')).timestamp()
    require(completed >= max((OUTPUT/'RiverPebbles-Proof.json').stat().st_mtime, (OUTPUT/'RiverPebblesPreparation.json').stat().st_mtime, (OUTPUT/'OrbitLight-Proof.json').stat().st_mtime, (OUTPUT/'OrbitLight-LifecycleProof.json').stat().st_mtime)
            and log_path.stat().st_mtime >= max((OUTPUT/'RiverPebbles-Proof.json').stat().st_mtime,(OUTPUT/'OrbitLight-Proof.json').stat().st_mtime), 'Fresh gate must follow restored proof and preparation')
    summaries = list(re.finditer(r'Total:\s*(\d+)\s+Passed:\s*(\d+)\s+Failed:\s*(\d+)\s+Skipped:\s*(\d+)\s+Contaminated:\s*(\d+)', log))
    require(gate['exit_code'] == 0 and summaries, 'Fresh focused generation gate failed or has no summary')
    total,passed,failed,skipped,contaminated=map(int,summaries[-1].groups())
    require(total>0 and passed==total and failed==skipped==contaminated==0
            and any('Test Completed.' in line and 'Result={Success}' in line and 'Name={GeneratesUsableMasters}' in line for line in log.splitlines()), 'Focused generation gate did not pass all tests')
    require(not re.search(r'Assertion failed|Fatal error|Ensure condition failed|Script Compile Error|Failed to compile Material', log), 'Fresh gate log contains a failure')
    report = {'passed': True, 'scope': 'Offline selected-source, rendered controls, same-object restoration and focused generation reconciliation; artistic acceptance remains separate.',
              'proof_sha256': digest(OUTPUT/'RiverPebbles-Proof.json'), 'preparation_sha256': digest(OUTPUT/'RiverPebblesPreparation.json'),
              'manifest_sha256': digest(MANIFEST), 'source_shader_sha256': digest(SHADER), 'source_file_sha256': sources,
              'capture_sha256': images, 'recomputed_metrics': metrics, 'new_asset_binary_sha256': binaries,
              'orbit_proof_sha256':digest(OUTPUT/'OrbitLight-Proof.json'),
              'orbit_lifecycle_proof_sha256':digest(OUTPUT/'OrbitLight-LifecycleProof.json'),'shared_grid_binary_sha256':shared_grid_hash,
              'grid_obj_sha256': digest(obj), 'grid_mtl_sha256': digest(mtl), 'grid_receipt_sha256': digest(obj.with_suffix('.json')),
              'protected_hashes_unchanged': len(protected), 'preserved_library_pairs': 42, 'preserved_river_pebble_pairs': 2,
              'gate': gate, 'gate_log_sha256': digest(log_path), 'retained_limits': proof['limits']}
    (OUTPUT/'RiverPebbles-Verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'captures': len(images), 'new_asset_binaries': len(binaries), 'protected': len(protected)}))


if __name__ == '__main__':
    main()
