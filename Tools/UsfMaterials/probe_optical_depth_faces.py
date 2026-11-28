"""Temporary native glass opacity diagnostic, with exact shader byte restoration."""
from pathlib import Path
import json,sys
from optical_depth_command import submit
from verify_optical_pair import wait_reload
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/OpticalDepthGlass.ush'
original=path.read_bytes()
old=b'    return O;'
assert original.count(old)==1
position='position' in sys.argv
normal='normal' in sys.argv
patch=b'    O.DiffuseAlbedo = float3(.3,.3,.3);\n    O.TransmittanceColor = float3(.001,.001,.001);\n    O.F0 = float3(.04,.04,.04);\n    O.Roughness = .4;\n'
if position:patch+=b'    O.EmissiveColor = In.WorldPosition.z > 3.9 ? float3(8,0,0) : (In.WorldPosition.z < 2.5 ? float3(0,0,8) : float3(0,8,0));\n'
if normal:patch+=b'    O.DiffuseAlbedo = 0; O.EmissiveColor = (normalize(In.VertexNormal)*.5+.5)*100;\n'
edited=original.replace(old,patch+old)
try:
    offset=(ROOT/'Saved/Logs/CkPlugins.log').stat().st_size
    path.write_bytes(edited);wait_reload(offset)
    name='OpticalDepth-Display-'+('NormalDiagnostic' if normal else 'PositionDiagnostic' if position else 'FacesDiagnostic')
    result=submit('capture',subject='display',name=name+'.png',camera=[17,-27,13],target=[0,-1,2],fov=35,settle_frames=60,sky=0,intensities=[0,0,0] if normal else [9,5,8])
    (ROOT/('Saved/UsfMaterialGallery/'+name+'.json')).write_text(json.dumps(result,indent=2))
finally:
    if path.read_bytes()!=edited:raise RuntimeError('Concurrent depth shader change; preserve')
    offset=(ROOT/'Saved/Logs/CkPlugins.log').stat().st_size
    path.write_bytes(original);wait_reload(offset)
