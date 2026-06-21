"""
Voyager_Mission.py
==================
Consolidated Voyager 1 & 2 spacecraft builder, trajectory animator, and HUD flyby labeler.

This script:
1. Procedurally models both Voyager probes ( HGA dishes, decagonal buses, RTGs, science booms, magnetometers, procedural materials ).
2. Bakes keyframed trajectories based on historical waypoints (Jupiter, Saturn, Uranus, Neptune).
3. Animates moving glows/trails behind each spacecraft.
4. Generates camera-facing letter overlays at flyby locations and a stacked, camera-facing legend overlay in world space.
"""

import bpy
import bmesh
import math
import random
import mathutils
from mathutils import Matrix, Vector

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION & SCALING (SYNCED WITH Orrery_Simulation.py)
# ──────────────────────────────────────────────────────────────────────────────
BASE_FRAMES = 300
EARTH_DIST_BU = 31.0
AU_TO_BU = EARTH_DIST_BU
VOYAGER_VISUAL_SCALE = 0.15
COLLECTION_NAME = "Voyager Probes"
VOYAGER_TRAIL_PHYSICAL_LENGTH = 15.0
EPOCH_YEAR = 1977

# Legend display configurations in world space
LEGEND_LOCATION = (-320.0, 380.0, 50.0)
LEGEND_SCALE = (5.0, 5.0, 5.0)
LEGEND_TEXT_SIZE = 1.0
LEGEND_LINE_GAP = 1.6

# Planet distances (must match Orrery_Simulation.py)
DISTANCE = {
    "Jupiter": 70.0,
    "Saturn":  95.0,
    "Uranus":  120.0,
    "Neptune": 145.0,
}

# Historical flyby details & UTC records
FLYBY_DATA = [
    {
        "name": "Voyager_V1_Flyby_Jupiter_Info",
        "marker": "Voyager_V1_Flyby_Jupiter",
        "text": "VOYAGER 1\nJUPITER FLYBY\nMarch 5, 1979\n12:05 UTC",
        "frame": 675,
        "color": (0.4, 0.8, 1.0)  # Ice blue
    },
    {
        "name": "Voyager_V1_Flyby_Saturn_Info",
        "marker": "Voyager_V1_Flyby_Saturn",
        "text": "VOYAGER 1\nSATURN FLYBY\nNovember 12, 1980\n23:46 UTC",
        "frame": 1170,
        "color": (0.4, 0.8, 1.0)
    },
    {
        "name": "Voyager_V2_Flyby_Jupiter_Info",
        "marker": "Voyager_V2_Flyby_Jupiter",
        "text": "VOYAGER 2\nJUPITER FLYBY\nJuly 9, 1979\n22:29 UTC",
        "frame": 795,
        "color": (1.0, 0.55, 0.25)  # Warm amber
    },
    {
        "name": "Voyager_V2_Flyby_Saturn_Info",
        "marker": "Voyager_V2_Flyby_Saturn",
        "text": "VOYAGER 2\nSATURN FLYBY\nAugust 26, 1981\n03:24 UTC",
        "frame": 1440,
        "color": (1.0, 0.55, 0.25)
    },
    {
        "name": "Voyager_V2_Flyby_Uranus_Info",
        "marker": "Voyager_V2_Flyby_Uranus",
        "text": "VOYAGER 2\nURANUS FLYBY\nJanuary 24, 1986\n17:59 UTC",
        "frame": 2745,
        "color": (1.0, 0.55, 0.25)
    },
    {
        "name": "Voyager_V2_Flyby_Neptune_Info",
        "marker": "Voyager_V2_Flyby_Neptune",
        "text": "VOYAGER 2\nNEPTUNE FLYBY\nAugust 25, 1989\n03:56 UTC",
        "frame": 3840,
        "color": (1.0, 0.55, 0.25)
    }
]

# Voyager 1 Waypoints (year, x_BU, y_BU, z_BU)
V1_WAYPOINTS_YEARS = [
    (1977.68, EARTH_DIST_BU * 1.0,   EARTH_DIST_BU * 0.15,   0.0),
    (1979.25,  DISTANCE["Jupiter"] * math.cos(math.radians(15)), DISTANCE["Jupiter"] * math.sin(math.radians(15)), 0.5),
    (1980.90,  DISTANCE["Saturn"] * math.cos(math.radians(28)), DISTANCE["Saturn"] * math.sin(math.radians(28)), 3.0),
    (1990.0,   180.0 * math.cos(math.radians(40)), 180.0 * math.sin(math.radians(40)), 55.0),
    (2004.0,   280.0 * math.cos(math.radians(48)), 280.0 * math.sin(math.radians(48)), 110.0),
    (2024.0,   380.0 * math.cos(math.radians(52)), 380.0 * math.sin(math.radians(52)), 175.0),
    (2040.0,   470.0 * math.cos(math.radians(54)), 470.0 * math.sin(math.radians(54)), 218.0),
]

# Voyager 2 Waypoints
V2_WAYPOINTS_YEARS = [
    (1977.63, EARTH_DIST_BU * 0.95,  EARTH_DIST_BU * -0.15,   0.0),
    (1979.65,  DISTANCE["Jupiter"] * math.cos(math.radians(-20)), DISTANCE["Jupiter"] * math.sin(math.radians(-20)), -0.5),
    (1981.80,  DISTANCE["Saturn"] * math.cos(math.radians(-35)), DISTANCE["Saturn"] * math.sin(math.radians(-35)), -2.0),
    (1986.15,  DISTANCE["Uranus"] * math.cos(math.radians(-55)), DISTANCE["Uranus"] * math.sin(math.radians(-55)), -8.0),
    (1989.80,  DISTANCE["Neptune"] * math.cos(math.radians(-75)), DISTANCE["Neptune"] * math.sin(math.radians(-75)), -22.0),
    (2004.0,   220.0 * math.cos(math.radians(-85)), 220.0 * math.sin(math.radians(-85)), -70.0),
    (2024.0,   310.0 * math.cos(math.radians(-90)), 310.0 * math.sin(math.radians(-90)), -110.0),
    (2040.0,   390.0 * math.cos(math.radians(-92)), 390.0 * math.sin(math.radians(-92)), -140.0),
]

# ──────────────────────────────────────────────────────────────────────────────
# TIMELINE HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def year_to_frame(year_float):
    return (year_float - EPOCH_YEAR) * BASE_FRAMES

# ──────────────────────────────────────────────────────────────────────────────
# PROCEDURAL MATERIALS
# ──────────────────────────────────────────────────────────────────────────────

