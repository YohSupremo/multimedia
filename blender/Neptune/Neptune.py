"""
Neptune — Realistic with Rings (Texture Loader + Ring Rotation)
==============================
Blender 4+/5
"""

import bpy
import math
from mathutils import Matrix

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

NEPTUNE_RADIUS_BU   = 7.60          # Neptune ~3.9× Earth; slightly smaller than Uranus
NEPTUNE_TILT_DEG    = 0.0           # Flat — no tilt (upright on X axis)
NEPTUNE_SPIN_FRAMES = 90            # ~16h rotation period (fastest rotation in solar system)
RING_ORBIT_FRAMES   = 140           # Adjust for how fast you want the rings to orbit

SEGMENTS = 128
RINGS    = 64
ANIM_END = 250

TEXTURE_BASE = r"C:\Users\kelly\Downloads\Blender\textures"
NEPTUNE_TEX  = TEXTURE_BASE + r"\neptune.jpg"

# ─────────────────────────────────────────────────────────────────────────────
# NEPTUNE RING SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

RING_BANDS = [
    # (inner_bu, outer_bu,  color_RGBA,                     emit_strength)
    (12.00, 13.40, (0.02, 0.02, 0.03, 0.18), 0.0), # Galle ring
    (15.80, 16.10, (0.03, 0.03, 0.04, 0.72), 0.0), # Le Verrier ring
    (16.10, 17.20, (0.02, 0.02, 0.03, 0.22), 0.0), # Lassell ring
    (17.20, 17.50, (0.03, 0.03, 0.04, 0.65), 0.0), # Arago ring
    (18.80, 19.20, (0.06, 0.06, 0.09, 0.90), 0.0), # Adams ring
]

