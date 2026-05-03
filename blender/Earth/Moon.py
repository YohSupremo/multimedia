"""
Moon Cinematic Material Setup for Blender 5.0
==============================================
1. Open Text Editor (Editor Type → Text Editor)
2. Click "+ New", paste this script
3. Select your Moon sphere, then Run Script (Alt+P)
"""

import bpy
import os
import math

# ── UPDATE THIS PATH ──────────────────────────────────────────────────────────
TEXTURE_PATH = r"C:\Users\kelly\Downloads\Blender\textures\moon.jpg"
# ─────────────────────────────────────────────────────────────────────────────

ROTATION_DEGREES   = 360    # prograde (counter-clockwise)
FRAME_START        = 1
FRAME_END          = 300
AXIAL_TILT_DEGREES = 6.68   # Moon's real axial tilt

def build_moon_material(texture_path: str):
    obj = bpy.context.active_object
    if obj is None or obj.type != 'MESH':
        raise RuntimeError("Select your Moon sphere first, then run the script.")

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

    # ── Output ────────────────────────────────────────────────────────────────
    out  = N("ShaderNodeOutputMaterial",  (900,   0))
    bsdf = N("ShaderNodeBsdfPrincipled",  (550,   0))

    # Moon surface properties — very matte, almost zero specular
    bsdf.inputs["Roughness"].default_value          = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    bsdf.inputs["Sheen Weight"].default_value       = 0.04

    # ── UV coords + mapping ───────────────────────────────────────────────────
    tex_coord = N("ShaderNodeTexCoord", (-900, 0))
    mapping   = N("ShaderNodeMapping",  (-700, 0))
    mapping.inputs["Scale"].default_value = (1, 1, 1)

    # ── Base texture ──────────────────────────────────────────────────────────
    tex_color = N("ShaderNodeTexImage", (-450, 100))
    tex_color.label = "Moon Base Color"
    if os.path.exists(texture_path):
        img = bpy.data.images.load(texture_path, check_existing=True)
        tex_color.image = img
        img.colorspace_settings.name = 'sRGB'
    else:
        print(f"⚠  Texture not found: {texture_path}")

    # ── Hue/Sat — desaturate and cool the tones (grey with slight blue) ───────
    hue_sat = N("ShaderNodeHueSaturation", (-150, 100))
    hue_sat.inputs["Hue"].default_value         = 0.58
    hue_sat.inputs["Saturation"].default_value  = 0.25
    hue_sat.inputs["Value"].default_value       = 0.95

    # ── RGB Curves — punch up crater contrast ─────────────────────────────────
    rgb_curves = N("ShaderNodeRGBCurve", (80, 100))
    c = rgb_curves.mapping.curves[3]
    c.points[0].location = (0.0,  0.0)
    c.points[1].location = (0.4,  0.36)
    c.points.new(0.8, 0.85)
    rgb_curves.mapping.update()

    # ── Bump from luminance ───────────────────────────────────────────────────
    sep_rgb  = N("ShaderNodeSeparateColor", (-450, -200))
    mix_bump = N("ShaderNodeMixRGB",        (-200, -200))
    mix_bump.blend_type = 'MIX'
    mix_bump.inputs["Fac"].default_value = 0.5

    bump = N("ShaderNodeBump", (80, -200))
    bump.inputs["Strength"].default_value = 0.80
    bump.inputs["Distance"].default_value = 0.08

    # ── Very faint cold emission ──────────────────────────────────────────────
    lum_math = N("ShaderNodeMath", (-200, -380))
    lum_math.operation = 'MULTIPLY'
    lum_math.inputs[1].default_value = 0.018

    emission = N("ShaderNodeEmission", (80, -380))
    emission.inputs["Color"].default_value = (0.80, 0.88, 1.0, 1.0)

    add_shader = N("ShaderNodeAddShader", (750, -100))

    # ── Wire it all up ────────────────────────────────────────────────────────
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
    print("   💡 Render tips:")
    print("      • Engine: Cycles, samples ≥ 128")
    print("      • Add an HDRI (deep space / black with stars)")
    print("      • Single directional light off to one side = sunlight")
    print("      • Disable Bloom OR keep it very subtle (0.05)")
    print("      • Add a subtle blue Rim light on the dark side")

    # ---- TILT + ROTATION ----
    bpy.context.scene.frame_start = FRAME_START
    bpy.context.scene.frame_end   = FRAME_END
    obj.animation_data_clear()

    obj.rotation_euler.x = math.radians(AXIAL_TILT_DEGREES)  # 6.68° real tilt
    obj.rotation_euler.y = 0.0

    bpy.context.scene.frame_set(FRAME_START)
    obj.rotation_euler.z = 0.0
    obj.keyframe_insert(data_path="rotation_euler", index=2)

    bpy.context.scene.frame_set(FRAME_END)
    obj.rotation_euler.z = math.radians(ROTATION_DEGREES)
    obj.keyframe_insert(data_path="rotation_euler", index=2)

    # ---- LINEAR INTERPOLATION — Blender 5.1 compatible ----
    if obj.animation_data and obj.animation_data.action:
        action = obj.animation_data.action
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
    print(f"✅  Tilt applied: {AXIAL_TILT_DEGREES}°")
    print(f"✅  Rotation applied: {ROTATION_DEGREES}° over {FRAME_END} frames (prograde)")

build_moon_material(TEXTURE_PATH)