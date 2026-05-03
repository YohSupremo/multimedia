"""
Jupiter + Io + Europa + Ganymede + Callisto — COMPRESSED FOR RECORDING
=======================================================================
Blender 5.1

Changes from realistic version:
  - Orbit distances are compressed so all moons fit nicely in one camera shot
  - Moon sizes kept large enough to be clearly visible
  - Spacing between orbits is even and readable
  - Set RECORDING_MODE = False to restore realistic distances

COMPRESSED ORBIT LAYOUT (Blender Units):
  Jupiter radius:  11.21 BU
  Io orbit:        30 BU   (realistic: 66 BU)
  Europa orbit:    50 BU   (realistic: 105 BU)
  Ganymede orbit:  72 BU   (realistic: 168 BU)
  Callisto orbit:  96 BU   (realistic: 295 BU)

Camera tip: Place camera ~160-180 BU away, FOV ~50°
"""

import bpy
import os
import math
from mathutils import Matrix

# ── RECORDING MODE TOGGLE ─────────────────────────────────────────────────────
RECORDING_MODE = True

# ── SETTINGS ──────────────────────────────────────────────────────────────────

JUPITER_RADIUS_BU = 11.21
JUPITER_TILT_DEG  = 3.13

SEGMENTS = 128
RINGS    = 64

ANIM_END = 250

# ── Realistic size ratios ──────────────────────────────────────────────────────
IO_SIZE_RATIO        = 1821.6  / 71492.0
EUROPA_SIZE_RATIO    = 1560.8  / 71492.0
GANYMEDE_SIZE_RATIO  = 2634.1  / 71492.0
CALLISTO_SIZE_RATIO  = 2410.3  / 71492.0

# ── Realistic orbit ratios ─────────────────────────────────────────────────────
IO_ORBIT_RATIO        = 421700.0   / 71492.0
EUROPA_ORBIT_RATIO    = 671100.0   / 71492.0
GANYMEDE_ORBIT_RATIO  = 1070400.0  / 71492.0
CALLISTO_ORBIT_RATIO  = 1882700.0  / 71492.0

# ── Orbital inclinations (relative to Jupiter's equatorial plane) ─────────────
IO_TILT_DEG        = 0.05
EUROPA_TILT_DEG    = 0.47
GANYMEDE_TILT_DEG  = 0.20
CALLISTO_TILT_DEG  = 0.19

# ── Frame counts ──────────────────────────────────────────────────────────────
IO_ORBIT_FRAMES        = 60
EUROPA_ORBIT_FRAMES    = round(IO_ORBIT_FRAMES * (3.551  / 1.769))
GANYMEDE_ORBIT_FRAMES  = round(IO_ORBIT_FRAMES * (7.155  / 1.769))
CALLISTO_ORBIT_FRAMES  = round(IO_ORBIT_FRAMES * (16.690 / 1.769))
JUPITER_SPIN_FRAMES    = round(IO_ORBIT_FRAMES * (1.769 * 24 / 9.925))

# ── Moon self-rotation (tidally locked — spin period = orbit period) ──────────
IO_SPIN_FRAMES        = IO_ORBIT_FRAMES
EUROPA_SPIN_FRAMES    = EUROPA_ORBIT_FRAMES
GANYMEDE_SPIN_FRAMES  = GANYMEDE_ORBIT_FRAMES
CALLISTO_SPIN_FRAMES  = CALLISTO_ORBIT_FRAMES

# ── Texture paths ─────────────────────────────────────────────────────────────
TEXTURE_BASE  = r"C:\Users\kelly\Downloads\Blender\textures"
JUPITER_TEX   = TEXTURE_BASE + r"\jupiter.jpg"
IO_TEX        = TEXTURE_BASE + r"\io_moon.jpg"
EUROPA_TEX    = TEXTURE_BASE + r"\europa_moon.jpg"
GANYMEDE_TEX  = TEXTURE_BASE + r"\ganymede_moon.jpg"
CALLISTO_TEX  = TEXTURE_BASE + r"\callisto_moon.jpg"

# ─────────────────────────────────────────────────────────────────────────────

if RECORDING_MODE:
    IO_ORBIT_BU        = 30.0
    EUROPA_ORBIT_BU    = 50.0
    GANYMEDE_ORBIT_BU  = 72.0
    CALLISTO_ORBIT_BU  = 96.0

    IO_RADIUS_BU        = 3.2
    EUROPA_RADIUS_BU    = 2.8
    GANYMEDE_RADIUS_BU  = 4.0
    CALLISTO_RADIUS_BU  = 3.6
