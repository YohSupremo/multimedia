"""
Uranus — Oberon + Titania Orbit Animation (Fixed Retrograde + Spin)
==========================================
Blender 4+/5  |  Based on Saturn moon reference pattern.

HOW TO USE:
  1. Run your Uranus script first (so Uranus exists in scene)
  2. Create 2 UV Sphere objects named exactly: Oberon, Titania
  3. Run this script in Scripting tab

RECORDING_MODE = True  → compressed orbits, both moons visible in one shot
RECORDING_MODE = False → realistic distances

Real facts:
  - Titania: largest moon of Uranus, icy/rocky, heavily cratered with canyons
  - Oberon:  second largest, dark reddish terrain, heavily cratered
  - Both orbit Uranus's equatorial plane — which is tilted 97.77°
    (but since we set Uranus tilt to 0° in the planet script, orbits are flat)
  - Titania period: 8.706 days
  - Oberon period:  13.463 days
"""

import bpy
import math
from mathutils import Matrix

# ── TOGGLE ────────────────────────────────────────────────────────────────────
RECORDING_MODE = True

# ── SETTINGS ──────────────────────────────────────────────────────────────────
URANUS_RADIUS_BU = 8.00
SEGMENTS         = 128
RINGS            = 64
ANIM_END         = 250

# ── Real size ratios (moon radius / Uranus radius) ────────────────────────────
# Titania radius: 788.4 km  |  Uranus radius: 25362 km
# Oberon radius:  761.4 km  |  Uranus radius: 25362 km
TITANIA_SIZE_RATIO =  788.4 / 25362.0
OBERON_SIZE_RATIO  =  761.4 / 25362.0

# ── Real orbit ratios (orbit radius / Uranus radius) ──────────────────────────
# Titania orbit: 435910 km  |  Oberon orbit: 583520 km
TITANIA_ORBIT_RATIO = 435910.0 / 25362.0
OBERON_ORBIT_RATIO  = 583520.0 / 25362.0

# ── Orbital inclinations (both nearly 0° to Uranus equator) ──────────────────
TITANIA_TILT_DEG = 0.0
OBERON_TILT_DEG  = 0.0

# ── Orbital periods ───────────────────────────────────────────────────────────
# Titania: 8.706 days  |  Oberon: 13.463 days
BASE_FRAMES           = 60
TITANIA_ORBIT_FRAMES  = BASE_FRAMES
OBERON_ORBIT_FRAMES   = round(BASE_FRAMES * (13.463 / 8.706))

# ── Independent Spin Speeds (Frames per 360-degree local rotation) ────────────
TITANIA_SPIN_FRAMES = 80
OBERON_SPIN_FRAMES  = 110

# ── Texture paths ─────────────────────────────────────────────────────────────
TEXTURE_BASE  = r"C:\Users\kelly\Downloads\Blender\textures"
TITANIA_TEX   = TEXTURE_BASE + r"\titania_moon.jpg"
OBERON_TEX    = TEXTURE_BASE + r"\oberon_moon.jpg"

# ── Orbit & size calculation ──────────────────────────────────────────────────
if RECORDING_MODE:
    # Compressed orbits but realistic-feeling size ratio
    TITANIA_ORBIT_BU = URANUS_RADIUS_BU * 4.5    # ~36 BU
    OBERON_ORBIT_BU  = URANUS_RADIUS_BU * 6.5    # ~52 BU

    # Realistic: Titania is ~3.1% of Uranus radius, boosted slightly to be visible
    TITANIA_RADIUS_BU = URANUS_RADIUS_BU * 0.060  # ~0.48 BU — small but visible
    OBERON_RADIUS_BU  = URANUS_RADIUS_BU * 0.058  # ~0.46 BU
else:
    MOON_SCALE_BOOST  = 600
    TITANIA_ORBIT_BU  = URANUS_RADIUS_BU * TITANIA_ORBIT_RATIO
    OBERON_ORBIT_BU   = URANUS_RADIUS_BU * OBERON_ORBIT_RATIO
    TITANIA_RADIUS_BU = URANUS_RADIUS_BU * TITANIA_SIZE_RATIO * MOON_SCALE_BOOST
    OBERON_RADIUS_BU  = URANUS_RADIUS_BU * OBERON_SIZE_RATIO  * MOON_SCALE_BOOST


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


def bake_rotation_z(obj, period_frames, tilt_deg, total_frames, retrograde=False):
    """Bakes rotation around Z. Added retrograde flag for Uranus clockwise rotation."""
    if obj.animation_data:
        obj.animation_data_clear()
        
    obj.rotation_mode = 'XYZ'
    ix = math.radians(tilt_deg)
    
    # Uranus and its moons rotate retrograde (clockwise)
    direction = -1.0 if retrograde else 1.0
    
    for frame in range(1, total_frames + 1):
        t       = (frame - 1) % period_frames
        angle_z = direction * (t / period_frames) * math.tau
        obj.rotation_euler = (ix, 0, angle_z)
        obj.keyframe_insert("rotation_euler", frame=frame)
        
    _set_linear(obj.animation_data.action if obj.animation_data else None)


