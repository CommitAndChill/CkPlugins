"""Additive UE-import front-face correction: reverse OBJ face corners only.

The canonical V2 sources have positive geometric volume and outward normals.
This explicit export reverses triangle order for the verified KeepXYZAxes Unreal
OBJ importer convention while preserving all positions, UVs and outward normals.
"""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Plugins/CkTests/Resources/CkUsf/OpticalDisplayDepthV2'
OUT=ROOT/'Plugins/CkTests/Resources/CkUsf/OpticalDisplayDepthV3'
SOURCE_MANIFEST_SHA256='d96b0fcd6f800c6372da6b6f855a92a67eca116d399dc4e16849561706f832eb'
CONVENTION='UE_KEEP_XYZ_REVERSED_OBJ_CORNERS_V1'


def sha(data):return hashlib.sha256(data).hexdigest()


def checked(path,expected):
    data=path.read_bytes()
    if sha(data)!=expected:raise RuntimeError('Preserve changed canonical source: '+str(path))
    return data


def write(relative,data):
    path=(OUT/relative).resolve()
    if not path.is_relative_to(OUT.resolve()):raise RuntimeError('Escaped V3 resource root')
    if path.exists():
        if path.read_bytes()!=data:raise RuntimeError('Preserve differing V3 output: '+str(path))
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(data)


def reverse_obj(data,record):
    output=[];points=[];normals=[];faces=[];face_normals=[]
    for line in data.splitlines(keepends=True):
        words=line.split()
        if words[0]==b'v':points.append([float(value) for value in words[1:]])
        if words[0]==b'vn':normals.append([float(value) for value in words[1:]])
        if words[0]==b'f':
            if len(words)!=4:raise RuntimeError('Only canonical triangle faces supported')
            faces.append([int(value.split(b'/')[0])-1 for value in words[1:]])
            face_normals.append([int(value.split(b'/')[2])-1 for value in words[1:]])
            newline=b'\r\n' if line.endswith(b'\r\n') else b'\n' if line.endswith(b'\n') else b''
            line=b'f '+b' '.join([words[1],words[3],words[2]])+newline
        output.append(line)
    p=np.asarray(points);n=np.asarray(normals);f=np.asarray(faces);fn=np.asarray(face_normals)
    cross=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    areas=np.linalg.norm(cross,axis=1)/2
    if not np.isfinite(p).all() or not np.isfinite(n).all() or np.any(areas<1e-10):raise RuntimeError('Invalid canonical triangles/normals')
    alignment=np.einsum('ij,ij->i',cross/np.linalg.norm(cross,axis=1)[:,None],n[fn].mean(1))
    if np.min(alignment)<=0 or np.max(abs(np.linalg.norm(n,axis=1)-1))>2e-9:raise RuntimeError('Canonical outward normals differ')
    directions=Counter((int(a),int(b)) for face in f for a,b in zip(face,np.roll(face,-1)))
    if not all(count==1 and directions[b,a]==1 for (a,b),count in directions.items()):raise RuntimeError('Canonical manifold/winding differs')
    reverse=f[:,[0,2,1]]
    reverse_directions=Counter((int(a),int(b)) for face in reverse for a,b in zip(face,np.roll(face,-1)))
    if reverse_directions!=Counter({(b,a):count for (a,b),count in directions.items()}):raise RuntimeError('Export edge directions not exactly reversed')
    source_volume=float(np.einsum('ij,ij->i',p[f[:,0]],np.cross(p[f[:,1]],p[f[:,2]])).sum()/6)
    export_volume=float(np.einsum('ij,ij->i',p[reverse[:,0]],np.cross(p[reverse[:,1]],p[reverse[:,2]])).sum()/6)
    if source_volume<=0 or export_volume>=0 or abs(source_volume+export_volume)>1e-8:raise RuntimeError('Unexpected exported volume sign')
    if abs(source_volume-sum(record['component_signed_volumes_cm3']))>1e-8:raise RuntimeError('Canonical component volumes differ')
    result=b''.join(output)
    original_lines=data.splitlines();export_lines=result.splitlines()
    if len(original_lines)!=len(export_lines) or any(a!=b for a,b in zip(original_lines,export_lines) if not a.startswith(b'f ')):raise RuntimeError('Non-face OBJ content changed')
    if not np.allclose(p.min(0),record['bounds']['min'],atol=1e-9,rtol=0) or not np.allclose(p.max(0),record['bounds']['max'],atol=1e-9,rtol=0):raise RuntimeError('Canonical bounds differ')
    return result,dict(signed_volume_cm3=export_volume,canonical_signed_volume_cm3=source_volume,
        outward_normal_alignment_to_canonical_min_dot=float(alignment.min()),
        exported_geometric_normal_alignment_max_dot=float((-alignment).max()))


def main():
    source_manifest_data=checked(SOURCE/'Geometry.json',SOURCE_MANIFEST_SHA256)
    source=json.loads(source_manifest_data)
    for prefix in ['generator','helper']:checked(ROOT/source[prefix+'_source'],source[prefix+'_sha256'])
    manifest=copy.deepcopy(source)
    manifest.update(schema_version=3,generator_source='Tools/UsfMaterials/author_optical_display_frontfaces.py',
        generator_sha256=sha(Path(__file__).read_bytes()),helper_source=source['generator_source'],helper_sha256=source['generator_sha256'],
        source_chain=[dict(path=source['helper_source'],sha256=source['helper_sha256'])],
        canonical_source=dict(path=(SOURCE/'Geometry.json').relative_to(ROOT).as_posix(),sha256=SOURCE_MANIFEST_SHA256),
        export_convention=CONVENTION,exported_winding_sign=-1,
        vertex_normals_convention='Unchanged outward canonical source normals; intentionally opposite exported geometric winding',
        correction='Swap complete OBJ face corner tokens 2 and 3 only. No position, UV, authored normal, material slot or MTL change.',
        limitations=['Explicit negative geometric volume export for the verified Unreal KeepXYZAxes OBJ importer convention; not a general-purpose outward-wound OBJ.',
                     'Canonical source solids retain positive volume and outward source normals. Native rendering verification belongs to the importer/scene.',
                     'All V1 and V2 sources remain unchanged.'])
    outputs={}
    for role,original in source['meshes'].items():
        data=checked(SOURCE/original['path'],original['sha256'])
        mtl=checked(SOURCE/original['mtl']['path'],original['mtl']['sha256'])
        corrected,validation=reverse_obj(data,original)
        record=manifest['meshes'][role]
        record.update(sha256=sha(corrected),canonical_source=dict(path=(SOURCE/original['path']).relative_to(ROOT).as_posix(),
            sha256=original['sha256'],component_signed_volumes_cm3=original['component_signed_volumes_cm3']),
            component_signed_volumes_cm3=[-volume for volume in original['component_signed_volumes_cm3']],
            source_normals_preserved=True,face_corner_permutation=[0,2,1],**validation)
        outputs[record['path']]=corrected;outputs[record['mtl']['path']]=mtl
    # Validate the complete input batch before writing any corrected resource.
    outputs['Geometry.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    for relative,data in outputs.items():write(relative,data)
    print(json.dumps(dict(output=str(OUT),schema_version=3,export_convention=CONVENTION,
        meshes={role:{key:record[key] for key in ['sha256','signed_volume_cm3','canonical_signed_volume_cm3','outward_normal_alignment_to_canonical_min_dot']} for role,record in manifest['meshes'].items()}),indent=2))


if __name__=='__main__':main()
