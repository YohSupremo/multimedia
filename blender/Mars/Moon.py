"""
Moon Cinematic Material + Tilt + Spin — MERGED
================================================
Run AFTER orbit_only.py (which parents Moon to its Spin Empty).

RUN ORDER:
  1. orbit_only.py        ← orbit hierarchy first
  2. earth_material.py    ← Earth tilt + spin
  3. THIS SCRIPT          ← Moon material + tilt + spin in local space

Select your Moon sphere before running.
"""

import bpy
import os
import math

# ── UPDATE THIS PATH ──────────────────────────────────────────────────────────
TEXTURE_PATH = r"C:\Users\kelly\Downloads\Blender\textures\moon.jpg"
# ─────────────────────────────────────────────────────────────────────────────

FRAME_START        = 1
FRAME_END          = 300
AXIAL_TILT_DEGREES = 6.68    # Moon's real axial tilt

# Tidally locked — self-rotation period = orbital period
# Must match MOON_ORBIT_FRAMES in orbit_only.py
MOON_ORBIT_FRAMES  = 274


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


def build_moon_material(texture_path: str):
    obj = bpy.context.active_object
    if obj is None or obj.type != 'MESH':
        raise RuntimeError("Select your Moon sphere first, then run the script.")

    # ── MATERIAL ──────────────────────────────────────────────────────────────
    mat_name = "Moon_Cinematic"
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

    out  = N("ShaderNodeOutputMaterial",  (900,   0))
    bsdf = N("ShaderNodeBsdfPrincipled",  (550,   0))
    bsdf.inputs["Roughness"].default_value          = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    bsdf.inputs["Sheen Weight"].default_value       = 0.04

    tex_coord = N("ShaderNodeTexCoord", (-900, 0))
    mapping   = N("ShaderNodeMapping",  (-700, 0))
    mapping.inputs["Scale"].default_value = (1, 1, 1)

    tex_color = N("ShaderNodeTexImage", (-450, 100))
    tex_color.label = "Moon Base Color"
    if os.path.exists(texture_path):
        img = bpy.data.images.load(texture_path, check_existing=True)
        tex_color.image = img
        img.colorspace_settings.name = 'sRGB'
    else:
        print(f"⚠  Texture not found: {texture_path}")

    hue_sat = N("ShaderNodeHueSaturation", (-150, 100))
    hue_sat.inputs["Hue"].default_value        = 0.58
    hue_sat.inputs["Saturation"].default_value = 0.25
    hue_sat.inputs["Value"].default_value      = 0.95

    rgb_curves = N("ShaderNodeRGBCurve", (80, 100))
    c = rgb_curves.mapping.curves[3]
    c.points[0].location = (0.0,  0.0)
    c.points[1].location = (0.4,  0.36)
    c.points.new(0.8, 0.85)
    rgb_curves.mapping.update()

    sep_rgb  = N("ShaderNodeSeparateColor", (-450, -200))
    mix_bump = N("ShaderNodeMixRGB",        (-200, -200))
    mix_bump.blend_type = 'MIX'
    mix_bump.inputs["Fac"].default_value = 0.5

    bump = N("ShaderNodeBump", (80, -200))
    bump.inputs["Strength"].default_value = 0.80
    bump.inputs["Distance"].default_value = 0.08

    lum_math = N("ShaderNodeMath", (-200, -380))
    lum_math.operation = 'MULTIPLY'
    lum_math.inputs[1].default_value = 0.018

    emission = N("ShaderNodeEmission", (80, -380))
    emission.inputs["Color"].default_value = (0.80, 0.88, 1.0, 1.0)

    add_shader = N("ShaderNodeAddShader", (750, -100))

    links.new(tex_coord.outputs["UV"],     mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"],   tex_color.inputs["Vector"])
    links.new(mapping.outputs["Vector"],   sep_rgb.inputs["Color"])
    links.new(tex_color.outputs["Color"],  hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],    rgb_curves.inputs["Color"])
    links.new(rgb_curves.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex_color.outputs["Color"],  sep_rgb.inputs["Color"])
    links.new(sep_rgb.outputs["Red"],      mix_bump.inputs["Color1"])
    links.new(sep_rgb.outputs["Green"],    mix_bump.inputs["Color2"])
    links.new(mix_bump.outputs["Color"],   bump.inputs["Height"])
    links.new(bump.outputs["Normal"],      bsdf.inputs["Normal"])
    links.new(sep_rgb.outputs["Red"],      lum_math.inputs[0])
    links.new(lum_math.outputs["Value"],   emission.inputs["Strength"])
    links.new(bsdf.outputs["BSDF"],         add_shader.inputs[0])
    links.new(emission.outputs["Emission"], add_shader.inputs[1])
    links.new(add_shader.outputs["Shader"], out.inputs["Surface"])

    print("✅  Moon_Cinematic material applied!")

    # ── TILT + SPIN — baked per frame in local space ──────────────────────────
    bpy.context.scene.frame_start = FRAME_START
    bpy.context.scene.frame_end   = FRAME_END

    obj.animation_data_clear()
    obj.rotation_mode = 'XYZ'

    tilt_x = math.radians(AXIAL_TILT_DEGREES)

    for frame in range(FRAME_START, FRAME_END + 1):
        bpy.context.scene.frame_set(frame)           # frame first
        t      = (frame - FRAME_START) % MOON_ORBIT_FRAMES
        spin_z = (t / MOON_ORBIT_FRAMES) * math.tau  # tidally locked
        obj.rotation_euler = (tilt_x, 0.0, spin_z)
        obj.keyframe_insert(data_path="rotation_euler")

    if obj.animation_data and obj.animation_data.action:
        set_linear_on_action(obj.animation_data.action)

    bpy.context.scene.frame_set(FRAME_START)

    print(f"✅  Tilt:  {AXIAL_TILT_DEGREES}° (X axis, local space)")
    print(f"✅  Spin:  tidally locked — 1 rotation per {MOON_ORBIT_FRAMES} frames")
    print(f"✅  Baked: frames {FRAME_START}–{FRAME_END}")
    print()
    print("   💡 Render tips:")
    print("      • Engine: EEVEE, samples: 128")
    print("      • Add an HDRI (deep space / black with stars)")
    print("      • Single directional light off to one side = sunlight")
    print("      • Add a subtle blue Rim light on the dark side")


build_moon_material(TEXTURE_PATH)