"""One decisive hero lookdev scene, preserving the rejected prototype assets."""
import math
import random
import unreal


def apply(scene):
    from prepare_amber_hero import prepare
    prepared = prepare()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for role in ['Backing', 'Botanical', 'Stem', 'Seed']:
        scene['meshes'][role].set_actor_hidden_in_game(True)
        scene['visible'][role] = False
    component = scene['meshes']['Body'].static_mesh_component
    component.set_static_mesh(unreal.load_asset(prepared['meshes']['Body']))
    # Strong native refraction remains an isolated diagnostic: actual captures
    # self-refract in this renderer. Keep the reviewed PNO optical body as default.
    body_master = scene['materials']['Body'][0]
    body = unreal.MaterialLibrary.create_dynamic_material_instance(scene['world'], body_master)
    component.set_material(component.get_material_index('Body'), body)
    scene['materials']['Body'] = (body_master, body)
    scene['materials']['Stem'][1].set_vector_parameter_value('TintColor', unreal.LinearColor(.10, .055, .02, 1))
    for key, value in {'ReferenceThicknessCm': 1.0, 'ThicknessCm': 3.8, 'EdgeThicknessCm': .3,
                        'AbsorptionStrength': 1, 'RoughnessScale': .2, 'RoughnessBias': .025,
                        'NormalStrength': .4, 'DistortionStrength': .008}.items():
        body.set_scalar_parameter_value(key, value)
    body.set_vector_parameter_value('TransmissionColor', unreal.LinearColor(.985, .72, .31, 1))
    def spawn(role, material):
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
        actor.set_actor_label('AmberHero_' + role)
        component = actor.static_mesh_component
        component.set_static_mesh(unreal.load_asset(prepared['meshes'][role]))
        component.set_material(component.get_material_index(role), material)
        return actor
    leaf_master = unreal.load_asset(prepared['leaf'])
    leaf = unreal.MaterialLibrary.create_dynamic_material_instance(scene['world'], leaf_master)
    leaf.set_vector_parameter_value('TintColor', unreal.LinearColor(.65, .65, .65, 1))
    leaf.set_scalar_parameter_value('TransmissionStrength', .45)
    leaf_actor = spawn('Leaf', leaf)
    debris_actor = spawn('Debris', scene['materials']['Stem'][1])
    debris_actor.static_mesh_component.set_editor_property('cast_shadow', False)
    bubble_master = unreal.load_asset(prepared['bubble'])
    bubble = unreal.MaterialLibrary.create_dynamic_material_instance(scene['world'], bubble_master)
    for material in [leaf_master, bubble_master]:
        unreal.MaterialEditingLibrary.get_statistics(material)
    for parameter in ['BaseColorMap', 'NormalMap', 'RoughnessMap', 'OpacityMap']:
        texture = leaf.get_texture_parameter_value(parameter)
        texture.set_force_mip_levels_to_be_resident(120, 0)
        scene['textures'][texture.get_path_name()] = texture
    generator = random.Random(84193)
    bubbles = [(.8, -1.8, 5.7, .24), (.65, 2.4, 3.0, .31), (.9, .3, 6.0, .18), (-.65, -2.7, 3.8, .16)]
    for index in range(55):
        for _ in range(100):
            x, y, z = generator.uniform(-1.15, 1.15), generator.uniform(-4.5, 4.5), generator.uniform(.9, 7.2)
            if (x / 1.8) ** 2 + (y / 5.0) ** 2 + ((z - 4) / 3.6) ** 2 < .8:
                bubbles.append((x, y, z, generator.uniform(.025, .085)))
                break
    for x, y, z, radius in bubbles:
        actor = spawn('BubbleSource', bubble)
        actor.set_actor_location(unreal.Vector(x, y, z), False, False)
        actor.set_actor_scale3d(unreal.Vector(radius, radius, radius))
        actor.static_mesh_component.set_editor_property('cast_shadow', False)
        actor.static_mesh_component.set_editor_property('translucency_sort_priority', -1)
    for actor in actors.get_all_level_actors():
        if not isinstance(actor, unreal.StaticMeshActor):
            continue
        mesh = actor.static_mesh_component.static_mesh
        if mesh and mesh.get_path_name().startswith('/Engine/BasicShapes/Cylinder'):
            actor.set_actor_hidden_in_game(True)
        if mesh and mesh.get_path_name().startswith('/Engine/BasicShapes/Plane'):
            actor.set_actor_location(unreal.Vector(0, 0, .08), False, False)
    scene['sky'].light_component.set_intensity(.8)
    for actor, position, intensity, length, radius, rotation in zip(scene['lights'],
            [(10, -10, 16), (8, 13, 11), (-7, -3, 11)], [7, 3, 10], [10, 7, 4], [.9, .45, 1.2],
            [(70, 25, 0), (65, -30, 0), (40, 45, 0)]):
        actor.set_actor_location(unreal.Vector(*position), False, False)
        actor.set_actor_rotation(unreal.Rotator(*rotation), False)
        light = actor.point_light_component
        light.set_intensity(intensity)
        light.set_editor_property('source_length', length)
        light.set_source_radius(radius)
    scene['capture'].set_actor_location(unreal.Vector(24, -11, 17), False, False)
    scene['capture'].set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(scene['capture'].get_actor_location(), unreal.Vector(0, 0, 3.8)), False)
    settings = scene['component'].get_editor_property('post_process_settings')
    settings.set_editor_property('auto_exposure_min_brightness', 4.2)
    settings.set_editor_property('auto_exposure_max_brightness', 4.2)
    settings.set_editor_property('override_lumen_front_layer_translucency_reflections', True)
    settings.set_editor_property('lumen_front_layer_translucency_reflections', True)
    scene['component'].set_editor_property('post_process_settings', settings)
    scene['hero'] = dict(leaf=leaf, bubble=bubble, leaf_actor=leaf_actor,
                         debris_actor=debris_actor, assets=prepared, bubble_count=len(bubbles))
    return dict(ready=True, bubbles=len(bubbles), assets=prepared)
