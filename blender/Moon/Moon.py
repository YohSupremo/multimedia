import bpy
import math
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
TEXTURE_BASE = r"C:\Users\kelly\Downloads\Blender\textures"
MOON_TEX     = TEXTURE_BASE + r"\moon.jpg"

# ── Helpers ────────────────────────────────────────────────────────────────────
def clean_scene():
    """Remove all default objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)

def make_moon(radius_km=1737.4, scale=1.0):
    r = (radius_km / 1000.0) * scale

    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=r,
        segments=256,
        ring_count=128,
        location=(0, 0, 0),
    )
    moon = bpy.context.active_object
    moon.name = "Moon"

    bpy.ops.object.shade_smooth()

    subsurf = moon.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels           = 2
    subsurf.render_levels    = 3
    subsurf.subdivision_type = 'CATMULL_CLARK'

    # Base rotation — poles aligned, equator around Z
    # Animation will spin Z on top of this
    moon.rotation_euler = (math.radians(90), 0.0, 0.0)
    return moon

def apply_moon_material(obj, tex_path):
    mat = bpy.data.materials.new(name="Moon_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out  = nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    bsdf.inputs["Roughness"].default_value          = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    bsdf.inputs["Metallic"].default_value           = 0.0
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.location      = (-100, 0)
    tex_node.interpolation = 'Cubic'
    tex_node.extension     = 'REPEAT'
    if os.path.exists(tex_path):
        img = bpy.data.images.load(tex_path)
        img.colorspace_settings.name = 'sRGB'
        tex_node.image = img
        print(f"[Moon] Texture loaded: {tex_path}")
    else:
        print(f"[Moon] WARNING - texture not found: {tex_path}")
    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

    coord   = nodes.new("ShaderNodeTexCoord")
    coord.location = (-500, 0)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-300, 0)
    mapping.inputs["Rotation"].default_value[2] = math.radians(180)
    links.new(coord.outputs["UV"],       mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

    obj.data.materials.append(mat)
    return mat

def setup_lighting():
    bpy.ops.object.light_add(type='SUN', location=(10, -10, 10))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.rotation_euler = (math.radians(45), 0, math.radians(-45))
    sun.data.energy    = 5.0
    sun.data.angle     = math.radians(0.53)
    return sun

def setup_camera(moon_radius_blender):
    bpy.ops.object.camera_add(location=(0, -moon_radius_blender * 5, 0))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = cam
    cam.data.lens     = 85
    cam.data.clip_end = 10_000
    return cam

def setup_render(output_path=r"C:\Users\kelly\Downloads\Blender\renders\moon_render.png"):
    scene = bpy.context.scene
    scene.render.engine                  = 'BLENDER_EEVEE'
    scene.render.resolution_x            = 2560
    scene.render.resolution_y            = 1440
    scene.render.resolution_percentage   = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath                = output_path
    scene.render.filter_size             = 1.5

    scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value    = (0, 0, 0, 1)
    bg.inputs["Strength"].default_value = 0.0

# ── Animation ──────────────────────────────────────────────────────────────────
def setup_rotation_animation(moon, total_frames=250, loops=1):
    """
    Keyframe a full 360 degree spin around the Moon's Z axis.

    total_frames : timeline length  (250 frames @ 24 fps = ~10 seconds)
    loops        : how many full rotations across total_frames
    """
    scene = bpy.context.scene
    scene.frame_start  = 1
    scene.frame_end    = total_frames
    scene.render.fps   = 24

    base_x = math.radians(90)   # keep the pole-alignment tilt

    # Frame 1 — start at 0 degrees Z
    scene.frame_set(1)
    moon.rotation_euler = (base_x, 0.0, math.radians(0))
    moon.keyframe_insert(data_path="rotation_euler", index=-1)

    # Last frame — end at 360 * loops degrees Z
    scene.frame_set(total_frames)
    moon.rotation_euler = (base_x, 0.0, math.radians(360 * loops))
    moon.keyframe_insert(data_path="rotation_euler", index=-1)

    # LINEAR interpolation = constant speed, no ease-in / ease-out
    # Blender 4+ uses layered actions: fcurves live inside
    # layers > strips > channelbags, not directly on the action.
    adt = moon.animation_data
    if adt and adt.action:
        action  = adt.action
        fcurves = []

        # Blender 4+ layered action structure
        if hasattr(action, 'layers') and action.layers:
            for layer in action.layers:
                for strip in layer.strips:
                    # channelbag() requires the active binding/slot
                    if hasattr(strip, 'channelbag'):
                        try:
                            cb = strip.channelbag(adt.action_binding)
                            fcurves.extend(cb.fcurves)
                        except Exception:
                            pass
                    elif hasattr(strip, 'channelbags'):
                        for cb in strip.channelbags:
                            fcurves.extend(cb.fcurves)

        # Fallback for legacy (pre-4.x) actions
        if not fcurves and hasattr(action, 'fcurves'):
            fcurves = list(action.fcurves)

        for fcurve in fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'LINEAR'

    scene.frame_set(1)
    print(f"[Moon] Animation: {total_frames} frames @ 24 fps, {loops} full rotation(s).")

def setup_render_animation(output_folder=r"C:\Users\kelly\Downloads\Blender\renders\\"):
    """
    Switch output to PNG image sequence.
    Blender writes:  renders/moon_0001.png, moon_0002.png, ...
    """
    scene = bpy.context.scene
    scene.render.filepath                   = output_folder + "moon_"
    scene.render.image_settings.file_format = 'PNG'

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    clean_scene()

    SCALE     = 1.0          # 1 Blender unit = 1 000 km
    moon      = make_moon(radius_km=1737.4, scale=SCALE)
    apply_moon_material(moon, MOON_TEX)

    moon_r_bu = (1737.4 / 1000.0) * SCALE
    setup_lighting()
    setup_camera(moon_r_bu)
    setup_render()

    # 250 frames = ~10 s at 24 fps, 1 full rotation
    # Increase loops=2 for two spins, or total_frames=500 for slower rotation
    setup_rotation_animation(moon, total_frames=250, loops=1)
    setup_render_animation()

    print("[Moon] Scene ready.")
    print("  Press F12        -> render current frame (still)")
    print("  Press Ctrl+F12   -> render full animation as PNG sequence")
    # Uncomment to render animation directly from script:
    # bpy.ops.render.render(animation=True)

main()