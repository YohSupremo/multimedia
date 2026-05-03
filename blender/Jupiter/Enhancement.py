"""
Fix Jupiter — High-Res Mesh + Preserve Rotation + Color Enhancement
====================================================================
Blender 5.0

This script:
  1. Deletes old low-poly Jupiter, creates fresh 128×64 UV sphere
  2. PRESERVES the existing spin animation (rebakes it automatically)
  3. Restores your texture material
  4. Adds color enhancement — warmer, more saturated, deeper contrast
     to match the vivid orange/brown/cream look in the reference image

Object name: "Jupiter" (change OBJECT_NAME if different)
"""

import bpy
import math

OBJECT_NAME       = "Jupiter"
SEGMENTS          = 128
RINGS             = 64
JUPITER_RADIUS_BU = 11.21
OBLATE_FACTOR     = 0.935
JUPITER_TILT_DEG  = 3.13

# ── Spin period — must match your main script ─────────────────────────────────
IO_ORBIT_FRAMES     = 60
JUPITER_SPIN_FRAMES = round(IO_ORBIT_FRAMES * (1.769 * 24 / 9.925))
ANIM_END            = 250

# ─────────────────────────────────────────────────────────────────────────────

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


def bake_rotation_z(obj, period_frames, tilt_deg, total_frames):
    """Rebake the spin animation onto the object."""
    obj.animation_data_clear()
    obj.rotation_mode = 'XYZ'
    tilt_rad = math.radians(tilt_deg)
    for frame in range(1, total_frames + 1):
        t       = (frame - 1) % period_frames
        angle_z = (t / period_frames) * math.tau
        obj.rotation_euler = (tilt_rad, 0.0, angle_z)
        obj.keyframe_insert("rotation_euler", frame=frame)
    _set_linear(obj.animation_data.action if obj.animation_data else None)
    print(f"   Spin rebaked: {period_frames} frames/rotation, tilt={tilt_deg}°")


def enhance_jupiter_material(obj):
    """
    Find Jupiter's existing image texture material and enhance it:
      - Boost saturation (more vivid orange/brown bands)
      - Warm the hue slightly toward orange
      - Add contrast via RGB Curves
      - Slight emission so the planet glows warmly
    Safely skips enhancement if no material or texture node is found.
    """
    if not obj.data.materials:
        print("   ⚠ No material found — skipping enhancement")
        return

    mat = obj.data.materials[0]
    if mat is None or not mat.use_nodes:
        print("   ⚠ Material has no nodes — skipping enhancement")
        return

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find the existing Principled BSDF and Output
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    out  = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    tex  = next((n for n in nodes if n.type == 'TEX_IMAGE'), None)

    if bsdf is None or out is None:
        print("   ⚠ Could not find BSDF/Output nodes — skipping enhancement")
        return

    # ── Adjust BSDF properties ────────────────────────────────────────────────
    bsdf.inputs["Roughness"].default_value          = 0.82
    bsdf.inputs["Specular IOR Level"].default_value = 0.03
    bsdf.inputs["Metallic"].default_value           = 0.0

    # ── Remove any old enhancement nodes to avoid duplicates ──────────────────
    for name in ["Jupiter_HueSat", "Jupiter_Curves", "Jupiter_Emit",
                 "Jupiter_AddShader", "Jupiter_Mapping", "Jupiter_TexCoord"]:
        n = nodes.get(name)
        if n:
            nodes.remove(n)

    def N(t, loc, name=None):
        node = nodes.new(t)
        node.location = loc
        if name:
            node.name  = name
            node.label = name
        return node

    # ── Find what is currently feeding Base Color ─────────────────────────────
    base_color_input = bsdf.inputs["Base Color"]
    existing_link = base_color_input.links[0] if base_color_input.links else None
    source_socket = existing_link.from_socket if existing_link else None

    # Disconnect existing link to Base Color so we can insert nodes
    if existing_link:
        links.remove(existing_link)

    # ── Hue / Saturation — warmer, more vivid ─────────────────────────────────
    hue_sat = N("ShaderNodeHueSaturation", (-100, 200), "Jupiter_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.52   # slight warm shift
    hue_sat.inputs["Saturation"].default_value = 1.55   # punchy colour
    hue_sat.inputs["Value"].default_value      = 1.05

    # ── RGB Curves — deepen shadows, lift highlights slightly ─────────────────
    curves = N("ShaderNodeRGBCurve", (120, 200), "Jupiter_Curves")
    # S-curve on combined channel for contrast
    c = curves.mapping.curves[3]   # index 3 = combined (C)
    c.points[0].location = (0.0,  0.0)    # black stays black
    c.points[1].location = (1.0,  1.0)    # white stays white
    c.points.new(0.25, 0.18)              # pull shadows down
    c.points.new(0.75, 0.82)              # push highlights up
    curves.mapping.update()

    # ── Emission — warm orange glow ───────────────────────────────────────────
    emit = N("ShaderNodeEmission", (350, -80), "Jupiter_Emit")
    emit.inputs["Color"].default_value    = (1.0, 0.65, 0.25, 1.0)
    emit.inputs["Strength"].default_value = 0.06

    add_sh = N("ShaderNodeAddShader", (600, 100), "Jupiter_AddShader")

    # ── Wire everything up ────────────────────────────────────────────────────
    # source → HueSat → Curves → BSDF Base Color
    if source_socket:
        links.new(source_socket,             hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],      curves.inputs["Color"])
    links.new(curves.outputs["Color"],       bsdf.inputs["Base Color"])
    links.new(curves.outputs["Color"],       emit.inputs["Color"])

    # Reconnect BSDF + Emit → Add → Output
    # First disconnect BSDF → Output if directly connected
    for lnk in list(out.inputs["Surface"].links):
        links.remove(lnk)

    links.new(bsdf.outputs["BSDF"],      add_sh.inputs[0])
    links.new(emit.outputs["Emission"],  add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],  out.inputs["Surface"])

    print("   ✅ Color enhancement applied:")
    print("      Saturation ×1.55 | Warm hue shift | S-curve contrast | Soft orange glow")


