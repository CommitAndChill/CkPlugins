"""Additive opal polish with original V2 artwork; previous looks stay unchanged."""
from copy import deepcopy
from optical_depth_settings import ASSET, LOOKS as PREVIOUS

LOOKS={'Opal':deepcopy(PREVIOUS['Opal'])}
TEXTURE_PREFIX=ASSET+'/Textures/Optical/OpalPolish/T_OpalPolish_'
opal=LOOKS['Opal']
opal.update(name='OpticalOpalPolishV2',source='OpticalOpalPolish')
opal['vectors']=[('MilkColor',(.28,.30,.27,1))]
overrides=dict(UVScale=1,MilkAmount=.6,FlashCoverage=1.15,FlashStrength=1,
    DomainNormalStrength=1,DomainRoughness=.25,WavelengthShift=.12,
    CoatRoughness=.035,CoatNormalStrength=0,LayerThicknessCm=.06,
    InternalDepthUV=.012,InternalLayerMix=.2)
opal['scalars']=[(key,overrides.get(key,value)) for key,value in opal['scalars']]+[
    ('DetailFilterMip',1.4),('FlashReflectance',.22),('BodyColorMix',.7)]
