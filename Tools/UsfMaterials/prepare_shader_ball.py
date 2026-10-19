"""Run from Unreal's Python console before PIE; creates only this gallery's assets.

Downloads the CC BY 4.0 USD shader ball at a resolved immutable upstream commit,
converts its scene into a normalized two-slot OBJ, imports it, and generates looks.
The upstream source, attribution, hashes, and converted OBJ remain under Resources.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import urllib.request

REPO = "KhronosGroup/glTF-Sample-Assets"
MODEL = "Models/USDShaderBallForGltf"
IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
CONVERSION_VERSION = 3


def export_axes(value):
    # Right-handed glTF: +Y up, +Z specimen front. Write right-handed Z-up
    # coordinates with the front toward -X. Unreal KeepXYZAxes handles its Y flip.
    return (-value[2], -value[0], value[1])


def repair_unmapped_faces(vertices, normals, uvs, triangles):
    repaired = 0
    result = []
    for slot, face in triangles:
        indices = [value-1 for value in face]
        a, b, c = [uvs[index] for index in indices]
        determinant = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        if abs(determinant) < 1e-12:
            points = [vertices[index] for index in indices]
            e = [points[1][k]-points[0][k] for k in range(3)]
            f = [points[2][k]-points[0][k] for k in range(3)]
            cross = [e[1]*f[2]-e[2]*f[1], e[2]*f[0]-e[0]*f[2], e[0]*f[1]-e[1]*f[0]]
            axis = max(range(3), key=lambda k: abs(cross[k]))
            if abs(cross[axis]) < 1e-12:
                raise ValueError("Zero-area geometry cannot have a valid tangent basis")
            projection = [(1, 2), (2, 0), (0, 1)][axis]
            # Split only unmapped corners; preserve valid charts and exact normals.
            replacement = []
            for index, point in zip(indices, points):
                vertices.append(point)
                normals.append(normals[index])
                uvs.append(tuple(point[k] for k in projection))
                replacement.append(len(vertices))
            face = replacement
            repaired += 1
        result.append((slot, face))
    return result, repaired


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "CkUsf-Material-Gallery"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def multiply(a, b):
    return [sum(a[k * 4 + row] * b[col * 4 + k] for k in range(4))
            for col in range(4) for row in range(4)]


def node_matrix(node):
    if "matrix" in node:
        return node["matrix"]
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    sx, sy, sz = node.get("scale", [1, 1, 1])
    tx, ty, tz = node.get("translation", [0, 0, 0])
    return [(1-2*y*y-2*z*z)*sx, (2*x*y+2*z*w)*sx, (2*x*z-2*y*w)*sx, 0,
            (2*x*y-2*z*w)*sy, (1-2*x*x-2*z*z)*sy, (2*y*z+2*x*w)*sy, 0,
            (2*x*z+2*y*w)*sz, (2*y*z-2*x*w)*sz, (1-2*x*x-2*y*y)*sz, 0,
            tx, ty, tz, 1]


def transform_position(m, p):
    return [sum(m[k*4 + row] * p[k] for k in range(3)) + m[12+row] for row in range(3)]


def transform_normal(m, n):
    # Cofactor matrix is the inverse transpose, up to a common determinant.
    a, b, c = m[0], m[4], m[8]
    d, e, f = m[1], m[5], m[9]
    g, h, i = m[2], m[6], m[10]
    det = a*(e*i-f*h) - b*(d*i-f*g) + c*(d*h-e*g)
    if abs(det) < 1e-12:
        raise ValueError("Singular shader-ball node transform")
    cofactors = [[e*i-f*h, f*g-d*i, d*h-e*g],
                 [c*h-b*i, a*i-c*g, b*g-a*h],
                 [b*f-c*e, c*d-a*f, a*e-b*d]]
    value = [sum(cofactors[row][k]*n[k] for k in range(3))/det for row in range(3)]
    length = math.sqrt(sum(v*v for v in value))
    if length < 1e-12:
        raise ValueError("Zero shader-ball normal")
    return [v/length for v in value]


def imported_mesh_from_task(task, object_path, source_path):
    # Loading the destination alone can return the old mesh after a failed import.
    imported = [value for value in task.get_objects() if value.get_path_name() == object_path]
    if len(imported) != 1:
        raise RuntimeError("Shader-ball import did not return the updated target; the old asset was not marked repaired")
    mesh = imported[0]
    filename = mesh.get_editor_property("asset_import_data").get_first_filename()
    if Path(filename).resolve() != source_path.resolve():
        raise RuntimeError("Shader-ball import retained an old source filename; refusing to mark it repaired")
    return mesh


def convert_glb(data, output):
    magic, version, size = struct.unpack_from("<III", data)
    if magic != 0x46546C67 or version != 2 or size != len(data):
        raise ValueError("Expected an intact glTF 2 binary asset")
    chunks, offset = {}, 12
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        chunks[kind] = data[offset+8:offset+8+length]
        offset += 8+length
    scene = json.loads(chunks[0x4E4F534A])
    binary = chunks[0x004E4942]
    if len(scene.get("buffers", [])) != 1 or "uri" in scene["buffers"][0]:
        raise ValueError("Only embedded single-buffer shader balls are supported")

    def accessor(index):
        entry = scene["accessors"][index]
        if "sparse" in entry or entry.get("normalized", False):
            raise ValueError("Sparse/normalized mesh accessors require explicit conversion")
        view = scene["bufferViews"][entry["bufferView"]]
        count = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[entry["type"]]
        fmt = "<" + {5121: "B", 5123: "H", 5125: "I", 5126: "f"}[entry["componentType"]]*count
        stride = view.get("byteStride", struct.calcsize(fmt))
        start = view.get("byteOffset", 0) + entry.get("byteOffset", 0)
        return [struct.unpack_from(fmt, binary, start + row*stride) for row in range(entry["count"])]

    materials = scene.get("materials", [])
    specimen_materials = {index for index, material in enumerate(materials)
                          if "KHR_materials_transmission" in material.get("extensions", {})}
    if len(specimen_materials) != 1:
        raise ValueError("Cannot unambiguously identify the upstream outer specimen material")
    vertices, normals, uvs, triangles = [], [], [], []

    def visit(index, parent):
        node = scene["nodes"][index]
        matrix = multiply(parent, node_matrix(node))
        if "mesh" in node:
            for primitive in scene["meshes"][node["mesh"]]["primitives"]:
                if primitive.get("mode", 4) != 4 or "targets" in primitive:
                    raise ValueError("Expected static triangle-list shader-ball primitives")
                attrs = primitive["attributes"]
                positions, ns, ts = [accessor(attrs[name]) for name in ("POSITION", "NORMAL", "TEXCOORD_0")]
                if len(positions) != len(ns) or len(ns) != len(ts):
                    raise ValueError("Shader-ball vertex attributes have different lengths")
                first = len(vertices)
                vertices.extend(transform_position(matrix, p) for p in positions)
                normals.extend(transform_normal(matrix, n) for n in ns)
                uvs.extend(ts)
                indices = [v[0] for v in accessor(primitive["indices"])] if "indices" in primitive else list(range(len(positions)))
                if len(indices) % 3 or any(v < 0 or v >= len(positions) for v in indices):
                    raise ValueError("Invalid shader-ball triangle indices")
                slot = 0 if primitive.get("material") in specimen_materials else 1
                a, b, c = matrix[0], matrix[4], matrix[8]
                d, e, f = matrix[1], matrix[5], matrix[9]
                g, h, i = matrix[2], matrix[6], matrix[10]
                mirrored = a*(e*i-f*h) - b*(d*i-f*g) + c*(d*h-e*g) < 0
                for offset in range(0, len(indices), 3):
                    face = indices[offset:offset+3]
                    if mirrored:
                        face[1], face[2] = face[2], face[1]
                    triangles.append((slot, [first+v+1 for v in face]))
        for child in node.get("children", []):
            visit(child, matrix)

    for root in scene["scenes"][scene.get("scene", 0)]["nodes"]:
        visit(root, IDENTITY)
    if not vertices or {slot for slot, _ in triangles} != {0, 1}:
        raise ValueError("Expected both an outer specimen and neutral core/base geometry")
    if not all(math.isfinite(v) for row in vertices+normals+list(uvs) for v in row):
        raise ValueError("Non-finite mesh attributes")
    minimum = [min(v[k] for v in vertices) for k in range(3)]
    maximum = [max(v[k] for v in vertices) for k in range(3)]
    center = [(a+b)*0.5 for a, b in zip(minimum, maximum)]
    scale = 100.0/max(b-a for a, b in zip(minimum, maximum))
    vertices = [[(v[k]-center[k])*scale for k in range(3)] for v in vertices]
    triangles, repaired = repair_unmapped_faces(vertices, normals, uvs, triangles)
    mtl = output.with_suffix(".mtl")
    mtl.write_text("newmtl Specimen\nKd 0.5 0.5 0.5\nnewmtl CoreBase\nKd 0.18 0.18 0.18\n", encoding="ascii")
    # OBJ has no axis metadata. Bake the agreed up/front frame explicitly.
    with output.open("w", encoding="ascii", newline="\n") as stream:
        stream.write("# USD shader ball, CC BY 4.0. Attribution: README.source.md\n")
        stream.write("mtllib " + mtl.name + "\n")
        for v in vertices:
            stream.write("v %.9g %.9g %.9g\n" % export_axes(v))
        for uv in uvs:
            stream.write("vt %.9g %.9g\n" % tuple(uv))
        for n in normals:
            stream.write("vn %.9g %.9g %.9g\n" % export_axes(n))
        for slot, name in enumerate(("Specimen", "CoreBase")):
            stream.write("g %s\nusemtl %s\ns 1\n" % (name, name))
            for face_slot, face in triangles:
                if face_slot == slot:
                    stream.write("f " + " ".join("%d/%d/%d" % (v, v, v) for v in face) + "\n")
    return {"vertices": len(vertices), "triangles": len(triangles),
            "repaired_uv_triangles": repaired, "conversion_version": CONVERSION_VERSION,
            "coordinate_frame": "Z-up RH OBJ, glTF +Z front mapped to -X; import with KeepXYZAxes",
            "materials": [m.get("name", "") for m in materials]}


def prepare():
    import unreal
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    source = root / "Plugins/CkTests/Resources/CkUsf/UsdShaderBall"
    source.mkdir(parents=True, exist_ok=True)
    destination = "/CkTests/CkUsf/Showcase/SM_UsdShaderBall"
    receipt = source / "provenance.json"
    obj = source / "SM_UsdShaderBall_ZUp3.obj"
    mesh = unreal.load_asset(destination) if unreal.EditorAssetLibrary.does_asset_exist(destination) else None
    if receipt.exists():
        saved = json.loads(receipt.read_text())
        data = (source / "USDShaderBallForGltf.glb").read_bytes()
        if hashlib.sha256(data).hexdigest() != saved["sha256"]:
            raise RuntimeError("Existing shader-ball source differs from its receipt; inspect it before continuing")
        if saved.get("conversion_version", 1) != CONVERSION_VERSION or not obj.exists():
            counts = convert_glb(data, obj)
            saved.update(counts)
            saved["obj_file"] = obj.name
            saved["modifications"] += " Conversion 3 explicitly rotates geometry and normals to Z-up, front toward -X, without changing UVs."
            receipt.write_text(json.dumps(saved, indent=2))
    else:
        if mesh or any((source / name).exists() for name in (
                "USDShaderBallForGltf.glb", "README.source.md", "SM_UsdShaderBall.obj", "SM_UsdShaderBall.mtl",
                "SM_UsdShaderBall_Uv2.obj", "SM_UsdShaderBall_ZUp3.obj")):
            raise RuntimeError("Unrecognized or partial shader-ball setup exists; inspect the named source files and asset before retrying. No files were overwritten.")
        commit = json.loads(fetch("https://api.github.com/repos/" + REPO + "/commits/main"))["sha"]
        prefix = "https://raw.githubusercontent.com/" + REPO + "/" + commit + "/" + MODEL
        data = fetch(prefix + "/glTF-Binary/USDShaderBallForGltf.glb")
        readme = fetch(prefix + "/README.md")
        if b"4.0" not in readme or b"Creative Commons" not in readme:
            raise RuntimeError("Upstream attribution changed; inspect its license before import")
        counts = convert_glb(data, obj)
        (source / "USDShaderBallForGltf.glb").write_bytes(data)
        (source / "README.source.md").write_bytes(readme)
        receipt.write_text(json.dumps({
            "repository": REPO, "commit": commit, "sha256": hashlib.sha256(data).hexdigest(),
            "license": "CC-BY-4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "obj_file": obj.name,
            "modifications": "Scene transforms baked; geometry centered/scaled to 100 cm, explicitly rotated to Z-up/front -X; normals rotated identically; valid UVs retained; unmapped triangle corners receive planar UV charts.",
            **counts}, indent=2))
    needs_import = mesh is None or unreal.EditorAssetLibrary.get_metadata_tag(mesh, "CkUsfStudio.ConversionVersion") != str(CONVERSION_VERSION)
    if mesh is not None and needs_import:
        imported_from = Path(mesh.get_editor_property("asset_import_data").get_first_filename()).resolve()
        owned_sources = {(source / name).resolve() for name in ("SM_UsdShaderBall.obj", "SM_UsdShaderBall_Uv2.obj", obj.name)}
        if imported_from not in owned_sources:
            raise RuntimeError("Refusing to reimport a shader ball from an unrecognized source: " + str(imported_from))
        original_asset = root / "Plugins/CkTests/Content/CkUsf/Showcase/SM_UsdShaderBall.uasset"
        backup = root / "Saved/UsfMaterialGallery/BeforeConversion3/SM_UsdShaderBall.uasset"
        if original_asset.exists() and not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(original_asset.read_bytes())
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.convert_scene = False
    options.static_mesh_import_data.set_editor_property("coordinate_system_policy", unreal.CoordinateSystemPolicy.KEEP_XYZ_AXES)
    options.static_mesh_import_data.convert_scene_unit = False
    options.static_mesh_import_data.import_rotation = unreal.Rotator(0.0, 0.0, 0.0)
    options.static_mesh_import_data.import_translation = unreal.Vector(0.0, 0.0, 0.0)
    options.static_mesh_import_data.import_uniform_scale = 1.0
    options.static_mesh_import_data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = unreal.AssetImportTask()
    task.filename = str(obj)
    task.destination_path = "/CkTests/CkUsf/Showcase"
    task.destination_name = "SM_UsdShaderBall"
    task.automated = True
    task.save = False
    task.replace_existing = mesh is not None
    task.replace_existing_settings = True
    task.factory = unreal.FbxFactory()
    task.options = options
    if needs_import:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh = imported_mesh_from_task(task, destination + ".SM_UsdShaderBall", obj)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("The shader-ball import did not produce the expected StaticMesh")
    slots = [str(slot.material_slot_name) for slot in mesh.static_materials]
    if len(slots) != 2 or set(slots) != {"Specimen", "CoreBase"}:
        raise RuntimeError("Imported mesh left unsaved: expected unique named Specimen/CoreBase slots, found " + repr(slots))
    previous_version = unreal.EditorAssetLibrary.get_metadata_tag(mesh, "CkUsfStudio.ConversionVersion")
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, "CkUsfStudio.ConversionVersion", str(CONVERSION_VERSION))
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh):
        unreal.EditorAssetLibrary.set_metadata_tag(mesh, "CkUsfStudio.ConversionVersion", previous_version)
        raise RuntimeError("Shader-ball save failed; conversion marker restored and setup stopped")
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    for name in ("StudioCeramic", "StudioCopper", "StudioRubber", "StudioLacquer", "StudioWax", "Toon"):
        unreal.SystemLibrary.execute_console_command(subsystem.get_editor_world(), "Ck_Usf_GenerateLooks " + name)
        material = unreal.load_asset("/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_" + name)
        if not material:
            raise RuntimeError("Look generation failed: " + name)
        unreal.MaterialEditingLibrary.get_statistics(material)
    unreal.log("USF_STUDIO_PREPARED: import and look generation complete; verify orientation, silhouette, material slots, lighting and live reload in the USF Materials gym")


if __name__ == "__main__":
    prepare()
