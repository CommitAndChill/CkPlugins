"""Additive canonical thick cover with flat 45-degree chamfers and crease normals.

Shared positions remain closed/manifold. Independent per-corner normal indices
keep cap, bevel and sidewall boundaries crisp without duplicating positions.
No editor work or imported assets are changed by this source generator.
"""
from pathlib import Path
from collections import Counter
import sys
sys.dont_write_bytecode=True
import copy
import hashlib
import json
import math
import numpy as np
import author_optical_pair as helper

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Plugins/CkTests/Resources/CkUsf/OpticalDisplayDepthV2'
OUT=ROOT/'Plugins/CkTests/Resources/CkUsf/OpticalDisplayDepthV4'
SOURCE_SHA='d96b0fcd6f800c6372da6b6f855a92a67eca116d399dc4e16849561706f832eb'


def sha(data):return hashlib.sha256(data).hexdigest()


def checked(path,pin):
    data=path.read_bytes()
    if sha(data)!=pin:raise RuntimeError('Preserve changed source: '+str(path))
    return data


def cover():
    mesh=helper.Mesh('GlassCover',17,10)
    profile=[(2.3,.15),(2.45,0),(3.95,0),(4.1,.15)]
    rings=[mesh.ring(x,17-2*inset,10-2*inset,.9-inset) for x,inset in profile]
    normals=[];normal_faces=[]
    for band,(a,b) in enumerate(zip(rings,rings[1:])):
        # The normal is constant across each band's axial width, analytic around
        # rounded corners, and split from the next band's normal at the crease.
        start=len(normals)
        axial=[-1,0,1][band]
        for corner in range(4):
            for sample in range(17):
                angle=math.radians(corner*90+sample*90/16)
                normal=np.array([axial,math.cos(angle),math.sin(angle)],float)
                normals.append((normal/np.linalg.norm(normal)).tolist())
        for i in range(len(a)):
            j=(i+1)%len(a)
            mesh.tri(a[i],b[j],b[i]);normal_faces.append((start+i,start+j,start+i))
            mesh.tri(a[i],a[j],b[j]);normal_faces.append((start+i,start+j,start+j))
    for ring,x,front in [(rings[0],2.3,False),(rings[-1],4.1,True)]:
        start=len(mesh.f)
        mesh.cap(ring,x,16.7,9.7,.75,front)
        index=len(normals);normals.append([1 if front else -1,0,0])
        normal_faces.extend([(index,index,index)]*(len(mesh.f)-start))
    p=np.round(np.asarray(mesh.p),9);f=np.asarray(mesh.f);n=np.asarray(normals);nf=np.asarray(normal_faces)
    cross=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    areas=np.linalg.norm(cross,axis=1)/2
    if not np.isfinite(p).all() or np.any(areas<1e-10) or not np.isfinite(n).all():raise RuntimeError('Invalid bevel geometry')
    edges=Counter(tuple(sorted((int(a),int(b)))) for face in f for a,b in zip(face,np.roll(face,-1)))
    directed=Counter((int(a),int(b)) for face in f for a,b in zip(face,np.roll(face,-1)))
    if not all(count==2 for count in edges.values()) or not all(directed[a,b]==directed[b,a]==1 for a,b in edges):raise RuntimeError('Bevel position topology/winding failed')
    volume=float(np.einsum('ij,ij->i',p[f[:,0]],np.cross(p[f[:,1]],p[f[:,2]])).sum()/6)
    alignment=np.einsum('ij,ij->i',cross/np.linalg.norm(cross,axis=1)[:,None],n[nf].mean(1))
    if volume<=0 or alignment.min()<=0 or not np.allclose(np.linalg.norm(n,axis=1),1,atol=1e-12,rtol=0):raise RuntimeError('Bevel outward normal validation failed')
    uv=np.column_stack((p[:,1]/17+.5,(p[:,2]-5.5)/10+.5))
    stem='SM_OpticalPair_GlassCover'
    lines=['# Original centimeters, +X front, +Y width, +Z up',
           '# Canonical positive winding; independent authored corner normals preserve cap/bevel/side creases',
           'mtllib '+stem+'.mtl','g GlassCover','usemtl GlassCover']
    lines+=['v %.9f %.9f %.9f'%tuple(value) for value in p]
    lines+=['vt %.9f %.9f'%tuple(value) for value in uv]
    lines+=['vn %.9f %.9f %.9f'%tuple(value) for value in n]
    lines+=['s off']
    for face,normal_face in zip(f,nf):
        lines.append('f '+' '.join('%d/%d/%d'%(int(v)+1,int(v)+1,int(ni)+1) for v,ni in zip(face,normal_face)))
    data=('\n'.join(lines)+'\n').encode('ascii')
    record=dict(path='Meshes/'+stem+'.obj',sha256=sha(data),slot='GlassCover',vertices=len(p),triangles=len(f),
        bounds={'min':p.min(0).tolist(),'max':p.max(0).tolist()},uv_bounds={'min':uv.min(0).tolist(),'max':uv.max(0).tolist()},
        closed_edge_manifold=True,consistent_edge_winding=True,degenerate_triangles=0,minimum_area_cm2=float(areas.min()),
        component_signed_volumes_cm3=[volume],signed_volume_cm3=volume,
        vertex_normals='Independent per-corner analytic normals: cap +/-X, side radial YZ, bevel normalized (+/-1,radial_Y,radial_Z); crease split at shared positions',
        normal_count=len(n),normal_indexing='Independent OBJ v/vt/vn corner indices; positions shared across creases',
        outward_normal_alignment_min_dot=float(alignment.min()),
        crease_boundaries_X_cm=[2.3,2.45,3.95,4.1],bevel_angle_degrees=45)
    return data,record


