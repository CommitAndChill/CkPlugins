"""Capture an owned native OpalLayered frame and retain its complete response/provenance.

Importing performs no work. This helper never launches an editor or changes assets/images.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import argparse,hashlib,json,re,traceback
from PIL import Image
from opal_layered_command import submit

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'
SHADERS=ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf'
SOURCE=SHADERS/'Looks/OpticalOpalLayered.ush'
BACKEND='AutomationLibrary.take_high_res_screenshot primary editor viewport'


def require(condition,message):
    if not condition:raise AssertionError(message)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def read_controls(text):
    value=json.loads(text,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON constant: '+value)))
    require(isinstance(value,dict),'Controls must be a JSON object')
    require(not set(value)&{'id','action','session_id','name','timeout'},'Controls may not override bridge ownership, action or capture name')
    require(value.get('subject','opal')=='opal','Only the owned opal subject is supported')
    return value


def source_hashes():
    result={};visited=set()
    def visit(path):
        path=path.resolve()
        require(path.is_relative_to(SHADERS.resolve()) and path.is_file(),'Missing/outside local shader dependency: '+str(path))
        if path in visited:return
        visited.add(path);result[path.relative_to(ROOT).as_posix()]=sha(path)
        for include in re.findall(r'^\s*#\s*include\s+"([^"]+)"',path.read_text(encoding='utf-8-sig'),re.MULTILINE):
            require(include.startswith('/CkUsf/'),'Unexpected shader include mount: '+include)
            visit(SHADERS/include[len('/CkUsf/'):])
    visit(SOURCE)
    return result


def validate_response(response,path):
    require(response.get('ok') is True,'Native capture failed')
    require(Path(response['capture']).resolve()==path.resolve(),'Unexpected native capture destination')
    require(response.get('capture_backend')==BACKEND and response.get('native_task_done') is True and response.get('native_task_valid') is True,'Completed native primary screenshot required')
    with Image.open(path) as image:
        require(image.format=='PNG' and image.size==(1600,1200),'Expected actual native 1600x1200 PNG')
        image.load()
    state=response['state'];require(state['scene_created'] and state['adaptive']==1 and set(state['looks'])==set(state['actors'])=={'Opal'},'Exactly one layered subject actor/material required')
    require(state['subject']=='opal','Unexpected subject state')
    look=state['looks']['Opal'];stats=look['compiled']
    require(stats['valid'] and not stats['compile_errors'] and stats['closure_count']==2 and not stats['has_glint'] and not stats['complex_special'],'Two retained native translucent closures without Glint/ComplexSpecial required')
    require(look['master']=='/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_OpticalOpalLayeredFire.M_CkUsf_Look_OpticalOpalLayeredFire' and look['mid'] and look['front'],'Exact layered master/MID/front required')
    actor=state['actors']['Opal']
    require(actor['mesh']=='/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body.SM_AmberHero_Body','Approved read-only Body mesh required')
    require(all(abs(v)<1e-5 for v in actor['position']) and all(abs(v-1)<1e-5 for v in actor['scale']) and all(abs(v)<1e-5 for v in actor['rotation'].values()),'Subject Body must retain its identity transform')
    require(response.get('primary_camera_state') and response['primary_camera_state']==state.get('primary_camera_state'),'Actual primary-camera sampling required')


def main(name,controls=None,controls_file=None):
    require(isinstance(name,str) and re.fullmatch(r'OpalLayered-[A-Za-z0-9_.-]+\.png',name),'Plain OpalLayered- prefixed PNG filename required')
    require(not (controls is not None and controls_file is not None),'Use either --controls or --controls-file')
    path=OUT/name;receipt=OUT/(path.stem+'.json');pending=receipt.with_suffix('.pending')
    require(not path.exists() and not receipt.exists() and not pending.exists(),'Preserve existing PNG/receipt/pending file; choose a fresh capture name')
    record=dict(schema_version=1,status='running',passed=False,capture_name=name,preset={},source_hash_scope='Local shader/dependency bytes sampled around capture; not an independent running-shader-map hash')
    # Exclusive creation reserves this receipt; existing command bridge owns command serialization.
    with receipt.open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2)
    def save():
        with pending.open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2)
        pending.replace(receipt)
    try:
        if controls_file is not None:
            preset_path=Path(controls_file).resolve();text=preset_path.read_text(encoding='utf-8-sig')
            record['preset_file']=dict(path=str(preset_path),sha256=sha(preset_path))
        else:text=controls if controls is not None else '{}'
        preset=read_controls(text);submitted=dict(preset);submitted.setdefault('subject','opal');submitted['name']=name
        record.update(preset=preset,submitted_controls=submitted,source_hashes=source_hashes(),settings_sha256=sha(Path(__file__).with_name('opal_layered_settings.py')),helper_sha256=sha(Path(__file__)),bridge_sha256=sha(Path(__file__).with_name('opal_layered_command.py')));save()
        response=submit('capture_primary',**submitted)
        record['response']=response;save()  # Retain the complete native result before any assertions.
        if path.is_file():record['capture_sha256']=sha(path);save()
        record['source_hashes_after']=source_hashes();save()
        validate_response(response,path)
        require(record['source_hashes_after']==record['source_hashes'],'Local shader/dependency bytes changed during capture')
        require(sha(Path(__file__).with_name('opal_layered_settings.py'))==record['settings_sha256'],'Settings changed during capture')
        record.update(status='passed',passed=True);save()
        print(json.dumps(dict(receipt=str(receipt),capture=str(path),sha256=record['capture_sha256'],passed=True),indent=2))
    except Exception:
        # submit() raises on a failed command; its complete native response remains on the
        # UUID bridge. Copy that record too, without claiming an unrelated response is ours.
        if 'response' not in record:
            bridge=OUT/'OpalLayeredResult.json'
            if bridge.is_file():
                try:record['bridge_response_at_failure']=json.loads(bridge.read_text(encoding='utf-8-sig'))
                except Exception:record['bridge_response_read_error']=traceback.format_exc()
        record.update(status='failed',passed=False,exception=traceback.format_exc());save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name',help='Fresh owned OpalLayered-*.png filename')
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--controls-file',help='JSON object with exactly the desired reversible capture controls')
    group.add_argument('--controls',help='Inline JSON object with reversible capture controls')
    args=parser.parse_args();main(args.name,controls=args.controls,controls_file=args.controls_file)
