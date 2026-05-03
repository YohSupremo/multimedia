"""
Earth + Moon — Orbit Only (Refined)
=====================================
This script ONLY handles the Moon's orbital path around Earth.
Tilt and spin are left entirely to the Earth and Moon material scripts.

Blender 5.1 compatible
"""

import bpy
import math

# ── SETTINGS ──────────────────────────────────────────────────────────────────
EARTH_RADIUS_BU  = 1.0

MOON_ORBIT_RATIO = 384400.0 / 6371.0   # 60.327
MOON_SIZE_RATIO  = 1737.4   / 6371.0   # 0.27270

MOON_SCALE_BOOST = 1.0
ORBIT_SCALE      = 0.15

MOON_ORBIT_FRAMES = 274    # frames per full Moon orbit
ANIM_END          = 270    # ~3 Moon orbits

MOON_ORBIT_BU  = EARTH_RADIUS_BU * MOON_ORBIT_RATIO * ORBIT_SCALE
MOON_RADIUS_BU = EARTH_RADIUS_BU * MOON_SIZE_RATIO  * MOON_SCALE_BOOST

MOON_ORBIT_TILT_DEG = 5.145   # orbital plane inclination only
# ─────────────────────────────────────────────────────────────────────────────


def remove_if_exists(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)


def _set_linear(action):
    """Blender 5.1 compatible linear interpolation setter."""
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
        try:
            for fc in action.fcurves:
                fc.extrapolation = 'LINEAR'
                for kp in fc.keyframe_points:
                    kp.interpolation     = 'LINEAR'
                    kp.handle_left_type  = 'VECTOR'
                    kp.handle_right_type = 'VECTOR'
        except Exception:
            pass


def bake_orbit_z(spin_empty, orbit_frames, total_frames):
    """
    Animate ONLY the Z rotation of the spin empty — this drives the orbit.
    Does NOT touch the Moon object's own rotation at all.
    """
    spin_empty.animation_data_clear()
    spin_empty.rotation_mode = 'XYZ'
    for frame in range(1, total_frames + 1):
        t = (frame - 1) % orbit_frames
        spin_empty.rotation_euler = (0.0, 0.0, (t / orbit_frames) * math.tau)
        spin_empty.keyframe_insert("rotation_euler", frame=frame)
    _set_linear(spin_empty.animation_data.action if spin_empty.animation_data else None)


def make_orbit_ring(tilt_empty, orbit_bu, color):
    name      = tilt_empty.name.replace("Tilt_Empty_", "")
    ring_name = f"Orbit_Ring_{name}"
    remove_if_exists(ring_name)

    bpy.ops.curve.primitive_nurbs_circle_add(radius=orbit_bu, location=(0, 0, 0))
    ring = bpy.context.active_object
    ring.name        = ring_name
    ring.hide_render = True
    ring.rotation_euler = (0, 0, 0)

    ring.parent = tilt_empty
    ring.matrix_parent_inverse = tilt_empty.matrix_world.inverted()

    ring.data.bevel_depth   = 0.008
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


def setup_moon_orbit(moon, name, orbit_bu, moon_radius_bu, orbit_frames, orbit_tilt_deg, color):
    """
    Sets up ONLY the orbital hierarchy and movement.

    Hierarchy:
        Tilt_Empty  (fixed orbital plane inclination) 
            └── Spin_Empty  (animated Z rotation = orbit)
                    └── Moon  (positioned at X = orbit_bu, self-rotation untouched)
        Tilt_Empty  └── Orbit_Ring

    The Moon object's own rotation_euler is NOT keyframed here.
    Run your Moon material/spin script AFTER this to add self-rotation.
    """
    tilt_name = f"Tilt_Empty_{name}"
    spin_name = f"Spin_Empty_{name}"
    remove_if_exists(tilt_name)
    remove_if_exists(spin_name)

    # Scale the moon to correct size
    moon.scale = (moon_radius_bu, moon_radius_bu, moon_radius_bu)

    # Clear any existing parent — use CLEAR (not CLEAR_KEEP_TRANSFORM)
    # CLEAR_KEEP_TRANSFORM bakes world transform into local, collapsing animation keyframes.
    # CLEAR just removes the parent link, leaving local rotation keyframes intact.
    moon.constraints.clear()
    if moon.parent:
        moon.parent = None
        moon.matrix_parent_inverse.identity()

    # Tilt empty — static orbital inclination only, no animation
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    tilt_empty = bpy.context.active_object
    tilt_empty.name = tilt_name
    tilt_empty.rotation_euler = (math.radians(orbit_tilt_deg), 0, 0)
    tilt_empty.animation_data_clear()

    # Spin empty — animated Z orbit, child of tilt empty
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    spin_empty = bpy.context.active_object
    spin_empty.name = spin_name
    spin_empty.parent = tilt_empty
    spin_empty.matrix_parent_inverse = tilt_empty.matrix_world.inverted()
    bake_orbit_z(spin_empty, orbit_frames, ANIM_END)

    # Parent Moon to spin empty, offset along local X = orbital radius
    moon.parent = spin_empty
    moon.matrix_parent_inverse = spin_empty.matrix_world.inverted()
    moon.location = (orbit_bu, 0, 0)

    # NOTE: moon.rotation_euler is intentionally left alone here.
    # Your Moon material script handles tilt + spin on the Moon object directly.

    # Orbit ring visual
    make_orbit_ring(tilt_empty, orbit_bu, color)

    print(f"   {name}: orbit {orbit_bu:.3f} BU | radius {moon_radius_bu:.4f} BU | "
          f"orbital incl {orbit_tilt_deg}° | {orbit_frames} frames/orbit")
    print(f"   ✅ Moon self-rotation left to Moon material script")


def setup():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    earth = bpy.data.objects.get("Earth")
    moon  = bpy.data.objects.get("Moon")
    if not earth: raise RuntimeError("❌ No object named 'Earth'!")
    if not moon:  raise RuntimeError("❌ No object named 'Moon'!")

    # Earth — orbit script does NOT touch Earth rotation or tilt.
    # Your Earth material script handles that independently.
    earth.location = (0, 0, 0)
    earth.scale    = (EARTH_RADIUS_BU,) * 3
    print("✅ Earth position/scale set — tilt & spin left to Earth material script")

    # Moon orbit only
    print("Baking Moon orbit...")
    setup_moon_orbit(
        moon           = moon,
        name           = "Moon",
        orbit_bu       = MOON_ORBIT_BU,
        moon_radius_bu = MOON_RADIUS_BU,
        orbit_frames   = MOON_ORBIT_FRAMES,
        orbit_tilt_deg = MOON_ORBIT_TILT_DEG,
        color          = (0.85, 0.88, 0.95),
    )
    print(f"✅ Moon orbit — {ANIM_END // MOON_ORBIT_FRAMES} full orbits over {ANIM_END} frames")

    scene.frame_set(1)
    print("\n🌍 Orbit setup complete!")
    print("   Run your Earth material script → handles Earth tilt + spin")
    print("   Run your Moon material script  → handles Moon tilt + spin")
    print(f"   ORBIT_SCALE={ORBIT_SCALE} → Moon orbit = {MOON_ORBIT_BU:.2f} BU")


setup()