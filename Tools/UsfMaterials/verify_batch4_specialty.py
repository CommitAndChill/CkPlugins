"""Offscreen same-MID flat tile and thin-plastic pane controls, with exact override restoration."""
import hashlib
import json
import numpy as np
from PIL import Image
from verify_industrial_reload import command, OUTPUT, SHADERS


def pixels(record):
    return np.asarray(Image.open(OUTPUT/record['image']).convert('RGB'),dtype=float)/255


def capture(name,label,debug=0,scalars=None,vectors=None):
    values=dict(scalars or {})
    if name == 'LibraryPorcelain': values['UVScale']=.5
    args=sum((['--scalar',k+'='+str(v)] for k,v in values.items()),[])
    args+=sum((['--vector',k+'='+','.join(map(str,v))] for k,v in (vectors or {}).items()),[])
    filename='Batch4-'+label+'.png'
    result=command('capture','--look',name,'--name',filename,'--debug',debug,
                   '--distance',280,'--height',0,'--shot',*args)
    return {'image':filename,'state':result['state']}


def restore(name,original):
    args=sum((['--scalar',k+'='+str(v)] for k,v in original['values'].items()),[])
    args+=sum((['--vector',k+'='+','.join(map(str,v))] for k,v in original['colors'].items()),[])
    command('select','--look',name,'--lighting','studio',*args)


def run(name,kind):
    initial=command('state');original=initial['library'][name]
    path=SHADERS/'Looks'/(name+'.ush')
    report={'passed':False,'restored':False,'scope':kind+' controls in the same existing library master/MID',
            'source_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest()},'captures':{}}
    preview=False
    flat=kind=='Porcelain'
    begin='surface_pane_begin' if flat else 'glass_pane_begin'
    end='surface_pane_end' if flat else 'glass_pane_end'
    try:
        command(begin,'--look',name)
        command('library_proof_begin')
        records=report['captures']
        if flat:
            report['inspection_uv_scale']=.5
            records['Lit']=capture(name,'Porcelain-Plane-Lit')
            records['Mask']=capture(name,'Porcelain-Plane-TileMask',5)
            records['Coat']=capture(name,'Porcelain-Plane-GlazeMask',6)
            records['NoCoat']=capture(name,'Porcelain-Plane-NoGlaze',6,{'GlazeWeight':0})
            restore(name,original)
            records['Color']=capture(name,'Porcelain-Plane-Color',1)
            records['GroutColor']=capture(name,'Porcelain-Plane-GroutColor',1,vectors={'GroutColor':[.8,.03,.5,1]})
            restore(name,original)
            records['RoughLow']=capture(name,'Porcelain-Plane-GroutRoughLow',3,{'GroutRoughness':.2})
            records['RoughHigh']=capture(name,'Porcelain-Plane-GroutRoughHigh',3,{'GroutRoughness':.95})
            roi=np.s_[140:375,265:490]
            lum=np.array([.2126,.7152,.0722]);mask=pixels(records['Mask'])[roi]@lum
            maximum=float(mask.max());tile=mask>maximum*.92;grout=mask<maximum*.04
            if tile.sum()<500 or grout.sum()<100:raise RuntimeError('Flat sample lacks resolved tile/grout regions')
            coat=pixels(records['Coat'])[roi]@lum
            no_coat=pixels(records['NoCoat'])[roi]@lum
            color_diff=abs(pixels(records['GroutColor'])[roi]-pixels(records['Color'])[roi])
            rough_diff=abs(pixels(records['RoughHigh'])[roi]-pixels(records['RoughLow'])[roi])
            report['metrics']={'tile_pixels':int(tile.sum()),'grout_pixels':int(grout.sum()),
                'coat_tile_mean':float(coat[tile].mean()),'coat_grout_max':float(coat[grout].max()),
                'disabled_coat_max':float(no_coat.max()),'color_tile_mean_change':float(color_diff[tile].mean()),
                'color_grout_mean_change':float(color_diff[grout].mean()),
                'roughness_tile_mean_change':float(rough_diff[tile].mean()),
                'roughness_grout_mean_change':float(rough_diff[grout].mean())}
            m=report['metrics']
            if not(m['coat_tile_mean']>.1 and m['coat_grout_max']<.02 and m['disabled_coat_max']<.02
                   and m['color_grout_mean_change']>.04 and m['color_tile_mean_change']<.02
                   and m['roughness_grout_mean_change']>.08 and m['roughness_tile_mean_change']<.02):
                raise RuntimeError('Tile/glaze/grout separation failed: '+str(m))
        else:
            report['metrics']={}
            for quality in ['Native','TAA']:
                if quality=='TAA':command('preview_quality');preview=True
                for label,body,trans in [('Baseline',original['values']['BodyCoverage'],1),('NoBody',0,1),('OpaqueBody',.9,1),('LowTransmission',0,.2)]:
                    records[quality+'-'+label]=capture(name,'Plastic-Pane-'+quality+'-'+label,scalars={
                        'BodyCoverage':body,'TransmissionAmount':trans,'Ior':1,'NormalStrength':0})
                base=pixels(records[quality+'-Baseline']);body=pixels(records[quality+'-OpaqueBody'])
                clear=pixels(records[quality+'-NoBody']);low=pixels(records[quality+'-LowTransmission'])
                covered=np.s_[140:375,265:345];uncovered=np.s_[140:375,420:500]
                m={'body_coverage_mean_rgb_change':float(abs(body[covered]-clear[covered]).mean()),
                   'transmission_mean_rgb_change':float(abs(clear[covered]-low[covered]).mean()),
                   'uncovered_reference_change':float(abs(clear[uncovered]-low[uncovered]).mean())}
                report['metrics'][quality]=m
                if not(m['body_coverage_mean_rgb_change']>.005 and m['transmission_mean_rgb_change']>.003
                       and m['uncovered_reference_change']<.02):raise RuntimeError('Plastic pane control failed: '+str(m))
                if preview:command('restore_quality');preview=False
        for record in records.values():
            state=record['state'];item=state['library'][name]
            if state['pid']!=initial['pid'] or not item['same_mid'] or not item['same_master'] or item['textures']!=original['textures']:
                raise RuntimeError('Specialty inspection replaced its existing material or texture binding')
        report['passed']=True
    finally:
        if preview:command('restore_quality')
        command(end,'--look',name)
        command('proof_end')
        restore(name,original)
        final=command('state')
        report['restored']=initial['library']==final['library'] and not final['preview_quality'] and final['diagnostic_light'] is None
        report['passed']=report['passed'] and report['restored']
        (OUTPUT/('Batch4-'+kind+'Proof.json')).write_text(json.dumps(report,indent=2))
    if not report['passed']:raise RuntimeError(kind+' proof incomplete')
    print(kind+' specialty proof passed',flush=True)


if __name__=='__main__':
    run('LibraryPorcelain','Porcelain')
    run('LibraryTranslucentPlastic','Plastic')
