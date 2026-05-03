"""
Neptune — Triton Orbit Animation (Tidally Locked)
=================================
Blender 4+/5  |  Based on Uranus moon reference pattern.

HOW TO USE:
  1. Run your Neptune script first (so Neptune exists in scene)
  2. Create 1 UV Sphere object named exactly: Triton
  3. Run this script in Scripting tab
"""

import bpy
import math
from mathutils import Matrix

# ── TOGGLE ────────────────────────────────────────────────────────────────────
RECORDING_MODE = True

# ── SETTINGS ──────────────────────────────────────────────────────────────────
NEPTUNE_RADIUS_BU = 7.60
SEGMENTS          = 128
RINGS             = 64
ANIM_END          = 250

# ── Orbital period ────────────────────────────────────────────────────────────
TRITON_ORBIT_FRAMES = 80   # base frames per orbit

# ── Real size ratio (Triton radius / Neptune radius) ─────────────────────────
TRITON_SIZE_RATIO  = 1353.4 / 24622.0   # ~0.0550

# ── Real orbit ratio (orbit radius / Neptune radius) ─────────────────────────
TRITON_ORBIT_RATIO = 354759.0 / 24622.0  # ~14.41

# ── Orbital inclination ───────────────────────────────────────────────────────
TRITON_TILT_DEG = 156.865

# ── Texture path ──────────────────────────────────────────────────────────────
TEXTURE_BASE = r"C:\Users\kelly\Downloads\Blender\textures"
TRITON_TEX   = TEXTURE_BASE + r"\triton_moon.jpg"

# ── Orbit & size calculation ──────────────────────────────────────────────────
if RECORDING_MODE:
    TRITON_ORBIT_BU  = NEPTUNE_RADIUS_BU * 4.0    # ~30.4 BU
    TRITON_RADIUS_BU = NEPTUNE_RADIUS_BU * 0.085  # ~0.65 BU
else:
    MOON_SCALE_BOOST = 500
    TRITON_ORBIT_BU  = NEPTUNE_RADIUS_BU * TRITON_ORBIT_RATIO
    TRITON_RADIUS_BU = NEPTUNE_RADIUS_BU * TRITON_SIZE_RATIO * MOON_SCALE_BOOST


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def remove_if_exists(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)


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


def bake_rotation_retrograde(obj, period_frames, tilt_deg, total_frames):
    """
    Triton orbits RETROGRADE — opposite direction to normal moons.
    We achieve this by animating angle_z in NEGATIVE direction (clockwise).
    """
    if obj.animation_data:
        obj.animation_data_clear()
        
    obj.rotation_mode = 'XYZ'
    ix = math.radians(tilt_deg)
    for frame in range(1, total_frames + 1):
        t = (frame - 1) % period_frames
        # NEGATIVE angle = retrograde (clockwise when viewed from north pole)
        angle_z = -((t / period_frames) * math.tau)
        obj.rotation_euler = (ix, 0.0, angle_z)
        obj.keyframe_insert("rotation_euler", frame=frame)
    _set_linear(obj.animation_data.action if obj.animation_data else None)


def fix_mesh(obj):
    """Replace mesh with clean high-res UV sphere — smooth shading, no polygonal look."""
    bpy.context.view_layer.objects.active = obj
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

    try:
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(30)
    except AttributeError:
        pass  


def hard_reset_object(obj):
    obj.animation_data_clear()
    obj.constraints.clear()
    if obj.parent is not None:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    obj.location       = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.rotation_mode  = 'XYZ'
    obj.scale          = (1.0, 1.0, 1.0)
    obj.matrix_parent_inverse = Matrix.Identity(4)


