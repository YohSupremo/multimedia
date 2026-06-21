"""
Comets.py
=========
Procedural Comets — Viewport-Spanned Comets with Unique Colors and Elliptical/Target trajectories.
Consolidated and migrated to the Solar System Consolidated collection.
"""

import sys
import builtins

# Force unbuffered printing so logs show up immediately in background tasks
def print(*args, **kwargs):
    builtins.print(*args, **kwargs)
    sys.stdout.flush()

import bpy
import bmesh
import math
import random
from mathutils import Vector

# Sun collision radius — matches SUN_SAFE_RADIUS from Cinematic Tour
SUN_RADIUS = 14.0

# Comets configuration: target planet, arrival frame, and trajectory curve factor
# Scaled sizes to prevent "too big" comets
COMET_CONFIGS = [
    # 1. Comet on Earth (early-stage tour)
    {"target": "Earth",   "arrival": 900,  "duration": 120, "size": 0.45,  "curve": 12.0,
     "coma_color": (0.15, 0.85, 0.70, 1.0), "tail_color": (0.25, 0.65, 1.0, 1.0)},

    # 2. Comet on Venus — shifted later so Venus orbits away from Sun-side
    {"target": "Venus",   "arrival": 1080, "duration": 110, "size": 0.40, "curve": 10.0,
     "coma_color": (0.9, 0.8, 0.1, 1.0),   "tail_color": (1.0, 0.4, 0.1, 1.0)},

    # 3. Comet on Earth (second visit)
    {"target": "Earth",   "arrival": 1210, "duration": 120, "size": 0.50, "curve": 13.0,
     "coma_color": (0.1, 0.9, 0.9, 1.0),   "tail_color": (0.8, 0.8, 0.95, 1.0)},

    # 4. Comet on Mars — shifted slightly later to reduce Sun-crossing risk
    {"target": "Mars",    "arrival": 1400, "duration": 100, "size": 0.35, "curve": 9.0,
     "coma_color": (0.8, 0.1, 0.9, 1.0),   "tail_color": (1.0, 0.15, 0.5, 1.0)},

    # 5. Comet on Jupiter (safe — far from Sun)
    {"target": "Jupiter", "arrival": 1700, "duration": 140, "size": 0.85,  "curve": 24.0,
     "coma_color": (1.0, 0.35, 0.1, 1.0),  "tail_color": (1.0, 0.75, 0.15, 1.0)},

    # 6. Comet on Saturn (safe — far from Sun)
    {"target": "Saturn",  "arrival": 1860, "duration": 150, "size": 0.70,  "curve": 28.0,
     "coma_color": (0.1, 0.85, 0.3, 1.0),  "tail_color": (0.8, 0.9, 0.1, 1.0)},

    # 7. Comet on Uranus (safe — far from Sun)
    {"target": "Uranus",  "arrival": 2000, "duration": 130, "size": 0.65,  "curve": 20.0,
     "coma_color": (0.25, 0.65, 1.0, 1.0), "tail_color": (0.5, 0.3, 1.0, 1.0)},

    # 8. Comet on Neptune (safe — far from Sun)
    {"target": "Neptune", "arrival": 2160, "duration": 140, "size": 0.70,  "curve": 22.0,
     "coma_color": (0.9, 0.1, 0.4, 1.0),   "tail_color": (1.0, 0.5, 0.8, 1.0)},

    # 9. Comet on Pluto (safe — far from Sun)
    {"target": "Pluto",   "arrival": 2310, "duration": 110, "size": 0.35, "curve": 8.0,
     "coma_color": (0.1, 0.9, 0.6, 1.0),   "tail_color": (0.15, 0.85, 0.85, 1.0)},

    # 10. Comet on Jupiter (wide-angle stage) — shifted +100 to avoid Sun crossing
    {"target": "Jupiter", "arrival": 2700, "duration": 160, "size": 0.90,  "curve": 26.0,
     "coma_color": (1.0, 0.2, 0.6, 1.0),   "tail_color": (1.0, 0.6, 0.1, 1.0)},

    # 11. Comet on Saturn (wide-angle stage) — shifted +100 to stay clear of Sun
    {"target": "Saturn",  "arrival": 2930, "duration": 160, "size": 0.80,  "curve": 30.0,
     "coma_color": (0.5, 0.2, 0.9, 1.0),   "tail_color": (0.1, 0.85, 0.85, 1.0)},
]

