"""Approved original RGB with full-area numerical native internal domains."""
ASSET='/CkFoundation/CkUsf'
TEXTURE_PREFIX=ASSET+'/Textures/Optical/OpalInternal/T_OpalInternal_'
LOOKS={'Opal':dict(name='OpticalOpalInternal',source='OpticalOpalInternal',graph=9,
    shading=0,blend=0,two_sided=False,directional_shading=False,adaptive_base_glints=False,
    textures=[('ColorMap','OpalColor'),('DomainMap','OpalDomains'),('DomainNormalMap','OpalDomainNormal'),
              ('PolishNormalMap','OpalPolishNormal'),('RoughnessMap','OpalRoughness')],
    vectors=[('MilkColor',(.25,.27,.24,1)),('CoatTransmission',(.995,.998,.999,1)),('BodyTransmission',(.4,.44,.48,1))],
    scalars=[('UVScale',1),('UVRotation',0),('ScatteringStrength',.35),('DomainNormalStrength',1),
        ('DomainRoughness',.12),('FlashReflectance',.30),('CoatRoughness',.025),('CoatNormalStrength',0),
        ('CoatIor',1.45),('CoatThicknessCm',.03),('CoatReferenceThicknessCm',.1),
        ('InternalReflectorThicknessCm',.01),('InternalReferenceThicknessCm',.01),
        ('BodyThicknessCm',4),('BodyReferenceThicknessCm',4),('RefractionStrength',1)])}
