"""Matched, reversible hero polish captures in the owned offscreen studio."""
import copy
import hashlib
import json
from pathlib import Path
from amber_specimen_command import submit

OUTPUT = Path(__file__).resolve().parents[2] / 'Saved/UsfMaterialGallery'
BASE = dict(camera=[24, -11, 17], exposure=4.2, sky=.8,
    intensities=[7, 3, 10], source_radii=[.9, .45, .2],
    vectors={'Stem': {'TintColor': [.025, .018, .008, 1]}},
    hero_controls=dict(leaf_shadow=True, debris_shadow=True,
                       leaf_tint=[1, 1, 1, 1], leaf_transmission=.7))


def main():
    variants = {'Baseline': {}, 'SoftRear': dict(source_radii=[.9, .45, 1.2]),
        'Sediment': dict(vectors={'Stem': {'TintColor': [.10, .055, .02, 1]}},
                         hero_controls=dict(debris_shadow=False)),
        'Camera': dict(camera=[25, -10, 14]),
        'Combined': dict(camera=[25, -10, 14], source_radii=[.9, .45, 1.2],
            vectors={'Stem': {'TintColor': [.10, .055, .02, 1]}},
            hero_controls=dict(debris_shadow=False)),
        'LeafQuiet': dict(source_radii=[.9, .45, 1.2],
            vectors={'Stem': {'TintColor': [.10, .055, .02, 1]}},
            hero_controls=dict(debris_shadow=False, leaf_tint=[.65, .65, .65, 1], leaf_transmission=.45))}
    receipt = {}
    for name, overrides in variants.items():
        values = copy.deepcopy(BASE)
        for key, value in overrides.items():
            if key == 'hero_controls':
                values[key].update(value)
            else:
                values[key] = value
        result = submit('capture', name='AmberPolish-' + name + '.png', **values)
        path = Path(result['capture'])
        receipt[name] = dict(request=values, state=result['state'],
            file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        print(name, flush=True)
    (OUTPUT / 'AmberPolish-Probes.json').write_text(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
