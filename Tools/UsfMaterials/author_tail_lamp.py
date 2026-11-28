"""Original compact lamp source authoring; only TailLampV1 is writable.

Host: python author_tail_lamp.py --stage maps
Blender4.4 factory-startup background CPU4: --python this_file -- --stage scene
Optional source-only beauty: --stage preview (loads selected packed .blend).
Coordinates are centimeters: +X front, Y width24, Z0..10, depthX4.5.
Lens is exactly one exterior one-sided optical sheet. Wall thickness.25cm is
material metadata; no inner transparent sheet or coincident transparent surfaces.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import sys
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Plugins/CkTests/Resources/CkUsf/TailLampV1'
SLOTS = ['Lens', 'Reflector', 'Housing', 'LED', 'Gasket', 'Fastener', 'LEDPackage']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def immutable(path, data):
    if not path.resolve().is_relative_to(OUTPUT.resolve()):
        raise RuntimeError('Output escaped TailLampV1')
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError('Preserve differing source output: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def maps():
    import numpy as np
    from PIL import Image
    width, height = 2048, 1024
    u, v = np.meshgrid((np.arange(width) + .5) / width, (np.arange(height) + .5) / height)
    # Molded vertical prism flutes, with weak orthogonal tooling. Heights are cm.
    lens_h = .0035 * np.cos(2 * np.pi * u * 168) + .0006 * np.cos(2 * np.pi * v * 64)
    reflector_h = .00028 * np.cos(2 * np.pi * v * 196)
    housing_h = .0005 * np.cos(2 * np.pi * u * 114) * np.cos(2 * np.pi * v * 48)
    def normal(h):
        du = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * 24 / width)
        dv = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * 10 / height)
        n = np.stack([-du, -dv, np.ones_like(h)], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        return np.round((n * .5 + .5) * 255).astype(np.uint8)
    ridge = .5 + .5 * np.cos(2 * np.pi * u * 168)
    arrays = {
        'LensNormal': normal(lens_h),
        'LensRoughness': np.round((.065 + .012 * ridge) * 255).astype(np.uint8),
        'LensThickness': np.round((.5 + .12 * np.cos(2 * np.pi * u * 6) * np.cos(2 * np.pi * v * 3)) * 65535).astype(np.uint16),
        'ReflectorNormal': normal(reflector_h),
        'ReflectorRoughness': np.round((.095 + .025 * (.5 + .5 * np.cos(2 * np.pi * v * 196))) * 255).astype(np.uint8),
        'HousingNormal': normal(housing_h),
        'HousingRoughness': np.round((.43 + .025 * np.cos(2 * np.pi * u * 12) * np.cos(2 * np.pi * v * 7)) * 255).astype(np.uint8)}
    linear = np.stack([np.full_like(u, .028), np.full_like(u, .034), np.full_like(u, .041)], -1)
    linear *= (1 + .025 * np.cos(2 * np.pi * u * 12) * np.cos(2 * np.pi * v * 7))[:, :, None]
    srgb = np.where(linear <= .0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - .055)
    arrays['HousingBaseColor'] = np.round(np.clip(srgb, 0, 1) * 255).astype(np.uint8)
    records = {}
    for name, array in arrays.items():
        buffer = io.BytesIO()
        Image.fromarray(array).save(buffer, format='PNG', compress_level=9)
        data = buffer.getvalue()
        path = 'Maps/' + name + '.png'
        immutable(OUTPUT / path, data)
        records[name] = {'path': path, 'sha256': sha(data), 'width': width, 'height': height,
            'channel': 'RGB' if array.ndim == 3 else 'R', 'bit_depth': 16 if name == 'LensThickness' else 8,
            'color_space': 'sRGB' if name == 'HousingBaseColor' else 'linear',
            'normal_convention': 'DirectX tangent space; Nx=-dH/dU, Ny=-dH/dV; no green flip' if name.endswith('Normal') else None}
    receipt = {'maps': records, 'authoring': 'Original deterministic modeled tooling profiles; no external scans, random/color noise or copied product artwork.',
        'lens_prism_pitch_cm': 24 / 168, 'lens_profile_amplitude_cm': .0035,
        'lens_thickness_map_decode_cm': '.25*(.9+.2*R); original full nominal range.225..275cm; authored map narrower',
        'height_normal_formula': 'N=normalize(-centralDifferenceU(H)/physicalUspacing,-centralDifferenceV(H)/physicalVspacing,1)',
        'uv_basis': 'OBJ source UV0 U=(Y+12)/24,V=Z/10; PNG rows increase V. Keep all map orientations identical; verify imported tangent basis before claiming UE optics.'}
    immutable(OUTPUT / 'MapsReceipt.json', (json.dumps(receipt, indent=2, sort_keys=True) + '\n').encode())
    print('TAIL_LAMP_MAPS_READY', len(records), flush=True)


def contour(width, height, radius, count=12):
    # Counterclockwise in Y/Z; viewed from +X this gives outward +X normals.
    result = []
    for cy, cz, start in [(width/2-radius, height/2-radius, 0),
                          (-width/2+radius, height/2-radius, 90),
                          (-width/2+radius, -height/2+radius, 180),
                          (width/2-radius, -height/2+radius, 270)]:
        for i in range(count):
            a = math.radians(start + i * 90 / count)
            result.append((cy + radius * math.cos(a), 5 + cz + radius * math.sin(a)))
    return result


def scene():
    import bpy
    from mathutils import Vector
    if (OUTPUT / 'Manifest.json').exists():
        manifest = json.loads((OUTPUT / 'Manifest.json').read_text())
        if manifest['generator_sha256'] != sha(Path(__file__).read_bytes()):
            raise RuntimeError('Preserve existing lamp; generator differs')
        for item in [*manifest['meshes'].values(), *manifest['maps'].values(), manifest['blend']]:
            if sha((OUTPUT / item['path']).read_bytes()) != item['sha256']:
                raise RuntimeError('Preserve changed source artifact')
        print('TAIL_LAMP_EXISTING_SOURCE_VERIFIED', flush=True)
        return
    map_receipt = json.loads((OUTPUT / 'MapsReceipt.json').read_text())
    for info in map_receipt['maps'].values():
        if sha((OUTPUT / info['path']).read_bytes()) != info['sha256']:
            raise RuntimeError('Tooling map changed')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = .01
    groups = {key: [] for key in SLOTS}
    materials = {}
    specs = {'Lens': ((.55,.009,.004,1),.08,0), 'Reflector': ((.82,.84,.86,1),.11,1),
             'Housing': ((.028,.034,.041,1),.43,0), 'LED': ((.9,.22,.06,1),.22,0),
             'Gasket': ((.008,.009,.01,1),.64,0), 'Fastener': ((.3,.32,.34,1),.25,1),
             'LEDPackage': ((.55,.51,.42,1),.42,0)}
    for key,(color,rough,metal) in specs.items():
        mat=bpy.data.materials.new(key);mat.use_nodes=True
        bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=color
        bsdf.inputs['Roughness'].default_value=rough;bsdf.inputs['Metallic'].default_value=metal
        if key=='LED':
            bsdf.inputs['Emission Color'].default_value=(1,.09,.015,1)
            bsdf.inputs['Emission Strength'].default_value=3
        if key=='Lens':
            # Source preview only: thin transparent mix to reveal authored assembly.
            # Native UE optical material and physical wall are configured separately.
            nodes=mat.node_tree.nodes;links=mat.node_tree.links
            transparent=nodes.new('ShaderNodeBsdfTransparent');transparent.inputs[0].default_value=(.93,.3,.22,1)
            mix=nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.18
            links.new(transparent.outputs[0],mix.inputs[1]);links.new(bsdf.outputs[0],mix.inputs[2])
            links.new(mix.outputs[0],nodes.get('Material Output').inputs['Surface'])
        materials[key]=mat
    def add_mesh(name, slot, vertices, faces, smooth=False):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
        mesh.materials.append(materials[slot]);groups[slot].append(obj)
        uv=mesh.uv_layers.new(name='UVMap')
        for poly in mesh.polygons:
            poly.use_smooth=smooth
            for li in poly.loop_indices:
                pos=mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv=((pos.y+12)/24,pos.z/10)
        return obj
    def ring_mesh(name,slot,rings,cap_back=False,cap_front=False,smooth=False):
        vertices=[]
        for x,w,h,r,cy in rings:
            vertices += [(x,y+cy,z) for y,z in contour(w,h,r)]
        n=len(contour(*rings[0][1:4]));faces=[]
        for j in range(len(rings)-1):
            for i in range(n):
                k=(i+1)%n;faces.append((j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i))
        if cap_back:faces.append(tuple(reversed(range(n))))
        if cap_front:faces.append(tuple((len(rings)-1)*n+i for i in range(n)))
        return add_mesh(name,slot,vertices,faces,smooth)
    # Closed housing bowl: outer back, rolled perimeter, front rim, inner wall and back interior.
    ring_mesh('Housing_Bowl','Housing',[(-2.25,22.8,8.8,.8,0),(-2.05,24,10,1.2,0),
              (1.55,24,10,1.2,0),(1.9,23.6,9.6,1.0,0),(1.92,22.6,8.6,.85,0),
              (-1.95,22.6,8.6,.85,0)],True,True,True)
    # Single smooth exterior lens sheet, center domeX2.25 -> edgeX1.97.
    outline=contour(22.8,8.8,.9,24);n=len(outline);vertices=[(2.25,0,5)];faces=[]
    for ring in range(1,33):
        t=ring/32
        for y,z in outline:vertices.append((1.97+.28*(1-t*t),y*t,5+(z-5)*t))
    for i in range(n):faces.append((0,1+i,1+(i+1)%n))
    for ring in range(1,32):
        a=1+(ring-1)*n;b=1+ring*n
        for i in range(n):k=(i+1)%n;faces.append((a+i,b+i,b+k,a+k))
    lens=add_mesh('Optical_Exterior_SingleSheet','Lens',vertices,faces,True)
    # Three genuine recessed faceted reflector cups. No flat image pretending to be geometry.
    for index,cy in enumerate([-7.15,0,7.15]):
        cup=ring_mesh('ReflectorCup_'+str(index),'Reflector',[(-1.38,3.5,4.8,.5,cy),
            (-.85,4.6,5.9,.65,cy),(.1,5.65,6.8,.8,cy),(1.57,6.65,7.8,.95,cy)],False,False,False)
        # Face the optical interior toward +X rather than outside of each bowl.
        for poly in cup.data.polygons:pass
        bpy.context.view_layer.objects.active=cup;cup.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.flip_normals();bpy.ops.object.mode_set(mode='OBJECT');cup.select_set(False)
        back=[(-1.38,y+cy,z) for y,z in contour(3.5,4.8,.5)]
        add_mesh('ReflectorBack_'+str(index),'Reflector',back,[tuple(range(len(back)))])
    def box(name,slot,center,size,bevel=.05):
        bpy.ops.mesh.primitive_cube_add(size=1,location=center)
        obj=bpy.context.object;obj.name=name;obj.dimensions=size
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        obj.data.materials.append(materials[slot]);groups[slot].append(obj)
        modifier=obj.modifiers.new('ManufacturedEdgeRadius','BEVEL');modifier.width=min(bevel,min(size)*.2);modifier.segments=3
        obj.modifiers.new('WeightedNormals','WEIGHTED_NORMAL')
        uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
        for poly in obj.data.polygons:
            for li in poly.loop_indices:
                pos=obj.matrix_world @ obj.data.vertices[obj.data.loops[li].vertex_index].co
                uv.data[li].uv=((pos.y+12)/24,pos.z/10)
        return obj
    for cy in [-3.57,3.57]:box('ChamberDivider','Housing',(-.1,cy,5),(3.1,.22,8.15),.06)
    for index,cy in enumerate([-7.15,0,7.15]):
        for row,z in enumerate([3.65,6.35]):
            box('LEDPackage_'+str(index)+'_'+str(row),'LEDPackage',(-1.10,cy,z),(.4,1.55,1.15),.10)
            box('EmitterChip_'+str(index)+'_'+str(row),'LED',(-.86,cy,z),(.10,.85,.5),.025)
            for side in [-1,1]:box('EmitterContact','Reflector',(-.83,cy+side*.56,z),(.05,.16,.55),.015)
    # Continuous narrow gasket bead, contained behind the exterior optical sheet.
    line=contour(23.05,9.05,.96,24);verts=[];faces=[]
    for y,z in line:
        dy=y/11.525;dz=(z-5)/4.525;length=math.hypot(dy,dz);dy/=length;dz/=length
        for j in range(8):
            a=2*math.pi*j/8;verts.append((1.97+.055*math.cos(a),y+dy*.055*math.sin(a),z+dz*.055*math.sin(a)))
    for i in range(len(line)):
        for j in range(8):faces.append((i*8+j,((i+1)%len(line))*8+j,((i+1)%len(line))*8+(j+1)%8,i*8+(j+1)%8))
    add_mesh('PerimeterSeal','Gasket',verts,faces,True)
    # Four recessed fasteners. Slots are separate dark inserts in the screw heads.
    for y in [-10.85,10.85]:
        for z in [.6,9.4]:
            bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.16,depth=.06,location=(1.96,y,z),rotation=(0,math.pi/2,0))
            obj=bpy.context.object;obj.name='FastenerHead';obj.data.materials.append(materials['Fastener']);groups['Fastener'].append(obj)
            for poly in obj.data.polygons:poly.use_smooth=False
            box('FastenerSlot','Housing',(1.993,y,z),(.008,.21,.045),.008)
    # Map-backed source materials use exactly the authored maps, packed into the .blend.
    for slot in ['Housing','Reflector','Lens']:
        mat=materials[slot];nodes=mat.node_tree.nodes;links=mat.node_tree.links;bsdf=nodes.get('Principled BSDF')
        for suffix,target in [('Roughness','Roughness'),('BaseColor','Base Color')]:
            key=slot+suffix
            if key not in map_receipt['maps']:continue
            tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OUTPUT/map_receipt['maps'][key]['path']),check_existing=True)
            tex.image.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color';links.new(tex.outputs['Color'],bsdf.inputs[target])
    bpy.context.view_layer.update()
    manifest={'schema_version':1,'generator_source':'Tools/UsfMaterials/author_tail_lamp.py',
        'generator_sha256':sha(Path(__file__).read_bytes()),'units':'centimeters','axes':'+X front; width+Y; height+Z; floorZ0',
        'nominal_dimensions_cm':{'width':24,'height':10,'depth':4.5},'lens_wall_thickness_cm':.25,
        'lens_representation':'Exactly one exterior optical sheet; no inner transparent shell. Thickness is shader-authored. Lens faces point +X.',
        'meshes':{},'maps':map_receipt['maps'],'map_authoring':map_receipt,
        'provenance':'Original project-authored geometry and analytical molded/tooling maps, no external asset/scanned optics/product logo.',
        'limits':'Source Blender preview is geometry lookdev only with transparent-mix lens, not UE/native optical proof, production lens ray tracing, retroreflective certification or photometry. OBJ importer may transformY/UVV; verify runtime basis independently.'}
    deps=bpy.context.evaluated_depsgraph_get()
    all_positions=[]
    for slot,objects in groups.items():
        lines=['# Original compact lamp component; centimeters +Xfront','mtllib SM_TailLamp_'+slot+'.mtl','g '+slot,'usemtl '+slot];positions=[];texcoords=[];normals=[];triangles=[]
        for obj in objects:
            evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh();mesh.calc_loop_triangles();base=len(positions)
            positions.extend([tuple(obj.matrix_world @ vertex.co) for vertex in mesh.vertices])
            for triangle in mesh.loop_triangles:
                tri=[]
                for li in triangle.loops:
                    vi=mesh.loops[li].vertex_index;pos=positions[base+vi]
                    uv=mesh.uv_layers.active.data[li].uv if mesh.uv_layers.active else ((pos[1]+12)/24,pos[2]/10)
                    # Source axes and UVs stay explicit even for factory primitives.
                    texcoords.append((float(uv[0]),float(uv[1])))
                    nrm=obj.matrix_world.to_3x3() @ mesh.corner_normals[li].vector
                    nrm.normalize();normals.append(tuple(nrm));tri.append((base+vi+1,len(texcoords),len(normals)))
                triangles.append(tri)
            evaluated.to_mesh_clear()
        for vertex in positions:lines.append('v '+' '.join(format(float(x),'.9g') for x in vertex))
        for uv in texcoords:lines.append('vt '+' '.join(format(float(x),'.9g') for x in uv))
        for normal in normals:lines.append('vn '+' '.join(format(float(x),'.9g') for x in normal))
        for tri in triangles:lines.append('f '+' '.join('/'.join(map(str,item)) for item in tri))
        data=('\n'.join(lines)+'\n').encode('ascii');relative='Meshes/SM_TailLamp_'+slot+'.obj'
        mtl=('newmtl '+slot+'\nKd .3 .3 .3\n').encode('ascii')
        bounds=[[min(v[i] for v in positions) for i in range(3)],[max(v[i] for v in positions) for i in range(3)]]
        degenerate=0
        for tri in triangles:
            a,b,c=[Vector(positions[t[0]-1]) for t in tri]
            if (b-a).cross(c-a).length<1e-9:degenerate+=1
        if degenerate:raise RuntimeError('Degenerate source triangles in '+slot)
        if any(not -1e-6<=value<=1+1e-6 for uv in texcoords for value in uv):raise RuntimeError('UVs outside normalized bounds in '+slot)
        immutable(OUTPUT/relative,data)
        immutable(OUTPUT/('Meshes/SM_TailLamp_'+slot+'.mtl'),mtl)
        manifest['meshes'][slot]={'path':relative,'sha256':sha(data),'slot':slot,'bounds':bounds,'vertices':len(positions),'triangles':len(triangles),'degenerate_triangles':degenerate,'uv_bounds':[[min(v[i] for v in texcoords) for i in range(2)],[max(v[i] for v in texcoords) for i in range(2)]]}
        all_positions.extend(positions)
    manifest['actual_bounds_cm']=[[min(v[i] for v in all_positions) for i in range(3)],[max(v[i] for v in all_positions) for i in range(3)]]
    # A stable source-only presentation, clearly separate from UE proof.
    world=bpy.data.worlds.new('SourceStudio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.18,1);world.node_tree.nodes['Background'].inputs[1].default_value=.35;scene.world=world
    def area(name,location,energy,size):
        light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size
        obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=location;obj.rotation_euler=(Vector((0,0,5))-obj.location).to_track_quat('-Z','Y').to_euler()
    area('Key',(22,-17,27),1800,18);area('Fill',(16,18,12),1200,15);area('Rim',(-8,0,22),1500,12)
    camera=bpy.data.cameras.new('SourceCamera');obj=bpy.data.objects.new('SourceCamera',camera);scene.collection.objects.link(obj);obj.location=(36,-29,20);obj.rotation_euler=(Vector((0,0,5))-obj.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=31;scene.camera=obj
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=1280;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    bpy.ops.file.pack_all();blend=OUTPUT/'Source/TailLamp.blend';blend.parent.mkdir(parents=True,exist_ok=True)
    if blend.exists():raise RuntimeError('Preserve existing editable source')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend));manifest['blend']={'path':'Source/TailLamp.blend','sha256':sha(blend.read_bytes())}
    immutable(OUTPUT/'Manifest.json',(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode())
    print('TAIL_LAMP_SOURCE_READY',str(OUTPUT/'Manifest.json'),flush=True)


def preview():
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT/'Source/TailLamp.blend'))
    for name,cutaway in [('SourceAssembly-Lit-Blender',False),('SourceAssembly-Cutaway-Blender',True)]:
        path=OUTPUT/'Proof'/(name+'.png')
        if path.exists():continue
        path.parent.mkdir(parents=True,exist_ok=True)
        bpy.data.objects['Optical_Exterior_SingleSheet'].hide_render=cutaway
        bpy.context.scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        print('TAIL_LAMP_SOURCE_PREVIEW',str(path),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',choices=['maps','scene','preview'],required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    {'maps':maps,'scene':scene,'preview':preview}[args.stage]()


if __name__=='__main__':main()
