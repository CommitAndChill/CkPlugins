"""Original opal and coated instrument display; additive Adaptive showcase."""
ASSET='/CkFoundation/CkUsf'
RESOURCE='Plugins/CkTests/Resources/CkUsf/OpticalPairV1'
LOOKS={
 'Opal':dict(name='OpticalOpal',source='OpticalOpal',graph=4,
    textures=[('ColorMap','OpalColor'),('DomainMap','OpalDomains'),('DomainNormalMap','OpalDomainNormal'),('PolishNormalMap','OpalPolishNormal'),('RoughnessMap','OpalRoughness')],
    vectors=[('MilkColor',(.38,.43,.44,1))],
    scalars=[('UVScale',1),('UVRotation',0),('MilkAmount',.85),('FlashCoverage',1.15),('FlashStrength',1),('DomainNormalStrength',.035),('DomainRoughness',.2),('WavelengthShift',0),('CoatRoughness',.055),('CoatNormalStrength',0),('LayerThicknessCm',.04)]),
 'GlassCover':dict(name='OpticalCoatedGlass',source='OpticalCoatedGlass',graph=6,
    textures=[('NormalMap','GlassFinishNormal'),('RoughnessMap','GlassFinishRoughness'),('CoatingMap','GlassCoating')],
    vectors=[('TransmissionColor',(.985,.994,.998,1))],
    scalars=[('UVScale',1),('UVRotation',0),('NormalStrength',.08),('PolishRoughness',.025),('GlassIor',1.52),('CoatingIor',1.7),('CoatingThicknessNm',210),('CoatingVariationNm',160),('CoatingStrength',.4),('ReferenceThicknessCm',.33),('GlassThicknessCm',.33)]),
 'Panel':dict(name='OpticalDisplayPanel',source='OpticalDisplayPanel',graph=0,
    textures=[('BaseColorMap','DisplayBaseColor'),('NormalMap','DisplayNormal'),('RoughnessMap','DisplayRoughness'),('EmissionMap','DisplayEmission')],
    vectors=[('TintColor',(1,1,1,1)),('EmissionColor',(1,1,1,1))],
    scalars=[('UVScale',1),('UVRotation',0),('NormalStrength',.25),('RoughnessScale',1),('RoughnessBias',.05),('EmissionStrength',45)])}
for role,tint,metal,rough in [('Housing',(.08,.10,.12,1),.65,.7),('MetalTrim',(.52,.57,.63,1),1,.45)]:
 LOOKS[role]=dict(name='OpticalPair'+role,source='OpticalTailLampHardware',graph=0,
    textures=[('BaseColorMap','DisplayBaseColor'),('NormalMap','DisplayNormal'),('RoughnessMap','DisplayRoughness')],
    vectors=[('TintColor',tint),('EmissionColor',(0,0,0,1))],
    scalars=[('UVScale',1),('UVRotation',0),('NormalStrength',.3),('RoughnessScale',rough),('RoughnessBias',.1),('MetalnessLevel',metal),('ColorMapInfluence',.1),('EmissionStrength',0)])
for recipe in LOOKS.values():recipe.update(shading=0,blend=0,two_sided=False)
