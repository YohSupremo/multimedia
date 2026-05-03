"""
Mars + Phobos + Deimos — ORBIT ONLY
=====================================
This script handles ONLY orbital movement.
Mars tilt + spin       → handled by mars_material.py
Phobos tilt + spin     → handled by phobos_material.py
Deimos tilt + spin     → handled by deimos_material.py

RUN ORDER (mandatory):
  1. mars_orbit_only.py      ← sets up hierarchy / parenting FIRST
  2. mars_material.py        ← Mars tilt + spin (no parent, safe anytime after)
  3. phobos_material.py      ← Phobos tilt + spin in local space
  4. deimos_material.py      ← Deimos tilt + spin in local space

Blender 5.1 compatible.

REAL DATA:
  Mars radius:            3,389 km
  Phobos orbit:           9,377 km  = 2.766× Mars radius
  Phobos period:          7.66 hr
  Phobos inclination:     1.08°
  Deimos orbit:           23,460 km = 6.922× Mars radius
  Deimos period:          30.35 hr
  Deimos inclination:     0.93°
"""

import bpy
import math

# ── SETTINGS ──────────────────────────────────────────────────────────────────
MARS_RADIUS_BU      = 1.0

PHOBOS_ORBIT_RATIO  = 9377.0  / 3389.0   # 2.766
DEIMOS_ORBIT_RATIO  = 23460.0 / 3389.0   # 6.922

PHOBOS_SIZE_RATIO   = 11.1  / 3389.0     # 0.003275
DEIMOS_SIZE_RATIO   = 6.3   / 3389.0     # 0.001859

MOON_SCALE_BOOST    = 80.0   # moons are invisible at true scale; boost for visibility

PHOBOS_ORBIT_TILT   = 1.08   # orbital plane inclination only
DEIMOS_ORBIT_TILT   = 0.93

# Frame counts — preserve real period ratios
# Real: Phobos 7.66 hr, Deimos 30.35 hr, Mars day 24.62 hr
PHOBOS_ORBIT_FRAMES = 46
DEIMOS_ORBIT_FRAMES = round(PHOBOS_ORBIT_FRAMES * (30.35 / 7.66))   # 182
ANIM_END            = 500

PHOBOS_ORBIT_BU  = MARS_RADIUS_BU * PHOBOS_ORBIT_RATIO
DEIMOS_ORBIT_BU  = MARS_RADIUS_BU * DEIMOS_ORBIT_RATIO
PHOBOS_RADIUS_BU = MARS_RADIUS_BU * PHOBOS_SIZE_RATIO * MOON_SCALE_BOOST
DEIMOS_RADIUS_BU = MARS_RADIUS_BU * DEIMOS_SIZE_RATIO * MOON_SCALE_BOOST
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
        for fc in action.fcurves:
            fc.extrapolation = 'LINEAR'
            for kp in fc.keyframe_points:
                kp.interpolation     = 'LINEAR'
                kp.handle_left_type  = 'VECTOR'
                kp.handle_right_type = 'VECTOR'


def bake_orbit_z(spin_empty, orbit_frames, total_frames):
    """
    Animate ONLY the spin empty's Z rotation — drives the orbital movement.
    Does NOT touch the moon object's own rotation at all.
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
    ring.data.bevel_depth   = 0.01
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
    Sets up ONLY the orbital hierarchy. Moon self-rotation is untouched.

    Hierarchy:
        Tilt_Empty  (fixed orbital plane inclination, no animation)
            └── Spin_Empty  (animated Z = orbit)
                    └── Moon  (at X = orbit_bu, self-rotation left to material script)
        Tilt_Empty  └── Orbit_Ring
    """
    tilt_name = f"Tilt_Empty_{name}"
    spin_name = f"Spin_Empty_{name}"
    remove_if_exists(tilt_name)
    remove_if_exists(spin_name)

    moon.scale = (moon_radius_bu, moon_radius_bu, moon_radius_bu)
    moon.constraints.clear()

    # Remove parent without touching keyframes
    if moon.parent:
        moon.parent = None
        moon.matrix_parent_inverse.identity()

    # Tilt empty — static orbital inclination, never animated
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

    # Parent moon to spin empty, offset to orbital radius
    moon.parent = spin_empty
    moon.matrix_parent_inverse = spin_empty.matrix_world.inverted()
    moon.location = (orbit_bu, 0, 0)

    # NOTE: moon.rotation_euler intentionally untouched.
    # Run phobos_material.py / deimos_material.py AFTER this script.

    make_orbit_ring(tilt_empty, orbit_bu, color)

    print(f"   {name}: orbit {orbit_bu:.3f} BU | radius {moon_radius_bu:.4f} BU | "
          f"orbital incl {orbit_tilt_deg}° | {orbit_frames} frames/orbit")
    print(f"   ✅ {name} self-rotation left to material script")


def setup():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    mars   = bpy.data.objects.get("Mars")
    phobos = bpy.data.objects.get("Phobos")
    deimos = bpy.data.objects.get("Deimos")

    if not mars:   raise RuntimeError("❌ No object named 'Mars'!")
    if not phobos: raise RuntimeError("❌ No object named 'Phobos'!")
    if not deimos: raise RuntimeError("❌ No object named 'Deimos'!")

    # Mars — orbit script only sets position and scale.
    # Tilt and spin are left entirely to mars_material.py.
    mars.location = (0, 0, 0)
    mars.scale    = (MARS_RADIUS_BU,) * 3
    print("✅ Mars position/scale set — tilt & spin left to mars_material.py")

    print("Baking Phobos orbit...")
    setup_moon_orbit(
        moon           = phobos,
        name           = "Phobos",
        orbit_bu       = PHOBOS_ORBIT_BU,
        moon_radius_bu = PHOBOS_RADIUS_BU,
        orbit_frames   = PHOBOS_ORBIT_FRAMES,
        orbit_tilt_deg = PHOBOS_ORBIT_TILT,
        color          = (0.85, 0.72, 0.58),
    )
    print(f"✅ Phobos — {ANIM_END // PHOBOS_ORBIT_FRAMES} orbits over {ANIM_END} frames")

    print("Baking Deimos orbit...")
    setup_moon_orbit(
        moon           = deimos,
        name           = "Deimos",
        orbit_bu       = DEIMOS_ORBIT_BU,
        moon_radius_bu = DEIMOS_RADIUS_BU,
        orbit_frames   = DEIMOS_ORBIT_FRAMES,
        orbit_tilt_deg = DEIMOS_ORBIT_TILT,
        color          = (0.55, 0.62, 0.75),
    )
    print(f"✅ Deimos — {ANIM_END // DEIMOS_ORBIT_FRAMES} orbits over {ANIM_END} frames")

    scene.frame_set(1)
    print("\n🔴 Mars orbit setup complete!")
    print("   Next: run mars_material.py, phobos_material.py, deimos_material.py")
    print(f"\n   Phobos orbit: {PHOBOS_ORBIT_BU:.3f} BU | Deimos orbit: {DEIMOS_ORBIT_BU:.3f} BU")
    print(f"   Moon size boost: {MOON_SCALE_BOOST}× (set to 1.0 for true scale)")


setup()