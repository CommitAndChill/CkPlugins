"""Clear polish over sparse texture-authored mineral facets."""
from copy import deepcopy
from opal_polish_settings import ASSET, LOOKS as PREVIOUS

LOOKS={'Opal':deepcopy(PREVIOUS['Opal'])}
TEXTURE_PREFIX=ASSET+'/Textures/Optical/OpalFire/T_OpalFire_'
LOOKS['Opal'].update(name='OpticalOpalFire',source='OpticalOpalFire')
LOOKS['Opal']['vectors']=[('MilkColor',(.18,.205,.20,1))]
overrides=dict(MilkAmount=0,FlashCoverage=1,FlashStrength=1,
    DomainNormalStrength=1,DomainRoughness=.065,CoatRoughness=.035,
    InternalDepthUV=.009,InternalLayerMix=.2,DetailFilterMip=0,
    FlashReflectance=.22,BodyColorMix=.10)
LOOKS['Opal']['scalars']=[(key,overrides.get(key,value)) for key,value in LOOKS['Opal']['scalars']]
