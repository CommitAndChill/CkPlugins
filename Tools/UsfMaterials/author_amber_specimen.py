"""Original immutable amber specimen authoring. Run with Python + NumPy + Pillow."""
from pathlib import Path
import hashlib, io, json, math
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Plugins/CkTests/Resources/CkUsf/AmberSpecimenV1'

def digest(data): return hashlib.sha256(data).hexdigest()
def write(relative,data):
    path=OUT/relative
    if not path.resolve().is_relative_to(OUT.resolve()): raise RuntimeError('Escaped output root')
    if path.exists():
        if path.read_bytes()!=data: raise RuntimeError('Preserve differing authored output: '+str(path))
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream: stream.write(data)
    return dict(path=relative,sha256=digest(data))

def normal(height,spacing_u,spacing_v):
    dv,du=np.gradient(height,spacing_v,spacing_u)
    n=np.stack([-du,-dv,np.ones_like(du)],-1); n/=np.linalg.norm(n,axis=-1,keepdims=True)
    return np.round((n*.5+.5)*255).astype(np.uint8)

def maps():
    count=2048; u,v=np.meshgrid((np.arange(count)+.5)/count,(np.arange(count)+.5)/count)
    # Original broad resin flow and faint polishing arcs. No baked illumination.
    flow=np.sin(2*np.pi*(1.2*u+.23*np.sin(4*v)))
    polish=np.cos(2*np.pi*(38*u+8*v*v))
    height=.000035*polish + .00010*np.sin(2*np.pi*(2*u+.4*v))
    radial=np.clip(((u-.5)*2)**2+((v-.5)*2)**2,0,1)
    # Decode in material: .45+2.15*R centimeters; cap center is deepest.
    thickness=np.clip((1-radial)**.65,0,1)
    tint=np.stack([.988+.006*flow,.970+.010*flow,.946+.014*flow],-1)
    arrays={'AmberNormal':normal(height,11/count,8/count),'AmberRoughness':np.round((.065+.008*flow+.002*polish)*255).astype('uint8'),
            'AmberThickness':np.round(thickness*65535).astype('uint16'),'AmberTint':np.round(tint*255).astype('uint8')}
    count=1024; u,v=np.meshgrid((np.arange(count)+.5)/count,(np.arange(count)+.5)/count)
    # Atlas: leaf U .04..64 V .04..72; seed U .70..98 V .04..72; stem V .80..98.
    q=(u-.34)/.30; longitudinal=np.clip((v-.04)/.68,0,1)
    lateral=np.exp(-((np.sin(2*np.pi*(longitudinal*9-np.abs(q)*.36)))/.10)**2)
    mid=np.exp(-(q/.035)**2)
    veins=np.maximum(mid,lateral*.65)
    edge=np.clip((np.abs(q)-.66)/.34,0,1)
    color=np.stack([.24+.12*edge+.065*veins,.18+.10*edge+.045*veins,.075+.055*edge+.025*veins],-1)
    seed=u>.67
    fibers=.5+.5*np.cos(2*np.pi*(u*73+v*3))
    color=np.where(seed[:,:,None],np.stack([.64+.12*fibers,.48+.12*fibers,.23+.08*fibers],-1),color)
    stem=v>.77
    bark=.5+.5*np.cos(2*np.pi*(u*32+.4*np.sin(v*13)))
    color=np.where(stem[:,:,None],np.stack([.19+.06*bark,.11+.045*bark,.048+.022*bark],-1),color)
    h=np.where(seed,.00008*fibers,.0002*veins);h=np.where(stem,.00015*bark,h)
    arrays.update(BotanicalBaseColor=np.round(np.clip(color,0,1)*255).astype('uint8'),BotanicalNormal=normal(h,1.4/count,2/count),BotanicalRoughness=np.round(np.where(seed,.60+.05*fibers,np.where(stem,.68+.04*bark,.57+.08*edge))*255).astype('uint8'))
    records={}
    for name,array in arrays.items():
        b=io.BytesIO();Image.fromarray(array).save(b,format='PNG',compress_level=9);data=b.getvalue()
        r=write('Maps/'+name+'.png',data)
        decoded=np.asarray(Image.open(io.BytesIO(data)))
        if not np.array_equal(decoded,array): raise RuntimeError('PNG pixel roundtrip failed '+name)
        # PNG IHDR bit depth is byte 24, independent of Pillow decode dtype.
        r.update(width=array.shape[1],height=array.shape[0],channels='RGB' if array.ndim==3 else 'R',container_bits=data[24],bit_depth=data[24],srgb=name=='BotanicalBaseColor',normal_convention='DirectX tangent; normalize(-dH/dUcm,-dH/dVcm,1); PNG rows increase V; no green flip' if name.endswith('Normal') else None,decoded_min=int(array.min()),decoded_max=int(array.max()),decoded_pixel_sha256=digest(array.tobytes()),decode_verified=True)
        records[name]=r
    return records

