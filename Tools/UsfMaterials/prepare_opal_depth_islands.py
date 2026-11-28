"""Import only the new pinned depth-island mesh; all Body/artwork sources are read-only.

verify_existing() returns (mesh, report) without importing, saving, or scene changes.
prepare() imports the exact missing destination once and returns the same report.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import unreal

OWNER = 'CkUsf.OpalDepthIslandsPreparation.v1'
MESH_PATH = '/CkTests/CkUsf/Showcase/OpalDepth/SM_OpalDepth_Islands'
MANIFEST_PATH = 'Plugins/CkTests/Resources/CkUsf/OpalDepthIslandsV1/Manifest.json'
GENERATOR_PATH = 'Tools/UsfMaterials/author_opal_depth_islands.py'


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sources():
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    manifest_path = root/MANIFEST_PATH
    document = json.loads(manifest_path.read_text(encoding='utf-8'))
    source_hashes = {MANIFEST_PATH: _sha(manifest_path)}

    def checked(relative, pin):
        path = (root/relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(root) or not path.is_file() or _sha(path) != pin:
            raise RuntimeError('Preserve missing/revised island source: '+relative)
        source_hashes[relative] = pin
        return path

    if document.get('schema_version') != 1 or document.get('generator_source') != GENERATOR_PATH:
        raise RuntimeError('Exact island source schema/generator required')
    checked(GENERATOR_PATH, document['generator_sha256'])
    required_sources = {
        'Plugins/CkTests/Resources/CkUsf/AmberHeroV1/Meshes/SM_AmberHero_Body.obj',
        'Plugins/CkTests/Resources/CkUsf/AmberHeroV1/Manifest.json',
        'Plugins/CkTests/Resources/CkUsf/OpalPolishV2/Textures/OpalColor.png',
        'Plugins/CkTests/Resources/CkUsf/OpalPolishV2/OpalTextures.json'}
    if set(document['source_hashes']) != required_sources:
        raise RuntimeError('Exact read-only Body/artwork source chain required')
    for relative, pin in document['source_hashes'].items():
        checked(relative, pin)
    folder = manifest_path.parent.relative_to(root).as_posix()
    mesh = document['mesh']
    if mesh['path'] != 'Meshes/SM_OpalDepth_Islands.obj' or mesh['mtl']['path'] != 'Meshes/SM_OpalDepth_Islands.mtl':
        raise RuntimeError('Exact additive island OBJ/MTL destinations required')
    obj = checked(folder+'/'+mesh['path'], mesh['sha256'])
    checked(folder+'/'+mesh['mtl']['path'], mesh['mtl']['sha256'])
    checks = document['geometry_checks']
    if (document['actor_transform'] != 'Identity; do not apply inset twice'
            or document['baked_scale'] != [.9285714285, .9727272725, .961928934]
            or document['baked_center'] != [0., 0., 4.06]
            or checks['slot'] != 'Body' or checks['disconnected_filled_patches'] != 20
            or checks['degenerate_triangles'] != 0 or not checks['filled_disk_euler_verified']
            or not .10 <= checks['projected_visible_coverage'] <= .15
            or min(checks['shell_triangle_plane_clearance_lower_bound_cm'], checks['core_convex_hull_plane_separation_lower_bound_cm']) <= 0):
        raise RuntimeError('Island physical representation/positive separation differs')
    vertices, normals, uvs, faces, slots = [], [], [], [], []
    for line in obj.read_text(encoding='ascii').splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v': vertices.append(tuple(map(float, fields[1:])))
        elif fields[0] == 'vn': normals.append(tuple(map(float, fields[1:])))
        elif fields[0] == 'vt': uvs.append(tuple(map(float, fields[1:])))
        elif fields[0] == 'usemtl': slots.append(fields[1])
        elif fields[0] == 'f':
            corners = [[int(value)-1 for value in corner.split('/')] for corner in fields[1:]]
            if len(corners) != 3 or any(a != b or a != c for a, b, c in corners):
                raise RuntimeError('Islands require unified triangular source attributes')
            faces.append(tuple(corner[0] for corner in corners))
    if slots != ['Body'] or len(vertices) != checks['vertices'] or len(faces) != checks['triangles'] or len(uvs) != len(vertices) or len(normals) != len(vertices):
        raise RuntimeError('Island OBJ counts/material slot differ from pinned manifest')
    if not all(math.isfinite(value) for row in vertices+normals+uvs for value in row):
        raise RuntimeError('Nonfinite island geometry')
    if any(abs(sum(value*value for value in normal)-1) > 1e-6 for normal in normals):
        raise RuntimeError('Island authored smooth normals are not unit vectors')
    edges = Counter()
    adjacency = {index: set() for face in faces for index in face}
    for face in faces:
        if any(index < 0 or index >= len(vertices) for index in face):
            raise RuntimeError('Island OBJ has invalid vertex index')
        a, b, c = [vertices[index] for index in face]
        ab, ac = [b[k]-a[k] for k in range(3)], [c[k]-a[k] for k in range(3)]
        cross = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0]]
        if cross[0] <= 0 or sum(value*value for value in cross) <= 1e-22:
            raise RuntimeError('Island winding/triangle degeneracy differs')
        for x, y in zip(face, face[1:]+face[:1]):
            edges[tuple(sorted((x, y)))] += 1
            adjacency[x].add(y); adjacency[y].add(x)
    if any(value > 2 for value in edges.values()):
        raise RuntimeError('Nonmanifold island edges')
    unseen, components = set(adjacency), []
    while unseen:
        pending, component = [unseen.pop()], set()
        while pending:
            index = pending.pop(); component.add(index)
            found = adjacency[index] & unseen; unseen.difference_update(found); pending.extend(found)
        components.append(component)
    if len(components) != 20:
        raise RuntimeError('Island source no longer contains twenty disconnected filled patches')
    for component in components:
        edge_count = sum(a in component for a, _ in edges)
        face_count = sum(face[0] in component for face in faces)
        if len(component)-edge_count+face_count != 1:
            raise RuntimeError('Island source patch is not a filled disk')
    report = dict(owner=OWNER, mesh_path=MESH_PATH, mesh_object=MESH_PATH+'.SM_OpalDepth_Islands',
        manifest_path=MANIFEST_PATH, manifest_sha256=source_hashes[MANIFEST_PATH], mesh_sha256=mesh['sha256'],
        source_hashes=source_hashes, geometry_checks=checks, actor_transform='Identity; baked midpoint inset')
    return obj, report


def _validate_asset(mesh, source, report):
    if not isinstance(mesh, unreal.StaticMesh) or mesh.get_path_name() != report['mesh_object']:
        raise RuntimeError('Preserve missing/different island mesh class/path')
    if unreal.EditorAssetLibrary.get_metadata_tag(mesh, OWNER) != report['mesh_sha256'] or unreal.EditorAssetLibrary.get_metadata_tag(mesh, OWNER+'.Manifest') != MANIFEST_PATH+':'+report['manifest_sha256']:
        raise RuntimeError('Preserve differently owned/revised island mesh')
    if [str(item.material_slot_name) for item in mesh.static_materials] != ['Body']:
        raise RuntimeError('Island mesh requires exactly the named Body material slot')
    if mesh.get_editor_property('nanite_settings').get_editor_property('enabled'):
        raise RuntimeError('Preserve changed island Nanite setting')
    data = mesh.get_editor_property('asset_import_data')
    if not data or [str(Path(value).resolve()) for value in data.extract_filenames()] != [str(source)]:
        raise RuntimeError('Preserve changed island import source')
    for field, expected in [('convert_scene', False), ('convert_scene_unit', False), ('import_uniform_scale', 1.),
                            ('remove_degenerates', False), ('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS),
                            ('coordinate_system_policy', unreal.CoordinateSystemPolicy.KEEP_XYZ_AXES)]:
        if data.get_editor_property(field) != expected:
            raise RuntimeError('Preserve changed island import setting: '+field)


def verify_existing():
    """Read-only scene preflight. Returns (StaticMesh, JSON-compatible provenance report)."""
    source, report = _sources()
    mesh = unreal.load_asset(MESH_PATH)
    _validate_asset(mesh, source, report)
    return mesh, report


def prepare():
    """Import only the missing exact owned destination; never replace/reimport existing assets."""
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Prepare island mesh outside PIE')
    source, report = _sources()
    mesh = unreal.load_asset(MESH_PATH)
    if unreal.EditorAssetLibrary.does_asset_exist(MESH_PATH):
        _validate_asset(mesh, source, report)
        return report
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = MESH_PATH.rsplit('/', 1)[0]
    task.destination_name = MESH_PATH.rsplit('/', 1)[1]
    task.automated = True
    task.replace_existing = False
    task.save = False
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_materials, options.import_textures = True, False, False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, False
    data.convert_scene, data.convert_scene_unit, data.import_uniform_scale = False, False, 1
    data.set_editor_property('coordinate_system_policy', unreal.CoordinateSystemPolicy.KEEP_XYZ_AXES)
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    # Clipping creates legitimate small boundary triangles; do not silently discard them.
    data.remove_degenerates = False
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = task.get_objects()
    if len(objects) != 1 or not isinstance(objects[0], unreal.StaticMesh) or objects[0].get_path_name() != report['mesh_object']:
        raise RuntimeError('Unexpected island import output; preserve it for inspection')
    mesh = objects[0]
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.set_editor_property('enabled', False)
    mesh.set_editor_property('nanite_settings', nanite)
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, OWNER, report['mesh_sha256'])
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, OWNER+'.Manifest', MANIFEST_PATH+':'+report['manifest_sha256'])
    _validate_asset(mesh, source, report)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('Could not save owned island mesh')
    return report
