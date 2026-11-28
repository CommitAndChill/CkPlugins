"""Offline single-opal evidence reconciliation; never contacts or launches Unreal.

Require completed final-session proof/encoding/closure records. The sole output
is OpalFire-Receipt.json; accepted seated evidence and source assets are read-only.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import json
import math
import re
import shutil
import subprocess
import uuid
import numpy as np
from PIL import Image
from opal_fire_settings import ASSET, LOOKS, TEXTURE_PREFIX
# These are pure filesystem/image helpers; the seated tool's main is guarded.
from record_optical_seated import ROOT, OUT, require, sha, root_path, output_path, read, close, pixels, mae, asset_file

SOURCE = 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/OpticalOpalFire.ush'
BODY = '/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body'
BASELINE_PIN = '50360455be1e18ea5b88794b7a924158490c693181d5637b0780b316380d7a85'
MAPS = {'OpalColor', 'OpalDomains', 'OpalDomainNormal', 'OpalPolishNormal', 'OpalRoughness'}
STAGES = ['SavedDefaults', 'FreshProof', 'LiveReload', 'MotionProof', 'EncodedMotion',
          'FinalSession', 'Preparation', 'ProtectedBaseline']


def main():
    names = {stage: 'OpalFire-'+stage+'.json' for stage in STAGES}
    input_pins = {name: sha(output_path(name)) for name in names.values()}
    documents = {stage: read(output_path(name)) for stage, name in names.items()}
    defaults, proof, reloads, motion, encoded, final, prep, protected = [documents[stage] for stage in STAGES]
    for stage in ['SavedDefaults', 'FreshProof', 'LiveReload', 'MotionProof']:
        require(documents[stage]['passed'] is True and documents[stage]['status'] == 'passed', 'Incomplete/failed stage: '+stage)
    require(input_pins[names['ProtectedBaseline']] == BASELINE_PIN and len(protected) == 62, 'Opening protection receipt changed')
    for path, pin in protected.items():
        require(sha(root_path(path)) == pin, 'Protected accepted evidence/source changed: '+path)
    require(ASSET == '/CkFoundation/CkUsf' and set(LOOKS) == {'Opal'}, 'Exact single-opal roster required')
    recipe = LOOKS['Opal']
    require((recipe['name'], recipe['source'], recipe['graph']) == ('OpticalOpalFire', 'OpticalOpalFire', 4), 'Wrong optical graph/look identity')
    require(TEXTURE_PREFIX == ASSET+'/Textures/Optical/OpalFire/T_OpalFire_', 'Wrong OpalFireV1 texture prefix')
    recipe_pin = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()
    require(prep['owner'] == 'CkUsf.OpalFirePreparation.v1' and prep['recipe_pins'] == {'Opal': recipe_pin}
            and prep['preserved_prior_definitions_and_masters'] and prep['ready_for_separate_scene_action'], 'Preparation recipe/ownership differs')
    master = ASSET+'/GeneratedLooks/M_CkUsf_Look_OpticalOpalFire.M_CkUsf_Look_OpticalOpalFire'
    definition = ASSET+'/Looks/Optical/DA_OpticalOpalFire.DA_OpticalOpalFire'
    require(prep['materials'] == prep['looks'] == {'Opal': master} and prep['definitions'] == {'Opal': definition}
            and prep['meshes'] == {'Opal': BODY+'.SM_AmberHero_Body'}, 'Prepared destinations differ')
    require(set(prep['textures']) == MAPS and {key for _, key in recipe['textures']} == MAPS
            and len(recipe['textures']) == 5 and prep['source_variant'] == 'OpalFireV1', 'Exact five OpalFireV1 textures required')
    for key, path in prep['textures'].items():
        require(path == TEXTURE_PREFIX+key+'.T_OpalFire_'+key, 'Wrong owned OpalFireV1 texture path: '+key)
    require(prep['reused_read_only_assets'] == [BODY+'.SM_AmberHero_Body'], 'Only the Amber body is reused in OpalFireV1')

    source_hashes = {path.replace('\\', '/'): pin for path, pin in prep['source_hashes'].items()}
    require(SOURCE in source_hashes, 'Preparation lacks final shader source pin')
    for path, pin in source_hashes.items():
        require(sha(root_path(path)) == pin, 'Preparation source changed; refresh final preparation: '+path)
    visited = set()

    def check_dependencies(path):
        relative = path.relative_to(ROOT).as_posix()
        require(relative in source_hashes and sha(path) == source_hashes[relative], 'Missing transitive shader pin: '+relative)
        if path in visited:
            return
        visited.add(path)
        for include in re.findall(r'^\s*#\s*include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.MULTILINE):
            require(include.startswith('/CkUsf/'), 'Unexpected shader include: '+include)
            check_dependencies(root_path('Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/'+include[len('/CkUsf/'):]))
    check_dependencies(root_path(SOURCE))
    manifest_path = 'Plugins/CkTests/Resources/CkUsf/AmberHeroV1/Manifest.json'
    maps_path = 'Plugins/CkTests/Resources/CkUsf/OpalFireV1/OpalTextures.json'
    require(manifest_path in source_hashes and maps_path in source_hashes, 'Pinned source manifests required')
    require(prep['texture_manifest'] == maps_path and prep['texture_manifest_sha256'] == source_hashes[maps_path], 'Selected OpalFireV1 manifest differs')
    geometry, maps = read(root_path(manifest_path)), read(root_path(maps_path))
    require(geometry['schema_version'] == maps['schema_version'] == 1 and set(maps['maps']) == MAPS, 'Wrong reused source schemas')
    for record in [geometry, maps]:
        require(record['generator_source'] in source_hashes
                and source_hashes[record['generator_source']] == record['generator_sha256'], 'Source generator pin missing')
    body = geometry['meshes']['Body']
    require(body['slot'] == 'Body' and body['closed_edge_manifold'] and body['consistent_edge_winding']
            and body['degenerate_triangles'] == 0 and body['signed_volume_cm3'] > 0, 'Body topology contract differs')
    for item in [body, body['mtl']]:
        path = str(Path(manifest_path).parent/item['path']).replace('\\', '/')
        require(source_hashes.get(path) == item['sha256'], 'Body OBJ/MTL pin missing')
    for item in [maps['source'], *maps['maps'].values()]:
        path = str(Path(maps_path).parent/item['path']).replace('\\', '/')
        require(source_hashes.get(path) == item['sha256'], 'Original/map source pin missing')
    require(maps['maps']['OpalColor']['sha256'] == maps['source']['sha256'], 'Original OpalFireV1 color bytes were not preserved')
    require(prep['source_provenance'] == maps['source']['provenance'], 'OpalFireV1 provenance receipt differs')
    prompt = str(Path(maps_path).parent/maps['source']['prompt_support']).replace('\\', '/')
    require(prompt in source_hashes, 'Original prompt-support file pin missing')
    require(set(prep['texture_checks']) == MAPS, 'Five saved texture-setting checks required')
    for key, info in maps['maps'].items():
        map_file = root_path(str(Path(maps_path).parent/info['path']).replace('\\', '/'))
        with Image.open(map_file) as image:
            require(image.size == (info['width'], info['height']) and image.mode == info['channels'], 'Decoded source map layout differs: '+key)
            decoded = np.asarray(image)
        require(info['bit_depth'] == 8 and info['decoded_roundtrip_verified']
                and hashlib.sha256(decoded.tobytes()).hexdigest() == info['decoded_pixel_sha256'], 'Decoded source pixels differ: '+key)
        check = prep['texture_checks'][key]
        require(check['asset'] == prep['textures'][key] and check['source_sha256'] == info['sha256']
                and check['manifest_sha256'] == source_hashes[maps_path], 'Texture source/manifest receipt differs: '+key)
        require([info['width'], info['height']] == check['source_size'] == [1254, 1254]
                and check['runtime_size'] == check['runtime_expected_size'] == [2048, 2048]
                and check['runtime_expected_mip_count'] == 12, 'Source/runtime stretch dimensions differ: '+key)
        settings = check['settings']
        require('STRETCH_TO_POWER_OF_TWO' in settings['power_of_two_mode'].upper()
                and 'TMGS_SIMPLE_AVERAGE' in settings['mip_gen_settings'].upper()
                and settings['srgb'] == str(key == 'OpalColor') and settings['flip_green_channel'] == 'False'
                and all('TA_CLAMP' in settings[field].upper() for field in ['address_x', 'address_y']), 'Texture sampling/color settings differ: '+key)
        require(('TC_NORMALMAP' if key.endswith('Normal') else 'TC_DEFAULT' if key == 'OpalColor' else 'TC_MASKS')
                in settings['compression_settings'].upper(), 'Texture compression differs: '+key)
    new_assets = {kind: dict(asset=path, file=asset_file(path).relative_to(ROOT).as_posix(), sha256=sha(asset_file(path)))
                  for kind, path in [('definition', definition), ('master', master)]}
    new_assets['textures'] = {key: dict(asset=path, file=asset_file(path).relative_to(ROOT).as_posix(), sha256=sha(asset_file(path)))
                              for key, path in prep['textures'].items()}
    reused_assets = {path: dict(file=asset_file(path).relative_to(ROOT).as_posix(), sha256=sha(asset_file(path)))
                     for path in prep['reused_read_only_assets']}
    initial = defaults['initial']
    require(initial['ok'], 'Initial state request failed')
    identity = (initial['pid'], initial['session_id'])
    require(type(identity[0]) is int and identity[0] > 0, 'Invalid owned PID')
    uuid.UUID(identity[1])
    baseline = initial['result']
    capture_hashes, capture_ids = {}, {}

    def check_state(state):
        require(state['scene_created'] and state['adaptive'] == 1 and state['subject'] == 'opal'
                and set(state['looks']) == set(state['actors']) == {'Opal'}, 'Wrong scene/profile/roster')
        look = state['looks']['Opal']
        require(look['master'] == master and look['front'] and look['compiled']['valid']
                and look['compiled']['closure_count'] == 2 and not look['compiled']['compile_errors'], 'Invalid compiled optical material')
        for field in ['master', 'mid', 'front', 'textures']:
            require(look[field] == baseline['looks']['Opal'][field], 'Object/binding identity changed: '+field)
        require(set(look['textures']) == {key for key, _ in recipe['textures']}, 'Texture parameter roster differs')
        for parameter, key in recipe['textures']:
            require(look['textures'][parameter] == prep['textures'][key], 'Wrong texture binding: '+parameter)
        require(state['geometry']['path'].replace('\\', '/') == manifest_path
                and state['geometry']['sha256'] == source_hashes[manifest_path] and state['geometry']['reused_mesh'] == BODY, 'Wrong reused geometry record')
        actor = state['actors']['Opal']
        require(actor == baseline['actors']['Opal'] and actor['mesh'] == prep['meshes']['Opal'], 'Body/transform changed')
        close(actor['scale'], [1, 1, 1], 'Body scale')
        close(actor['position'], [0, 0, 0], 'Body position')
        for key in ['exposure', 'front_layer_reflections', 'sorted_triangles_supported', 'floor', 'stand_visible']:
            require(state['rig'][key] == baseline['rig'][key], 'Unrelated staging/quality changed: '+key)

    def check_defaults(state, changes=None):
        look = state['looks']['Opal']
        scalars = dict(recipe['scalars']); scalars.update(changes or {})
        vectors = dict(recipe['vectors'])
        require(set(look['scalars']) == set(scalars) and set(look['vectors']) == set(vectors), 'Material control roster changed')
        for key, value in scalars.items():
            close(look['scalars'][key], value, 'Scalar '+key)
        for key, value in vectors.items():
            close(look['vectors'][key], value, 'Vector '+key)

    def capture(record):
        require(record['ok'] and (record['pid'], record['session_id']) == identity, 'Mixed/failed native session evidence')
        uuid.UUID(record['id'])
        path = output_path(record['capture'])
        require(path.name.startswith('OpalFire-') and path.suffix == '.png' and sha(path) == record['sha256'], 'Capture hash/path differs')
        require(record['id'] not in capture_ids and path.name not in capture_hashes, 'Duplicate capture ID/file')
        capture_ids[record['id']] = path.name; capture_hashes[path.name] = record['sha256']
        pixels(record)  # Decode every PNG and enforce its actual dimensions.
        check_state(record['state'])

    check_state(baseline)
    check_defaults(baseline)
    require(prep['compiled']['valid'] and prep['compiled']['closure_count'] == 2 and not prep['compiled']['compile_errors'], 'Preparation closure proof failed')
    require(set(defaults['captures']) == {'opal'} and proof['saved_defaults'] == dict(file=names['SavedDefaults'], sha256=input_pins[names['SavedDefaults']]), 'Fresh proof references another defaults record')
    capture(defaults['captures']['opal']); check_defaults(defaults['captures']['opal']['state'])
    require(defaults['captures']['opal']['state']['rig'] == baseline['rig'], 'Default capture rig changed')
    require(set(proof['captures']) == {'opal'} and set(reloads)-{'status', 'passed'} == {'opal'}
            and set(motion)-{'status', 'passed'} == {'opal'}, 'Unexpected proof subjects/schema')
    records = proof['captures']['opal']
    require(set(records) == {'Final', 'Repeat', 'Macro', 'FlashOff', 'FacetsFlat', 'DepthOff', 'PolishRough', 'LightsOff', 'Recovered'}, 'Nine final-control captures required')
    changes = {'FlashOff': {'FlashStrength': 0}, 'FacetsFlat': {'DomainNormalStrength': 0}, 'DepthOff': {'InternalDepthUV': 0, 'InternalLayerMix': 0}, 'PolishRough': {'CoatRoughness': .45}}
    for label, record in records.items():
        capture(record); check_defaults(record['state'], changes.get(label))
        require(record['state']['visible'] == {'Opal': True}, 'Opal was hidden during control proof')
        rig = json.loads(json.dumps(record['state']['rig']))
        if label == 'Macro':
            close(rig['camera'], [18, -8, 11], 'Macro camera'); close(rig['target'], [0, 0, 4.1], 'Macro target'); close(rig['fov'], 27, 'Macro FOV')
            for field in ['camera', 'target', 'fov']:
                rig[field] = baseline['rig'][field]
        elif label == 'LightsOff':
            require(all(light['intensity'] == 0 for light in rig['lights']) and rig['sky'] == 0
                    and rig['environment']['intensity'] == 0 and rig['environment']['reflection_brightness'] == 0, 'Lights-off controls incomplete')
            for light, original in zip(rig['lights'], baseline['rig']['lights']):
                light['intensity'] = original['intensity']
            rig['sky'] = baseline['rig']['sky']
            for field in ['intensity', 'reflection_brightness']:
                rig['environment'][field] = baseline['rig']['environment'][field]
        require(rig == baseline['rig'], 'Unexpected control rig difference: '+label)
    values = {label: mae(records['Final'], record) for label, record in records.items() if label not in ['Final', 'Macro']}
    noise = values['Repeat']; threshold = max(.1, 2*noise)
    require(all(values[label] > threshold for label in ['FlashOff', 'FacetsFlat', 'PolishRough']), 'Flash/facet/roughness effect does not exceed repeat noise')
    require(values['Recovered'] < max(1, 3*noise) and pixels(records['LightsOff']).max() == 0, 'Recovery or zero-emission isolation failed')
    for key, value in values.items():
        close(value, proof['metrics']['opal'][key], 'Reported fresh metric '+key)
    close(threshold, proof['metrics']['opal']['control_signal_threshold'], 'Control threshold differs')

    probe = reloads['opal']
    require(probe['source'].replace('\\', '/') == SOURCE
            and probe['source_original_sha256'] == probe['source_restored_sha256'] == source_hashes[SOURCE] == sha(root_path(SOURCE)), 'Shader bytes not exactly restored')
    for label in ['before', 'repeat', 'changed', 'restored']:
        capture(probe[label]); check_defaults(probe[label]['state'])
        require(probe[label]['state']['rig'] == baseline['rig'], 'Reload changed rig controls')
    reload_noise, delta, recovery = mae(probe['before'], probe['repeat']), mae(probe['before'], probe['changed']), mae(probe['before'], probe['restored'])
    require(delta > max(.1, 2*reload_noise) and recovery < max(1, 3*reload_noise, delta*.25), 'Rendered reload signal/recovery failed')
    for value, key in [(reload_noise, 'repeat_mae'), (delta, 'changed_mae'), (recovery, 'restored_mae')]:
        close(value, probe[key], 'Reported reload metric '+key)
    for key in ['changed_log', 'restored_log']:
        require('CkUsf reload complete:' in probe[key] and '[0] failed' in probe[key]
                and not any(marker in probe[key] for marker in ['CkUsf reload batch rejected:', 'Failed to compile Material', 'error X']), 'Reload completion failed')

    sequence = motion['opal']; frames = sequence['frames']
    require(sequence['frame_count'] == len(frames) == 24 and sequence['fps'] == 8, 'Twenty-four actual motion frames required')
    for record in [sequence['seed'], *frames, sequence['recovered']]:
        capture(record); check_defaults(record['state'])
        require(record['state']['visible'] == {'Opal': True}, 'Motion specimen hidden')
    seed_rig = sequence['seed']['state']['rig']
    require(seed_rig == baseline['rig'] == sequence['recovered']['state']['rig'], 'Motion controls not restored')
    target = np.asarray(seed_rig['target'], dtype=float)
    offset = np.asarray(seed_rig['camera'], dtype=float)-target
    for index, frame in enumerate(frames):
        require(output_path(frame['capture']).name == f'OpalFire-Motion-{index:03d}.png', 'Motion order/name differs')
        phase = 2*math.pi*index/24; angle = .18*math.sin(phase)
        position = target+np.array([math.cos(angle)*offset[0]-math.sin(angle)*offset[1], math.sin(angle)*offset[0]+math.cos(angle)*offset[1], offset[2]])
        rig = json.loads(json.dumps(frame['state']['rig']))
        close(rig['camera'], position, 'Motion camera'); close(rig['target'], target, 'Motion target')
        require(len(rig['lights']) == len(seed_rig['lights']) == 3, 'Three motion lights required')
        for light_index, light in enumerate(rig['lights']):
            expected = list(seed_rig['lights'][light_index]['position'])
            if light_index == 2:
                expected[0] += 2*math.sin(phase); expected[1] += 2*math.cos(phase)
            close(light['position'], expected, 'Motion light position')
            light['position'] = seed_rig['lights'][light_index]['position']
        rig['camera'], rig['target'] = seed_rig['camera'], seed_rig['target']
        require(rig == seed_rig, 'Motion changed unrelated rig controls')
    require(len({tuple(frame['state']['rig']['camera']) for frame in frames}) > 10, 'Motion camera did not move')
    close(mae(sequence['seed'], sequence['recovered']), sequence['recovered_mae'], 'Motion recovery metric')
    close(mae(frames[0], frames[-1]), sequence['first_last_mae'], 'Motion first/last metric')

    require(set(encoded) == {'opal'}, 'One encoded subject required')
    movie = encoded['opal']; hashes = [frame['sha256'] for frame in frames]
    signature = json.dumps(dict(frames=hashes, fps=8, codec='libx264', crf=18, pix_fmt='yuv420p'), sort_keys=True)
    fingerprint = hashlib.sha256(signature.encode()).hexdigest()[:16]
    require(movie['file'] == 'OpalFire-Motion-'+fingerprint+'.mp4' and movie['concat_file'] == 'OpalFire-Motion-'+fingerprint+'.ffconcat'
            and movie['input_sha256'] == hashes and movie['frame_count'] == 24 and movie['fps'] == 8 and movie['all_frames_decode_verified'], 'Encoded frame provenance differs')
    movie_path, concat = output_path(movie['file']), output_path(movie['concat_file'])
    require(sha(movie_path) == movie['sha256'], 'Video bytes changed')
    listing = ''.join("file '"+output_path(frame['capture']).as_posix().replace("'", "'\\''")+"'\n" for frame in frames)
    require(concat.read_text(encoding='utf-8') == listing, 'Encoder input list differs')
    ffmpeg, ffprobe = shutil.which('ffmpeg'), shutil.which('ffprobe')
    require(ffmpeg and ffprobe, 'Existing ffmpeg/ffprobe required to independently decode video')
    metadata = json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
        'stream=codec_name,width,height,nb_read_frames,duration,r_frame_rate', '-of', 'json', str(movie_path)], text=True))['streams'][0]
    require(metadata == {key: movie[key] for key in metadata} and metadata['codec_name'] == 'h264'
            and (metadata['width'], metadata['height']) == (1600, 1200) and int(metadata['nb_read_frames']) == 24
            and abs(float(metadata['duration'])-3) < .001 and metadata['r_frame_rate'] == '8/1', 'Actual encoded metadata differs')
    subprocess.run([ffmpeg, '-v', 'error', '-xerror', '-i', str(movie_path), '-f', 'null', '-'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require((final['editor_pid'], final['session_id']) == identity and final['editor_and_toolbox_absent_from_process_check']
            and final['clean_shutdown_marker'] and not final['error_ensure_traceback_matches'], 'Final owned studio not cleanly closed')
    log_path = output_path(final['log']); log = log_path.read_text(errors='replace')
    require(sha(log_path) == final['log_sha256'] and 'LogExit: Exiting.' in log and 'Log file closed' in log
            and not any(marker in log for marker in ['Error:', 'Ensure condition failed', 'Fatal error', 'AS_COMPILE_FAILED', 'Traceback']), 'Closed log hash/errors differ')
    require(len(capture_hashes) == len(capture_ids) == 40, 'Expected 40 native proof PNGs')
    require(all(sha(output_path(name)) == pin for name, pin in input_pins.items()), 'Input evidence changed during reconciliation')
    report = dict(schema_version=1, passed=True, status='Recorded native rendering evidence; user visual approval remains separate',
        evidence_session=dict(pid=identity[0], session_id=identity[1]), evidence_hashes=input_pins,
        capture_count=40, capture_hashes=capture_hashes, native_stats=baseline['looks']['Opal']['compiled'], recipe_pin=recipe_pin,
        source_hashes=source_hashes, protected_hashes=protected, new_assets=new_assets, reused_read_only_assets=reused_assets,
        texture_checks=prep['texture_checks'], source_variant='OpalFireV1',
        source_provenance=prep['source_provenance'], fresh_metrics=values, control_signal_threshold=threshold,
        live_reload=dict(source=SOURCE, source_restored_sha256=source_hashes[SOURCE], repeat_mae=reload_noise, changed_mae=delta, restored_mae=recovery),
        motion=dict(frame_count=24, encoded=movie, concat_sha256=sha(concat), independently_decoded_all_frames=True), final_session=final,
        depth_signal_exceeds_repeat_noise=values['DepthOff'] > threshold,
        automated_test_suite_run=False, performance_measured=False, published=False,
        limitations=['Original artistic reference and derived utility maps, not a scanned or physically calibrated opal.',
                     'Two retained native closures and visible flash/facet/polish controls do not establish spectral diffraction or volumetric optical transport.',
                     'Depth-off response is quantified without requiring it to exceed noise; no verified physical-depth claim.',
                     'Motion consists of 24 actual captured frames without interpolation; no runtime performance claim.',
                     'Process absence is established by the hashed FinalSession record; this tool never controls Unreal.'])
    destination = OUT/'OpalFire-Receipt.json'
    data = json.dumps(report, indent=2)+'\n'
    require(not destination.exists() or destination.read_text() == data, 'Preserve differing existing opal receipt')
    if not destination.exists():
        destination.write_text(data)
    print(json.dumps(dict(receipt=str(destination), passed=True, captures=40, pid=identity[0]), indent=2))


if __name__ == '__main__':
    main()