def fix_mesh(obj):
    """Replace mesh with clean high-res UV sphere — smooth shading, no polygonal look."""
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

    # Auto smooth to eliminate any remaining faceting
    try:
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(30)
    except AttributeError:
        pass  # Blender 4.1+ handles this via geometry nodes / shade smooth


def hard_reset_object(obj):
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
    """Decorative orbit path — viewport only, hidden in render."""
    ring_name = f"Orbit_Ring_{name}"
    remove_if_exists(ring_name)
    bpy.ops.curve.primitive_nurbs_circle_add(radius=radius_bu, location=(0, 0, 0))
    ring = bpy.context.active_object
    ring.name              = ring_name
    ring.hide_render       = True
    ring.rotation_euler[0] = math.radians(tilt_deg)
    ring.data.bevel_depth  = 0.06 if RECORDING_MODE else 0.04
    ring.data.use_fill_caps = False

    mat_name = f"OrbitMat_{name}"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em  = mat.node_tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value    = (*color, 1.0)
    em.inputs["Strength"].default_value = 1.5
    mat.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    ring.data.materials.clear()
    ring.data.materials.append(mat)


def build_moon_material(obj, mat_name, tex_path,
                        roughness, sat, hue, bump_strength,
                        emit_color, emit_strength,
                        base_color_fallback):
    """
    Full PBR material with texture support.
    If texture missing → uses procedural fallback color.
    Smooth normals via bump map to avoid polygon look.
    """
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

    out  = N("ShaderNodeOutputMaterial", (900,   0))
    bsdf = N("ShaderNodeBsdfPrincipled", (500,   0))
    bsdf.inputs["Roughness"].default_value          = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.03
    bsdf.inputs["Metallic"].default_value           = 0.0

    tex_c   = N("ShaderNodeTexCoord", (-800,  0))
    mapping = N("ShaderNodeMapping",  (-600,  0))
    tex     = N("ShaderNodeTexImage", (-350, 120))

    tex_found = os.path.exists(tex_path)
    if tex_found:
        tex.image = bpy.data.images.load(tex_path, check_existing=True)
        print(f"      ✅ Texture loaded: {tex_path}")
    else:
        print(f"      ⚠  No texture at {tex_path} — using procedural fallback")

    hue_sat = N("ShaderNodeHueSaturation", (-80, 120))
    hue_sat.inputs["Hue"].default_value        = hue
    hue_sat.inputs["Saturation"].default_value = sat
    hue_sat.inputs["Value"].default_value      = 1.0

    # Bump map for surface detail — smooths out polygon faceting visually
    sep  = N("ShaderNodeSeparateColor", (-350, -150))
    bump = N("ShaderNodeBump",          ( 100, -150))
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.04

    # Small emission to keep moon visible on dark side
    emit   = N("ShaderNodeEmission", (100, -300))
    emit.inputs["Color"].default_value    = (*emit_color, 1.0)
    emit.inputs["Strength"].default_value = emit_strength

    add_sh = N("ShaderNodeAddShader", (700, -100))

    if tex_found:
        links.new(tex_c.outputs["UV"],       mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"],      hue_sat.inputs["Color"])
        links.new(hue_sat.outputs["Color"],  bsdf.inputs["Base Color"])
        links.new(tex.outputs["Color"],      sep.inputs["Color"])
        links.new(sep.outputs["Red"],        bump.inputs["Height"])
        links.new(bump.outputs["Normal"],    bsdf.inputs["Normal"])
    else:
        # Procedural fallback — noise texture for surface variation
        noise = N("ShaderNodeTexNoise", (-350, 120))
        noise.inputs["Scale"].default_value     = 8.0
        noise.inputs["Detail"].default_value    = 12.0
        noise.inputs["Roughness"].default_value = 0.65
        noise.inputs["Distortion"].default_value = 0.3

        ramp = N("ShaderNodeValToRGB", (-80, 220))
        cr   = ramp.color_ramp
        cr.interpolation = 'EASE'
        r, g, b = base_color_fallback
        # Darken shadow areas, lighten highlight areas of base color
        cr.elements[0].color = (r * 0.55, g * 0.55, b * 0.55, 1.0)
        cr.elements[1].color = (min(r * 1.25, 1.0), min(g * 1.25, 1.0), min(b * 1.25, 1.0), 1.0)
        e = cr.elements.new(0.45); e.color = (r * 0.85, g * 0.85, b * 0.85, 1.0)

        links.new(tex_c.outputs["UV"],       mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
        links.new(noise.outputs["Fac"],      ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"],     bsdf.inputs["Base Color"])
        links.new(noise.outputs["Fac"],      bump.inputs["Height"])
        links.new(bump.outputs["Normal"],    bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"],     add_sh.inputs[0])
    links.new(emit.outputs["Emission"], add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"], out.inputs["Surface"])


def setup_moon(moon, name, orbit_bu, moon_radius_bu, orbit_frames,
               tilt_deg, color, mat_name, tex_path,
               roughness, sat, hue, bump_strength,
               emit_color, emit_strength, base_color_fallback, spin_frames=None):
    """
    Full moon setup following Saturn moon reference pattern:
      1. hard_reset_object
      2. fix_mesh  (128×64 sphere, smooth shading, auto smooth)
      3. build_moon_material
      4. create Empty at (0,0,0)
      5. parent moon to empty at (orbit_bu, 0, 0)
      6. bake_rotation_z on empty (Orbital revolution)
      7. bake_rotation_z on moon (Local axial spin)
      8. make_orbit_ring
    """
    empty_name = f"Orbit_Empty_{name}"
    remove_if_exists(empty_name)

    print(f"\n   Setting up {name}...")

    hard_reset_object(moon)
    fix_mesh(moon)
    build_moon_material(moon, mat_name, tex_path,
                        roughness, sat, hue, bump_strength,
                        emit_color, emit_strength, base_color_fallback)

    # Create pivot empty at world origin
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.0))
    empty = bpy.context.active_object
    empty.name           = empty_name
    empty.rotation_euler = (0.0, 0.0, 0.0)
    empty.location       = (0.0, 0.0, 0.0)

    # Parent moon to empty, position at orbit radius
    bpy.ops.object.select_all(action='DESELECT')
    moon.parent                = empty
    moon.matrix_parent_inverse = Matrix.Identity(4)
    moon.location              = (orbit_bu, 0.0, 0.0)
    moon.rotation_euler        = (0.0, 0.0, 0.0)
    moon.scale                 = (moon_radius_bu, moon_radius_bu, moon_radius_bu)

    # Bake orbit animation on the empty (Retrograde)
    bake_rotation_z(empty, orbit_frames, tilt_deg, ANIM_END, retrograde=True)
    
    # Bake independent local spin on the moon itself (Retrograde)
    if spin_frames is not None:
        bake_rotation_z(moon, spin_frames, 0.0, ANIM_END, retrograde=True)

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

    titania = bpy.data.objects.get("Titania")
    oberon  = bpy.data.objects.get("Oberon")

    missing = [n for n, o in [("Titania", titania), ("Oberon", oberon)] if o is None]
    if missing:
        raise RuntimeError(
            f"❌  Missing objects: {missing}\n"
            f"    Create UV Sphere objects with those exact names and re-run."
        )

    # ── TITANIA ───────────────────────────────────────────────────────────────
    setup_moon(
        moon=titania, name="Titania",
        orbit_bu=TITANIA_ORBIT_BU, moon_radius_bu=TITANIA_RADIUS_BU,
        orbit_frames=TITANIA_ORBIT_FRAMES, tilt_deg=TITANIA_TILT_DEG,
        color=(0.75, 0.85, 0.90),           
        mat_name="Titania_Mat", tex_path=TITANIA_TEX,
        roughness=0.92,                     
        sat=0.45,                           
        hue=0.54,                           
        bump_strength=0.55,                 
        emit_color=(0.72, 0.80, 0.85),      
        emit_strength=0.008,
        base_color_fallback=(0.58, 0.65, 0.70), 
        spin_frames=TITANIA_SPIN_FRAMES
    )

    # ── OBERON ────────────────────────────────────────────────────────────────
    setup_moon(
        moon=oberon, name="Oberon",
        orbit_bu=OBERON_ORBIT_BU, moon_radius_bu=OBERON_RADIUS_BU,
        orbit_frames=OBERON_ORBIT_FRAMES, tilt_deg=OBERON_TILT_DEG,
        color=(0.80, 0.68, 0.55),           
        mat_name="Oberon_Mat", tex_path=OBERON_TEX,
        roughness=0.95,                     
        sat=0.60,                           
        hue=0.56,                           
        bump_strength=0.70,                 
        emit_color=(0.55, 0.45, 0.35),      
        emit_strength=0.005,
        base_color_fallback=(0.42, 0.35, 0.28), 
        spin_frames=OBERON_SPIN_FRAMES
    )

    scene.frame_set(1)

    print(f"\n🌀 Uranus moon system ready!")
    print(f"   Titania: {TITANIA_ORBIT_BU:.1f} BU  ({TITANIA_ORBIT_FRAMES} frames/orbit)")
    print(f"   Oberon:  {OBERON_ORBIT_BU:.1f} BU  ({OBERON_ORBIT_FRAMES} frames/orbit)")
    print(f"   Mode: {'RECORDING (compressed)' if RECORDING_MODE else 'REALISTIC'}")
    print(f"   📷 Camera tip: ~80 BU away, FOV ~50°")
    print(f"   Press Space to play ▶")
    print(f"   NOTE: Place textures at:")
    print(f"         {TITANIA_TEX}")
    print(f"         {OBERON_TEX}")


setup()