else:
    MOON_SCALE_BOOST = 1000
    IO_ORBIT_BU        = JUPITER_RADIUS_BU * IO_ORBIT_RATIO
    EUROPA_ORBIT_BU    = JUPITER_RADIUS_BU * EUROPA_ORBIT_RATIO
    GANYMEDE_ORBIT_BU  = JUPITER_RADIUS_BU * GANYMEDE_ORBIT_RATIO
    CALLISTO_ORBIT_BU  = JUPITER_RADIUS_BU * CALLISTO_ORBIT_RATIO
    IO_RADIUS_BU        = JUPITER_RADIUS_BU * IO_SIZE_RATIO        * MOON_SCALE_BOOST
    EUROPA_RADIUS_BU    = JUPITER_RADIUS_BU * EUROPA_SIZE_RATIO    * MOON_SCALE_BOOST
    GANYMEDE_RADIUS_BU  = JUPITER_RADIUS_BU * GANYMEDE_SIZE_RATIO  * MOON_SCALE_BOOST
    CALLISTO_RADIUS_BU  = JUPITER_RADIUS_BU * CALLISTO_SIZE_RATIO  * MOON_SCALE_BOOST

# ─────────────────────────────────────────────────────────────────────────────


def remove_if_exists(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)


def fix_mesh(obj):
    """
    Smooth shade and add Subdivision Surface.
    Does NOT delete/recreate geometry — avoids the Blender 5.1 bug where
    primitive_uv_sphere_add in Edit Mode creates a new object instead of
    adding geometry to the existing mesh, leaving it empty.
    """
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.shade_smooth()

    has_subsurf = any(m.type == 'SUBSURF' for m in obj.modifiers)
    if not has_subsurf:
        sub = obj.modifiers.new(name="Subdivision", type='SUBSURF')
        sub.levels        = 2
        sub.render_levels = 3

    if not obj.data.uv_layers:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.sphere_project()
        bpy.ops.object.mode_set(mode='OBJECT')


def _set_linear(action):
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


def bake_rotation_z(obj, period_frames, tilt_deg, total_frames):
    """
    Per-frame Z rotation bake. frame_set first to avoid transform stomping.
    tilt_deg is baked as an X offset on the rotation so the spin axis tilts.
    For moon meshes tilt_deg=0 is passed since their tilt comes from
    the parent orbit empty; for Jupiter tilt_deg=0 too since its tilt
    comes from the Jupiter_Axis empty.
    """
    obj.animation_data_clear()
    obj.rotation_mode = 'XYZ'
    tilt_x = math.radians(tilt_deg)

    for frame in range(1, total_frames + 1):
        bpy.context.scene.frame_set(frame)
        t       = (frame - 1) % period_frames
        angle_z = (t / period_frames) * math.tau
        obj.rotation_euler = (tilt_x, 0.0, angle_z)
        obj.keyframe_insert("rotation_euler")

    _set_linear(obj.animation_data.action if obj.animation_data else None)


def make_orbit_ring(name, radius_bu, color, tilt_deg, parent_empty):
    """Orbit ring parented to the Jupiter axis empty so it tilts with the system."""
    ring_name = f"Orbit_Ring_{name}"
    remove_if_exists(ring_name)

    bpy.ops.curve.primitive_nurbs_circle_add(radius=radius_bu, location=(0, 0, 0))
    ring = bpy.context.active_object
    ring.name = ring_name
    ring.hide_render = True

    # Own orbital inclination only — system tilt comes from parent_empty
    ring.rotation_euler[0] = math.radians(tilt_deg)
    ring.data.bevel_depth   = 0.08 if RECORDING_MODE else 0.05
    ring.data.use_fill_caps = False

    # Parent to the Jupiter axis empty
    ring.parent = parent_empty
    ring.matrix_parent_inverse = Matrix.Identity(4)

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


