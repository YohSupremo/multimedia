"""
Debris_Belts.py
===============
Consolidated script that procedurally generates both the Asteroid Belt and the
Kuiper Belt.

Features:
- Keplerian orbital periods (inner rings orbit faster than outer rings).
- Keplarian 3D inclinations and nodal rotations for the Kuiper Belt (KBOs).
- Detailed organic tholin/rock/ice procedural shaders.
- Custom viewport labels with camera copy-rotation tracking.
"""

import bpy
import bmesh
import math
import random

# ──────────────────────────────────────────────────────────────────────────────
# GLOBAL ORRERY SYNC DEFINITIONS
# ──────────────────────────────────────────────────────────────────────────────
BASE_FRAMES   = 300
MARS_DIST     = 39.0
JUPITER_DIST  = 70.0
MARS_AU       = 1.52
JUPITER_AU    = 5.20

NEPTUNE_DIST  = 145.0
PLUTO_DIST    = 165.0
NEPTUNE_AU    = 30.07
PLUTO_AU      = 39.48

# ──────────────────────────────────────────────────────────────────────────────
# ASTEROID BELT CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
ASTEROID_COUNT       = 1000
LARGE_ASTEROID_SCALE = 0.60
ASTEROID_DUST_ALPHA  = 0.04
ASTEROID_TILT_DEG    = 1.7
ASTEROID_SEED        = 42
ASTEROID_SIZE_MIN    = 0.080
ASTEROID_SIZE_MAX    = 0.220
ASTEROID_THICKNESS   = 0.60

ASTEROID_INNER_BU = MARS_DIST + ((2.06 - MARS_AU) / (JUPITER_AU - MARS_AU)) * (JUPITER_DIST - MARS_DIST)
ASTEROID_OUTER_BU = MARS_DIST + ((3.27 - MARS_AU) / (JUPITER_AU - MARS_AU)) * (JUPITER_DIST - MARS_DIST)
ASTEROID_MID_BU   = MARS_DIST + ((2.77 - MARS_AU) / (JUPITER_AU - MARS_AU)) * (JUPITER_DIST - MARS_DIST)

NAMED_ASTEROIDS = [
    ("Ceres",   2.766, 0.50, (0.38, 0.38, 0.38, 1.0)),
    ("Vesta",   2.362, 0.30, (0.48, 0.48, 0.48, 1.0)),
    ("Pallas",  2.772, 0.24, (0.32, 0.32, 0.32, 1.0)),
    ("Hygiea",  3.142, 0.22, (0.24, 0.24, 0.24, 1.0)),
]

ASTEROID_COLOR_FAMILIES = [
    (0.55, (0.38, 0.38, 0.38, 1.0), 0.90),  # stony silicate
    (0.35, (0.22, 0.22, 0.22, 1.0), 0.95),  # carbonaceous
    (0.10, (0.42, 0.42, 0.42, 1.0), 0.80),  # metallic
]

# Kirkwood gaps: (center_bu, half_width_bu, rejection_strength)
def _ast_au_to_bu(au):
    return MARS_DIST + ((au - MARS_AU) / (JUPITER_AU - MARS_AU)) * (JUPITER_DIST - MARS_DIST)

AST_KIRKWOOD_GAPS = [
    (_ast_au_to_bu(2.50), 0.35, 1.00),  # 3:1
    (_ast_au_to_bu(2.82), 0.25, 0.80),  # 5:2
    (_ast_au_to_bu(2.96), 0.20, 0.70),  # 7:3
    (_ast_au_to_bu(3.27), 0.30, 1.00),  # 2:1
]

# ──────────────────────────────────────────────────────────────────────────────
# KUIPER BELT CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
KBO_COUNT            = 3000
LARGE_KBO_SCALE      = 0.50
KBO_DUST_ALPHA       = 0.04
KBO_SEED             = 137
KBO_SIZE_MIN         = 0.180
KBO_SIZE_MAX         = 0.450
KBO_THICKNESS        = 1.5

KBO_INNER_BU = 146.0
KBO_OUTER_BU = 205.0
KBO_MID_BU   = 175.0

