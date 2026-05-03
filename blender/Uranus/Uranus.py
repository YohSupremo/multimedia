"""
Uranus — Realistic with Rings (Retrograde Spin + Orbit)
==============================
Blender 4+/5

Key differences from Saturn:
  - Uranus is ice-blue/cyan in color (pale blue-green)
  - Retrograde rotation: spins clockwise!
  - Rings orbit in the same retrograde direction
  - Rings are very dark (almost black/charcoal) — unlike Saturn's bright rings
  - 13 known rings, narrow and dark (mostly epsilon ring is notable)
  - Procedural material: smooth featureless blue-green globe
  - Slightly oblate (flattened poles)
  - Cooler blue-white key light to match the planet's icy feel
"""

import bpy
import math
from mathutils import Matrix

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

URANUS_RADIUS_BU   = 8.00          # Uranus is ~4× Earth radius; scale to taste
URANUS_TILT_DEG    = 0.0           # Kept flat/horizontal as requested!
URANUS_SPIN_FRAMES = 100           # ~17h rotation period (faster than Saturn)
RING_ORBIT_FRAMES  = 160           # Adjust for how fast you want the rings to orbit

SEGMENTS = 128
RINGS    = 64
ANIM_END = 250

TEXTURE_BASE = r"C:\Users\kelly\Downloads\Blender\textures"
URANUS_TEX   = TEXTURE_BASE + r"\uranus.jpg"

# ─────────────────────────────────────────────────────────────────────────────
# URANUS RING SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

RING_BANDS = [
    # (inner_bu, outer_bu,  color_RGBA,                     emit_strength)
    (12.50, 13.20, (0.02, 0.02, 0.02, 0.15), 0.0), # Zeta ring
    (13.30, 13.44, (0.03, 0.03, 0.03, 0.70), 0.0), # 6 ring
    (13.54, 13.68, (0.03, 0.03, 0.03, 0.65), 0.0), # 5 ring
    (13.78, 13.92, (0.03, 0.03, 0.03, 0.62), 0.0), # 4 ring
    (14.10, 14.28, (0.04, 0.04, 0.04, 0.75), 0.0), # Alpha ring
    (14.44, 14.62, (0.04, 0.04, 0.04, 0.72), 0.0), # Beta ring
    (14.78, 14.92, (0.03, 0.03, 0.03, 0.60), 0.0), # Eta ring
    (15.04, 15.20, (0.04, 0.04, 0.04, 0.75), 0.0), # Gamma ring
    (15.36, 15.54, (0.04, 0.04, 0.04, 0.78), 0.0), # Delta ring
    (15.74, 15.86, (0.02, 0.02, 0.02, 0.30), 0.0), # Lambda ring
    (16.40, 16.96, (0.08, 0.08, 0.09, 0.92), 0.0), # Epsilon ring
    (18.40, 19.20, (0.02, 0.02, 0.02, 0.12), 0.0), # Nu ring
    (20.60, 21.80, (0.02, 0.02, 0.02, 0.08), 0.0), # Mu ring
]

