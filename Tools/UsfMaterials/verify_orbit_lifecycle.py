"""Exercise the real gym respawn and EndPlay paths after the same-instance proofs finish."""
import json
from verify_industrial_reload import command,OUTPUT


def require(value,message):
    if not value: raise RuntimeError(message)


def main():
    initial=command('state')
    report={'passed':False,'scope':'Fresh gym instances after actual respawn and active-light EndPlay; separate from same-instance source proof.','initial_state':initial}
    try:
        require(not initial['inspection_orbit']['enabled'],'Finish the light proof before lifecycle checks')
        command('select','--environment','displacement')
        command('orbit_on')
        active=command('orbit_pause')
        require(active['inspection_orbit']['enabled'],'Could not activate the real selected light')
        respawn=command('orbit_respawn')
        report['active_before_respawn']=active
        report['after_respawn']=respawn
        orbit=respawn['inspection_orbit']
        require(orbit['actor']!=active['inspection_orbit']['actor'] and not orbit['enabled']
                and orbit['intensity']==0 and orbit['target'] is None,'Respawn left old or emitting light state')
        require(len(orbit['rigs'])==len(initial['inspection_orbit']['rigs']) and len(respawn['library'])==42,'Respawn changed the gym roster')
        expected=sorted(initial['inspection_orbit']['rigs'].values())
        require(sorted(orbit['rigs'].values())==expected,'Respawn did not return the studio rigs to their original values')
        for section in ['library','environment']:
            for name,old in initial[section].items():
                now=respawn[section][name]
                require(all(now[field]==old[field] for field in ['parent','textures','values','colors']),'Respawn changed material defaults: '+name)
        command('select','--look','LibraryAluminum')
        active_end=command('orbit_on')
        report['active_before_end']=active_end
        require(active_end['inspection_orbit']['enabled'],'EndPlay test requires an emitting owned light')
        report['end']=command('end')
        report['gc']=command('gc')
        outside=command('state')
        report['outside_pie']=outside
        require(outside['inspection_orbit'] is None and not outside['library'] and not outside['environment'],'PIE light/material actors survived into editor state')
        reopened=command('open')
        report['reopened_state']=reopened
        require(reopened['pid']==initial['pid'] and not reopened['inspection_orbit']['enabled']
                and reopened['inspection_orbit']['intensity']==0 and reopened['inspection_orbit']['target'] is None,'Warm reopen retained an emitting inspection light')
        require(sorted(reopened['inspection_orbit']['rigs'].values())==expected and len(reopened['library'])==42,'Warm reopen did not restore the complete normal presentation')
        report['passed']=True
    except BaseException as error:
        report['error']=str(error)
        raise
    finally:
        try:
            current=command('state')
            if current.get('inspection_orbit') and current['inspection_orbit']['enabled']: command('orbit_off')
        except BaseException as error: report['cleanup_error']=str(error)
        try: final=command('state')
        except BaseException as error: final={'error':str(error)}
        report['final_state']=final
        report['restored']=bool(report['passed'] and final.get('inspection_orbit') and not final['inspection_orbit']['enabled'])
        (OUTPUT/'OrbitLight-LifecycleProof.json').write_text(json.dumps(report,indent=2))
    if not report['passed'] or not report['restored']: raise SystemExit(1)
    print('Real respawn, active EndPlay, GC and warm reopen passed')


if __name__=='__main__': main()
