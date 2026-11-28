"""Serial UUID file bridge for the owned offscreen amber studio."""
import argparse
import json
from pathlib import Path
import time
import uuid


def submit(action, timeout=300, **values):
    directory = Path(__file__).resolve().parents[2] / 'Saved/UsfMaterialGallery'
    request, result = directory / 'AmberRequest.json', directory / 'AmberResult.json'
    if request.exists():
        raise RuntimeError('An amber command is already queued; inspect the owned editor')
    identity = str(uuid.uuid4())
    temporary = request.with_suffix('.pending')
    temporary.write_text(json.dumps(dict(id=identity, action=action, **values)))
    temporary.replace(request)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result.exists():
            data = json.loads(result.read_text())
            if data.get('id') == identity:
                if not data.get('ok'):
                    raise RuntimeError(data.get('error', str(data)))
                return data
        time.sleep(.25)
    raise RuntimeError('Amber command timed out; inspect existing editor, do not duplicate')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'scene', 'hero', 'state', 'capture', 'quit'])
    parser.add_argument('--name')
    args = parser.parse_args()
    print(json.dumps(submit(args.action, **({'name': args.name} if args.name else {})), indent=2))