def build_body_material(obj, mat_name, tex_path, roughness, sat, hue,
                        bump_strength, emit_color, emit_strength,
                        specular=0.03, metallic=0.0):
    """
    Generic material builder used for both Jupiter and all moons.
    Loads texture, applies hue/sat, bump from luminance, faint emission.
    """
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    def N(t, loc):
        n = nodes.new(t)
        n.location = loc
        return n

    out     = N("ShaderNodeOutputMaterial",  (900,   0))
    bsdf    = N("ShaderNodeBsdfPrincipled",  (500,   0))
    bsdf.inputs["Roughness"].default_value          = roughness
    bsdf.inputs["Specular IOR Level"].default_value = specular
    bsdf.inputs["Metallic"].default_value           = metallic

    tex_c   = N("ShaderNodeTexCoord",        (-800,  0))
    mapping = N("ShaderNodeMapping",         (-600,  0))

    tex     = N("ShaderNodeTexImage",        (-350, 120))
    tex.label = mat_name
    if os.path.exists(tex_path):
        img = bpy.data.images.load(tex_path, check_existing=True)
        tex.image = img
        img.colorspace_settings.name = 'sRGB'
    else:
        print(f"⚠  Texture not found: {tex_path}")

    hue_sat = N("ShaderNodeHueSaturation",   (-80,  120))
    hue_sat.inputs["Hue"].default_value        = hue
    hue_sat.inputs["Saturation"].default_value = sat
    hue_sat.inputs["Value"].default_value      = 1.0

    sep     = N("ShaderNodeSeparateColor",   (-350, -150))
    bump    = N("ShaderNodeBump",            ( 100, -150))
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.05

    emit    = N("ShaderNodeEmission",        ( 100, -300))
    emit.inputs["Color"].default_value    = (*emit_color, 1.0)
    emit.inputs["Strength"].default_value = emit_strength

    add_sh  = N("ShaderNodeAddShader",       ( 700, -100))

    links.new(tex_c.outputs["UV"],        mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"],  tex.inputs["Vector"])
    links.new(tex.outputs["Color"],       hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],   bsdf.inputs["Base Color"])
    links.new(tex.outputs["Color"],       sep.inputs["Color"])
    links.new(sep.outputs["Red"],         bump.inputs["Height"])
    links.new(bump.outputs["Normal"],     bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"],       add_sh.inputs[0])
    links.new(emit.outputs["Emission"],   add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],   out.inputs["Surface"])


def hard_reset_object(obj):
    obj.animation_data_clear()
    obj.constraints.clear()
    if obj.parent is not None:
        obj.parent = None
        obj.matrix_parent_inverse.identity()
    obj.location       = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.rotation_mode  = 'XYZ'
    obj.scale          = (1.0, 1.0, 1.0)
    obj.matrix_parent_inverse = Matrix.Identity(4)


def setup_moon(moon, name, orbit_bu, moon_radius_bu, orbit_frames,
               tilt_deg, color, mat_name, tex_path,
               roughness, sat, hue, bump_strength, emit_color, emit_strength,
               axis_empty, spin_frames):
    """
    axis_empty  — the Jupiter_Axis empty carrying JUPITER_TILT_DEG.
    spin_frames — how many frames for one full self-rotation of the moon.
                  Tidally locked = same as orbit_frames (physically correct).
    """

    empty_name = f"Orbit_Empty_{name}"
    remove_if_exists(empty_name)

    hard_reset_object(moon)
    fix_mesh(moon)
    build_body_material(moon, mat_name, tex_path, roughness, sat, hue,
                        bump_strength, emit_color, emit_strength)

    moon.scale = (moon_radius_bu,) * 3

    # Create orbit empty at origin, parented to the Jupiter axis empty
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.0))
    empty = bpy.context.active_object
    empty.name = empty_name
    empty.rotation_euler = (0.0, 0.0, 0.0)

    # System-wide tilt inherited from axis_empty parent
    empty.parent = axis_empty
    empty.matrix_parent_inverse = Matrix.Identity(4)

    # Moon parented to orbit empty, offset to its orbital radius
    moon.parent = empty
    moon.matrix_parent_inverse = Matrix.Identity(4)
    moon.location = (orbit_bu, 0.0, 0.0)

    # Orbital revolution baked onto the empty (tilt_deg = own inclination)
    bake_rotation_z(empty, orbit_frames, tilt_deg, ANIM_END)

    # Self-rotation baked directly onto the moon mesh
    # tilt_deg=0 here — the moon's axis tilt relative to its orbit plane
    # is negligible for the Galilean moons, and system tilt already
    # comes from axis_empty above
    bake_rotation_z(moon, spin_frames, tilt_deg=0.0, total_frames=ANIM_END)

    make_orbit_ring(name, orbit_bu, color, tilt_deg, axis_empty)

    print(f"   {name}: orbit {orbit_bu:.1f} BU | radius {moon_radius_bu:.2f} BU "
          f"| orbit {orbit_frames} f | spin {spin_frames} f")


