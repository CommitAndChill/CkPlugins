"""File-bridge client for the explicitly launched offscreen Adaptive studio."""
import argparse
import json
from pathlib import Path
import time
import uuid


def submit(action, timeout=300, **values):
    directory = Path(__file__).resolve().parents[2] / 'Saved/UsfMaterialGallery'
    request = directory / 'AdaptiveRequest.json'
    result = directory / 'AdaptiveResult.json'
    if request.exists():
        raise RuntimeError('An Adaptive command is already queued; inspect it before retrying')
    identity = str(uuid.uuid4())
    payload = {'id': identity, 'action': action, **values}
    temporary = request.with_suffix('.pending')
    temporary.write_text(json.dumps(payload), encoding='utf-8')
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
    raise RuntimeError('Adaptive command timed out; inspect the existing editor before retrying')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['state', 'prepare', 'scene', 'capture', 'quit'])
    parser.add_argument('--look')
    parser.add_argument('--name')
    parser.add_argument('--phase', type=float, default=0)
    parser.add_argument('--distance', type=float, default=4.8)
    parser.add_argument('--scalar', action='append', default=[])
    args = parser.parse_args()
    values = {key: value for key, value in vars(args).items() if key not in ['action', 'scalar'] and value is not None}
    values['scalars'] = {key: float(value) for key, value in (item.split('=', 1) for item in args.scalar)}
    print(json.dumps(submit(args.action, **values), indent=2))