RING_BAND_NAMES = [
    "URing_Zeta", "URing_6", "URing_5", "URing_4",
    "URing_Alpha", "URing_Beta", "URing_Eta", "URing_Gamma",
    "URing_Delta", "URing_Lambda", "URing_Epsilon",
    "URing_Nu", "URing_Mu",
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


def bake_rotation_x(obj, period_frames, tilt_deg, total_frames, retrograde=True):
    """
    Bakes rotation around the Z-axis while maintaining the X tilt.
    Retrograde (clockwise) rotation is applied via negative angle progression.
    """
    obj.animation_data_clear()
    obj.rotation_mode = 'XYZ'
    tilt_x = math.radians(tilt_deg)
    
    # Uranus spins retrograde (clockwise)
    direction = -1.0 if retrograde else 1.0
    
    for frame in range(1, total_frames + 1):
        t       = (frame - 1) % period_frames
        angle_z = direction * (t / period_frames) * math.tau
        obj.rotation_euler = (tilt_x, 0.0, angle_z)
        obj.keyframe_insert("rotation_euler", frame=frame)
        
    _set_linear(obj.animation_data.action if obj.animation_data else None)


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
# URANUS MATERIAL
# ─────────────────────────────────────────────────────────────────────────────

def build_uranus_material(obj):
    import os

    mat_name = "Uranus_Mat"
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
    bsdf.inputs["Roughness"].default_value          = 0.85
    bsdf.inputs["Specular IOR Level"].default_value = 0.05
    bsdf.inputs["Metallic"].default_value           = 0.0

    tex_c   = N("ShaderNodeTexCoord", (-900, 0))
    mapping = N("ShaderNodeMapping",  (-700, 0))
    tex     = N("ShaderNodeTexImage", (-480, 120))

    if os.path.exists(URANUS_TEX):
        tex.image = bpy.data.images.load(URANUS_TEX, check_existing=True)
        print(f"   ✅ Uranus texture loaded")

        hue_sat = N("ShaderNodeHueSaturation", (-220, 120))
        hue_sat.inputs["Hue"].default_value        = 0.50
        hue_sat.inputs["Saturation"].default_value = 2.20
        hue_sat.inputs["Value"].default_value      = 0.85

        ramp = N("ShaderNodeValToRGB", (20, 120))
        cr = ramp.color_ramp
        cr.interpolation = 'EASE'
        cr.elements[0].position = 0.0; cr.elements[0].color = (0.18, 0.50, 0.62, 1.0)
        cr.elements[1].position = 1.0; cr.elements[1].color = (0.48, 0.82, 0.88, 1.0)
        e = cr.elements.new(0.50);     e.color = (0.32, 0.68, 0.78, 1.0)

        mix = N("ShaderNodeMixRGB", (260, 120))
        mix.blend_type = 'MULTIPLY'
        mix.inputs["Fac"].default_value = 0.45

        bump = N("ShaderNodeBump", (300, -150))
        bump.inputs["Strength"].default_value = 0.08
        bump.inputs["Distance"].default_value = 0.01

        sep = N("ShaderNodeSeparateColor", (-480, -150))

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
        print(f"   ⚠  Texture not found: {URANUS_TEX} — using procedural fallback")
        tex_c2  = N("ShaderNodeTexCoord",  (-500,  0))
        sep_xyz = N("ShaderNodeSeparateXYZ", (-300, 0))

        ramp = N("ShaderNodeValToRGB", (-80, 0))
        cr = ramp.color_ramp
        cr.interpolation = 'EASE'
        cr.elements[0].position = 0.0; cr.elements[0].color = (0.18, 0.50, 0.64, 1.0)
        cr.elements[1].position = 1.0; cr.elements[1].color = (0.45, 0.80, 0.88, 1.0)
        e = cr.elements.new(0.45);     e.color = (0.30, 0.66, 0.78, 1.0)
        e = cr.elements.new(0.70);     e.color = (0.38, 0.74, 0.84, 1.0)

        math_abs  = N("ShaderNodeMath", (100, 0))
        math_abs.operation = 'ABSOLUTE'

        math_inv  = N("ShaderNodeMath", (260, 0))
        math_inv.operation = 'SUBTRACT'
        math_inv.inputs[0].default_value = 1.0

        wave = N("ShaderNodeTexWave", (-500, -200))
        wave.wave_type       = 'BANDS'
        wave.bands_direction = 'Y'
        wave.inputs["Scale"].default_value        = 6.0
        wave.inputs["Distortion"].default_value   = 0.3
        wave.inputs["Detail"].default_value       = 2.0
        wave.inputs["Detail Scale"].default_value = 1.0

        mix_bands = N("ShaderNodeMixRGB", (430, -100))
        mix_bands.blend_type = 'MIX'
        mix_bands.inputs["Fac"].default_value = 0.08

        links.new(tex_c2.outputs["Normal"],    sep_xyz.inputs["Vector"])
        links.new(sep_xyz.outputs["Y"],        math_abs.inputs[0])
        links.new(math_abs.outputs["Value"],   math_inv.inputs[1])
        links.new(math_inv.outputs["Value"],   ramp.inputs["Fac"])
        links.new(tex_c2.outputs["Normal"],    wave.inputs["Vector"])
        links.new(ramp.outputs["Color"],       mix_bands.inputs["Color1"])
        links.new(wave.outputs["Color"],       mix_bands.inputs["Color2"])
        links.new(mix_bands.outputs["Color"],  bsdf.inputs["Base Color"])
        links.new(bsdf.outputs["BSDF"],        out.inputs["Surface"])


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

    out  = N("ShaderNodeOutputMaterial", (500, 0))
    bsdf = N("ShaderNodeBsdfPrincipled", (200, 0))
    bsdf.inputs["Base Color"].default_value         = (r, g, b, 1.0)
    bsdf.inputs["Alpha"].default_value              = a
    bsdf.inputs["Roughness"].default_value          = 1.00
    bsdf.inputs["Specular IOR Level"].default_value = 0.00
    bsdf.inputs["Metallic"].default_value           = 0.0
    
    try:
        bsdf.inputs["Emission Color"].default_value    = (r * 0.6, g * 0.6, b * 0.6, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 0.08
    except KeyError:
        bsdf.inputs["Emission"].default_value          = (r * 0.6, g * 0.6, b * 0.6, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 0.08

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)

    obj.location       = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale          = (1.0, 1.0, 1.0)

    return obj


def build_ring_system():
    for n in RING_BAND_NAMES:
        remove_if_exists(n)
    remove_if_exists("Uranus_Ring_Root")

    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    ring_root = bpy.context.object
    ring_root.name = "Uranus_Ring_Root"
    ring_root.rotation_euler = (0.0, 0.0, 0.0)

    for i, (inner_bu, outer_bu, color, emit) in enumerate(RING_BANDS):
        band_obj = make_ring_band(RING_BAND_NAMES[i], inner_bu, outer_bu, color, emit)
        band_obj.parent = ring_root
        band_obj.matrix_parent_inverse = Matrix.Identity(4)
        print(f"   ✅ {RING_BAND_NAMES[i]}: {inner_bu:.2f}–{outer_bu:.2f} BU")

    # Animate the entire ring system to rotate retrograde!
    bake_rotation_x(ring_root, RING_ORBIT_FRAMES, URANUS_TILT_DEG, ANIM_END, retrograde=True)


# ─────────────────────────────────────────────────────────────────────────────
# LIGHTING
# ─────────────────────────────────────────────────────────────────────────────

def add_sun(name, energy, color, rx, ry, rz, shadow=False):
    remove_light(name)
    ld            = bpy.data.lights.new(name=name, type='SUN')
    ld.energy     = energy
    ld.color      = color
    ld.angle      = math.radians(2.0)
    ld.use_shadow = shadow
    obj = bpy.data.objects.new(name=name, object_data=ld)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    return obj

OLD_LIGHTS = [
    "Light_Fill_Right", "Light_Fill_Bottom", "Light_Fill_Top",
    "Light_Fill_Back",  "Light_Fill_Left",   "Light_Rim",
    "Light_Key",        "Light_Fill",
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
    add_sun("Light_Key",  3.50, (0.88, 0.94, 1.00), rx=-30, ry=0, rz=-50, shadow=True)
    add_sun("Light_Fill", 0.04, (0.50, 0.60, 0.80), rx=20,  ry=0, rz=140)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def setup():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    uranus = bpy.data.objects.get("Uranus")
    if uranus is None:
        raise RuntimeError("❌ No object named 'Uranus' found in scene!")

    print("🌀 Building Uranus...")
    setup_lighting()

    uranus.constraints.clear()
    uranus.animation_data_clear()
    if uranus.parent:
        bpy.context.view_layer.objects.active = uranus
        bpy.ops.object.select_all(action='DESELECT')
        uranus.select_set(True)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    uranus.location              = (0.0, 0.0, 0.0)
    uranus.rotation_euler        = (0.0, 0.0, 0.0)
    uranus.scale                 = (1.0, 1.0, 1.0)
    uranus.matrix_parent_inverse = Matrix.Identity(4)

    rebuild_sphere(uranus)
    uranus.scale = (URANUS_RADIUS_BU, URANUS_RADIUS_BU, URANUS_RADIUS_BU * 0.977)

    build_uranus_material(uranus)

    # Spin animation — Retrograde spin
    bake_rotation_x(uranus, URANUS_SPIN_FRAMES, URANUS_TILT_DEG, ANIM_END, retrograde=True)

    build_ring_system()

    scene.frame_set(1)

    print()
    print("✅ Uranus complete!")
    print(f"   Tilt:        {URANUS_TILT_DEG}° (Flat!)")
    print(f"   Rotation:    Retrograde (Clockwise)")
    print(f"   Uranus:      {URANUS_RADIUS_BU} BU radius")
    print(f"   Polar scale: {URANUS_RADIUS_BU * 0.977:.3f} BU (slightly oblate)")
    print(f"   Rings:       {len(RING_BANDS)} bands orbiting retrograde")
    print("   NOTE: Rename your Blender object to 'Uranus' before running!")


setup()