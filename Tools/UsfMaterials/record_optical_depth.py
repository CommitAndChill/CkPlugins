"""Assemble existing optical-depth evidence only; never launch or command the studio.

Requires completed V4 FreshProof, SavedDefaults, LiveReload, MotionProof,
Preparation and a separately recorded final macro capture. No gallery/docs build.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import argparse
import hashlib
import json
import uuid
import numpy as np
from PIL import Image
from optical_depth_settings import ASSET,LOOKS

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'
GEOMETRY='Plugins/CkTests/Resources/CkUsf/OpticalDisplayDepthV4/Geometry.json'
PROTECTED={
    'Config/DefaultEngine.ini':'20d012dff0397da2198fb8af0e7b19dade2f8f204d10c54340f80c5eeb579438',
    'Saved/UsfMaterialGallery/AmberPolish-Final.png':'7c5893f5a053c7cdcfefda09223d388dc85609dab2387f031a3c18a049225b60',
    'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/AmberSpecimen.ush':'277d81292c5aefa92948810869530146d4e7307350a42be30d4b225654808402',
    'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/OpticalOpal.ush':'0b04f0867807fce2a24c6afb9dd308e8bd978b5dec125182a4694023c86d236d',
    'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/OpticalCoatedGlass.ush':'bd4386001802a315a8684a4ecf58f4b17a24c21edcc1915cdd63b834169d5682',
    'Saved/UsfMaterialGallery/OpticalPair-Opal-Final.png':'bba3d625e25d36c5bdb5e187889d49b855e1c5c57f46d8ccf867fc87a4c0a40e',
    'Saved/UsfMaterialGallery/OpticalPair-Display-Final.png':'811c9d0b6bef1d4b69690431e5f0ff2306e6506bfdb35a916896dd2918e74a0f'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    path=(OUT/name).resolve()
    assert path.parent==OUT.resolve(), 'Evidence filename must remain in gallery folder'
    return json.loads(path.read_text())


def pixels(record):
    with Image.open(record['capture']) as image:
        return np.asarray(image.convert('RGB'),dtype=np.float32)


def mae(a,b):
    x,y=pixels(a),pixels(b)
    assert x.shape==y.shape
    return float(np.abs(x-y).mean())


def expected_mesh(role):
    if role=='Opal':return '/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body'
    return '/CkTests/CkUsf/Showcase/OpticalDisplayDepth/'+('SM_OpticalDepthBevel_' if role=='GlassCover' else 'SM_OpticalDepth_')+role


def check_state(state,geometry_hash):
    assert state['scene_created'] and state['adaptive']==1
    assert set(state['looks'])==set(LOOKS)
    assert state['geometry']['path'].replace('\\','/')==GEOMETRY
    assert state['geometry']['sha256']==geometry_hash
    for role,recipe in LOOKS.items():
        look=state['looks'][role]
        master=ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name']
        assert look['master'].split('.')[0]==master,(role,'master')
        assert bool(look['front'])==(recipe['graph'] in [4,6]),(role,'native versus legacy graph front input')
        assert look['compiled']['valid'] and not look['compiled']['compile_errors'],role
        assert look['compiled']['closure_count']==(2 if role=='Opal' else 1),role
        for parameter,key in recipe['textures']:
            assert look['textures'][parameter].split('.')[0]==ASSET+'/Textures/Optical/Pair/T_OpticalPair_'+key
        actor=state['actors'][role]
        assert actor['mesh'].split('.')[0]==expected_mesh(role),(role,'mesh')
        assert np.allclose(actor['scale'],[1,1,1],atol=1e-6)
        if role!='Opal':
            assert np.allclose(actor['position'],[5.5,0,0],atol=1e-6)
            assert np.allclose([actor['rotation'][key] for key in ['pitch','yaw','roll']],[90,0,0],atol=1e-4)


def check_defaults(state):
    errors=[]
    for role,recipe in LOOKS.items():
        actual=state['looks'][role]
        for key,value in recipe['scalars']:errors.append(abs(actual['scalars'][key]-value))
        for key,value in recipe['vectors']:
            assert len(actual['vectors'][key])==len(value)
            errors.extend(abs(a-b) for a,b in zip(actual['vectors'][key],value))
    assert errors and max(errors)<1e-5, 'Recorded initial MIDs do not match current saved defaults'
    return max(errors)


def main(macro_record,editor_boots):
    names=['OpticalDepth-'+suffix+'.json' for suffix in ['FreshProof','SavedDefaults','LiveReload','MotionProof','Preparation']]
    proof,defaults,reloads,motion,preparation=[read(name) for name in names]
    macro=read(macro_record)
    geometry=json.loads((ROOT/GEOMETRY).read_text());geometry_hash=sha(ROOT/GEOMETRY)
    assert geometry['schema_version']==4 and geometry['exported_winding_sign']==1
    assert geometry['export_convention']=='CANONICAL_OUTWARD_OBJ_PER_CORNER_NORMALS_V1'
    assert preparation['source_variant']=='V4_canonical_crease_bevel' and not preparation['reversed_diagnostic']
    assert preparation['geometry_source'].replace('\\','/')==str(Path(GEOMETRY).parent).replace('\\','/')
    for role,recipe in LOOKS.items():
        assert preparation['meshes'][role]==expected_mesh(role)
        assert preparation['materials'][role].split('.')[0]==ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name']
        assert preparation['recipe_pins'][role]==hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest()
    for path,pin in preparation['source_hashes'].items():assert sha(ROOT/path)==pin,('Prepared source changed',path)
    for path,pin in PROTECTED.items():assert sha(ROOT/path)==pin,('Protected baseline changed',path)
    for prefix in ['generator','helper']:assert sha(ROOT/geometry[prefix+'_source'])==geometry[prefix+'_sha256']
    for record in geometry['source_chain']+[geometry['canonical_source']]:assert sha(ROOT/record['path'])==record['sha256']
    for record in geometry['meshes'].values():
        base=(ROOT/GEOMETRY).parent
        assert sha(base/record['path'])==record['sha256']
        assert sha(base/record['mtl']['path'])==record['mtl']['sha256']
        assert all(value>0 for value in record['component_signed_volumes_cm3'])
    initial=defaults['initial'];assert initial['ok']
    check_state(initial['result'],geometry_hash)
    default_error=check_defaults(initial['result'])
    identity=(initial['pid'],initial['session_id'])
    uuid.UUID(identity[1]);assert isinstance(identity[0],int) and identity[0]>0
    all_captures=[];captured_hashes={}
    def check_capture(record,subject,require_hash=True):
        assert record['ok'] and (record['pid'],record['session_id'])==identity,'Mixed editor session evidence'
        uuid.UUID(record['id'])
        check_state(record['state'],geometry_hash)
        assert record['state']['subject']==subject
        path=Path(record['capture']).resolve()
        assert path.parent==OUT.resolve() and path.suffix=='.png'
        digest=sha(path)
        if require_hash:assert record['sha256']==digest,('Capture changed',path.name)
        if path.name in captured_hashes:assert captured_hashes[path.name]==digest
        captured_hashes[path.name]=digest
        for role in LOOKS:
            for field in ['master','mid']:
                assert record['state']['looks'][role][field]==initial['result']['looks'][role][field],(role,field)
        all_captures.append(record)
    for subject in ['opal','display']:
        check_capture(defaults['captures'][subject],subject)
        check_defaults(defaults['captures'][subject]['state'])
    metrics={};reload_metrics={};motion_metrics={}
    for subject in ['opal','display']:
        records=proof['captures'][subject]
        required={'Final','Repeat','LightsOff','Recovered'}|({'FlashOff','DepthOff'} if subject=='opal' else {'Uncoated','CoverOff'})
        assert set(records)==required
        for record in records.values():check_capture(record,subject)
        for stage in ['Final','Repeat','Recovered']:check_defaults(records[stage]['state'])
        values={stage:mae(records['Final'],record) for stage,record in records.items() if stage!='Final'}
        assert values['Recovered']<max(.75,3*values['Repeat']),('Recovery',subject,values)
        dark=pixels(records['LightsOff']);values.update(lights_off_mean=float(dark.mean()),lights_off_max=float(dark.max()),lights_off_nonzero_pixels=int(np.any(dark>0,axis=2).sum()))
        if subject=='opal':
            assert dark.max()==0
            assert records['FlashOff']['state']['looks']['Opal']['scalars']['FlashStrength']==0
            assert all(records['DepthOff']['state']['looks']['Opal']['scalars'][key]==0 for key in ['InternalDepthUV','InternalLayerMix'])
        else:
            assert dark.max()>32 and values['lights_off_nonzero_pixels']>100
            assert records['Uncoated']['state']['looks']['GlassCover']['scalars']['CoatingStrength']==0
            assert not records['CoverOff']['state']['visible']['GlassCover']
        metrics[subject]=values
        probe=reloads[subject]
        expected_source='OpticalOpalDepth.ush' if subject=='opal' else 'OpticalDepthGlass.ush'
        source=Path(probe['source']);assert source.name==expected_source
        assert sha(ROOT/source)==probe['source_restored_sha256'],('Shader not restored',source)
        for stage in ['before','repeat','changed','restored']:check_capture(probe[stage],subject)
        noise=mae(probe['before'],probe['repeat']);changed=mae(probe['before'],probe['changed']);restored=mae(probe['before'],probe['restored'])
        assert changed>max(.1,2*noise) and restored<max(.75,3*noise,changed*.25),(subject,'Reload rendered signal')
        assert all('[0] failed' in probe[key] and 'CkUsf reload complete:' in probe[key] for key in ['changed_log','restored_log'])
        reload_metrics[subject]=dict(source=str(source),source_restored_sha256=probe['source_restored_sha256'],repeat_mae=noise,changed_mae=changed,restored_mae=restored)
        sequence=motion[subject];assert sequence['frame_count']==24 and len(sequence['frames'])==24
        for record in [sequence['seed'],*sequence['frames'],sequence['recovered']]:check_capture(record,subject)
        assert len({tuple(record['state']['rig']['camera']) for record in sequence['frames']})>12,'Motion camera did not move'
        motion_metrics[subject]=dict(frame_count=24,first_last_mae=mae(sequence['frames'][0],sequence['frames'][-1]),recovered_mae=mae(sequence['seed'],sequence['recovered']))
    check_capture(macro,'display',require_hash=False);check_defaults(macro['state'])
    video=read('OpticalDepth-EncodedMotion.json')
    for subject,record in video.items():
        assert subject in motion and record['all_frames_decode_verified'] and int(record['nb_read_frames'])==24
        assert sha(OUT/record['file'])==record['sha256']
    shutdown=read('OpticalDepth-FinalSession.json')
    assert (shutdown['editor_pid'],shutdown['session_id'])==identity
    assert shutdown['editor_and_toolbox_absent_from_process_check'] and shutdown['clean_shutdown_marker']
    assert not shutdown['error_ensure_traceback_matches'] and sha(OUT/shutdown['log'])==shutdown['log_sha256']
    report=dict(schema_version=1,status='Recorded native rendering evidence; user visual approval remains separate',
        renderer='Separate process-only Adaptive profile; five role masters with native compiled substrate statistics',
        editor_boots_reported_by_lead=editor_boots,editor_boot_count_provenance='Lead-reported total session boots, not inferred from capture count or this receipt',
        cpp_rebuild_performed=False,cpp_rebuild_provenance='Lead-reported no C++ rebuild; this assembler only inspects saved evidence',
        automated_test_suite_run=False,performance_measured=False,published=False,
        evidence_session=dict(pid=identity[0],session_id=identity[1]),
        persistent_defaults_max_error=default_error,native_stats={role:record['compiled'] for role,record in initial['result']['looks'].items()},
        geometry=dict(path=GEOMETRY,sha256=geometry_hash,glass=geometry['glass'],mesh_paths=preparation['meshes']),
        image_difference_mae_0_to_255=metrics,live_reload=reload_metrics,motion=motion_metrics,encoded_motion=video,final_session=shutdown,
        final_appearance_provenance='Captured after live shader refinements within the final fresh boot; initial persistent defaults were recorded before material overrides, not promoted as final startup appearance.',
        capture_record_count=len(all_captures),unique_png_count=len(captured_hashes),capture_hashes=captured_hashes,
        macro_record=macro_record,preserved_hashes=PROTECTED,
        evidence_hashes={name:sha(OUT/name) for name in names+[macro_record]},
        source_hashes=preparation['source_hashes'],
        limitations=['Glass uses native slab transmission and authored effective edge thickness; no traced entry/exit refraction or measured optical transport is established.',
                    'Opal gives artist-authored layered mineral appearance and view-dependent flashes; it is not a spectral diffraction or volumetric scattering solver.',
                    'Image and motion differences establish visible response in this studio, not runtime performance or repository-wide test coverage.',
                    'Control deltas and repeat-noise values are reported quantitatively; subtle differences do not imply visual approval.',
                    'Same-process identity checks describe the final evidence session; earlier diagnostic boots are represented only by the lead-reported count.'])
    destination=OUT/'OpticalDepth-Receipt.json'
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(destination),capture_records=len(all_captures),unique_pngs=len(captured_hashes),pid=identity[0],default_error=default_error,metrics=metrics),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--macro-record',default='OpticalDepth-Display-Macro-Final.json',help='Final V4 display macro capture response JSON in gallery folder')
    parser.add_argument('--editor-boots',type=int,default=6,help='Lead-reported total editor boots for this refinement')
    args=parser.parse_args()
    if args.editor_boots<1:parser.error('Positive editor boot count required')
    main(args.macro_record,args.editor_boots)
