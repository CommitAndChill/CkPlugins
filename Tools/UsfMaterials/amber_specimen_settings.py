"""Owned specimen recipes. Material inputs and sampling live in the .ush sources."""
RESOURCE = 'Plugins/CkTests/Resources/CkUsf/AmberSpecimenV1'
ASSET = '/CkFoundation/CkUsf'
LOOKS = {
    'Body': dict(name='OpticalAmberBody', graph=6, source='AmberSpecimen',
        textures=[('NormalMap', 'AmberNormal'), ('RoughnessMap', 'AmberRoughness'),
                  ('ThicknessMap', 'AmberThickness'), ('TintMap', 'AmberTint')],
        vectors=[('TransmissionColor', (.97, .70, .32, 1))],
        scalars=[('UVScale', 1), ('UVRotation', 0), ('NormalStrength', 1),
                 ('RoughnessScale', .35), ('RoughnessBias', .035), ('Ior', 1.54),
                 ('AbsorptionStrength', 1), ('ReferenceThicknessCm', .8), ('ThicknessCm', 2.6),
                 ('EdgeThicknessCm', .45), ('TintVariation', .8), ('DistortionStrength', .008)])}
for role, tint, roughness, bias, normal in [
        ('Botanical', (1, 1, 1, 1), 1, .04, .65),
        ('Seed', (1.6, 1.3, .8, 1), 1, .06, .3),
        ('Stem', (.4, .27, .12, 1), 1, .08, .4),
        ('Backing', (.62, .58, .46, 1), 2, .4, .1)]:
    backing = role == 'Backing'
    LOOKS[role] = dict(name='OpticalAmber' + role, graph=0, source='AmberInclusion',
        textures=[('BaseColorMap', 'AmberTint' if backing else 'BotanicalBaseColor'),
                  ('NormalMap', 'AmberNormal' if backing else 'BotanicalNormal'),
                  ('RoughnessMap', 'AmberRoughness' if backing else 'BotanicalRoughness')],
        vectors=[('TintColor', tint)],
        scalars=[('UVScale', 1), ('UVRotation', 0), ('NormalStrength', normal),
                 ('RoughnessScale', roughness), ('RoughnessBias', bias)])
