"""Original structural amber hero. Immutable source outputs; no editor or Blender dependency."""
from pathlib import Path
import hashlib,json,math
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Plugins/CkTests/Resources/CkUsf/AmberHeroV1'
def sha(data):return hashlib.sha256(data).hexdigest()
def write(relative,data):
    path=OUT/relative
    if not path.resolve().is_relative_to(OUT.resolve()):raise RuntimeError('Escaped resource directory')
    if path.exists():
        if path.read_bytes()!=data:raise RuntimeError('Preserve differing source '+str(path))
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(data)
    return dict(path=relative,sha256=sha(data))
class Mesh:
    def __init__(self,name):self.name=name;self.p=[];self.uv=[];self.f=[]
    def vertex(self,p,uv=(0,0)):self.p.append(tuple(p));self.uv.append(tuple(uv));return len(self.p)-1
    def tri(self,a,b,c):self.f.append((a,b,c))
    def quad(self,a,b,c,d):self.tri(a,b,c);self.tri(a,c,d)
    def save(self,closed=False):
        p=np.asarray(self.p,dtype=float);f=np.asarray(self.f);uv=np.asarray(self.uv)
        cross=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
        areas=np.linalg.norm(cross,axis=1)/2
        if not np.isfinite(p).all() or np.any(areas<1e-11):raise RuntimeError('Nonfinite/degenerate '+self.name)
        edges=Counter(tuple(sorted((int(a),int(b)))) for face in f for a,b in zip(face,np.roll(face,-1)))
        directed=Counter((int(a),int(b)) for face in f for a,b in zip(face,np.roll(face,-1)))
        manifold=all(value==2 for value in edges.values())
        consistent=all(value==1 or directed[a,b]==directed[b,a] for (a,b),value in edges.items())
        volume=float(np.einsum('ij,ij->i',p[f[:,0]],np.cross(p[f[:,1]],p[f[:,2]])).sum()/6)
        if closed and (not manifold or not consistent or volume<=0):raise RuntimeError('Closed winding check failed '+self.name)
        n=np.zeros_like(p)
        for i,face in enumerate(f):
            for index in face:n[index]+=cross[i]
        lengths=np.linalg.norm(n,axis=1)
        if np.any(lengths<1e-12):raise RuntimeError('Zero vertex normal '+self.name)
        n/=lengths[:,None]
        lines=['# Original centimeters, +X front, +Y width, +Z up','mtllib SM_AmberHero_'+self.name+'.mtl','g '+self.name,'usemtl '+self.name]
        lines+=['v %.9f %.9f %.9f'%tuple(v) for v in p]
        lines+=['vt %.9f %.9f'%tuple(v) for v in uv]
        lines+=['vn %.9f %.9f %.9f'%tuple(v) for v in n]
        lines+=['s 1']
        lines+=['f '+' '.join('%d/%d/%d'%(int(i)+1,int(i)+1,int(i)+1) for i in face) for face in f]
        r=write('Meshes/SM_AmberHero_'+self.name+'.obj',('\n'.join(lines)+'\n').encode('ascii'))
        m=write('Meshes/SM_AmberHero_'+self.name+'.mtl',('newmtl '+self.name+'\nKd 0.5 0.3 0.1\nd 1\n').encode('ascii'))
        r.update(slot=self.name,mtl=m,vertices=len(p),triangles=len(f),bounds=dict(min=p.min(0).tolist(),max=p.max(0).tolist()),uv_bounds=dict(min=uv.min(0).tolist(),max=uv.max(0).tolist()),degenerate_triangles=0,minimum_area_cm2=float(areas.min()),closed_edge_manifold=manifold,consistent_edge_winding=consistent,signed_volume_cm3=volume,vertex_normals='Authored area-weighted smooth normals')
        return r

def sphere(name,latitudes,longitudes,body=False):
    m=Mesh(name)
    m.vertex((1,0,0),(0.5,.5))
    for j in range(1,latitudes):
        theta=math.pi*j/latitudes
        for i in range(longitudes):
            phi=2*math.pi*i/longitudes
            x=math.cos(theta);y=math.sin(theta)*math.cos(phi);z=math.sin(theta)*math.sin(phi)
            if body:
                # Low-amplitude hand-polished shoulder variation, not a perfect ellipse.
                flow=math.sin(theta)**2
                x*=2.1*(1+.035*flow*math.sin(3*phi+.4))
                y*=5.5*(1+.045*z+.018*flow*math.cos(3*phi))
                z=4+4*z*(1+.035*y/5.5)
            m.vertex((x,y,z))
    end=m.vertex((-1,0,0),(.5,.5))
    if body:
        m.p[0]=(2.1,0,4);m.p[-1]=(-2.1,0,4)
        p=np.asarray(m.p)
        p[:,0]=p[:,0]/max(abs(p[:,0].min()),abs(p[:,0].max()))*2.1
        p[:,1]=(p[:,1]-p[:,1].min())/(p[:,1].max()-p[:,1].min())*11-5.5
        p[:,2]=(p[:,2]-p[:,2].min())/(p[:,2].max()-p[:,2].min())*8
        p[:,2]=np.maximum(p[:,2],.12)
        m.p=[tuple(v) for v in p];m.uv=[((v[1]+5.5)/11,v[2]/8) for v in p]
    else:
        m.uv=[((math.atan2(v[2],v[1])/(2*math.pi))%1,math.acos(max(-1,min(1,v[0])))/math.pi) for v in m.p]
    for i in range(longitudes):m.tri(0,1+i,1+(i+1)%longitudes)
    for j in range(latitudes-2):
        a=1+j*longitudes;b=a+longitudes
        for i in range(longitudes):k=(i+1)%longitudes;m.quad(a+i,b+i,b+k,a+k)
    start=1+(latitudes-2)*longitudes
    for i in range(longitudes):m.tri(start+i,end,start+(i+1)%longitudes)
    # Canonical +X-pole fan and ring ordering produce outward frontfaces.

    return m

