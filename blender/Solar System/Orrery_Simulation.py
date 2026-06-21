"""
Orrery_Simulation.py
====================
Consolidated script that handles the main Orrery timeline, axial tilts,
rotational animations, orbital drivers, orbit guide rings, and camera-facing
text labels for the planets, the Moon, and the Sun.

Includes robust Data API object creation (context-independent) and combines
Sun rotation, constraint-based camera-facing Sun labels, and orbit path rendering.
"""

import bpy
import math
from mathutils import Matrix

# ── GLOBAL SCALES (HOLLYWOOD ORRERY EDITION) ──────────────────────────────────
ANIM_END = 3000
PLANET_SIZE_MULTIPLIER = 1.0
TEXT_SIZE = 2.5

SUN_NAME = "The Sun"
SUN_VISUAL_SIZE = 4.0

# ── WIDE ORRERY DISTANCES ─────────────────────────────────────────────────────
DISTANCE = {
    "Mercury": 15.0,
    "Venus":   23.0,
    "Earth":   31.0,
    "Mars":    39.0,
    "Jupiter": 70.0,  
    "Saturn":  95.0,
    "Uranus":  120.0,
    "Neptune": 145.0,
    "Pluto":   165.0,
}

# ── EDUCATIONAL SIZES ─────────────────────────────────────────────────────────
SIZE = {
    "Mercury": 0.55,
    "Venus":   0.92,
    "Earth":   1.00,
    "Mars":    0.65,
    "Jupiter": 5.50,
    "Saturn":  4.80,
    "Uranus":  2.50,
    "Neptune": 2.40,
    "Pluto":   0.35,
}

# ── ORBITAL PERIODS (faked for visuals) ───────────────────────────────────────
PERIOD = {
    "Mercury": 0.4,
    "Venus":   0.7,
    "Earth":   1.0,
    "Mars":    1.5,
    "Jupiter": 3.0,
    "Saturn":  5.0,
    "Uranus":  7.0,
    "Neptune": 9.0,
    "Pluto":   11.0,
}

# ── SELF-ROTATION PERIODS (relative to Earth = 1.0) ───────────────────────────
SPIN_PERIOD = {
    "Sun":     5.0,   
    "Mercury": 1.5,   
    "Venus":   2.0,   
    "Earth":   1.0,   
    "Mars":    1.1,   
    "Jupiter": 0.3,   
    "Saturn":  0.35,  
    "Uranus":  0.5,   
    "Neptune": 0.45,  
    "Pluto":   1.8,   
    "Moon":    1.2,   
}

# ── AXIAL TILTS (Degrees) ─────────────────────────────────────────────────────
AXIAL_TILT = {
    "Sun":     7.25,
    "Mercury": 0.03,
    "Venus":   177.36, 
    "Earth":   23.44,
    "Mars":    25.19,
    "Jupiter": 3.13,
    "Saturn":  26.73,
    "Uranus":  97.77,
    "Neptune": 28.32,
    "Pluto":   122.53,
    "Moon":    1.54,
}

# Calibration constants
BASE_FRAMES = 300
SPIN_BASE_FRAMES = 10
EARTH_YEAR_DAYS = 365.25

# ── SUN VISUAL PARAMETERS FOR LABELING ────────────────────────────────────────
SUN_VISUAL_CANDIDATES = ["Star_Surface", "Solar_Fire", "Corona"]
SUN_LABEL_MARGIN_FRACTION = -0.10
SUN_LABEL_X_OFFSET_FRACTION = -0.10
SUN_TEXT_SIZE = 3.2
SUN_TEXT_EMISSION = 6.0

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def remove_if_exists(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)


def bake_orbit(empty, frames):
    """Attach a rotation driver to an orbit empty."""
    empty.animation_data_clear()
    driver_fcurve = empty.driver_add("rotation_euler", 2)
    driver = driver_fcurve.driver
    driver.type = 'SCRIPTED'
    driver.expression = f"(frame / {frames}) * {math.tau}"


