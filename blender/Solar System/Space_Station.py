"""
Space_Station.py
================
Consolidated ISS-Style Space Station — Procedural Build + Accurate Orbital Animation.
Consolidated and migrated to the Solar System Consolidated collection.
"""

import bpy
import bmesh
import math
import random

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION & SYNC (with Orrery Scene)
# ─────────────────────────────────────────────────────────────────────────────

BASE_FRAMES        = 300      # frames = 1 Earth year
EARTH_OBJECT_NAME  = "Earth"  # name of the Earth sphere object
EARTH_SPHERE_RADIUS_BU = 1.0  # fallback if Earth is not found

# Visual gap above Earth surface (in Blender Units) so the station is clearly visible.
VISUAL_GAP_BU = 0.18

# Orbital speed: 120 frames per 1 visible orbit
ISS_VISUAL_PERIOD_FRAMES = 120

# Physical ratio of ISS orbital radius to Earth radius
ISS_ORBITAL_RADIUS_RATIO = 1.0659  # (6371 + 420) / 6371
ISS_INCLINATION_DEG = 51.6         # orbital inclination to Earth equator

# Visual scale of the ISS.
# All dimensions are in meters, and scaled by: METER_TO_BU = Earth_Radius_BU * (ISS_VISUAL_SCALE / 10.0)
ISS_VISUAL_SCALE = 0.08

# Collection name for all ISS objects
COLLECTION_NAME = "Space Station"

# Colors (RGBA)
COLOR_TRUSS        = (0.90, 0.90, 0.92, 1.0)   # bright metallic gray/white aluminum
COLOR_MODULE       = (0.92, 0.92, 0.92, 1.0)   # clean off-white
COLOR_ZARYA        = (0.70, 0.55, 0.25, 1.0)   # olive-gold/yellow thermal blankets
COLOR_SILVER       = (0.90, 0.90, 0.92, 1.0)   # shiny silver metallic aluminum
COLOR_SOLAR_PANEL  = (0.05, 0.08, 0.22, 1.0)   # deep blue-purple photovoltaic
COLOR_RADIATOR     = (0.95, 0.95, 0.95, 1.0)   # white thermal panels
COLOR_SOLAR_FRAME  = (0.85, 0.65, 0.30, 1.0)   # golden blanket frame/mast
COLOR_DOCK         = (0.85, 0.85, 0.85, 1.0)   # light gray docking port
COLOR_DARK_METAL   = (0.35, 0.35, 0.38, 1.0)   # dark gray structural joints
COLOR_RED          = (0.85, 0.10, 0.10, 1.0)   # red warning details

# ─────────────────────────────────────────────────────────────────────────────
# MATERIAL CREATION UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def simple_material(name, color, roughness=0.5, metallic=0.0):
    """Create a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color  # viewport color
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    out  = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def white_module_material(name, color):
    """Create off-white module material with procedural panel lines."""
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color  # viewport color
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.inputs["Metallic"].default_value = 0.1
    
    try:
        tex_coord = nodes.new("ShaderNodeTexCoord")
        mapping = nodes.new("ShaderNodeMapping")
        
        wave = nodes.new("ShaderNodeTexWave")
        wave.wave_type = 'BANDS'
        wave.bands_direction = 'X'
        wave.inputs["Scale"].default_value = 15.0
        wave.inputs["Distortion"].default_value = 0.0
        
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.15
        bump.inputs["Distance"].default_value = 0.05
        
        links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
        links.new(wave.outputs["Color"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    except Exception as e:
        print(f"   ℹ Procedural panel shader fallback: {e}")
        
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def solar_panel_material(name, color=COLOR_SOLAR_PANEL):
    """Create reflective solar panel material with cell grid and subtle emission."""
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color  # viewport color
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Metallic"].default_value = 0.2
    
    # Subtle emission to simulate space glow
    bsdf.inputs["Emission Color"].default_value = (0.01, 0.01, 0.02, 1.0)
    if "Emission Strength" in bsdf.inputs:
        scene_cycles = getattr(bpy.context.scene, "cycles", None)
        bsdf.inputs["Emission Strength"].default_value = 0.1
        
    try:
        tex_coord = nodes.new("ShaderNodeTexCoord")
        mapping = nodes.new("ShaderNodeMapping")
        
        voronoi = nodes.new("ShaderNodeTexVoronoi")
        voronoi.feature = 'DISTANCE_TO_EDGE'
        voronoi.inputs["Scale"].default_value = 40.0
        
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.2
        bump.inputs["Distance"].default_value = 0.02
        
        links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], voronoi.inputs["Vector"])
        links.new(voronoi.outputs["Distance"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        
        # Specular coat
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = 0.3
            bsdf.inputs["Coat Roughness"].default_value = 0.1
            
    except Exception as e:
        print(f"   ℹ Procedural solar panel shader fallback: {e}")
        
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

# ─────────────────────────────────────────────────────────────────────────────
# GEOMETRY GENERATORS (bmesh based)
# ─────────────────────────────────────────────────────────────────────────────

def make_box(name, sx, sy, sz):
    """Manually construct a rectangular box mesh."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    hx, hy, hz = sx/2.0, sy/2.0, sz/2.0
    verts = [
        bm.verts.new(( hx,  hy,  hz)), bm.verts.new(( hx, -hy,  hz)),
        bm.verts.new((-hx, -hy,  hz)), bm.verts.new((-hx,  hy,  hz)),
        bm.verts.new(( hx,  hy, -hz)), bm.verts.new(( hx, -hy, -hz)),
        bm.verts.new((-hx, -hy, -hz)), bm.verts.new((-hx,  hy, -hz)),
    ]
    bm.verts.ensure_lookup_table()
    faces = [
        [0,1,2,3], [4,7,6,5],
        [0,3,7,4], [1,5,6,2],
        [0,4,5,1], [3,2,6,7],
    ]
    for f in faces:
        bm.faces.new([verts[i] for i in f])
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def make_cylinder_mesh(name, radius, height, segs=16):
    """Manually construct a cylinder mesh."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    half = height / 2.0
    
    top_center = bm.verts.new((0, 0,  half))
    bot_center = bm.verts.new((0, 0, -half))
    
    top_ring = []
    bot_ring = []
    for i in range(segs):
        angle = (i / segs) * math.tau
        c, s  = math.cos(angle), math.sin(angle)
        top_ring.append(bm.verts.new((c * radius, s * radius,  half)))
        bot_ring.append(bm.verts.new((c * radius, s * radius, -half)))
        
    bm.verts.ensure_lookup_table()
    
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new([top_ring[i], top_ring[j], bot_ring[j], bot_ring[i]])
        bm.faces.new([top_center, top_ring[j], top_ring[i]])
        bm.faces.new([bot_center, bot_ring[i], bot_ring[j]])
        
    bm.to_mesh(mesh)
    bm.free()
    
    # Shade smooth all faces of this curved geometry
    for f in mesh.polygons:
        f.use_smooth = True
        
    mesh.update()
    return mesh


def make_sphere_slice_mesh(name, radius, height, segs=16, rings=8, dome=True):
    """Manually construct a hemisphere or dome slice."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    v_rows = []
    for r in range(rings + 1):
        phi = (r / rings) * (math.pi / 2.0)
        z = radius * math.cos(phi)
        r_slice = radius * math.sin(phi)
        
        z_scaled = z * (height / radius)
        
        row = []
        for s in range(segs):
            theta = (s / segs) * math.tau
            x = r_slice * math.cos(theta)
            y = r_slice * math.sin(theta)
            row.append(bm.verts.new((x, y, z_scaled)))
        v_rows.append(row)
        
    bm.verts.ensure_lookup_table()
    
    for r in range(rings):
        for s in range(segs):
            s_next = (s + 1) % segs
            bm.faces.new((v_rows[r][s], v_rows[r][s_next], v_rows[r+1][s_next], v_rows[r+1][s]))
            
    if dome:
        v_center_bottom = bm.verts.new((0, 0, 0))
        for s in range(segs):
            s_next = (s + 1) % segs
            bm.faces.new((v_center_bottom, v_rows[rings][s], v_rows[rings][s_next]))
            
    bm.to_mesh(mesh)
    bm.free()
    
    # Shade smooth all faces of this curved geometry
    for f in mesh.polygons:
        f.use_smooth = True
        
    mesh.update()
    return mesh


