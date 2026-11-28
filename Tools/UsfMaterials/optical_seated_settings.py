"""Seated display refinement; preserve the prior depth study and opal."""
from copy import deepcopy
from optical_depth_settings import ASSET, LOOKS as PREVIOUS
LOOKS=deepcopy(PREVIOUS)
glass=LOOKS['GlassCover']
glass.update(name='OpticalSeatedGlass',source='OpticalSeatedGlass')
glass['vectors']=[('TransmissionColor',(.997,.999,.998,1)),('GlassFaceNormalWS',(0,0,1,1))]
changes={'CoatingStrength':.2,'CoatingThicknessNm':310,'CoatingVariationNm':90,'EdgePathCm':7,'NormalStrength':.04}
glass['scalars']=[(key,changes.get(key,value)) for key,value in glass['scalars']]+[
    ('BevelFilmIor',2.2),('BevelFilmThicknessNm',310),('BevelFilmVariationNm',90),('BevelFilmStrength',1)]
for role,tint,roughness,bias,anisotropy in [
        ('Housing',(.72,.74,.76,1),.65,.22,.5),('MetalTrim',(.70,.72,.74,1),.55,.18,.45)]:
    recipe=LOOKS[role]
    recipe.update(name='OpticalSeated'+role,source='OpticalSeatedAluminum',vectors=[('TintColor',tint)])
    changes={'RoughnessScale':roughness,'RoughnessBias':bias,'Anisotropy':anisotropy,'NormalStrength':.12}
    recipe['scalars']=[(key,changes.get(key,value)) for key,value in recipe['scalars']]
