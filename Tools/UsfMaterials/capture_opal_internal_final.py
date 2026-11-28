"""Capture the saved three-layer preset and reversible native lighting controls."""
from pathlib import Path
import copy,json,sys
sys.dont_write_bytecode=True
from capture_opal_internal import main as capture


def main():
    preset=json.loads(Path(__file__).with_name('opal_internal_preset.json').read_text())
    for key in ['name','schema_version']:preset.pop(key)
    preset['settle_frames']=96
    # The first capture inherits every material value from the saved instance.
    inherited={key:value for key,value in preset.items() if key not in ['scalars','vectors']}
    capture('OpalInternal-Final.png',controls=json.dumps(inherited))
    variants={
        'NoFlash':{'scalars':{'Opal':{'FlashReflectance':0}}},
        'LowCoat':{'scalars':{'Opal':{'CoatIor':1.01}}},
        'BodyTransmission':{'vectors':{'Opal':{'BodyTransmission':[.8,.84,.88,1]}}},
        'LightsOff':{'intensities':[0,0,0],'sky':0,'environment_intensity':0,
                     'reflection_brightness':0,'front_reflections':False},
        'Restored':{},
    }
    for name,changes in variants.items():
        controls=copy.deepcopy(preset)
        for field,value in changes.items():
            if field in ['scalars','vectors']:controls[field]['Opal'].update(value['Opal'])
            else:controls[field]=value
        capture('OpalInternal-Final-'+name+'.png',controls=json.dumps(controls))


if __name__=='__main__':main()
