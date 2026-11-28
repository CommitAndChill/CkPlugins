"""Original vector instrument artwork and manufactured finish data; no external images."""
from pathlib import Path
import hashlib,io,json,math,os
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Plugins/CkTests/Resources/CkUsf/OpticalPairV1'
SIZE=2048
SEED=48117

def sha(data):return hashlib.sha256(data).hexdigest()
def font(size):
    for file in ['C:/Windows/Fonts/bahnschrift.ttf','C:/Windows/Fonts/consola.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(file).is_file():return ImageFont.truetype(file,size)
    raise RuntimeError('A local scalable font is required for legible authored artwork')

def artwork():
    image=Image.new('RGB',(SIZE,SIZE),(0,0,0));draw=ImageDraw.Draw(image)
    cyan=(33,214,244);white=(213,239,242);dim=(14,74,90);accent=(68,159,180)
    def point(x,y):return (int(round(x*SIZE/18)),int(round(y*SIZE/11)))
    def line(points,color,width=.018):draw.line([point(*p) for p in points],fill=color,width=max(1,round(width*SIZE/18)))
    def arc(cx,cy,r,start,end,color,width=.018):
        points=[(cx+r*math.cos(math.radians(a)),cy+r*math.sin(math.radians(a))) for a in np.linspace(start,end,max(3,round(abs(end-start)*3)))]
        line(points,color,width)
    def text(x,y,value,height,color=white,anchor='mm'):
        # Compress glyphs horizontally so their physical aspect remains natural on 18:11 panel.
        f=font(round(height*SIZE/11));bounds=f.getbbox(value);w=bounds[2]-bounds[0];h=bounds[3]-bounds[1]
        tile=Image.new('RGBA',(w+12,h+12));d=ImageDraw.Draw(tile);d.text((6-bounds[0],6-bounds[1]),value,font=f,fill=(*color,255))
        tile=tile.resize((max(1,round(tile.width*11/18)),tile.height),Image.Resampling.LANCZOS)
        px,py=point(x,y)
        if anchor=='mm':px-=tile.width//2;py-=tile.height//2
        image.paste(tile,(px,py),tile)
    # Sparse outer registration and small electrical-status furniture.
    for x,y,sx,sy in [(1,.7,1,1),(17,.7,-1,1),(1,10.3,1,-1),(17,10.3,-1,-1)]:
        line([(x+sx*.35,y),(x,y),(x,y+sy*.22)],accent,.022)
    text(2.1,1.02,'SYSTEM 04',.21,accent)
    text(15.4,1.02,'READY',.21,cyan)
    line([(1.5,1.45),(5.1,1.45)],dim,.012)
    line([(12.7,1.45),(16.5,1.45)],dim,.012)
    # Principal precision dial: calibrated physical circles, not circular bitmap pixels.
    cx,cy=9.25,6.0
    arc(cx,cy,3.72,132,408,dim,.025)
    arc(cx,cy,3.56,132,408,accent,.012)
    arc(cx,cy,3.12,142,398,dim,.012)
    arc(cx,cy,2.96,149,391,cyan,.018)
    arc(cx,cy,3.82,132,330,cyan,.043)
    for index in range(101):
        angle=math.radians(132+276*index/100);major=index%10==0;medium=index%5==0
        outer=3.60;inner=outer-(.31 if major else .22 if medium else .12)
        col=cyan if index<=72 else accent
        line([(cx+inner*math.cos(angle),cy+inner*math.sin(angle)),(cx+outer*math.cos(angle),cy+outer*math.sin(angle))],col,.039 if major else .018)
        if major:
            text(cx+4.12*math.cos(angle),cy+4.12*math.sin(angle),str(index).zfill(2),.22,white)
    # Inner dotted telemetry track and bounded data windows.
    for index in range(54):
        angle=math.radians(150+240*index/53)
        arc(cx,cy,2.72,math.degrees(angle)-.42,math.degrees(angle)+.42,accent,.018)
    text(cx,cy-.75,'VELOCITY',.23,accent)
    text(cx,cy+.10,'72',1.08,white)
    text(cx,cy+.94,'M/S',.23,cyan)
    line([(cx-1.05,cy+1.35),(cx+1.05,cy+1.35)],dim,.012)
    text(cx,cy+1.68,'TRACK  /  04',.17,accent)
    # Side modules intentionally differ: compact scales on left, channel bars on right.
    text(2.65,3.15,'OUTPUT',.21,accent)
    for row in range(15):
        y=3.62+row*.235;length=.62 if row%5 else .97
        line([(1.85,y),(1.85+length,y)],cyan if row<10 else dim,.035)
        line([(3.2,y),(3.42,y)],accent,.016)
    text(2.7,7.5,'068',.43,white)
    text(2.7,8.05,'LOAD %',.18,accent)
    text(15.15,3.25,'CHANNELS',.21,accent)
    for row,fill in enumerate([.84,.61,.72,.44]):
        y=3.84+row*.78
        text(13.8,y-.23,str(row+1).zfill(2),.15,accent)
        line([(13.55,y),(16.5,y)],dim,.055)
        line([(13.55,y),(13.55+2.95*fill,y)],cyan,.055)
        for mark in range(11):line([(13.55+mark*.295,y+.12),(13.55+mark*.295,y+.19)],dim,.01)
    text(15.1,7.8,'NOMINAL',.18,cyan)
    line([(6.65,10.28),(11.85,10.28)],dim,.012)
    text(9.25,10.57,'CONTROL  /  072',.17,accent)
    return np.asarray(image)

def normals(height,dx,dy):
    dv,du=np.gradient(height,dy,dx);n=np.stack([-du,-dv,np.ones_like(du)],-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    return np.round((n*.5+.5)*255).astype('uint8')

def main():
    u,v=np.meshgrid((np.arange(SIZE)+.5)/SIZE,(np.arange(SIZE)+.5)/SIZE)
    # Fine manufactured substrate: original shallow parallel tooling and sparse etched grid.
    tooling=np.cos(2*np.pi*(u*360+.035*np.sin(v*15)))
    grid=np.maximum(np.exp(-(np.sin(np.pi*u*36)/.09)**2),np.exp(-(np.sin(np.pi*v*22)/.09)**2))
    display_height=.000012*tooling-.000020*grid
    base_linear=.0095+.00075*tooling+.0009*grid
    base=np.stack([base_linear*.90,base_linear*.98,base_linear*1.05],-1)
    base_srgb=np.where(base<=.0031308,12.92*base,1.055*np.power(base,1/2.4)-.055)
    # Smooth broad coating flow plus subvisible polish, no stochastic rainbow/color noise.
    flow=np.sin(2*np.pi*(u*.62+v*.18)+.22*np.sin(v*6))
    polish=np.cos(2*np.pi*(u*227+.10*v*v))
    glass_height=.0000038*polish+.000010*np.sin(2*np.pi*(u*1.4+v*.5))
    arrays={
        'DisplayEmission':artwork(),
        'DisplayBaseColor':np.round(np.clip(base_srgb,0,1)*255).astype('uint8'),
        'DisplayRoughness':np.round((.29+.018*tooling+.022*grid)*255).astype('uint8'),
        'DisplayNormal':normals(display_height,18/SIZE,11/SIZE),
        'GlassFinishNormal':normals(glass_height,18/SIZE,11/SIZE),
        'GlassFinishRoughness':np.round((.055+.006*flow+.003*polish)*255).astype('uint8'),
        'GlassCoating':np.round(np.clip(.50+.035*flow+.010*np.cos(2*np.pi*(v*.75-u*.12)),0,1)*65535).astype('uint16')}
    payloads={};records={}
    for name,array in arrays.items():
        stream=io.BytesIO();Image.fromarray(array).save(stream,format='PNG',compress_level=9);data=stream.getvalue()
        decoded=np.asarray(Image.open(io.BytesIO(data)))
        if not np.array_equal(decoded,array) or array.shape[:2]!=(SIZE,SIZE) or int(array.max())==int(array.min()):raise RuntimeError('Texture verification failed '+name)
        relative='Textures/'+name+'.png';payloads[relative]=data
        channels='RGB' if array.ndim==3 else 'R'
        records[name]=dict(path=relative,sha256=sha(data),width=SIZE,height=SIZE,channels=channels,bit_depth=data[24],srgb=name in ['DisplayEmission','DisplayBaseColor'],decoded_min=int(array.min()),decoded_max=int(array.max()),channel_min=array.reshape(-1,3).min(0).tolist() if channels=='RGB' else [int(array.min())],channel_max=array.reshape(-1,3).max(0).tolist() if channels=='RGB' else [int(array.max())],decoded_pixel_sha256=sha(array.tobytes()),decoded_roundtrip_verified=True,normal_convention='DirectX tangent; normalize(-dH/dUcm,-dH/dVcm,1); PNG top-left origin' if name.endswith('Normal') else None)
    receipt=dict(schema_version=1,generator_source='Tools/UsfMaterials/author_display_textures.py',generator_sha256=sha(Path(__file__).read_bytes()),seed=SEED,stochastic_sampling=False,maps=records,physical_panel_cm=dict(width=18,height=11),uv='Conventional top-left image; lead flips panel V at sampling. Glass maps need no specific direction.',artwork='Original PIL vector instrument graphics: 101 calibrated dial marks, nested arcs, minimal legible telemetry, asymmetric auxiliary bars; no logo, external image, simulated reflection or baked lighting.',manufacturing='Analytical shallow etched grid, parallel substrate tooling and gentle broad coating thickness; all nonflat sampled bitmap data.',normal_formula='normalize(-gradient(Hcm)/physical_Uspacing_cm,-gradient(Hcm)/physical_Vspacing_cm,1); data stored linear DirectX',coating_decode='GlassCoating normalized linear 16-bit utility R; nominal0.5 with gentle broad variation, shader chooses physical thickness scale.',provenance='Original code-native artwork and mathematical material data. Uses locally installed font rasterization only; no AI raster images, scans, external artwork or generic color noise.',limits='Source textures only; no native Unreal response, emission intensity, UV orientation, glass absorption, coating interference or visual acceptance established.')
    payloads['DisplayTextures.json']=(json.dumps(receipt,indent=2)+'\n').encode()
    # Preflight every exact destination before any output mutation; preserve all differing existing files.
    for relative,data in payloads.items():
        path=OUT/relative
        if not path.resolve().is_relative_to(OUT.resolve()):raise RuntimeError('Output escaped source root')
        if path.exists() and path.read_bytes()!=data:raise RuntimeError('Preserve differing authored source '+str(path))
    for relative,data in payloads.items():
        path=OUT/relative
        if path.exists():continue
        path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_name(path.name+'.pending')
        with temporary.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        if path.exists():raise RuntimeError('Concurrent output appeared '+str(path))
        temporary.rename(path)
    print(json.dumps(dict(receipt=str(OUT/'DisplayTextures.json'),maps={name:dict(channels=r['channels'],bit_depth=r['bit_depth'],range=[r['decoded_min'],r['decoded_max']]) for name,r in records.items()}),indent=2))
if __name__=='__main__':main()
