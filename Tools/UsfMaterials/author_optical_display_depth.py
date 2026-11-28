"""Additive original thick-cover display geometry; V1 sources remain immutable.

Source axes remain +X front, +Y width, +Z up, centimeters. The assembly's
horizontal staging transform is deliberately owned by the scene, not these OBJs.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import json
import math
import author_optical_pair as geometry

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Plugins/CkTests/Resources/CkUsf/OpticalDisplayDepthV2'


def glass_cover():
    mesh = geometry.Mesh('GlassCover',17,10)
    width,height,radius,back,front,bevel = 17,10,.9,2.3,4.1,.2
    # Fine circular bevels and uniform sidewall samples retain a polished edge
    # rather than allowing the thick long wall to dominate area-weighted normals.
    profile = []
    for index in range(13):
        angle = math.pi/2*index/12
        profile.append((back+bevel*(1-math.cos(angle)),bevel*(1-math.sin(angle))))
    for index in range(1,15):
        profile.append((back+bevel+(front-back-2*bevel)*index/15,0))
    for index in range(13):
        angle = math.pi/2*index/12
        profile.append((front-bevel+bevel*math.sin(angle),bevel*(1-math.cos(angle))))
    rings = [mesh.ring(x,width-2*inset,height-2*inset,radius-inset) for x,inset in profile]
    for a,b in zip(rings,rings[1:]):
        mesh.join(a,b)
    mesh.f = [(a,c,b) for a,b,c in mesh.f]
    mesh.cap(rings[0],back,width-2*bevel,height-2*bevel,radius-bevel,False)
    mesh.cap(rings[-1],front,width-2*bevel,height-2*bevel,radius-bevel,True)
    mesh.components.append((0,len(mesh.f)))
    return mesh


def main():
    glass = glass_cover()
    panel = geometry.Mesh('Panel',16.35,9.35)
    panel.slab(16.35,9.35,.55,1.23,1.41,.025)
    housing = geometry.Mesh('Housing')
    housing.slab(18,11,.95,0,.94,.14)
    housing.rim(18,11,.95,.67,.85,1.48,.10)
    metal = geometry.Mesh('MetalTrim')
    metal.rim(17.68,10.68,.83,.30,1.40,1.58,.035)
    for y in [-8.24,8.24]:
        for z in [.72,10.28]:
            metal.slab(.24,.24,.10,1.52,2.29,.025,cy=y,cz=z)
    # Validate layout and exact assembly dimensions before writing any resource.
    expected = {'GlassCover':([2.3,-8.5,.5],[4.1,8.5,10.5]),
                'Panel':([1.23,-8.175,.825],[1.41,8.175,10.175]),
                'Housing':([0,-9,0],[1.48,9,11]),
                'MetalTrim':([1.4,-8.84,.16],[2.29,8.84,10.84])}
    meshes = [glass,panel,housing,metal]
    for mesh in meshes:
        actual = geometry.np.asarray(mesh.p)
        minimum,maximum = expected[mesh.name]
        if not geometry.np.allclose(actual.min(0),minimum,atol=1e-9,rtol=0) or not geometry.np.allclose(actual.max(0),maximum,atol=1e-9,rtol=0):
            raise RuntimeError('Unexpected exact V2 bounds: '+mesh.name)
    previous_out = geometry.OUT
    try:
        geometry.OUT = OUT
        records = {mesh.name:mesh.save() for mesh in meshes}
        manifest = dict(schema_version=2,
            generator_source='Tools/UsfMaterials/author_optical_display_depth.py',
            generator_sha256=geometry.sha(Path(__file__).read_bytes()),
            helper_source='Tools/UsfMaterials/author_optical_pair.py',
            helper_sha256=geometry.sha(Path(geometry.__file__).read_bytes()),
            units='centimeters',axes='+X front, +Y width, +Z up',floor_Z=0,
            display_dimensions_cm={'width_Y':18,'height_Z':11,'depth_X':4.1},
            glass={'width_Y_cm':17,'height_Z_cm':10,'thickness_cm':1.8,'back_X_cm':2.3,'front_X_cm':4.1,
                   'bevel_cm':.2,'outer_corner_radius_cm':.9,'central_bow_cm':0,
                   'sidewall_representation':'True 1.4cm straight polished wall between circular .2cm bevels; 14 intermediate wall rings; 12 intervals per bevel',
                   'minimum_panel_gap_cm':.89,'standoff_clearance_cm':.01},
            layout={'housing_backplate_X':[0,.94],'housing_rim_X':[.85,1.48],
                    'panel_X':[1.23,1.41],'metal_bezel_X':[1.40,1.58],
                    'glass_X':[2.3,4.1],'standoffs_X':[1.52,2.29]},
            design='Original additive thick optical cover with visibly deep polished edge, floated above recessed instrument panel and machined metallic bezel. Separate closed mesh components; no geometry copied from concept image.',
            uv_contract='Planar YZ: U=Y/role_width+.5; V=(Z-5.5)/role_height+.5; GlassCover 17x10, Panel 16.35x9.35, Housing/MetalTrim 18x11cm. Same V1 face texture contract; projected back/side UVs overlap intentionally.',
            staging_contract='Source axes unchanged. Horizontal display placement, pitch, floor elevation and camera are scene-owned; no baked rotation.',
            meshes=records,
            limitations=['Source topology and dimensional checks only; no native rendering claim.',
                         'MTL files declare exact role slots; production material binding belongs to scene.',
                         'Housing and trim contain intentional assembly overlaps between individually closed positive-volume components.',
                         'V1 generated resources and imported assets remain unchanged by this generator.'])
        geometry.write('Geometry.json',(json.dumps(manifest,indent=2)+'\n').encode())
    finally:
        geometry.OUT = previous_out
    print(json.dumps({'output':str(OUT),'meshes':{role:{key:record[key] for key in ['vertices','triangles','bounds','closed_edge_manifold','consistent_edge_winding','degenerate_triangles','component_signed_volumes_cm3']} for role,record in records.items()}},indent=2))


if __name__=='__main__':
    main()
