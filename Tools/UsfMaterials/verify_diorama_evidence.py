"""Reconcile diorama source, assets, rendered responses and fresh focused gate offline."""
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import numpy as np
from PIL import Image
from verify_diorama_patches import PATCHES, pixels, metric, ROOT, OUTPUT, SHADERS


def require(value,message):
    if not value:raise RuntimeError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name):return json.loads((OUTPUT/name).read_text(encoding='utf-8-sig'))


def owned(base,relative):
    path=(base/relative).resolve()
    require(path.is_relative_to(base.resolve()),'Evidence path escapes its owner: '+str(relative))
    return path


def source_evidence(manifest_path,manifest,prep):
    """Source data/calibration evidence is separate from the Unreal capture checks below."""
    source=manifest_path.parent
    channels={'BaseColor','Normal','Roughness','Height','AO'}
    looks={'grass':'EnvironmentDioramaGrass','dirt':'EnvironmentDioramaDirt','mud':'EnvironmentDioramaMud'}
    require(manifest['schema_version']==1 and set(manifest['materials'])==set(looks),'Source material roster differs')
    verification_path=source/'SourceVerification.json'
    verification=json.loads(verification_path.read_text())
    require(verification['verified'] is True and verification['manifest_sha256']==sha(manifest_path)
            and verification['generator_sha256']==manifest['generator_sha256']
            and set(verification['materials'])==set(looks) and verification['total_runtime_maps']==15
            and verification['total_EXR_masters']==15,'Native source verification is stale or incomplete')
    expected_provenance={};hashes={};maps={};calibration_hashes={};source_beauties={}
    def checked(path,expected,provenance=True):
        require(sha(path)==expected,'Source hash differs: '+str(path))
        relative=str(path.relative_to(ROOT));hashes[relative]=expected
        if provenance:expected_provenance[relative]=expected
    for field,hashfield,filename in [('generator_source','generator_sha256','author_diorama_patches.py'),
                                    ('helper_source','helper_sha256','author_woodland_patch.py')]:
        path=owned(ROOT,manifest[field])
        require(path==(ROOT/'Tools/UsfMaterials'/filename).resolve(),'Unexpected source generator/helper')
        checked(path,manifest[hashfield])
    require(bool(manifest['provenance_evidence']) and bool(manifest['licensed_source_sha256']),'Missing licensed source evidence')
    for info in manifest['provenance_evidence']:checked(owned(source,info['path']),info['sha256'])
    for relative,expected in manifest['licensed_source_sha256'].items():
        path=owned(ROOT,relative)
        require(path.is_relative_to((ROOT/'Plugins/CkTests/Resources/CkUsf').resolve()),'Licensed input escapes resources')
        checked(path,expected)
    texture_receipts={(item['patch'],item['channel']):item for item in prep['textures']}
    require(len(texture_receipts)==len(prep['textures'])==15,'Imported texture roster must be exactly fifteen unique channels')
    for patch,look in looks.items():
        record=manifest['materials'][patch];native=verification['materials'][patch]
        require(record['look_id']==look and set(record['maps'])==channels
                and record['physical_width_cm']==record['physical_height_cm']==80,'Source look/footprint differs')
        height=record['height'];span=height['range_cm']
        require(all(type(height[k]) in (int,float) and math.isfinite(height[k]) for k in ['z_min_cm','z_max_cm','range_cm'])
                and 0<span<=6 and math.isclose(height['z_max_cm']-height['z_min_cm'],span,abs_tol=1e-6)
                and height['not_albedo_derived'] is True and height['decode']=='height_cm=z_min_cm+sampleHeight16*range_cm'
                and native['height']==height,'Source physical height calibration differs')
        require(set(record['masters'])=={'BaseColor','WorldNormal','Roughness','HeightCm','AO'} and native['masters_verified']==5,'Missing aligned EXR masters')
        checked(owned(source,record['blend']['path']),record['blend']['sha256'])
        for info in record['masters'].values():
            require(info['bit_depth']==32 and info['color_space']=='linear','EXR master precision differs')
            checked(owned(source,info['path']),info['sha256'])
        beauty=owned(source,record['beauty']['path']);checked(beauty,record['beauty']['sha256'],False)
        source_beauties[patch]={'label':'Blender source art, not an Unreal capture','path':str(beauty.relative_to(ROOT)),'sha256':sha(beauty)}
        resolution=record['maps']['BaseColor']['width'];decoded={}
        for channel,info in record['maps'].items():
            path=owned(source,info['path']);checked(path,info['sha256'])
            data=path.read_bytes();size=[info['width'],info['height']]
            require(len(data)>=29 and data[:8]==b'\x89PNG\r\n\x1a\n' and data[12:16]==b'IHDR'
                    and list(struct.unpack('>II',data[16:24]))==size and data[24]==info['bit_depth']
                    and size==[resolution,resolution] and resolution>=1024 and resolution&(resolution-1)==0
                    and info['bit_depth'] in ([8] if channel=='BaseColor' else [16] if channel=='Height' else [8,16])
                    and info['runtime_name']=='T_'+look+'_'+channel
                    and info['color_space']==('sRGB' if channel=='BaseColor' else 'linear'),'Source PNG contract differs: '+patch+'/'+channel)
            require(native['maps'][channel]['sha256']==info['sha256'] and native['maps'][channel]['bit_depth']==data[24],'Native source verification does not describe this map')
            with Image.open(path) as image:array=np.asarray(image)
            decoded[channel]=array
            if channel!='Normal':
                stats={'unique_values':int(np.unique(array).size),'min':int(array.min()),'max':int(array.max())}
                require(all(native['maps'][channel][key]==value for key,value in stats.items()),'Actual decoded map statistics differ: '+patch+'/'+channel)
            else:stats={'precision_note':f'Encoded RGB{info["bit_depth"]} hash/header verified; Pillow RGB decode is eight-bit for the independent correlation check.'}
            maps[patch+'/'+channel]={'sha256':sha(path),'dimensions':size,'bit_depth':data[24],**stats}
            receipt=texture_receipts[(patch,channel)];settings=receipt['settings']
            compression={'BaseColor':'TC_DEFAULT','Normal':'TC_NORMALMAP','Height':'TC_GRAYSCALE','Roughness':'TC_MASKS','AO':'TC_MASKS'}[channel]
            group='TEXTUREGROUP_WORLD' if channel=='BaseColor' else 'TEXTUREGROUP_WORLD_NORMAL_MAP' if channel=='Normal' else 'TEXTUREGROUP_WORLD_SPECULAR'
            require(receipt['path']=='/CkFoundation/CkUsf/Textures/Environment/'+info['runtime_name']
                    and receipt['source_sha256']==info['sha256'] and receipt['source_size']==receipt['runtime_size']==size
                    and settings['srgb']==(channel=='BaseColor') and '.'+compression+':' in settings['compression_settings']
                    and '.'+group+':' in settings['lod_group'] and '.TA_CLAMP:' in settings['address_x'] and '.TA_CLAMP:' in settings['address_y']
                    and '.TMGS_SIMPLE_AVERAGE:' in settings['mip_gen_settings'] and '.NONE:' in settings['power_of_two_mode']
                    and settings['flip_green_channel'] is False,'Saved texture semantic/size receipt differs')
        h=decoded['Height'];require(h.dtype.kind in 'ui' and h.dtype.itemsize>=2 and int(h.min())==0
                                   and int(h.max())==65535 and np.unique(h).size>256,'Height lost normalized sixteen-bit information')
        require(str(record['maps']['Normal']['normal_convention']).startswith('DirectX'),'Normal convention differs')
        calibration=record['calibration']
        analytic_normal=np.array([-.04,-.07,1.0]);analytic_normal/=np.linalg.norm(analytic_normal)
        require(np.max(np.abs(np.array(calibration['expected_world_normal'])-analytic_normal))<1e-10
                and calibration['known_linear_color']==[.18,.31,.47]
                and np.max(np.abs(np.array(calibration['measured_world_normal'])-analytic_normal))<.001
                and np.max(np.abs(np.array(calibration['measured_linear_color'])-calibration['known_linear_color']))<.001,'Native source calibration failed')
        normal=decoded['Normal'].astype(float)/255*2-1
        require(normal.shape==(*h.shape,3),'Normal and height arrays do not align')
        dv,du=np.gradient(h.astype(float)/65535*span,80/resolution)
        valid=(normal[:,:,2]>.9)&(np.abs(du)<.45)&(np.abs(dv)<.45)
        valid[:3]=False;valid[-3:]=False;valid[:,:3]=False;valid[:,-3:]=False
        require(int(valid.sum())>100,'Insufficient source normal/height correlation pixels')
        correlations=[float(np.corrcoef(-gradient[valid],normal[:,:,index][valid])[0,1]) for index,gradient in enumerate([du,dv])]
        require(all(math.isfinite(value) and value>.8 and abs(value-expected)<.01 for value,expected in zip(correlations,native['normal_height_correlations_RG'])),
                'Actual normal and height directions disagree')
        maps[patch+'/normal_height_correlations_RGB8']=correlations
        calibration_dir=owned(source,record['blend']['path']).parent/'Calibration'
        for filename in ['HeightCm.exr','WorldNormal.exr','LinearColor.exr','NormalDX-linear16.png','BaseColor-sRGB8.png']:
            path=calibration_dir/filename;calibration_hashes[str(path.relative_to(ROOT))]=sha(path)
        with Image.open(calibration_dir/'NormalDX-linear16.png') as image:probe=np.asarray(image.convert('RGB'),dtype=float)[8:-8,8:-8]/255*2-1
        measured=np.median(probe,axis=(0,1));expected=np.array(calibration['expected_world_normal'])*[1,-1,1]
        require(np.max(np.abs(measured-expected))<2/255+.0001
                and np.max(np.abs(np.array(native['calibrated_normalDX'])-expected))<.001,'Asymmetric normal calibration PNG has wrong sign/transfer')
        with Image.open(calibration_dir/'BaseColor-sRGB8.png') as image:probe=np.asarray(image.convert('RGB'),dtype=float)[8:-8,8:-8]
        color=np.median(probe,axis=(0,1));linear=np.array(calibration['known_linear_color'])
        expected=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)*255
        require(np.max(np.abs(color-expected))<=1 and np.max(np.abs(color-native['calibrated_BC8_RGB']))<=1,'Base-color PNG is not the calibrated sRGB transfer')
        require(prep['presentation'][patch]==({'ReliefCm':1.0,'HeightMip':2} if patch=='grass' else {'ReliefCm':span,'HeightMip':0}),
                'Reviewed presentation differs from calibrated source metadata')
    require(prep['provenance_sha256']==expected_provenance,'Preparation source evidence roster differs from selected manifest')
    return {'source_verification_sha256':sha(verification_path),'source_file_sha256':hashes,'map_statistics':maps,
            'calibration_file_sha256':calibration_hashes,'blender_source_art':source_beauties,'presentation':prep['presentation'],
            'scope':'Source integrity and data transfer; separate from Unreal rendered controls, art approval and measured optics.'}


