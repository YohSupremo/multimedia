"""
Saturn — Titan + Rhea + Enceladus Orbit & Spin Animation
===================================================
Blender 4+/5  |  Based directly on Jupiter reference script pattern.

HOW TO USE:
  1. Run your Saturn script first (so Saturn exists in scene)
  2. Create 3 UV Sphere objects named exactly: Titan, Rhea, Enceladus
  3. Run this script in Scripting tab
"""

import bpy
import math
from mathutils import Matrix

# ── TOGGLE ────────────────────────────────────────────────────────────────────
RECORDING_MODE = True

# ── SETTINGS ──────────────────────────────────────────────────────────────────
SATURN_RADIUS_BU = 9.45
SATURN_TILT_DEG  = 26.73
SEGMENTS         = 128
RINGS            = 64
ANIM_END         = 1200

# ── Real size ratios (moon radius / Saturn radius) ────────────────────────────
TITAN_SIZE_RATIO     = 2574.7 / 58232.0
RHEA_SIZE_RATIO      =  763.8 / 58232.0
ENCELADUS_SIZE_RATIO =  252.1 / 58232.0

# ── Real orbit ratios (orbit radius / Saturn radius) ──────────────────────────
TITAN_ORBIT_RATIO     = 1221870.0 / 58232.0
RHEA_ORBIT_RATIO      =  527108.0 / 58232.0
ENCELADUS_ORBIT_RATIO =  238020.0 / 58232.0

# ── Orbital inclinations ──────────────────────────────────────────────────────
TITAN_TILT_DEG     = 0.0
RHEA_TILT_DEG      = 0.0
ENCELADUS_TILT_DEG = 0.0

# ── Orbital periods ───────────────────────────────────────────────────────────
# Enceladus: 1.370 days | Rhea: 4.518 days | Titan: 15.945 days
BASE_FRAMES            = 60
ENCELADUS_ORBIT_FRAMES = BASE_FRAMES
RHEA_ORBIT_FRAMES      = round(BASE_FRAMES * (4.518  / 1.370))
TITAN_ORBIT_FRAMES     = round(BASE_FRAMES * (15.945 / 1.370))

# ── Independent Spin Speeds (Frames per 360-degree local rotation) ────────────
# Lower numbers = faster spin. Adjust these to your liking!
ENCELADUS_SPIN_FRAMES = 30
RHEA_SPIN_FRAMES      = 45
TITAN_SPIN_FRAMES     = 80

# ── Texture paths ─────────────────────────────────────────────────────────────
TEXTURE_BASE  = r"C:\Users\kelly\Downloads\Blender\textures"
TITAN_TEX     = TEXTURE_BASE + r"\titan_moon.jpg"
RHEA_TEX      = TEXTURE_BASE + r"\rhea_moon.jpg"
ENCELADUS_TEX = TEXTURE_BASE + r"\enceladus_moon.jpg"

# ── Orbit & size calculation ──────────────────────────────────────────────────
if RECORDING_MODE:
    F_RING_OUTER_BU    = SATURN_RADIUS_BU * 2.36   # ~22.3 BU

    ENCELADUS_ORBIT_BU = F_RING_OUTER_BU * 1.6     # ~36 BU
    RHEA_ORBIT_BU      = F_RING_OUTER_BU * 3.2     # ~71 BU
    TITAN_ORBIT_BU     = F_RING_OUTER_BU * 5.5     # ~123 BU

    TITAN_RADIUS_BU     = 5.5
    RHEA_RADIUS_BU      = 2.2
    ENCELADUS_RADIUS_BU = 1.4
else:
    MOON_SCALE_BOOST   = 800
    TITAN_ORBIT_BU     = SATURN_RADIUS_BU * TITAN_ORBIT_RATIO
    RHEA_ORBIT_BU      = SATURN_RADIUS_BU * RHEA_ORBIT_RATIO
    ENCELADUS_ORBIT_BU = SATURN_RADIUS_BU * ENCELADUS_ORBIT_RATIO
    TITAN_RADIUS_BU     = SATURN_RADIUS_BU * TITAN_SIZE_RATIO     * MOON_SCALE_BOOST
    RHEA_RADIUS_BU      = SATURN_RADIUS_BU * RHEA_SIZE_RATIO      * MOON_SCALE_BOOST
    ENCELADUS_RADIUS_BU = SATURN_RADIUS_BU * ENCELADUS_SIZE_RATIO * MOON_SCALE_BOOST


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def remove_if_exists(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)


def _set_linear(action):
    if action is None:
        return
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for fc in strip.fcurves:
                    fc.extrapolation = 'LINEAR'
                    for kp in fc.keyframe_points:
                        kp.interpolation     = 'LINEAR'
                        kp.handle_left_type  = 'VECTOR'
                        kp.handle_right_type = 'VECTOR'
        return
    except AttributeError:
        pass
    try:
        for fc in action.fcurves:
            fc.extrapolation = 'LINEAR'
            for kp in fc.keyframe_points:
                kp.interpolation     = 'LINEAR'
                kp.handle_left_type  = 'VECTOR'
                kp.handle_right_type = 'VECTOR'
    except AttributeError:
        pass