def make_mat(name, base_color, roughness=0.5, metallic=0.0,
             emission_color=None, emission_strength=0.0,
             coat_weight=0.0, coat_roughness=0.2):
    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)

    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*base_color, 1.0)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out  = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value  = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value   = roughness
    bsdf.inputs["Metallic"].default_value    = metallic

    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value    = coat_weight
        bsdf.inputs["Coat Roughness"].default_value = coat_roughness

    if emission_color and emission_strength > 0:
        bsdf.inputs["Emission Color"].default_value = (*emission_color, 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength
        else:
            emit = nodes.new("ShaderNodeEmission")
            emit.inputs["Color"].default_value    = (*emission_color, 1.0)
            emit.inputs["Strength"].default_value = emission_strength
            add_sh = nodes.new("ShaderNodeAddShader")
            links.new(bsdf.outputs["BSDF"],      add_sh.inputs[0])
            links.new(emit.outputs["Emission"],  add_sh.inputs[1])
            links.new(add_sh.outputs["Shader"],  out.inputs["Surface"])
            return mat

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_dish_material(name):
    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)

    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (0.85, 0.85, 0.85, 1.0)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial")
    bsdf  = nodes.new("ShaderNodeBsdfPrincipled")
    coord = nodes.new("ShaderNodeTexCoord")
    wave  = nodes.new("ShaderNodeTexWave")
    bump  = nodes.new("ShaderNodeBump")

    bsdf.inputs["Base Color"].default_value  = (0.80, 0.82, 0.85, 1.0)
    bsdf.inputs["Metallic"].default_value    = 0.92
    bsdf.inputs["Roughness"].default_value   = 0.08

    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value    = 0.15
        bsdf.inputs["Coat Roughness"].default_value = 0.05

    wave.wave_type       = 'RINGS'
    wave.rings_direction = 'SPHERICAL'
    wave.inputs["Scale"].default_value       = 60.0
    wave.inputs["Distortion"].default_value  = 0.4
    wave.inputs["Detail"].default_value      = 3.0

    bump.inputs["Strength"].default_value  = 0.04
    bump.inputs["Distance"].default_value  = 0.01

    links.new(coord.outputs["Generated"], wave.inputs["Vector"])
    links.new(wave.outputs["Color"],      bump.inputs["Height"])
    links.new(bump.outputs["Normal"],     bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"],       out.inputs["Surface"])
    return mat


def make_mylar_material(name):
    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)

    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (0.92, 0.88, 0.72, 1.0)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial")
    bsdf  = nodes.new("ShaderNodeBsdfPrincipled")
    coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp  = nodes.new("ShaderNodeValToRGB")
    mix   = nodes.new("ShaderNodeMixRGB")

    bsdf.inputs["Metallic"].default_value   = 0.55
    bsdf.inputs["Roughness"].default_value  = 0.35

    noise.inputs["Scale"].default_value     = 120.0
    noise.inputs["Detail"].default_value    = 8.0
    noise.inputs["Roughness"].default_value = 0.7

    cr = ramp.color_ramp
    cr.interpolation = 'LINEAR'
    cr.elements[0].position = 0.30; cr.elements[0].color = (0.55, 0.40, 0.08, 1.0)
    cr.elements[1].position = 0.70; cr.elements[1].color = (0.95, 0.92, 0.78, 1.0)

    mix.blend_type = 'MIX'
    mix.inputs["Fac"].default_value = 0.3
    mix.inputs["Color1"].default_value = (0.92, 0.88, 0.72, 1.0)

    links.new(coord.outputs["Object"],  noise.inputs["Vector"])
    links.new(noise.outputs["Fac"],     ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"],    mix.inputs["Color2"])
    links.new(mix.outputs["Color"],     bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"],     out.inputs["Surface"])
    return mat


def make_rtg_material(name):
    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)

    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (0.02, 0.02, 0.02, 1.0)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial")
    bsdf  = nodes.new("ShaderNodeBsdfPrincipled")
    emit  = nodes.new("ShaderNodeEmission")
    add   = nodes.new("ShaderNodeAddShader")

    bsdf.inputs["Base Color"].default_value  = (0.025, 0.02, 0.015, 1.0)
    bsdf.inputs["Roughness"].default_value   = 0.90
    bsdf.inputs["Metallic"].default_value    = 0.15

    emit.inputs["Color"].default_value    = (1.0, 0.35, 0.06, 1.0)
    emit.inputs["Strength"].default_value = 0.18

    links.new(bsdf.outputs["BSDF"],     add.inputs[0])
    links.new(emit.outputs["Emission"], add.inputs[1])
    links.new(add.outputs["Shader"],    out.inputs["Surface"])
    return mat


def make_strut_material(name):
    return make_mat(name, (0.18, 0.18, 0.20), roughness=0.55, metallic=0.6)


def make_electronics_material(name):
    return make_mat(name, (0.60, 0.62, 0.65), roughness=0.45, metallic=0.7)


def make_gold_foil_material(name):
    return make_mat(name, (0.80, 0.55, 0.08), roughness=0.28, metallic=0.82)

# ──────────────────────────────────────────────────────────────────────────────
# GEOMETRY HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def new_obj(name, mesh_or_none, col, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    obj = bpy.data.objects.new(name, mesh_or_none)
    col.objects.link(obj)
    obj.location       = loc
    obj.rotation_euler = rot
    obj.scale          = scale
    if mat:
        obj.data.materials.append(mat)
    return obj


def make_cylinder(name, radius, height, segs=16, smooth=True):
    mesh = bpy.data.meshes.new(name)
    bm   = bmesh.new()
    half = height / 2.0

    top = bm.verts.new((0, 0,  half))
    bot = bm.verts.new((0, 0, -half))
    top_r, bot_r = [], []

    for i in range(segs):
        a = (i / segs) * math.tau
        c, s = math.cos(a), math.sin(a)
        top_r.append(bm.verts.new((c * radius, s * radius,  half)))
        bot_r.append(bm.verts.new((c * radius, s * radius, -half)))

    bm.verts.ensure_lookup_table()
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new([top_r[i], top_r[j], bot_r[j], bot_r[i]])
        bm.faces.new([top, top_r[j], top_r[i]])
        bm.faces.new([bot, bot_r[i], bot_r[j]])

    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        for f in mesh.polygons:
            f.use_smooth = True
    mesh.update()
    return mesh


def make_box(name, sx, sy, sz):
    mesh = bpy.data.meshes.new(name)
    bm   = bmesh.new()
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    verts = [
        bm.verts.new(( hx,  hy,  hz)), bm.verts.new(( hx, -hy,  hz)),
        bm.verts.new((-hx, -hy,  hz)), bm.verts.new((-hx,  hy,  hz)),
        bm.verts.new(( hx,  hy, -hz)), bm.verts.new(( hx, -hy, -hz)),
        bm.verts.new((-hx, -hy, -hz)), bm.verts.new((-hx,  hy, -hz)),
    ]
    bm.verts.ensure_lookup_table()
    for fi in [[0,1,2,3],[4,7,6,5],[0,3,7,4],[1,5,6,2],[0,4,5,1],[3,2,6,7]]:
        bm.faces.new([verts[i] for i in fi])
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def make_cone(name, radius_top, radius_bot, height, segs=16):
    mesh = bpy.data.meshes.new(name)
    bm   = bmesh.new()
    half = height / 2.0

    top_c = bm.verts.new((0, 0,  half))
    bot_c = bm.verts.new((0, 0, -half))
    top_r, bot_r = [], []

    for i in range(segs):
        a = (i / segs) * math.tau
        c, s = math.cos(a), math.sin(a)
        top_r.append(bm.verts.new((c * radius_top, s * radius_top,  half)))
        bot_r.append(bm.verts.new((c * radius_bot, s * radius_bot, -half)))

    bm.verts.ensure_lookup_table()
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new([top_r[i], top_r[j], bot_r[j], bot_r[i]])

    if radius_top < 0.001:
        for i in range(segs):
            bm.faces.new([top_c, top_r[(i + 1) % segs], top_r[i]])
    else:
        bm.faces.new(list(reversed(top_r)))

    bm.faces.new(bot_r)

    bm.to_mesh(mesh)
    bm.free()
    for f in mesh.polygons:
        f.use_smooth = True
    mesh.update()
    return mesh


def make_parabolic_dish(name, dish_radius, dish_depth, segs=32, rings=12):
    mesh = bpy.data.meshes.new(name)
    bm   = bmesh.new()
    p = (dish_radius ** 2) / (2.0 * dish_depth) if dish_depth > 0 else 1.0

    rows = []
    for r in range(rings + 1):
        frac = r / rings
        rad  = frac * dish_radius
        z    = -(rad ** 2) / (2.0 * p)
        row  = []
        for s in range(segs):
            a = (s / segs) * math.tau
            row.append(bm.verts.new((math.cos(a) * rad, math.sin(a) * rad, z)))
        rows.append(row)

    bm.verts.ensure_lookup_table()
    centre = bm.verts.new((0, 0, -(dish_radius ** 2) / (2.0 * p)))

    for s in range(segs):
        bm.faces.new([centre, rows[0][(s + 1) % segs], rows[0][s]])

    for r in range(rings):
        for s in range(segs):
            sn = (s + 1) % segs
            bm.faces.new([rows[r][s], rows[r][sn], rows[r + 1][sn], rows[r + 1][s]])

    bm.to_mesh(mesh)
    bm.free()
    for f in mesh.polygons:
        f.use_smooth = True
    mesh.update()
    return mesh


def make_decagon_prism(name, radius, height, sides=10):
    mesh = bpy.data.meshes.new(name)
    bm   = bmesh.new()
    half = height / 2.0

    top_r, bot_r = [], []
    for i in range(sides):
        a = (i / sides) * math.tau
        c, s = math.cos(a), math.sin(a)
        top_r.append(bm.verts.new((c * radius, s * radius,  half)))
        bot_r.append(bm.verts.new((c * radius, s * radius, -half)))

    bm.verts.ensure_lookup_table()
    top_face = list(reversed(top_r))
    bot_face  = list(bot_r)
    bm.faces.new(top_face)
    bm.faces.new(bot_face)

    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new([top_r[i], bot_r[i], bot_r[j], top_r[j]])

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh

# ──────────────────────────────────────────────────────────────────────────────
# MODEL CONSTRUCTION
# ──────────────────────────────────────────────────────────────────────────────

def build_voyager_geometry(root, col, S, suffix,
                           mat_body, mat_dish, mat_rtg,
                           mat_strut, mat_elec, mat_gold, mat_foil):
    bus_r = 0.89 * S
    bus_h = 0.47 * S
    bus_mesh = make_decagon_prism(f"Voyager_{suffix}_Bus_Mesh", bus_r, bus_h, sides=10)
    bus = new_obj(f"Voyager_{suffix}_Bus", bus_mesh, col, mat_body, loc=(0, 0, 0))
    bus.parent = root
    bus.matrix_parent_inverse.identity()

    foil_mesh = make_cylinder(f"Voyager_{suffix}_Foil_Mesh", bus_r * 1.01, 0.12 * S, segs=10)
    foil = new_obj(f"Voyager_{suffix}_Foil", foil_mesh, col, mat_gold, loc=(0, 0, -bus_h * 0.38))
    foil.parent = bus
    foil.matrix_parent_inverse.identity()

    elec_w = 0.40 * S
    elec_h = 0.28 * S
    for i in range(3):
        z_off = bus_h * 0.5 + elec_h * 0.5 + i * elec_h * 1.05
        em = make_box(f"Voyager_{suffix}_Elec_{i}_Mesh", elec_w, elec_w * 0.7, elec_h)
        eo = new_obj(f"Voyager_{suffix}_Elec_{i}", em, col, mat_elec, loc=(0, 0, z_off))
        eo.parent = bus
        eo.matrix_parent_inverse.identity()

    dish_r = 1.83 * S
    dish_d = 0.46 * S
    dish_mesh = make_parabolic_dish(f"Voyager_{suffix}_Dish_Mesh", dish_r, dish_d, segs=32, rings=14)
    dish = new_obj(f"Voyager_{suffix}_Dish", dish_mesh, col, mat_dish,
                   loc=(0, 0, -bus_h * 0.5 - dish_d * 0.5), rot=(math.pi, 0, 0))
    dish.parent = bus
    dish.matrix_parent_inverse.identity()

    rim_mesh = make_cylinder(f"Voyager_{suffix}_DishRim_Mesh", dish_r * 1.005, 0.04 * S, segs=32)
    rim = new_obj(f"Voyager_{suffix}_DishRim", rim_mesh, col, mat_strut, loc=(0, 0, -bus_h * 0.5 - dish_d))
    rim.parent = bus
    rim.matrix_parent_inverse.identity()

    sub_mesh = make_cone(f"Voyager_{suffix}_SubRef_Mesh", 0.10 * S, 0.07 * S, 0.14 * S, segs=12)
    sub = new_obj(f"Voyager_{suffix}_SubRef", sub_mesh, col, mat_elec, loc=(0, 0, -bus_h * 0.5 - dish_d * 0.08))
    sub.parent = bus
    sub.matrix_parent_inverse.identity()

    for i in range(4):
        angle = (i / 4.0) * math.tau
        sx_ = math.cos(angle) * dish_r * 0.8
        sy_ = math.sin(angle) * dish_r * 0.8
        strut_len = math.sqrt(sx_ ** 2 + sy_ ** 2 + (dish_d * 0.92) ** 2)
        sm = make_cylinder(f"Voyager_{suffix}_SubStrut_{i}_Mesh", 0.02 * S, strut_len, segs=6)
        so = new_obj(f"Voyager_{suffix}_SubStrut_{i}", sm, col, mat_strut, loc=(sx_ * 0.5, sy_ * 0.5, -bus_h * 0.5 - dish_d * 0.54))
        pitch = math.atan2(dish_d * 0.92, math.sqrt(sx_ ** 2 + sy_ ** 2))
        so.rotation_euler = (math.pi / 2.0 - pitch, 0, angle + math.pi / 2.0)
        so.parent = bus
        so.matrix_parent_inverse.identity()

    lga_rod_mesh = make_cylinder(f"Voyager_{suffix}_LGA_Rod_Mesh", 0.018 * S, 0.85 * S, segs=6)
    lga_rod = new_obj(f"Voyager_{suffix}_LGA_Rod", lga_rod_mesh, col, mat_strut, loc=(0, 0, bus_h * 0.5 + elec_h * 3.2 + 0.42 * S))
    lga_rod.parent = bus
    lga_rod.matrix_parent_inverse.identity()

    lga_horn_mesh = make_cone(f"Voyager_{suffix}_LGA_Horn_Mesh", 0.12 * S, 0.035 * S, 0.22 * S, segs=12)
    lga_horn = new_obj(f"Voyager_{suffix}_LGA_Horn", lga_horn_mesh, col, mat_elec, loc=(0, 0, bus_h * 0.5 + elec_h * 3.2 + 0.85 * S + 0.11 * S))
    lga_horn.parent = bus
    lga_horn.matrix_parent_inverse.identity()

    rtg_boom_len  = 2.28 * S
    rtg_body_len  = 0.55 * S
    rtg_body_r    = 0.14 * S
    rtg_angle_deg = 120.0

    rtg_boom_mesh = make_cylinder(f"Voyager_{suffix}_RTG_Boom_Mesh", 0.025 * S, rtg_boom_len, segs=6)
    rtg_body_mesh = make_cylinder(f"Voyager_{suffix}_RTG_Body_Mesh", rtg_body_r, rtg_body_len, segs=12)
    rtg_fin_mesh  = make_box(f"Voyager_{suffix}_RTG_Fin_Mesh", rtg_body_r * 2.1, 0.30 * S, 0.04 * S)

    for i in range(3):
        azimuth = math.radians(i * rtg_angle_deg + 30)
        tip_x = math.cos(azimuth) * rtg_boom_len
        tip_y = math.sin(azimuth) * rtg_boom_len
        tip_z = -0.15 * S

        mid_x = tip_x * 0.5
        mid_y = tip_y * 0.5
        mid_z = tip_z * 0.5

        tilt = math.atan2(-tip_z, math.sqrt(tip_x ** 2 + tip_y ** 2))
        bm_obj = new_obj(f"Voyager_{suffix}_RTG_Boom_{i}", rtg_boom_mesh, col, mat_strut, loc=(mid_x, mid_y, mid_z))
        bm_obj.rotation_euler = (-math.pi / 2.0 + tilt, 0, azimuth + math.pi / 2.0)
        bm_obj.parent = bus
        bm_obj.matrix_parent_inverse.identity()

        rtg_obj = new_obj(f"Voyager_{suffix}_RTG_{i}", rtg_body_mesh, col, mat_rtg, loc=(tip_x, tip_y, tip_z), rot=(-math.pi / 2.0 + tilt, 0, azimuth + math.pi / 2.0))
        rtg_obj.parent = bus
        rtg_obj.matrix_parent_inverse.identity()

        for f_idx in range(4):
            fin_rot_z = azimuth + (f_idx / 4.0) * math.tau
            fin_x = tip_x + math.cos(fin_rot_z) * rtg_body_r * 1.4
            fin_y = tip_y + math.sin(fin_rot_z) * rtg_body_r * 1.4
            fin_obj = new_obj(f"Voyager_{suffix}_RTG_{i}_Fin_{f_idx}", rtg_fin_mesh, col, mat_rtg, loc=(fin_x, fin_y, tip_z), rot=(tilt * 0.2, 0, fin_rot_z))
            fin_obj.parent = bus
            fin_obj.matrix_parent_inverse.identity()

    sci_boom_len   = 5.0 * S
    sci_boom_angle = math.radians(210)
    sci_boom_mesh = make_cylinder(f"Voyager_{suffix}_Sci_Boom_Mesh", 0.02 * S, sci_boom_len, segs=6)
    sbx = math.cos(sci_boom_angle) * sci_boom_len * 0.5
    sby = math.sin(sci_boom_angle) * sci_boom_len * 0.5
    sci_boom_obj = new_obj(f"Voyager_{suffix}_Sci_Boom", sci_boom_mesh, col, mat_strut, loc=(sbx, sby, 0.05 * S), rot=(math.pi / 2.0, 0, sci_boom_angle + math.pi / 2.0))
    sci_boom_obj.parent = bus
    sci_boom_obj.matrix_parent_inverse.identity()

    tip_x_s = math.cos(sci_boom_angle) * sci_boom_len
    tip_y_s = math.sin(sci_boom_angle) * sci_boom_len
    mag_mesh = make_box(f"Voyager_{suffix}_MAG_Mesh", 0.12 * S, 0.08 * S, 0.22 * S)
    mag_obj = new_obj(f"Voyager_{suffix}_MAG", mag_mesh, col, mat_elec, loc=(tip_x_s, tip_y_s, 0.05 * S))
    mag_obj.parent = bus
    mag_obj.matrix_parent_inverse.identity()

    pls_mesh = make_cone(f"Voyager_{suffix}_PLS_Mesh", 0.16 * S, 0.06 * S, 0.20 * S, segs=10)
    pls_x = math.cos(sci_boom_angle) * sci_boom_len * 0.45
    pls_y = math.sin(sci_boom_angle) * sci_boom_len * 0.45
    pls_obj = new_obj(f"Voyager_{suffix}_PLS", pls_mesh, col, mat_elec, loc=(pls_x, pls_y, 0.06 * S), rot=(math.pi / 2.0, 0, sci_boom_angle + math.pi / 2.0))
    pls_obj.parent = bus
    pls_obj.matrix_parent_inverse.identity()

    return bus

# ──────────────────────────────────────────────────────────────────────────────
# TRAJECTORY KEYFRAMING
# ──────────────────────────────────────────────────────────────────────────────

def get_action_fcurves(action):
    fcurves = []
    if hasattr(action, "fcurves") and action.fcurves:
        fcurves.extend(action.fcurves)
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in getattr(layer, "strips", []):
                cbs = getattr(strip, "channelbags", [])
                if hasattr(cbs, "values"): cbs = cbs.values()
                for cb in cbs:
                    if hasattr(cb, "fcurves"): fcurves.extend(cb.fcurves)
    return fcurves


def set_trajectory_keyframes(probe_root, probe_bus, waypoints_years, label):
    probe_root.animation_data_clear()
    probe_root.animation_data_create()

    action_loc = bpy.data.actions.new(f"Voyager_{label}_Location")
    probe_root.animation_data.action = action_loc

    for (year, x, y, z) in waypoints_years:
        frame = year_to_frame(year)
        probe_root.location = (x, y, z)
        probe_root.keyframe_insert(data_path="location", frame=frame)

    fcurves_loc = get_action_fcurves(action_loc)
    for fcurve in fcurves_loc:
        if fcurve.data_path == "location":
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'BEZIER'
                kf.handle_left_type  = 'VECTOR'
                kf.handle_right_type = 'VECTOR'

    probe_bus.animation_data_clear()
    probe_bus.animation_data_create()
    action_rot = bpy.data.actions.new(f"Voyager_{label}_Rotation")
    probe_bus.animation_data.action = action_rot

    for (year, x, y, z) in waypoints_years:
        frame = year_to_frame(year)
        years_elapsed = year - waypoints_years[0][0]
        spin_rad = years_elapsed * math.tau * 0.15
        probe_bus.rotation_euler = (
            math.radians(5) * math.sin(spin_rad * 0.3),
            spin_rad * 0.25,
            spin_rad,
        )
        probe_bus.keyframe_insert(data_path="rotation_euler", frame=frame)

    fcurves_rot = get_action_fcurves(action_rot)
    for fcurve in fcurves_rot:
        if fcurve.data_path == "rotation_euler":
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'

    print(f"   ✅ {len(waypoints_years)} trajectory keyframes generated for Voyager {label}")
    return action_loc


def build_trajectory_curve(name, action_loc, start_year, end_year, col, color):
    old_c = bpy.data.objects.get(name)
    if old_c: bpy.data.objects.remove(old_c, do_unlink=True)
    
    old_taper = bpy.data.objects.get(f"Taper_{name}")
    if old_taper: bpy.data.objects.remove(old_taper, do_unlink=True)

    curve_data = bpy.data.curves.new(name, type='CURVE')
    curve_data.dimensions  = '3D'
    curve_data.bevel_depth = 0.22
    curve_data.bevel_resolution = 2
    curve_data.use_fill_caps = True
    curve_data.use_map_taper = True

    taper_cdata = bpy.data.curves.new(f"Taper_{name}", type='CURVE')
    taper_cdata.dimensions = '2D'
    taper_sp = taper_cdata.splines.new('NURBS')
    taper_sp.points.add(3)
    taper_sp.points[0].co = (-1.0, 0.16, 0.0, 1.0)
    taper_sp.points[1].co = (-0.35, 0.90, 0.0, 1.0)
    taper_sp.points[2].co = ( 0.35, 0.90, 0.0, 1.0)
    taper_sp.points[3].co = ( 1.0, 0.01, 0.0, 1.0)
    taper_sp.use_endpoint_u = True
    taper_obj = bpy.data.objects.new(f"Taper_{name}", taper_cdata)
    col.objects.link(taper_obj)
    taper_obj.hide_viewport = False; taper_obj.hide_render = False
    curve_data.taper_object = taper_obj

    start_frame = int(year_to_frame(start_year))
    end_frame = int(year_to_frame(end_year))

    fcurves = get_action_fcurves(action_loc)
    fc_x = next((fc for fc in fcurves if fc.data_path == "location" and fc.array_index == 0), None)
    fc_y = next((fc for fc in fcurves if fc.data_path == "location" and fc.array_index == 1), None)
    fc_z = next((fc for fc in fcurves if fc.data_path == "location" and fc.array_index == 2), None)

    samples = []
    curve_step = 3
    for f in range(start_frame, end_frame + 1, curve_step):
        x = fc_x.evaluate(f) if fc_x else 0.0
        y = fc_y.evaluate(f) if fc_y else 0.0
        z = fc_z.evaluate(f) if fc_z else 0.0
        samples.append((x, y, z))

    dists = [0.0]
    for i in range(1, len(samples)):
        p1 = samples[i-1]; p2 = samples[i]
        d = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
        dists.append(dists[-1] + d)

    spline = curve_data.splines.new('POLY')
    spline.points.add(len(samples) - 1)
    for i, (x, y, z) in enumerate(samples):
        spline.points[i].co = (x, y, z, 1.0)

    # Keyframe moving trails
    curve_data.animation_data_create()
    keyframe_step = 15
    total_pts = len(samples)
    kf_frames = list(range(start_frame, end_frame, keyframe_step))
    if kf_frames[-1] != end_frame: kf_frames.append(end_frame)
        
    for f in kf_frames:
        idx = min(total_pts - 1, (f - start_frame) // curve_step)
        bevel_end = idx / (total_pts - 1) if total_pts > 1 else 0.0
        curve_data.bevel_factor_end = bevel_end
        curve_data.keyframe_insert(data_path="bevel_factor_end", frame=f)
        
        target_dist = max(0.0, dists[idx] - VOYAGER_TRAIL_PHYSICAL_LENGTH)
        start_idx = 0
        for i in range(idx):
            if dists[i] >= target_dist:
                start_idx = i
                break
        
        bevel_start = start_idx / (total_pts - 1) if total_pts > 1 else 0.0
        curve_data.bevel_factor_start = bevel_start
        curve_data.keyframe_insert(data_path="bevel_factor_start", frame=f)

    if curve_data.animation_data and curve_data.animation_data.action:
        for fc in get_action_fcurves(curve_data.animation_data.action):
            if fc.data_path in ["bevel_factor_end", "bevel_factor_start"]:
                for kf in fc.keyframe_points: kf.interpolation = 'LINEAR'

    curve_obj = bpy.data.objects.new(name, curve_data)
    col.objects.link(curve_obj)

    curve_obj.animation_data_create()
    curve_obj.hide_viewport = True; curve_obj.hide_render = True
    curve_obj.keyframe_insert(data_path="hide_viewport", frame=0)
    curve_obj.keyframe_insert(data_path="hide_render", frame=0)
    curve_obj.keyframe_insert(data_path="hide_viewport", frame=start_frame - 1)
    curve_obj.keyframe_insert(data_path="hide_render", frame=start_frame - 1)
    curve_obj.hide_viewport = False; curve_obj.hide_render = False
    curve_obj.keyframe_insert(data_path="hide_viewport", frame=start_frame)
    curve_obj.keyframe_insert(data_path="hide_render", frame=start_frame)

    mat_name = f"Voyager_{name}_TrailMat"
    old_m = bpy.data.materials.get(mat_name)
    if old_m: bpy.data.materials.remove(old_m)
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    emit = mat.node_tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*color, 1.0)
    emit.inputs["Strength"].default_value = 2.5
    mat.node_tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    curve_data.materials.append(mat)

    return curve_obj


def add_flyby_marker(name, position, col, color, reveal_frame=None):
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    mesh = make_cylinder(f"{name}_Mesh", 0.80, 0.80, segs=16)
    mat  = make_mat(f"{name}_Mat", color[:3], roughness=0.2, metallic=0.0, emission_color=color[:3], emission_strength=1.8)
    obj  = new_obj(name, mesh, col, mat, loc=position)
    obj.hide_render = True

    if reveal_frame is not None:
        obj.animation_data_create()
        obj.hide_viewport = True; obj.hide_render = True
        obj.keyframe_insert(data_path="hide_viewport", frame=0)
        obj.keyframe_insert(data_path="hide_render", frame=0)
        obj.keyframe_insert(data_path="hide_viewport", frame=reveal_frame - 1)
        obj.keyframe_insert(data_path="hide_render", frame=reveal_frame - 1)
        obj.hide_viewport = False; obj.hide_render = False
        obj.keyframe_insert(data_path="hide_viewport", frame=reveal_frame)
        obj.keyframe_insert(data_path="hide_render", frame=reveal_frame)
    return obj


def add_voyager_label(parent_obj, text, suffix, col):
    name = f"Voyager_{suffix}_Label"
    tdata = bpy.data.curves.get(name)
    if tdata: bpy.data.curves.remove(tdata)
    cd = bpy.data.curves.new(name, type='FONT')
    cd.body = text
    cd.size = 1.0
    cd.align_x = 'CENTER'; cd.align_y = 'BOTTOM'
    
    mat = bpy.data.materials.get("Text_Bright_Mat")
    if not mat:
        mat = bpy.data.materials.new("Text_Bright_Mat")
        mat.use_nodes = True
        mat.node_tree.nodes.clear()
        mout = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        emit = mat.node_tree.nodes.new("ShaderNodeEmission")
        emit.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        emit.inputs["Strength"].default_value = 1.0
        mat.node_tree.links.new(emit.outputs["Emission"], mout.inputs["Surface"])
        
    cd.materials.append(mat)
    obj = bpy.data.objects.new(name, cd)
    col.objects.link(obj)
    obj.show_in_front = True
    obj.parent = parent_obj
    obj.matrix_parent_inverse.identity()
    obj.location = (0.0, 0.0, 2.0)
    obj.scale = (1.5, 1.5, 1.5)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    
    for attr in ["visible_glossy", "visible_diffuse", "visible_shadow", "visible_transmission", "visible_volume_scatter"]:
        setattr(obj, attr, False)
        
    cam = bpy.data.objects.get("Camera") or bpy.context.scene.camera
    if cam:
        con = obj.constraints.new(type='COPY_ROTATION')
        con.target = cam
    return obj

# ──────────────────────────────────────────────────────────────────────────────
# FLYBY INFOGRAPHICS & HUD LABELS
# ──────────────────────────────────────────────────────────────────────────────

def clean_existing_labels():
    root_obj = bpy.data.objects.get("Voyager_Flyby_Legend_Root")
    if root_obj: bpy.data.objects.remove(root_obj, do_unlink=True)
        
    for item in FLYBY_DATA:
        names_to_clean = [item["name"], f"{item['name']}_Marker", f"{item['name']}_HUD"]
        for name in names_to_clean:
            obj = bpy.data.objects.get(name)
            if obj: bpy.data.objects.remove(obj, do_unlink=True)
            tdata = bpy.data.curves.get(name)
            if tdata: bpy.data.curves.remove(tdata)
            mat_name = f"Mat_{name}"
            mat = bpy.data.materials.get(mat_name)
            if mat: bpy.data.materials.remove(mat)


def create_flyby_labels(col):
    print("✍️ Generating Voyager flyby infographics and HUD legends...")
    clean_existing_labels()

    cam = bpy.data.objects.get("Camera") or bpy.context.scene.camera
    sorted_flybys = sorted(FLYBY_DATA, key=lambda x: x["frame"])
    letters = {item["name"]: chr(65 + i) for i, item in enumerate(sorted_flybys)}

    legend_root = bpy.data.objects.new("Voyager_Flyby_Legend_Root", None)
    legend_root.empty_display_type = 'PLAIN_AXES'
    legend_root.empty_display_size = 2.0
    col.objects.link(legend_root)
    legend_root.location = LEGEND_LOCATION
    legend_root.scale = LEGEND_SCALE

    if cam:
        con = legend_root.constraints.new(type='COPY_ROTATION')
        con.target = cam

    for idx, item in enumerate(sorted_flybys):
        marker = bpy.data.objects.get(item["marker"])
        if not marker: continue

        letter = letters[item["name"]]

        # 1. 3D Marker Label (A, B, C...)
        marker_name = f"{item['name']}_Marker"
        
        old_mc = bpy.data.curves.get(marker_name)
        if old_mc: bpy.data.curves.remove(old_mc)
            
        tdata_marker = bpy.data.curves.new(marker_name, type='FONT')
        tdata_marker.body = letter
        tdata_marker.size = 3.0
        tdata_marker.align_x = 'LEFT'; tdata_marker.align_y = 'CENTER'
        tdata_marker.extrude = 0.05
        
        mat_marker_name = f"Mat_{marker_name}"
        mat_marker = bpy.data.materials.new(mat_marker_name)
        mat_marker.use_nodes = True
        mat_marker.node_tree.nodes.clear()
        out_marker = mat_marker.node_tree.nodes.new("ShaderNodeOutputMaterial")
        emit_marker = mat_marker.node_tree.nodes.new("ShaderNodeEmission")
        emit_marker.inputs["Color"].default_value = (*item["color"], 1.0)
        emit_marker.inputs["Strength"].default_value = 5.0
        mat_marker.node_tree.links.new(emit_marker.outputs["Emission"], out_marker.inputs["Surface"])
        tdata_marker.materials.append(mat_marker)

        obj_marker = bpy.data.objects.new(marker_name, tdata_marker)
        col.objects.link(obj_marker)

        loc = marker.location
        offset_x = 3.2
        obj_marker.location = (loc.x + offset_x, loc.y, loc.z)

        if cam:
            con = obj_marker.constraints.new(type='COPY_ROTATION')
            con.target = cam

        for attr in ["visible_glossy", "visible_diffuse", "visible_shadow", "visible_transmission", "visible_volume_scatter"]:
            setattr(obj_marker, attr, False)

        # 2. Static HUD Legend overlay stack
        hud_name = f"{item['name']}_HUD"
        
        old_hc = bpy.data.curves.get(hud_name)
        if old_hc: bpy.data.curves.remove(old_hc)
            
        tdata_hud = bpy.data.curves.new(hud_name, type='FONT')
        lines = item["text"].split("\n")
        clean_text = f"{lines[0]} - {lines[1]} - {lines[2]} ({lines[3]})" if len(lines) >= 4 else " - ".join(lines)
        tdata_hud.body = f"{letter}: {clean_text}"
        tdata_hud.size = LEGEND_TEXT_SIZE
        tdata_hud.align_x = 'LEFT'; tdata_hud.align_y = 'TOP'
        tdata_hud.extrude = 0.01
        
        mat_hud_name = f"Mat_{hud_name}"
        mat_hud = bpy.data.materials.new(mat_hud_name)
        mat_hud.use_nodes = True
        mat_hud.node_tree.nodes.clear()
        out_hud = mat_hud.node_tree.nodes.new("ShaderNodeOutputMaterial")
        emit_hud = mat_hud.node_tree.nodes.new("ShaderNodeEmission")
        emit_hud.inputs["Color"].default_value = (*item["color"], 1.0)
        emit_hud.inputs["Strength"].default_value = 4.0
        mat_hud.node_tree.links.new(emit_hud.outputs["Emission"], out_hud.inputs["Surface"])
        tdata_hud.materials.append(mat_hud)

        obj_hud = bpy.data.objects.new(hud_name, tdata_hud)
        col.objects.link(obj_hud)
        obj_hud.parent = legend_root
        obj_hud.matrix_parent_inverse.identity()
        obj_hud.location = (0.0, -idx * LEGEND_LINE_GAP, 0.0)
        obj_hud.rotation_euler = (0, 0, 0)

        for attr in ["visible_glossy", "visible_diffuse", "visible_shadow", "visible_transmission", "visible_volume_scatter"]:
            setattr(obj_hud, attr, False)

        # Keyframe reveals
        for obj in [obj_marker, obj_hud]:
            obj.animation_data_clear()
            obj.animation_data_create()
            obj.hide_viewport = True; obj.hide_render = True
            obj.keyframe_insert(data_path="hide_viewport", frame=0)
            obj.keyframe_insert(data_path="hide_render", frame=0)
            obj.keyframe_insert(data_path="hide_viewport", frame=item["frame"] - 1)
            obj.keyframe_insert(data_path="hide_render", frame=item["frame"] - 1)
            obj.hide_viewport = False; obj.hide_render = False
            obj.keyframe_insert(data_path="hide_viewport", frame=item["frame"])
            obj.keyframe_insert(data_path="hide_render", frame=item["frame"])

def keyframe_visibility_recursive(obj, launch_frame):
    """Recursively apply visibility keyframes to an object and all its children."""
    obj.show_in_front = True  # Always draw Voyager parts in front of trails/paths in viewport
    if not obj.animation_data:
        obj.animation_data_create()
        
    # Hide at frame 0 and frame launch_frame - 1
    obj.hide_viewport = True
    obj.hide_render = True
    obj.keyframe_insert(data_path="hide_viewport", frame=0)
    obj.keyframe_insert(data_path="hide_render", frame=0)
    obj.keyframe_insert(data_path="hide_viewport", frame=launch_frame - 1)
    obj.keyframe_insert(data_path="hide_render", frame=launch_frame - 1)
    
    # Show at launch_frame
    obj.hide_viewport = False
    obj.hide_render = False
    obj.keyframe_insert(data_path="hide_viewport", frame=launch_frame)
    obj.keyframe_insert(data_path="hide_render", frame=launch_frame)
    
    for child in obj.children:
        keyframe_visibility_recursive(child, launch_frame)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN RUNNER
# ──────────────────────────────────────────────────────────────────────────────

def remove_voyager_objects():
    prefixes = ("Voyager_", "Taper_Voyager_")
    for o in list(bpy.data.objects):
        if any(o.name.startswith(p) for p in prefixes) or o.name == "Voyager_Flyby_Legend_Root":
            bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        if any(m.name.startswith(p) for p in prefixes):
            bpy.data.meshes.remove(m)
    for c in list(bpy.data.curves):
        if any(c.name.startswith(p) for p in prefixes):
            bpy.data.curves.remove(c)
    for mat in list(bpy.data.materials):
        if any(mat.name.startswith(p) for p in prefixes) or mat.name.startswith("Mat_Voyager_"):
            bpy.data.materials.remove(mat)
    for act in list(bpy.data.actions):
        if any(act.name.startswith(p) for p in prefixes):
            bpy.data.actions.remove(act)


def run_mission():
    print("\n🛸 Running Consolidated Voyager Mission setup...")
    col = bpy.data.collections.get(COLLECTION_NAME)
    if col is None:
        col = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(col)

    remove_voyager_objects()

    v1_wp = list(V1_WAYPOINTS_YEARS)
    v2_wp = list(V2_WAYPOINTS_YEARS)

    earth = bpy.data.objects.get("Earth")
    jupiter = bpy.data.objects.get("Jupiter")
    saturn = bpy.data.objects.get("Saturn")
    uranus = bpy.data.objects.get("Uranus")
    neptune = bpy.data.objects.get("Neptune")
    current_frame = bpy.context.scene.frame_current

    # Sync waypoints to planetary positions at flyby dates
    if earth:
        bpy.context.scene.frame_set(int(year_to_frame(v1_wp[0][0])))
        v1_wp[0] = (v1_wp[0][0], *earth.matrix_world.translation)
        bpy.context.scene.frame_set(int(year_to_frame(v2_wp[0][0])))
        v2_wp[0] = (v2_wp[0][0], *earth.matrix_world.translation)
    
    if jupiter:
        bpy.context.scene.frame_set(int(year_to_frame(v1_wp[1][0])))
        v1_wp[1] = (v1_wp[1][0], *jupiter.matrix_world.translation)
        bpy.context.scene.frame_set(int(year_to_frame(v2_wp[1][0])))
        v2_wp[1] = (v2_wp[1][0], *jupiter.matrix_world.translation)

    if saturn:
        bpy.context.scene.frame_set(int(year_to_frame(v1_wp[2][0])))
        v1_wp[2] = (v1_wp[2][0], *saturn.matrix_world.translation)
        bpy.context.scene.frame_set(int(year_to_frame(v2_wp[2][0])))
        v2_wp[2] = (v2_wp[2][0], *saturn.matrix_world.translation)

    if uranus:
        bpy.context.scene.frame_set(int(year_to_frame(v2_wp[3][0])))
        v2_wp[3] = (v2_wp[3][0], *uranus.matrix_world.translation)

    if neptune:
        bpy.context.scene.frame_set(int(year_to_frame(v2_wp[4][0])))
        v2_wp[4] = (v2_wp[4][0], *neptune.matrix_world.translation)

    # Compute V1 Escape Path
    p_jup = Vector(v1_wp[1][1:])
    p_sat = Vector(v1_wp[2][1:])
    d_xy = (p_sat - p_jup); d_xy.z = 0.0
    if d_xy.length > 1e-6: d_xy.normalize()
    else: d_xy = Vector((1.0, 0.0, 0.0))
    v1_esc = d_xy * math.cos(math.radians(35)) + Vector((0.0, 0.0, 1.0)) * math.sin(math.radians(35))

    v1_esc_dists = {1990.0: 180.0, 2004.0: 280.0, 2024.0: 380.0, 2040.0: 470.0}
    for idx in range(3, len(v1_wp)):
        y = v1_wp[idx][0]
        pos = p_sat + v1_esc * (v1_esc_dists.get(y, 180.0) - DISTANCE["Saturn"])
        v1_wp[idx] = (y, pos.x, pos.y, pos.z)

    # Compute V2 Escape Path
    p_ura = Vector(v2_wp[3][1:])
    p_nep = Vector(v2_wp[4][1:])
    d_xy2 = (p_nep - p_ura); d_xy2.z = 0.0
    if d_xy2.length > 1e-6: d_xy2.normalize()
    else: d_xy2 = Vector((1.0, 0.0, 0.0))
    v2_esc = d_xy2 * math.cos(math.radians(48)) - Vector((0.0, 0.0, 1.0)) * math.sin(math.radians(48))

    v2_esc_dists = {2004.0: 220.0, 2024.0: 310.0, 2040.0: 390.0}
    for idx in range(5, len(v2_wp)):
        y = v2_wp[idx][0]
        pos = p_nep + v2_esc * (v2_esc_dists.get(y, 220.0) - DISTANCE["Neptune"])
        v2_wp[idx] = (y, pos.x, pos.y, pos.z)

    bpy.context.scene.frame_set(current_frame)

    mat_body_v1 = make_mylar_material("Voyager_V1_Mylar")
    mat_body_v2 = make_mylar_material("Voyager_V2_Mylar")
    mat_dish_v1 = make_dish_material("Voyager_V1_Dish")
    mat_dish_v2 = make_dish_material("Voyager_V2_Dish")
    mat_rtg_v1  = make_rtg_material("Voyager_V1_RTG")
    mat_rtg_v2  = make_rtg_material("Voyager_V2_RTG")
    mat_strut   = make_strut_material("Voyager_Strut")
    mat_elec    = make_electronics_material("Voyager_Elec")
    mat_gold    = make_gold_foil_material("Voyager_Gold")

    S = VOYAGER_VISUAL_SCALE

    # VOYAGER 1 BUILD
    v1_root = bpy.data.objects.new("Voyager_V1_Root", None)
    v1_root.empty_display_type = 'ARROWS'; v1_root.empty_display_size = 0.5
    col.objects.link(v1_root)
    v1_root.location = v1_wp[0][1:]
    v1_bus = build_voyager_geometry(v1_root, col, S, "V1", mat_body_v1, mat_dish_v1, mat_rtg_v1, mat_strut, mat_elec, mat_gold, mat_body_v1)
    action_loc_v1 = set_trajectory_keyframes(v1_root, v1_bus, v1_wp, "V1")
    add_voyager_label(v1_root, "Voyager 1", "V1", col)
    build_trajectory_curve("Voyager_V1_Trajectory", action_loc_v1, v1_wp[0][0], v1_wp[-1][0], col, color=(0.4, 0.8, 1.0))
    add_flyby_marker("Voyager_V1_Flyby_Jupiter", v1_wp[1][1:], col, (0.85, 0.65, 0.35), reveal_frame=int(year_to_frame(v1_wp[1][0])))
    add_flyby_marker("Voyager_V1_Flyby_Saturn", v1_wp[2][1:], col, (0.95, 0.88, 0.60), reveal_frame=int(year_to_frame(v1_wp[2][0])))
    keyframe_visibility_recursive(v1_root, int(year_to_frame(v1_wp[0][0])))

    # VOYAGER 2 BUILD
    v2_root = bpy.data.objects.new("Voyager_V2_Root", None)
    v2_root.empty_display_type = 'ARROWS'; v2_root.empty_display_size = 0.5
    col.objects.link(v2_root)
    v2_root.location = v2_wp[0][1:]
    v2_bus = build_voyager_geometry(v2_root, col, S, "V2", mat_body_v2, mat_dish_v2, mat_rtg_v2, mat_strut, mat_elec, mat_gold, mat_body_v2)
    action_loc_v2 = set_trajectory_keyframes(v2_root, v2_bus, v2_wp, "V2")
    add_voyager_label(v2_root, "Voyager 2", "V2", col)
    build_trajectory_curve("Voyager_V2_Trajectory", action_loc_v2, v2_wp[0][0], v2_wp[-1][0], col, color=(1.0, 0.55, 0.25))
    add_flyby_marker("Voyager_V2_Flyby_Jupiter", v2_wp[1][1:], col, (0.85, 0.65, 0.35), reveal_frame=int(year_to_frame(v2_wp[1][0])))
    add_flyby_marker("Voyager_V2_Flyby_Saturn", v2_wp[2][1:], col, (0.95, 0.88, 0.60), reveal_frame=int(year_to_frame(v2_wp[2][0])))
    add_flyby_marker("Voyager_V2_Flyby_Uranus", v2_wp[3][1:], col, (0.45, 0.90, 0.95), reveal_frame=int(year_to_frame(v2_wp[3][0])))
    add_flyby_marker("Voyager_V2_Flyby_Neptune", v2_wp[4][1:], col, (0.25, 0.40, 1.00), reveal_frame=int(year_to_frame(v2_wp[4][0])))
    keyframe_visibility_recursive(v2_root, int(year_to_frame(v2_wp[0][0])))

    # Generate HUD Labels and stack
    create_flyby_labels(col)

    # Set timeline frame ranges
    scene = bpy.context.scene
    launch_frame = int(year_to_frame(min(v1_wp[0][0], v2_wp[0][0])))
    scene.frame_start = max(0, launch_frame - BASE_FRAMES)
    scene.frame_end   = int(year_to_frame(2050))
    scene.frame_set(int(year_to_frame(1979)))

    print("\n✅ Voyager Mission consolidated setup completed successfully!")


if __name__ == "__main__":
    run_mission()