def capture_plan(patch):
    pom,wpo=patch+'_pom',patch+'_displacement';plan=[]
    for quality in ['Native','TAA']:
        for station,mode in [(pom,'pom'),(wpo,'displacement')]:
            for view in ['Oblique','Low','Top']:plan.append((quality+'-'+mode+'-'+view,station,{},quality=='TAA'))
    for debug,name in [(1,'BaseColor'),(2,'Normal'),(3,'Roughness'),(5,'Height')]:plan.append(('Inspect-'+name,pom,{'DebugView':debug},False))
    plan.extend([('POM-Off-UV',pom,{'DebugView':8,'PomAmount':0},False),('POM-Off-UV-Repeat',pom,{'DebugView':8,'PomAmount':0},False),
                 ('POM-On-UV',pom,{'DebugView':8,'PomAmount':1},False),('WPO-Flat-Depth',wpo,{'DebugView':6,'DisplacementAmount':0},False),
                 ('WPO-Flat-Depth-Repeat',wpo,{'DebugView':6,'DisplacementAmount':0},False),('WPO-On-Depth',wpo,{'DebugView':6,'DisplacementAmount':1},False)])
    for station in [pom,wpo]:plan.append(('Source-'+station+'-Baseline',station,{'DebugView':1},False))
    plan.append(('Source-Repeat',pom,{'DebugView':1},False))
    for stage in ['Edited','Recovered']:
        for station in [pom,wpo]:plan.append(('Source-'+station+'-'+stage,station,{'DebugView':1},False))
    for stage in ['Baseline','Edited','Recovered']:plan.append(('Vertex-'+stage,wpo,{'DebugView':6},False))
    return plan