# Cache to store planet positions at specific frames to avoid redundant frame_set calls
planet_positions_cache = {}

def get_planet_position(p_name, frame):
    key = (p_name, frame)
    if key not in planet_positions_cache:
        bpy.context.scene.frame_set(frame)
        # Store positions of all planets for this frame to minimize frame_set updates
        all_planets = ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
        for name in all_planets:
            obj = bpy.data.objects.get(name)
            if obj:
                planet_positions_cache[(name, frame)] = obj.matrix_world.to_translation().copy()
            else:
                planet_positions_cache[(name, frame)] = Vector((0.0, 0.0, 0.0))
    return planet_positions_cache[key]

def clean_comets():
    """Remove previous comet objects for safe re-running."""
    for obj in [o for o in bpy.data.objects if o.name.startswith("Comet_")]:
        bpy.data.objects.remove(obj, do_unlink=True)
            
    for mesh in [m for m in bpy.data.meshes if m.name.startswith("Comet_")]:
        bpy.data.meshes.remove(mesh)
            
    for curve in [c for c in bpy.data.curves if c.name.startswith("Comet_")]:
        bpy.data.curves.remove(curve)
            
    for mat in [m for m in bpy.data.materials if m.name.startswith("Comet_")]:
        bpy.data.materials.remove(mat)

    # Clean fallback helper if exists
    helper = bpy.data.objects.get("Sun_Position_Helper")
    if helper:
        bpy.data.objects.remove(helper, do_unlink=True)


def check_sun_collision(path_points, sun_radius=SUN_RADIUS):
    """
    Check if any point along the comet path passes within sun_radius of the origin (Sun).
    Returns (True, frame_index) if collision found, (False, -1) if clear.
    """
    sun_pos = Vector((0.0, 0.0, 0.0))
    for idx, P in enumerate(path_points):
        if (Vector(P) - sun_pos).length < sun_radius:
            return True, idx
    return False, -1