def bake_rotation_z(obj, period_frames, tilt_deg, total_frames):
    """Per-frame Z rotation keyframes."""
    # Only clear animation if the object doesn't already have one, 
    # to avoid overwriting previously baked local animations if called twice.
    # Wait, we want to clear it safely first.
    if obj.animation_data:
        obj.animation_data_clear()
        
    obj.rotation_mode = 'XYZ'
    ix = math.radians(tilt_deg)

    for frame in range(1, total_frames + 1):
        t       = (frame - 1) % period_frames
        angle_z = (t / period_frames) * math.tau
        obj.rotation_euler = (ix, 0, angle_z)
        obj.keyframe_insert("rotation_euler", frame=frame)

    _set_linear(obj.animation_data.action if obj.animation_data else None)


def fix_mesh(obj):
    """Replace mesh with clean high-res UV sphere at origin, scale 1."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj.modifiers.clear()

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete(type='VERT')
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=SEGMENTS, ring_count=RINGS, radius=1.0, location=(0, 0, 0))
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.faces_shade_smooth()
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def hard_reset_object(obj):
    """Zero all transforms and remove parent."""
    obj.animation_data_clear()
    obj.constraints.clear()

    if obj.parent is not None:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    obj.location       = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.rotation_mode  = 'XYZ'
    obj.scale          = (1.0, 1.0, 1.0)
    obj.matrix_parent_inverse = Matrix.Identity(4)


def make_orbit_ring(name, radius_bu, color, tilt_deg):
    """Decorative orbit path ring — viewport only, hidden at render."""
    ring_name = f"Orbit_Ring_{name}"
    remove_if_exists(ring_name)

    bpy.ops.curve.primitive_nurbs_circle_add(radius=radius_bu, location=(0, 0, 0))
    ring = bpy.context.active_object
    ring.name             = ring_name
    ring.hide_render      = True
    ring.rotation_euler[0] = math.radians(tilt_deg)
    ring.data.bevel_depth   = 0.08 if RECORDING_MODE else 0.05
    ring.data.use_fill_caps = False

    mat_name = f"OrbitMat_{name}"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em  = mat.node_tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value    = (*color, 1.0)
    em.inputs["Strength"].default_value = 2.0
    mat.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    ring.data.materials.clear()
    ring.data.materials.append(mat)


def build_moon_material(obj, mat_name, tex_path, roughness, sat, hue,
                        bump_strength, emit_color, emit_strength):
    import os

    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    def N(t, loc):
        n = nodes.new(t); n.location = loc; return n

    out     = N("ShaderNodeOutputMaterial", (900,   0))
    bsdf    = N("ShaderNodeBsdfPrincipled", (500,   0))
    bsdf.inputs["Roughness"].default_value          = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.03
    bsdf.inputs["Metallic"].default_value           = 0.0

    tex_c   = N("ShaderNodeTexCoord",       (-800,  0))
    mapping = N("ShaderNodeMapping",        (-600,  0))
    tex     = N("ShaderNodeTexImage",       (-350, 120))

    if os.path.exists(tex_path):
        tex.image = bpy.data.images.load(tex_path, check_existing=True)
        print(f"      ✅ Texture: {tex_path}")
    else:
        print(f"      ⚠  No texture at {tex_path} — using fallback colour")

    hue_sat = N("ShaderNodeHueSaturation", (-80, 120))
    hue_sat.inputs["Hue"].default_value        = hue
    hue_sat.inputs["Saturation"].default_value = sat
    hue_sat.inputs["Value"].default_value      = 1.0

    sep  = N("ShaderNodeSeparateColor", (-350, -150))
    bump = N("ShaderNodeBump",          ( 100, -150))
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.05

    emit = N("ShaderNodeEmission", (100, -300))
    emit.inputs["Color"].default_value    = (*emit_color, 1.0)
    emit.inputs["Strength"].default_value = emit_strength

    add_sh = N("ShaderNodeAddShader", (700, -100))

    links.new(tex_c.outputs["UV"],       mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"],      hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],  bsdf.inputs["Base Color"])
    links.new(tex.outputs["Color"],      sep.inputs["Color"])
    links.new(sep.outputs["Red"],        bump.inputs["Height"])
    links.new(bump.outputs["Normal"],    bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"],      add_sh.inputs[0])
    links.new(emit.outputs["Emission"],  add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],  out.inputs["Surface"])


def setup_moon(moon, name, orbit_bu, moon_radius_bu, orbit_frames,
               tilt_deg, color, mat_name, tex_path,
               roughness, sat, hue, bump_strength, emit_color, emit_strength,
               spin_frames=None): # <-- Added spin_frames parameter
    """
    1. hard_reset_object
    2. fix_mesh
    3. build_moon_material
    4. create Empty at (0,0,0)
    5. parent moon to empty, moon.location = (orbit_bu, 0, 0)
    6. bake_rotation_z on the empty (Orbital revolution)
    7. bake_rotation_z on the moon (Local axial spin)
    8. make_orbit_ring
    """
    empty_name = f"Orbit_Empty_{name}"
    remove_if_exists(empty_name)

    print(f"\n   Setting up {name}...")

    hard_reset_object(moon)
    fix_mesh(moon)
    build_moon_material(moon, mat_name, tex_path, roughness, sat, hue,
                        bump_strength, emit_color, emit_strength)

    # Create empty pivot at world origin FIRST
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.0))
    empty = bpy.context.active_object
    empty.name           = empty_name
    empty.rotation_euler = (0.0, 0.0, 0.0)
    empty.location       = (0.0, 0.0, 0.0)

    # Parent moon to empty, THEN set position and scale
    bpy.ops.object.select_all(action='DESELECT')
    moon.parent                 = empty
    moon.matrix_parent_inverse  = Matrix.Identity(4)
    moon.location               = (orbit_bu, 0.0, 0.0)
    moon.rotation_euler         = (0.0, 0.0, 0.0)
    moon.scale                  = (moon_radius_bu, moon_radius_bu, moon_radius_bu)

    # Bake orbital revolution on the empty
    bake_rotation_z(empty, orbit_frames, tilt_deg, ANIM_END)

    # Bake local independent spin on the moon object itself
    if spin_frames is not None:
        bake_rotation_z(moon, spin_frames, 0.0, ANIM_END)

    # Decorative orbit ring
    make_orbit_ring(name, orbit_bu, color, tilt_deg)

    print(f"   ✅ {name} — orbit {orbit_bu:.1f} BU | radius {moon_radius_bu:.2f} BU | {orbit_frames} frames/orbit")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def setup():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    titan     = bpy.data.objects.get("Titan")
    rhea      = bpy.data.objects.get("Rhea")
    enceladus = bpy.data.objects.get("Enceladus")

    missing = [n for n, o in [("Titan", titan),
                               ("Rhea", rhea),
                               ("Enceladus", enceladus)] if o is None]
    if missing:
        raise RuntimeError(
            f"❌  Missing objects: {missing}\n"
            f"    Create UV Sphere objects with those exact names and re-run."
        )

    # ── TITAN ─────────────────────────────────────────────────────────────────
    setup_moon(
        moon=titan, name="Titan",
        orbit_bu=TITAN_ORBIT_BU, moon_radius_bu=TITAN_RADIUS_BU,
        orbit_frames=TITAN_ORBIT_FRAMES, tilt_deg=TITAN_TILT_DEG,
        color=(1.0, 0.75, 0.30),
        mat_name="Titan_Mat", tex_path=TITAN_TEX,
        roughness=0.90, sat=1.20, hue=0.54,
        bump_strength=0.20,
        emit_color=(1.0, 0.65, 0.20), emit_strength=0.02,
        spin_frames=TITAN_SPIN_FRAMES # <-- Assigned independent spin
    )

    # ── RHEA ──────────────────────────────────────────────────────────────────
    setup_moon(
        moon=rhea, name="Rhea",
        orbit_bu=RHEA_ORBIT_BU, moon_radius_bu=RHEA_RADIUS_BU,
        orbit_frames=RHEA_ORBIT_FRAMES, tilt_deg=RHEA_TILT_DEG,
        color=(0.78, 0.82, 0.90),
        mat_name="Rhea_Mat", tex_path=RHEA_TEX,
        roughness=0.88, sat=0.55, hue=0.52,
        bump_strength=0.50,
        emit_color=(0.80, 0.82, 0.88), emit_strength=0.005,
        spin_frames=RHEA_SPIN_FRAMES # <-- Assigned independent spin
    )

    # ── ENCELADUS ─────────────────────────────────────────────────────────────
    setup_moon(
        moon=enceladus, name="Enceladus",
        orbit_bu=ENCELADUS_ORBIT_BU, moon_radius_bu=ENCELADUS_RADIUS_BU,
        orbit_frames=ENCELADUS_ORBIT_FRAMES, tilt_deg=ENCELADUS_TILT_DEG,
        color=(0.70, 0.95, 1.00),
        mat_name="Enceladus_Mat", tex_path=ENCELADUS_TEX,
        roughness=0.35, sat=0.30, hue=0.54,
        bump_strength=0.15,
        emit_color=(0.85, 0.95, 1.00), emit_strength=0.04,
        spin_frames=ENCELADUS_SPIN_FRAMES # <-- Assigned independent spin
    )

    scene.frame_set(1)

    print(f"\n🪐 Saturn moon system ready!")
    print(f"   Enceladus: {ENCELADUS_ORBIT_BU:.1f} BU  ({ENCELADUS_ORBIT_FRAMES} frames/orbit)")
    print(f"   Rhea:      {RHEA_ORBIT_BU:.1f} BU  ({RHEA_ORBIT_FRAMES} frames/orbit)")
    print(f"   Titan:     {TITAN_ORBIT_BU:.1f} BU  ({TITAN_ORBIT_FRAMES} frames/orbit)")
    print(f"   📷 Camera tip: ~160 BU away, FOV ~50°")
    print(f"   Press Space to play ▶")


setup()