NAMED_KBOS = [
    # (name, semi_major_au, size_bu, tilt_deg, phase_offset, color_RGBA, roughness, scale_tuple)
    ("Haumea",     43.1, 0.60, 2.8, 0.0,     (0.85, 0.88, 0.95, 1.0), 0.15, (1.6, 0.9, 0.7)),
    ("Makemake",   45.3, 0.55, 2.9, 1.2,     (0.60, 0.32, 0.18, 1.0), 0.88, (1.0, 1.0, 1.0)),
    ("Quaoar",     43.7, 0.45, 1.5, 2.5,     (0.28, 0.25, 0.24, 1.0), 0.92, (1.1, 1.0, 0.9)),
    ("Orcus",      39.2, 0.48, 2.1, math.pi, (0.68, 0.68, 0.70, 1.0), 0.35, (1.0, 0.95, 0.95)),
]

# ──────────────────────────────────────────────────────────────────────────────
# GENERAL UTILITIES & CLEANUPS
# ──────────────────────────────────────────────────────────────────────────────

def remove_debris_objects(prefix):
    """Remove all objects whose name starts with prefix, except the root empty.
    do_unlink=True handles mesh/curve data unlinking safely."""
    for o in [o for o in bpy.data.objects if o.name.startswith(prefix) and o.name != prefix + "_Root"]:
        bpy.data.objects.remove(o, do_unlink=True)



def make_root_empty(name, size):
    root = bpy.data.objects.get(name)
    if root is None:
        root = bpy.data.objects.new(name, None)
        root.empty_display_type = 'PLAIN_AXES'
        root.empty_display_size = size
        bpy.context.collection.objects.link(root)
    root.location       = (0.0, 0.0, 0.0)
    root.rotation_euler = (0.0, 0.0, 0.0)
    root.scale          = (1.0, 1.0, 1.0)
    return root


def make_rock_mesh(name, detail, rng_seed):
    mesh = bpy.data.meshes.new(name)
    bm   = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=detail, radius=1.0)
    rng  = random.Random(rng_seed)
    for v in bm.verts:
        s = rng.uniform(0.60, 1.40)
        v.co = v.co * s
        v.co.x += rng.uniform(-0.12, 0.12)
        v.co.y += rng.uniform(-0.12, 0.12)
        v.co.z += rng.uniform(-0.10, 0.10)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def set_material_blend(mat, alpha):
    try:
        mat.surface_render_method = 'BLENDED' if alpha < 0.99 else 'OPAQUE'
    except AttributeError:
        pass
    try:
        mat.blend_method = 'BLEND' if alpha < 0.99 else 'OPAQUE'
    except AttributeError:
        pass


def add_self_spin_driver(obj, spin_period_frames, axis=0):
    fc  = obj.driver_add("rotation_euler", axis)
    drv = fc.driver
    drv.type       = 'SCRIPTED'
    drv.expression = f"(frame / {spin_period_frames}) * {math.tau}"


# ──────────────────────────────────────────────────────────────────────────────
# ASTEROID ORBIT MATH & DRIVERS
# ──────────────────────────────────────────────────────────────────────────────

def _ast_bu_to_au(bu):
    frac = (bu - MARS_DIST) / (JUPITER_DIST - MARS_DIST)
    return MARS_AU + frac * (JUPITER_AU - MARS_AU)

def _ast_period_frames(bu):
    au = _ast_bu_to_au(bu)
    return max(1, round(BASE_FRAMES * (au ** 1.5)))

def add_asteroid_orbit_driver(obj, radius_bu, initial_phase_rad):
    T     = _ast_period_frames(radius_bu)
    phase = initial_phase_rad

    fc_x = obj.driver_add("location", 0)
    d    = fc_x.driver
    d.type       = 'SCRIPTED'
    d.expression = f"{radius_bu} * cos((frame / {T}) * {math.tau} + {phase:.6f})"

    fc_y = obj.driver_add("location", 1)
    d    = fc_y.driver
    d.type       = 'SCRIPTED'
    d.expression = f"{radius_bu} * sin((frame / {T}) * {math.tau} + {phase:.6f})"
    return T


# ──────────────────────────────────────────────────────────────────────────────
# KBO ORBIT MATH & DRIVERS
# ──────────────────────────────────────────────────────────────────────────────

def _kbo_period_frames(bu):
    return max(1, round(1.5464 * (bu ** 1.5)))

