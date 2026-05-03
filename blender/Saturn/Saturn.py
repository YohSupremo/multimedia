"""
Saturn — Realistic with Rings  (GOLDEN V2 + TILT/SPIN FIX)
============================================================
Blender 5.1.x compatible

Changes in this version:
  1. Saturn axial tilt set to 26.73° (accurate real-world value)
  2. Ring planes tilt to match Saturn's axial tilt exactly
  3. Spin animation rotates around Saturn's LOCAL tilted Z axis
     using a parent Empty as a pivot — avoids gimbal lock issues
  4. Ring system parented to same spin pivot so rings co-rotate correctly
  5. GOLDEN V2: Deep saturated ring colors, emission on rings for viewport,
     strong contrast on Saturn bands, warmer key light
"""

import bpy
import math
from mathutils import Matrix, Euler

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

SATURN_RADIUS_BU   = 9.45

# Real Saturn axial tilt = 26.73°
SATURN_TILT_DEG    = 0.0

# How many frames for one full rotation (lower = faster spin)
SATURN_SPIN_FRAMES = 120

SEGMENTS = 128
RINGS    = 64
ANIM_END = 250

TEXTURE_BASE = r"C:\Users\kelly\Downloads\Blender\textures"
SATURN_TEX   = TEXTURE_BASE + r"\saturn.jpg"

