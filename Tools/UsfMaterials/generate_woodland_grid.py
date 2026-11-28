"""Generate an owned, deterministic 80 cm woodland grid; no Unreal process required."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'Plugins/CkTests/Resources/CkUsf/WoodlandGeometryV1'
NAME = 'SM_UsfWoodlandGrid'
SOURCE_NAME = NAME + '_v1'
CELLS = 256
WIDTH = 80.0


def build():
    lines = ['# CkUsf woodland grid v1; centimeters; KEEP_XYZ_AXES',
             'mtllib ' + SOURCE_NAME + '.mtl', 'o ' + NAME]
    for y in range(CELLS + 1):
        for x in range(CELLS + 1):
            lines.append(f'v {(x / CELLS - .5) * WIDTH:.9f} {(y / CELLS - .5) * WIDTH:.9f} 0')
    corners = [(-40, -40), (40, -40), (40, 40), (-40, 40)]
    for z in [-6.5, -9]:
        for x, y in corners:
            lines.append(f'v {x} {y} {z}')
    # Follow the proven import convention: source UV follows source XY.
    # The importer negates position Y and maps V to 1-V, preserving imported +V=+Y.
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
    receipt = {'generator': 'CkUsf.WoodlandGrid.v1', 'obj_file': SOURCE_NAME + '.obj',
               'mtl_file': SOURCE_NAME + '.mtl', 'mtl_sha256': hashlib.sha256(mtl).hexdigest(),
               'sha256': hashlib.sha256(data).hexdigest(), 'cells': [CELLS, CELLS],
               'top_vertices': (CELLS + 1) ** 2, 'vertices': (CELLS + 1) ** 2 + 8,
               'top_triangles': CELLS * CELLS * 2, 'triangles': CELLS * CELLS * 2 + len(faces),
               'width_cm': WIDTH, 'local_bounds': [[-40, -40, -9], [40, 40, 0]],
               'slab_top_cm': -6.5, 'slab_bottom_cm': -9, 'height_mip': 2,
               'maximum_relief_cm': 6, 'import_axes': 'KEEP_XYZ_AXES', 'import_scale': 1,
               'runtime_uv_basis': 'U=+localX,V=+localY; importer negates positionY and maps UV V to 1-sourceV',
               'slots': ['Specimen', 'CoreBase'], 'nanite': False,
               'positive_bounds_extension': [0, 0, 6], 'negative_bounds_extension': [0, 0, 6],
               'expanded_local_bounds': [[-40, -40, -15], [40, 40, 6]],
               'runtime_import_and_render_validation': 'Not performed by this source generator'}
    receipt['source_validation'] = validate_source(data, receipt)
    return data, receipt


def validate_source(data, receipt):
    vertices, uvs, normals, faces = [], [], [], []
    group = material = None
    libraries = []
    for line in data.decode('ascii').splitlines():
        fields = line.split()
        if not fields or fields[0].startswith('#'):
            continue
        kind = fields[0]
        if kind == 'v':
            vertices.append(tuple(map(float, fields[1:])))
        elif kind == 'vt':
            uvs.append(tuple(map(float, fields[1:])))
        elif kind == 'vn':
            normals.append(tuple(map(float, fields[1:])))
        elif kind == 'g':
            group = fields[1]
        elif kind == 'usemtl':
            material = fields[1]
        elif kind == 'mtllib':
            libraries.append(fields[1])
        elif kind == 'f':
            if group != material or material not in ['Specimen', 'CoreBase'] or len(fields) != 4:
                raise RuntimeError('Every triangle requires its matching named group/material')
            face = [tuple(map(int, field.split('/'))) for field in fields[1:]]
            if any(len(corner) != 3 or not (1 <= corner[0] <= len(vertices)
                   and 1 <= corner[1] <= len(uvs) and 1 <= corner[2] <= len(normals)) for corner in face):
                raise RuntimeError('Invalid OBJ position/UV/normal reference')
            faces.append((material, face))
    if (libraries != [receipt['mtl_file']] or len(vertices) != 66057 or len(uvs) != 66079
            or len(normals) != 6 or len(faces) != 131082):
        raise RuntimeError('Woodland source topology/material-library counts differ')
    counts, top_area = {'Specimen': 0, 'CoreBase': 0}, 0.0
    for material, face in faces:
        p = [vertices[corner[0] - 1] for corner in face]
        uv = [uvs[corner[1] - 1] for corner in face]
        a, b = [tuple(p[index][axis] - p[0][axis] for axis in range(3)) for index in [1, 2]]
        cross = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        area_uv = ((uv[1][0] - uv[0][0]) * (uv[2][1] - uv[0][1])
                   - (uv[1][1] - uv[0][1]) * (uv[2][0] - uv[0][0]))
        if abs(area_uv) <= 1e-10 or sum(value * value for value in cross) <= 1e-16:
            raise RuntimeError('Degenerate geometry or UV chart')
        if any(sum(cross[axis] * normals[corner[2] - 1][axis] for axis in range(3)) <= 0 for corner in face):
            raise RuntimeError('Triangle winding and supplied normals disagree')
        if material == 'Specimen':
            if any(point[2] != 0 for point in p) or cross[2] <= 0 or any(corner[0] != corner[1] for corner in face):
                raise RuntimeError('Specimen top must be planar and face +Z')
            top_area += cross[2] * .5
        elif any(point[2] not in [-6.5, -9] for point in p):
            raise RuntimeError('The entire neutral slab must stay below the six-centimeter recess')
        counts[material] += 1
    if counts != {'Specimen': 131072, 'CoreBase': 10} or abs(top_area - 6400) > 1e-6:
        raise RuntimeError('Woodland top area or section triangle counts differ')
    bounds = [[min(point[axis] for point in vertices) for axis in range(3)],
              [max(point[axis] for point in vertices) for axis in range(3)]]
    if bounds != [[-40, -40, -9], [40, 40, 0]]:
        raise RuntimeError('Woodland bounds differ from the eighty-centimeter patch')
    # Independent asymmetric probes verify the known importer transform, rather than a symmetric checker.
    lookup = {point: index for index, point in enumerate(vertices[:66049])}
    probes = []
    for point in [(-31.25, 17.5, 0), (21.5625, -8.125, 0)]:
        source_uv = uvs[lookup[point]]
        imported = [point[0], -point[1], point[2]]
        imported_uv = [source_uv[0], 1 - source_uv[1]]
        expected_uv = [(imported[0] + 40) / 80, (imported[1] + 40) / 80]
        if imported_uv != expected_uv:
            raise RuntimeError('Asymmetric imported U=+X/V=+Y basis prediction failed')
        probes.append({'source_position_cm': list(point), 'source_uv': list(source_uv),
                       'predicted_imported_position_cm': imported, 'predicted_imported_uv': imported_uv})
    return {'validated_source_vertices': len(vertices), 'validated_source_triangles': len(faces),
            'section_triangles': counts, 'top_area_cm2': top_area, 'asymmetric_basis_probes': probes}


def main():
    data, receipt = build()
    outputs = {DIRECTORY / (SOURCE_NAME + '.obj'): data,
               DIRECTORY / (SOURCE_NAME + '.mtl'): b'newmtl Specimen\nKd 0.5 0.5 0.5\nnewmtl CoreBase\nKd 0.18 0.18 0.18\n',
               DIRECTORY / (SOURCE_NAME + '.json'): (json.dumps(receipt, indent=2) + '\n').encode('utf-8')}
    # Validate every destination before writing any file. Never replace another grid version.
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
