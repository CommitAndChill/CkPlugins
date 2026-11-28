"""Original non-tiling molded optics. Preserves every TailLampV1 resource."""
from pathlib import Path
import hashlib
import io
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Plugins/CkTests/Resources/CkUsf/TailLampRefinedV1'


def main():
    width, height = 2048, 1024
    y, z = np.meshgrid((np.arange(width) + .5) * 24 / width - 12,
                       (np.arange(height) + .5) * 10 / height - 5)
    def smooth(a, b, value):
        t = np.clip((value - a) / (b - a), 0, 1)
        return t * t * (3 - 2 * t)
    def rounded_distance(x, yy, half_x, half_y, radius):
        qx, qy = np.abs(x) - half_x + radius, np.abs(yy) - half_y + radius
        return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - radius
    # The physical lens contour is 22.8x8.8cm with .9cm rounded corners.
    edge = rounded_distance(y, z, 11.4, 4.4, .9)
    field = 1 - smooth(-.68, -.38, edge)
    height_cm = np.zeros_like(y)
    zones = np.zeros_like(y)
    for center in [-7.15, 0, 7.15]:
        local = y - center
        boundary = rounded_distance(local, z, 3.22, 3.78, .85)
        zone = 1 - smooth(-.14, .06, boundary)
        # .48cm pillowed optical cells, shallow enough to retain six-chip readability.
        pillow = .00085 * np.cos(2 * np.pi * local / .48) * np.cos(2 * np.pi * z / .48)
        # Fan tooling on the top/bottom of each optical chamber; smooth center windows.
        fan = .0010 * np.cos(2 * np.pi * (local / .19 + .075 * z * z))
        upper_lower = smooth(1.85, 2.8, np.abs(z))
        height_cm += zone * (pillow * (1 - upper_lower) + fan * upper_lower)
        zones = np.maximum(zones, zone)
    # Keep a fine flute field in narrow dividers, surrounded by a continuous clear flange.
    height_cm += (1 - zones) * field * .00045 * np.cos(2 * np.pi * y / .16)
    height_cm *= field
    du = np.gradient(height_cm, 24 / width, axis=1)
    dv = np.gradient(height_cm, 10 / height, axis=0)
    normals = np.stack([-du, -dv, np.ones_like(y)], -1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    roughness = .075 * zones + .115 * (1 - zones)
    roughness = roughness * field + .16 * (1 - field)
    # Supporting rim and chamber webs have more material, not painted black borders.
    thickness = .47 + .30 * (1 - field) + .10 * (1 - zones) * field
    arrays = {'LensNormal': np.round((normals * .5 + .5) * 255).astype(np.uint8),
              'LensRoughness': np.round(roughness * 255).astype(np.uint8),
              'LensThickness': np.round(np.clip(thickness, 0, 1) * 65535).astype(np.uint16)}
    records = {}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    def write(path, data):
        if path.exists() and path.read_bytes() != data:
            raise RuntimeError('Preserve differing authored source: ' + str(path))
        if not path.exists():
            path.write_bytes(data)
    for key, array in arrays.items():
        stream = io.BytesIO()
        Image.fromarray(array).save(stream, format='PNG', compress_level=9)
        data = stream.getvalue()
        write(OUTPUT / (key + '.png'), data)
        records[key] = dict(file=key + '.png', sha256=hashlib.sha256(data).hexdigest(),
                            width=width, height=height, bit_depth=16 if key.endswith('Thickness') else 8,
                            srgb=False, range=[int(array.min()), int(array.max())])
    receipt = dict(generator='Tools/UsfMaterials/author_tail_lamp_refinement.py',
                   generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), maps=records,
                   provenance='Original analytical molded optical tooling, no external images, scans, random noise or baked illumination.',
                   units='centimeters; U=(Y+12)/24,V=Z/10, all maps use the same orientation',
                   features='Three rounded optical fields, .48cm shallow pillow cells, .19cm fan tooling, continuous smooth perimeter, thicker support webs.',
                   normal_convention='DirectX tangent; normalize(-dH/dUphysical,-dH/dVphysical,1); no green flip',
                   maximum_slope=float(np.hypot(du, dv).max()),
                   limits='Analytical normal/thickness textures on the existing single sheet, not geometric prism tracing or certified optics.')
    write(OUTPUT / 'Manifest.json', (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