class Mesh:
    def __init__(self,name): self.name=name;self.vertices=[];self.uv=[];self.faces=[]
    def vertex(self,p,uv): self.vertices.append(tuple(p));self.uv.append(tuple(uv));return len(self.vertices)-1
    def tri(self,a,b,c): self.faces.append((a,b,c))
    def quad(self,a,b,c,d): self.tri(a,b,c);self.tri(a,c,d)
    def save(self):
        p=np.asarray(self.vertices);uv=np.asarray(self.uv);f=np.asarray(self.faces)
        cross=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
        area=np.linalg.norm(cross,axis=1)/2
        if np.any(area<1e-10): raise RuntimeError('Degenerate '+self.name)
        if self.name=='Body' and np.any(cross[:,0]<=0): raise RuntimeError('Body not +X facing')
        lines=['# Original centimeter specimen geometry; +X front','mtllib SM_Amber_'+self.name+'.mtl','g '+self.name,'usemtl '+self.name]
        lines += ['v %.9f %.9f %.9f'%x for x in self.vertices]
        lines += ['vt %.9f %.9f'%x for x in self.uv]
        # Authored per-vertex normals, averaged over this role; no import recompute dependency.
        normals=np.zeros_like(p)
        for i,face in enumerate(f):
            for index in face: normals[index]+=cross[i]
        lengths=np.linalg.norm(normals,axis=1)
        if np.any(lengths<1e-12): raise RuntimeError('Invalid vertex normal '+self.name)
        normals/=lengths[:,None]
        lines += ['vn %.9f %.9f %.9f'%tuple(x) for x in normals]
        lines += ['s 1']
        lines += ['f '+' '.join('%d/%d/%d'%(j+1,j+1,j+1) for j in face) for face in f]
        record=write('Meshes/SM_Amber_'+self.name+'.obj',('\n'.join(lines)+'\n').encode('ascii'))
        mtl='newmtl '+self.name+'\nKd 0.55 0.35 0.12\nKs 0.04 0.04 0.04\nNs 80\nd 1\n'
        m=write('Meshes/SM_Amber_'+self.name+'.mtl',mtl.encode('ascii'))
        record.update(material_slot=self.name,slot=self.name,bounds=dict(min=p.min(axis=0).tolist(),max=p.max(axis=0).tolist()),mtl=m,vertices=len(p),triangles=len(f),bounds_min=p.min(axis=0).tolist(),bounds_max=p.max(axis=0).tolist(),uv_min=uv.min(axis=0).tolist(),uv_max=uv.max(axis=0).tolist(),degenerate_triangles=0,minimum_triangle_area_cm2=float(area.min()),winding_check='All triangle cross products +X' if self.name=='Body' else 'Authored explicit winding; finite nonzero normals verified',front_facing_triangles=int((cross[:,0]>0).sum()),finite_positions=bool(np.isfinite(p).all()))
        return record

