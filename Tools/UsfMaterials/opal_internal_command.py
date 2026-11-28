"""Serial UUID file bridge for the owned offscreen opal-internal studio."""
import argparse
import json
from pathlib import Path
import time
import uuid


def submit(action, timeout=300, **values):
    directory=Path(__file__).resolve().parents[2]/'Saved/UsfMaterialGallery'
    request,result=directory/'OpalInternalRequest.json',directory/'OpalInternalResult.json'
    lock=directory/'OpalInternalCommand.lock'
    if not result.is_file():
        raise RuntimeError('Launch the owned opal-internal session and wait for readiness')
    ready=json.loads(result.read_text())
    session=ready.get('session_id','')
    if str(uuid.UUID(session))!=session:
        raise RuntimeError('Missing owned session identity')
    identity=str(uuid.uuid4())
    # Exclusive creation serializes independent clients across the entire command lifetime.
    with lock.open('x') as stream:
        json.dump(dict(id=identity,session_id=session,action=action),stream)
    complete=False
    queued=False
    try:
        if request.exists():
            raise RuntimeError('An opal-internal command is already queued')
        temporary=request.with_suffix('.pending')
        temporary.write_text(json.dumps(dict(values,id=identity,session_id=session,action=action)))
        temporary.replace(request)
        queued=True
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if result.exists():
                data=json.loads(result.read_text())
                if data.get('session_id')!=session:
                    raise RuntimeError('Owned editor session changed; inspect before another command')
                if data.get('id')==identity:
                    complete=True
                    if not data.get('ok'):
                        raise RuntimeError(data.get('error',str(data)))
                    return data
            time.sleep(.25)
        raise RuntimeError('Opal-fire command timed out. Lock retained; inspect editor/result UUID before retrying. Do not launch another editor.')
    finally:
        if complete or not queued:
            lock.unlink()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','scene','state','comparison','diagnostics','capture','capture_primary','quit'])
    parser.add_argument('--name')
    parser.add_argument('--op',choices=['inspect','compile_comparison','shadow_mode'])
    parser.add_argument('--value',type=int,choices=[0,1])
    parser.add_argument('--variant',choices=['stack3','layered2'])
    parser.add_argument('--subject',choices=['opal'])
    parser.add_argument('--controls',help='JSON object containing reversible capture controls')
    parser.add_argument('--timeout',type=float,default=300)
    args=parser.parse_args()
    values=json.loads(args.controls) if args.controls else {}
    if not isinstance(values,dict) or set(values)&{'id','action','session_id'}:
        parser.error('Controls must be an object without ownership/action fields')
    if args.op:
        values['op']=args.op
    if args.value is not None:
        values['value']=args.value
    if args.variant:
        values['variant']=args.variant
    if args.name:
        values['name']=args.name
    if args.subject:
        values['subject']=args.subject
    print(json.dumps(submit(args.action,timeout=args.timeout,**values),indent=2))
