"""Original V5 seated optical display, with flat machined chamfers and no posts.

Canonical positive winding; independently indexed outward corner normals. Only
new immutable source files are written. No asset imports or studio interaction.
"""
from pathlib import Path
from collections import Counter
import sys
sys.dont_write_bytecode=True
import copy
import hashlib
import json
import numpy as np
import author_optical_pair as helper

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Plugins/CkTests/Resources/CkUsf/OpticalDisplayDepthV4'
OUT=ROOT/'Plugins/CkTests/Resources/CkUsf/OpticalDisplaySeatedV5'
SOURCE_SHA='b34e8ddf9be6549e79ee9788a352c5d938e9182527b056ecb12189c2283f7332'


def sha(data):return hashlib.sha256(data).hexdigest()


def checked(path,pin):
    data=path.read_bytes()
    if sha(data)!=pin:raise RuntimeError('Preserve changed source '+str(path))
    return data


def slab(mesh,w,h,r,back,front,bevel):
    start=len(mesh.f)
    rings=[mesh.ring(x,w-2*d,h-2*d,r-d) for x,d in [(back,bevel),(back+bevel,0),(front-bevel,0),(front,bevel)]]
    for a,b in zip(rings,rings[1:]):mesh.join(a,b)
    mesh.f[start:]=[(a,c,b) for a,b,c in mesh.f[start:]]
    mesh.cap(rings[0],back,w-2*bevel,h-2*bevel,r-bevel,False)
    mesh.cap(rings[-1],front,w-2*bevel,h-2*bevel,r-bevel,True)
    mesh.components.append((start,len(mesh.f)))


def annulus(mesh,w,h,r,band,back,front,bevel):
    start=len(mesh.f)
    profile=[(back+bevel,0),(front-bevel,0),(front,bevel),(front,band-bevel),
             (front-bevel,band),(back+bevel,band),(back,band-bevel),(back,bevel)]
    rings=[mesh.ring(x,w-2*d,h-2*d,r-d) for x,d in profile]
    for a,b in zip(rings,rings[1:]+rings[:1]):mesh.join(a,b)
    mesh.f[start:]=[(a,c,b) for a,b,c in mesh.f[start:]]
    mesh.components.append((start,len(mesh.f)))


def encode(mesh):
    p=np.round(np.asarray(mesh.p),9);f=np.asarray(mesh.f)
    cross=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    lengths=np.linalg.norm(cross,axis=1)
    if not np.isfinite(p).all() or np.any(lengths<2e-10):raise RuntimeError('Invalid machined triangles')
    n=cross/lengths[:,None]
    directed=Counter((int(a),int(b)) for face in f for a,b in zip(face,np.roll(face,-1)))
    if not all(count==1 and directed[b,a]==1 for (a,b),count in directed.items()):raise RuntimeError('Machined topology/winding failed')
    volumes=[]
    for start,end in mesh.components:
        q=f[start:end];volume=float(np.einsum('ij,ij->i',p[q[:,0]],np.cross(p[q[:,1]],p[q[:,2]])).sum()/6)
        if volume<=0:raise RuntimeError('Nonpositive machined component')
        volumes.append(volume)
    uv=np.column_stack((p[:,1]/mesh.width+.5,(p[:,2]-5.5)/mesh.height+.5))
    stem='SM_OpticalPair_'+mesh.name
    lines=['# Original centimeters, +X front, +Y width, +Z up',
           '# Flat faces and explicit per-corner normals; canonical positive winding',
           'mtllib '+stem+'.mtl','g '+mesh.name,'usemtl '+mesh.name]
    lines+=['v %.9f %.9f %.9f'%tuple(v) for v in p]
    lines+=['vt %.9f %.9f'%tuple(v) for v in uv]
    lines+=['vn %.9f %.9f %.9f'%tuple(v) for v in n]
    lines+=['s off']
    for index,face in enumerate(f):lines.append('f '+' '.join('%d/%d/%d'%(int(v)+1,int(v)+1,index+1) for v in face))
    data=('\n'.join(lines)+'\n').encode('ascii')
    return data,dict(path='Meshes/'+stem+'.obj',sha256=sha(data),slot=mesh.name,vertices=len(p),triangles=len(f),
        bounds={'min':p.min(0).tolist(),'max':p.max(0).tolist()},uv_bounds={'min':uv.min(0).tolist(),'max':uv.max(0).tolist()},
        closed_edge_manifold=True,consistent_edge_winding=True,degenerate_triangles=0,minimum_area_cm2=float(lengths.min()/2),
        component_signed_volumes_cm3=volumes,signed_volume_cm3=sum(volumes),normal_count=len(n),
        vertex_normals='Explicit per-triangle outward planar normals; corner indices independent of shared positions; no averaging across cap/chamfer/wall boundaries',
        normal_indexing='Independent OBJ v/vt/vn corner indices',outward_normal_alignment_min_dot=1.0,bevel_angle_degrees=45)


