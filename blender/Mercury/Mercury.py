"""
Mercury Cinematic Material Setup + Rotation + Axial Tilt for Blender
=====================================================================
Run this INSIDE Blender:
  1. Open Blender's Text Editor (top menu: Editor Type → Text Editor)
  2. Click "+ New", paste this entire script
  3. Click "Run Script" (or press Alt+P)

Make sure your Mercury sphere is SELECTED before running.
Update TEXTURE_PATH below to your actual file.
"""

import bpy
import os
import math

# ── CHANGE THIS TO YOUR TEXTURE FILE ─────────────────────────────────────────
TEXTURE_PATH = r"C:\Users\kelly\Downloads\Blender\textures\mercury.jpg"
# ─────────────────────────────────────────────────────────────────────────────

# ── ROTATION SETTINGS ─────────────────────────────────────────────────────────
ROTATION_AXIS    = 'Z'   # Spin axis: 'X', 'Y', or 'Z'
ROTATION_DEGREES = 360   # Total degrees over the animation
FRAME_START      = 1     # Start frame
FRAME_END        = 250   # End frame (lower = faster, higher = slower)
# ─────────────────────────────────────────────────────────────────────────────

# ── AXIAL TILT ────────────────────────────────────────────────────────────────
# Mercury's real tilt is only 0.034° (nearly perfectly upright).
# Increase this for a more dramatic/visible tilt (e.g. 23.5 = Earth-like).
AXIAL_TILT_DEGREES = 0.034   # 🪐 Real Mercury value
# AXIAL_TILT_DEGREES = 23.5  # 🌍 Uncomment for Earth-like tilt (more visible)
# AXIAL_TILT_DEGREES = 15.0  # 🎨 Uncomment for subtle artistic tilt
# ─────────────────────────────────────────────────────────────────────────────

SEGMENTS = 128
RINGS    = 64


