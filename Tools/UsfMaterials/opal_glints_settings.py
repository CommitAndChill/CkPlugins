"""Native lower-layer glints beneath a smooth clear polish; V2 maps reused read-only."""
ASSET = '/CkFoundation/CkUsf'
TEXTURE_PREFIX = ASSET+'/Textures/Optical/OpalPolish/T_OpalPolish_'
LOOKS = {'Opal': dict(
    name='OpticalOpalGlints', source='OpticalOpalGlints', graph=4,
    shading=0, blend=0, two_sided=False, directional_shading=False,
    textures=[('ColorMap','OpalColor'), ('DomainMap','OpalDomains'),
              ('DomainNormalMap','OpalDomainNormal'), ('PolishNormalMap','OpalPolishNormal'),
              ('RoughnessMap','OpalRoughness')],
    vectors=[('MilkColor',(.20,.225,.235,1))],
    scalars=[('UVScale',1), ('UVRotation',0), ('BodyColorMix',.25),
             ('DetailFilterMip',0), ('InternalDepthUV',.008), ('InternalLayerMix',.18),
             ('DomainNormalStrength',0), ('DomainRoughness',.3),
             ('FlashReflectance',.4), ('FlashStrength',1), ('FlashCoverage',1),
             ('WavelengthShift',0), ('CoatRoughness',.035), ('CoatNormalStrength',0),
             ('LayerThicknessCm',.06), ('GlintDensity',.6), ('GlintUVScale',1)]
)}
