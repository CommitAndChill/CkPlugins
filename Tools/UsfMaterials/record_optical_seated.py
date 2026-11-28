"""Reconcile completed seated-display evidence offline; write only its final receipt.

Never launches or commands Unreal. Run after all proof, encoding and clean-session
closure records exist. Rendering evidence does not imply user visual approval.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import math
import shutil
import subprocess
import uuid
import numpy as np
from PIL import Image
from optical_seated_settings import ASSET, LOOKS
from optical_depth_settings import LOOKS as DEPTH_LOOKS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Saved/UsfMaterialGallery'
GEOMETRY = 'Plugins/CkTests/Resources/CkUsf/OpticalDisplaySeatedV5/Geometry.json'
BASELINE_PIN = '71825391ef7a7dbd81982721fb3a042d252cdc1b530f016b873bd9c55c39638a'
SOURCES = {key: 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/'+name for key, name in
           [('Glass', 'OpticalSeatedGlass.ush'), ('Aluminum', 'OpticalSeatedAluminum.ush')]}
ROLES = {'Opal', 'GlassCover', 'Panel', 'Housing', 'MetalTrim'}
NEW_ROLES = {'GlassCover', 'Housing', 'MetalTrim'}
SUFFIXES = ['SavedDefaults', 'FreshProof', 'LiveReload', 'MotionProof', 'EncodedMotion',
            'FinalSession', 'Preparation', 'ProtectedBaseline']


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def root_path(value):
    path = (ROOT/Path(value.replace('\\', '/'))).resolve()
    require(path.is_relative_to(ROOT.resolve()) and path.is_file(), 'Missing/outside source: '+str(value))
    return path


def output_path(value):
    path = Path(value)
    path = (path if path.is_absolute() else OUT/path).resolve()
    require(path.parent == OUT.resolve() and path.is_file(), 'Missing/outside evidence: '+str(value))
    return path


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'),
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+value)))


def close(actual, expected, label):
    require(np.shape(actual) == np.shape(expected) and np.all(np.isfinite(actual))
            and np.allclose(actual, expected, atol=1e-5, rtol=0), label)


def expected_mesh(role):
    if role == 'Opal':
        return '/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body'
    if role == 'Panel':
        return '/CkTests/CkUsf/Showcase/OpticalDisplayDepth/SM_OpticalDepth_Panel'
    return '/CkTests/CkUsf/Showcase/OpticalDisplaySeated/SM_OpticalSeated_'+role


def asset_file(value):
    package = value.split('.')[0]
    mount = next((name for name in ['CkFoundation', 'CkTests'] if package.startswith('/'+name+'/')), None)
    require(mount is not None, 'Unexpected asset mount: '+value)
    return root_path('Plugins/'+mount+'/Content/'+package[len(mount)+2:]+'.uasset')


def pixels(record):
    with Image.open(output_path(record['capture'])) as image:
        require(image.size == (1600, 1200), 'Unexpected native capture dimensions')
        return np.asarray(image.convert('RGB'), dtype=np.float32)


def mae(a, b):
    return float(np.abs(pixels(a)-pixels(b)).mean())


def main():
    names = ['OpticalSeated-'+suffix+'.json' for suffix in SUFFIXES]
    input_pins = {name: sha(output_path(name)) for name in names}
    documents = {suffix: read(output_path(name)) for suffix, name in zip(SUFFIXES, names)}
    defaults, proof, reloads, motion, encoded, final, prep, protected = [documents[key] for key in SUFFIXES]
    require(set(LOOKS) == ROLES and len(protected) == 13, 'Exact five roles/thirteen protected files required')
    require(sha(output_path('OpticalSeated-ProtectedBaseline.json')) == BASELINE_PIN, 'Opening protection receipt changed')
    for path, pin in protected.items():
        require(sha(root_path(path)) == pin, 'Protected baseline changed: '+path)
    geometry_path = root_path(GEOMETRY)
    geometry = read(geometry_path)
    geometry_hash = sha(geometry_path)
    require(geometry['schema_version'] == 5 and geometry['exported_winding_sign'] == 1
            and geometry['export_convention'] == 'CANONICAL_OUTWARD_OBJ_SEATED_MACHINED_V1', 'Wrong geometry version/convention')
    require(set(geometry['meshes']) == ROLES-{'Opal'}, 'Wrong geometry roles')
    require(prep['source_variant'] == 'V5_seated_machined' and prep['geometry_source'].replace('\\', '/') == str(Path(GEOMETRY).parent).replace('\\', '/'), 'Wrong preparation source')
    require(prep['reused_read_only_roles'] == ['Opal', 'Panel'] and prep['preserved_depth_assets']
            and prep['ready_for_separate_scene_action'], 'Read-only reuse not established')
    source_hashes = {}

    def source_pin(path, pin):
        file = root_path(path)
        require(sha(file) == pin, 'Source differs: '+str(path))
        source_hashes[file.relative_to(ROOT).as_posix()] = pin

    for path, pin in prep['source_hashes'].items():
        source_pin(path, pin)
    require(prep['source_hashes'].get(str(Path(GEOMETRY))) == geometry_hash
            or prep['source_hashes'].get(GEOMETRY) == geometry_hash, 'Preparation geometry pin missing')
    for prefix in ['generator', 'helper']:
        source_pin(geometry[prefix+'_source'], geometry[prefix+'_sha256'])
    for record in geometry['source_chain']+[geometry['canonical_source']]:
        source_pin(record['path'], record['sha256'])
    for role, record in geometry['meshes'].items():
        base = geometry_path.parent
        source_pin((base/record['path']).relative_to(ROOT).as_posix(), record['sha256'])
        source_pin((base/record['mtl']['path']).relative_to(ROOT).as_posix(), record['mtl']['sha256'])
        require(record['closed_edge_manifold'] and record['consistent_edge_winding']
                and record['degenerate_triangles'] == 0 and all(v > 0 for v in record['component_signed_volumes_cm3']), 'Invalid geometry topology: '+role)
        check = prep['mesh_checks'][role]
        require(check['source_variant'] == 'V5_seated_machined' and check['exported_signed_volume_cm3'] > 0
                and check['minimum_normal_winding_alignment'] > .99, 'Imported geometry check differs: '+role)

    depth_receipt = read(root_path('Saved/UsfMaterialGallery/OpticalDepth-Receipt.json'))
    depth_prep_path = root_path('Saved/UsfMaterialGallery/OpticalDepth-Preparation.json')
    require(sha(depth_prep_path) == depth_receipt['evidence_hashes']['OpticalDepth-Preparation.json'], 'Pinned depth preparation changed')
    depth_prep = read(depth_prep_path)
    new_assets, reused_assets = {}, {}
    require(set(prep['materials']) == ROLES and set(prep['definitions']) == ROLES and set(prep['meshes']) == ROLES, 'Preparation roster mismatch')
    for role, recipe in LOOKS.items():
        require(prep['recipe_pins'][role] == hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest(), 'Recipe pin differs: '+role)
        master = ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name']
        definition = ASSET+'/Looks/Optical/DA_'+recipe['name']
        require(prep['materials'][role].split('.')[0] == master and prep['definitions'][role].split('.')[0] == definition
                and prep['meshes'][role] == expected_mesh(role), 'Prepared asset identities differ: '+role)
        if role not in NEW_ROLES:
            require(recipe == DEPTH_LOOKS[role] and prep['recipe_pins'][role] == depth_prep['recipe_pins'][role]
                    and prep['materials'][role] == depth_prep['materials'][role], 'Reused role changed: '+role)
        else:
            require(recipe['name'] == {'GlassCover': 'OpticalSeatedGlass', 'Housing': 'OpticalSeatedHousing', 'MetalTrim': 'OpticalSeatedMetalTrim'}[role], 'Unexpected new material')
        bucket = new_assets if role in NEW_ROLES else reused_assets
        bucket[role] = {kind: dict(asset=value, file=asset_file(value).relative_to(ROOT).as_posix(), sha256=sha(asset_file(value)))
                        for kind, value in [('master', prep['materials'][role]), ('definition', prep['definitions'][role]), ('mesh', prep['meshes'][role])]}
        for parameter, key in recipe['textures']:
            require(prep['textures'][key].split('.')[0] == ASSET+'/Textures/Optical/Pair/T_OpticalPair_'+key, 'Texture receipt differs: '+role+'/'+parameter)
    require(len(new_assets) == 3, 'Three owned new material families required')

    initial = defaults['initial']
    require(initial['ok'], 'Initial state failed')
    identity = (initial['pid'], initial['session_id'])
    require(type(identity[0]) is int and identity[0] > 0, 'Invalid editor PID')
    uuid.UUID(identity[1])
    baseline = initial['result']
    capture_hashes = {}
    capture_ids = {}
    capture_records = 0

    def check_defaults(state, scalar_changes=None, vector_changes=None):
        for role, recipe in LOOKS.items():
            scalars = dict(recipe['scalars']); scalars.update((scalar_changes or {}).get(role, {}))
            vectors = dict(recipe['vectors']); vectors.update((vector_changes or {}).get(role, {}))
            require(set(state['looks'][role]['scalars']) == set(scalars) and set(state['looks'][role]['vectors']) == set(vectors), 'Parameter roster differs: '+role)
            for key, value in scalars.items():
                close(state['looks'][role]['scalars'][key], value, role+'/'+key)
            for key, value in vectors.items():
                close(state['looks'][role]['vectors'][key], value, role+'/'+key)

    def check_state(state):
        require(state['scene_created'] and state['adaptive'] == 1 and state['subject'] == 'display'
                and set(state['looks']) == ROLES and set(state['actors']) == ROLES, 'Wrong scene/profile/roster')
        require(state['geometry']['path'].replace('\\', '/') == GEOMETRY and state['geometry']['sha256'] == geometry_hash, 'Scene geometry pin differs')
        for role, recipe in LOOKS.items():
            look = state['looks'][role]
            require(look['master'] == prep['materials'][role] and bool(look['front']) == (recipe['graph'] in [4, 6]), 'Wrong master/native root: '+role)
            require(look['compiled']['valid'] and not look['compiled']['compile_errors']
                    and look['compiled']['closure_count'] == (2 if role == 'Opal' else 1), 'Invalid compiled closures: '+role)
            require(look['master'] == baseline['looks'][role]['master'] and look['mid'] == baseline['looks'][role]['mid'], 'Material/MID identity changed: '+role)
            for parameter, key in recipe['textures']:
                require(look['textures'][parameter] == prep['textures'][key], 'Wrong bound texture: '+role+'/'+parameter)
            actor = state['actors'][role]
            require(actor == baseline['actors'][role] and actor['mesh'].split('.')[0] == expected_mesh(role), 'Geometry/actor changed: '+role)
            close(actor['scale'], [1, 1, 1], 'Actor scale')
            if role != 'Opal':
                close(actor['position'], [5.5, 0, 0], 'Display staging')
                close([actor['rotation'][key] for key in ['pitch', 'yaw', 'roll']], [90, 0, 0], 'Display rotation')
        for key in ['exposure', 'front_layer_reflections', 'sorted_triangles_supported', 'floor', 'stand_visible']:
            require(state['rig'][key] == baseline['rig'][key], 'Capture quality/staging changed: '+key)

    check_state(baseline)
    check_defaults(baseline)
    require(set(defaults['captures']) == {'display'} and proof['saved_defaults'] == defaults, 'Fresh proof does not reference final-session defaults')

    def check_capture(record):
        nonlocal capture_records
        require(record['ok'] and (record['pid'], record['session_id']) == identity, 'Mixed/failed capture session')
        uuid.UUID(record['id'])
        check_state(record['state'])
        path = output_path(record['capture'])
        require(path.suffix == '.png' and sha(path) == record['sha256'], 'Capture hash differs: '+path.name)
        if path.name in capture_hashes:
            require(capture_hashes[path.name] == record['sha256'], 'Conflicting capture reference')
        if record['id'] in capture_ids:
            require(capture_ids[record['id']] == path.name, 'One request ID assigned to different captures')
        capture_ids[record['id']] = path.name
        capture_hashes[path.name] = record['sha256']
        pixels(record)
        capture_records += 1

    # Walk all documents so nested/repeated references cannot escape session/hash checks.
    def walk(value):
        if isinstance(value, dict):
            if 'capture' in value:
                check_capture(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    for document in documents.values():
        walk(document)
    check_defaults(defaults['captures']['display']['state'])
    require(defaults['captures']['display']['state']['rig'] == baseline['rig'], 'Saved-default capture rig changed')
    records = proof['captures']
    require(set(records) == {'Final', 'Repeat', 'Macro', 'Uncoated', 'GlassOff', 'MetalControls', 'LightsOff', 'Recovered'}, 'Incomplete fresh controls')
    noise = mae(records['Final'], records['Repeat'])
    close(noise, proof['repeat_noise_mae'], 'Fresh repeat metric differs')
    metrics = {key: mae(records['Final'], records[key]) for key in ['Uncoated', 'GlassOff', 'MetalControls', 'Recovered']}
    for key, value in metrics.items():
        close(value, proof['metrics'][key], 'Fresh metric differs: '+key)
    require(all(metrics[key] > max(noise*3, .05) for key in ['GlassOff', 'MetalControls'])
            and metrics['Recovered'] < max(noise*3, .15), 'Fresh signal/recovery failed')
    region = proof['bevel_region']
    require(region['bounds_xyxy'] == [680, 570, 1490, 810], 'Unexpected coating-proof ROI')
    bevel = pixels(records['Final'])[570:810, 680:1490]
    bevel_noise = float(np.abs(bevel-pixels(records['Repeat'])[570:810, 680:1490]).mean())
    bevel_change = float(np.abs(bevel-pixels(records['Uncoated'])[570:810, 680:1490]).mean())
    close(bevel_noise, region['repeat_noise_mae'], 'Bevel repeat-noise metric')
    close(bevel_change, region['uncoated_mae'], 'Bevel uncoated metric')
    require(bevel_change > max(bevel_noise*3, .05), 'Localized coating signal failed')
    for key in ['Final', 'Repeat', 'Macro', 'GlassOff', 'Recovered']:
        check_defaults(records[key]['state'])
    check_defaults(records['Uncoated']['state'], {'GlassCover': {'BevelFilmStrength': 0}})
    check_defaults(records['LightsOff']['state'], {'Panel': {'EmissionStrength': 0}})
    changes = {role: dict(UVScale=2.7, UVRotation=70, NormalStrength=.7, RoughnessBias=.35) for role in ['Housing', 'MetalTrim']}
    check_defaults(records['MetalControls']['state'], changes, {role: {'TintColor': [.20, .36, .58, 1]} for role in changes})
    require(not records['GlassOff']['state']['visible']['GlassCover'], 'Cover visibility control missing')
    for key, record in records.items():
        require(record['state']['visible'] == {role: role != 'Opal' and (role != 'GlassCover' or key != 'GlassOff') for role in ROLES}, 'Wrong control visibility: '+key)
        rig = json.loads(json.dumps(record['state']['rig']))
        if key == 'Macro':
            for field in ['camera', 'target', 'fov']:
                rig[field] = baseline['rig'][field]
        elif key == 'LightsOff':
            for light, original in zip(rig['lights'], baseline['rig']['lights']):
                light['intensity'] = original['intensity']
            rig['sky'] = baseline['rig']['sky']
            for field in ['intensity', 'reflection_brightness']:
                rig['environment'][field] = baseline['rig']['environment'][field]
        require(rig == baseline['rig'], 'Unrelated fresh-control rig changes: '+key)
    dark = records['LightsOff']
    require(all(light['intensity'] == 0 for light in dark['state']['rig']['lights'])
            and dark['state']['rig']['sky'] == 0 and dark['state']['rig']['environment']['intensity'] == 0
            and dark['state']['rig']['environment']['reflection_brightness'] == 0 and pixels(dark).max() <= 1, 'Lights-off isolation failed')
    close(float(pixels(dark).max()), proof['lights_off_max_8bit'], 'Black-frame metric differs')
    require(records['Final']['state']['rig'] == records['Recovered']['state']['rig'], 'Rig not recovered')
    close(records['Macro']['state']['rig']['camera'], [20, -25, 9], 'Macro camera')
    close(records['Macro']['state']['rig']['target'], [4, -6, 2.3], 'Macro target')
    close(records['Macro']['state']['rig']['fov'], 23, 'Macro FOV')

    require(set(reloads) == set(SOURCES), 'Both source reload probes required')
    reload_metrics = {}
    for role, relative in SOURCES.items():
        probe = reloads[role]
        pin = sha(root_path(relative))
        require(probe['restored_exactly'] and probe['original_sha256'] == pin
                and proof['sources'][Path(relative).name] == pin, 'Source restoration failed: '+role)
        source_hashes[relative] = pin
        for stage in ['before', 'changed', 'restored']:
            check_defaults(probe[stage]['state'])
            require(probe[stage]['state']['rig'] == baseline['rig'], 'Reload changed capture rig: '+role+'/'+stage)
        change, restore = mae(probe['before'], probe['changed']), mae(probe['before'], probe['restored'])
        close(change, probe['change_mae'], 'Reload change metric')
        close(restore, probe['restore_mae'], 'Reload recovery metric')
        require(change > max(restore*3, .05), 'Reload signal/recovery failed: '+role)
        for key in ['reload_log', 'restore_log']:
            require('CkUsf reload complete:' in probe[key] and '[0] failed' in probe[key]
                    and 'CkUsf reload batch rejected:' not in probe[key], 'Reload acknowledgment failed')
        reload_metrics[role] = dict(source=relative, sha256=pin, change_mae=change, restore_mae=restore)

    require(set(motion) == {'display'} and set(encoded) == {'display'}, 'Exact display motion required')
    frames = motion['display']['frames']
    require(len(frames) == 24 and motion['display']['fps'] == 8 and len({frame['sha256'] for frame in frames}) == 24, 'Twenty-four distinct native frames required')
    for index, frame in enumerate(frames):
        require(output_path(frame['capture']).name == f'OpticalSeated-Display-Motion-{index:03d}.png', 'Motion frame order/name differs')
        check_defaults(frame['state'])
        phase = 2*math.pi*index/24
        view = math.atan2(-27, 17)+.24*math.sin(phase)
        radius = math.hypot(17, 27)
        close(frame['state']['rig']['camera'], [radius*math.cos(view), radius*math.sin(view), 13], 'Motion camera')
        for light, position, intensity in zip(frame['state']['rig']['lights'], [[-4, -12, 1], [8, -3, 1], [16*math.cos(phase), 16*math.sin(phase), 8]], [.0025, .0025, .001]):
            close(light['position'], position, 'Motion light position')
            close(light['intensity'], intensity, 'Motion light intensity')
        rig = json.loads(json.dumps(frame['state']['rig']))
        require(len(rig['lights']) == len(baseline['rig']['lights']) == 3, 'Three motion lights required')
        rig['camera'] = baseline['rig']['camera']
        for light, original in zip(rig['lights'], baseline['rig']['lights']):
            light['position'], light['intensity'] = original['position'], original['intensity']
        require(rig == baseline['rig'], 'Motion changed unrelated rig controls')
    movie = encoded['display']; movie_path = output_path(movie['file'])
    require(movie['file'] == 'OpticalSeated-Display-Orbit.mp4' and sha(movie_path) == movie['sha256']
            and movie['all_frames_decode_verified'] and int(movie['nb_read_frames']) == 24 and movie['fps'] == 8, 'Encoded video receipt differs')
    ffmpeg, ffprobe = shutil.which('ffmpeg'), shutil.which('ffprobe')
    require(ffmpeg and ffprobe, 'Existing ffmpeg/ffprobe required for independent decode verification')
    metadata = json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-count_frames', '-select_streams', 'v:0',
        '-show_entries', 'stream=codec_name,width,height,nb_read_frames,duration', '-of', 'json', str(movie_path)], text=True))['streams'][0]
    require(metadata['codec_name'] == movie['codec_name'] == 'h264' and metadata['width'] == movie['width'] == 1600
            and metadata['height'] == movie['height'] == 1200 and int(metadata['nb_read_frames']) == 24
            and abs(float(metadata['duration'])-3) < .001, 'Actual encoded metadata differs')
    require(metadata == {key: movie[key] for key in metadata}, 'Recorded video metadata differs from actual stream')
    subprocess.run([ffmpeg, '-v', 'error', '-xerror', '-i', str(movie_path), '-f', 'null', '-'],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require((final['editor_pid'], final['session_id']) == identity and final['editor_and_toolbox_absent_from_process_check']
            and final['clean_shutdown_marker'] and not final['error_ensure_traceback_matches'], 'Final owned session was not cleanly closed')
    log_path = output_path(final['log'])
    require(sha(log_path) == final['log_sha256'], 'Closed log hash differs')
    log = log_path.read_text(errors='replace')
    require('LogExit: Exiting.' in log and 'Log file closed' in log
            and not any(marker in log for marker in ['Error:', 'Ensure condition failed', 'Fatal error', 'AS_COMPILE_FAILED', 'Traceback']), 'Closed log has errors or missing shutdown')
    require(len(capture_hashes) == len(capture_ids) == 39, 'Expected 39 unique saved-default/control/reload/motion captures')
    require(all(sha(output_path(name)) == pin for name, pin in input_pins.items()), 'Evidence changed during reconciliation')
    report = dict(schema_version=1, passed=True, status='Recorded native rendering evidence; visual approval remains separate',
        evidence_session=dict(pid=identity[0], session_id=identity[1]), evidence_hashes=input_pins,
        capture_reference_count=capture_records, unique_png_count=len(capture_hashes), capture_hashes=capture_hashes,
        native_stats={role: baseline['looks'][role]['compiled'] for role in ROLES}, recipe_pins=prep['recipe_pins'],
        protected_hashes=protected, source_hashes=source_hashes, new_assets=new_assets, reused_read_only_assets=reused_assets,
        geometry=dict(path=GEOMETRY, sha256=geometry_hash, glass=geometry['glass'], seat=geometry['seat'], meshes=prep['meshes']),
        repeat_noise_mae=noise, fresh_metrics=metrics, bevel_region=region, live_reload=reload_metrics,
        motion=dict(frame_count=24, fps=8, encoded=movie, independently_decoded_all_frames=True), final_session=final,
        automated_test_suite_run=False, performance_measured=False, published=False,
        limitations=['Native thin-sheet optical approximation; no traced entry/exit or measured optical transport claim.',
                     'Phase-sampled native frames and visible control deltas are rendering evidence, not performance or visual approval.',
                     'Process absence is established by the hashed FinalSession record; this tool never controls Unreal.'])
    destination = OUT/'OpticalSeated-Receipt.json'
    destination.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(receipt=str(destination), passed=True, unique_pngs=len(capture_hashes), pid=identity[0]), indent=2))


if __name__ == '__main__':
    main()