def make_nucleus_mesh(size=0.15):
    mesh = bpy.data.meshes.new("Comet_Nucleus_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=4, radius=size)
    
    # Deform to make it irregular/potato-like with micro crags
    rng = random.Random(random.randint(1, 10000))
    for v in bm.verts:
        s = rng.uniform(0.75, 1.25)
        v.co = v.co * s
        v.co.x += rng.uniform(-0.16 * size, 0.16 * size)
        v.co.y += rng.uniform(-0.16 * size, 0.16 * size)
        v.co.z += rng.uniform(-0.16 * size, 0.16 * size)
        
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh

def make_coma_mesh(size=0.6):
    mesh = bpy.data.meshes.new("Comet_Coma_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=size)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh

def make_tail_mesh(depth=15.0, size_scale=1.0):
    mesh = bpy.data.meshes.new("Comet_Tail_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=False,
        cap_tris=False,
        segments=32,
        radius1=0.04 * size_scale,
        radius2=0.8 * size_scale,
        depth=depth
    )
    for v in bm.verts:
        v.co.z -= depth / 2.0
        
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh

def make_nucleus_material(index):
    mat = bpy.data.materials.new(f"Comet_Nucleus_Mat_{index}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.04, 0.04, 0.04, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    
    mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def make_coma_material(index, color):
    mat = bpy.data.materials.new(f"Comet_Coma_Mat_{index}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    try:
        mat.blend_method = 'BLEND'
    except AttributeError:
        pass
    try:
        mat.surface_render_method = 'BLENDED'
    except AttributeError:
        pass
    try:
        mat.shadow_method = 'NONE'
    except AttributeError:
        pass
        
    out = nodes.new("ShaderNodeOutputMaterial")
    trans = nodes.new("ShaderNodeBsdfTransparent")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = 4.0
    
    mix = nodes.new("ShaderNodeMixShader")
    lw = nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.20
    
    # Procedural gas texture for a non-uniform swirling coma look
    tex_coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 6.0
    noise.inputs["Detail"].default_value = 2.0
    
    multiply = nodes.new("ShaderNodeMath")
    multiply.operation = 'MULTIPLY'
    
    links.new(tex_coord.outputs["Generated"], noise.inputs["Vector"])
    links.new(lw.outputs["Facing"], multiply.inputs[0])
    links.new(noise.outputs["Fac"], multiply.inputs[1])
    
    links.new(multiply.outputs["Value"], mix.inputs["Fac"])
    links.new(trans.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat

def make_tail_material(index, color):
    mat = bpy.data.materials.new(f"Comet_Tail_Mat_{index}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    try:
        mat.blend_method = 'BLEND'
    except AttributeError:
        pass
    try:
        mat.surface_render_method = 'BLENDED'
    except AttributeError:
        pass
    try:
        mat.shadow_method = 'NONE'
    except AttributeError:
        pass
        
    out = nodes.new("ShaderNodeOutputMaterial")
    trans = nodes.new("ShaderNodeBsdfTransparent")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = 5.0
    
    mix = nodes.new("ShaderNodeMixShader")
    tex_coord = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    
    # Z gradient (fades along the length of the tail)
    ramp_z = nodes.new("ShaderNodeValToRGB")
    cr_z = ramp_z.color_ramp
    cr_z.interpolation = 'EASE'
    cr_z.elements[0].position = 0.0
    cr_z.elements[0].color = (0.0, 0.0, 0.0, 0.0)             # Base is fully transparent
    cr_z.elements[1].position = 0.95
    cr_z.elements[1].color = (1.0, 1.0, 1.0, 0.8)             # Tip is glowing/opaque
    
    # Noise texture stretched along Z to create wispy streaks
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (12.0, 12.0, 0.8)  # Stretched along Z length
    
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 8.0
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Distortion"].default_value = 1.0
    
    multiply = nodes.new("ShaderNodeMath")
    multiply.operation = 'MULTIPLY'
    
    links.new(tex_coord.outputs["Generated"], sep.inputs["Vector"])
    links.new(sep.outputs["Z"], ramp_z.inputs["Fac"])
    
    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    
    # Multiply gradient alpha with noise streaks
    links.new(ramp_z.outputs["Alpha"], multiply.inputs[0])
    links.new(noise.outputs["Fac"], multiply.inputs[1])
    
    links.new(multiply.outputs["Value"], mix.inputs["Fac"])
    links.new(trans.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat

def smooth_obj_keyframes(obj):
    """Set f-curve interpolation to LINEAR to prevent overshoot."""
    if obj.animation_data and obj.animation_data.action:
        action = obj.animation_data.action
        fcurves = []
        if hasattr(action, "fcurves"):
            fcurves.extend(action.fcurves)
        if hasattr(action, "layers"):
            for layer in action.layers:
                if hasattr(layer, "strips"):
                    for strip in layer.strips:
                        if hasattr(strip, "channelbags"):
                            cbs = getattr(strip, "channelbags", [])
                            if hasattr(cbs, "values"):
                                cbs = cbs.values()
                            for cb in cbs:
                                if hasattr(cb, "fcurves"):
                                    fcurves.extend(cb.fcurves)
        for fcurve in fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'LINEAR'

def build_comets():
    print("\n☄️ Generating Procedural Planet-Falling Comets...")
    clean_comets()
    
    wide_loc = Vector((275.6685, -398.0674, 159.8474))
    wide_target = Vector((0.0, 0.0, 0.0))
    
    D_cam = (wide_target - wide_loc).normalized()
    R_cam = D_cam.cross(Vector((0.0, 0.0, 1.0))).normalized()
    U_cam = R_cam.cross(D_cam).normalized()

    print(f"\n   ☀️  Sun collision radius: {SUN_RADIUS} BU")
    print("   Running Sun collision pre-check on all comets...\n")

    for i, cfg in enumerate(COMET_CONFIGS):
        planet_name = cfg["target"]
        f_impact = cfg["arrival"]
        duration = cfg["duration"]
        size_scale = cfg["size"]
        curve_amt = cfg["curve"]
        coma_color = cfg["coma_color"]
        tail_color = cfg["tail_color"]
        
        planet = bpy.data.objects.get(planet_name)
        if not planet:
            print(f"   ⚠ Planet {planet_name} not found! Skipping comet {i}.")
            continue

        f_start = f_impact - duration

        # Pre-check: compute path and check for Sun collision
        P_planet_start = get_planet_position(planet_name, f_start)

        # Spawn offset: starts top-right of camera viewport to fall towards target,
        # but is anchored exactly in the Kuiper Belt (165 - 195 BU from Sun).
        rng = random.Random(42 + i * 99)
        dir_in = (D_cam * rng.uniform(0.4, 0.7) + R_cam * rng.uniform(0.5, 0.8) + U_cam * rng.uniform(0.4, 0.7)).normalized()
        
        R_kuiper = rng.uniform(165.0, 195.0)
        
        # Solve quadratic equation for dist along dir_in to hit R_kuiper distance from origin:
        b = 2.0 * P_planet_start.dot(dir_in)
        c = P_planet_start.length_squared - R_kuiper**2
        disc = b**2 - 4.0 * c
        if disc >= 0.0:
            dist = (-b + math.sqrt(disc)) / 2.0
        else:
            dist = 175.0  # Fallback
            
        P_start = P_planet_start + dist * dir_in

        P_planet_impact = get_planet_position(planet_name, f_impact)

        dir_vector   = (P_planet_impact - P_start).normalized()
        planet_radius = max(planet.dimensions) / 2.0 if max(planet.dimensions) > 0.0 else 1.0
        P_impact = P_planet_impact - dir_vector * planet_radius

        # Build preview path for Sun collision check
        preview_path = []
        for f in range(f_start, f_impact + 1):
            t = (f - f_start) / max(1, duration)
            P = P_start + (P_impact - P_start) * t
            preview_path.append(P)

        sun_hit, sun_hit_idx = check_sun_collision(preview_path, SUN_RADIUS)
        if sun_hit:
            sun_hit_frame = f_start + sun_hit_idx
            print(f"   ☀️  WARNING — Comet {i} ({planet_name}, arrival f{f_impact}): "
                  f"Path crosses Sun at frame ~{sun_hit_frame}! "
                  f"Consider shifting arrival frame later.")
        else:
            print(f"   ✅ Comet {i} ({planet_name}, arrival f{f_impact}): Path is clear of Sun.")

    print("\n   Building comet objects...\n")

    for i, cfg in enumerate(COMET_CONFIGS):
        planet_name = cfg["target"]
        f_impact = cfg["arrival"]
        duration = cfg["duration"]
        size_scale = cfg["size"]
        curve_amt = cfg["curve"]
        coma_color = cfg["coma_color"]
        tail_color = cfg["tail_color"]
        
        planet = bpy.data.objects.get(planet_name)
        if not planet:
            continue

        print(f"   Building Comet {i} → {planet_name} at frame {f_impact}...")

        nuc_mat  = make_nucleus_material(i)
        coma_mat = make_coma_material(i, coma_color)
        tail_mat = make_tail_material(i, tail_color)

        nuc_mesh  = make_nucleus_mesh(0.15 * size_scale)
        coma_mesh = make_coma_mesh(0.6 * size_scale)
        tail_mesh = make_tail_mesh(15.0 * size_scale, size_scale)

        nuc_name = f"Comet_Nucleus_{i}"
        nuc_obj  = bpy.data.objects.new(nuc_name, nuc_mesh)
        bpy.context.collection.objects.link(nuc_obj)
        nuc_obj.data.materials.append(nuc_mat)

        coma_obj = bpy.data.objects.new(f"Comet_Coma_{i}", coma_mesh)
        bpy.context.collection.objects.link(coma_obj)
        coma_obj.parent = nuc_obj
        coma_obj.location = (0.0, 0.0, 0.0)
        coma_obj.data.materials.append(coma_mat)

        tail_obj = bpy.data.objects.new(f"Comet_Tail_{i}", tail_mesh)
        bpy.context.collection.objects.link(tail_obj)
        tail_obj.parent = nuc_obj
        tail_obj.location = (0.0, 0.0, 0.0)
        tail_obj.data.materials.append(tail_mat)

        nuc_obj.animation_data_clear()
        nuc_obj.animation_data_create()
        tail_obj.animation_data_clear()
        tail_obj.animation_data_create()

        f_start = f_impact - duration

        path_points = []

        P_planet_start = get_planet_position(planet_name, f_start)

        rng = random.Random(42 + i * 99)
        dir_in = (D_cam * rng.uniform(0.4, 0.7) + R_cam * rng.uniform(0.5, 0.8) + U_cam * rng.uniform(0.4, 0.7)).normalized()
        
        R_kuiper = rng.uniform(165.0, 195.0)
        
        # Solve quadratic equation for dist along dir_in to hit R_kuiper distance from origin:
        b = 2.0 * P_planet_start.dot(dir_in)
        c = P_planet_start.length_squared - R_kuiper**2
        disc = b**2 - 4.0 * c
        if disc >= 0.0:
            dist = (-b + math.sqrt(disc)) / 2.0
        else:
            dist = 175.0
            
        P_start = P_planet_start + dist * dir_in

        P_planet_impact = get_planet_position(planet_name, f_impact)

        dir_vector    = (P_planet_impact - P_start).normalized()
        planet_radius = max(planet.dimensions) / 2.0 if max(planet.dimensions) > 0.0 else 1.0
        P_impact = P_planet_impact - dir_vector * planet_radius

        collision_frame       = None
        collision_planet_name = None
        collision_planet_loc  = None
        
        all_planets = ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
        
        for f in range(f_start, f_impact + 1):
            t = (f - f_start) / duration
            P = P_start + (P_impact - P_start) * t
            
            for p_name in all_planets:
                if p_name == planet_name:
                    continue
                    
                other_p_loc = get_planet_position(p_name, f)
                other_p = bpy.data.objects.get(p_name)
                if not other_p:
                    continue
                    
                other_p_radius = max(other_p.dimensions) / 2.0 if max(other_p.dimensions) > 0.0 else 1.0
                
                if (P - other_p_loc).length < other_p_radius:
                    collision_frame       = f
                    collision_planet_name = p_name
                    collision_planet_loc  = other_p_loc
                    break
            
            if collision_frame is not None:
                break
            
            path_points.append(P)

        if collision_frame is not None:
            print(f"      💥 Collision! Comet {i} intercepted by {collision_planet_name} at frame {collision_frame}!")
            f_impact = collision_frame
            duration = f_impact - f_start
            
            other_p        = bpy.data.objects.get(collision_planet_name)
            other_p_radius = max(other_p.dimensions) / 2.0 if max(other_p.dimensions) > 0.0 else 1.0
            
            dir_vector = (collision_planet_loc - P_start).normalized()
            P_impact   = collision_planet_loc - dir_vector * other_p_radius
            
            path_points = []
            for f in range(f_start, f_impact + 1):
                t = (f - f_start) / max(1, duration)
                P = P_start + (P_impact - P_start) * t
                path_points.append(P)

        nuc_obj.scale = (0.0, 0.0, 0.0)
        nuc_obj.keyframe_insert(data_path="scale", frame=f_start - 5)

        for f_idx, f in enumerate(range(f_start, f_impact + 6)):
            t = (f - f_start) / duration
            
            if f < f_start + 15:
                sc = (f - f_start) / 15.0
                nuc_obj.scale = (sc, sc, sc)
            elif f >= f_impact:
                nuc_obj.scale = (0.0, 0.0, 0.0)
            else:
                nuc_obj.scale = (1.0, 1.0, 1.0)
            nuc_obj.keyframe_insert(data_path="scale", frame=f)

            if f <= f_impact:
                P = path_points[f_idx]
                nuc_obj.location = P
                nuc_obj.keyframe_insert(data_path="location", frame=f)

                d_sun = P.length
                tail_z_scale = max(0.1, min(2.2, 45.0 / max(0.1, d_sun)))
                tail_obj.scale = (1.0, 1.0, tail_z_scale)
                tail_obj.keyframe_insert(data_path="scale", frame=f)

                if f_idx > 0:
                    V = path_points[f_idx] - path_points[f_idx - 1]
                else:
                    V = path_points[1] - path_points[0]

                if V.length > 0.0001:
                    V_dir = V.normalized()
                    quat  = V_dir.to_track_quat('Z', 'Y')
                    tail_obj.rotation_mode = 'QUATERNION'
                    tail_obj.rotation_quaternion = quat
                    tail_obj.keyframe_insert(data_path="rotation_quaternion", frame=f)
            else:
                nuc_obj.location = P_impact
                nuc_obj.keyframe_insert(data_path="location", frame=f)

        smooth_obj_keyframes(nuc_obj)
        smooth_obj_keyframes(tail_obj)

    print("\n☄️ All procedural comets created successfully!")
    print("   ☀️  Check warnings above for any Sun-crossing paths.")
    print("   If any warnings appear, increase that comet's arrival frame by ~50–100 frames.\n")

if __name__ == "__main__":
    build_comets()
