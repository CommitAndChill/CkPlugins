"""Author clustered multiscale mineral reflector utility maps; original color is unedited."""
from pathlib import Path
import hashlib,io,json,math,os
import numpy as np
from PIL import Image,ImageFilter
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Plugins/CkTests/Resources/CkUsf/OpalFireV1'
SOURCE=ROOT/'Plugins/CkTests/Resources/CkUsf/OpalPolishV2/Source'
SEED=715093

def sha(data):return hashlib.sha256(data).hexdigest()
def png(array):
    stream=io.BytesIO();Image.fromarray(array).save(stream,format='PNG',compress_level=9);return stream.getvalue()
def blur(array,radius):
    # Float planes retain numerical precision; Pillow Gaussian uses 8-bit authored data here.
    encoded=np.round(np.clip(array,0,1)*255).astype('uint8')
    return np.asarray(Image.fromarray(encoded).filter(ImageFilter.GaussianBlur(radius)),dtype=np.float64)/255

def cells(width,height,spacing,rng):
    """Jittered nearest-site cells: local 3x3 search, connected irregular Voronoi facets."""
    rows=math.ceil(height/spacing)+3;cols=math.ceil(width/spacing)+3
    gy,gx=np.mgrid[:rows,:cols]
    px=(gx-1+.5+rng.uniform(-.30,.30,(rows,cols)))*spacing
    py=(gy-1+.5+rng.uniform(-.30,.30,(rows,cols)))*spacing
    yy,xx=np.mgrid[:height,:width];by=yy//spacing+1;bx=xx//spacing+1
    best=np.full((height,width),np.inf);labels=np.zeros((height,width),np.int32)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            iy=by+dy;ix=bx+dx;distance=(xx-px[iy,ix])**2+(yy-py[iy,ix])**2
            mask=distance<best;best[mask]=distance[mask];labels[mask]=(iy*cols+ix)[mask]
    return labels,rows*cols,px.ravel(),py.ravel()