def orbit_evidence(proof):
    require(proof['passed'] is True and proof['restored'] is True and not proof['cleanup_errors'],'Diorama orbit proof did not pass and restore')
    initial,final=proof['initial_state'],proof['final_state'];baseline=initial['inspection_orbit']
    roster={'pom','displacement'}|{patch+'_'+mode for patch in PATCHES for mode in ['pom','displacement']}
    require(set(initial['environment'])==roster and len(initial['library'])==42 and initial['pid']==final['pid'], 'Orbit material/editor roster differs')
    require(initial['environment']==final['environment'] and initial['library']==final['library']
            and initial['industrial']==final['industrial'] and initial['render_cvars']==final['render_cvars'],'Orbit material/renderer state did not restore')
    def off(state):
        light=state['inspection_orbit']
        require(light['actor']==baseline['actor'] and not light['enabled'] and light['intensity']==0
                and light['target'] is None and light['rigs']==baseline['rigs']
                and light['paused']==baseline['paused'] and abs((light['phase']-baseline['phase']+180)%360-180)<1e-4,
                'Operative orbit state or original rigs were not restored')
        require(not state['preview_quality'] and not state['diagnostic_quantization'] and state['diagnostic_light'] is None
                and state['render_cvars']['r.AntiAliasingMethod']==0 and state['render_cvars']['r.ScreenPercentage']==87,'Orbit native renderer state differs')
    off(initial);off(final)
    labels={patch+'-'+stage for patch in PATCHES for stage in ['Phase0','Phase0Repeat','Phase180']}
    require(set(proof['captures'])==labels and set(proof['metrics'])==set(PATCHES),'Exactly nine orbit captures and three response metrics required')
    def materials(state):
        return {key:{field:value for field,value in item.items() if field!='rect_intensities'} for key,item in state['environment'].items()}
    hashes={};regions={};metrics={}
    for label,capture in proof['captures'].items():
        patch,stage=label.split('-',1);state=capture['state'];light=state['inspection_orbit']
        target=initial['environment'][patch+'_displacement']['actor'];phase=180 if stage=='Phase180' else 0
        filename='Diorama-'+patch+'-Orbit-'+stage+'.png';path=OUTPUT/filename
        require(capture['image']==filename and path.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n' and sha(path)==capture['sha256'],'Orbit capture bytes/hash differ')
        hashes[filename]=sha(path);regions[label]=pixels(filename)
        require(state['pid']==initial['pid'] and state['library']==initial['library'] and state['industrial']==initial['industrial']
                and materials(state)==materials(initial) and state['render_cvars']==initial['render_cvars']
                and not state['preview_quality'] and not state['diagnostic_quantization'] and state['diagnostic_light'] is None,'Orbit capture changed material/editor/quality state')
        require(light['actor']==baseline['actor'] and light['target']==target and light['enabled'] and light['paused']
                and abs(light['phase']-phase)<1e-4 and light['intensity']==40 and light['light_class']=='PointLightComponent'
                and 'CANDELAS' in light['intensity_units'] and light['source_radius']==6 and light['attenuation_radius']==200
                and light['radius']==100 and light['height']==70 and light['speed']==20,'Orbit capture used the wrong Point-light control')
        require(set(light['rigs'])==set(baseline['rigs']),'Orbit rig roster changed')
        for actor,values in baseline['rigs'].items():
            expected=[0,values[1]*.15,0] if actor==target else values
            require(light['rigs'][actor]==expected,'Orbit capture altered a nonselected rig or failed to dim the selected rig')
    for patch in PATCHES:
        noise=metric(regions[patch+'-Phase0'],regions[patch+'-Phase0Repeat'])['mean_absolute_rgb']
        effect=metric(regions[patch+'-Phase0'],regions[patch+'-Phase180'])['mean_absolute_rgb']
        actual={'repeat_noise':noise,'opposed_phase_difference':effect}
        require(set(proof['metrics'][patch])==set(actual) and all(math.isclose(value,proof['metrics'][patch][key],rel_tol=1e-10,abs_tol=1e-12)
                for key,value in actual.items()) and effect>max(.001,3*noise),'Orbit image response does not exceed independently measured repeat noise')
        metrics[patch]=actual
    return {'capture_sha256':hashes,'metrics':metrics,'scope':'Paused Point-light response and operative restoration; cached off-state position/radius are intentionally not restoration criteria.'}


def main():
    manifest_path=ROOT/'Plugins/CkTests/Resources/CkUsf/DioramaPatchesV1/Manifest.json'
    manifest=json.loads(manifest_path.read_text());prep=read('DioramaPreparation.json')
    require(prep['manifest_sha256']==sha(manifest_path),'Preparation source changed')
    source_checks=source_evidence(manifest_path,manifest,prep)
    for relative,expected in prep['provenance_sha256'].items():
        path=(ROOT/relative).resolve()
        require(path.is_relative_to(ROOT) and sha(path)==expected,'Source provenance changed: '+relative)
    captures={};binaries={};proofs={};metrics={}
    protected=read('Diorama-OpeningHashes.json')
    require(len(protected)==396,'Opening protection roster differs')
    for relative,expected in protected.items():require(sha(owned(ROOT,relative))==expected,'Earlier protected file changed: '+relative)
    grid=ROOT/'Plugins/CkTests/Content/CkUsf/Showcase/SM_UsfWoodlandGrid.uasset'
    require(prep['grid']['reused_without_resave'] and sha(grid)==prep['grid']['asset_sha256']==protected[str(grid.relative_to(ROOT))], 'Shared grid changed')
    latest=(OUTPUT/'DioramaPreparation.json').stat().st_mtime
    for patch in PATCHES:
        file=OUTPUT/('Diorama-'+patch+'-Proof.json');proof=read(file.name);proofs[patch]=sha(file)
        latest=max(latest,file.stat().st_mtime)
        record=manifest['materials'][patch];look=record['look_id'];shader=SHADERS/('Looks/'+look+'.ush')
        require(proof['passed'] is True and proof['restored'] is True and not proof['cleanup_errors'],'Incomplete/restoration failed proof: '+patch)
        require(proof['manifest_sha256']==sha(manifest_path) and proof['preparation_sha256']==sha(OUTPUT/'DioramaPreparation.json')
                and proof['source_sha256']==sha(shader),'Source/preparation changed after proof')
        require(len(proof['captures'])==32 and len(proof['reloads'])==4 and all('[0] failed' in s and 'CkUsf reload complete:' in s for s in proof['reloads']),'Incomplete capture/reload proof')
        initial,final=proof['initial_state'],proof['final_state']
        require(initial['pid']==final['pid'] and initial['environment']==final['environment'] and initial['library']==final['library']
                and initial['industrial']==final['industrial'] and initial['inspection_orbit']==final['inspection_orbit']
                and initial['render_cvars']==final['render_cvars'],'State not restored')
        roster={'pom','displacement'}|{p+'_'+mode for p in PATCHES for mode in ['pom','displacement']}
        require(set(initial['environment'])==roster and len(initial['library'])==42
                and len({item['mid'] for item in initial['environment'].values()})==8,'Incomplete or aliased environment/library roster')
        for state in [initial,final]:
            orbit=state['inspection_orbit']
            require(not orbit['enabled'] and orbit['intensity']==0 and orbit['target'] is None
                    and not state['preview_quality'] and not state['diagnostic_quantization'] and state['diagnostic_light'] is None
                    and state['render_cvars']['r.AntiAliasingMethod']==0 and state['render_cvars']['r.ScreenPercentage']==87,'Temporary lighting/quality state remains')
        require(all(item['same_mid'] is None and item['same_master'] is None for item in initial['environment'].values()),'Initial environment proof references were already retained')
        pom,wpo=patch+'_pom',patch+'_displacement'
        expected={c+'Map':'/CkFoundation/CkUsf/Textures/Environment/'+v['runtime_name']+'.'+v['runtime_name'] for c,v in record['maps'].items()}
        parent='/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_'+look+'.M_CkUsf_Look_'+look
        for key in [pom,wpo]:
            item=initial['environment'][key];values=item['values'];presentation=prep['presentation'][patch]
            require(item['textures']==expected and item['parent']==parent
                    and item['mesh']=='/CkTests/CkUsf/Showcase/SM_UsfWoodlandGrid.SM_UsfWoodlandGrid'
                    and item['scale']==[1,1,1] and values['DebugView']==0 and values['UVScale']==1
                    and values['NormalStrength']==1 and values['StepCount']==64 and values['TileSizeCm']==80
                    and values['HeightMip']==presentation['HeightMip'] and abs(values['ReliefCm']-presentation['ReliefCm'])<1e-5
                    and values['PomAmount']==(1 if key==pom else 0) and values['DisplacementAmount']==(1 if key==wpo else 0),
                    'Wrong source bindings, physical presentation or mode defaults')
        for channel,info in record['maps'].items():
            require(sha(manifest_path.parent/info['path'])==info['sha256'],'Map changed')
            binary=ROOT/('Plugins/CkFoundation/Content/CkUsf/Textures/Environment/'+info['runtime_name']+'.uasset')
            binaries[str(binary.relative_to(ROOT))]=sha(binary)
        binary=ROOT/('Plugins/CkFoundation/Content/CkUsf/GeneratedLooks/M_CkUsf_Look_'+look+'.uasset')
        binaries[str(binary.relative_to(ROOT))]=sha(binary)
        images={};plan=capture_plan(patch)
        require(len(plan)==32 and set(proof['captures'])=={label for label,_,_,_ in plan},'Exact diorama capture stages differ')
        current_values={key:dict(value['values']) for key,value in initial['environment'].items()}
        for label,station,overrides,taa in plan:
            capture=proof['captures'][label]
            path=OUTPUT/capture['image']
            require(path.parent==OUTPUT and path.name=='Diorama-'+patch+'-'+label+'.png'
                    and path.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n' and sha(path)==capture['sha256'],'Capture changed')
            captures[path.name]=sha(path);images[label]=pixels(path.name)
            state=capture['state']
            require(state['pid']==initial['pid'] and state['library']==initial['library'] and state['industrial']==initial['industrial']
                    and set(state['environment'])==roster and state['inspection_orbit']==initial['inspection_orbit'],'Capture modified sibling/light/editor')
            require(state['render_cvars']['r.AntiAliasingMethod']==(2 if taa else 0)
                    and state['render_cvars']['r.ScreenPercentage']==(100 if taa else 87)
                    and state['preview_quality']==taa and not state['diagnostic_quantization'] and state['diagnostic_light'] is None,
                    'Capture quality or diagnostic state differs')
            require(all(value==initial['render_cvars'][key] for key,value in state['render_cvars'].items()
                        if key not in ['r.AntiAliasingMethod','r.ScreenPercentage']),'Unrelated render CVar changed')
            current_values[station].update(overrides)
            for key,before in initial['environment'].items():
                now=state['environment'][key]
                require(now['same_mid'] and now['same_master'] and all(now[f]==before[f] for f in ['actor','mid','parent','mesh','textures','colors','scale','rect_intensities']),'Capture changed identity')
                require(now['values']==current_values[key],'Capture scalar/control or sibling values differ: '+label+'/'+key)
        pairs={'UV repeat noise':('POM-Off-UV','POM-Off-UV-Repeat'),'POM UV response':('POM-Off-UV','POM-On-UV'),
               'Depth repeat noise':('WPO-Flat-Depth','WPO-Flat-Depth-Repeat'),'WPO raster depth':('WPO-Flat-Depth','WPO-On-Depth'),
               'BaseColor repeat noise':('Source-'+pom+'-Baseline','Source-Repeat'),
               'USH vertex height':('Vertex-Baseline','Vertex-Edited'),'Vertex recovery':('Vertex-Baseline','Vertex-Recovered')}
        for s in [pom,wpo]:
            pairs['USH sampling/color '+s]=('Source-'+s+'-Baseline','Source-'+s+'-Edited')
            pairs['Source recovery '+s]=('Source-'+s+'-Baseline','Source-'+s+'-Recovered')
        measured={name:metric(images[a],images[b]) for name,(a,b) in pairs.items()}
        require(set(measured)==set(proof['metrics']),'Metric roster differs')
        for name,value in measured.items():
            require(all(math.isclose(v,proof['metrics'][name][k],rel_tol=1e-10,abs_tol=1e-12) for k,v in value.items()),'Recomputed pixels differ')
        uv,depth,bc=[measured[n]['mean_absolute_rgb'] for n in ['UV repeat noise','Depth repeat noise','BaseColor repeat noise']]
        for name,minimum,noise in [('POM UV response',.001,uv),('WPO raster depth',.0005,depth),('USH vertex height',.0005,depth)]+[('USH sampling/color '+s,.01,bc) for s in [pom,wpo]]:
            threshold=max(minimum,3*noise)
            require(measured[name]['mean_absolute_rgb']>threshold and proof['metrics'][name]['required_mean_above_repeat_noise']==threshold,'Rendered response below measured noise')
        for s in [pom,wpo]:require(measured['Source recovery '+s]['mean_absolute_rgb']<max(3*bc,measured['USH sampling/color '+s]['mean_absolute_rgb']*.25),'Pixel recovery failed')
        require(measured['Vertex recovery']['mean_absolute_rgb']<max(3*depth,measured['USH vertex height']['mean_absolute_rgb']*.25),'Vertex recovery failed')
        require(metric(images['WPO-Flat-Depth'],images['Vertex-Edited'])['mean_absolute_rgb']
                <max(3*depth,measured['USH vertex height']['mean_absolute_rgb']*.25),'Edited vertex shader did not approach the actual flat-depth control')
        metrics[patch]=measured
    orbit_path=OUTPUT/'Diorama-OrbitProof.json'
    orbit_checks=orbit_evidence(read(orbit_path.name));latest=max(latest,orbit_path.stat().st_mtime)
    gate=read('Diorama-Gate.exit.json');log=owned(ROOT,gate['log']);text=log.read_text(errors='replace')
    completed=datetime.datetime.fromisoformat(gate['completed_utc'].replace('Z','+00:00')).timestamp()
    summaries=list(re.finditer(r'Total:\s*(\d+)\s+Passed:\s*(\d+)\s+Failed:\s*(\d+)\s+Skipped:\s*(\d+)\s+Contaminated:\s*(\d+)',text))
    require(gate['exit_code']==0 and completed>=latest and log.stat().st_mtime>=latest and summaries,'Fresh gate missing or older than proof')
    total,passed,failed,skipped,contaminated=map(int,summaries[-1].groups())
    require(total>0 and total==passed and failed==skipped==contaminated==0
            and any('Test Completed.' in s and 'Result={Success}' in s and 'Name={GeneratesUsableMasters}' in s for s in text.splitlines()),'Generation gate failed')
    require(not re.search(r'Fatal error|Assertion failed|Ensure condition failed|Script Compile Error|Failed to compile Material',text),'Fresh log contains failure')
    require(len(captures)==96 and len(binaries)==18,'Incomplete diorama artifact roster')
    report={'passed':True,'manifest_sha256':sha(manifest_path),'preparation_sha256':sha(OUTPUT/'DioramaPreparation.json'),
            'proof_sha256':proofs,'capture_sha256':captures,'new_asset_binary_sha256':binaries,'metrics':metrics,
            'source_evidence':source_checks,
            'orbit_proof_sha256':sha(orbit_path),'orbit_evidence':orbit_checks,
            'protected_unchanged':len(protected),'gate':gate,'gate_log_sha256':sha(log),
            'scope':'Three texture-backed height materials; native controls and live edits verified. User art approval and GPU performance remain separate.'}
    (OUTPUT/'Diorama-Verification.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passed':True,'captures':len(captures),'orbit_captures':len(orbit_checks['capture_sha256']),'assets':len(binaries),'protected':len(protected)}))


if __name__=='__main__':main()
