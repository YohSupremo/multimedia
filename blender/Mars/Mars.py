"""
Mars Cinematic Material + Tilt + Spin
======================================
Run AFTER mars_orbit_only.py.

RUN ORDER:
  1. mars_orbit_only.py   ← orbit hierarchy first
  2. THIS SCRIPT          ← Mars material + tilt + spin
  3. phobos_material.py
  4. deimos_material.py

Select your Mars sphere before running.
"""

import bpy
import os
import math

# ── UPDATE THIS PATH ──────────────────────────────────────────────────────────
TEXTURE_PATH = r"C:\Users\kelly\Downloads\Blender\textures\mars.jpg"
# ─────────────────────────────────────────────────────────────────────────────

FRAME_START        = 1
FRAME_END          = 500
AXIAL_TILT_DEGREES = 25.19   # Mars real axial tilt

# Real period ratio: Mars day = 24.62 hr, Phobos = 7.66 hr
# Matches MARS_SPIN_FRAMES in orbit script (46 * 24.62/7.66 = 148)
MARS_SPIN_FRAMES   = 148

SEGMENTS = 128
RINGS    = 64


def fix_mesh(obj):
    """Replace mesh with a high-res UV sphere. Does NOT touch rotation — bake loop owns that."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    loc   = obj.location.copy()
    scale = obj.scale.copy()
    # Intentionally NOT saving/restoring rotation — the bake loop sets all rotation keyframes.

    obj.modifiers.clear()

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete(type='VERT')
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments   = SEGMENTS,
        ring_count = RINGS,
        radius     = 1.0,
        location   = (0, 0, 0),
    )
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.faces_shade_smooth()
    bpy.ops.object.mode_set(mode='OBJECT')

    obj.location = loc
    obj.scale    = scale
    # rotation_euler intentionally left alone here

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"✅  Mesh replaced: UV Sphere {SEGMENTS}×{RINGS}, smooth shading applied.")


def set_linear_on_action(action):
    """Blender 5.1 compatible linear interpolation setter."""
    if action is None:
        return
    if hasattr(action, 'layers'):
        try:
            for layer in action.layers:
                for strip in layer.strips:
                    channelbag = None
                    if hasattr(strip, 'channelbags') and strip.channelbags:
                        channelbag = strip.channelbags[0]
                    if channelbag is None:
                        continue
                    for fc in channelbag.fcurves:
                        fc.extrapolation = 'LINEAR'
                        for kp in fc.keyframe_points:
                            kp.interpolation     = 'LINEAR'
                            kp.handle_left_type  = 'VECTOR'
                            kp.handle_right_type = 'VECTOR'
            return
        except Exception:
            pass
    if hasattr(action, 'fcurves'):
        for fc in action.fcurves:
            fc.extrapolation = 'LINEAR'
            for kp in fc.keyframe_points:
                kp.interpolation     = 'LINEAR'
                kp.handle_left_type  = 'VECTOR'
                kp.handle_right_type = 'VECTOR'


def build_mars_material(texture_path: str):
    obj = bpy.context.active_object
    if obj is None or obj.type != 'MESH':
        raise RuntimeError("Select your Mars sphere first, then run the script.")

    fix_mesh(obj)

    # ── MATERIAL ──────────────────────────────────────────────────────────────
    mat_name = "Mars_Cinematic"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    def N(bl_type, loc):
        n = nodes.new(bl_type)
        n.location = loc
        return n

    out  = N("ShaderNodeOutputMaterial",  ( 900,   0))
    bsdf = N("ShaderNodeBsdfPrincipled",  ( 500,   0))
    bsdf.inputs["Roughness"].default_value          = 0.88
    bsdf.inputs["Specular IOR Level"].default_value = 0.05
    bsdf.inputs["Sheen Weight"].default_value       = 0.08

    tex_coord = N("ShaderNodeTexCoord", (-900,   0))
    mapping   = N("ShaderNodeMapping",  (-700,   0))
    mapping.inputs["Scale"].default_value = (1, 1, 1)

    tex_color = N("ShaderNodeTexImage", (-450, 100))
    tex_color.label = "Mars Base Color"
    if os.path.exists(texture_path):
        img = bpy.data.images.load(texture_path, check_existing=True)
        tex_color.image = img
    else:
        print(f"⚠  Texture not found: {texture_path}")

    hue_sat = N("ShaderNodeHueSaturation", (-150, 100))
    hue_sat.inputs["Hue"].default_value        = 0.50
    hue_sat.inputs["Saturation"].default_value = 1.45
    hue_sat.inputs["Value"].default_value      = 1.05

    rgb_curves = N("ShaderNodeRGBCurve", (80, 100))
    c = rgb_curves.mapping.curves[3]
    c.points[0].location = (0.0,  0.0)
    c.points[1].location = (0.5,  0.52)
    c.points.new(0.85, 0.90)
    rgb_curves.mapping.update()

    sep_rgb  = N("ShaderNodeSeparateColor", (-450, -200))
    mix_bump = N("ShaderNodeMixRGB",        (-200, -200))
    mix_bump.blend_type = 'MIX'
    mix_bump.inputs["Fac"].default_value = 0.4

    bump = N("ShaderNodeBump", (80, -200))
    bump.inputs["Strength"].default_value = 0.55
    bump.inputs["Distance"].default_value = 0.05

    lum_math = N("ShaderNodeMath", (-200, -400))
    lum_math.operation = 'MULTIPLY'
    lum_math.inputs[1].default_value = 0.06

    emission   = N("ShaderNodeEmission",  (80, -400))
    emission.inputs["Color"].default_value = (1.0, 0.45, 0.15, 1.0)

    add_shader = N("ShaderNodeAddShader", (700, -150))

    links.new(tex_coord.outputs["UV"],      mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"],    tex_color.inputs["Vector"])
    links.new(mapping.outputs["Vector"],    sep_rgb.inputs["Color"])
    links.new(tex_color.outputs["Color"],   hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],     rgb_curves.inputs["Color"])
    links.new(rgb_curves.outputs["Color"],  bsdf.inputs["Base Color"])
    links.new(tex_color.outputs["Color"],   sep_rgb.inputs["Color"])
    links.new(sep_rgb.outputs["Red"],       mix_bump.inputs["Color1"])
    links.new(sep_rgb.outputs["Green"],     mix_bump.inputs["Color2"])
    links.new(mix_bump.outputs["Color"],    bump.inputs["Height"])
    links.new(bump.outputs["Normal"],       bsdf.inputs["Normal"])
    links.new(sep_rgb.outputs["Red"],       lum_math.inputs[0])
    links.new(lum_math.outputs["Value"],    emission.inputs["Strength"])
    links.new(bsdf.outputs["BSDF"],         add_shader.inputs[0])
    links.new(emission.outputs["Emission"], add_shader.inputs[1])
    links.new(add_shader.outputs["Shader"], out.inputs["Surface"])

    print("✅  Mars_Cinematic material applied!")

    # ── TILT + SPIN — baked per frame, safe after parenting ──────────────────
    bpy.context.scene.frame_start = FRAME_START
    bpy.context.scene.frame_end   = FRAME_END

    obj.animation_data_clear()
    obj.rotation_mode = 'XYZ'

    tilt_x = math.radians(AXIAL_TILT_DEGREES)

    for frame in range(FRAME_START, FRAME_END + 1):
        bpy.context.scene.frame_set(frame)          # set frame FIRST
        t      = (frame - FRAME_START) % MARS_SPIN_FRAMES
        spin_z = (t / MARS_SPIN_FRAMES) * math.tau
        obj.rotation_euler = (tilt_x, 0.0, spin_z)
        obj.keyframe_insert(data_path="rotation_euler")

    if obj.animation_data and obj.animation_data.action:
        set_linear_on_action(obj.animation_data.action)

    bpy.context.scene.frame_set(FRAME_START)

    print(f"✅  Tilt:  {AXIAL_TILT_DEGREES}° (X axis)")
    print(f"✅  Spin:  1 rotation per {MARS_SPIN_FRAMES} frames")
    print(f"✅  Baked: frames {FRAME_START}–{FRAME_END}")
    print("   💡 Tips: EEVEE 128 samples | HDRI space lighting | Sun lamp off to one side")


build_mars_material(TEXTURE_PATH)