def fix_mesh(obj):
    """Replace whatever low-poly mesh is on obj with a high-res UV sphere."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    loc   = obj.location.copy()
    scale = obj.scale.copy()

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

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"✅  Mesh replaced: UV Sphere {SEGMENTS}×{RINGS} ({SEGMENTS * RINGS:,} faces), smooth shading applied.")


def apply_axial_tilt(obj):
    """
    Tilt the object on the X axis to simulate axial tilt.
    This is applied as a static rotation BEFORE the spin animation,
    so the spin happens around the already-tilted axis.
    """
    tilt_rad = math.radians(AXIAL_TILT_DEGREES)

    # Apply tilt on X, leave Y and Z at 0 (spin keyframes will handle Z)
    obj.rotation_euler.x = tilt_rad
    obj.rotation_euler.y = 0.0
    # Do NOT touch Z here — the spin animation will keyframe it

    print(f"✅  Axial tilt applied: {AXIAL_TILT_DEGREES}° on X axis")
    if AXIAL_TILT_DEGREES < 1.0:
        print(f"     ℹ️  Tilt is {AXIAL_TILT_DEGREES}° (Mercury's real value) — nearly invisible by design.")
        print(f"        Set AXIAL_TILT_DEGREES = 23.5 for a visible Earth-like tilt.")


def set_linear_interpolation(action, axis_idx):
    """
    Set LINEAR interpolation on rotation_euler fcurves.
    Handles both the legacy API (Blender <4.x) and the new layered
    Action API introduced in Blender 4.x / 5.x.
    """
    data_path = "rotation_euler"

    # ── Legacy flat fcurves (Blender 3.x and below) ───────────────────────────
    if hasattr(action, 'fcurves'):
        for fc in action.fcurves:
            if fc.data_path == data_path and fc.array_index == axis_idx:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
        return

    # ── New layered Action API (Blender 4.x / 5.x) ───────────────────────────
    if not hasattr(action, 'layers') or len(action.layers) == 0:
        print("⚠  Could not find action layers — interpolation not set.")
        return

    layer = action.layers[0]
    if len(layer.strips) == 0:
        print("⚠  No strips in action layer — interpolation not set.")
        return

    strip = layer.strips[0]

    try:
        channelbag = strip.channelbag(strip.channelbags[0] if hasattr(strip, 'channelbags') else None)
    except Exception:
        channelbag = strip.channelbags[0] if hasattr(strip, 'channelbags') and len(strip.channelbags) > 0 else None

    if channelbag is None:
        print("⚠  Could not access channelbag — interpolation not set.")
        return

    for fc in channelbag.fcurves:
        if fc.data_path == data_path and fc.array_index == axis_idx:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


def add_rotation_animation(obj):
    """Keyframe a full constant rotation on the chosen axis."""
    axis_map = {'X': 0, 'Y': 1, 'Z': 2}
    axis_idx = axis_map.get(ROTATION_AXIS.upper(), 2)

    bpy.context.scene.frame_start = FRAME_START
    bpy.context.scene.frame_end   = FRAME_END

    # Clear existing animation data
    obj.animation_data_clear()

    # Re-apply tilt after clearing animation data (clear resets euler)
    apply_axial_tilt(obj)

    # Keyframe at start — preserve tilt, 0° spin
    bpy.context.scene.frame_set(FRAME_START)
    obj.rotation_euler[axis_idx] = 0.0
    obj.keyframe_insert(data_path="rotation_euler", index=axis_idx)

    # Keyframe at end — preserve tilt, full spin
    bpy.context.scene.frame_set(FRAME_END)
    obj.rotation_euler[axis_idx] = math.radians(ROTATION_DEGREES)
    obj.keyframe_insert(data_path="rotation_euler", index=axis_idx)

    # Set constant speed
    if obj.animation_data and obj.animation_data.action:
        set_linear_interpolation(obj.animation_data.action, axis_idx)

    bpy.context.scene.frame_set(FRAME_START)

    print(f"✅  Rotation animation applied:")
    print(f"     • Spin axis : {ROTATION_AXIS.upper()}")
    print(f"     • Frames    : {FRAME_START} → {FRAME_END}")
    print(f"     • Degrees   : {ROTATION_DEGREES}°")
    print(f"     • Speed     : constant (LINEAR interpolation)")


def build_mercury_material(texture_path: str):
    obj = bpy.context.active_object
    if obj is None or obj.type != 'MESH':
        raise RuntimeError("Select your Mercury sphere first, then run the script.")

    fix_mesh(obj)
    add_rotation_animation(obj)

    mat_name = "Mercury_Cinematic"
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

    out        = N("ShaderNodeOutputMaterial",        (1000,   0))

    bsdf       = N("ShaderNodeBsdfPrincipled",        ( 580,   0))
    bsdf.inputs["Roughness"].default_value           = 0.95
    bsdf.inputs["Specular IOR Level"].default_value  = 0.02
    bsdf.inputs["Sheen Weight"].default_value        = 0.04
    bsdf.inputs["Metallic"].default_value            = 0.0

    tex_coord  = N("ShaderNodeTexCoord",              (-950,   0))
    mapping    = N("ShaderNodeMapping",               (-750,   0))
    mapping.inputs["Scale"].default_value            = (1, 1, 1)

    tex_color  = N("ShaderNodeTexImage",              (-500, 120))
    tex_color.label = "Mercury Base Color"
    if os.path.exists(texture_path):
        img = bpy.data.images.load(texture_path, check_existing=True)
        tex_color.image = img
    else:
        print(f"⚠  Texture not found: {texture_path}")
        print("   The material will still be created — add texture manually.")

    hue_sat    = N("ShaderNodeHueSaturation",         (-200, 120))
    hue_sat.inputs["Hue"].default_value          = 0.52
    hue_sat.inputs["Saturation"].default_value   = 0.30
    hue_sat.inputs["Value"].default_value        = 0.85

    rgb_curves = N("ShaderNodeRGBCurve",              ( 50,  120))
    c = rgb_curves.mapping.curves[3]
    c.points[0].location = (0.0,  0.0)
    c.points[1].location = (0.4,  0.35)
    c.points.new(0.85, 0.92)
    rgb_curves.mapping.update()

    mix_tint   = N("ShaderNodeMixRGB",               ( 280,  120))
    mix_tint.blend_type = 'MULTIPLY'
    mix_tint.inputs["Fac"].default_value         = 0.18
    mix_tint.inputs["Color2"].default_value      = (0.72, 0.66, 0.60, 1.0)

    sep_rgb    = N("ShaderNodeSeparateColor",         (-500, -180))
    invert     = N("ShaderNodeInvert",                (-250, -180))
    invert.inputs["Fac"].default_value = 0.35

    mix_bump   = N("ShaderNodeMixRGB",               ( -50, -180))
    mix_bump.blend_type = 'MIX'
    mix_bump.inputs["Fac"].default_value = 0.5

    bump       = N("ShaderNodeBump",                  ( 200, -180))
    bump.inputs["Strength"].default_value  = 0.80
    bump.inputs["Distance"].default_value  = 0.08

    links.new(tex_coord.outputs["UV"],       mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"],     tex_color.inputs["Vector"])
    links.new(mapping.outputs["Vector"],     sep_rgb.inputs["Color"])

    links.new(tex_color.outputs["Color"],    hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],      rgb_curves.inputs["Color"])
    links.new(rgb_curves.outputs["Color"],   mix_tint.inputs["Color1"])
    links.new(mix_tint.outputs["Color"],     bsdf.inputs["Base Color"])

    links.new(tex_color.outputs["Color"],    sep_rgb.inputs["Color"])
    links.new(sep_rgb.outputs["Red"],        invert.inputs["Color"])
    links.new(sep_rgb.outputs["Red"],        mix_bump.inputs["Color1"])
    links.new(invert.outputs["Color"],       mix_bump.inputs["Color2"])
    links.new(mix_bump.outputs["Color"],     bump.inputs["Height"])
    links.new(bump.outputs["Normal"],        bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"],          out.inputs["Surface"])

    print("✅  Mercury_Cinematic material applied successfully!")
    print()
    print("   🪨  Real Mercury surface properties applied:")
    print("       • Dark dull gray with faint brownish tint")
    print("       • Very low albedo (7%) — nearly as dark as coal")
    print("       • Heavy crater bump (more cratered than Mars)")
    print("       • No atmosphere emission (airless world)")
    print()
    print("   💡  Render tips:")
    print("       • Single strong Sun/Point light (Mercury is close to the Sun)")
    print("       • Very low ambient — no atmosphere scattering")
    print("       • Black background, EEVEE, 128 samples")


build_mercury_material(TEXTURE_PATH)