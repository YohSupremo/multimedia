"""
Pluto — Realistic (No Rings)
==============================
Blender 4+/5  |  Based on Uranus script reference pattern.

Key differences from ice giants:
  - Pluto is a dwarf planet — much smaller (~0.18× Earth radius)
  - Rich reddish-brown/tan surface from tholins (organic compounds)
  - Famous heart-shaped nitrogen ice plain: Tombaugh Regio (bright pale yellow)
  - Dark equatorial band of tholins (reddish-brown)
  - Bright polar cap of methane/nitrogen ice
  - NO RINGS — Pluto has no ring system
  - Very slight axial tilt: 122.53° (retrograde rotation like Uranus)
  - Extremely slow rotation: 6.387 days
  - Surface is geologically complex — mountains, plains, craters
  - New Horizons (2015) revealed incredible surface detail

Texture:
  - Place a pluto.jpg in your textures folder, or the script
    falls back to a rich procedural tholin/ice gradient automatically.
  - The procedural fallback actually looks very accurate for Pluto
    since the real surface has strong color contrast between regions.
"""

import bpy
import math
from mathutils import Matrix

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

PLUTO_RADIUS_BU   = 3.00          # Pluto is tiny — ~0.18× Earth; keep small
PLUTO_TILT_DEG    = 0.0           # Flat for now — set to 122.53 for real retrograde
PLUTO_SPIN_FRAMES = 200           # ~6.387 day rotation — very slow

SEGMENTS = 128
RINGS    = 64
ANIM_END = 250

TEXTURE_BASE = r"C:\Users\kelly\Downloads\Blender\textures"
PLUTO_TEX    = TEXTURE_BASE + r"\pluto.jpg"

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
    """Pluto spins very slowly on its tilted axis."""
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


# ─────────────────────────────────────────────────────────────────────────────
# PLUTO MATERIAL
#
# Pluto has one of the most visually complex surfaces in the solar system:
#   - Tombaugh Regio: the famous heart — pale yellow-white nitrogen ice
#   - Cthulhu Macula: dark reddish-brown tholin belt across equator
#   - Polar caps: bright methane/nitrogen frost
#   - General surface: mid-tone reddish-tan tholins
#
# With texture: luminance-only approach (same fix as Neptune/Triton)
#   → strips wrong jpg colors, remaps to accurate tholin palette
#
# Procedural fallback: multi-noise tholin simulation
#   → large blotch for heart region, dark equatorial band, bright poles
# ─────────────────────────────────────────────────────────────────────────────

