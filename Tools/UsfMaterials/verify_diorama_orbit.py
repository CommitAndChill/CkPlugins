"""Check the existing inspection light on the three added ground stations, serially."""
import json
from verify_industrial_reload import command,OUTPUT
from verify_diorama_patches import sha,require,PATCHES
from verify_river_pebbles import pixels,metric


def materials(state):
    return {key:{name:value for name,value in record.items() if name!='rect_intensities'}
            for key,record in state['environment'].items()}


def main():
    initial=command('state');orbit=initial['inspection_orbit']
    require(not orbit['enabled'] and orbit['intensity']==0,'Finish source proofs with the light disabled')
    report={'passed':False,'restored':False,'initial_state':initial,'captures':{},'metrics':{}}
    try:
        for patch in PATCHES:
            key=patch+'_displacement';actor=initial['environment'][key]['actor']
            command('select','--environment',key);command('orbit_on');command('orbit_pause')
            samples={}
            for name,phase in [('Phase0',0),('Phase0Repeat',0),('Phase180',180)]:
                state=command('orbit_phase','--phase',phase);light=state['inspection_orbit']
                require(light['target']==actor and light['enabled'] and light['paused'] and light['intensity']==40
                        and light['light_class']=='PointLightComponent' and 'CANDELAS' in light['intensity_units'],'Wrong selected ground light')
                for rig,values in orbit['rigs'].items():
                    require(light['rigs'][rig]==([0,values[1]*.15,0] if rig==actor else values),'Unrelated rig changed')
                filename='Diorama-'+patch+'-Orbit-'+name+'.png'
                capture=command('capture','--environment',key,'--name',filename,'--shot','--distance',65,'--height',45)['state']
                require(materials(capture)==materials(initial) and capture['library']==initial['library'],'Material state changed during orbit')
                report['captures'][patch+'-'+name]={'image':filename,'sha256':sha(OUTPUT/filename),'state':capture}
                samples[name]=pixels(filename)
            noise=metric(samples['Phase0'],samples['Phase0Repeat'])['mean_absolute_rgb']
            effect=metric(samples['Phase0'],samples['Phase180'])['mean_absolute_rgb']
            require(effect>max(.001,3*noise),'Orbit illumination response below repeat noise')
            report['metrics'][patch]={'repeat_noise':noise,'opposed_phase_difference':effect}
            disabled=command('orbit_off')
            require(disabled['inspection_orbit']['rigs']==orbit['rigs'],'Rig intensities did not restore')
        report['passed']=True
    except BaseException as error:
        report['error']=str(error);raise
    finally:
        errors=[]
        for action,args in [('orbit_off',[]),('orbit_phase',['--phase',orbit['phase']]),('orbit_pause' if orbit['paused'] else 'orbit_resume',[])]:
            try:command(action,*args)
            except BaseException as error:errors.append(str(error))
        try:final=command('state')
        except BaseException as error:final={'error':str(error)}
        report['final_state']=final;report['cleanup_errors']=errors
        final_orbit=final.get('inspection_orbit',{})
        report['restored']=bool(not errors and final_orbit and not final_orbit['enabled'] and final_orbit['intensity']==0
                                and final_orbit['target'] is None and final_orbit['rigs']==orbit['rigs']
                                and final_orbit['paused']==orbit['paused'] and abs(final_orbit['phase']-orbit['phase'])<1e-4
                                and final.get('environment')==initial['environment']
                                and final.get('library')==initial['library'] and final.get('render_cvars')==initial['render_cvars'])
        report['passed']=report['passed'] and report['restored']
        (OUTPUT/'Diorama-OrbitProof.json').write_text(json.dumps(report,indent=2))
    require(report['passed'],'New-station orbit proof failed')
    print('Three new stations: orbit response, rig and material restoration passed')


if __name__=='__main__':main()
