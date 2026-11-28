"""Original centimeter display solids; no editor/Blender dependency or copied geometry.

All OBJ files use +X front, +Y width, +Z up and authored smooth normals.
Existing differing outputs are immutable: use a new resource version to revise them.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Plugins/CkTests/Resources/CkUsf/OpticalPairV1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(relative, data):
    path = OUT / relative
    if not path.resolve().is_relative_to(OUT.resolve()):
        raise RuntimeError('Escaped resource directory')
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError('Preserve differing source ' + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
    return {'path': relative, 'sha256': sha(data)}


class Mesh:
    def __init__(self, name, width=18, height=11):
        self.name, self.width, self.height = name, width, height
        self.p, self.f, self.components = [], [], []

    def vertex(self, x, y, z):
        self.p.append((x, y, z))
        return len(self.p) - 1

    def tri(self, a, b, c):
        self.f.append((a, b, c))

    def join(self, a, b):
        for i in range(len(a)):
            j = (i + 1) % len(a)
            self.tri(a[i], b[i], b[j])
            self.tri(a[i], b[j], a[j])

    def ring(self, x, width, height, radius, cy=0, cz=5.5, curve=0):
        # Counterclockwise viewed from +X. Equal arc intervals, actual straight sides.
        ring = []
        for sy, sz, start in [(1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)]:
            for i in range(17):
                angle = math.radians(start + i * 90 / 16)
                y = sy * (width / 2 - radius) + radius * math.cos(angle)
                z = sz * (height / 2 - radius) + radius * math.sin(angle)
                bulge = curve * (1 - (y / (width / 2)) ** 2) * (1 - (z / (height / 2)) ** 2)
                ring.append(self.vertex(x + bulge, y + cy, z + cz))
        return ring

    def cap(self, boundary, x, width, height, radius, front, cy=0, cz=5.5, curve=0):
        # Homothetic nested rings resolve the shallow cover curvature without a large fan.
        previous = boundary
        start = len(self.f)
        for i in range(1, 19):
            scale = 1 - i / 19
            current = self.ring(x, width * scale, height * scale, radius * scale, cy, cz)
            # Curvature uses full-face coordinates, not each inner ring's extent.
            for index in current:
                px, y, z = self.p[index]
                self.p[index] = (px + curve * (1 - ((y-cy)/(width/2))**2) * (1 - ((z-cz)/(height/2))**2), y, z)
            self.join(previous, current)
            previous = current
        center = self.vertex(x + curve, cy, cz)
        for i in range(len(previous)):
            self.tri(previous[i], center, previous[(i + 1) % len(previous)])
        # join inward rings naturally faces -X; flip for front cap.
        if front:
            self.f[start:] = [(a, c, b) for a, b, c in self.f[start:]]

    def slab(self, width, height, radius, back, front, bevel, cy=0, cz=5.5, curve=0):
        start = len(self.f)
        # Six smooth bevel samples on each edge, with a genuine finite side wall.
        profile = []
        for i in range(7):
            t = math.pi / 2 * i / 6
            profile.append((back + bevel * (1-math.cos(t)), bevel * (1-math.sin(t))))
        for i in range(7):
            t = math.pi / 2 * i / 6
            profile.append((front-bevel+bevel*math.sin(t), bevel*(1-math.cos(t))))
        rings = [self.ring(x, width-2*inset, height-2*inset, radius-inset, cy, cz, curve) for x, inset in profile]
        for a, b in zip(rings, rings[1:]):
            self.join(a, b)
        self.f[start:] = [(a, c, b) for a, b, c in self.f[start:]]
        self.cap(rings[0], back, width-2*bevel, height-2*bevel, radius-bevel, False, cy, cz, curve)
        self.cap(rings[-1], front, width-2*bevel, height-2*bevel, radius-bevel, True, cy, cz, curve)
        self.components.append((start, len(self.f)))

    def rim(self, width, height, radius, band, back, front, bevel):
        start = len(self.f)
        # Closed annular section: outward wall, front bevel, inner wall, back face.
        profiles = [(back, 0), (front-bevel, 0), (front, bevel),
                    (front, band-bevel), (front-bevel, band), (back, band)]
        rings = [self.ring(x, width-2*d, height-2*d, radius-d) for x, d in profiles]
        for a, b in zip(rings, rings[1:]+rings[:1]):
            self.join(a, b)
        self.f[start:] = [(a, c, b) for a, b, c in self.f[start:]]
        self.components.append((start, len(self.f)))

    def save(self):
        # Validate the serialized precision, not merely higher precision intermediates.
        p = np.round(np.asarray(self.p, float), 9)
        f = np.asarray(self.f, int)
        cross = np.cross(p[f[:,1]]-p[f[:,0]], p[f[:,2]]-p[f[:,0]])
        areas = np.linalg.norm(cross, axis=1)/2
        if not np.isfinite(p).all() or np.any(areas < 1e-10):
            raise RuntimeError('Invalid triangle ' + self.name)
        edges = Counter(tuple(sorted((int(a), int(b)))) for face in f for a,b in zip(face, np.roll(face,-1)))
        directed = Counter((int(a),int(b)) for face in f for a,b in zip(face,np.roll(face,-1)))
        if not all(v == 2 for v in edges.values()) or not all(directed[a,b] == directed[b,a] == 1 for a,b in edges):
            raise RuntimeError('Nonmanifold/inconsistent winding ' + self.name)
        volumes = []
        for start,end in self.components:
            q = f[start:end]
            volume = float(np.einsum('ij,ij->i',p[q[:,0]],np.cross(p[q[:,1]],p[q[:,2]])).sum()/6)
            if volume <= 0:
                raise RuntimeError('Inward component ' + self.name)
            volumes.append(volume)
        n = np.zeros_like(p)
        for face, normal in zip(f,cross):
            for index in face:
                n[index] += normal
        lengths = np.linalg.norm(n,axis=1)
        if np.any(lengths < 1e-12):
            raise RuntimeError('Zero normal ' + self.name)
        n /= lengths[:,None]
        uv = np.column_stack((p[:,1]/self.width+.5, (p[:,2]-5.5)/self.height+.5))
        stem = 'SM_OpticalPair_' + self.name
        lines = ['# Original centimeters, +X front, +Y width, +Z up', 'mtllib '+stem+'.mtl', 'g '+self.name, 'usemtl '+self.name]
        lines += ['v %.9f %.9f %.9f' % tuple(v) for v in p]
        lines += ['vt %.9f %.9f' % tuple(v) for v in uv]
        lines += ['vn %.9f %.9f %.9f' % tuple(v) for v in n]
        lines += ['s 1']
        lines += ['f '+' '.join('%d/%d/%d' % (i+1,i+1,i+1) for i in face) for face in f]
        record = write('Meshes/'+stem+'.obj', ('\n'.join(lines)+'\n').encode('ascii'))
        record.update(slot=self.name, mtl=write('Meshes/'+stem+'.mtl', ('newmtl '+self.name+'\nKd 0.5 0.5 0.5\nd 1\n').encode('ascii')),
                      vertices=len(p), triangles=len(f), bounds={'min':p.min(0).tolist(),'max':p.max(0).tolist()},
                      uv_bounds={'min':uv.min(0).tolist(),'max':uv.max(0).tolist()}, closed_edge_manifold=True,
                      consistent_edge_winding=True, degenerate_triangles=0, minimum_area_cm2=float(areas.min()),
                      component_signed_volumes_cm3=volumes, vertex_normals='Authored area-weighted smooth normals')
        return record


def main():
    glass = Mesh('GlassCover',17,10)
    glass.slab(17,10,.78,2.07,2.40,.055,curve=.10)
    panel = Mesh('Panel',16.35,9.35)
    panel.slab(16.35,9.35,.55,1.23,1.41,.025)
    housing = Mesh('Housing')
    housing.slab(18,11,.95,0,.94,.14)
    housing.rim(18,11,.95,.67,.85,1.48,.10)
    metal = Mesh('MetalTrim')
    metal.rim(17.68,10.68,.83,.30,1.40,1.58,.035)
    # Small standoffs outside the active panel support the visibly floated cover.
    for y in [-8.24,8.24]:
        for z in [.72,10.28]:
            metal.slab(.24,.24,.10,1.52,2.06,.025,cy=y,cz=z)
    body = ROOT/'Plugins/CkTests/Resources/CkUsf/AmberHeroV1/Meshes/SM_AmberHero_Body.obj'
    amber = json.loads((body.parent.parent/'Manifest.json').read_text())
    if sha(body.read_bytes()) != amber['meshes']['Body']['sha256']:
        raise RuntimeError('Reused AmberHero body differs from its immutable manifest')
    manifest = dict(schema_version=1, generator_source='Tools/UsfMaterials/author_optical_pair.py',
        generator_sha256=sha(Path(__file__).read_bytes()), units='centimeters', axes='+X front, +Y width, +Z up',
        display_dimensions_cm={'width_Y':18,'height_Z':11,'depth_X':2.5}, floor_Z=0,
        design='Original beveled instrument housing, recessed bezel and illuminated panel, floated softly bowed solid cover. No copied concept geometry.',
        uv_contract='Planar YZ on all solids: U=Y/role_width+0.5, V=(Z-5.5)/role_height+0.5; GlassCover 17x10cm, Panel 16.35x9.35cm, Housing/MetalTrim 18x11cm. Front camera +X; UV V increases upward. Back and side projection overlaps intentionally.',
        glass={'edge_thickness_cm':.33,'bevel_cm':.055,'central_bow_cm':.10,'minimum_panel_gap_cm':.66,'surface':'Closed tessellated solid; broad central faces retain gently varying normals. Finite polished edge, bevel and air gap establish silhouette without strong refraction.'},
        layout={'housing_backplate_X':[0,.94],'housing_rim_X':[.85,1.48],'panel_X':[1.23,1.41], 'metal_bezel_X':[1.40,1.58],'glass_nominal_X':[2.07,2.50], 'standoffs_X':[1.52,2.06]},
        opal_reused_body={'path':body.relative_to(ROOT).as_posix(),'sha256':sha(body.read_bytes()),'source_slot':'Body','target_material_role':'Opal','bounds':amber['meshes']['Body']['bounds'],'uv':'Existing U=(Y+5.5)/11,V=Z/8; body referenced in place, not regenerated or copied'},
        meshes={m.name:m.save() for m in [glass,panel,housing,metal]},
        limitations=['Geometry validation only; no native visual correctness claim.', 'MTL files declare slots only; production optical materials assigned by scene.', 'Housing/trim contain separate closed components with intentional assembly overlaps.'])
    write('Geometry.json',(json.dumps(manifest,indent=2)+'\n').encode())
    print(json.dumps({k:{key:v[key] for key in ['vertices','triangles','bounds','minimum_area_cm2','component_signed_volumes_cm3']} for k,v in manifest['meshes'].items()},indent=2))


if __name__ == '__main__':
    main()