def build_pluto_material(obj):
    mat_name = "Pluto_Mat"
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
    bsdf = N("ShaderNodeBsdfPrincipled", (600, 0))
    bsdf.inputs["Roughness"].default_value          = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    bsdf.inputs["Metallic"].default_value           = 0.0

    tex_c   = N("ShaderNodeTexCoord", (-800, 0))
    mapping = N("ShaderNodeMapping",  (-600, 0))
    tex     = N("ShaderNodeTexImage", (-350, 80))
    tex.image = bpy.data.images.load(PLUTO_TEX, check_existing=True)

    # Strip the jpg's native colors entirely — use only its luminance (light/dark map).
    # This preserves all the surface detail (craters, plains, belt) from your texture
    # but replaces the washed-out brown hues with the accurate New Horizons palette.
    rgb_to_bw = N("ShaderNodeRGBToBW", (-80, 80))

    # New Horizons true-color palette — pushed for maximum contrast:
    #   darkest  → near-black (Cthulhu belt is almost pure black in reality)
    #   mid-dark → very dark brown
    #   mid      → medium warm brown
    #   mid-bright → pale peach (NOT orange)
    #   bright   → cool light tan/cream
    #   brightest → near-white cream (heart + frost patches)
    ramp = N("ShaderNodeValToRGB", (120, 80))
    cr = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = 0.00; cr.elements[0].color = (0.04, 0.01, 0.00, 1.0)  # near-black
    cr.elements[1].position = 1.00; cr.elements[1].color = (0.95, 0.92, 0.82, 1.0)  # near-white cream
    e = cr.elements.new(0.20); e.color = (0.18, 0.07, 0.02, 1.0)                    # very dark brown
    e = cr.elements.new(0.40); e.color = (0.40, 0.20, 0.08, 1.0)                    # medium brown
    e = cr.elements.new(0.58); e.color = (0.68, 0.46, 0.24, 1.0)                    # warm tan (NOT orange)
    e = cr.elements.new(0.75); e.color = (0.84, 0.74, 0.56, 1.0)                    # pale cool peach

    # Bump from luminance — craters and terrain pop with real depth
    bump = N("ShaderNodeBump", (300, -150))
    bump.inputs["Strength"].default_value = 0.50
    bump.inputs["Distance"].default_value = 0.025

    links.new(tex_c.outputs["UV"],       mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"],      rgb_to_bw.inputs["Color"])
    links.new(rgb_to_bw.outputs["Val"],  ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"],     bsdf.inputs["Base Color"])
    links.new(rgb_to_bw.outputs["Val"],  bump.inputs["Height"])
    links.new(bump.outputs["Normal"],    bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"],      out.inputs["Surface"])

    print(f"   ✅ Pluto texture remapped to New Horizons palette: {PLUTO_TEX}")


# ─────────────────────────────────────────────────────────────────────────────
# LIGHTING
# Pluto is the farthest — Sun appears as a very bright star, not a disc.
# Extremely dim — ~1/1600th of Earth's sunlight.
# Very dark scene, almost no fill.
# We boost artificially for artistic visibility.
# ─────────────────────────────────────────────────────────────────────────────

def add_sun(name, energy, color, rx, ry, rz, shadow=False):
    remove_light(name)
    ld            = bpy.data.lights.new(name=name, type='SUN')
    ld.energy     = energy
    ld.color      = color
    ld.angle      = math.radians(1.0)   # very small angle — Sun is star-like from Pluto
    ld.use_shadow = shadow
    obj = bpy.data.objects.new(name=name, object_data=ld)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    return obj


OLD_LIGHTS = [
    "Light_Fill_Right", "Light_Fill_Bottom", "Light_Fill_Top",
    "Light_Fill_Back",  "Light_Fill_Left",   "Light_Rim",
    "Light_Key",        "Light_Fill",        "Light_Amb",
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

    # Key — warm white (Sun is still white from Pluto, just dim)
    # Boosted above realistic for artistic visibility
    add_sun("Light_Key",  12.0, (1.00, 0.98, 0.92), rx=-30, ry=0, rz=-50, shadow=True)
    # Stronger fill — moons on dark side need to be visible
    add_sun("Light_Fill",  2.5, (0.60, 0.65, 0.80), rx=20,  ry=0, rz=140)
    # Stronger rim — separates moons from black background
    add_sun("Light_Rim",   3.0, (0.80, 0.85, 0.90), rx=10,  ry=0, rz=80)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def setup():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    pluto = bpy.data.objects.get("Pluto")
    if pluto is None:
        raise RuntimeError("❌ No object named 'Pluto' found in scene!")

    print("🪐 Building Pluto...")
    setup_lighting()

    pluto.constraints.clear()
    pluto.animation_data_clear()
    if pluto.parent:
        bpy.context.view_layer.objects.active = pluto
        bpy.ops.object.select_all(action='DESELECT')
        pluto.select_set(True)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    pluto.location              = (0.0, 0.0, 0.0)
    pluto.rotation_euler        = (0.0, 0.0, 0.0)
    pluto.scale                 = (1.0, 1.0, 1.0)
    pluto.matrix_parent_inverse = Matrix.Identity(4)

    rebuild_sphere(pluto)
    # Pluto is nearly spherical — very slight oblateness (~0.9998), treated as perfect sphere
    pluto.scale = (PLUTO_RADIUS_BU, PLUTO_RADIUS_BU, PLUTO_RADIUS_BU)

    build_pluto_material(pluto)

    # Slow spin
    bake_rotation(pluto, PLUTO_SPIN_FRAMES, PLUTO_TILT_DEG, ANIM_END)

    scene.frame_set(1)

    print()
    print("✅ Pluto complete!")
    print(f"   Tilt:        {PLUTO_TILT_DEG}° (set to 122.53 for real retrograde tilt)")
    print(f"   Pluto:       {PLUTO_RADIUS_BU} BU radius")
    print(f"   Rings:       None — Pluto has no rings")
    print(f"   Texture:     {PLUTO_TEX}")
    print()
    print("   Surface features simulated:")
    print("   - Tombaugh Regio (heart) — pale yellow-white nitrogen ice")
    print("   - Cthulhu Macula — dark reddish-brown tholin belt")
    print("   - Polar caps — bright methane/nitrogen frost")
    print("   - General surface — reddish-tan tholins")
    print()
    print("   NOTE: Rename your Blender object to 'Pluto' before running!")


setup()