def geometry():
    meshes={role:Mesh(role) for role in ['Body','Backing','Botanical','Seed','Stem']}
    body=meshes['Body'];n=160;rings=36
    outline=[]
    for i in range(n):
        a=2*math.pi*i/n;outline.append((5.5*math.cos(a)*(1-.045*math.sin(a)),4*math.sin(a)*(1+.045*math.cos(a))))
    arr=np.asarray(outline);arr=(arr-arr.min(axis=0))/(arr.max(axis=0)-arr.min(axis=0))*[11,8]-[5.5,4]
    def uv(y,z):return ((y+5.5)/11,z/8)
    body.vertex((1.5,0,4),(.5,.5))
    for j in range(1,rings+1):
        t=j/rings
        for y,z in arr: body.vertex((1.5-2.4*t*t,y*t,4+z*t),uv(y*t,4+z*t))
    for i in range(n):body.tri(0,1+i,1+(i+1)%n)
    for j in range(1,rings):
        a=1+(j-1)*n;b=1+j*n
        for i in range(n):k=(i+1)%n;body.quad(a+i,b+i,b+k,a+k)
    back=meshes['Backing']
    for x,scale in [(-.915,1),(-1.2,.97)]:
        for y,z in arr:back.vertex((x,y*scale,4+z*scale),uv(y*scale,4+z*scale))
    center=back.vertex((-1.2,0,4),(.5,.5))
    for i in range(n):
        k=(i+1)%n;back.quad(i,n+i,n+k,k);back.tri(center,n+k,n+i)
    # Diagonal twig is actual tapered cylindrical geometry, behind curved leaf blades.
    def branch(t):return np.array([-.34+.11*math.sin(t*3),-2.6+4.7*t,1.7+4.6*t])
    stem=meshes['Stem'];segments=40;sides=10
    for j in range(segments+1):
        t=j/segments;c=branch(t);r=.055*(1-.72*t)
        for i in range(sides):
            a=2*math.pi*i/sides;stem.vertex(c+np.array([math.cos(a)*r,math.sin(a)*r*.70,-math.sin(a)*r*.72]),(.04+.60*i/sides,.80+.18*t))
    for j in range(segments):
        for i in range(sides):k=(i+1)%sides;stem.quad(j*sides+i,j*sides+k,(j+1)*sides+k,(j+1)*sides+i)
    # Eight pairs. Each blade is a small curled surface, with longitudinal atlas V.
    leaf=meshes['Botanical'];rows=18;cols=6
    for pair in range(8):
        t=.12+pair*.105;c=branch(t);length=1.37*(1-.48*t)
        for side in [-1,1]:
            start=len(leaf.vertices)
            direction=np.array([0,side*.78,-side*.22+.30]);direction/=np.linalg.norm(direction)
            across=np.array([0,-direction[2],direction[1]])
            for j in range(rows+1):
                s=.02+.96*j/rows;width=.21*(math.sin(math.pi*s)**.72)*(1-.25*t)
                for k in range(cols+1):
                    q=2*k/cols-1
                    pos=c+direction*(length*s)+across*(q*width)
                    pos[0]+=.08+.13*math.sin(math.pi*s)+.11*s**3+.05*q*q
                    leaf.vertex(pos,(.04+.60*k/cols,.04+.68*s))
            for j in range(rows):
                for k in range(cols):
                    a=start+j*(cols+1)+k;b=a+cols+1
                    # Across and longitudinal ordering adjusted to +X-facing blade.
                    ids=(a,a+1,b+1,b)
                    pts=np.asarray([leaf.vertices[x] for x in ids])
                    if np.cross(pts[1]-pts[0],pts[2]-pts[0])[0]<0:ids=tuple(reversed(ids))
                    leaf.quad(*ids)
    seed=meshes['Seed'];base=np.array([-.55,1.65,5.35]);rows=24;cols=8
    for j in range(rows+1):
        t=.015+.97*j/rows;width=.34*math.sin(math.pi*t)**.6
        for k in range(cols+1):
            q=2*k/cols-1;seed.vertex(base+[.035*math.sin(t*math.pi)+.04*q*q,t*.86+q*width,t*1.55-q*width*.3],(.70+.28*k/cols,.04+.68*t))
    for j in range(rows):
        for k in range(cols):
            a=j*(cols+1)+k;b=a+cols+1;seed.quad(a,a+1,b+1,b)
    return {role:mesh.save() for role,mesh in meshes.items()}

def main():
    manifest=dict(schema_version=1,generator_source='Tools/UsfMaterials/author_amber_specimen.py',generator_sha256=digest(Path(__file__).read_bytes()),units='centimeters',axes='+X front, +Y width, +Z up; floor Z0',nominal_dimensions_cm=dict(width=11,height=8,depth=2.7),body_representation='Exactly one +X-facing convex exterior optical sheet. No inner optical shell. Opaque recessed matching rear support.',thickness_decode_cm='.45+2.15*AmberThickness.R; shader metadata, not ray traced thickness',maps=maps(),meshes=geometry(),uv_contract=dict(Body='U=(Y+5.5)/11,V=Z/8',Botanical='Each blade width U=.04..64, longitudinal V=.04..72',Seed='Width U=.70..98, longitudinal V=.04..72',Stem='Circumference U=.04..64, length V=.80..98',Backing='Same planar mapping as Body'),normal_height_units='cm; normalize(-dH/dUphysical,-dH/dVphysical,1); amber physical domain 11x8cm; botanical atlas nominal domain 1.4x2cm',provenance='Original deterministic geometry and analytical resin flow, polish, leaf veins, seed fibers and bark maps. No external assets, noise pretending inclusions, or baked lighting.',limitations=['Front acceptance angles limited to approximately +/-30 degrees; single cap is not a closed traced resin solid.','Botanical and seed blades are thin open geometry; use two-sided opaque botanical material. Twig ends are open and hidden in foliage.','Backing source is opaque. Source MTL is slot metadata only; Unreal native materials own optical response.','Interior appearance, UV orientation and native PNO require rendered Unreal verification. No source-only optical correctness or visual acceptance claim.'])
    write('Manifest.json',(json.dumps(manifest,indent=2)+'\n').encode())
    print(json.dumps(dict(output=str(OUT),meshes={k:{x:v[x] for x in ['vertices','triangles','bounds_min','bounds_max','degenerate_triangles']} for k,v in manifest['meshes'].items()},maps=len(manifest['maps'])),indent=2))
if __name__=='__main__':main()