def bake_spin(obj, spin_name, axis=2):
    """Add a self-rotation driver on the given object along local axis."""
    frames = max(1, round(SPIN_BASE_FRAMES * SPIN_PERIOD.get(spin_name, 1.0)))

    try:
        obj.driver_remove("rotation_euler", axis)
    except Exception:
        pass

    driver_fcurve = obj.driver_add("rotation_euler", axis)
    driver = driver_fcurve.driver
    driver.type = 'SCRIPTED'
    driver.expression = f"(frame / {frames}) * {math.tau}"


def smooth_planet(obj, subdivision_levels=2):
    """Apply smooth shading + Subdivision Surface modifier."""
    if obj is None or obj.type != 'MESH':
        return

    # 1. Smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.data.update()

    # 2. Subdivision Surface
    existing = [m for m in obj.modifiers if m.type == 'SUBSURF']
    if not existing:
        mod = obj.modifiers.new(name="Subsurf_Smooth", type='SUBSURF')
        mod.levels           = subdivision_levels
        mod.render_levels    = subdivision_levels
        mod.subdivision_type = 'CATMULL_CLARK'


def create_orbit_ring(name, radius, parent=None):
    """Create a guide ring via Data API, visible in rendering."""
    ring_name = f"Orbit_{name}"
    remove_if_exists(ring_name)

    # Clean curve data block if it exists
    old_curve = bpy.data.curves.get(ring_name)
    if old_curve:
        bpy.data.curves.remove(old_curve)

    curve_data = bpy.data.curves.new(ring_name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = 0.02  # subtle guide line

    spline = curve_data.splines.new('POLY')
    N = 128
    spline.points.add(N - 1)
    for i in range(N):
        angle = (i / N) * math.tau
        spline.points[i].co = (radius * math.cos(angle), radius * math.sin(angle), 0.0, 1.0)
    spline.use_cyclic_u = True

    ring = bpy.data.objects.new(ring_name, curve_data)
    bpy.context.scene.collection.objects.link(ring)
    ring.hide_render = False

    mat_name = name + "_OrbitMat"
    old_mat = bpy.data.materials.get(mat_name)
    if old_mat:
        bpy.data.materials.remove(old_mat)
        
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    em  = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    em.inputs["Strength"].default_value = 0.12
    links.new(em.outputs["Emission"], out.inputs["Surface"])
    ring.data.materials.append(mat)
    
    if parent:
        ring.parent = parent
        ring.matrix_parent_inverse = Matrix.Identity(4)
        ring.location = (0, 0, 0)


# ── PLANET TRAIL COLOURS (RGBA, rendered glow colour per planet) ──────────────
TRAIL_COLOR = {
    "Mercury": (0.60, 0.58, 0.56, 1.0),  # warm grey
    "Venus":   (0.95, 0.85, 0.50, 1.0),  # golden yellow
    "Earth":   (0.30, 0.65, 1.00, 1.0),  # sky blue
    "Mars":    (0.95, 0.38, 0.15, 1.0),  # rusty orange
    "Jupiter": (0.85, 0.72, 0.55, 1.0),  # tan / cream
    "Saturn":  (0.90, 0.80, 0.55, 1.0),  # pale gold
    "Uranus":  (0.45, 0.88, 0.90, 1.0),  # cyan-teal
    "Neptune": (0.20, 0.45, 0.95, 1.0),  # cobalt blue
    "Pluto":   (0.72, 0.68, 0.62, 1.0),  # pale tan
    "Moon":    (0.80, 0.80, 0.82, 1.0),  # cool silver
}


def _create_taper_curve(name):
    """Create (or reuse) a small taper control curve for a planet trail.

    The taper curve is a NURBS spline in the XY plane whose Y value at each X
    position controls the tube radius of the trail at that point along its
    length.  X=-1 → start (thin tip),  X=+1 → end (thick head).
    """
    taper_name = f"Taper_Trail_{name}"
    # Remove stale object + data so we always start clean
    old_obj = bpy.data.objects.get(taper_name)
    if old_obj:
        bpy.data.objects.remove(old_obj, do_unlink=True)
    old_data = bpy.data.curves.get(taper_name)
    if old_data:
        bpy.data.curves.remove(old_data)

    tdata = bpy.data.curves.new(taper_name, type='CURVE')
    tdata.dimensions = '2D'
    sp = tdata.splines.new('NURBS')
    # 4 control points: (X, Y, Z, W)
    # X runs -1..+1 (= start of trail → head of trail)
    # Y = radius at that point (1 → full bevel_depth at planet, 0 → paper-thin behind)
    pts = [(-1.0,  1.00, 0.0),
           (-0.30, 0.85, 0.0),
           ( 0.30, 0.40, 0.0),
           ( 1.00, 0.00, 0.0)]
    sp.points.add(len(pts) - 1)
    for i, (x, y, z) in enumerate(pts):
        sp.points[i].co = (x, y, z, 1.0)

    tobj = bpy.data.objects.new(taper_name, tdata)
    bpy.context.scene.collection.objects.link(tobj)
    # The taper object must NOT be rendered itself
    tobj.hide_render   = True
    tobj.hide_viewport = True
    return tobj


def create_planet_trail(name, dist_bu, orbit_period_frames):
    """Create a glowing tapered NURBS trail ring for the given planet.

    The trail is a full-circle NURBS ring (same radius as the planet's orbit)
    that rotates at exactly the same angular speed as the planet's orbit empty.
    A taper object makes the trail thin at its start and thick at its head,
    giving the comet-tail illusion.

    Parameters
    ----------
    name : str
        Planet name ("Earth", "Mars", …).
    dist_bu : float
        Orbital radius in Blender Units (must match DISTANCE[name]).
    orbit_period_frames : int
        Number of frames for one complete orbit (must match bake_orbit() call).
    """
    trail_name  = f"Trail_{name}"
    taper_obj   = _create_taper_curve(name)

    # ── Remove stale trail object & its curve data ────────────────────────────
    old_obj  = bpy.data.objects.get(trail_name)
    if old_obj:
        bpy.data.objects.remove(old_obj, do_unlink=True)
    old_data = bpy.data.curves.get(trail_name)
    if old_data:
        bpy.data.curves.remove(old_data)

    # ── Build the NURBS ring ──────────────────────────────────────────────────
    cdata = bpy.data.curves.new(trail_name, type='CURVE')
    cdata.dimensions   = '3D'
    cdata.fill_mode    = 'FULL'
    cdata.bevel_depth  = 0.12          # tube thickness at the thick end
    cdata.bevel_resolution = 4
    cdata.taper_object = taper_obj     # drives the tapered fade

    N  = 128   # number of NURBS control points
    sp = cdata.splines.new('NURBS')
    sp.points.add(N - 1)
    for i in range(N):
        angle = - (i / N) * math.tau
        sp.points[i].co = (
            dist_bu * math.cos(angle),
            dist_bu * math.sin(angle),
            0.0, 1.0
        )
    sp.use_cyclic_u    = False   # open arc so taper start ≠ taper end
    sp.order_u         = 4
    sp.use_endpoint_u  = True

    trail = bpy.data.objects.new(trail_name, cdata)
    bpy.context.scene.collection.objects.link(trail)
    trail.hide_render   = False
    trail.hide_viewport = False

    # ── Emission material (gradient-coloured glow) ────────────────────────────
    mat_name = f"Trail_Mat_{trail_name}"
    old_mat  = bpy.data.materials.get(mat_name)
    if old_mat:
        bpy.data.materials.remove(old_mat)

    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes       = True
    try:
        mat.surface_render_method = 'BLENDED'
    except AttributeError:
        pass
    try:
        mat.blend_method  = 'HASHED'
    except AttributeError:
        pass

    nt    = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    color = TRAIL_COLOR.get(name, (1.0, 1.0, 1.0, 1.0))

    out      = nodes.new("ShaderNodeOutputMaterial")
    mix_main = nodes.new("ShaderNodeMixShader")     # transparent + (emission+bsdf)
    mix_em   = nodes.new("ShaderNodeMixShader")     # emission blend
    transp   = nodes.new("ShaderNodeBsdfTransparent")
    em       = nodes.new("ShaderNodeEmission")
    bsdf     = nodes.new("ShaderNodeBsdfPrincipled")
    grad     = nodes.new("ShaderNodeTexGradient")
    ramp     = nodes.new("ShaderNodeValToRGB")
    coord    = nodes.new("ShaderNodeTexCoord")

    # Gradient driven by the curve's UV (along the trail length)
    grad.gradient_type = 'LINEAR'

    # Colour ramp: opaque coloured at the planet, transparent tail behind
    cr = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = 0.0
    cr.elements[0].color    = (*color[:3], 1.0)        # full colour head at planet
    cr.elements[1].position = 1.0
    cr.elements[1].color    = (0.0, 0.0, 0.0, 0.0)    # fully transparent tail behind

    em.inputs["Color"].default_value    = color
    em.inputs["Strength"].default_value = 0.30
    bsdf.inputs["Alpha"].default_value  = 0.0

    links.new(coord.outputs["UV"],          grad.inputs["Vector"])
    links.new(grad.outputs["Color"],        ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"],        bsdf.inputs["Base Color"])
    links.new(ramp.outputs["Alpha"],        bsdf.inputs["Alpha"])
    links.new(ramp.outputs["Color"],        em.inputs["Color"])
    links.new(bsdf.outputs["BSDF"],         mix_em.inputs[1])
    links.new(em.outputs["Emission"],       mix_em.inputs[2])
    links.new(ramp.outputs["Alpha"],        mix_main.inputs["Fac"])
    links.new(transp.outputs["BSDF"],       mix_main.inputs[1])
    links.new(mix_em.outputs["Shader"],     mix_main.inputs[2])
    links.new(mix_main.outputs["Shader"],   out.inputs["Surface"])

    trail.data.materials.append(mat)

    # ── Rotation driver synced to planet orbit ────────────────────────────────
    fc  = trail.driver_add("rotation_euler", 2)
    drv = fc.driver
    drv.type       = 'SCRIPTED'
    drv.expression = f"(frame / {orbit_period_frames}) * {math.tau}"

    print(f"  ✓ Trail created: {trail_name} (r={dist_bu:.1f} BU, {orbit_period_frames} frames)")


def setup_label(parent_obj, name, x_offset=0.0):
    """Create a billboard text label parented to parent_obj via Data API."""
    label_name = f"Text_{name}"
    remove_if_exists(label_name)

    old_curve = bpy.data.curves.get(label_name)
    if old_curve:
        bpy.data.curves.remove(old_curve)

    font_curve = bpy.data.curves.new(label_name, type='FONT')
    font_curve.body = name
    font_curve.align_x = 'CENTER'
    font_curve.align_y = 'BOTTOM'

    txt = bpy.data.objects.new(label_name, font_curve)
    bpy.context.scene.collection.objects.link(txt)

    mat_name = "Text_Bright_Mat"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        em  = nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1)
        em.inputs["Strength"].default_value = 2.5
        links.new(em.outputs["Emission"], out.inputs["Surface"])
    txt.data.materials.append(mat)

    txt.parent = parent_obj
    txt.matrix_parent_inverse = Matrix.Identity(4)
    
    # Avoid label intersecting the planet sphere by scaling height with planet radius
    planet_radius = SIZE.get(name, 1.0) * PLANET_SIZE_MULTIPLIER
    txt.location = (x_offset, 0, planet_radius + 0.8)

    p_scale = parent_obj.scale[0]
    inv_scale = TEXT_SIZE / p_scale if p_scale > 0 else TEXT_SIZE
    txt.scale = (inv_scale, inv_scale, inv_scale)

    camera = bpy.context.scene.camera
    if camera:
        con = txt.constraints.new(type='COPY_ROTATION')
        con.target = camera


def get_sun_world_radius():
    """Return the largest world-space radius among the visual candidate objects."""
    max_radius = 0.0
    found_name = None
    for name in SUN_VISUAL_CANDIDATES:
        obj = bpy.data.objects.get(name)
        if not obj:
            continue
        radius = max(obj.dimensions.x, obj.dimensions.y, obj.dimensions.z) / 2.0
        if radius > max_radius:
            max_radius = radius
            found_name = name
    return max_radius, found_name


def setup_sun_label(parent_obj):
    """Sets up a non-spinning, constraint-based billboard label for the Sun."""
    label_name = "Text_Sun"
    remove_if_exists(label_name)

    world_radius, source_name = get_sun_world_radius()
    if world_radius <= 0:
        world_radius = 4.0
        source_name = "(default)"

    old_curve = bpy.data.curves.get(label_name)
    if old_curve:
        bpy.data.curves.remove(old_curve)

    font_curve = bpy.data.curves.new(label_name, type='FONT')
    font_curve.body = "Sun"
    font_curve.align_x = 'CENTER'
    font_curve.align_y = 'BOTTOM'

    txt = bpy.data.objects.new(label_name, font_curve)
    bpy.context.scene.collection.objects.link(txt)

    mat_name = "Text_Sun_Bright_Mat"
    mat = bpy.data.materials.get(mat_name)
    if mat:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    em  = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value    = (1.0, 1.0, 1.0, 1.0)
    em.inputs["Strength"].default_value = SUN_TEXT_EMISSION
    links.new(em.outputs["Emission"], out.inputs["Surface"])
    txt.data.materials.append(mat)

    world_height = world_radius * (1.0 + SUN_LABEL_MARGIN_FRACTION)
    world_x_offset = world_radius * SUN_LABEL_X_OFFSET_FRACTION

    # Positions the label with offset, avoiding parent-based rotation spin
    txt.location = (world_x_offset, 0, world_height)
    txt.scale = (SUN_TEXT_SIZE, SUN_TEXT_SIZE, SUN_TEXT_SIZE)

    loc_con = txt.constraints.new(type='COPY_LOCATION')
    loc_con.target = parent_obj
    loc_con.use_offset = True

    camera = bpy.context.scene.camera
    if camera:
        con = txt.constraints.new(type='TRACK_TO')
        con.target = camera
        con.track_axis = 'TRACK_Z'
        con.up_axis = 'UP_Y'
        print(f"  ✓ Sun label tracks active camera: {camera.name}")
    else:
        print("  ⚠ No active camera found — Sun label won't auto-face viewport.")

    print(f"  ✓ Sun label added (radius source: '{source_name}', radius: {world_radius:.2f})")


def setup_sun_rotation(sun_obj):
    """Sets up accurate physical rotation animation on the Sun object."""
    # Sidereal period 25.05 days
    sun_period_frames = 25.05 * (BASE_FRAMES / EARTH_YEAR_DAYS)

    if sun_obj.animation_data:
        drivers = [d for d in sun_obj.animation_data.drivers if d.data_path == "rotation_euler"]
        for d in drivers:
            sun_obj.animation_data.drivers.remove(d)
        action = sun_obj.animation_data.action
        if action:
            fcurves = [fc for fc in action.fcurves if fc.data_path == "rotation_euler"]
            for fc in fcurves:
                action.fcurves.remove(fc)

    sun_obj.rotation_mode = 'XYZ'
    sun_obj.rotation_euler[0] = math.radians(AXIAL_TILT["Sun"])
    sun_obj.rotation_euler[1] = 0.0

    fc = sun_obj.driver_add("rotation_euler", 2)
    drv = fc.driver
    drv.type = 'SCRIPTED'
    drv.expression = f"(frame / {sun_period_frames:.6f}) * {math.tau}"
    
    print(f"  ✓ Sun rotation configured ({sun_period_frames:.4f} frames period)")


def setup_moon():
    earth = bpy.data.objects.get("Earth")
    moon  = bpy.data.objects.get("Moon")
    if not earth or not moon:
        return

    m_scale = 0.273 * PLANET_SIZE_MULTIPLIER
    moon.scale = (m_scale, m_scale, m_scale)

    empty_name = "Orbit_Moon_Empty"
    remove_if_exists(empty_name)

    m_empty = bpy.data.objects.new(empty_name, None)
    m_empty.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(m_empty)

    m_empty.parent = earth
    m_empty.matrix_parent_inverse = Matrix.Identity(4)
    m_empty.location = (0, 0, 0)

    desired_visual_gap = 4.0
    local_dist = desired_visual_gap / earth.scale[0]

    moon.parent = m_empty
    moon.matrix_parent_inverse = Matrix.Identity(4)
    moon.location = (local_dist, 0, 0)

    moon.rotation_mode = 'ZXY'
    moon.rotation_euler[0] = math.radians(AXIAL_TILT["Moon"])

    smooth_planet(moon)

    moon_period = max(1, round(BASE_FRAMES * 0.2))
    bake_orbit(m_empty, moon_period)
    # Moon is tidally locked to Earth — it naturally inherits orbit rotation from parent empty, so no self-spin driver is added.

    create_orbit_ring("Moon_Ring", local_dist, parent=earth)
    # Moon trail: radius in world space = local_dist * earth.scale[0]
    moon_world_dist = local_dist * earth.scale[0]
    create_planet_trail("Moon", moon_world_dist, moon_period)
    setup_label(m_empty, "Moon", x_offset=local_dist)


def setup_planet(name):
    planet = bpy.data.objects.get(name)
    if not planet:
        return

    real_scale = SIZE[name] * PLANET_SIZE_MULTIPLIER
    planet.scale = (real_scale, real_scale, real_scale)
    dist   = DISTANCE[name]
    frames = max(1, round(BASE_FRAMES * PERIOD[name]))

    empty_name = f"Orbit_{name}_Empty"
    remove_if_exists(empty_name)

    empty = bpy.data.objects.new(empty_name, None)
    empty.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(empty)

    planet.parent = empty
    planet.matrix_parent_inverse = Matrix.Identity(4)
    planet.location = (dist, 0, 0)

    planet.rotation_mode = 'ZXY'
    planet.rotation_euler[0] = math.radians(AXIAL_TILT[name])

    smooth_planet(planet)

    bake_orbit(empty, frames)
    bake_spin(planet, name)

    create_orbit_ring(name, dist)
    create_planet_trail(name, dist, frames)
    setup_label(empty, name, x_offset=dist)

# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def run():
    print("\n🎬 Consolidating Orrery Simulation Setup...")
    scene = bpy.context.scene
    
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    remove_if_exists("Label_Master_Target")

    sun_obj = bpy.data.objects.get(SUN_NAME)
    if sun_obj:
        sun_obj.location = (0, 0, 0)
        smooth_planet(sun_obj, subdivision_levels=2)
        setup_sun_rotation(sun_obj)
        setup_sun_label(sun_obj)
    
    planets = [
        "Mercury", "Venus", "Earth", "Mars",
        "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
    ]
    for p in planets:
        setup_planet(p)

    setup_moon()

    # Disable relationship line overlays in View3D viewport
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.overlay.show_relationship_lines = False

    print("\n🎬 Hollywood Continuous Loop Calibrated!")
    print("🌍 Authentic Axial Tilts Added: ZXY rotation order fixed planet wobbles.")
    print("✨ Orbits and Empties successfully rebuilt using robust Data API calls.")


if __name__ == "__main__":
    run()