RING_BAND_NAMES = [
    "NRing_Galle",
    "NRing_LeVerrier",
    "NRing_Lassell",
    "NRing_Arago",
    "NRing_Adams",
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


def bake_rotation(obj, period_frames, tilt_deg, total_frames):
    """
    Spins around Z axis, Prograde (Counter-Clockwise).
    """
    obj.animation_data_clear()
    obj.rotation_mode = 'XYZ'
    tilt_x = math.radians(tilt_deg)
    for frame in range(1, total_frames + 1):
        t       = (frame - 1) % period_frames
        angle_z = (t / period_frames) * math.tau
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
# NEPTUNE MATERIAL
# ─────────────────────────────────────────────────────────────────────────────

def build_neptune_material(obj):
    import os

    mat_name = "Neptune_Mat"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    def N(t, loc):
        n = nodes.new(t); n.location = loc; return n

    out  = N("ShaderNodeOutputMaterial", (1200, 0))
    bsdf = N("ShaderNodeBsdfPrincipled", (800,  0))
    bsdf.inputs["Roughness"].default_value          = 0.80
    bsdf.inputs["Specular IOR Level"].default_value = 0.08   
    bsdf.inputs["Metallic"].default_value           = 0.0

    if os.path.exists(NEPTUNE_TEX):
        print(f"   ✅ Neptune texture loaded")

        tex_c   = N("ShaderNodeTexCoord", (-900, 0))
        mapping = N("ShaderNodeMapping",  (-700, 0))
        tex     = N("ShaderNodeTexImage", (-480, 120))
        tex.image = bpy.data.images.load(NEPTUNE_TEX, check_existing=True)

        rgb_to_bw = N("ShaderNodeRGBToBW", (-220, 120))

        ramp = N("ShaderNodeValToRGB", (20, 120))
        cr = ramp.color_ramp
        cr.interpolation = 'EASE'
        cr.elements[0].position = 0.0; cr.elements[0].color = (0.01, 0.08, 0.45, 1.0)  
        cr.elements[1].position = 1.0; cr.elements[1].color = (0.04, 0.28, 0.82, 1.0)  
        e = cr.elements.new(0.30); e.color = (0.02, 0.14, 0.58, 1.0)                   
        e = cr.elements.new(0.65); e.color = (0.03, 0.22, 0.72, 1.0)                   

        bump = N("ShaderNodeBump", (400, -150))
        bump.inputs["Strength"].default_value = 0.18
        bump.inputs["Distance"].default_value = 0.012

        links.new(tex_c.outputs["UV"],       mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"],      rgb_to_bw.inputs["Color"])
        links.new(rgb_to_bw.outputs["Val"],  ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"],     bsdf.inputs["Base Color"])
        links.new(rgb_to_bw.outputs["Val"],  bump.inputs["Height"])
        links.new(bump.outputs["Normal"],    bsdf.inputs["Normal"])
        links.new(bsdf.outputs["BSDF"],      out.inputs["Surface"])

    else:
        print(f"   ⚠  Texture not found: {NEPTUNE_TEX} — using procedural fallback")

        tex_c   = N("ShaderNodeTexCoord",    (-900, 0))
        sep_xyz = N("ShaderNodeSeparateXYZ", (-700, 0))

        ramp_lat = N("ShaderNodeValToRGB", (-460, 60))
        cr = ramp_lat.color_ramp
        cr.interpolation = 'EASE'
        cr.elements[0].position = 0.0; cr.elements[0].color = (0.03, 0.06, 0.36, 1.0)  
        cr.elements[1].position = 1.0; cr.elements[1].color = (0.07, 0.22, 0.68, 1.0)  
        e = cr.elements.new(0.35); e.color = (0.04, 0.11, 0.50, 1.0)                   
        e = cr.elements.new(0.70); e.color = (0.06, 0.18, 0.62, 1.0)                   

        math_abs = N("ShaderNodeMath", (-640, -60))
        math_abs.operation = 'ABSOLUTE'

        math_inv = N("ShaderNodeMath", (-440, -60))
        math_inv.operation = 'SUBTRACT'
        math_inv.inputs[0].default_value = 1.0

        wave = N("ShaderNodeTexWave", (-700, -200))
        wave.wave_type       = 'BANDS'
        wave.bands_direction = 'Y'
        wave.inputs["Scale"].default_value        = 10.0   
        wave.inputs["Distortion"].default_value   = 1.20   
        wave.inputs["Detail"].default_value       = 4.0
        wave.inputs["Detail Scale"].default_value = 2.0
        wave.inputs["Detail Roughness"].default_value = 0.65

        noise_gds = N("ShaderNodeTexNoise", (-700, -400))
        noise_gds.inputs["Scale"].default_value     = 1.8   
        noise_gds.inputs["Detail"].default_value    = 3.0
        noise_gds.inputs["Roughness"].default_value = 0.55
        noise_gds.inputs["Distortion"].default_value = 0.4

        ramp_gds = N("ShaderNodeValToRGB", (-460, -400))
        cr_g = ramp_gds.color_ramp
        cr_g.interpolation = 'EASE'
        cr_g.elements[0].position = 0.0; cr_g.elements[0].color = (0.02, 0.04, 0.25, 1.0)  
        cr_g.elements[1].position = 1.0; cr_g.elements[1].color = (0.07, 0.22, 0.68, 1.0)  

        mix_bands = N("ShaderNodeMixRGB", (-180, -100))
        mix_bands.blend_type = 'MIX'
        mix_bands.inputs["Fac"].default_value = 0.20   

        mix_gds = N("ShaderNodeMixRGB", (60, -200))
        mix_gds.blend_type = 'MIX'
        mix_gds.inputs["Fac"].default_value = 0.18   

        bump = N("ShaderNodeBump", (400, -300))
        bump.inputs["Strength"].default_value = 0.20
        bump.inputs["Distance"].default_value = 0.015

        mix_bump_src = N("ShaderNodeMixRGB", (160, -350))
        mix_bump_src.blend_type = 'ADD'
        mix_bump_src.inputs["Fac"].default_value = 0.5

        links.new(tex_c.outputs["Normal"],     sep_xyz.inputs["Vector"])
        links.new(sep_xyz.outputs["Y"],        math_abs.inputs[0])
        links.new(math_abs.outputs["Value"],   math_inv.inputs[1])
        links.new(math_inv.outputs["Value"],   ramp_lat.inputs["Fac"])

        links.new(tex_c.outputs["Normal"],     wave.inputs["Vector"])
        links.new(tex_c.outputs["Normal"],     noise_gds.inputs["Vector"])

        links.new(ramp_lat.outputs["Color"],   mix_bands.inputs["Color1"])
        links.new(wave.outputs["Color"],       mix_bands.inputs["Color2"])

        links.new(noise_gds.outputs["Fac"],    ramp_gds.inputs["Fac"])
        links.new(mix_bands.outputs["Color"],  mix_gds.inputs["Color1"])
        links.new(ramp_gds.outputs["Color"],   mix_gds.inputs["Color2"])

        links.new(mix_gds.outputs["Color"],    bsdf.inputs["Base Color"])

        links.new(wave.outputs["Color"],       mix_bump_src.inputs["Color1"])
        links.new(noise_gds.outputs["Color"],  mix_bump_src.inputs["Color2"])
        links.new(mix_bump_src.outputs["Color"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"],      bsdf.inputs["Normal"])
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

    try:
        mat.surface_render_method = 'BLENDED'
    except AttributeError:
        try:
            mat.blend_method = 'BLEND'
        except AttributeError:
            pass

    r, g, b, a = color_rgba

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    def N(t, loc):
        n = nodes.new(t); n.location = loc; return n

    out  = N("ShaderNodeOutputMaterial", (700, 0))

    transparent = N("ShaderNodeBsdfTransparent", (-100, 100))
    transparent.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)

    diffuse = N("ShaderNodeBsdfDiffuse", (-100, -60))
    diffuse.inputs["Roughness"].default_value = 1.0

    # ── Added dust texture so Ring Orbit is visible ──
    tex_coord = N("ShaderNodeTexCoord", (-500, -60))
    noise = N("ShaderNodeTexNoise", (-300, -60))
    noise.inputs["Scale"].default_value = 150.0
    noise.inputs["Detail"].default_value = 15.0
    
    mix_color = N("ShaderNodeMixRGB", (-100, -200))
    mix_color.inputs["Color1"].default_value = (r * 0.4, g * 0.4, b * 0.4, 1.0)
    mix_color.inputs["Color2"].default_value = (r * 0.1, g * 0.1, b * 0.1, 1.0) # Darker dust
    
    links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], mix_color.inputs["Fac"])
    links.new(mix_color.outputs["Color"], diffuse.inputs["Color"])
    # ──────────────────────────────────────────────────────

    mix_shader = N("ShaderNodeMixShader", (260, 0))
    mix_shader.inputs["Fac"].default_value = a   # alpha drives transparency

    links.new(transparent.outputs["BSDF"],  mix_shader.inputs[1])
    links.new(diffuse.outputs["BSDF"],      mix_shader.inputs[2])
    links.new(mix_shader.outputs["Shader"], out.inputs["Surface"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)

    obj.location       = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale          = (1.0, 1.0, 1.0)

    return obj


def build_ring_system():
    for n in RING_BAND_NAMES:
        remove_if_exists(n)
    remove_if_exists("Neptune_Ring_Root")

    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    ring_root = bpy.context.object
    ring_root.name = "Neptune_Ring_Root"
    ring_root.rotation_euler = (0.0, 0.0, 0.0)  

    for i, (inner_bu, outer_bu, color, emit) in enumerate(RING_BANDS):
        band_obj = make_ring_band(RING_BAND_NAMES[i], inner_bu, outer_bu, color, emit)
        band_obj.parent = ring_root
        band_obj.matrix_parent_inverse = Matrix.Identity(4)
        print(f"   ✅ {RING_BAND_NAMES[i]}: {inner_bu:.2f}–{outer_bu:.2f} BU")

    # ── Animate the entire ring system to orbit counter-clockwise! ──
    bake_rotation(ring_root, RING_ORBIT_FRAMES, NEPTUNE_TILT_DEG, ANIM_END)


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
    add_sun("Light_Key",  2.80, (0.82, 0.90, 1.00), rx=-25, ry=0, rz=-50, shadow=True)
    add_sun("Light_Fill", 0.03, (0.40, 0.55, 0.90), rx=20,  ry=0, rz=140)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def setup():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    neptune = bpy.data.objects.get("Neptune")
    if neptune is None:
        raise RuntimeError("❌ No object named 'Neptune' found in scene!")

    print("🔵 Building Neptune...")
    setup_lighting()

    neptune.constraints.clear()
    neptune.animation_data_clear()
    if neptune.parent:
        bpy.context.view_layer.objects.active = neptune
        bpy.ops.object.select_all(action='DESELECT')
        neptune.select_set(True)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    neptune.location              = (0.0, 0.0, 0.0)
    neptune.rotation_euler        = (0.0, 0.0, 0.0)
    neptune.scale                 = (1.0, 1.0, 1.0)
    neptune.matrix_parent_inverse = Matrix.Identity(4)

    rebuild_sphere(neptune)
    neptune.scale = (NEPTUNE_RADIUS_BU, NEPTUNE_RADIUS_BU, NEPTUNE_RADIUS_BU * 0.983)

    build_neptune_material(neptune)

    # Spin animation
    bake_rotation(neptune, NEPTUNE_SPIN_FRAMES, NEPTUNE_TILT_DEG, ANIM_END)

    build_ring_system()

    scene.frame_set(1)

    print()
    print("✅ Neptune complete!")

setup()