def main():
    source=json.loads(checked(SOURCE/'Geometry.json',SOURCE_SHA))
    for prefix in ['generator','helper']:checked(ROOT/source[prefix+'_source'],source[prefix+'_sha256'])
    for record in source['source_chain']:checked(ROOT/record['path'],record['sha256'])
    outputs={}
    for record in source['meshes'].values():
        checked(SOURCE/record['path'],record['sha256'])
        outputs[record['mtl']['path']]=checked(SOURCE/record['mtl']['path'],record['mtl']['sha256'])
    manifest=copy.deepcopy(source)
    glass=copy.deepcopy(source['meshes']['GlassCover']);original=checked(SOURCE/glass['path'],glass['sha256'])
    lines=[]
    for line in original.decode('ascii').splitlines():
        words=line.split()
        if words[0]=='v':line='v %.9f %.9f %.9f'%(float(words[1])-.68,float(words[2]),float(words[3]))
        lines.append(line)
    data=('\n'.join(lines)+'\n').encode('ascii');outputs[glass['path']]=data
    glass.update(sha256=sha(data),bounds={'min':[1.62,-8.5,.5],'max':[3.42,8.5,10.5]},crease_boundaries_X_cm=[1.62,1.77,3.27,3.42])
    manifest['meshes']['GlassCover']=glass
    panel=source['meshes']['Panel'];outputs[panel['path']]=checked(SOURCE/panel['path'],panel['sha256'])
    housing=helper.Mesh('Housing');slab(housing,18,11,1.0,0,.94,.06)
    annulus(housing,18,11,1.0,.65,.86,1.48,.055)
    trim=helper.Mesh('MetalTrim');annulus(trim,17.3,10.3,1.05,.50,1.46,1.60,.025)
    for mesh in [housing,trim]:
        data,record=encode(mesh);record['mtl']=source['meshes'][mesh.name]['mtl']
        manifest['meshes'][mesh.name]=record;outputs[record['path']]=data
    manifest.update(schema_version=5,generator_source='Tools/UsfMaterials/author_optical_display_seated.py',
        generator_sha256=sha(Path(__file__).read_bytes()),helper_source=source['helper_source'],helper_sha256=source['helper_sha256'],
        source_chain=[dict(path=source['generator_source'],sha256=source['generator_sha256']),*source['source_chain']],
        canonical_source=dict(path=(SOURCE/'Geometry.json').relative_to(ROOT).as_posix(),sha256=SOURCE_SHA),
        export_convention='CANONICAL_OUTWARD_OBJ_SEATED_MACHINED_V1',exported_winding_sign=1,
        vertex_normals_convention='Outward independent face-corner normals; glass cap/bevel/wall creases retained, housing/seat planar faces never averaged',
        display_dimensions_cm={'width_Y':18,'height_Z':11,'depth_X':3.42},
        design='Original continuous perimeter-seated glass assembly with broad flat machined housing shoulder and small straight 45-degree chamfers; no discrete posts.',
        layout={'housing_backplate_X':[0,.94],'housing_rim_X':[.86,1.48],'panel_X':[1.23,1.41],
                'metal_seat_X':[1.46,1.60],'glass_X':[1.62,3.42],'standoffs_X':None},
        seat={'continuous':True,'discrete_post_count':0,'top_X_cm':1.60,'glass_back_X_cm':1.62,'nominal_clearance_cm':.02,
              'outer_dimensions_YZ_cm':[17.3,10.3],'inner_dimensions_YZ_cm':[16.3,9.3],
              'outer_radius_cm':1.05,'band_width_cm':.5,'chamfer_cm':.025,
              'support':'Continuous annular ledge underneath peripheral flat glass back face; .02cm intended nonintersecting seam, not a physical-contact simulation'},
        housing={'outer_dimensions_YZ_cm':[18,11],'outer_radius_cm':1.0,'rim_band_cm':.65,'rim_top_flat_width_cm':.54,
                 'backplate_chamfer_cm':.06,'rim_chamfer_cm':.055,'planar_face_normals':True},
        limitations=['Geometry source validation only; direct rendered review required before claiming visual correction.',
                     'Continuous support has a deliberate .02cm clearance seam; panel-to-glass clearance is .21cm.',
                     'Closed housing backplate/rim have intentional interior assembly overlap; panel is reused byte-identically.',
                     'Glass retains V4 independent analytic corner normals; housing and seat use explicit planar triangle normals.',
                     'No V1-V4 source resources or imported assets are modified.'])
    manifest['glass'].update(back_X_cm=1.62,front_X_cm=3.42,minimum_panel_gap_cm=.21,standoff_clearance_cm=None,seat_clearance_cm=.02)
    outputs['Geometry.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    for relative,data in outputs.items():
        path=OUT/relative
        if path.exists() and path.read_bytes()!=data:raise RuntimeError('Preserve differing V5 output: '+str(path))
    for relative,data in outputs.items():
        path=OUT/relative
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as stream:stream.write(data)
    print(json.dumps(dict(output=str(OUT),seat=manifest['seat'],meshes={role:{key:record[key] for key in ['bounds','triangles','component_signed_volumes_cm3']} for role,record in manifest['meshes'].items()}),indent=2))


if __name__=='__main__':main()
