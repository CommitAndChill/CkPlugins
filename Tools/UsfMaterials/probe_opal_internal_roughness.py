"""One reversible numerical probe: test whether lower-slab roughness suppresses A.

Native captures only; restores exact shader bytes even when capture fails.
"""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
from verify_opal_internal_reload import wait_reload, LOG
from opal_internal_command import submit

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/OpticalOpalInternal.ush'
OUT=ROOT/'Saved/UsfMaterialGallery'

def main(layer='All'):
    if layer not in ['All','B','C']:raise ValueError('Expected All, B or C')
    name='OpalInternal-Smooth'+layer
    receipt=OUT/(name+'-Probe.json')
    if receipt.exists():raise RuntimeError('Preserve existing probe')
    original=SOURCE.read_bytes()
    pairs=[(b'O.BRoughness = clamp(DomainRoughness*Finish/(31.0/255.0),.045,.5);',b'O.BRoughness = .025;'),
           (b'O.CRoughness = .35;',b'O.CRoughness = .025;')]
    if layer!='All':pairs=[pairs[0 if layer=='B' else 1]]
    edited=original
    for before,after in pairs:
        if edited.count(before)!=1:raise RuntimeError('Unique source anchor required')
        edited=edited.replace(before,after)
    record={'purpose':'Check whether lower-slab roughness removes independent sharp coat response',
            'original_sha256':hashlib.sha256(original).hexdigest()}
    owned=original
    try:
        offset=LOG.stat().st_size;SOURCE.write_bytes(edited);owned=edited
        record['reload']=wait_reload(offset)
        record['compile']=submit('diagnostics',op='compile_comparison')
        record['capture']=submit('capture_primary',name=name+'.png',subject='opal',body_shadow=False,front_reflections=True,settle_frames=90)
    finally:
        if SOURCE.read_bytes()!=owned:raise RuntimeError('Concurrent edit preserved; manual recovery required')
        offset=LOG.stat().st_size;SOURCE.write_bytes(original)
        record['restore_reload']=wait_reload(offset)
        record['restore_compile']=submit('diagnostics',op='compile_comparison')
        record['restored_sha256']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        receipt.write_text(json.dumps(record,indent=2))
    print(receipt)

if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'All')
