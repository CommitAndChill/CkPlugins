"""Single-mesh native transmitting opal; source maps retain their original provenance."""
ASSET = '/CkFoundation/CkUsf'
TEXTURE_PREFIX = ASSET+'/Textures/Optical/OpalLayeredFire/T_OpalLayeredFire_'
LOOKS = {
    'Opal': dict(name='OpticalOpalLayeredFire', source='OpticalOpalLayered', graph=8,
        shading=0, blend=0, two_sided=False, directional_shading=False,
        adaptive_base_glints=False,
        textures=[('ColorMap','OpalColor'),('DomainMap','OpalDomains'),
            ('DomainNormalMap','OpalDomainNormal'),('PolishNormalMap','OpalPolishNormal'),
            ('RoughnessMap','OpalRoughness')],
        vectors=[('MilkColor',(.48,.50,.46,1)),
            ('CoatTransmission',(.995,.998,.999,1)),
            ('BodyTransmission',(.78,.82,.84,1))],
        scalars=[('UVScale',1),('UVRotation',0),('ScatteringStrength',.45),
            ('InternalDepthUV',.012),('InternalLayerMix',0),
            ('DomainNormalStrength',1),('DomainRoughness',.12),
            ('FlashReflectance',.30),('FlashStrength',1),('FlashCoverage',1),
            ('CoatRoughness',.025),('CoatNormalStrength',0),('CoatIor',1.45),
            ('CoatThicknessCm',.03),('CoatReferenceThicknessCm',.1),
            ('BodyThicknessCm',4),('BodyReferenceThicknessCm',4),
            ('RefractionStrength',1)])
}
