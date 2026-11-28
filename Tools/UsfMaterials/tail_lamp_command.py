"""Serial UUID file bridge for the owned offscreen optical studio."""
import argparse
import json
from pathlib import Path
import time
import uuid


def submit(action, timeout=300, **values):
    directory = Path(__file__).resolve().parents[2] / 'Saved/UsfMaterialGallery'
    request, result = directory / 'TailLampRequest.json', directory / 'TailLampResult.json'
    if request.exists():
        raise RuntimeError('An optical command is already queued; inspect the owned editor')
    identity = str(uuid.uuid4())
    temporary = request.with_suffix('.pending')
    temporary.write_text(json.dumps(dict(id=identity, action=action, **values)), encoding='utf-8')
    temporary.replace(request)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result.exists():
            data = json.loads(result.read_text(encoding='utf-8'))
            if data.get('id') == identity:
                if not data.get('ok'):
                    raise RuntimeError(data.get('error', str(data)))
                return data
        time.sleep(.25)
    raise RuntimeError('Optical command timed out; inspect existing editor, do not duplicate')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'prepare_refined', 'scene', 'state', 'capture', 'quit'])
    parser.add_argument('--name')
    parser.add_argument('--refined', action='store_true', help='Load both original and refined finishes for scene comparison')
    args = parser.parse_args()
    if args.refined and args.action != 'scene':
        parser.error('--refined requires scene')
    values = {'name': args.name} if args.name else {}
    if args.refined:
        values['refined'] = True
    print(json.dumps(submit(args.action, **values), indent=2))