def make_lattice_truss_mesh(name, length, width, height, num_bays):
    """Construct a rectangular lattice truss mesh with repeating triangular braces as faces."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    hl = length / 2.0
    hw = width / 2.0
    hh = height / 2.0
    
    sections = []
    for i in range(num_bays + 1):
        x = -hl + (i / num_bays) * length
        v0 = bm.verts.new((x, -hw, -hh))
        v1 = bm.verts.new((x,  hw, -hh))
        v2 = bm.verts.new((x,  hw,  hh))
        v3 = bm.verts.new((x, -hw,  hh))
        sections.append((v0, v1, v2, v3))
        
    bm.verts.ensure_lookup_table()
    
    # Create side faces split by diagonals for each bay
    for i in range(num_bays):
        s1 = sections[i]
        s2 = sections[i+1]
        
        # We have 4 sides for each bay:
        # Side 0: bottom face (v0, v1, w1, w0)
        # Side 1: right face  (v1, v2, w2, w1)
        # Side 2: top face    (v2, v3, w3, w2)
        # Side 3: left face   (v3, v0, w0, w3)
        
        for c in range(4):
            v_a = s1[c]
            v_b = s1[(c+1)%4]
            w_b = s2[(c+1)%4]
            w_a = s2[c]
            
            # Alternating diagonal direction per bay for realistic triangular lattice truss
            if (i + c) % 2 == 0:
                bm.faces.new((v_a, v_b, w_b))
                bm.faces.new((v_a, w_b, w_a))
            else:
                bm.faces.new((v_a, v_b, w_a))
                bm.faces.new((v_b, w_b, w_a))
                
    # Add end cap faces to ensure boundaries are closed
    bm.faces.new((sections[0][3], sections[0][2], sections[0][1], sections[0][0]))
    bm.faces.new((sections[num_bays][0], sections[num_bays][1], sections[num_bays][2], sections[num_bays][3]))
            
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh

# ─────────────────────────────────────────────────────────────────────────────
# OBJECT INSTANTIATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def add_obj(name, mesh, mat, parent, col, loc=(0,0,0), rot=(0,0,0), scale=(1,1,1)):
    """Instantiate and configure a standard mesh object."""
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    obj.scale = scale
    obj.parent = parent
    if parent:
        obj.matrix_parent_inverse.identity()
    obj.data.materials.append(mat)
    return obj


def add_lattice_obj(name, length, width, height, num_bays, strut_thickness, mat, parent, col, loc=(0,0,0), rot=(0,0,0)):
    """Create a lattice truss object by applying a Wireframe modifier."""
    mesh = make_lattice_truss_mesh(name + "_Mesh", length, width, height, num_bays)
    obj = add_obj(name, mesh, mat, parent, col, loc=loc, rot=rot)
    
    wire = obj.modifiers.new(name="TrussWire", type='WIREFRAME')
    wire.thickness = strut_thickness
    wire.use_boundary = True
    wire.use_replace = True
    return obj


def build_module(name, length, radius, mat, parent, col, loc=(0,0,0), rot=(0,0,0)):
    """Assemble a cylindrical pressure module with rounded caps and structural ribs."""
    cyl_len = length - (2.0 * radius)
    if cyl_len <= 0:
        cyl_len = length * 0.5
        radius = length * 0.25
        
    cyl_mesh = make_cylinder_mesh(f"{name}_CylMesh", radius, cyl_len, segs=16)
    module_parent = add_obj(name, cyl_mesh, mat, parent, col, loc=loc, rot=rot)
    
    cap_mesh = make_sphere_slice_mesh(f"{name}_CapMesh", radius, radius, segs=16, rings=8, dome=True)
    add_obj(f"{name}_Cap_Top", cap_mesh, mat, module_parent, col, loc=(0, 0, cyl_len/2.0), rot=(0, 0, 0))
    add_obj(f"{name}_Cap_Bottom", cap_mesh, mat, module_parent, col, loc=(0, 0, -cyl_len/2.0), rot=(0, math.pi, 0))
    
    rib_mesh = make_cylinder_mesh(f"{name}_RibMesh", radius * 1.02, length * 0.02, segs=16)
    num_ribs = 4
    for r in range(num_ribs):
        pos_z = -cyl_len/2.0 + (r / max(1, num_ribs - 1)) * cyl_len
        add_obj(f"{name}_Rib_{r}", rib_mesh, mat, module_parent, col, loc=(0, 0, pos_z))
        
    return module_parent


def add_truss_internal_details(parent, name, x_start, x_end, bays, truss_w, truss_h, M, col, mat_truss, mat_dark, mat_silver, mat_red, mat_dock):
    """Add detailed internal piping, boxes, and cross-braces inside the truss structure."""
    length = abs(x_end - x_start) * M
    center_x = (x_start + x_end) / 2.0 * M
    
    # 1. Run internal conduits/pipes (representing ammonia lines and power cables)
    pipe_radius = 0.12 * M
    pipe_mesh = make_cylinder_mesh(f"SpaceStation_Truss_{name}_Pipe_Mesh", pipe_radius, length, segs=8)
    
    # Run 2 pipes through the truss
    add_obj(
        name=f"SpaceStation_Truss_{name}_Pipe_1",
        mesh=pipe_mesh,
        mat=mat_silver,
        parent=parent,
        col=col,
        loc=(center_x, 0.35 * truss_w, -0.35 * truss_h),
        rot=(0, math.radians(90), 0)
    )
    add_obj(
        name=f"SpaceStation_Truss_{name}_Pipe_2",
        mesh=pipe_mesh,
        mat=mat_dark,
        parent=parent,
        col=col,
        loc=(center_x, -0.35 * truss_w, -0.35 * truss_h),
        rot=(0, math.radians(90), 0)
    )
    
    # 2. Run central power conduit (thicker, segmented)
    conduit_radius = 0.22 * M
    conduit_mesh = make_cylinder_mesh(f"SpaceStation_Truss_{name}_Conduit_Mesh", conduit_radius, length * 0.98, segs=8)
    add_obj(
        name=f"SpaceStation_Truss_{name}_Conduit",
        mesh=conduit_mesh,
        mat=mat_truss,
        parent=parent,
        col=col,
        loc=(center_x, 0.0, 0.0),
        rot=(0, math.radians(90), 0)
    )
    
    # 3. Add transverse bulkheads (open frames) at each bay boundary
    bulkhead_mesh = make_box(f"SpaceStation_Truss_{name}_Bulkhead_Mesh", 0.12 * M, truss_w * 0.95, truss_h * 0.95)
    for i in range(bays + 1):
        x_pos = (x_start + (i / bays) * (x_end - x_start)) * M
        bulk_obj = add_obj(
            name=f"SpaceStation_Truss_{name}_Bulkhead_{i}",
            mesh=bulkhead_mesh,
            mat=mat_dark,
            parent=parent,
            col=col,
            loc=(x_pos, 0, 0)
        )
        # Apply a Wireframe modifier to make the bulkhead an open structural frame (no solid block)
        wire = bulk_obj.modifiers.new(name="BulkheadWire", type='WIREFRAME')
        wire.thickness = 0.06 * M
        wire.use_replace = True
        
    # 4. Populate with random internal electronics and battery boxes (ORUs)
    random.seed(hash(name) % 1000)
    box_materials = [mat_silver, mat_dock, mat_dark]
    for b in range(bays):
        x_bay_center = (x_start + ((b + 0.5) / bays) * (x_end - x_start)) * M
        num_boxes = random.randint(1, 3)
        for j in range(num_boxes):
            bw = random.uniform(0.5, 0.9) * M
            bd = random.uniform(0.5, 0.9) * M
            bh = random.uniform(0.4, 0.8) * M
            
            box_mesh = make_box(f"SpaceStation_Truss_{name}_ORU_{b}_{j}_Mesh", bw, bd, bh)
            offset_y = random.uniform(-0.25, 0.25) * truss_w
            offset_z = random.uniform(-0.25, 0.25) * truss_h
            
            b_mat = random.choice(box_materials)
            if random.random() < 0.15:
                b_mat = mat_red
                
            add_obj(
                name=f"SpaceStation_Truss_{name}_ORU_{b}_{j}",
                mesh=box_mesh,
                mat=b_mat,
                parent=parent,
                col=col,
                loc=(x_bay_center, offset_y, offset_z)
            )

# ─────────────────────────────────────────────────────────────────────────────
# MAIN ISS GEOMETRY BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_iss_geometry(root, col, M):
    """Build the entire detailed ISS model procedurally, scaled by factor M."""
    
    for mn in ["SpaceStation_Truss", "SpaceStation_Module", "SpaceStation_Solar",
               "SpaceStation_Radiator", "SpaceStation_Frame", "SpaceStation_Dock", "SpaceStation_Gold",
               "SpaceStation_Zarya", "SpaceStation_Silver", "SpaceStation_Dark", "SpaceStation_Red"]:
        m = bpy.data.materials.get(mn)
        if m: bpy.data.materials.remove(m)
        
    mat_truss  = simple_material("SpaceStation_Truss",   COLOR_TRUSS,       roughness=0.4, metallic=0.9)
    mat_module = white_module_material("SpaceStation_Module", COLOR_MODULE)
    mat_zarya  = white_module_material("SpaceStation_Zarya",  COLOR_ZARYA)
    mat_silver = simple_material("SpaceStation_Silver",  COLOR_SILVER,      roughness=0.25, metallic=0.85)
    mat_dark   = simple_material("SpaceStation_Dark",    COLOR_DARK_METAL,  roughness=0.4, metallic=0.7)
    mat_red    = simple_material("SpaceStation_Red",     COLOR_RED,         roughness=0.5, metallic=0.1)
    mat_solar  = solar_panel_material("SpaceStation_Solar")
    mat_rad    = simple_material("SpaceStation_Radiator",COLOR_RADIATOR,    roughness=0.8, metallic=0.0)
    mat_frame  = simple_material("SpaceStation_Frame",   COLOR_SOLAR_FRAME, roughness=0.5, metallic=0.3)
    mat_dock   = simple_material("SpaceStation_Dock",    COLOR_DOCK,        roughness=0.5, metallic=0.2)
    mat_gold   = simple_material("SpaceStation_Gold",    (0.85, 0.65, 0.15, 1.0), roughness=0.3, metallic=0.8)

    # ── 1. Integrated Truss Structure (ITS) ──────────────────────────────────
    truss_w = 4.0 * M
    truss_h = 4.0 * M
    trut_strut = 0.12 * M
    
    truss_segments = [
        ("S0",    -5.0,   5.0,  3),
        ("S1",     5.0,  20.0,  4),
        ("S3_S4", 21.0,  36.0,  4),
        ("S5",    36.0,  39.0,  1),
        ("S6",    39.0,  54.0,  4),
        ("P1",   -20.0,  -5.0,  4),
        ("P3_P4",-36.0, -21.0,  4),
        ("P5",   -39.0, -36.0,  1),
        ("P6",   -54.0, -39.0,  4),
    ]

    for name, x_start, x_end, bays in truss_segments:
        length = abs(x_end - x_start) * M
        center_x = (x_start + x_end) / 2.0 * M
        add_lattice_obj(
            name=f"SpaceStation_Truss_{name}",
            length=length,
            width=truss_w,
            height=truss_h,
            num_bays=bays,
            strut_thickness=trut_strut,
            mat=mat_truss,
            parent=root,
            col=col,
            loc=(center_x, 0, 0),
            rot=(0, 0, 0)
        )
        
        # Populate truss with internal pipes, bulkheads, and mechanical ORUs (like real ISS)
        add_truss_internal_details(
            parent=root,
            name=name,
            x_start=x_start,
            x_end=x_end,
            bays=bays,
            truss_w=truss_w,
            truss_h=truss_h,
            M=M,
            col=col,
            mat_truss=mat_truss,
            mat_dark=mat_dark,
            mat_silver=mat_silver,
            mat_red=mat_red,
            mat_dock=mat_dock
        )

    # ── 2. Solar Alpha Rotary Joints (SARJ) ──────────────────────────────────
    sarj_mesh = make_cylinder_mesh("SpaceStation_SARJ_Mesh", 2.3 * M, 1.2 * M, segs=16)
    sarj_gear_mesh = make_cylinder_mesh("SpaceStation_SARJ_Gear_Mesh", 2.6 * M, 0.2 * M, segs=16)
    sarj_bracket_mesh = make_box("SpaceStation_SARJ_Bracket_Mesh", 0.4 * M, 0.8 * M, 0.6 * M)
    
    for side, sign in [("S", 1), ("P", -1)]:
        sarj_center_x = 20.5 * sign * M
        sarj_obj = add_obj(
            name=f"SpaceStation_SARJ_{side}",
            mesh=sarj_mesh,
            mat=mat_truss,
            parent=root,
            col=col,
            loc=(sarj_center_x, 0, 0),
            rot=(0, math.radians(90), 0)
        )
        # Add gear ring in the middle
        add_obj(f"SpaceStation_SARJ_{side}_Gear", sarj_gear_mesh, mat_dark, sarj_obj, col, loc=(0, 0, 0))
        
        # Add 4 mechanical bracket boxes around the perimeter of the joint
        for i in range(4):
            angle = (i / 4) * math.tau
            bx = math.cos(angle) * 2.4 * M
            by = math.sin(angle) * 2.4 * M
            add_obj(
                name=f"SpaceStation_SARJ_{side}_Bracket_{i}",
                mesh=sarj_bracket_mesh,
                mat=mat_dark,
                parent=sarj_obj,
                col=col,
                loc=(bx, by, 0.0),
                rot=(0, 0, angle)
            )

    # ── 3. Pressurized Modules ───────────────────────────────────────────────
    modules = [
        ("Destiny",   0.0,  -8.0,  0.0,  8.5, 2.2, 'Y'),
        ("Unity",     0.0,  -1.5,  0.0,  5.5, 2.2, 'Y'),
        ("Harmony",   0.0, -14.5,  0.0,  5.5, 2.2, 'Y'),
        ("Tranquility",-3.5, -1.5, 0.0,  4.0, 2.2, 'X'),
        ("Columbus",   3.5,-14.5,  0.0,  6.0, 2.2, 'X'),
        ("Kibo",      -4.5,-14.5,  0.0,  9.0, 2.2, 'X'),
        ("Zarya",     0.0,   7.0,  0.0,  8.0, 2.0, 'Y'),
        ("Zvezda",    0.0,  17.0,  0.0, 12.0, 2.1, 'Y'),
    ]

    for name, cx, cy, cz, length, radius, axis in modules:
        loc = (cx * M, cy * M, cz * M)
        rot = (math.radians(90), 0, 0) if axis == 'Y' else ((0, math.radians(90), 0) if axis == 'X' else (0, 0, 0))
        
        # Select appropriate material to display realistic color variety
        if name == "Zarya":
            m_mat = mat_zarya
        elif name in ["Destiny", "Harmony", "Columbus", "Kibo"]:
            m_mat = mat_silver
        else:
            m_mat = mat_module
            
        build_module(
            name=f"SpaceStation_Module_{name}",
            length=length * M,
            radius=radius * M,
            mat=m_mat,
            parent=root,
            col=col,
            loc=loc,
            rot=rot
        )
        
        # Add Zvezda engine details
        if name == "Zvezda":
            collar_mesh = make_cylinder_mesh("SpaceStation_ZvezdaEngine_Collar_Mesh", 1.25 * M, 1.0 * M, segs=12)
            eng_col = add_obj(
                name="SpaceStation_Zvezda_EngineCollar",
                mesh=collar_mesh,
                mat=mat_truss,  # standard truss aluminum gray
                parent=root,
                col=col,
                loc=(0, 23.0 * M, 0),
                rot=(math.radians(90), 0, 0)
            )
            nozzle_mesh = make_sphere_slice_mesh("SpaceStation_ZvezdaNozzle_Mesh", 0.35 * M, 0.6 * M, segs=8, rings=4, dome=True)
            add_obj(
                name="SpaceStation_Zvezda_Nozzle1",
                mesh=nozzle_mesh,
                mat=mat_dock,
                parent=eng_col,
                col=col,
                loc=(0.45 * M, 0, 0.5 * M),
                rot=(0, 0, 0)
            )
            add_obj(
                name="SpaceStation_Zvezda_Nozzle2",
                mesh=nozzle_mesh,
                mat=mat_dock,
                parent=eng_col,
                col=col,
                loc=(-0.45 * M, 0, 0.5 * M),
                rot=(0, 0, 0)
            )
        
        if name == "Tranquility":
            cupola_radius = 1.0 * M
            cupola_height = 0.7 * M
            cupola_mesh = make_sphere_slice_mesh("SpaceStation_Cupola_Mesh", cupola_radius, cupola_height, segs=8, rings=4, dome=True)
            cup_obj = add_obj(
                name="SpaceStation_Module_Cupola",
                mesh=cupola_mesh,
                mat=mat_module,
                parent=root,
                col=col,
                loc=(cx * M, cy * M, (cz - radius - 0.1) * M),
                rot=(math.pi, 0, 0)
            )
            
            win_mesh = make_cylinder_mesh("SpaceStation_Cupola_Window_Mesh", cupola_radius * 0.85, 0.05 * M, segs=8)
            add_obj(
                name="SpaceStation_Cupola_Window",
                mesh=win_mesh,
                mat=mat_solar,
                parent=cup_obj,
                col=col,
                loc=(0, 0, cupola_height * 0.5),
                rot=(0, 0, 0)
            )
            
    # S0 to Destiny structural cradle struts (adds realism to the truss mount)
    strut_rod_mesh = make_cylinder_mesh("SpaceStation_S0_Strut_Mesh", 0.08 * M, 4.5 * M, segs=8)
    # Strut 1: Front-Left
    add_obj("SpaceStation_S0_Strut_FL", strut_rod_mesh, mat_truss, root, col, loc=(-1.2 * M, -3.5 * M, -1.0 * M), rot=(math.radians(35), math.radians(20), 0))
    # Strut 2: Front-Right
    add_obj("SpaceStation_S0_Strut_FR", strut_rod_mesh, mat_truss, root, col, loc=(1.2 * M, -3.5 * M, -1.0 * M), rot=(math.radians(35), math.radians(-20), 0))
    # Strut 3: Aft-Left
    add_obj("SpaceStation_S0_Strut_AL", strut_rod_mesh, mat_truss, root, col, loc=(-1.2 * M, -6.5 * M, -1.0 * M), rot=(math.radians(-35), math.radians(20), 0))
    # Strut 4: Aft-Right
    add_obj("SpaceStation_S0_Strut_AR", strut_rod_mesh, mat_truss, root, col, loc=(1.2 * M, -6.5 * M, -1.0 * M), rot=(math.radians(-35), math.radians(-20), 0))

    # ── 4. Docking Ports ─────────────────────────────────────────────────────
    dock_ports = [
        ("Harmony_Fwd",  (0.0, -17.5, 0.0), (math.radians(90), 0, 0)),
        ("Zvezda_Aft",   (0.0, 24.0, 0.0),  (math.radians(90), 0, 0)),
        ("Unity_Zenith", (0.0, -1.5, 2.5),  (0, 0, 0)),
        ("Unity_Nadir",  (0.0, -1.5, -2.5), (0, 0, 0)),
    ]

    for name, ploc, prot in dock_ports:
        collar_mesh = make_cylinder_mesh(f"SpaceStation_Dock_{name}_ColMesh", 1.2 * M, 0.6 * M, segs=12)
        col_obj = add_obj(
            name=f"SpaceStation_Dock_{name}",
            mesh=collar_mesh,
            mat=mat_dock,
            parent=root,
            col=col,
            loc=(ploc[0] * M, ploc[1] * M, ploc[2] * M),
            rot=prot
        )
        ring_mesh = make_cylinder_mesh(f"SpaceStation_Dock_{name}_RingMesh", 1.4 * M, 0.15 * M, segs=12)
        add_obj(
            name=f"SpaceStation_Dock_{name}_Ring",
            mesh=ring_mesh,
            mat=mat_truss,
            parent=col_obj,
            col=col,
            loc=(0, 0, 0.25 * M),
            rot=(0, 0, 0)
        )

    # ── 5. Solar Array Wings (8 total) ───────────────────────────────────────
    solar_wing_x_positions = [
        ("P6", -46.5),
        ("P4", -28.5),
        ("S4",  28.5),
        ("S6",  46.5)
    ]

    for label, xw in solar_wing_x_positions:
        gimbal_mesh = make_cylinder_mesh(f"SpaceStation_Gimbal_{label}_Mesh", 1.5 * M, 2.0 * M, segs=12)
        gimbal_obj = add_obj(
            name=f"SpaceStation_Gimbal_{label}",
            mesh=gimbal_mesh,
            mat=mat_truss,
            parent=root,
            col=col,
            loc=(xw * M, 0, 0),
            rot=(0, 0, 0)
        )
        
        for wing_dir, y_sign in [("Fwd", 1), ("Aft", -1)]:
            mast_length = 35.0 * M
            mast_w = 0.7 * M
            mast_center_y = y_sign * (1.5 + 35.0/2.0) * M
            # Since the mast mesh is generated along X, rotate it 90 degrees around Z to align with Y
            add_lattice_obj(
                name=f"SpaceStation_Mast_{label}_{wing_dir}",
                length=mast_length,
                width=mast_w,
                height=mast_w,
                num_bays=10,
                strut_thickness=0.04 * M,
                mat=mat_frame,
                parent=gimbal_obj,
                col=col,
                loc=(0, mast_center_y, 0),
                rot=(0, 0, math.radians(90))
            )
            
            num_panels = 8
            panel_len = 32.0 / num_panels * M
            panel_w = 5.2 * M
            panel_thick = 0.02 * M
            y_start = 2.0 * M
            
            # The panel mesh extends along Y now: width (X), length (Y), thickness (Z)
            panel_mesh = make_box(f"SpaceStation_SolarBlanket_{label}_{wing_dir}_Mesh", panel_w, panel_len * 0.95, panel_thick)
            
            for p in range(num_panels):
                y_pos = y_sign * (y_start + (p + 0.5) * panel_len)
                
                # Blanket 1: offset along X by +3.2 * M, extend along Y
                add_obj(
                    name=f"SpaceStation_Panel_{label}_{wing_dir}_B1_{p}",
                    mesh=panel_mesh,
                    mat=mat_solar,
                    parent=gimbal_obj,
                    col=col,
                    loc=(3.2 * M, y_pos, 0),
                    rot=(0, 0, 0)
                )
                # Blanket 2: offset along X by -3.2 * M, extend along Y
                add_obj(
                    name=f"SpaceStation_Panel_{label}_{wing_dir}_B2_{p}",
                    mesh=panel_mesh,
                    mat=mat_solar,
                    parent=gimbal_obj,
                    col=col,
                    loc=(-3.2 * M, y_pos, 0),
                    rot=(0, 0, 0)
                )
                
                if p == 0 or p == num_panels - 1:
                    # The border mesh is wide in X (panel_w), short in Y (0.1 * M), and slightly thicker in Z
                    border_mesh = make_box(f"SpaceStation_PanelBorder_{label}_{wing_dir}_{p}_Mesh", panel_w, 0.1 * M, panel_thick * 1.5)
                    border_y = y_pos + y_sign * (panel_len * 0.48)
                    add_obj(
                        name=f"SpaceStation_PanelBorder_{label}_{wing_dir}_B1_{p}",
                        mesh=border_mesh,
                        mat=mat_frame,
                        parent=gimbal_obj,
                        col=col,
                        loc=(3.2 * M, border_y, 0),
                        rot=(0, 0, 0)
                    )
                    add_obj(
                        name=f"SpaceStation_PanelBorder_{label}_{wing_dir}_B2_{p}",
                        mesh=border_mesh,
                        mat=mat_frame,
                        parent=gimbal_obj,
                        col=col,
                        loc=(-3.2 * M, border_y, 0),
                        rot=(0, 0, 0)
                    )

        # ── 5b. Photovoltaic Radiators (PVR) near Gimbals ─────────────────────
        # Thin vertical radiator sheet pointing aft (-Y)
        pvr_mesh = make_box(f"SpaceStation_PVR_{label}_Mesh", 0.08 * M, 8.0 * M, 2.2 * M)
        add_obj(
            name=f"SpaceStation_PVR_{label}",
            mesh=pvr_mesh,
            mat=mat_rad,
            parent=gimbal_obj,
            col=col,
            loc=(0, -4.5 * M, 0),
            rot=(0, 0, 0)
        )
        # Structural radiator support arm connecting back to gimbal
        rad_arm_mesh = make_cylinder_mesh(f"SpaceStation_PVR_Arm_{label}_Mesh", 0.1 * M, 2.0 * M, segs=6)
        add_obj(
            name=f"SpaceStation_PVR_Arm_{label}",
            mesh=rad_arm_mesh,
            mat=mat_truss,
            parent=gimbal_obj,
            col=col,
            loc=(0, -1.0 * M, 0),
            rot=(math.radians(90), 0, 0)
        )

    # ── 5c. Cargo Platforms (ELC) & Multi-Colored Details Between Wings ──────
    # Placed on P5 and S5 truss segments (exactly in between P4/P6 and S4/S6)
    elc_mesh = make_box("SpaceStation_ELC_Mesh", 3.0 * M, 2.5 * M, 0.4 * M)
    box_gold = make_box("SpaceStation_ELCBox_Gold_Mesh", 0.8 * M, 0.8 * M, 0.8 * M)
    box_white = make_box("SpaceStation_ELCBox_White_Mesh", 1.1 * M, 1.1 * M, 1.1 * M)
    box_grey1 = make_box("SpaceStation_ELCBox_Grey1_Mesh", 0.6 * M, 0.6 * M, 0.6 * M)
    box_grey2 = make_box("SpaceStation_ELCBox_Grey2_Mesh", 0.8 * M, 0.8 * M, 0.8 * M)

    for side_name, elc_x in [("Port", -37.5), ("Starboard", 37.5)]:
        elc_obj = add_obj(
            name=f"SpaceStation_ELC_{side_name}",
            mesh=elc_mesh,
            mat=mat_dark,
            parent=root,
            col=col,
            loc=(elc_x * M, 2.2 * M, 0.5 * M),
            rot=(0, 0, 0)
        )
        # Gold box
        add_obj(f"SpaceStation_ELC_{side_name}_BoxGold", box_gold, mat_gold, elc_obj, col, loc=(-1.0 * M, -0.6 * M, 0.3 * M))
        # White box
        add_obj(f"SpaceStation_ELC_{side_name}_BoxWhite", box_white, mat_module, elc_obj, col, loc=(0.8 * M, -0.6 * M, 0.4 * M))
        # Red warning box (vibrant color accent!)
        add_obj(f"SpaceStation_ELC_{side_name}_BoxRed", box_grey1, mat_red, elc_obj, col, loc=(-0.6 * M, 0.7 * M, 0.2 * M))
        # Grey box 2
        add_obj(f"SpaceStation_ELC_{side_name}_BoxGrey2", box_grey2, mat_truss, elc_obj, col, loc=(0.7 * M, 0.6 * M, 0.3 * M))

    # ── 6. Thermal Radiator Panels ───────────────────────────────────────────
    radiator_x_positions = [
        ("P1", -12.5),
        ("S1",  12.5)
    ]

    for label, xr in radiator_x_positions:
        mount_mesh = make_cylinder_mesh(f"SpaceStation_RadMount_{label}_Mesh", 0.8 * M, 1.5 * M, segs=10)
        mount_obj = add_obj(
            name=f"SpaceStation_RadMount_{label}",
            mesh=mount_mesh,
            mat=mat_truss,
            parent=root,
            col=col,
            loc=(xr * M, -2.5 * M, 0),
            rot=(0, 0, 0)
        )
        
        rad_panel_w = 3.0 * M
        rad_panel_len = 20.0 * M
        rad_panel_thick = 0.1 * M
        # Create a vertical sheet (thin in X, long in Y, tall in Z) extending aft
        panel_mesh = make_box(f"SpaceStation_RadPanel_{label}_Mesh", rad_panel_thick, rad_panel_len, rad_panel_w)
        
        for i in [-1, 0, 1]:
            offset_x = i * (rad_panel_w + 0.3 * M)
            add_obj(
                name=f"SpaceStation_RadPanel_{label}_{i}",
                mesh=panel_mesh,
                mat=mat_rad,
                parent=mount_obj,
                col=col,
                loc=(offset_x, -rad_panel_len / 2.0, 0),
                rot=(0, 0, 0)
            )

    # ── 7. Communication Antennas ────────────────────────────────────────────
    dish_mesh = make_sphere_slice_mesh("SpaceStation_Dish_Mesh", 1.8 * M, 0.9 * M, segs=12, rings=6, dome=True)
    dish_mount_mesh = make_cylinder_mesh("SpaceStation_DishMount_Mesh", 0.15 * M, 1.5 * M, segs=6)
    
    mount_arm = add_obj(
        name="SpaceStation_Antenna_Arm",
        mesh=dish_mount_mesh,
        mat=mat_truss,
        parent=root,
        col=col,
        loc=(0.0, 23.5 * M, 1.5 * M),
        rot=(math.radians(-45), 0, 0)
    )
    add_obj(
        name="SpaceStation_Antenna_Dish",
        mesh=dish_mesh,
        mat=mat_dock,
        parent=mount_arm,
        col=col,
        loc=(0, 0, 0.75 * M),
        rot=(0, 0, 0)
    )
    
    destiny_ant_mesh = make_sphere_slice_mesh("SpaceStation_DestinyAnt_Mesh", 0.6 * M, 0.3 * M, segs=8, rings=4, dome=True)
    add_obj("SpaceStation_Destiny_Antenna", destiny_ant_mesh, mat_dock, root, col, loc=(0.0, -8.0 * M, 2.3 * M), rot=(0, 0, 0))

    # ── 8. Surface Micro-details (Boxes & Handrails) ─────────────────────────
    cable_tray_mesh = make_box("SpaceStation_CableTray_Mesh", 25.0 * M, 0.4 * M, 0.2 * M)
    add_obj("SpaceStation_CableTray_S", cable_tray_mesh, mat_frame, root, col, loc=(18.0 * M, 0.0, 2.1 * M))
    add_obj("SpaceStation_CableTray_P", cable_tray_mesh, mat_frame, root, col, loc=(-18.0 * M, 0.0, 2.1 * M))

    random.seed(42)
    for i in range(12):
        w = random.uniform(0.6, 1.5) * M
        d = random.uniform(0.6, 1.2) * M
        h = random.uniform(0.4, 0.8) * M
        x_pos = random.uniform(-35.0, 35.0) * M
        side = random.choice(['top', 'front', 'back'])
        box_mesh = make_box(f"SpaceStation_EquipBox_{i}_Mesh", w, d, h)
        
        loc = (x_pos, 0, 2.1 * M) if side == 'top' else ((x_pos, 2.1 * M, 0) if side == 'front' else (x_pos, -2.1 * M, 0))
        add_obj(f"SpaceStation_EquipBox_{i}", box_mesh, mat_dock, root, col, loc=loc)

    handrail_mesh = make_cylinder_mesh("SpaceStation_Handrail_Mesh", 0.03 * M, 2.0 * M, segs=6)
    modules_for_handrails = [
        ("Destiny", -8.0, 2.2),
        ("Unity", -1.5, 2.2),
        ("Harmony", -14.5, 2.2),
        ("Zarya", 7.0, 2.0),
        ("Zvezda", 17.0, 2.1)
    ]

    for name, cy_center, r_mod in modules_for_handrails:
        for side, (offset_x, offset_z, rot_z) in enumerate([
            (0.0, r_mod + 0.1, 0),
            (r_mod + 0.1, 0.0, math.radians(90)),
            (-(r_mod + 0.1), 0.0, math.radians(90))
        ]):
            add_obj(
                name=f"SpaceStation_Handrail_{name}_{side}_1",
                mesh=handrail_mesh,
                mat=mat_gold,
                parent=root,
                col=col,
                loc=(offset_x * M, (cy_center - 1.5) * M, offset_z * M),
                rot=(math.radians(90), 0, rot_z)
            )
            add_obj(
                name=f"SpaceStation_Handrail_{name}_{side}_2",
                mesh=handrail_mesh,
                mat=mat_gold,
                parent=root,
                col=col,
                loc=(offset_x * M, (cy_center + 1.5) * M, offset_z * M),
                rot=(math.radians(90), 0, rot_z)
            )

    print("   ✅ Highly detailed ISS geometry generated:")
    print("      Struts, solar arrays, pressurized modules, and micro-details successfully built.")

# ─────────────────────────────────────────────────────────────────────────────
# VIEWPORT LABELS
# ─────────────────────────────────────────────────────────────────────────────

def build_labels_and_pointer(root, orbit_center, col, M, earth_radius_bu, earth_obj):
    """Create a camera-facing 'Space Station' label and a short pointer line,
    using the same Copy Rotation → Camera billboard technique as the planet
    and Asteroid Belt labels."""

    # 1. Create / reuse the shared bright label material (emissive white)
    label_mat = bpy.data.materials.get("Text_Bright_Mat")
    if label_mat is None:
        label_mat = bpy.data.materials.new("Text_Bright_Mat")
        label_mat.diffuse_color = (1.0, 1.0, 1.0, 1.0)
        label_mat.use_nodes = True
        label_mat.node_tree.nodes.clear()

        lout  = label_mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        lemit = label_mat.node_tree.nodes.new("ShaderNodeEmission")
        lemit.inputs["Color"].default_value    = (1.0, 1.0, 1.0, 1.0)
        lemit.inputs["Strength"].default_value = 3.0
        label_mat.node_tree.links.new(lemit.outputs["Emission"], lout.inputs["Surface"])

    # 2. Create Label text curve
    curve = bpy.data.curves.new("SpaceStation_Label_Curve", type='FONT')
    curve.body    = "Space Station"
    curve.size    = 1.0
    curve.align_x = 'CENTER'
    curve.align_y = 'BOTTOM'

    label_obj = bpy.data.objects.new("SpaceStation_Label", curve)
    col.objects.link(label_obj)
    label_obj.data.materials.append(label_mat)

    # No parent — driven entirely by constraints.
    # Scale the text to match the station's metric scale M so it reads at a
    # sensible size next to the model (same idea as the truss/module sizes).
    label_obj.rotation_euler = (0, 0, 0)
    label_obj.scale          = (24.0 * M, 24.0 * M, 24.0 * M)

    # Step 1 — Follow the station's world position
    copy_loc = label_obj.constraints.new(type='COPY_LOCATION')
    copy_loc.target       = root
    copy_loc.use_x        = True
    copy_loc.use_y        = True
    copy_loc.use_z        = True
    copy_loc.target_space = 'WORLD'
    copy_loc.owner_space  = 'WORLD'

    # Step 2 — Offset upward in world Z (scaled with M) so the label sits
    # just above the station rather than swamping the whole scene.
    copy_loc.use_offset = True
    label_obj.location  = (-45.0 * M, 0, -50.0 * M)

    # Step 3 — Face the camera (billboard), exactly like the planet /
    # Asteroid Belt labels: a Copy Rotation constraint targeting the Camera.
    # This copies the camera's FINAL evaluated orientation (including its
    # own Track To constraint), unlike copying rotation_euler directly which
    # only reflects the camera's un-evaluated base rotation (often (0,0,0)).
    cam = bpy.data.objects.get("Camera") or bpy.context.scene.camera
    if cam:
        copy_rot = label_obj.constraints.new(type='COPY_ROTATION')
        copy_rot.target = cam
        print("   ✓ Added Copy Rotation constraint to Camera for the Space Station label")
    else:
        label_obj.rotation_euler = (math.radians(90), 0, 0)

    # 3. Pointer — short tick line from the station up to the label, parented
    # to the station root (and scaled with M) so it orbits along with it.
    pointer_curve = bpy.data.curves.new("SpaceStation_Pointer_Curve", type='CURVE')
    pointer_curve.dimensions  = '3D'
    pointer_curve.bevel_depth = 0.01 * M   # thin line, scaled with the station
    sp = pointer_curve.splines.new('NURBS')
    sp.points.add(1)
    sp.points[0].co = (0, 0, 0.0,      1)
    sp.points[1].co = (0, 0, 6.0 * M,  1)   # up to where the label sits
    sp.use_endpoint_u = True

    pointer_obj = bpy.data.objects.new("SpaceStation_Pointer", pointer_curve)
    col.objects.link(pointer_obj)
    pointer_obj.parent = root
    pointer_obj.matrix_parent_inverse.identity()
    pointer_obj.location = (0, 0, 0)
    pointer_curve.materials.append(label_mat)

# ─────────────────────────────────────────────────────────────────────────────
# ORBIT SETUP & PATH RING
# ─────────────────────────────────────────────────────────────────────────────

def setup_orbit(root, earth_obj, earth_radius_bu, col):
    """Setup scientifically accurate orbital location drivers and tracking."""
    iss_orbit_r = earth_radius_bu * ISS_ORBITAL_RADIUS_RATIO + VISUAL_GAP_BU
    
    # Create an Orbit Center empty that tracks Earth's location without inheriting its scale/rotation.
    # This prevents non-uniform scaling or skewing from warping the station geometry.
    center_name = "SpaceStation_OrbitCenter"
    center_obj = bpy.data.objects.get(center_name)
    if center_obj is None:
        center_obj = bpy.data.objects.new(center_name, None)
        center_obj.empty_display_type = 'PLAIN_AXES'
        center_obj.empty_display_size = 0.05
        col.objects.link(center_obj)
        
    # Copy location constraint to follow Earth without scale inheritance
    center_obj.constraints.clear()
    copy_loc = center_obj.constraints.new(type='COPY_LOCATION')
    copy_loc.target = earth_obj
    
    # Parent the station root to this Orbit Center (which has a perfect, uniform (1,1,1) scale)
    root.parent = center_obj
    root.matrix_parent_inverse.identity()
    root.location = (iss_orbit_r, 0, 0)
    
    i_rad = math.radians(ISS_INCLINATION_DEG)
    
    root.animation_data_clear()
    T_expr = f"{ISS_VISUAL_PERIOD_FRAMES}"
    
    fc_x = root.driver_add("location", 0)
    fc_x.driver.type       = 'SCRIPTED'
    fc_x.driver.expression = f"{iss_orbit_r:.6f} * cos((frame / {T_expr}) * {math.tau})"

    fc_y = root.driver_add("location", 1)
    fc_y.driver.type       = 'SCRIPTED'
    fc_y.driver.expression = f"{iss_orbit_r:.6f} * sin((frame / {T_expr}) * {math.tau}) * {math.cos(i_rad):.6f}"

    fc_z = root.driver_add("location", 2)
    fc_z.driver.type       = 'SCRIPTED'
    fc_z.driver.expression = f"{iss_orbit_r:.6f} * sin((frame / {T_expr}) * {math.tau}) * {math.sin(i_rad):.6f}"
    
    root.constraints.clear()
    track = root.constraints.new(type='TRACK_TO')
    track.target     = earth_obj
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis    = 'UP_Y'
    
    return center_obj, iss_orbit_r


def build_orbit_ring(parent_obj, orbit_r, col):
    """Draw a thin reference circle outlining the orbital path in the viewport."""
    ring_name = "SpaceStation_OrbitRing"
    cd = bpy.data.curves.new(ring_name, type='CURVE')
    cd.dimensions  = '3D'
    cd.bevel_depth = 0.002
    
    sp = cd.splines.new('NURBS')
    N  = 128
    sp.points.add(N - 1)
    
    i_rad = math.radians(ISS_INCLINATION_DEG)
    for k in range(N):
        theta = (k / N) * math.tau
        x = orbit_r * math.cos(theta)
        y = orbit_r * math.sin(theta) * math.cos(i_rad)
        z = orbit_r * math.sin(theta) * math.sin(i_rad)
        sp.points[k].co = (x, y, z, 1.0)
        
    sp.use_cyclic_u  = True
    sp.use_endpoint_u = True
    sp.order_u = 4
    
    obj = bpy.data.objects.new(ring_name, cd)
    col.objects.link(obj)
    obj.parent = parent_obj
    obj.matrix_parent_inverse.identity()
    obj.hide_render = True
    
    mat = bpy.data.materials.new("SpaceStation_OrbitRingMat")
    mat.diffuse_color = (0.3, 0.75, 1.0, 1.0)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    out  = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    emit = mat.node_tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value    = (0.3, 0.75, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 1.0
    mat.node_tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    cd.materials.append(mat)

# ─────────────────────────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────────────────────────

def remove_ss_objects():
    """Cleanly purge all previously generated ISS elements."""
    # Delete objects
    for o in list(bpy.data.objects):
        if o.name.startswith("SpaceStation_") or o.name.startswith("ISS_"):
            bpy.data.objects.remove(o, do_unlink=True)
            
    # Delete meshes
    for m in list(bpy.data.meshes):
        if m.name.startswith("SpaceStation_") or m.name.startswith("ISS_"):
            bpy.data.meshes.remove(m)
            
    # Delete curves
    for c in list(bpy.data.curves):
        if c.name.startswith("SpaceStation_") or c.name.startswith("ISS_"):
            bpy.data.curves.remove(c)
            
    # Delete materials
    for m in list(bpy.data.materials):
        if m.name.startswith("SpaceStation_") or m.name.startswith("ISS_"):
            bpy.data.materials.remove(m)
            
    # Delete lights
    for l in list(bpy.data.lights):
        if l.name.startswith("SpaceStation_"):
            bpy.data.lights.remove(l)

# ─────────────────────────────────────────────────────────────────────────────
# RENDER SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

def setup_render_settings(scene):
    """Configure render engine and parameters for high-quality Cycles output."""
    scene.render.engine = 'CYCLES'
    if hasattr(scene, 'cycles'):
        scene.cycles.samples = 256
        scene.cycles.preview_samples = 32
        
    scene.render.film_transparent = True
    
    if hasattr(scene, 'eevee'):
        if hasattr(scene.eevee, 'use_gtao'):
            scene.eevee.use_gtao = True
        elif hasattr(scene.eevee, 'use_ambient_occlusion'):
            scene.eevee.use_ambient_occlusion = True
        if hasattr(scene.eevee, 'use_ssr'):
            scene.eevee.use_ssr = True

# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────

def run():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
        
    print("\n" + "=" * 62)
    print("  PROCEDURAL ISS SPACE STATION GENERATOR — BLENDER 5.1")
    print("=" * 62)
    
    # 1. Collection check
    col = bpy.data.collections.get(COLLECTION_NAME)
    if col is None:
        col = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(col)
        
    # 2. Find or create Earth
    earth_obj = bpy.data.objects.get(EARTH_OBJECT_NAME)
    if earth_obj is None:
        print(f"   ℹ Earth object '{EARTH_OBJECT_NAME}' not found. Generating dummy Earth sphere...")
        bpy.ops.mesh.primitive_uv_sphere_add(radius=EARTH_SPHERE_RADIUS_BU, location=(0, 0, 0))
        earth_obj = bpy.context.active_object
        earth_obj.name = EARTH_OBJECT_NAME
        
        # Shade smooth the dummy Earth
        for f in earth_obj.data.polygons:
            f.use_smooth = True
            
        # Simple Earth blue material
        earth_mat = bpy.data.materials.new("Earth_Dummy_Mat")
        earth_mat.diffuse_color = (0.05, 0.25, 0.65, 1.0)
        earth_mat.use_nodes = True
        bsdf = next((n for n in earth_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.05, 0.25, 0.65, 1.0)
        earth_obj.data.materials.append(earth_mat)
        
    earth_radius_bu = earth_obj.scale[0] * EARTH_SPHERE_RADIUS_BU
    
    # Compute the metric scaling factor based on Earth's size
    M = (earth_radius_bu / 1.0) * (ISS_VISUAL_SCALE / 10.0)
    
    # 3. Cleanup existing station objects
    remove_ss_objects()
    
    # 4. Create Station Root Empty
    root = bpy.data.objects.new("SpaceStation_Root", None)
    root.empty_display_type = 'ARROWS'
    root.empty_display_size = 0.05
    col.objects.link(root)
    
    # 5. Build geometry, orbit, labels, render settings
    orbit_center, orbit_r = setup_orbit(root, earth_obj, earth_radius_bu, col)
    build_iss_geometry(root, col, M)
    build_labels_and_pointer(root, orbit_center, col, M, earth_radius_bu, earth_obj)
    build_orbit_ring(orbit_center, orbit_r, col)

    setup_render_settings(bpy.context.scene)

    print("\n" + "=" * 62)
    print("✅ ISS Generation Complete!")
    print("=" * 62)
    print(f"  • Orbital radius: {orbit_r:.4f} BU (ratio to Earth radius: {ISS_ORBITAL_RADIUS_RATIO})")
    print(f"  • Metric scale: 1 meter = {M:.6f} BU")
    print(f"  • Inclination: {ISS_INCLINATION_DEG}°")

run()
