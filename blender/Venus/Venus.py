"""
Venus — Complete Setup (Mesh + Material + Rotation)
====================================================
Fixed: reduced brightness, emission, saturation
"""

import bpy
import os
import math

OBJECT_NAME  = "Venus"
TEXTURE_PATH = r"C:\Users\kelly\Downloads\Blender\textures\venus.jpg"

SEGMENTS = 128
RINGS    = 64

ROTATION_AXIS    = 'Z'
ROTATION_DEGREES = -360              # ← changed: retrograde (clockwise)
FRAME_START      = 1
FRAME_END        = 300
AXIAL_TILT_DEGREES = 177.4           # ← changed: Venus real tilt


def fix_mesh(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    loc, scale = obj.location.copy(), obj.scale.copy()
    obj.modifiers.clear()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete(type='VERT')
    bpy.ops.mesh.primitive_uv_sphere_add(segments=SEGMENTS, ring_count=RINGS, radius=1.0, location=(0,0,0))
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.faces_shade_smooth()
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.location, obj.scale = loc, scale
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    print("✅  Mesh ready.")


def set_linear_interpolation(action, axis_idx):
    data_path = "rotation_euler"
    if hasattr(action, 'fcurves'):
        for fc in action.fcurves:
            if fc.data_path == data_path and fc.array_index == axis_idx:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
        return
    if not hasattr(action, 'layers') or not action.layers:
        return
    layer = action.layers[0]
    if not layer.strips:
        return
    strip = layer.strips[0]
    channelbag = None
    try:
        channelbag = strip.channelbags[0] if hasattr(strip, 'channelbags') and strip.channelbags else None
    except Exception:
        pass
    if channelbag is None:
        return
    for fc in channelbag.fcurves:
        if fc.data_path == data_path and fc.array_index == axis_idx:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


def add_rotation_and_tilt(obj):
    axis_map = {'X': 0, 'Y': 1, 'Z': 2}
    axis_idx = axis_map.get(ROTATION_AXIS.upper(), 2)
    bpy.context.scene.frame_start = FRAME_START
    bpy.context.scene.frame_end   = FRAME_END
    obj.animation_data_clear()
    obj.rotation_euler.x = math.radians(AXIAL_TILT_DEGREES)
    obj.rotation_euler.y = 0.0
    bpy.context.scene.frame_set(FRAME_START)
    obj.rotation_euler[axis_idx] = 0.0
    obj.keyframe_insert(data_path="rotation_euler", index=axis_idx)
    bpy.context.scene.frame_set(FRAME_END)
    obj.rotation_euler[axis_idx] = math.radians(ROTATION_DEGREES)
    obj.keyframe_insert(data_path="rotation_euler", index=axis_idx)
    if obj.animation_data and obj.animation_data.action:
        set_linear_interpolation(obj.animation_data.action, axis_idx)
    bpy.context.scene.frame_set(FRAME_START)
    print("✅  Rotation + tilt applied.")


def build_material(obj, texture_path):
    if obj.data.materials:
        mat = obj.data.materials[0] or bpy.data.materials.new("Venus_Mat")
        if obj.data.materials[0] is None:
            obj.data.materials[0] = mat
    else:
        mat = bpy.data.materials.new("Venus_Mat")
        obj.data.materials.append(mat)

    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    def N(t, loc, name=None):
        node = nodes.new(t)
        node.location = loc
        if name:
            node.name = node.label = name
        return node

    # Load texture
    image = None
    if os.path.exists(texture_path):
        image = bpy.data.images.load(texture_path, check_existing=True)
        print(f"   Texture loaded: {texture_path}")
    else:
        print(f"   ⚠  Texture not found: {texture_path}")

    # ── Nodes ─────────────────────────────────────────────────────────────────

    tex_coord = N("ShaderNodeTexCoord",  (-1100, 300), "TexCoord")
    mapping   = N("ShaderNodeMapping",   (-900,  300), "Mapping")

    tex = N("ShaderNodeTexImage", (-680, 300), "TexImage")
    if image:
        tex.image = image

    # HueSat — darkened vs reference to fix brightness
    hue_sat = N("ShaderNodeHueSaturation", (-400, 300), "HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.52   # keep orange hue
    hue_sat.inputs["Saturation"].default_value = 1.10   # was 1.35 — reduced to stop bleaching
    hue_sat.inputs["Value"].default_value      = 0.72   # was 0.90 — darker overall
    hue_sat.inputs["Factor"].default_value     = 1.0

    # RGB Curves — crush shadows slightly, protect highlights
    curves = N("ShaderNodeRGBCurve", (-160, 300), "RGBCurves")
    c = curves.mapping.curves[3]
    c.points[0].location = (0.0, 0.0)
    c.points[1].location = (1.0, 1.0)
    c.points.new(0.15, 0.08)   # shadow crush — stops darks going grey
    c.points.new(0.80, 0.78)   # gentle highlight rolloff
    curves.mapping.update()

    # Separate Color → drives Mix nodes for bump detail
    sep_col = N("ShaderNodeSeparateColor", (-400, 0), "SeparateColor")

    # Mix1 — warm tint blend
    mix1 = N("ShaderNodeMixRGB", (-160, 0), "Mix1")
    mix1.blend_type = 'MIX'
    mix1.inputs["Fac"].default_value    = 0.25
    mix1.inputs["Color1"].default_value = (0.5, 0.5, 0.5, 1.0)
    mix1.inputs["Color2"].default_value = (1.0, 0.72, 0.35, 1.0)

    # Mix2 — bump height source
    mix2 = N("ShaderNodeMixRGB", (-160, -200), "Mix2")
    mix2.blend_type = 'MIX'
    mix2.inputs["Fac"].default_value    = 0.45
    mix2.inputs["Color1"].default_value = (0.5, 0.5, 0.5, 1.0)
    mix2.inputs["Color2"].default_value = (0.5, 0.5, 0.5, 1.0)

    # Principled BSDF
    bsdf = N("ShaderNodeBsdfPrincipled", (200, 300), "PrincipledBSDF")
    bsdf.inputs["Roughness"].default_value          = 0.80
    bsdf.inputs["Metallic"].default_value           = 0.0
    bsdf.inputs["IOR"].default_value                = 1.5
    bsdf.inputs["Alpha"].default_value              = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.08
    bsdf.inputs["Sheen Weight"].default_value       = 0.05
    bsdf.inputs["Sheen Roughness"].default_value    = 0.5

    # Bump
    bump = N("ShaderNodeBump", (0, -50), "Bump")
    bump.inputs["Strength"].default_value = 0.65
    bump.inputs["Distance"].default_value = 0.06

    # Fresnel — rim glow
    fresnel = N("ShaderNodeFresnel", (0, -350), "Fresnel")
    fresnel.inputs["IOR"].default_value = 2.20

    # Math1 — scale fresnel (was 1.8, reduced to soften rim)
    math1 = N("ShaderNodeMath", (200, -350), "Math_FresnelMult")
    math1.operation = 'MULTIPLY'
    math1.inputs[1].default_value = 0.80   # was 1.80 — rim glow much softer now

    # Emission1 — warm orange rim (drastically reduced)
    emit1 = N("ShaderNodeEmission", (400, -200), "Emission1")
    emit1.inputs["Color"].default_value    = (1.0, 0.65, 0.15, 1.0)
    emit1.inputs["Strength"].default_value = 0.25   # was 1.20 — main brightness culprit

    # Math2 — scale emit2
    math2 = N("ShaderNodeMath", (400, -400), "Math_EmitScale")
    math2.operation = 'MULTIPLY'
    math2.inputs[1].default_value = 0.02   # was 0.04 — halved

    # Emission2 — deeper orange (reduced)
    emit2 = N("ShaderNodeEmission", (600, -400), "Emission2")
    emit2.inputs["Color"].default_value    = (1.0, 0.50, 0.10, 1.0)
    emit2.inputs["Strength"].default_value = 0.15   # was 0.50

    # Add Shader 1: BSDF + Emission1
    add1 = N("ShaderNodeAddShader", (650, 200), "AddShader1")

    # Add Shader 2: Add1 + Emission2
    add2 = N("ShaderNodeAddShader", (850, 100), "AddShader2")

    # Output
    out = N("ShaderNodeOutputMaterial", (1050, 100), "Output")

    # ── Wiring ────────────────────────────────────────────────────────────────

    links.new(tex_coord.outputs["UV"],      mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"],    tex.inputs["Vector"])
    links.new(tex.outputs["Color"],         hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],     curves.inputs["Color"])
    links.new(curves.outputs["Color"],      bsdf.inputs["Base Color"])

    links.new(tex.outputs["Color"],         sep_col.inputs["Color"])
    links.new(sep_col.outputs["Red"],       mix1.inputs["Color1"])
    links.new(mix1.outputs["Color"],        mix2.inputs["Color1"])
    links.new(mix2.outputs["Color"],        bump.inputs["Height"])
    links.new(bump.outputs["Normal"],       bsdf.inputs["Normal"])

    links.new(fresnel.outputs["Fac"],       math1.inputs[0])
    links.new(math1.outputs["Value"],       emit1.inputs["Strength"])
    links.new(math1.outputs["Value"],       math2.inputs[0])
    links.new(math2.outputs["Value"],       emit2.inputs["Strength"])

    links.new(bsdf.outputs["BSDF"],         add1.inputs[0])
    links.new(emit1.outputs["Emission"],    add1.inputs[1])
    links.new(add1.outputs["Shader"],       add2.inputs[0])
    links.new(emit2.outputs["Emission"],    add2.inputs[1])
    links.new(add2.outputs["Shader"],       out.inputs["Surface"])

    print("✅  Material applied — brightness fixed.")


def run():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    obj = bpy.data.objects.get(OBJECT_NAME)
    if obj is None:
        obj = bpy.context.active_object
        if obj is None or obj.type != 'MESH':
            raise RuntimeError("Select your Venus sphere and run again.")
        print(f"⚠  Using active object '{obj.name}'.")

    print("🌕 Venus setup starting...")
    fix_mesh(obj)
    add_rotation_and_tilt(obj)
    build_material(obj, TEXTURE_PATH)

    print()
    print("✅  Venus complete!")
    print("   Brightness fixes applied:")
    print("   • Saturation 1.10  (was 1.35)")
    print("   • Value 0.72       (was 0.90)")
    print("   • Emission1 ×0.25  (was ×1.20)")
    print("   • Emission2 ×0.15  (was ×0.50)")
    print("   • Fresnel mult 0.80 (was 1.80)")
    print("   • Math2 scale 0.02  (was 0.04)")
    print("   • Retrograde spin: -360°")
    print("   • Axial tilt: 177.4°")


run()