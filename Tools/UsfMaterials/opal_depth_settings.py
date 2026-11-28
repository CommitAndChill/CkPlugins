"""Geometric opal depth study: distinct clear exterior and recessed mineral core."""
ASSET = '/CkFoundation/CkUsf'
TEXTURE_PREFIX = ASSET+'/Textures/Optical/OpalPolish/T_OpalPolish_'
LOOKS = {
    'Core': dict(name='OpticalOpalCore',source='OpticalOpalCore',graph=4,
        shading=0,blend=0,two_sided=False,directional_shading=False,adaptive_base_glints=True,
        textures=[('ColorMap','OpalColor'),('DomainMap','OpalDomains'),
            ('DomainNormalMap','OpalDomainNormal'),('PolishNormalMap','OpalPolishNormal'),
            ('RoughnessMap','OpalRoughness')],
        vectors=[('MilkColor',(.06,.08,.10,1))],
        scalars=[('UVScale',1),('UVRotation',0),('BodyColorMix',.04),
            ('DetailFilterMip',0),('InternalDepthUV',.006),('InternalLayerMix',.16),
            ('DomainOrientationStrength',1),('DomainNormalStrength',0),('DomainRoughness',.38),
            ('FlashReflectance',.4),('FlashStrength',1),('FlashCoverage',1),
            ('WavelengthShift',0),('WavelengthMinNm',500),('WavelengthMaxNm',780),
            ('SpectralBandwidthNm',30),('CoatRoughness',.3),('CoatNormalStrength',0),
            ('LayerThicknessCm',.12),('GlintDensity',1),('GlintUVScale',8)]),
    'Shell': dict(name='OpticalOpalShell',source='OpticalOpalShell',graph=6,
        shading=0,blend=0,two_sided=False,directional_shading=False,adaptive_base_glints=False,
        textures=[('NormalMap','OpalPolishNormal'),('RoughnessMap','OpalRoughness')],
        vectors=[('TransmissionColor',(.995,.997,.999,1))],
        scalars=[('UVScale',1),('UVRotation',0),('NormalStrength',0),
            ('PolishRoughness',.025),('GlassIor',1.45),('ReferenceThicknessCm',.3),
            ('ShellThicknessCm',.3),('RefractionStrength',1)])
}

FIRE_LOOK = dict(name='OpticalOpalFireLayer',source='OpticalOpalFireLayer',graph=6,
    shading=0,blend=0,two_sided=False,directional_shading=False,adaptive_base_glints=False,
    textures=[('ColorMap','OpalColor'),('DomainMap','OpalDomains'),
        ('DomainNormalMap','OpalDomainNormal'),('RoughnessMap','OpalRoughness')],
    vectors=[('ColorTint',(1,1,1,1)),('UVOffset',(.025,-.018,0,1))],
    scalars=[('UVScale',1),('UVRotation',0),('OrientationStrength',1),
        ('FlashStrength',1),('FlashCoverage',1),('FlashReflectance',.20),
        ('DomainRoughness',.22),('AngularPeak',.88),('AngularWidth',.1),
        ('Transmission',.999),('ReferenceThicknessCm',.1),('LayerThicknessCm',.02)])
