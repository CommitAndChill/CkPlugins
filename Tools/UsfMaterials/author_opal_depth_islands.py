"""Immutable front-facing mineral patches cut from the pinned AmberHero surface.

Run with Python + NumPy + Pillow + SciPy. Geometry is baked at the midpoint
between the separate clear exterior and recessed core; actor transform is identity.
"""
from pathlib import Path
import hashlib
import json
import math
from collections import Counter
import numpy as np
from PIL import Image
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Plugins/CkTests/Resources/CkUsf/OpalDepthIslandsV1'
SCALE = np.array([.9285714285, .9727272725, .961928934])
CORE_SCALE = np.array([.857142857, .945454545, .923857868])
CENTER = np.array([0., 0., 4.06])
SEED = 80423


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(relative, data):
    path = OUT/relative
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError('Preserve differing immutable island source: '+str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
    return dict(path=relative, sha256=hashlib.sha256(data).hexdigest())


def clip_triangle(attributes, polygon):
    """Clip in physical YZ, interpolating source XYZ/UV/smooth-normal attributes."""
    values = list(attributes)
    for index in range(len(polygon)):
        a, b = polygon[index], polygon[(index+1) % len(polygon)]
        edge = b-a
        def distance(value):
            q = value[1:3]-a
            return edge[0]*q[1]-edge[1]*q[0]
        result = []
        if not values:
            break
        previous, previous_d = values[-1], distance(values[-1])
        for current in values:
            current_d = distance(current)
            if (current_d >= 0) != (previous_d >= 0):
                result.append(previous+(current-previous)*(previous_d/(previous_d-current_d)))
            if current_d >= 0:
                result.append(current)
            previous, previous_d = current, current_d
        values = result
    return values


def main():
    body_manifest = ROOT/'Plugins/CkTests/Resources/CkUsf/AmberHeroV1/Manifest.json'
    body_record = json.loads(body_manifest.read_text())['meshes']['Body']
    body_path = body_manifest.parent/body_record['path']
    color_manifest = ROOT/'Plugins/CkTests/Resources/CkUsf/OpalPolishV2/OpalTextures.json'
    color_record = json.loads(color_manifest.read_text())['maps']['OpalColor']
    color_path = color_manifest.parent/color_record['path']
    if sha(body_path) != body_record['sha256'] or sha(color_path) != color_record['sha256']:
        raise RuntimeError('Pinned read-only Body/color source changed')
    positions, uv, normals, faces = [], [], [], []
    for line in body_path.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v': positions.append(list(map(float, fields[1:])))
        elif fields[0] == 'vt': uv.append(list(map(float, fields[1:])))
        elif fields[0] == 'vn': normals.append(list(map(float, fields[1:])))
        elif fields[0] == 'f':
            corners = [[int(value)-1 for value in corner.split('/')] for corner in fields[1:]]
            if len(corners) != 3 or any(a != b or a != c for a, b, c in corners):
                raise RuntimeError('Expected pinned Body unified triangular attributes')
            faces.append([corner[0] for corner in corners])
    p, f, uv, n = map(np.asarray, [positions, faces, uv, normals])
    tri = p[f]
    crosses = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    lengths = np.linalg.norm(crosses, axis=1)
    face_normals = crosses/lengths[:, None]
    centroids = tri.mean(1)
    projected_front_area = float(np.sum(np.abs(crosses[centroids[:, 0] > 0, 0]))*.5*SCALE[1]*SCALE[2])
    image = np.asarray(Image.open(color_path).convert('RGB'), dtype=float)/255
    face_uv = uv[f].mean(1)
    pixel = np.clip(np.rint(face_uv*(np.array(image.shape[:2][::-1])-1)).astype(int), 0, image.shape[0]-1)
    rgb = image[pixel[:, 1], pixel[:, 0]]
    chroma = (rgb.max(1)-rgb.min(1))/np.maximum(rgb.max(1), .001)
    eligible = ((centroids[:, 0] > .65) & (face_normals[:, 0] > .5)
                & (np.abs(centroids[:, 1]) < 4.25) & (centroids[:, 2] > 1.15)
                & (centroids[:, 2] < 6.95) & (chroma > .48))
    rng = np.random.default_rng(SEED)
    scores = chroma+rng.uniform(0, .08, len(chroma))
    selected = []
    for index in np.argsort(scores)[::-1]:
        if eligible[index] and all(np.linalg.norm(centroids[index, 1:3]-centroids[other, 1:3]) > .88 for other in selected):
            selected.append(int(index))
            if len(selected) == 20:
                break
    if len(selected) != 20:
        raise RuntimeError('Could not fit twenty separated chromatic patches')
    attributes = np.concatenate([p, uv, n], axis=1)
    output, triangles, patches = [], [], []
    front_indices = np.flatnonzero((centroids[:, 0] > .35) & (face_normals[:, 0] > .3))
    for patch, index in enumerate(selected):
        center = centroids[index, 1:3]
        angle = rng.uniform(0, 2*math.pi)
        theta = np.linspace(0, 2*math.pi, 10, endpoint=False)
        radius = .4*(.94+.035*np.sin(3*theta+angle)+.025*np.cos(2*theta-angle))
        polygon = np.stack([np.cos(theta)*radius, np.sin(theta)*radius*.93], axis=1)+center
        start = len(triangles)
        remap = {}
        for source_face in front_indices:
            source = attributes[f[source_face]]
            if np.any(source[:, 1:3].max(0) < polygon.min(0)) or np.any(source[:, 1:3].min(0) > polygon.max(0)):
                continue
            clipped = clip_triangle(source, polygon)
            if len(clipped) < 3:
                continue
            ids = []
            for item in clipped:
                key = tuple(np.round(item[:3], 8))
                if key not in remap:
                    remap[key] = len(output)
                    output.append(item)
                ids.append(remap[key])
            for corner in range(1, len(ids)-1):
                face = [ids[0], ids[corner], ids[corner+1]]
                points = np.array([output[k][:3] for k in face])
                if np.linalg.norm(np.cross(points[1]-points[0], points[2]-points[0])) > 1e-10:
                    triangles.append(face)
        patches.append(dict(index=patch, source_face=index, center_yz_cm=center.tolist(),
                            center_chroma=float(chroma[index]), triangles=len(triangles)-start))
    output, triangles = np.asarray(output), np.asarray(triangles)
    vertices = CENTER+(output[:, :3]-CENTER)*SCALE
    authored_normals = output[:, 5:8]/SCALE
    authored_normals /= np.linalg.norm(authored_normals, axis=1)[:, None]
    q = vertices[triangles]
    cross = np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0])
    areas = np.linalg.norm(cross, axis=1)*.5
    if not np.isfinite(output).all() or np.any(areas < 1e-11) or np.any(cross[:, 0] <= 0):
        raise RuntimeError('Invalid front-facing island geometry')
    normal_dot = np.sum(cross/np.linalg.norm(cross, axis=1)[:, None]*authored_normals[triangles].mean(1), axis=1)
    if np.any(normal_dot <= .9):
        raise RuntimeError('Island smooth normals disagree with triangle winding')
    edges = Counter(tuple(sorted((int(a), int(b)))) for face in triangles for a, b in zip(face, np.roll(face, -1)))
    if any(value > 2 for value in edges.values()):
        raise RuntimeError('Nonmanifold patch edges')
    adjacency = {int(k): set() for k in triangles.flat}
    for a, b in edges:
        adjacency[a].add(b); adjacency[b].add(a)
    components = []
    unseen = set(adjacency)
    while unseen:
        pending = [unseen.pop()]; component = []
        while pending:
            vertex = pending.pop(); component.append(vertex)
            found = adjacency[vertex] & unseen; unseen.difference_update(found); pending.extend(found)
        components.append(component)
    if len(components) != 20:
        raise RuntimeError('Expected exactly twenty disconnected filled islands')
    for component in components:
        member = set(component)
        component_edges = [edge for edge in edges if edge[0] in member]
        component_faces = [face for face in triangles if int(face[0]) in member]
        if len(component)-len(component_edges)+len(component_faces) != 1:
            raise RuntimeError('Patch must be a filled disk without holes')
    coverage = float(np.sum(cross[:, 0])*.5/projected_front_area)
    if not .10 <= coverage <= .15:
        raise RuntimeError('Projected patch coverage outside 10-15 percent: '+str(coverage))
    shell_normals = face_normals
    shell_offsets = -np.sum(shell_normals*tri[:, 0], axis=1)
    shell_max = -np.inf
    for start in range(0, len(f), 256):
        shell_max = max(shell_max, float(np.max(vertices@shell_normals[start:start+256].T+shell_offsets[start:start+256])))
    core = CENTER+(p-CENTER)*CORE_SCALE
    hull = ConvexHull(core)
    core_separation = np.full(len(triangles), -np.inf)
    for start in range(0, len(hull.equations), 256):
        eq = hull.equations[start:start+256]
        distances = vertices@eq[:, :3].T+eq[:, 3]
        core_separation = np.maximum(core_separation, distances[triangles].min(axis=1).max(axis=1))
    if shell_max >= 0 or np.min(core_separation) <= 0:
        raise RuntimeError('Island triangles intersect shell/core separation regions')
    component_spans = [np.ptp(vertices[component], axis=0) for component in components]
    if any(max(span[1:]) > .8 or max(span[1:]) < .3 for span in component_spans):
        raise RuntimeError('Island dimensions outside 3-8mm')
    lines = ['# Pinned Body front triangle subsets; centimeters; baked midpoint transform; identity actor',
             'mtllib SM_OpalDepth_Islands.mtl', 'g Body', 'usemtl Body', 's 1']
    lines += ['v %.9f %.9f %.9f' % tuple(value) for value in vertices]
    lines += ['vt %.9f %.9f' % tuple(value) for value in output[:, 3:5]]
    lines += ['vn %.9f %.9f %.9f' % tuple(value) for value in authored_normals]
    lines += ['f '+' '.join('%d/%d/%d' % (k+1, k+1, k+1) for k in face) for face in triangles]
    mesh = write('Meshes/SM_OpalDepth_Islands.obj', ('\n'.join(lines)+'\n').encode('ascii'))
    mesh['mtl'] = write('Meshes/SM_OpalDepth_Islands.mtl', b'newmtl Body\nKd 0.5 0.3 0.1\nd 1\n')
    checks = dict(vertices=len(vertices), triangles=len(triangles), slot='Body', disconnected_filled_patches=len(components),
        patch_spans_cm=[span.tolist() for span in component_spans], projected_visible_coverage=coverage,
        coverage_scope='Projected +X front area, not arbitrary-camera pixel coverage', degenerate_triangles=0,
        minimum_triangle_area_cm2=float(areas.min()), minimum_normal_winding_dot=float(normal_dot.min()),
        boundary_edges=sum(value == 1 for value in edges.values()), filled_disk_euler_verified=True,
        shell_triangle_plane_clearance_lower_bound_cm=-shell_max,
        core_convex_hull_plane_separation_lower_bound_cm=float(np.min(core_separation)),
        floor_clearance_cm=float(vertices[:, 2].min()-.11), bounds=dict(min=vertices.min(0).tolist(), max=vertices.max(0).tolist()))
    source_paths = [body_path, body_manifest, color_path, color_manifest]
    manifest = dict(schema_version=1, generator_source=Path(__file__).relative_to(ROOT).as_posix(), generator_sha256=sha(Path(__file__)),
        source_hashes={path.relative_to(ROOT).as_posix(): sha(path) for path in source_paths}, seed=SEED,
        representation='Twenty disconnected filled opaque front-facing mineral patches; geometric gaps, no masks or image edits',
        source_uvs='Original Body UVs, barycentrically interpolated on clipped source triangles; image samples use row=V*(height-1)',
        baked_scale=SCALE.tolist(), baked_center=CENTER.tolist(), actor_transform='Identity; do not apply inset twice',
        mesh=mesh, geometry_checks=checks, patches=patches,
        limitations=['Open one-sided patches: rear/edge views intentionally reveal gaps and recessed core.',
                     'Plane tests provide conservative positive separation bounds, not exact triangle distance or optical ray thickness.',
                     'Selected artwork chroma is an artistic placement criterion, not measured opal structure.',
                     'No rendered appearance or visual acceptance is established by geometry generation.'])
    record = write('Manifest.json', (json.dumps(manifest, indent=2)+'\n').encode())
    print(json.dumps(dict(manifest=record, geometry_checks=checks), indent=2))


if __name__ == '__main__':
    main()