def add_kbo_orbit_driver(obj, radius_bu, initial_phase_rad, tilt_deg=0.0, omega_deg=0.0, z_offset=0.0):
    T        = _kbo_period_frames(radius_bu)
    phase    = initial_phase_rad
    tilt_rad = math.radians(tilt_deg)
    om_rad   = math.radians(omega_deg)

    cos_o = math.cos(om_rad)
    sin_o = math.sin(om_rad)
    cos_i = math.cos(tilt_rad)
    sin_i = math.sin(tilt_rad)

    A_expr = f"((frame / {T}) * {math.tau} + {phase:.6f})"

    fc_x = obj.driver_add("location", 0)
    d    = fc_x.driver
    d.type       = 'SCRIPTED'
    d.expression = f"{radius_bu:.4f} * (cos({A_expr}) * {cos_o:.6f} - sin({A_expr}) * {cos_i:.6f} * {sin_o:.6f})"

    fc_y = obj.driver_add("location", 1)
    d    = fc_y.driver
    d.type       = 'SCRIPTED'
    d.expression = f"{radius_bu:.4f} * (cos({A_expr}) * {sin_o:.6f} + sin({A_expr}) * {cos_i:.6f} * {cos_o:.6f})"

    fc_z = obj.driver_add("location", 2)
    d    = fc_z.driver
    d.type       = 'SCRIPTED'
    d.expression = f"{radius_bu:.4f} * sin({A_expr}) * {sin_i:.6f} + {z_offset:.6f}"
    return T

# ──────────────────────────────────────────────────────────────────────────────
# PROCEDURAL SHADERS
# ──────────────────────────────────────────────────────────────────────────────

