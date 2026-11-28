"""Generate an owned, deterministic non-Nanite ground grid; no Unreal process required."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'Plugins/CkTests/Resources/CkUsf/Environment1Geometry'
NAME = 'SM_UsfGroundGrid'
SOURCE_NAME = NAME + '_v4'
CELLS = 256
WIDTH = 230.0


def build():
    lines = ['# CkUsf environment grid v4; centimeters; KEEP_XYZ_AXES',
             'mtllib ' + SOURCE_NAME + '.mtl', 'o ' + NAME]
    for y in range(CELLS + 1):
        for x in range(CELLS + 1):
            lines.append(f'v {(x / CELLS - .5) * WIDTH:.9f} {(y / CELLS - .5) * WIDTH:.9f} 0')
    corners = [(-115, -115), (115, -115), (115, 115), (-115, 115)]
    for z in [-12.5, -16]:
        for x, y in corners:
            lines.append(f'v {x} {y} {z}')
    # Import negates position Y AND maps V to 1-V. Exporting V=sourceY makes
    # imported V increase along imported +Y. v3's extra V flip reversed this basis.
    for y in range(CELLS + 1):
        for x in range(CELLS + 1):
            lines.append(f'vt {x / CELLS:.9f} {y / CELLS:.9f}')
    # Every neutral slab triangle gets a non-degenerate chart, independently of the top grid.
    for triangle in range(10):
        lines += ['vt 0 0', 'vt 1 0', 'vt 0 1']
    lines += ['vn 0 0 1', 'g Specimen', 'usemtl Specimen']
    for y in range(CELLS):
        for x in range(CELLS):
            a = y * (CELLS + 1) + x + 1
            b, c, d = a + 1, a + CELLS + 2, a + CELLS + 1
            lines += [f'f {a}/{a}/1 {b}/{b}/1 {c}/{c}/1', f'f {a}/{a}/1 {c}/{c}/1 {d}/{d}/1']
    start = (CELLS + 1) ** 2 + 1
    lines += ['vn 0 0 -1', 'vn 0 -1 0', 'vn 1 0 0', 'vn 0 1 0', 'vn -1 0 0',
              'g CoreBase', 'usemtl CoreBase']
    # Bottom and four slab sides; no coplanar top cap beneath the specimen.
    faces = [(4, 6, 5), (4, 7, 6)]
    for i in range(4):
        j = (i + 1) % 4
        faces += [(i, i + 4, j + 4), (i, j + 4, j)]
    for number, face in enumerate(faces):
        normal = 2 if number < 2 else 3 + (number - 2) // 2
        uv_start = (CELLS + 1) ** 2 + number * 3 + 1
        lines.append('f ' + ' '.join(f'{start + index}/{uv_start + corner}/{normal}'
                                    for corner, index in enumerate(face)))
    data = ('\n'.join(lines) + '\n').encode('ascii')
    mtl = b'newmtl Specimen\nKd 0.5 0.5 0.5\nnewmtl CoreBase\nKd 0.18 0.18 0.18\n'
    receipt = {'generator': 'CkUsf.EnvironmentGrid.v4', 'obj_file': SOURCE_NAME + '.obj',
               'mtl_file': SOURCE_NAME + '.mtl', 'mtl_sha256': hashlib.sha256(mtl).hexdigest(),
               'sha256': hashlib.sha256(data).hexdigest(), 'cells': [CELLS, CELLS],
               'top_vertices': (CELLS + 1) ** 2, 'vertices': (CELLS + 1) ** 2 + 8,
               'top_triangles': CELLS * CELLS * 2, 'triangles': CELLS * CELLS * 2 + len(faces),
               'width_cm': WIDTH, 'local_bounds': [[-115, -115, -16], [115, 115, 0]],
               'slab_top_cm': -12.5, 'slab_bottom_cm': -16, 'height_mip': 2,
               'maximum_relief_cm': 12, 'import_axes': 'KEEP_XYZ_AXES', 'import_scale': 1,
               'runtime_uv_basis': 'U=+localX,V=+localY; importer negates positionY and maps UV V to 1-sourceV',
               'slots': ['Specimen', 'CoreBase'], 'nanite': False}
    return data, receipt


def main():
    data, receipt = build()
    outputs = {DIRECTORY / (SOURCE_NAME + '.obj'): data,
               DIRECTORY / (SOURCE_NAME + '.mtl'): b'newmtl Specimen\nKd 0.5 0.5 0.5\nnewmtl CoreBase\nKd 0.18 0.18 0.18\n',
               DIRECTORY / (SOURCE_NAME + '.json'): (json.dumps(receipt, indent=2) + '\n').encode('utf-8')}
    # Validate every destination before writing either file. Never replace another grid version.
    for path, content in outputs.items():
        if path.exists() and path.read_bytes() != content:
            raise RuntimeError('Existing grid source differs; preserve it: ' + str(path))
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        if not path.exists():
            path.write_bytes(content)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