def main():
    source=json.loads(checked(SOURCE/'Geometry.json',SOURCE_SHA))
    for prefix in ['generator','helper']:checked(ROOT/source[prefix+'_source'],source[prefix+'_sha256'])
    outputs={};manifest=copy.deepcopy(source)
    for role,record in source['meshes'].items():
        outputs[record['path']]=checked(SOURCE/record['path'],record['sha256'])
        outputs[record['mtl']['path']]=checked(SOURCE/record['mtl']['path'],record['mtl']['sha256'])
    data,glass=cover();glass['mtl']=source['meshes']['GlassCover']['mtl']
    outputs[glass['path']]=data;manifest['meshes']['GlassCover']=glass
    manifest.update(schema_version=4,generator_source='Tools/UsfMaterials/author_optical_display_bevel.py',
        generator_sha256=sha(Path(__file__).read_bytes()),helper_source=source['helper_source'],helper_sha256=source['helper_sha256'],
        source_chain=[dict(path=source['generator_source'],sha256=source['generator_sha256'])],
        canonical_source=dict(path=(SOURCE/'Geometry.json').relative_to(ROOT).as_posix(),sha256=SOURCE_SHA),
        export_convention='CANONICAL_OUTWARD_OBJ_PER_CORNER_NORMALS_V1',exported_winding_sign=1,
        vertex_normals_convention='Canonical outward analytic per-corner normals with cap/bevel/side crease separation',
        design='Original V2 thick cover dimensions with flat .15cm 45-degree chamfers and crisp authored reflection boundaries; no winding reversal.',
        limitations=['Source geometric and normal validation only; visual result requires direct native render.',
                     'Only GlassCover is regenerated; other three OBJ/MTL sources are byte-identical to pinned V2.',
                     'No V1/V2/V3 resources or imported assets are changed.'])
    manifest['glass'].update(bevel_cm=.15,bevel_angle_degrees=45,central_bow_cm=0,
        sidewall_representation='True 1.5cm straight wall between flat .15cm 45-degree chamfers; independent authored cap/bevel/side corner normals')
    for role in ['Panel','Housing','MetalTrim']:
        manifest['meshes'][role]['canonical_source']=dict(path=(SOURCE/source['meshes'][role]['path']).relative_to(ROOT).as_posix(),sha256=source['meshes'][role]['sha256'])
        manifest['meshes'][role]['reused_byte_identical']=True
    outputs['Geometry.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    # Preflight the full existing destination batch before the first immutable write.
    for relative,data in outputs.items():
        path=OUT/relative
        if path.exists() and path.read_bytes()!=data:raise RuntimeError('Preserve differing V4 output: '+str(path))
    for relative,data in outputs.items():
        path=OUT/relative
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as stream:stream.write(data)
    print(json.dumps(dict(output=str(OUT),glass=glass),indent=2))


if __name__=='__main__':main()