def leaf():
    m=Mesh('Leaf');rows=28;cols=20;angle=math.radians(-25)
    for j in range(rows+1):
        v=j/rows;b=(v-.5)*5.8
        for i in range(cols+1):
            u=i/cols;a=(u-.5)*4.2
            y=a*math.cos(angle)-b*math.sin(angle);z=4+a*math.sin(angle)+b*math.cos(angle)
            x=-.22+.18*math.sin(math.pi*v)-.39*(2*u-1)**2+.16*(v-.5)
            m.vertex((x,y,z),(u,v))
    for j in range(rows):
        for i in range(cols):a=j*(cols+1)+i;b=a+cols+1;m.quad(a,a+1,b+1,b)
    return m

def debris():
    m=Mesh('Debris');rng=np.random.default_rng(80423)
    for chip in range(65):
        for attempt in range(1000):
            c=np.array([rng.uniform(-1.0,.90),rng.uniform(-4.5,4.5),rng.uniform(.8,7.2)])
            radius=(c[1]/5.1)**2+((c[2]-4)/3.6)**2+(c[0]/1.9)**2
            # Protect central broad-leaf image while leaving peripheral sediment.
            if radius<.78 and (abs(c[1])>1.5 or abs(c[2]-4)>2.0):break
        else:raise RuntimeError('Could not place contained sediment')
        size=rng.uniform(.025,.16);thread=chip%5==0
        if thread:size*=.70
        # Unequal six-point octahedra, stretched thin for occasional woody threads.
        scale=np.array([size*.42,size*(3.2 if thread else .85),size*(.20 if thread else 1.1)])
        angle=rng.uniform(0,2*math.pi);cs,sn=math.cos(angle),math.sin(angle)
        local=np.array([[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]],float)
        local*=rng.uniform(.72,1.15,(6,1))*scale
        local[:,[1,2]]=local[:,[1,2]]@np.array([[cs,-sn],[sn,cs]])
        start=len(m.p)
        for p in local:m.vertex(c+p,((p[1]/max(size,1e-6)+1)*.5,(p[2]/max(size,1e-6)+1)*.5))
        for face in [(0,2,4),(0,4,3),(0,3,5),(0,5,2),(1,4,2),(1,3,4),(1,5,3),(1,2,5)]:m.tri(*(start+i for i in face))
    return m

def main():
    meshes={'Body':sphere('Body',96,160,True),'Leaf':leaf(),'Debris':debris(),'BubbleSource':sphere('BubbleSource',16,32)}
    manifest=dict(schema_version=1,generator_source='Tools/UsfMaterials/author_amber_hero.py',generator_sha256=sha(Path(__file__).read_bytes()),units='centimeters',axes='+X front, Y width, Z up',nominal_dimensions_cm=dict(width=11,height=7.88,depth=4.2),body_representation='Closed outward-wound irregular convex pebble, one-sided native optical material; NO opaque backing',body_uv='U=(Y+5.5)/11,V=Z/8; current AmberSpecimenV1 body maps compatible',leaf_representation='Curved 5.8x4.2cm rectangular tessellated carrier; full UV0..1. Photograph opacity mask supplies actual leaf outline/holes; carrier is NOT the final botanical silhouette.',debris=dict(count=65,seed=80423,representation='Actual irregular dark chips and sparse elongated woody threads; deterministic placement only, no appearance-noise texture'),bubble_source='Closed outward UV sphere radius1cm at origin; instance transforms and bubble optics owned by scene, not this source',meshes={role:m.save(role in ['Body','BubbleSource']) for role,m in meshes.items()},maps={},limitations=['No native-rendered optical or visual correctness claim from source generation','Full rectangular leaf carrier must use photographed opacity mask, not opaque shading','Body planarUV and older analytical thickness remain an approximation, not front/back ray-traced chord length','BubbleSource geometry alone does not establish air/resin interface rendering; renderer material must be chosen independently'])
    write('Manifest.json',(json.dumps(manifest,indent=2)+'\n').encode())
    print(json.dumps(dict(output=str(OUT),meshes={k:{x:v[x] for x in ['vertices','triangles','bounds','degenerate_triangles','closed_edge_manifold','consistent_edge_winding','signed_volume_cm3']} for k,v in manifest['meshes'].items()}),indent=2))
if __name__=='__main__':main()