# Ring sizes in world-space BU — GOLDEN V2
# Colors are intentionally deep/saturated to fight Blender's gamma correction
# emit_strength > 0 ensures color shows in viewport preview mode too
RING_BANDS = [
    # (inner_bu, outer_bu,  color_RGBA,                      emit_strength)
    (10.49, 11.72, (0.12, 0.07, 0.01, 0.55), 0.08),   # D — very dark dust
    (11.72, 14.36, (0.28, 0.14, 0.02, 0.85), 0.10),   # C — deep dark brown
    (14.36, 18.43, (0.72, 0.42, 0.04, 1.00), 0.18),   # B — rich amber-gold ★ (widest, brightest)
    (18.43, 19.09, (0.00, 0.00, 0.00, 0.04), 0.00),   # Cassini gap — nearly invisible
    (19.09, 21.45, (0.55, 0.30, 0.04, 0.95), 0.14),   # A — dark warm gold
    (22.02, 22.31, (0.80, 0.58, 0.10, 0.92), 0.20),   # F — bright thin gold
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def remove_if_exists(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)


def remove_light(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
    ld = bpy.data.lights.get(name)
    if ld:
        bpy.data.lights.remove(ld)


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


def rebuild_sphere(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
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


def apply_material_transparency(mat, alpha):
    try:
        if alpha < 0.99:
            mat.surface_render_method = 'DITHERED'
        else:
            mat.surface_render_method = 'BLENDED'
        return
    except AttributeError:
        pass
    try:
        if alpha < 0.99:
            mat.blend_method = 'BLEND'
        else:
            mat.blend_method = 'OPAQUE'
        return
    except AttributeError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# SPIN PIVOT EMPTY
# ─────────────────────────────────────────────────────────────────────────────

def create_spin_pivot():
    """Create or reset the Saturn_Pivot empty."""
    remove_if_exists("Saturn_Pivot")

    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    pivot = bpy.context.object
    pivot.name = "Saturn_Pivot"

    pivot.rotation_mode   = 'XYZ'
    pivot.rotation_euler  = (math.radians(SATURN_TILT_DEG), 0.0, 0.0)
    pivot.scale           = (1.0, 1.0, 1.0)
    pivot.location        = (0.0, 0.0, 0.0)

    return pivot


def bake_pivot_spin(pivot, period_frames, total_frames):
    """Animate pivot's local Z (rotation_euler[2]) for continuous spin."""
    pivot.animation_data_clear()
    pivot.rotation_mode = 'XYZ'

    for frame in range(1, total_frames + 1):
        t       = (frame - 1) % period_frames
        angle_z = (t / period_frames) * math.tau
        pivot.rotation_euler = (math.radians(SATURN_TILT_DEG), 0.0, angle_z)
        pivot.keyframe_insert("rotation_euler", frame=frame)

    _set_linear(pivot.animation_data.action if pivot.animation_data else None)
    print(f"   ✅ Spin baked: {total_frames} frames, period={period_frames} frames")


def parent_to_pivot(child, pivot):
    """Parent child object to pivot, keeping child at world origin with no offset."""
    child.parent                = pivot
    child.matrix_parent_inverse = pivot.matrix_world.inverted()


# ─────────────────────────────────────────────────────────────────────────────
# SATURN MATERIAL — GOLDEN UPDATE
# ─────────────────────────────────────────────────────────────────────────────

def build_saturn_material(obj):
    import os

    mat_name = "Saturn_Mat"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    def N(t, loc):
        n = nodes.new(t); n.location = loc; return n

    out  = N("ShaderNodeOutputMaterial", (1100, 0))
    bsdf = N("ShaderNodeBsdfPrincipled", (700,  0))
    bsdf.inputs["Roughness"].default_value          = 0.88
    bsdf.inputs["Specular IOR Level"].default_value = 0.04
    bsdf.inputs["Metallic"].default_value           = 0.0

    tex_c   = N("ShaderNodeTexCoord", (-900, 0))
    mapping = N("ShaderNodeMapping",  (-700, 0))
    tex     = N("ShaderNodeTexImage", (-480, 120))

    if os.path.exists(SATURN_TEX):
        tex.image = bpy.data.images.load(SATURN_TEX, check_existing=True)
        print(f"   ✅ Saturn texture loaded")

        hue_sat = N("ShaderNodeHueSaturation", (-220, 120))
        # Deep gold: high saturation, warm hue shift
        hue_sat.inputs["Hue"].default_value        = 0.57
        hue_sat.inputs["Saturation"].default_value = 3.80   # very saturated
        hue_sat.inputs["Value"].default_value      = 0.95

        ramp = N("ShaderNodeValToRGB", (20, 120))
        cr = ramp.color_ramp
        cr.interpolation = 'EASE'
        # Deep contrast: very dark shadows, very bright gold peaks
        cr.elements[0].position = 0.0;  cr.elements[0].color = (0.10, 0.05, 0.00, 1.0)  # near-black shadow
        cr.elements[1].position = 1.0;  cr.elements[1].color = (1.00, 0.78, 0.18, 1.0)  # bright gold peak
        e = cr.elements.new(0.35);      e.color = (0.38, 0.20, 0.02, 1.0)  # dark amber band
        e = cr.elements.new(0.55);      e.color = (0.72, 0.48, 0.08, 1.0)  # mid gold
        e = cr.elements.new(0.75);      e.color = (0.90, 0.65, 0.14, 1.0)  # bright warm gold

        mix = N("ShaderNodeMixRGB", (260, 120))
        mix.blend_type = 'MULTIPLY'
        mix.inputs["Fac"].default_value = 0.65   # stronger multiply = more contrast

        sep  = N("ShaderNodeSeparateColor", (-480, -150))
        bump = N("ShaderNodeBump",          (300,  -150))
        bump.inputs["Strength"].default_value = 0.35
        bump.inputs["Distance"].default_value = 0.02

        links.new(tex_c.outputs["UV"],       mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"],      hue_sat.inputs["Color"])
        links.new(hue_sat.outputs["Color"],  ramp.inputs["Fac"])
        links.new(hue_sat.outputs["Color"],  mix.inputs["Color1"])
        links.new(ramp.outputs["Color"],     mix.inputs["Color2"])
        links.new(mix.outputs["Color"],      bsdf.inputs["Base Color"])
        links.new(tex.outputs["Color"],      sep.inputs["Color"])
        links.new(sep.outputs["Red"],        bump.inputs["Height"])
        links.new(bump.outputs["Normal"],    bsdf.inputs["Normal"])
        links.new(bsdf.outputs["BSDF"],      out.inputs["Surface"])

    else:
        print(f"   ⚠  Texture not found: {SATURN_TEX} — using procedural fallback")

        wave = N("ShaderNodeTexWave", (-300, 0))
        wave.wave_type        = 'BANDS'
        wave.bands_direction  = 'Y'
        wave.inputs["Scale"].default_value        = 9.0
        wave.inputs["Distortion"].default_value   = 3.0
        wave.inputs["Detail"].default_value       = 8.0
        wave.inputs["Detail Scale"].default_value = 2.5

        # GOLDEN UPDATE: richer gold procedural fallback
        ramp = N("ShaderNodeValToRGB", (0, 0))
        cr = ramp.color_ramp
        cr.elements[0].color    = (0.65, 0.42, 0.06, 1.0)   # warm dark gold
        cr.elements[1].color    = (1.00, 0.82, 0.28, 1.0)   # bright gold
        e = cr.elements.new(0.30); e.color = (0.48, 0.30, 0.05, 1.0)
        e = cr.elements.new(0.55); e.color = (0.90, 0.68, 0.18, 1.0)
        e = cr.elements.new(0.80); e.color = (0.78, 0.56, 0.14, 1.0)

        links.new(tex_c.outputs["UV"],       mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
        links.new(wave.outputs["Color"],     ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"],     bsdf.inputs["Base Color"])
        links.new(bsdf.outputs["BSDF"],      out.inputs["Surface"])


# ─────────────────────────────────────────────────────────────────────────────
# RING BANDS
# ─────────────────────────────────────────────────────────────────────────────

def make_ring_band(name, inner_bu, outer_bu, color_rgba, emit_strength):
    remove_if_exists(name)

    import bmesh

    mesh = bpy.data.meshes.new(name)
    obj  = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm        = bmesh.new()
    RING_SEGS = 256

    outer_verts = []
    inner_verts = []
    for i in range(RING_SEGS):
        angle = (i / RING_SEGS) * math.tau
        c, s  = math.cos(angle), math.sin(angle)
        outer_verts.append(bm.verts.new((c * outer_bu, s * outer_bu, 0.0)))
        inner_verts.append(bm.verts.new((c * inner_bu, s * inner_bu, 0.0)))

    bm.verts.ensure_lookup_table()

    for i in range(RING_SEGS):
        j = (i + 1) % RING_SEGS
        bm.faces.new([outer_verts[i], outer_verts[j],
                      inner_verts[j], inner_verts[i]])

    uv_layer = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for loop in face.loops:
            v     = loop.vert
            dist  = math.sqrt(v.co.x**2 + v.co.y**2)
            u     = (dist - inner_bu) / (outer_bu - inner_bu)
            angle = math.atan2(v.co.y, v.co.x) / math.tau
            loop[uv_layer].uv = (u, angle)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for poly in mesh.polygons:
        poly.use_smooth = True

    mat_name = f"RingMat_{name}"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes            = True
    mat.use_backface_culling = False

    r, g, b, a = color_rgba
    apply_material_transparency(mat, a)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    def N(t, loc):
        n = nodes.new(t); n.location = loc; return n

    out  = N("ShaderNodeOutputMaterial", (700, 0))
    mix  = N("ShaderNodeMixShader",      (480, 0))
    bsdf = N("ShaderNodeBsdfPrincipled", (200, 80))
    emit = N("ShaderNodeEmission",       (200, -120))

    bsdf.inputs["Base Color"].default_value         = (r, g, b, 1.0)
    bsdf.inputs["Alpha"].default_value              = a
    bsdf.inputs["Roughness"].default_value          = 0.92
    bsdf.inputs["Specular IOR Level"].default_value = 0.03
    bsdf.inputs["Metallic"].default_value           = 0.0

    # Emission so color is visible in solid/material preview viewport
    emit.inputs["Color"].default_value    = (r, g, b, 1.0)
    emit.inputs["Strength"].default_value = emit_strength

    # Blend: mostly BSDF for renders, tiny emit for viewport presence
    mix.inputs["Fac"].default_value = 0.12 if emit_strength > 0 else 0.0

    links.new(bsdf.outputs["BSDF"],   mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"],  out.inputs["Surface"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)

    obj.location       = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale          = (1.0, 1.0, 1.0)

    return obj


def build_ring_system(pivot):
    band_names = ["Ring_D", "Ring_C", "Ring_B", "Ring_Cassini", "Ring_A", "Ring_F"]
    for n in band_names:
        remove_if_exists(n)

    ring_objects = []
    for i, (inner_bu, outer_bu, color, emit) in enumerate(RING_BANDS):
        ring_obj = make_ring_band(band_names[i], inner_bu, outer_bu, color, emit)
        parent_to_pivot(ring_obj, pivot)
        ring_objects.append(ring_obj)
        print(f"   ✅ {band_names[i]}: {inner_bu:.2f}–{outer_bu:.2f} BU → parented to pivot")

    return ring_objects


# ─────────────────────────────────────────────────────────────────────────────
# LIGHTING
# ─────────────────────────────────────────────────────────────────────────────

def add_sun(name, energy, color, rx, ry, rz, shadow=False):
    remove_light(name)
    ld            = bpy.data.lights.new(name=name, type='SUN')
    ld.energy     = energy
    ld.color      = color
    ld.angle      = math.radians(3.0)
    ld.use_shadow = shadow
    obj = bpy.data.objects.new(name=name, object_data=ld)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    return obj


OLD_LIGHTS = [
    "Light_Fill_Right", "Light_Fill_Bottom", "Light_Fill_Top",
    "Light_Fill_Back",  "Light_Fill_Left",
    "Light_Key",        "Light_Fill",        "Light_Rim",
]


def set_black_background():
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    bg  = nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value    = (0.0, 0.0, 0.0, 1.0)
    bg.inputs["Strength"].default_value = 0.0
    links.new(bg.outputs["Background"], out.inputs["Surface"])


def setup_lighting():
    for lname in OLD_LIGHTS:
        remove_light(lname)

    set_black_background()

    # Warm golden key light + subtle warm rim to bring out gold tones
    add_sun("Light_Key",  4.50, (1.00, 0.85, 0.55), rx=-30, ry=0, rz=-50, shadow=True)
    add_sun("Light_Fill", 0.15, (0.60, 0.65, 0.80), rx=20,  ry=0, rz=140)
    add_sun("Light_Rim",  0.80, (1.00, 0.75, 0.40), rx=10,  ry=0, rz=80)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def setup():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    saturn = bpy.data.objects.get("Saturn")
    if saturn is None:
        raise RuntimeError("❌ No object named 'Saturn' found in scene!")

    print("🪐 Building Golden Saturn with accurate tilt + spin...")
    setup_lighting()

    # ── Clear any existing parent / animation on saturn ──────────────────────
    saturn.constraints.clear()
    saturn.animation_data_clear()
    if saturn.parent:
        bpy.context.view_layer.objects.active = saturn
        bpy.ops.object.select_all(action='DESELECT')
        saturn.select_set(True)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    # ── Rebuild Saturn mesh & scale ───────────────────────────────────────────
    saturn.location       = (0.0, 0.0, 0.0)
    saturn.rotation_euler = (0.0, 0.0, 0.0)
    saturn.scale          = (1.0, 1.0, 1.0)
    saturn.matrix_parent_inverse = Matrix.Identity(4)

    rebuild_sphere(saturn)
    # Oblate spheroid: equatorial > polar by ~10%
    saturn.scale = (SATURN_RADIUS_BU, SATURN_RADIUS_BU, SATURN_RADIUS_BU * 0.902)

    build_saturn_material(saturn)

    # ── Create the tilt+spin pivot ────────────────────────────────────────────
    remove_if_exists("Saturn_Pivot")
    pivot = create_spin_pivot()

    # ── Animate the pivot spinning around its local (tilted) Z ───────────────
    bake_pivot_spin(pivot, SATURN_SPIN_FRAMES, ANIM_END)

    # ── Parent Saturn to pivot ────────────────────────────────────────────────
    parent_to_pivot(saturn, pivot)

    # ── Build rings, parented to same pivot ───────────────────────────────────
    build_ring_system(pivot)

    scene.frame_set(1)

    print()
    print("✅ Golden Saturn complete!")
    print(f"   Axial tilt:  {SATURN_TILT_DEG}° (accurate real-world value) ✅")
    print(f"   Spin period: {SATURN_SPIN_FRAMES} frames per rotation ✅")
    print(f"   Pivot:       'Saturn_Pivot' empty drives tilt + spin ✅")
    print(f"   Saturn:      {SATURN_RADIUS_BU} BU equatorial radius")
    print(f"   Ring inner:  {RING_BANDS[0][0]:.2f} BU")
    print(f"   Ring outer:  {RING_BANDS[-1][1]:.2f} BU")
    print(f"   Texture:     {SATURN_TEX}")
    print()
    print("   📷 TIP: Press Numpad 1 then orbit down ~25° to see the tilt!")
    print("   ▶ Run moon script next")


setup()