def make_asteroid_material(name, base_color, roughness=0.92):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location  = (550, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (150, 80)
    bsdf.inputs["Base Color"].default_value         = base_color
    bsdf.inputs["Roughness"].default_value          = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    bsdf.inputs["Metallic"].default_value           = 0.0

    emit = nodes.new("ShaderNodeEmission"); emit.location = (150, -120)
    emit.inputs["Strength"].default_value = 0.90

    add_sh = nodes.new("ShaderNodeAddShader"); add_sh.location = (380, 0)

    noise = nodes.new("ShaderNodeTexNoise"); noise.location = (-300, 80)
    noise.inputs["Scale"].default_value      = 18.0
    noise.inputs["Detail"].default_value     = 8.0
    noise.inputs["Roughness"].default_value  = 0.7
    noise.inputs["Distortion"].default_value = 0.3
    
    ramp = nodes.new("ShaderNodeValToRGB"); ramp.location = (-50, 80)
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color    = (base_color[0]*0.55, base_color[1]*0.55, base_color[2]*0.55, 1.0)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color    = base_color
    
    mix = nodes.new("ShaderNodeMixRGB"); mix.location = (0, 0)
    mix.blend_type = 'MULTIPLY'
    mix.inputs["Fac"].default_value = 0.55
    
    links.new(noise.outputs["Fac"],   ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"],  mix.inputs["Color1"])
    links.new(ramp.outputs["Color"],  mix.inputs["Color2"])
    links.new(mix.outputs["Color"],   bsdf.inputs["Base Color"])
    links.new(mix.outputs["Color"],   emit.inputs["Color"])
    links.new(bsdf.outputs["BSDF"],    add_sh.inputs[0])
    links.new(emit.outputs["Emission"], add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],  out.inputs["Surface"])
    return mat


def make_kbo_material(name, base_color, roughness=0.92,
                      emission_color=(0.1, 0.1, 0.1, 1.0), emission_strength=0.15,
                      ice_factor=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    tex_c = nodes.new("ShaderNodeTexCoord")
    tex_c.location = (-900, 0)

    noise1 = nodes.new("ShaderNodeTexNoise")
    noise1.location = (-680, 120)
    noise1.inputs["Scale"].default_value      = 4.5
    noise1.inputs["Detail"].default_value     = 10.0
    noise1.inputs["Roughness"].default_value  = 0.75
    noise1.inputs["Distortion"].default_value = 0.6

    noise2 = nodes.new("ShaderNodeTexNoise")
    noise2.location = (-680, -120)
    noise2.inputs["Scale"].default_value      = 22.0
    noise2.inputs["Detail"].default_value     = 12.0
    noise2.inputs["Roughness"].default_value  = 0.80
    noise2.inputs["Distortion"].default_value = 0.2

    links.new(tex_c.outputs["Object"], noise1.inputs["Vector"])
    links.new(tex_c.outputs["Object"], noise2.inputs["Vector"])

    mix_noise = nodes.new("ShaderNodeMixRGB")
    mix_noise.location = (-440, 0)
    mix_noise.blend_type = 'MIX'
    mix_noise.inputs["Fac"].default_value = 0.55
    links.new(noise1.outputs["Fac"], mix_noise.inputs["Color1"])
    links.new(noise2.outputs["Fac"], mix_noise.inputs["Color2"])

    ice_ramp = nodes.new("ShaderNodeValToRGB")
    ice_ramp.location = (-220, 80)
    cr = ice_ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = 0.30; cr.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    cr.elements[1].position = 0.72; cr.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    links.new(mix_noise.outputs["Color"], ice_ramp.inputs["Fac"])

    ice_bias = nodes.new("ShaderNodeMath")
    ice_bias.location = (-220, -120)
    ice_bias.operation = 'MULTIPLY'
    ice_bias.inputs[1].default_value = max(0.0, min(1.0, ice_factor))
    links.new(ice_ramp.outputs["Color"], ice_bias.inputs[0])

    rock_bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    rock_bsdf.location = (80, 200)
    rock_bsdf.inputs["Roughness"].default_value          = roughness
    rock_bsdf.inputs["Specular IOR Level"].default_value = 0.02
    rock_bsdf.inputs["Metallic"].default_value           = 0.0

    rock_darken = nodes.new("ShaderNodeMixRGB")
    rock_darken.location = (-50, 250)
    rock_darken.blend_type = 'MULTIPLY'
    rock_darken.inputs["Fac"].default_value = 0.70
    rock_darken.inputs["Color2"].default_value = (base_color[0] * 0.45, base_color[1] * 0.45, base_color[2] * 0.45, 1.0)
    links.new(noise1.outputs["Fac"],     rock_darken.inputs["Color1"])
    links.new(rock_darken.outputs["Color"], rock_bsdf.inputs["Base Color"])

    ice_bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    ice_bsdf.location = (80, -60)
    ice_bsdf.inputs["Base Color"].default_value         = (0.78, 0.88, 0.98, 1.0)
    ice_bsdf.inputs["Roughness"].default_value          = 0.08
    ice_bsdf.inputs["Specular IOR Level"].default_value = 0.85
    ice_bsdf.inputs["IOR"].default_value                = 1.31
    ice_bsdf.inputs["Metallic"].default_value           = 0.0

    mix_sh = nodes.new("ShaderNodeMixShader")
    mix_sh.location = (420, 80)
    links.new(ice_bias.outputs["Value"],   mix_sh.inputs["Fac"])
    links.new(rock_bsdf.outputs["BSDF"],   mix_sh.inputs[1])
    links.new(ice_bsdf.outputs["BSDF"],    mix_sh.inputs[2])

    bump = nodes.new("ShaderNodeBump")
    bump.location = (80, -260)
    bump.inputs["Strength"].default_value = 0.65
    bump.inputs["Distance"].default_value = 0.04
    links.new(noise2.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], rock_bsdf.inputs["Normal"])
    links.new(bump.outputs["Normal"], ice_bsdf.inputs["Normal"])

    emit = nodes.new("ShaderNodeEmission")
    emit.location = (420, -120)
    emit.inputs["Color"].default_value    = (0.25, 0.50, 0.85, 1.0)
    emit.inputs["Strength"].default_value = emission_strength * (0.5 + ice_factor * 1.2)

    add_sh = nodes.new("ShaderNodeAddShader")
    add_sh.location = (680, 0)
    links.new(mix_sh.outputs["Shader"],  add_sh.inputs[0])
    links.new(emit.outputs["Emission"],  add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],  out.inputs["Surface"])
    return mat

# ──────────────────────────────────────────────────────────────────────────────
# ASTEROID BELT BUILDER
# ──────────────────────────────────────────────────────────────────────────────

