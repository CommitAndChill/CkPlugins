"""Reconcile completed native opal-glint evidence offline; write only its final receipt."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib,json,math,re,shutil,subprocess,uuid
import numpy as np
from PIL import Image
from opal_glints_settings import ASSET,LOOKS,TEXTURE_PREFIX
from record_optical_seated import ROOT,OUT,require,sha,root_path,output_path,read,close,pixels,mae,asset_file
SOURCE='Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/OpticalOpalGlints.ush'
PRIMARY_BACKEND='AutomationLibrary.take_high_res_screenshot primary editor viewport'
BASELINE_PIN='e1aa10e7becc83a136dc8c4a7caf0ead656a23cdc4d04c3389fbd08599f2ef11'
STAGES=['Preparation','ProtectedBaseline','SavedDefaults','FreshProof','LiveReload','MotionProof','EncodedMotion','FinalSession']

def native(stats):
    require(stats['valid'] and stats['closure_count']==2 and not stats['compile_errors'] and stats['has_glint'] and stats['complex_special'],'Native two-closure glint/complex-special compilation required')
    require(type(stats['material_type']) is int and type(stats['bsdf_features']) is int,'Native resource type/feature fields required')

def main():
    names={stage:'OpalGlints-'+stage+'.json' for stage in STAGES}
    pins={name:sha(output_path(name)) for name in names.values()}
    docs={stage:read(output_path(name)) for stage,name in names.items()}
    prep,protected,defaults,proof,reload,motion,encoded,final=[docs[s] for s in STAGES]
    for stage in ['SavedDefaults','FreshProof','LiveReload','MotionProof']:
        require(docs[stage]['passed'] is True and docs[stage]['status']=='passed','Incomplete stage: '+stage)
    require(pins[names['ProtectedBaseline']]==BASELINE_PIN,'Opening baseline receipt changed')
    require(protected['prior_baseline']=='OpalFire-ProtectedBaseline.json' and sha(output_path(protected['prior_baseline']))==protected['prior_sha256'],'Prior baseline receipt differs')
    allowed=['Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Common.ush']
    require(protected['approved_shared_changes']==allowed and len(protected['files'])==61,'Protected files/authorized exclusion differ')
    require(not set(allowed)&{p.replace('\\','/') for p in protected['files']},'Authorized shared change must be excluded explicitly')
    for path,pin in protected['files'].items():require(sha(root_path(path))==pin,'Protected asset/source/evidence changed: '+path)
    recipe=LOOKS['Opal'];recipe_pin=hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest()
    require(ASSET=='/CkFoundation/CkUsf' and set(LOOKS)=={'Opal'} and (recipe['name'],recipe['source'],recipe['graph'])==('OpticalOpalGlints','OpticalOpalGlints',4),'Unexpected recipe identity')
    require(TEXTURE_PREFIX==ASSET+'/Textures/Optical/OpalPolish/T_OpalPolish_','Only approved Polish texture mount allowed')
    master=ASSET+'/GeneratedLooks/M_CkUsf_Look_OpticalOpalGlints.M_CkUsf_Look_OpticalOpalGlints'
    definition=ASSET+'/Looks/Optical/DA_OpticalOpalGlints.DA_OpticalOpalGlints'
    require(prep['owner']=='CkUsf.OpalGlintsPreparation.v1' and prep['recipe_pins']=={'Opal':recipe_pin} and prep['materials']==prep['looks']=={'Opal':master} and prep['definitions']=={'Opal':definition},'Preparation identity/pin differs')
    require(prep['preserved_prior_definitions_and_masters'] and prep['ready_for_separate_scene_action'] and prep['source_variant']=='OpalPolishV2_read_only','Read-only preparation contract differs')
    native(prep['compiled'])
    sources={path.replace('\\','/'):pin for path,pin in prep['source_hashes'].items()}
    require(SOURCE in sources,'Final shader pin missing')
    for path,pin in sources.items():require(sha(root_path(path))==pin,'Final preparation source changed: '+path)
    visited=set()
    def dependencies(path):
        relative=path.relative_to(ROOT).as_posix();require(sources.get(relative)==sha(path),'Transitive shader pin missing: '+relative)
        if path in visited:return
        visited.add(path)
        for include in re.findall(r'^\s*#\s*include\s+"([^"]+)"',path.read_text(encoding='utf-8-sig'),re.M):
            require(include.startswith('/CkUsf/'),'Unexpected include mount');dependencies(root_path('Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/'+include[7:]))
    dependencies(root_path(SOURCE))
    maps_path='Plugins/CkTests/Resources/CkUsf/OpalPolishV2/OpalTextures.json';maps=read(root_path(maps_path))
    require(prep['texture_manifest']==maps_path and prep['texture_manifest_sha256']==sources[maps_path] and prep['source_provenance']==maps['source']['provenance'],'Approved source manifest/provenance differs')
    require(set(prep['textures'])==set(prep['texture_checks'])==set(maps['maps'])=={key for _,key in recipe['textures']} and len(prep['textures'])==5,'Exact five approved texture channels required')
    expected_reuse=set(prep['meshes'].values())|set(prep['textures'].values())
    require(set(prep['reused_read_only_assets'])==expected_reuse and len(expected_reuse)==6,'Five textures and Amber body must be reused read-only')
    require(prep['meshes']=={'Opal':'/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body.SM_AmberHero_Body'},'Unexpected geometry')
    require(sources[maps['generator_source']]==maps['generator_sha256'] and maps['source']['sha256']==maps['maps']['OpalColor']['sha256'],'Generator/original artwork pin differs')
    for item in [maps['source'],*maps['maps'].values()]:require(sources[(Path(maps_path).parent/item['path']).as_posix()]==item['sha256'],'Map/source provenance pin missing')
    for key,info in maps['maps'].items():
        path=prep['textures'][key];check=prep['texture_checks'][key]
        require(path==TEXTURE_PREFIX+key+'.T_OpalPolish_'+key and check['asset']==path and check['source_sha256']==info['sha256'] and check['manifest_sha256']==sources[maps_path],'Texture source binding differs')
        with Image.open(root_path((Path(maps_path).parent/info['path']).as_posix())) as image:
            require(image.size==(1254,1254) and image.mode==info['channels'] and hashlib.sha256(np.asarray(image).tobytes()).hexdigest()==info['decoded_pixel_sha256'],'Decoded approved map differs')
        require(info['bit_depth']==8 and info['decoded_roundtrip_verified'] and check['source_size']==[1254,1254] and check['runtime_size']==check['runtime_expected_size']==[2048,2048] and check['runtime_expected_mip_count']==12,'Approved runtime texture dimensions differ')
        settings=check['settings'];compression='TC_NORMALMAP' if key.endswith('Normal') else 'TC_DEFAULT' if key=='OpalColor' else 'TC_MASKS'
        require(compression in settings['compression_settings'].upper() and settings['srgb']==str(key=='OpalColor') and settings['flip_green_channel']=='False' and 'STRETCH_TO_POWER_OF_TWO' in settings['power_of_two_mode'].upper() and 'TMGS_SIMPLE_AVERAGE' in settings['mip_gen_settings'].upper() and all('TA_CLAMP' in settings[f].upper() for f in ['address_x','address_y']),'Approved texture sampling settings differ')
        relative=asset_file(path).relative_to(ROOT).as_posix();require(protected['files'][relative]==sha(asset_file(path)),'Reused texture bytes changed')
    initial=defaults['initial'];identity=(initial['pid'],initial['session_id']);uuid.UUID(identity[1]);baseline=initial['result']
    require(initial['ok'] and type(identity[0]) is int and identity[0]>0,'Invalid initial owned session')
    def state(s):
        look=s['looks']['Opal'];native(look['compiled'])
        require(s['scene_created'] and s['adaptive']==s['native_glints']==1 and s['subject']=='opal' and s['visible']=={'Opal':True} and set(s['looks'])==set(s['actors'])=={'Opal'},'Invalid native studio state')
        require(look['master']==master and look['front'] and all(look[f]==baseline['looks']['Opal'][f] for f in ['master','mid','front','textures']),'Material/MID bindings changed')
        require(look['textures']=={parameter:prep['textures'][key] for parameter,key in recipe['textures']} and s['actors']==baseline['actors'] and s['actors']['Opal']['mesh']==prep['meshes']['Opal'],'Texture/body identity changed')
        require(s['geometry']['sha256']==sources[s['geometry']['path'].replace('\\','/')],'Geometry provenance changed')
    def parameters(s,changes=None):
        look=s['looks']['Opal'];scalars=dict(recipe['scalars']);scalars.update(changes or {})
        require(set(look['scalars'])==set(scalars) and set(look['vectors'])=={k for k,_ in recipe['vectors']},'Parameter roster differs')
        for key,value in scalars.items():close(look['scalars'][key],value,'Scalar '+key)
        for key,value in recipe['vectors']:close(look['vectors'][key],value,'Vector '+key)
    captures={};ids=set();primary_cameras=set()
    def capture(record,changes=None):
        require(record['ok'] and (record['pid'],record['session_id'])==identity,'Mixed or failed session evidence');uuid.UUID(record['id'])
        require(record.get('capture_backend')==PRIMARY_BACKEND and record.get('native_task_done') is True and record.get('native_task_valid') is True,'Completed native primary screenshot required')
        camera=record.get('primary_camera');require(isinstance(camera,str) and ':PersistentLevel.' in camera,'Native primary CameraActor path required');primary_cameras.add(camera)
        require(len(primary_cameras)==1,'Native primary CameraActor identity changed')
        path=output_path(record['capture']);require(path.name.startswith('OpalGlints-') and path.suffix=='.png' and sha(path)==record['sha256'] and path.name not in captures and record['id'] not in ids,'Capture hash/ownership/uniqueness differs')
        captures[path.name]=record['sha256'];ids.add(record['id']);pixels(record);state(record['state']);parameters(record['state'],changes)
    state(baseline);parameters(baseline);capture(defaults['captures']['opal'])
    require(defaults['captures']['opal']['state']['rig']==baseline['rig'] and proof['saved_defaults']==dict(file=names['SavedDefaults'],sha256=pins[names['SavedDefaults']]),'Saved defaults linkage differs')
    records=proof['captures']['opal'];changes={'GlintsOff':{'GlintDensity':1},'FlashOff':{'FlashStrength':0},'DepthOff':{'InternalDepthUV':0,'InternalLayerMix':0},'PolishRough':{'CoatRoughness':.45}}
    require(set(records)=={'Final','Repeat','Macro','GlintsOff','FlashOff','DepthOff','PolishRough','LightsOff','Recovered'},'Nine final-control captures required')
    for label,record in records.items():
        capture(record,changes.get(label));rig=json.loads(json.dumps(record['state']['rig']))
        if label=='Macro':
            close(rig['camera'],[18,-8,11],'Macro camera');close(rig['target'],[0,0,4.1],'Macro target');close(rig['fov'],27,'Macro FOV')
            for key in ['camera','target','fov']:rig[key]=baseline['rig'][key]
        if label=='LightsOff':
            require(all(light['intensity']==0 for light in rig['lights']) and rig['sky']==rig['environment']['intensity']==rig['environment']['reflection_brightness']==0,'Lights-off isolation incomplete')
            for light,old in zip(rig['lights'],baseline['rig']['lights']):light['intensity']=old['intensity']
            rig['sky']=baseline['rig']['sky']
            for key in ['intensity','reflection_brightness']:rig['environment'][key]=baseline['rig']['environment'][key]
        require(rig==baseline['rig'],'Unexpected final rig change: '+label)
    values={label:mae(records['Final'],r) for label,r in records.items() if label not in ['Final','Macro']};noise=values['Repeat'];threshold=max(.1,2*noise);dark=pixels(records['LightsOff'])
    require(all(values[k]>threshold for k in ['GlintsOff','FlashOff','PolishRough']) and values['Recovered']<max(1,3*noise) and dark.max()==0,'Endpoint signal/recovery/black isolation failed')
    metrics=proof['metrics']['opal']
    for key,value in {**values,'control_signal_threshold':threshold,'lights_off_max':float(dark.max()),'lights_off_mean':float(dark.mean()),'lights_off_nonzero_pixels':int(np.any(dark>0,axis=2).sum())}.items():close(value,metrics[key],'Final metric '+key)
    require(metrics['control_exceeds_repeat_noise']=={k:values[k]>threshold for k in ['GlintsOff','FlashOff','DepthOff','PolishRough']},'Reported endpoint decisions differ')
    require(root_path(SOURCE).read_bytes().count(b'    O.BGlintValue = lerp(1.0,clamp(GlintDensity,0.0,1.0),Coverage);')==1,'Exact native glint reload probe anchor missing')
    probe=reload['opal'];require(probe['source'].replace('\\','/')==SOURCE and probe['source_original_sha256']==probe['source_restored_sha256']==sources[SOURCE],'Live shader bytes not exactly restored')
    for label in ['before','repeat','changed','restored']:capture(probe[label]);require(probe[label]['state']['rig']==baseline['rig'],'Reload changed rig')
    rn,delta,recovery=[mae(probe['before'],probe[k]) for k in ['repeat','changed','restored']]
    require(delta>max(.1,2*rn) and recovery<max(1,3*rn,delta*.25),'Live reload signal/recovery failed')
    for key,value in [('repeat_mae',rn),('changed_mae',delta),('restored_mae',recovery)]:close(value,probe[key],'Reload '+key)
    for key in ['changed_log','restored_log']:require('CkUsf reload complete:' in probe[key] and '[0] failed' in probe[key] and not any(m in probe[key] for m in ['rejected:','Failed to compile Material','error X']),'Reload completion failed')
    sequence=motion['opal'];frames=sequence['frames'];require(sequence['frame_count']==len(frames)==24 and sequence['fps']==8,'24 actual motion frames required')
    for record in [sequence['seed'],*frames,sequence['recovered']]:capture(record)
    rig=sequence['seed']['state']['rig'];require(rig==baseline['rig']==sequence['recovered']['state']['rig'],'Motion rig not restored')
    target=np.asarray(rig['target']);offset=np.asarray(rig['camera'])-target
    for index,frame in enumerate(frames):
        require(output_path(frame['capture']).name==f'OpalGlints-Motion-{index:03d}.png','Motion frame ordering differs');phase=2*math.pi*index/24;angle=.18*math.sin(phase);actual=json.loads(json.dumps(frame['state']['rig']))
        close(actual['camera'],target+np.array([math.cos(angle)*offset[0]-math.sin(angle)*offset[1],math.sin(angle)*offset[0]+math.cos(angle)*offset[1],offset[2]]),'Motion camera');actual['camera']=rig['camera']
        for i,light in enumerate(actual['lights']):
            expected=list(rig['lights'][i]['position'])
            if i==2:expected[0]+=2*math.sin(phase);expected[1]+=2*math.cos(phase)
            close(light['position'],expected,'Motion light');light['position']=rig['lights'][i]['position']
        require(actual==rig,'Motion altered unrelated rig state')
    require(len({tuple(r['state']['rig']['camera']) for r in frames})>10,'Motion camera did not move')
    close(mae(sequence['seed'],sequence['recovered']),sequence['recovered_mae'],'Motion recovered MAE');close(mae(frames[0],frames[-1]),sequence['first_last_mae'],'Motion first-last MAE')
    movie=encoded['opal'];hashes=[r['sha256'] for r in frames];fingerprint=hashlib.sha256(json.dumps(dict(frames=hashes,fps=8,codec='libx264',crf=18,pix_fmt='yuv420p'),sort_keys=True).encode()).hexdigest()[:16]
    require(movie['file']=='OpalGlints-Motion-'+fingerprint+'.mp4' and movie['concat_file']=='OpalGlints-Motion-'+fingerprint+'.ffconcat' and movie['input_sha256']==hashes and movie['frame_count']==24 and movie['fps']==8 and movie['all_frames_decode_verified'],'Movie provenance differs')
    video=output_path(movie['file']);require(sha(video)==movie['sha256'],'Movie hash differs')
    listing=''.join("file '"+output_path(r['capture']).as_posix().replace("'","'\\''")+"'\n" for r in frames);require(output_path(movie['concat_file']).read_text(encoding='utf-8')==listing,'Encoder input list differs')
    ffmpeg,ffprobe=shutil.which('ffmpeg'),shutil.which('ffprobe');require(ffmpeg and ffprobe,'Existing video tools required')
    metadata=json.loads(subprocess.check_output([ffprobe,'-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=codec_name,width,height,nb_read_frames,duration,r_frame_rate','-of','json',str(video)],text=True))['streams'][0]
    require(metadata=={k:movie[k] for k in metadata} and metadata['codec_name']=='h264' and (metadata['width'],metadata['height'])==(1600,1200) and int(metadata['nb_read_frames'])==24 and metadata['r_frame_rate']=='8/1' and abs(float(metadata['duration'])-3)<.001,'Independent video metadata differs')
    subprocess.run([ffmpeg,'-v','error','-xerror','-i',str(video),'-f','null','-'],check=True,capture_output=True)
    require((final['editor_pid'],final['session_id'])==identity and final['editor_and_toolbox_absent_from_process_check'] and final['clean_shutdown_marker'] and not final['error_ensure_traceback_matches'],'Final studio closure failed')
    log=output_path(final['log']);text=log.read_text(errors='replace');require(sha(log)==final['log_sha256'] and 'LogExit: Exiting.' in text and 'Log file closed' in text and not any(x in text for x in ['Error:','Ensure condition failed','Fatal error','AS_COMPILE_FAILED','Traceback']),'Final native log differs/errors present')
    gates={}
    for kind in ['Adaptive','Blendable']:
        name='OpalGlints-'+kind+'Gate';process=output_path(name+'-process.json');result=read(process);gate_log=root_path('Saved/Logs/'+name+'.log');text=gate_log.read_text(errors='replace')
        require(result['profile']==name and result['exit_code']==0 and result['pid']>0 and result['completed_utc'],'Gate process failed: '+kind)
        summary=text.rsplit('Test summary',1);require(len(summary)==2,'Missing gate test summary')
        counts={key:int(re.search(r'\b'+key+r'\s*:\s*(\d+)',summary[1]).group(1)) for key in ['Total','Passed','Failed','Skipped','Contaminated']}
        require(counts['Total']==counts['Passed'] and counts['Total']>0 and counts['Failed']==counts['Skipped']==counts['Contaminated']==0,'Gate summary failed')
        require(not any(x in text for x in ['Ensure condition failed','Fatal error','AS_COMPILE_FAILED']),'Gate native errors present')
        gates[kind]=dict(process=result,process_sha256=sha(process),log=gate_log.relative_to(ROOT).as_posix(),log_sha256=sha(gate_log),counts=counts)
    require(len(captures)==len(ids)==40 and all(sha(output_path(name))==pin for name,pin in pins.items()),'Evidence count or input hashes changed during reconciliation')
    require(all(sha(root_path(path))==pin for path,pin in {**sources,**protected['files']}.items()),'Source/protected bytes changed during reconciliation')
    snapshots={path.relative_to(ROOT).as_posix():sha(path) for folder in ['Plugins/CkFoundation/Source/CkUsf','Plugins/CkFoundation/Source/CkUsfEditor'] if (ROOT/folder).is_dir() for path in (ROOT/folder).rglob('*') if path.is_file() and path.suffix in ['.h','.cpp','.cs']}
    assets={kind:dict(asset=path,file=asset_file(path).relative_to(ROOT).as_posix(),sha256=sha(asset_file(path))) for kind,path in [('definition',definition),('master',master)]}
    report=dict(schema_version=1,passed=True,status='Native glint evidence reconciled; artist approval remains separate',evidence_session=dict(pid=identity[0],session_id=identity[1]),evidence_hashes=pins,capture_count=len(captures),capture_hashes=captures,primary_capture_provenance=dict(backend=PRIMARY_BACKEND,camera_path=next(iter(primary_cameras)),all_native_tasks_done_and_valid=True,controls_scope='Per-capture state reports the owned source rig; the screenshot API reports the primary CameraActor path. Primary camera transforms, FOV and postprocess were not independently sampled in these responses.'),native_stats=baseline['looks']['Opal']['compiled'],recipe_pin=recipe_pin,settings_sha256=sha(Path(__file__).with_name('opal_glints_settings.py')),core_source_snapshot_at_reconciliation=snapshots,core_snapshot_scope='Current source hashes only; build-time source hash identity was not independently recorded',source_hashes=sources,protected_hashes=protected,new_assets=assets,reused_read_only_assets={p:sha(asset_file(p)) for p in expected_reuse},texture_checks=prep['texture_checks'],source_provenance=prep['source_provenance'],fresh_metrics=metrics,live_reload=dict(repeat_mae=rn,changed_mae=delta,restored_mae=recovery),motion=dict(frame_count=24,encoded=movie,independently_decoded_all_frames=True),gates=gates,final_session=final,performance_measured=False,published=False,limitations=['Artist-derived opal artwork and utility maps, not scanned/calibrated mineral data.','Native glints and two layered closures do not prove volumetric transport or spectral diffraction.','DepthOff signal is measured without requiring it to exceed noise.','24 actual primary-viewport motion captures; no performance or artist acceptance claim.','Process absence is established by the hashed closure record; this tool never controls Unreal.'])
    destination=OUT/'OpalGlints-Receipt.json';data=json.dumps(report,indent=2)+'\n';require(not destination.exists() or destination.read_text()==data,'Preserve differing existing receipt')
    if not destination.exists():destination.write_text(data)
    print(json.dumps(dict(receipt=str(destination),passed=True,captures=len(captures)),indent=2))

if __name__=='__main__':main()