# ─────────────────────────────────────────────────────────────────────────────

def fix_jupiter():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    old_obj = bpy.data.objects.get(OBJECT_NAME)
    if old_obj is None:
        old_obj = bpy.context.active_object
        if old_obj is None or old_obj.type != 'MESH':
            raise RuntimeError(
                f"❌ No object named '{OBJECT_NAME}' found. "
                "Select your Jupiter sphere and run again."
            )
        print(f"⚠  Using active object '{old_obj.name}' instead.")

    # Save materials before deleting
    mats = [slot.material for slot in old_obj.material_slots if slot.material]
    print(f"   Materials saved : {[m.name for m in mats]}")

    # ── Delete old object + mesh ──────────────────────────────────────────────
    bpy.ops.object.select_all(action='DESELECT')
    old_obj.select_set(True)
    bpy.context.view_layer.objects.active = old_obj
    old_mesh = old_obj.data
    bpy.ops.object.delete()
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    print("   Old Jupiter deleted ✓")

    # ── Create fresh high-res UV sphere ──────────────────────────────────────
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments   = SEGMENTS,
        ring_count = RINGS,
        radius     = JUPITER_RADIUS_BU,   # baked into vertices
        location   = (0.0, 0.0, 0.0),
        rotation   = (0.0, 0.0, 0.0),
    )

    new_obj      = bpy.context.active_object
    new_obj.name = OBJECT_NAME

    # Oblate squish
    new_obj.scale = (1.0, 1.0, OBLATE_FACTOR)

    # ── Smooth shading ────────────────────────────────────────────────────────
    bpy.ops.object.shade_smooth()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # ── Restore materials ─────────────────────────────────────────────────────
    new_obj.data.materials.clear()
    for mat in mats:
        new_obj.data.materials.append(mat)
    print("   Materials restored ✓")

    # ── Enhance colors ────────────────────────────────────────────────────────
    print("   Applying color enhancement...")
    enhance_jupiter_material(new_obj)

    # ── Rebake spin so Jupiter keeps rotating ─────────────────────────────────
    print("   Rebaking spin animation...")
    bake_rotation_z(new_obj, JUPITER_SPIN_FRAMES, JUPITER_TILT_DEG, ANIM_END)

    bpy.context.scene.frame_set(1)

    print()
    print(f"✅  Jupiter fixed!")
    print(f"   Mesh     : {SEGMENTS}×{RINGS} UV sphere (~{SEGMENTS * RINGS:,} faces)")
    print(f"   Radius   : {JUPITER_RADIUS_BU} BU | Scale Z: {OBLATE_FACTOR}")
    print(f"   Rotation : rebaked ({JUPITER_SPIN_FRAMES} frames/spin)")
    print(f"   Shading  : Smooth")


fix_jupiter()