def make_orbit_ring(name, radius_bu, color, tilt_deg):
    """Decorative orbit path — viewport only, hidden in render."""
    ring_name = f"Orbit_Ring_{name}"
    remove_if_exists(ring_name)
    bpy.ops.curve.primitive_nurbs_circle_add(radius=radius_bu, location=(0, 0, 0))
    ring = bpy.context.active_object
    ring.name              = ring_name
    ring.hide_render       = True
    ring.rotation_euler[0] = math.radians(tilt_deg)
    ring.data.bevel_depth  = 0.06 if RECORDING_MODE else 0.04
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


def build_triton_material(obj):
    import os

    mat_name = "Triton_Mat"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    def N(t, loc):
        n = nodes.new(t); n.location = loc; return n

    out  = N("ShaderNodeOutputMaterial", (1000, 0))
    bsdf = N("ShaderNodeBsdfPrincipled", (600,  0))
    bsdf.inputs["Roughness"].default_value          = 0.95   
    bsdf.inputs["Specular IOR Level"].default_value = 0.02   
    bsdf.inputs["Metallic"].default_value           = 0.0

    emit   = N("ShaderNodeEmission", (200, -300))
    emit.inputs["Color"].default_value    = (0.55, 0.48, 0.45, 1.0)  
    emit.inputs["Strength"].default_value = 0.006

    add_sh = N("ShaderNodeAddShader", (800, -100))

    if os.path.exists(TRITON_TEX):
        print(f"   ✅ Triton texture loaded: {TRITON_TEX}")

        tex_c   = N("ShaderNodeTexCoord", (-900, 0))
        mapping = N("ShaderNodeMapping",  (-700, 0))
        tex     = N("ShaderNodeTexImage", (-480, 120))
        tex.image = bpy.data.images.load(TRITON_TEX, check_existing=True)

        rgb_to_bw = N("ShaderNodeRGBToBW", (-220, 120))

        ramp = N("ShaderNodeValToRGB", (20, 120))
        cr = ramp.color_ramp
        cr.interpolation = 'EASE'
        cr.elements[0].position = 0.0; cr.elements[0].color = (0.12, 0.10, 0.09, 1.0)  
        cr.elements[1].position = 1.0; cr.elements[1].color = (0.82, 0.76, 0.72, 1.0)  
        e = cr.elements.new(0.30); e.color = (0.35, 0.30, 0.28, 1.0)                   
        e = cr.elements.new(0.60); e.color = (0.65, 0.58, 0.54, 1.0)                   

        bump = N("ShaderNodeBump", (300, -150))
        bump.inputs["Strength"].default_value = 0.35   
        bump.inputs["Distance"].default_value = 0.02

        links.new(tex_c.outputs["UV"],       mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"],      rgb_to_bw.inputs["Color"])
        links.new(rgb_to_bw.outputs["Val"],  ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"],     bsdf.inputs["Base Color"])
        links.new(rgb_to_bw.outputs["Val"],  bump.inputs["Height"])
        links.new(bump.outputs["Normal"],    bsdf.inputs["Normal"])

    else:
        print(f"   ⚠  No texture at {TRITON_TEX} — using procedural fallback")

        tex_c = N("ShaderNodeTexCoord", (-700, 0))

        noise_base = N("ShaderNodeTexNoise", (-500, 100))
        noise_base.inputs["Scale"].default_value      = 3.5
        noise_base.inputs["Detail"].default_value     = 8.0
        noise_base.inputs["Roughness"].default_value  = 0.60
        noise_base.inputs["Distortion"].default_value = 0.25

        noise_fine = N("ShaderNodeTexNoise", (-500, -150))
        noise_fine.inputs["Scale"].default_value      = 12.0
        noise_fine.inputs["Detail"].default_value     = 14.0
        noise_fine.inputs["Roughness"].default_value  = 0.75
        noise_fine.inputs["Distortion"].default_value = 0.8

        ramp_base = N("ShaderNodeValToRGB", (-220, 100))
        cr = ramp_base.color_ramp
        cr.interpolation = 'EASE'
        cr.elements[0].position = 0.0; cr.elements[0].color = (0.10, 0.08, 0.07, 1.0)  
        cr.elements[1].position = 1.0; cr.elements[1].color = (0.78, 0.72, 0.68, 1.0)  
        e = cr.elements.new(0.40); e.color = (0.42, 0.37, 0.34, 1.0)                   
        e = cr.elements.new(0.70); e.color = (0.62, 0.56, 0.52, 1.0)                   

        mix_detail = N("ShaderNodeMixRGB", (20, -50))
        mix_detail.blend_type = 'OVERLAY'
        mix_detail.inputs["Fac"].default_value = 0.18   

        mix_bump = N("ShaderNodeMixRGB", (20, -200))
        mix_bump.blend_type = 'ADD'
        mix_bump.inputs["Fac"].default_value = 0.5

        bump = N("ShaderNodeBump", (240, -200))
        bump.inputs["Strength"].default_value = 0.40
        bump.inputs["Distance"].default_value = 0.025

        links.new(tex_c.outputs["Normal"],     noise_base.inputs["Vector"])
        links.new(tex_c.outputs["Normal"],     noise_fine.inputs["Vector"])
        links.new(noise_base.outputs["Fac"],   ramp_base.inputs["Fac"])
        links.new(ramp_base.outputs["Color"],  mix_detail.inputs["Color1"])
        links.new(noise_fine.outputs["Color"], mix_detail.inputs["Color2"])
        links.new(mix_detail.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(noise_base.outputs["Fac"],   mix_bump.inputs["Color1"])
        links.new(noise_fine.outputs["Fac"],   mix_bump.inputs["Color2"])
        links.new(mix_bump.outputs["Color"],   bump.inputs["Height"])
        links.new(bump.outputs["Normal"],      bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"],     add_sh.inputs[0])
    links.new(emit.outputs["Emission"], add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"], out.inputs["Surface"])


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def setup():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    triton = bpy.data.objects.get("Triton")
    if triton is None:
        raise RuntimeError(
            "❌  No object named 'Triton' found!\n"
            "    Create a UV Sphere object named exactly 'Triton' and re-run."
        )

    empty_name = "Orbit_Empty_Triton"
    remove_if_exists(empty_name)

    print("\n🔵 Setting up Triton...")

    hard_reset_object(triton)
    fix_mesh(triton)
    build_triton_material(triton)

    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.0))
    empty = bpy.context.active_object
    empty.name           = empty_name
    empty.rotation_euler = (0.0, 0.0, 0.0)
    empty.location       = (0.0, 0.0, 0.0)

    bpy.ops.object.select_all(action='DESELECT')
    triton.parent                = empty
    triton.matrix_parent_inverse = Matrix.Identity(4)
    triton.location              = (TRITON_ORBIT_BU, 0.0, 0.0)
    triton.rotation_euler        = (0.0, 0.0, 0.0)
    triton.scale                 = (TRITON_RADIUS_BU, TRITON_RADIUS_BU, TRITON_RADIUS_BU)

    # ── Bake RETROGRADE orbit animation on the empty ──
    # Because Triton is parented to this Empty, this naturally sweeps it around
    # Neptune AND keeps it perfectly tidally locked!
    bake_rotation_retrograde(empty, TRITON_ORBIT_FRAMES, 0.0, ANIM_END)

    make_orbit_ring("Triton", TRITON_ORBIT_BU, (0.75, 0.68, 0.65), 0.0)

    scene.frame_set(1)

    print()
    print("✅ Triton complete!")
    print(f"   Orbit:      {TRITON_ORBIT_BU:.1f} BU from Neptune center")
    print(f"   Radius:     {TRITON_RADIUS_BU:.3f} BU")
    print(f"   Orbit Rate: {TRITON_ORBIT_FRAMES} frames/orbit")
    print(f"   Rotation:   PERFECTLY TIDALLY LOCKED")
    print(f"   Direction:  RETROGRADE (clockwise)")
    print(f"   NOTE: Rename your sphere object to 'Triton' before running!")


setup()