def build_asteroid_belt(root, rng):
    print("🪐 Generating Asteroid Belt...")
    remove_debris_objects("AsteroidBelt")

    # Places named large asteroids
    for ast_name, sma_au, size_bu, color in NAMED_ASTEROIDS:
        radius = _ast_au_to_bu(sma_au)
        phase  = rng.uniform(0, math.tau)
        z      = rng.gauss(0.0, ASTEROID_THICKNESS * 0.3)
        z      = max(-ASTEROID_THICKNESS, min(ASTEROID_THICKNESS, z))

        random.seed(hash(ast_name) & 0xFFFF)
        mesh = make_rock_mesh(f"AsteroidBelt_{ast_name}_Mesh", detail=3, rng_seed=random.randint(0, 10000))
        random.seed(ASTEROID_SEED)

        obj = bpy.data.objects.new(f"AsteroidBelt_{ast_name}", mesh)
        bpy.context.collection.objects.link(obj)

        T = _ast_period_frames(radius)
        obj.location = (radius * math.cos(phase + (1/T) * math.tau), radius * math.sin(phase + (1/T) * math.tau), z)
        obj.rotation_euler = (rng.uniform(0, math.tau), rng.uniform(0, math.tau), 0)

        actual_size = size_bu * LARGE_ASTEROID_SCALE
        obj.scale   = (actual_size, actual_size * 0.85, actual_size * 0.90)

        mat = make_asteroid_material(f"AsteroidBelt_{ast_name}_Mat", color, 0.93)
        obj.data.materials.append(mat)
        obj.parent = root

        add_asteroid_orbit_driver(obj, radius, phase)
        add_self_spin_driver(obj, round(T * rng.uniform(50, 120)), axis=0)
        print(f"   ✓ Placed asteroid: {ast_name:8s} (T={T}f)")

    # Places medium debris field
    mesh_pool = []
    for i in range(12):
        mesh_pool.append(make_rock_mesh(f"AsteroidBelt_RockMesh_{i:02d}", detail=2, rng_seed=ASTEROID_SEED + i*100))
        
    mat_pool = []
    for i in range(8):
        # Pick rock family weight
        r_val = rng.random()
        fam = ASTEROID_COLOR_FAMILIES[0] if r_val < 0.55 else (ASTEROID_COLOR_FAMILIES[1] if r_val < 0.90 else ASTEROID_COLOR_FAMILIES[2])
        color, roughness = fam[1], fam[2]
        mat_pool.append(make_asteroid_material(f"AsteroidBelt_RockMat_{i:02d}", color, roughness))

    placed = 0
    attempts = 0
    sigma = (ASTEROID_OUTER_BU - ASTEROID_INNER_BU) / 4.0

    while placed < ASTEROID_COUNT and attempts < ASTEROID_COUNT * 8:
        attempts += 1
        radius = rng.gauss(ASTEROID_MID_BU, sigma)
        radius = max(ASTEROID_INNER_BU, min(ASTEROID_OUTER_BU, radius))

        # Check Kirkwood gaps
        gap_hit = False
        for centre, half_w, strength in AST_KIRKWOOD_GAPS:
            if abs(radius - centre) < half_w and rng.random() < strength:
                gap_hit = True
                break
        if gap_hit: continue

        phase = rng.uniform(0, math.tau)
        z     = rng.gauss(0.0, ASTEROID_THICKNESS * 0.45)
        z     = max(-ASTEROID_THICKNESS, min(ASTEROID_THICKNESS, z))

        T = _ast_period_frames(radius)
        x = radius * math.cos(phase + (1/T) * math.tau)
        y = radius * math.sin(phase + (1/T) * math.tau)

        obj = bpy.data.objects.new(f"AsteroidBelt_Rock_{placed:04d}", mesh_pool[placed % len(mesh_pool)])
        bpy.context.collection.objects.link(obj)

        obj.location = (x, y, z)
        obj.rotation_euler = (rng.uniform(0, math.tau), rng.uniform(0, math.tau), 0)

        size = rng.uniform(ASTEROID_SIZE_MIN, ASTEROID_SIZE_MAX)
        obj.scale = (size * rng.uniform(0.7, 1.3), size * rng.uniform(0.7, 1.3), size * rng.uniform(0.6, 1.2))

        obj.data.materials.append(mat_pool[placed % len(mat_pool)])
        obj.parent = root

        add_asteroid_orbit_driver(obj, radius, phase)
        add_self_spin_driver(obj, round(T * rng.uniform(30, 150)), axis=0)
        placed += 1

    # Dust haze
    if ASTEROID_DUST_ALPHA > 0:
        name = "AsteroidBelt_Dust"
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        SEGS, RINGS = 256, 32
        vg = []
        for ri in range(RINGS + 1):
            rad = ASTEROID_INNER_BU + (ri / RINGS) * (ASTEROID_OUTER_BU - ASTEROID_INNER_BU)
            row = []
            for si in range(SEGS):
                a = (si / SEGS) * math.tau
                row.append(bm.verts.new((rad * math.cos(a), rad * math.sin(a), 0.0)))
            vg.append(row)
        bm.verts.ensure_lookup_table()
        for ri in range(RINGS):
            for si in range(SEGS):
                bm.faces.new([vg[ri][si], vg[ri][(si+1)%SEGS], vg[ri+1][(si+1)%SEGS], vg[ri+1][si]])
        bm.to_mesh(mesh)
        bm.free()
        
        dust = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(dust)
        dust.parent = root
        dust.rotation_euler = (math.radians(ASTEROID_TILT_DEG), 0, 0)
        
        mat = bpy.data.materials.new("AsteroidBelt_DustMat")
        mat.use_nodes = True
        set_material_blend(mat, ASTEROID_DUST_ALPHA)
        rnodes = mat.node_tree.nodes
        rnodes.clear()
        rout  = rnodes.new("ShaderNodeOutputMaterial")
        rbsdf = rnodes.new("ShaderNodeBsdfPrincipled")
        rbsdf.inputs["Base Color"].default_value = (0.12, 0.12, 0.12, 1.0)
        rbsdf.inputs["Roughness"].default_value   = 1.00
        rbsdf.inputs["Alpha"].default_value       = ASTEROID_DUST_ALPHA
        mat.node_tree.links.new(rbsdf.outputs["BSDF"], rout.inputs["Surface"])
        dust.data.materials.append(mat)

    # Label Setup
    label_name = "AsteroidBelt_Label"
    old_c = bpy.data.curves.get(label_name)
    if old_c: bpy.data.curves.remove(old_c)
    cd = bpy.data.curves.new(label_name, type='FONT')
    cd.body = "Asteroid Belt"
    cd.size = 1.0
    cd.align_x = 'CENTER'; cd.align_y = 'BOTTOM'
    
    mat = bpy.data.materials.get("Text_Bright_Mat")
    if mat: cd.materials.append(mat)
    
    lbl = bpy.data.objects.new(label_name, cd)
    bpy.context.collection.objects.link(lbl)
    lbl.parent = root
    lbl.location = (-36.0, 40.0, 0.0)
    lbl.scale = (3.2, 3.2, 3.2)
    for attr in ["visible_glossy", "visible_diffuse", "visible_shadow", "visible_transmission", "visible_volume_scatter"]:
        setattr(lbl, attr, False)
    cam = bpy.data.objects.get("Camera")
    if cam:
        con = lbl.constraints.new(type='COPY_ROTATION')
        con.target = cam