def main():
    original=(SOURCE/'OpalOriginal.png').read_bytes();prompt=(SOURCE/'ImagePrompt.txt').read_bytes()
    color=Image.open(io.BytesIO(original));color.load()
    if color.mode!='RGB' or color.size!=(1254,1254):raise RuntimeError('Expected preserved1254-square RGB original')
    width,height=color.size;rgb=np.asarray(color,dtype=float)/255;rng=np.random.default_rng(SEED)
    broad=np.asarray(color.filter(ImageFilter.GaussianBlur(9)),dtype=float)/255
    chroma=(broad.max(2)-broad.min(2))/np.maximum(broad.max(2),1e-8)
    colored=chroma>.19;cluster=blur(colored.astype(float),1.0)
    # Coarse, hue-independent cluster orientation field. No appearance-gradient derivatives.
    cy,cx=np.mgrid[:math.ceil(height/96)+2,:math.ceil(width/96)+2]
    cluster_angle=rng.uniform(-np.pi,np.pi,cy.shape);cluster_magnitude=rng.uniform(.12,.25,cy.shape)
    tilt_x=cluster_magnitude*np.cos(cluster_angle);tilt_y=cluster_magnitude*np.sin(cluster_angle)
    active=np.zeros((height,width),bool);sx=np.zeros((height,width));sy=np.zeros_like(sx)
    phase=np.zeros_like(sx)+.5;facet_rough=np.zeros_like(sx)+.19;records=[]
    for name,spacing,probability in [('flakes',12,.27),('sheets',42,.14)]:
        labels,count,px,py=cells(width,height,spacing,rng)
        selected=rng.random(count)<probability
        ay=np.clip((py/96).astype(int),0,cy.shape[0]-1);ax=np.clip((px/96).astype(int),0,cx.shape[1]-1)
        delta=rng.uniform(.04,.10,count);angle=rng.uniform(-np.pi,np.pi,count)
        tx=tilt_x[ay,ax]+delta*np.cos(angle);ty=tilt_y[ay,ax]+delta*np.sin(angle)
        magnitude=np.hypot(tx,ty);scale=np.minimum(1,.34/np.maximum(magnitude,1e-8));tx*=scale;ty*=scale
        use=selected[labels]&colored
        # Reject tiny clipped boundary slivers before assigning any facet orientation.
        clipped_area=np.bincount(labels[use],minlength=count)
        use &= clipped_area[labels]>=(16 if name=='flakes' else 100)
        phases=rng.uniform(.05,.95,count);rough=rng.uniform(.065,.12,count)
        active[use]=True;sx[use]=tx[labels[use]];sy[use]=ty[labels[use]]
        phase[use]=phases[labels[use]];facet_rough[use]=rough[labels[use]]
        touched,areas=np.unique(labels[use],return_counts=True)
        records.append(dict(scale=name,site_spacing_source_pixels=spacing,selection_probability=probability,visible_facets=int(len(touched)),active_pixels_before_overlap=int(use.sum()),visible_area_pixels_min=int(areas.min()),visible_area_pixels_median=float(np.median(areas)),visible_area_pixels_max=int(areas.max())))
    mask=blur(active.astype(float),.8)*cluster
    # Feather only1-2 source pixels; active interiors keep individual constant facet normals.
    sx=(blur(sx/.70+.5,.65)-.5)*.70;sy=(blur(sy/.70+.5,.65)-.5)*.70
    outside=mask<1/255;sx[outside]=0;sy[outside]=0
    length=np.sqrt(sx*sx+sy*sy+1);normal=np.stack([sx/length,sy/length,1/length],-1)
    normal_bytes=np.round((normal*.5+.5)*255).astype('uint8');normal_bytes[outside]=[128,128,255]
    body=blur(broad.mean(2),7);phase=blur(phase,.65)
    roughness=.19*(1-mask)+blur(facet_rough,.65)*mask
    arrays={'OpalColor':np.asarray(color),'OpalDomains':np.round(np.stack([mask,body,phase],-1)*255).astype('uint8'),
            'OpalDomainNormal':normal_bytes,'OpalPolishNormal':np.broadcast_to(np.array([128,128,255],np.uint8),(height,width,3)).copy(),
            'OpalRoughness':np.round(roughness*255).astype('uint8')}
    pending={'Source/OpalOriginal.png':original,'Source/ImagePrompt.txt':prompt};maps={}
    for name,array in arrays.items():
        relative='Textures/'+name+'.png';data=original if name=='OpalColor' else png(array)
        decoded=np.asarray(Image.open(io.BytesIO(data)))
        if not np.array_equal(decoded,array):raise RuntimeError('Pixel roundtrip failed: '+name)
        pending[relative]=data;maps[name]=dict(path=relative,sha256=sha(data),width=width,height=height,srgb=name=='OpalColor',channels='RGB' if array.ndim==3 else 'L',bit_depth=data[24],decoded_min=int(array.min()),decoded_max=int(array.max()),decoded_pixel_sha256=sha(decoded.tobytes()),decoded_roundtrip_verified=True)
    decoded=normal_bytes.astype(float)/255*2-1;slopes=decoded[:,:,:2]/decoded[:,:,2:3]
    max_slope=float(np.linalg.norm(slopes,axis=2).max())
    if max_slope>.35 or not np.all(normal_bytes[outside]==[128,128,255]):raise RuntimeError('Facet normal bound/flat exterior failed')
    coverage=float(active[colored].mean())
    if not .25<=coverage<=.40:raise RuntimeError('Unexpected colored-cluster facet coverage: '+str(coverage))
    stats=dict(scales=records,colored_cluster_pixels=int(colored.sum()),colored_cluster_image_fraction=float(colored.mean()),active_fraction_within_colored_clusters=coverage,active_image_fraction=float(active.mean()),feathered_mask_mean_within_colored_clusters=float(mask[colored].mean()),maximum_decoded_slope_magnitude=max_slope,decoded_slope_component_min=slopes.reshape(-1,2).min(0).tolist(),decoded_slope_component_max=slopes.reshape(-1,2).max(0).tolist(),flat_outside_mask_verified=True)
    report=dict(schema_version=1,generator_source='Tools/UsfMaterials/author_opal_fire_maps.py',generator_sha256=sha(Path(__file__).read_bytes()),seed=SEED,
        source=dict(path='Source/OpalOriginal.png',sha256=sha(original),provenance='Original built-in image generation2026-10-22; original artwork, not a scan. Numerical utility data are artist estimates, not measured mineral optics.',generation_image_id='exec-6f70bd07-e659-496b-9121-d0f11029d84d',prompt_support='Source/ImagePrompt.txt',prompt_sha256=sha(prompt)),maps=maps,
        color_preservation='Original RGB PNG and original prompt copied byte-identically from OpalPolishV2; no appearance artwork edits.',
        authoring=dict(domain_channels='R=spatial facet mask,G=broad body/depth value,B=facet spectral-phase artist estimate',normal_convention='DirectX tangent normalize(slope_u,slope_v,1), top-left image orientation, no green flip',orientation='Hue-independent seeded broadcluster tilt.12-.25 plus per-facetdelta.04-.10; constant within each nearest-site facet, clamped.34 beforeencoding; no luminance gradients.',facets='Jittered nearest-site irregular connected cells at12px and42px spacing, clipped to broad chromatic clusters; sheets override flakes; no per-pixel random normals.',boundary_feather_source_pixels=[1,2],polish_normal=[128,128,255],roughness_linear_range=[float(roughness.min()),float(roughness.max())],statistics=stats),
        limitations=['Reflector geometry, phase, depth and roughness are numerical artist estimates, not calibrated optical scans.','Facet orientation is authored material data, not a displacement or luminance-gradient normal.','These maps do not bake sparkle or illumination; visible response requires native lighting/render verification.'])
    pending['OpalTextures.json']=(json.dumps(report,indent=2)+'\n').encode()
    for relative,data in pending.items():
        path=(OUT/relative).resolve()
        if not path.is_relative_to(OUT.resolve()):raise RuntimeError('Output escaped owned resource')
        if path.exists() and path.read_bytes()!=data:raise RuntimeError('Refuse changed-existing authored output: '+str(path))
    for relative,data in pending.items():
        path=OUT/relative
        if path.exists():continue
        path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.pending')
        with temporary.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        if path.exists():raise RuntimeError('Concurrent output appeared')
        temporary.rename(path)
    assert (OUT/'Textures/OpalColor.png').read_bytes()==original==(OUT/'Source/OpalOriginal.png').read_bytes()
    print(json.dumps(dict(receipt=str(OUT/'OpalTextures.json'),source_sha256=sha(original),dimensions=[width,height],statistics=stats),indent=2))
if __name__=='__main__':main()
