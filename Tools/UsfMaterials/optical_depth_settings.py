"""Additive thick-glass and buried-domain opal refinement; V1 stays reproducible."""
from copy import deepcopy
from optical_pair_settings import ASSET, LOOKS as PREVIOUS
LOOKS=deepcopy(PREVIOUS)
for role in LOOKS:LOOKS[role]['name']='OpticalDepth'+role
opal=LOOKS['Opal'];opal.update(name='OpticalOpalDepth',source='OpticalOpalDepth')
opal['vectors']=[('MilkColor',(.18,.23,.25,1))]
overrides={'MilkAmount':.65,'FlashCoverage':1.6,'DomainRoughness':.13,'DomainNormalStrength':.075,'LayerThicknessCm':.07}
opal['scalars']=[(key,overrides.get(key,value)) for key,value in opal['scalars']]+[('InternalDepthUV',.016),('InternalLayerMix',.25)]
glass=LOOKS['GlassCover'];glass.update(name='OpticalDepthGlass',source='OpticalDepthGlass')
glass['vectors']=[('TransmissionColor',(.985,.994,.998,1)),('GlassFaceNormalWS',(0,0,1,1))]
overrides={'GlassThicknessCm':1.8,'CoatingStrength':.8,'CoatingThicknessNm':265,'PolishRoughness':.025}
glass['scalars']=[(key,overrides.get(key,value)) for key,value in glass['scalars']]+[('EdgePathCm',6)]
panel=LOOKS['Panel'];panel['scalars']=[(key,32 if key=='EmissionStrength' else value) for key,value in panel['scalars']]
for role,tint,rough,anisotropy in [('Housing',(.46,.50,.55,1),.45,.65),('MetalTrim',(.62,.66,.7,1),.3,.45)]:
    LOOKS[role].update(source='OpticalDepthHardware',graph=0,directional_shading=True,vectors=[('TintColor',tint)],
        scalars=[('UVScale',1),('UVRotation',0),('NormalStrength',.3),('RoughnessScale',rough),('RoughnessBias',.11),('Anisotropy',anisotropy)])
INITIAL_LOOKS=deepcopy(LOOKS)
for role,changes in [('Panel',{'EmissionStrength':130}),('GlassCover',{'EdgePathCm':9}),('Opal',{'WavelengthShift':.22})]:
    LOOKS[role]['scalars']=[(key,changes.get(key,value)) for key,value in LOOKS[role]['scalars']]
