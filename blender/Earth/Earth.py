import bpy
import math

EARTH_NAME    = "Earth"
EARTH_TEXTURE = r"C:\Users\kelly\Downloads\Blender\textures\earth.jpg"
CLOUD_TEXTURE = r"C:\Users\kelly\Downloads\Blender\textures\clouds.jpg"
NIGHT_TEXTURE = r"C:\Users\kelly\Downloads\Blender\textures\night.jpg"

ROTATION_DEGREES   = 360
FRAME_START        = 1
FRAME_END          = 300
AXIAL_TILT_DEGREES = 23.5

earth = bpy.data.objects.get(EARTH_NAME)
if not earth:
    print("ERROR: Object not found!")
else:
    bpy.context.view_layer.objects.active = earth
    bpy.ops.object.shade_smooth()
    # ---- SUBDIVISION ----
    has_subsurf = any(m.type == 'SUBSURF' for m in earth.modifiers)
    if not has_subsurf:
        subsurf = earth.modifiers.new(name="Subdivision", type='SUBSURF')
        subsurf.levels = 3
        subsurf.render_levels = 4
        print("Subdivision Surface added")
    # ---- UV MAP ----
    if not earth.data.uv_layers:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.sphere_project()
        bpy.ops.object.mode_set(mode='OBJECT')
        print("UV map created")
    # ---- MATERIAL ----
    if len(earth.data.materials) == 0:
        mat = bpy.data.materials.new(name="EarthMat")
        earth.data.materials.append(mat)
        print("Created new material")
    else:
        mat = earth.data.materials[0]
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    # ---- NODES ----
    output     = nodes.new("ShaderNodeOutputMaterial")
    add_shader = nodes.new("ShaderNodeAddShader")
    princip    = nodes.new("ShaderNodeBsdfPrincipled")
    mix        = nodes.new("ShaderNodeMixRGB")
    tex_earth  = nodes.new("ShaderNodeTexImage")
    tex_cloud  = nodes.new("ShaderNodeTexImage")
    tex_night  = nodes.new("ShaderNodeTexImage")
    emission   = nodes.new("ShaderNodeEmission")
    # ---- LOAD IMAGES ----
    tex_earth.image = bpy.data.images.load(EARTH_TEXTURE, check_existing=True)
    tex_cloud.image = bpy.data.images.load(CLOUD_TEXTURE, check_existing=True)
    tex_night.image = bpy.data.images.load(NIGHT_TEXTURE, check_existing=True)
    # ---- COLOR SPACE ----
    tex_earth.image.colorspace_settings.name = 'sRGB'
    tex_cloud.image.colorspace_settings.name = 'sRGB'
    tex_night.image.colorspace_settings.name = 'Non-Color'
    # ---- MATERIAL VALUES ----
    princip.inputs["Metallic"].default_value           = 0.0
    princip.inputs["Roughness"].default_value          = 0.75
    princip.inputs["IOR"].default_value                = 1.5
    princip.inputs["Alpha"].default_value              = 1.0
    princip.inputs["Specular IOR Level"].default_value = 0.05
    mix.blend_type                  = 'MIX'
    mix.use_clamp                   = True
    mix.inputs["Fac"].default_value = 0.10
    emission.inputs["Strength"].default_value = 0.5
    # ---- NODE POSITIONS ----
    tex_earth.location  = (-500,  200)
    tex_cloud.location  = (-500, -100)
    tex_night.location  = (-500, -400)
    mix.location        = (-200,  100)
    princip.location    = (100,   200)
    emission.location   = (100,  -200)
    add_shader.location = (450,     0)
    output.location     = (700,     0)
    # ---- LINKS ----
    links.new(tex_earth.outputs["Color"],   mix.inputs["Color1"])
    links.new(tex_cloud.outputs["Color"],   mix.inputs["Color2"])
    links.new(mix.outputs["Color"],         princip.inputs["Base Color"])
    links.new(tex_night.outputs["Color"],   emission.inputs["Color"])
    links.new(princip.outputs["BSDF"],      add_shader.inputs[0])
    links.new(emission.outputs["Emission"], add_shader.inputs[1])
    links.new(add_shader.outputs["Shader"], output.inputs["Surface"])
    print("✅ Earth material applied!")

    # ---- TILT + ROTATION ----
    bpy.context.scene.frame_start = FRAME_START
    bpy.context.scene.frame_end   = FRAME_END
    earth.animation_data_clear()

    earth.rotation_euler.x = math.radians(AXIAL_TILT_DEGREES)
    earth.rotation_euler.y = 0.0

    bpy.context.scene.frame_set(FRAME_START)
    earth.rotation_euler.z = 0.0
    earth.keyframe_insert(data_path="rotation_euler", index=2)

    bpy.context.scene.frame_set(FRAME_END)
    earth.rotation_euler.z = math.radians(ROTATION_DEGREES)
    earth.keyframe_insert(data_path="rotation_euler", index=2)

    # ---- LINEAR INTERPOLATION — Blender 5.1 compatible ----
    if earth.animation_data and earth.animation_data.action:
        action = earth.animation_data.action
        if hasattr(action, 'fcurves'):
            for fc in action.fcurves:
                if fc.data_path == "rotation_euler" and fc.array_index == 2:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'LINEAR'
        elif hasattr(action, 'layers') and action.layers:
            layer = action.layers[0]
            if layer.strips:
                strip = layer.strips[0]
                channelbag = None
                try:
                    channelbag = strip.channelbags[0] if hasattr(strip, 'channelbags') and strip.channelbags else None
                except Exception:
                    pass
                if channelbag:
                    for fc in channelbag.fcurves:
                        if fc.data_path == "rotation_euler" and fc.array_index == 2:
                            for kp in fc.keyframe_points:
                                kp.interpolation = 'LINEAR'

    bpy.context.scene.frame_set(FRAME_START)
    print(f"✅ Tilt applied: {AXIAL_TILT_DEGREES}°")
    print(f"✅ Rotation applied: {ROTATION_DEGREES}° over {FRAME_END} frames")
    print("👉 Press Z → Material Preview or Rendered to see result.")