# ──────────────────────────────────────────────────────────────────────────────
# KUIPER BELT BUILDER
# ──────────────────────────────────────────────────────────────────────────────

def build_kuiper_belt(root, rng):
    print("🪐 Generating Kuiper Belt...")
    remove_debris_objects("KuiperBelt")

    # Named Dwarf Planets
    for name, sma_au, size_bu, tilt, phase, color, roughness, scale_tup in NAMED_KBOS:
        radius = KBO_INNER_BU + ((sma_au - 30.0) / 20.0) * (KBO_OUTER_BU - KBO_INNER_BU)
        omega  = rng.uniform(0, 360)
        z_off  = rng.uniform(-KBO_THICKNESS * 0.2, KBO_THICKNESS * 0.2)

        random.seed(hash(name) & 0xFFFF)
        mesh = make_rock_mesh(f"KuiperBelt_{name}_Mesh", detail=3, rng_seed=random.randint(0, 10000))
        random.seed(KBO_SEED)

        obj = bpy.data.objects.new(f"KuiperBelt_{name}", mesh)
        bpy.context.collection.objects.link(obj)

        T = _kbo_period_frames(radius)
        tilt_rad = math.radians(tilt)
        om_rad   = math.radians(omega)
        A = phase + (1/T) * math.tau
        
        x = radius * (math.cos(A) * math.cos(om_rad) - math.sin(A) * math.cos(tilt_rad) * math.sin(om_rad))
        y = radius * (math.cos(A) * math.sin(om_rad) + math.sin(A) * math.cos(tilt_rad) * math.cos(om_rad))
        z = radius * math.sin(A) * math.sin(tilt_rad) + z_off
        
        obj.location = (x, y, z)
        obj.rotation_euler = (rng.uniform(0, math.tau), rng.uniform(0, math.tau), 0)

        actual_size = size_bu * LARGE_KBO_SCALE
        obj.scale   = (actual_size * scale_tup[0], actual_size * scale_tup[1], actual_size * scale_tup[2])

        emit_strength = 0.20 if name in ["Haumea", "Makemake"] else 0.10
        ice_factor = 0.90 if name == "Haumea" else (0.45 if name == "Orcus" else (0.20 if name == "Makemake" else 0.05))
        mat = make_kbo_material(f"KuiperBelt_{name}_Mat", color, roughness, color, emit_strength, ice_factor)
        obj.data.materials.append(mat)
        obj.parent = root

        add_kbo_orbit_driver(obj, radius, phase, tilt_deg=tilt, omega_deg=omega, z_offset=z_off)
        add_self_spin_driver(obj, 15 if name == "Haumea" else round(T * rng.uniform(40, 100)), axis=2)
        print(f"   ✓ Placed dwarf planet: {name:8s} (T={T}f, i={tilt}°)")

    # Medium classical KBO field
    mesh_pool = []
    for i in range(16):
        mesh_pool.append(make_rock_mesh(f"KuiperBelt_RockMesh_{i:02d}", detail=2, rng_seed=KBO_SEED + i*150))

    mat_pool = []
    for i in range(12):
        # Pick KBO type
        r_val = rng.random()
        if r_val < 0.40:
            color = (rng.uniform(0.78, 0.88), rng.uniform(0.82, 0.92), rng.uniform(0.90, 0.98), 1.0)
            roughness = rng.uniform(0.12, 0.28)
            emit_color = (0.30, 0.45, 0.65, 1.0)
            ice_factor = rng.uniform(0.65, 1.00)
        elif r_val < 0.85:
            color = (rng.uniform(0.55, 0.68), rng.uniform(0.30, 0.42), rng.uniform(0.18, 0.28), 1.0)
            roughness = rng.uniform(0.80, 0.95)
            emit_color = (0.35, 0.20, 0.10, 1.0)
            ice_factor = rng.uniform(0.10, 0.35)
        else:
            color = (rng.uniform(0.22, 0.34), rng.uniform(0.22, 0.34), rng.uniform(0.24, 0.36), 1.0)
            roughness = rng.uniform(0.90, 0.98)
            emit_color = (0.18, 0.18, 0.20, 1.0)
            ice_factor = rng.uniform(0.00, 0.15)
        mat_pool.append(make_kbo_material(f"KuiperBelt_RockMat_{i:02d}", color, roughness, emit_color, 0.45, ice_factor))

    placed = 0
    attempts = 0
    sigma = (KBO_OUTER_BU - KBO_INNER_BU) / 4.5

    while placed < KBO_COUNT and attempts < KBO_COUNT * 6:
        attempts += 1
        radius = rng.gauss(KBO_MID_BU, sigma)
        radius = max(KBO_INNER_BU, min(KBO_OUTER_BU, radius))

        phase = rng.uniform(0, math.tau)
        omega = rng.uniform(0, 360)
        tilt  = rng.uniform(0.0, 2.0) if rng.random() < 0.50 else rng.uniform(2.0, 5.0)
        z_off = rng.gauss(0.0, KBO_THICKNESS * 0.30)
        z_off = max(-KBO_THICKNESS, min(KBO_THICKNESS, z_off))

        T = _kbo_period_frames(radius)
        tilt_rad = math.radians(tilt)
        om_rad   = math.radians(omega)
        A = phase + (1/T) * math.tau
        
        x = radius * (math.cos(A) * math.cos(om_rad) - math.sin(A) * math.cos(tilt_rad) * math.sin(om_rad))
        y = radius * (math.cos(A) * math.sin(om_rad) + math.sin(A) * math.cos(tilt_rad) * math.cos(om_rad))
        z = radius * math.sin(A) * math.sin(tilt_rad) + z_off

        obj = bpy.data.objects.new(f"KuiperBelt_Rock_{placed:04d}", mesh_pool[placed % len(mesh_pool)])
        bpy.context.collection.objects.link(obj)

        obj.location = (x, y, z)
        obj.rotation_euler = (rng.uniform(0, math.tau), rng.uniform(0, math.tau), 0)

        size = rng.uniform(KBO_SIZE_MIN, KBO_SIZE_MAX)
        obj.scale = (size * rng.uniform(0.75, 1.25), size * rng.uniform(0.75, 1.25), size * rng.uniform(0.65, 1.15))

        obj.data.materials.append(mat_pool[placed % len(mat_pool)])
        obj.parent = root

        add_kbo_orbit_driver(obj, radius, phase, tilt_deg=tilt, omega_deg=omega, z_offset=z_off)
        add_self_spin_driver(obj, round(T * rng.uniform(25, 120)), axis=0)
        placed += 1

    # Dust haze
    if KBO_DUST_ALPHA > 0:
        name = "KuiperBelt_Dust"
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        SEGS, RINGS = 256, 32
        vg = []
        for ri in range(RINGS + 1):
            rad = KBO_INNER_BU + (ri / RINGS) * (KBO_OUTER_BU - KBO_INNER_BU)
            row = []
            for si in range(SEGS):
                a = (si / SEGS) * math.tau
                row.append(bm.verts.new((rad * math.cos(a), rad * math.sin(a), 0.0)))
            vg.append(row)
        bm.verts.ensure_lookup_table()
        for ri in range(RINGS):
            for si in range(SEGS):
                bm.faces.new([vg[ri][si], vg[ri][(si+1)%SEGS], vg[ri+1][(si+1)%SEGS], vg[ri+1][si]])
        bm.to_mesh(mesh)
        bm.free()
        
        dust = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(dust)
        dust.parent = root
        
        mat = bpy.data.materials.new("KuiperBelt_DustMat")
        mat.use_nodes = True
        set_material_blend(mat, KBO_DUST_ALPHA)
        rnodes = mat.node_tree.nodes
        rnodes.clear()
        rout  = rnodes.new("ShaderNodeOutputMaterial")
        rbsdf = rnodes.new("ShaderNodeBsdfPrincipled")
        rbsdf.inputs["Base Color"].default_value = (0.15, 0.18, 0.22, 1.0)
        rbsdf.inputs["Roughness"].default_value   = 1.00
        rbsdf.inputs["Alpha"].default_value       = KBO_DUST_ALPHA
        mat.node_tree.links.new(rbsdf.outputs["BSDF"], rout.inputs["Surface"])
        dust.data.materials.append(mat)

    # Label Setup
    label_name = "KuiperBelt_Label"
    old_c = bpy.data.curves.get(label_name)
    if old_c: bpy.data.curves.remove(old_c)
    cd = bpy.data.curves.new(label_name, type='FONT')
    cd.body = "Kuiper Belt"
    cd.size = 1.0
    cd.align_x = 'CENTER'; cd.align_y = 'BOTTOM'
    
    mat = bpy.data.materials.get("Text_Bright_Mat")
    if mat: cd.materials.append(mat)
    
    lbl = bpy.data.objects.new(label_name, cd)
    bpy.context.collection.objects.link(lbl)
    lbl.parent = root
    lbl.location = (-130.0, 158.0, 0.0)
    lbl.scale = (6.0, 6.0, 6.0)
    for attr in ["visible_glossy", "visible_diffuse", "visible_shadow", "visible_transmission", "visible_volume_scatter"]:
        setattr(lbl, attr, False)
    cam = bpy.data.objects.get("Camera")
    if cam:
        con = lbl.constraints.new(type='COPY_ROTATION')
        con.target = cam

# ──────────────────────────────────────────────────────────────────────────────
# MAIN RUNNER
# ──────────────────────────────────────────────────────────────────────────────

def run_all_debris():
    # Ensure Object mode
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    print("\n" + "=" * 65)
    print("  DEBRIS FIELD PROCEDURAL GENERATOR  —  ASTEROIDS & KBOs")
    print("=" * 65)

    ast_rng = random.Random(ASTEROID_SEED)
    kbo_rng = random.Random(KBO_SEED)

    ast_root = make_root_empty("AsteroidBelt_Root", size=2.0)
    build_asteroid_belt(ast_root, ast_rng)

    kbo_root = make_root_empty("KuiperBelt_Root", size=3.0)
    build_kuiper_belt(kbo_root, kbo_rng)

    print("\n✅ All debris belts generated successfully!")

    # Purge any orphaned mesh/material/curve data left over from previous runs.
    # This is safe here because all objects are already built and parented.
    try:
        bpy.ops.outliner.orphans_purge(do_recursive=True)
    except Exception:
        pass  # non-critical — orphans will be purged on next file save



if __name__ == "__main__":
    run_all_debris()
