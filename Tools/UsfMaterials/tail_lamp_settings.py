"""Owned optical lamp recipe. Native lens; separate opaque textured hardware."""
RESOURCE = 'Plugins/CkTests/Resources/CkUsf/TailLampV1'
ASSET = '/CkFoundation/CkUsf'
LOOKS = {
    'OpticalTailLampLens': dict(graph=6, source='OpticalTailLampLens',
        textures=[('NormalMap', 'LensNormal'), ('RoughnessMap', 'LensRoughness'), ('ThicknessMap', 'LensThickness')],
        vectors=[('TransmissionColor', (.94, .055, .018, 1))],
        scalars=[('UVScale', 1), ('UVRotation', 0), ('NormalStrength', 1), ('RoughnessScale', .25),
                 ('RoughnessBias', .035), ('Ior', 1.49), ('AbsorptionStrength', 1),
                 ('ReferenceThicknessCm', .25), ('ThicknessCm', .25), ('ThicknessVariation', .4), ('DistortionStrength', .02)])
}
for role, tint, metal, roughness, emission in [
        ('Reflector', (.94, .94, .94, 1), 1, .4, 0),
        ('Housing', (.045, .05, .06, 1), 0, 1, 0),
        ('Gasket', (.012, .014, .018, 1), 0, 1.3, 0),
        ('Fastener', (.5, .53, .57, 1), 1, .7, 0),
        ('LEDPackage', (.8, .76, .64, 1), .1, .7, 0),
        ('LED', (1, .06, .015, 1), 0, .35, 40)]:
    reflective = role in ['Reflector', 'Fastener']
    LOOKS['OpticalTailLamp' + role] = dict(graph=0, source='OpticalTailLampHardware',
        textures=[('BaseColorMap', 'HousingBaseColor'), ('NormalMap', 'ReflectorNormal' if reflective else 'HousingNormal'),
                  ('RoughnessMap', 'ReflectorRoughness' if reflective else 'HousingRoughness')],
        vectors=[('TintColor', tint), ('EmissionColor', (1, .006, .001, 1))],
        scalars=[('UVScale', 1), ('UVRotation', 0), ('NormalStrength', .08 if reflective else .2),
                 ('RoughnessScale', roughness), ('RoughnessBias', .04), ('MetalnessLevel', metal),
                 ('ColorMapInfluence', .3 if role == 'Housing' else 0), ('EmissionStrength', emission)])
