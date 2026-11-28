"""Temporary owned rendered normal/UV diagnostics with exact source recovery."""
from pathlib import Path
from tail_lamp_command import submit
from verify_industrial_reload import wait_reload

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/OpticalTailLampLens.ush'
LOG = ROOT / 'Saved/Logs/CkPlugins.log'


def main():
    original = PATH.read_bytes()
    owned = original
    anchor = b'    return O;'
    if original.count(anchor) != 1:
        raise RuntimeError('Diagnostic anchor differs')
    try:
        for label, emission in [('Normal', b'float3(saturate(O.Normal.x * 8.0 + 0.5), saturate(O.Normal.y * 8.0 + 0.5), 0.0)'),
                                ('UV', b'float3(frac(In.UV.x * 16.0), frac(In.UV.y * 8.0), 0.0)')]:
            if PATH.read_bytes() != owned:
                raise RuntimeError('Preserve concurrent source edit')
            owned = original.replace(anchor, b'    O.F0 = 0.0; O.TransmittanceColor = 0.001.xxx; O.EmissiveColor = ' + emission + b' * 20.0;\n' + anchor)
            offset = LOG.stat().st_size
            PATH.write_bytes(owned)
            print(wait_reload(offset))
            print(submit('capture', name='TailLamp-Diagnostic-' + label + '.png',
                         scalars={'OpticalTailLampLens': {'UVScale': 1, 'NormalStrength': 1, 'DistortionStrength': .02}}, exposure=5)['capture'])
    finally:
        if PATH.read_bytes() != owned:
            raise RuntimeError('Preserve concurrent source edit; inspect diagnostic source')
        offset = LOG.stat().st_size
        PATH.write_bytes(original)
        print(wait_reload(offset))


if __name__ == '__main__':
    main()