def setup():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    jupiter  = bpy.data.objects.get("Jupiter")
    io       = bpy.data.objects.get("Io")
    europa   = bpy.data.objects.get("Europa")
    ganymede = bpy.data.objects.get("Ganymede")
    callisto = bpy.data.objects.get("Callisto")

    missing = [n for n, o in [("Jupiter", jupiter), ("Io", io),
               ("Europa", europa), ("Ganymede", ganymede),
               ("Callisto", callisto)] if o is None]
    if missing:
        raise RuntimeError(f"❌ Missing objects in scene: {missing}")

    # ── JUPITER AXIS EMPTY ────────────────────────────────────────────────────
    # Single static empty tilted at JUPITER_TILT_DEG on X.
    # All moon orbit empties, orbit rings, and Jupiter itself are parented
    # here so the entire Jovian system shares one consistent axial tilt.
    axis_name = "Jupiter_Axis"
    remove_if_exists(axis_name)

    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.0))
    axis_empty = bpy.context.active_object
    axis_empty.name = axis_name
    axis_empty.rotation_euler = (math.radians(JUPITER_TILT_DEG), 0.0, 0.0)

    print(f"✅ Jupiter_Axis empty created — tilt {JUPITER_TILT_DEG}° on X")

    # ── JUPITER ───────────────────────────────────────────────────────────────
    print("Setting up Jupiter...")

    bpy.ops.object.select_all(action='DESELECT')
    jupiter.select_set(True)
    bpy.context.view_layer.objects.active = jupiter

    jupiter.constraints.clear()
    jupiter.animation_data_clear()
    if jupiter.parent:
        jupiter.parent = None
        jupiter.matrix_parent_inverse = Matrix.Identity(4)

    jupiter.location       = (0.0, 0.0, 0.0)
    jupiter.rotation_euler = (0.0, 0.0, 0.0)
    jupiter.rotation_mode  = 'XYZ'

    fix_mesh(jupiter)
    jupiter.scale = (JUPITER_RADIUS_BU,
                     JUPITER_RADIUS_BU,
                     JUPITER_RADIUS_BU * 0.935)   # Jupiter is oblate

    build_body_material(
        obj          = jupiter,
        mat_name     = "Jupiter_Cinematic",
        tex_path     = JUPITER_TEX,
        roughness    = 0.80,
        sat          = 1.30,
        hue          = 0.52,
        bump_strength= 0.20,
        emit_color   = (1.0, 0.80, 0.55),
        emit_strength= 0.02,
        specular     = 0.04,
    )
    print("✅ Jupiter material applied!")

    # Parent Jupiter mesh to axis_empty — tilt comes from the empty,
    # so spin is baked with tilt_deg=0 to avoid double-applying it
    jupiter.parent = axis_empty
    jupiter.matrix_parent_inverse = Matrix.Identity(4)

    print("Baking Jupiter spin...")
    bake_rotation_z(jupiter, JUPITER_SPIN_FRAMES, tilt_deg=0.0, total_frames=ANIM_END)
    print(f"✅ Jupiter — radius {JUPITER_RADIUS_BU} BU | spin {JUPITER_SPIN_FRAMES} frames")

    # ── IO ────────────────────────────────────────────────────────────────────
    print("Setting up Io...")
    setup_moon(
        moon=io, name="Io",
        orbit_bu=IO_ORBIT_BU, moon_radius_bu=IO_RADIUS_BU,
        orbit_frames=IO_ORBIT_FRAMES, tilt_deg=IO_TILT_DEG,
        color=(1.0, 0.85, 0.20),
        mat_name="Io_Cinematic", tex_path=IO_TEX,
        roughness=0.85, sat=1.60, hue=0.51,
        bump_strength=0.60,
        emit_color=(1.0, 0.55, 0.05), emit_strength=0.03,
        axis_empty=axis_empty,
        spin_frames=IO_SPIN_FRAMES,
    )
    print("✅ Io done")

    # ── EUROPA ────────────────────────────────────────────────────────────────
    print("Setting up Europa...")
    setup_moon(
        moon=europa, name="Europa",
        orbit_bu=EUROPA_ORBIT_BU, moon_radius_bu=EUROPA_RADIUS_BU,
        orbit_frames=EUROPA_ORBIT_FRAMES, tilt_deg=EUROPA_TILT_DEG,
        color=(0.70, 0.85, 1.00),
        mat_name="Europa_Cinematic", tex_path=EUROPA_TEX,
        roughness=0.55, sat=0.80, hue=0.54,
        bump_strength=0.25,
        emit_color=(0.75, 0.90, 1.00), emit_strength=0.01,
        axis_empty=axis_empty,
        spin_frames=EUROPA_SPIN_FRAMES,
    )
    print("✅ Europa done")

    # ── GANYMEDE ──────────────────────────────────────────────────────────────
    print("Setting up Ganymede...")
    setup_moon(
        moon=ganymede, name="Ganymede",
        orbit_bu=GANYMEDE_ORBIT_BU, moon_radius_bu=GANYMEDE_RADIUS_BU,
        orbit_frames=GANYMEDE_ORBIT_FRAMES, tilt_deg=GANYMEDE_TILT_DEG,
        color=(0.75, 0.72, 0.68),
        mat_name="Ganymede_Cinematic", tex_path=GANYMEDE_TEX,
        roughness=0.90, sat=0.70, hue=0.52,
        bump_strength=0.55,
        emit_color=(0.80, 0.75, 0.65), emit_strength=0.005,
        axis_empty=axis_empty,
        spin_frames=GANYMEDE_SPIN_FRAMES,
    )
    print("✅ Ganymede done")

    # ── CALLISTO ──────────────────────────────────────────────────────────────
    print("Setting up Callisto...")
    setup_moon(
        moon=callisto, name="Callisto",
        orbit_bu=CALLISTO_ORBIT_BU, moon_radius_bu=CALLISTO_RADIUS_BU,
        orbit_frames=CALLISTO_ORBIT_FRAMES, tilt_deg=CALLISTO_TILT_DEG,
        color=(0.45, 0.42, 0.40),
        mat_name="Callisto_Cinematic", tex_path=CALLISTO_TEX,
        roughness=0.95, sat=0.50, hue=0.51,
        bump_strength=0.75,
        emit_color=(0.60, 0.55, 0.50), emit_strength=0.005,
        axis_empty=axis_empty,
        spin_frames=CALLISTO_SPIN_FRAMES,
    )
    print("✅ Callisto done")

    scene.frame_set(1)

    mode_label = "RECORDING (compressed)" if RECORDING_MODE else "REALISTIC"
    print(f"\n🪐 Jupiter system ready! Mode: {mode_label}")
    print(f"\n   System axial tilt: {JUPITER_TILT_DEG}° (via Jupiter_Axis empty)")
    print(f"\n   Orbit distances:")
    print(f"   Io:       {IO_ORBIT_BU:.1f} BU")
    print(f"   Europa:   {EUROPA_ORBIT_BU:.1f} BU")
    print(f"   Ganymede: {GANYMEDE_ORBIT_BU:.1f} BU")
    print(f"   Callisto: {CALLISTO_ORBIT_BU:.1f} BU")
    print(f"\n   Frame periods:")
    print(f"   Jupiter spin: {JUPITER_SPIN_FRAMES} frames")
    print(f"   Io:           {IO_ORBIT_FRAMES} frames  | spin {IO_SPIN_FRAMES} frames")
    print(f"   Europa:       {EUROPA_ORBIT_FRAMES} frames  | spin {EUROPA_SPIN_FRAMES} frames")
    print(f"   Ganymede:     {GANYMEDE_ORBIT_FRAMES} frames  | spin {GANYMEDE_SPIN_FRAMES} frames")
    print(f"   Callisto:     {CALLISTO_ORBIT_FRAMES} frames | spin {CALLISTO_SPIN_FRAMES} frames")
    if RECORDING_MODE:
        print(f"\n   📷 Camera tip: place ~160 BU away, FOV ~50°")
    print(f"\n   To switch modes: set RECORDING_MODE = {'False' if RECORDING_MODE else 'True'}")
    print(f"   Update TEXTURE_BASE path if textures not loading.")


setup()