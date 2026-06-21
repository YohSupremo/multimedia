"""
Scene_And_Rendering.py
======================
Consolidated script that handles the entire Solar System environment, lighting, 
render engine configurations, label ray-visibility overrides, shader cleanups,
and the full 32-second camera cinematic flight tour.

Combines:
  - Viewport camera pointing at the Sun (Camera.py)
  - Procedural stars & swirling nebula world shader (Space Background.py)
  - Cinematic lighting setup & planet firefly fixes (Fireflies - fixed.py)
  - Universal label reflection & shadow ray-visibility disabler (Disable Label Reflections.py)
  - Particle system trail remover (Blue Spots - Remover.py)
  - Cinematic tour animation, safe arcs, Sun avoidance, and waypoint transitions (Cinematic Tour.py)
"""

import bpy
import math
from mathutils import Vector
import os
import random

# ─────────────────────────────────────────────────────────────────────────────
# GLOBALS & CONFIGURATION (matching original settings)
# ─────────────────────────────────────────────────────────────────────────────

# Camera Tour Settings
SUN_SAFE_RADIUS = 14.0      # hard XY floor from origin (Sun centre), in BU
WIDE_LOC    = Vector((0.0, -600.0, 190.0))
WIDE_TARGET = Vector((0.0, 0.0, 0.0))
INTRO_END   = 30
OUTRO_START = 931
TOUR_END    = 960

# Space Background Settings
BG_STAR_DENSITY  = 1000.0 # Tiny background stars
BG_STAR_BRIGHT   = 1.2    # Faint, natural background stars
FG_STAR_DENSITY  = 300.0  # Sparse foreground stars
FG_STAR_BRIGHT   = 5.0    # Crisp star points
NEBULA_SCALE     = 4.5    # Higher scale so gradient features are visible in viewport
NEBULA_DENSITY   = 0.50   # Roughness for natural interstellar gas detail
NEBULA_DISTORT   = 1.5    # Soft, organic gas distortion

# Phases Schedule for Camera Tour
PHASES = [
    dict(name="Sun",          obj="Sun",                mode="sun",
         cam_radius=60.0, cam_height=30.0, angle_start=0.5,  sweep=0.18, sf=31,  ef=75),
    dict(name="Mercury",      obj="Mercury",            mode="face",
         cam_radius=8.0,  cam_height=15.0,  angle_start=0.30, sweep=0.15, sf=91,  ef=135),
    dict(name="Venus",        obj="Venus",              mode="face",
         cam_radius=1.0,  cam_height=17.0,  angle_start=0.30, sweep=0.15, sf=151, ef=195),
    dict(name="Earth",        obj="Earth",              mode="face",
         cam_radius=12.0, cam_height=17.0,  angle_start=0.35, sweep=0.15, sf=211, ef=255),
    dict(name="ISS",          obj="SpaceStation_Root",  mode="iss",
         cam_radius=5.0,  cam_height=1.0,   angle_start=0.50, sweep=0.25, sf=271, ef=315),
    dict(name="Mars",         obj="Mars",               mode="face",
         cam_radius=12.0, cam_height=13.0,   angle_start=0.30, sweep=0.18, sf=331, ef=375),
    dict(name="AsteroidBelt", obj="AsteroidBelt_Root",  mode="belt",
         cam_radius=20.0, cam_height=28.0,  angle_start=0.25, sweep=0.06, sf=391, ef=435),
    dict(name="Jupiter",      obj="Jupiter",            mode="face",
         cam_radius=30.0, cam_height=35.0,  angle_start=0.30, sweep=0.18, sf=451, ef=495),
    dict(name="Saturn",       obj="Saturn",             mode="face",
         cam_radius=32.0, cam_height=50.0,  angle_start=0.25, sweep=0.18, sf=511, ef=555),
    dict(name="Uranus",       obj="Uranus",             mode="outer_face",
         cam_radius=30.0, cam_height=22.0,  angle_start=0.30, sweep=0.15, sf=571, ef=615),
    dict(name="Neptune",      obj="Neptune",            mode="face",
         cam_radius=25.0, cam_height=17.0,  angle_start=0.30, sweep=0.18, sf=631, ef=675),
    dict(name="Pluto",        obj="Pluto",              mode="face",
         cam_radius=10.0, cam_height=13.0,   angle_start=0.40, sweep=0.18, sf=691, ef=735),
    dict(name="KuiperBelt",   obj="KuiperBelt_Root",    mode="kuiper",
         cam_radius=30.0,  cam_height=150.0, angle_start=0.20, sweep=0.08, sf=751, ef=795),
    dict(name="Voyager1",     obj="Voyager_V1_Root",    mode="side_chase",
         cam_radius=3.0,  cam_height=13.0,  angle_start=1.1,  sweep=0.15, sf=811, ef=855),
    dict(name="Voyager2",     obj="Voyager_V2_Root",    mode="outer_voyager",
         cam_radius=3.0,   cam_height=13.0,  angle_start=0.40, sweep=0.20, sf=871, ef=915),
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. VIEWPORT CAMERA RESET (Camera.py)
# ─────────────────────────────────────────────────────────────────────────────

def setup_space_camera():
    """Fix the default camera settings, clip end, position, and tracking constraint."""
    print("\n🎥 Fixing viewport camera properties...")
    cam = bpy.context.scene.camera
    sun = bpy.data.objects.get("Sun")
    
    if not cam:
        print("  ⚠ No active camera found in the scene!")
        return
        
    cam.data.clip_end = 100000.0
    cam.location = (0, -250, 150)
    
    if sun:
        cam.constraints.clear()
        track = cam.constraints.new(type='TRACK_TO')
        track.target = sun
        track.track_axis = 'TRACK_NEGATIVE_Z'
        track.up_axis = 'UP_Y'
        print("  ✓ Camera tracking set to 'Sun' with 100K clipping distance.")
    else:
        print("  ℹ Sun object not found for default tracking constraint.")

# ─────────────────────────────────────────────────────────────────────────────
# 2. COSMIC WORLD BACKGROUND (Space Background.py)
# ─────────────────────────────────────────────────────────────────────────────

def setup_space_background():
    """Generates a realistic 360° deep-space background in the world shader."""
    print("\n🌌 Generating procedural cosmic stars & nebula background...")
    world = bpy.data.worlds.get("Space_World")
    if not world:
        world = bpy.data.worlds.new("Space_World")
    bpy.context.scene.world = world
    
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    
    def N(node_type, loc, name=None):
        node = nt.nodes.new(node_type)
        node.location = loc
        if name:
            node.name = name
            node.label = name
        return node
        
    out       = N("ShaderNodeOutputWorld",     (950, 0),    "Space_WorldOutput")
    add_sh1   = N("ShaderNodeAddShader",       (550, -50),  "Space_AddShader1")
    add_sh2   = N("ShaderNodeAddShader",       (750, 0),    "Space_AddShader2")
    tex_coord = N("ShaderNodeTexCoord",        (-900, 0),   "Space_TexCoord")
    
    # Nebula Layer
    neb_noise = N("ShaderNodeTexNoise",        (-550, 250), "Space_NebulaNoise")
    neb_noise.inputs["Scale"].default_value      = NEBULA_SCALE
    neb_noise.inputs["Detail"].default_value     = 5.0
    neb_noise.inputs["Roughness"].default_value  = NEBULA_DENSITY
    neb_noise.inputs["Distortion"].default_value = NEBULA_DISTORT
    
    neb_ramp = N("ShaderNodeValToRGB",         (-250, 250), "Space_NebulaRamp")
    cr_neb = neb_ramp.color_ramp
    cr_neb.interpolation = 'B_SPLINE'
    cr_neb.elements[0].position = 0.05
    cr_neb.elements[0].color    = (0.0, 0.0, 0.0, 1.0)
    cr_neb.elements[1].position = 0.35
    cr_neb.elements[1].color    = (0.015, 0.020, 0.055, 1.0)
    
    e1 = cr_neb.elements.new(0.60)
    e1.color = (0.040, 0.025, 0.090, 1.0)
    e2 = cr_neb.elements.new(0.78)
    e2.color = (0.001, 0.001, 0.002, 1.0)
    e3 = cr_neb.elements.new(0.92)
    e3.color = (0.008, 0.015, 0.035, 1.0)
    
    neb_bg = N("ShaderNodeBackground",         (150, 250),  "Space_NebulaBg")
    neb_bg.inputs["Strength"].default_value = 0.20
    
    # Background Stars Layer
    bg_star_noise = N("ShaderNodeTexNoise",    (-550, 0),   "Space_BgStarNoise")
    bg_star_noise.inputs["Scale"].default_value      = BG_STAR_DENSITY
    bg_star_noise.inputs["Detail"].default_value     = 8.0
    bg_star_noise.inputs["Roughness"].default_value  = 0.55
    
    bg_star_mask = N("ShaderNodeValToRGB",     (-250, 20),  "Space_BgStarMask")
    cr_bg = bg_star_mask.color_ramp
    cr_bg.interpolation = 'LINEAR'
    cr_bg.elements[0].position = 0.730
    cr_bg.elements[0].color    = (0.0, 0.0, 0.0, 1.0)
    cr_bg.elements[1].position = 0.745
    cr_bg.elements[1].color    = (1.0, 1.0, 1.0, 1.0)
    
    bg_star_color = N("ShaderNodeValToRGB",    (-250, -60), "Space_BgStarColor")
    cr_bg_col = bg_star_color.color_ramp
    cr_bg_col.interpolation = 'LINEAR'
    cr_bg_col.elements[0].position = 0.0; cr_bg_col.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    cr_bg_col.elements[1].position = 1.0; cr_bg_col.elements[1].color = (0.95, 0.98, 1.0, 1.0)
    cr_bg_col.elements.new(0.35).color = (1.0, 1.0, 1.0, 1.0)
    cr_bg_col.elements.new(0.70).color = (1.0, 0.98, 0.95, 1.0)
    cr_bg_col.elements.new(0.90).color = (1.0, 0.96, 0.92, 1.0)
    
    bg_star_mult = N("ShaderNodeMath",         (-50, 0),    "Space_BgStarMult")
    bg_star_mult.operation = 'MULTIPLY'
    bg_star_mult.inputs[1].default_value = BG_STAR_BRIGHT
    
    bg_star_bg = N("ShaderNodeBackground",     (150, 0),    "Space_BgStarBg")
    bg_star_bg.inputs["Strength"].default_value = BG_STAR_BRIGHT
    
    # Foreground Stars Layer
    fg_star_noise = N("ShaderNodeTexNoise",    (-550, -250), "Space_FgStarNoise")
    fg_star_noise.inputs["Scale"].default_value      = FG_STAR_DENSITY
    fg_star_noise.inputs["Detail"].default_value     = 6.0
    fg_star_noise.inputs["Roughness"].default_value  = 0.50
    
    fg_star_mask = N("ShaderNodeValToRGB",     (-250, -230), "Space_FgStarMask")
    cr_fg = fg_star_mask.color_ramp
    cr_fg.interpolation = 'LINEAR'
    cr_fg.elements[0].position = 0.770
    cr_fg.elements[0].color    = (0.0, 0.0, 0.0, 1.0)
    cr_fg.elements[1].position = 0.785
    cr_fg.elements[1].color    = (1.0, 1.0, 1.0, 1.0)
    
    fg_star_color = N("ShaderNodeValToRGB",    (-250, -310), "Space_FgStarColor")
    cr_fg_col = fg_star_color.color_ramp
    cr_fg_col.interpolation = 'LINEAR'
    cr_fg_col.elements[0].position = 0.0; cr_fg_col.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    cr_fg_col.elements[1].position = 1.0; cr_fg_col.elements[1].color = (0.95, 0.98, 1.0, 1.0)
    cr_fg_col.elements.new(0.35).color = (1.0, 1.0, 1.0, 1.0)
    cr_fg_col.elements.new(0.70).color = (1.0, 0.98, 0.95, 1.0)
    cr_fg_col.elements.new(0.90).color = (1.0, 0.96, 0.92, 1.0)
    
    fg_star_mult = N("ShaderNodeMath",         (-50, -250), "Space_FgStarMult")
    fg_star_mult.operation = 'MULTIPLY'
    fg_star_mult.inputs[1].default_value = FG_STAR_BRIGHT
    
    fg_star_bg = N("ShaderNodeBackground",     (150, -250), "Space_FgStarBg")
    fg_star_bg.inputs["Strength"].default_value = FG_STAR_BRIGHT
    
    # Links
    links = nt.links
    links.new(tex_coord.outputs["Normal"],  neb_noise.inputs["Vector"])
    links.new(tex_coord.outputs["Normal"],  bg_star_noise.inputs["Vector"])
    links.new(tex_coord.outputs["Normal"],  fg_star_noise.inputs["Vector"])
    
    links.new(neb_noise.outputs["Fac"],     neb_ramp.inputs["Fac"])
    links.new(neb_ramp.outputs["Color"],    neb_bg.inputs["Color"])
    
    links.new(bg_star_noise.outputs["Fac"], bg_star_mask.inputs["Fac"])
    links.new(bg_star_noise.outputs["Color"], bg_star_color.inputs["Fac"])
    links.new(bg_star_mask.outputs["Color"], bg_star_mult.inputs[0])
    links.new(bg_star_mult.outputs["Value"], bg_star_bg.inputs["Strength"])
    links.new(bg_star_color.outputs["Color"], bg_star_bg.inputs["Color"])
    
    links.new(fg_star_noise.outputs["Fac"], fg_star_mask.inputs["Fac"])
    links.new(fg_star_noise.outputs["Color"], fg_star_color.inputs["Fac"])
    links.new(fg_star_mask.outputs["Color"], fg_star_mult.inputs[0])
    links.new(fg_star_mult.outputs["Value"], fg_star_bg.inputs["Strength"])
    links.new(fg_star_color.outputs["Color"], fg_star_bg.inputs["Color"])
    
    links.new(neb_bg.outputs["Background"],     add_sh1.inputs[0])
    links.new(bg_star_bg.outputs["Background"],  add_sh1.inputs[1])
    links.new(add_sh1.outputs["Shader"],         add_sh2.inputs[0])
    links.new(fg_star_bg.outputs["Background"],  add_sh2.inputs[1])
    links.new(add_sh2.outputs["Shader"],         out.inputs["Surface"])
    
    bpy.context.scene.render.film_transparent = False
    
    # Active viewport viewport options
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'RENDERED'
                    space.shading.use_scene_world = True
                    print(f"  ✓ Set View3D viewport to RENDERED shading with scene world.")
    print("  ✓ Procedural 360° deep-space background world shader complete.")

# ─────────────────────────────────────────────────────────────────────────────
# 3. LIGHTING & SPECS/FIREFLY REMOVERS (Fireflies - fixed.py)
# ─────────────────────────────────────────────────────────────────────────────

def apply_firefly_fixes():
    """Sets up balanced lights, caps EEVEE bloom, zero speculars on rings, restores colors."""
    print("\n💡 Applying lighting fixes and specular/firefly overrides...")
    
    # 1. Lights Cleanup and Rebuilding
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
            
    def make_light(name, ltype, energy, color, location, size=10.0):
        ld = bpy.data.lights.new(name, ltype)
        ld.energy              = energy
        ld.color               = color
        ld.shadow_soft_size    = size
        ld.use_custom_distance = False
        lo = bpy.data.objects.new(name, ld)
        bpy.context.collection.objects.link(lo)
        lo.location = location
        return lo

    make_light("Sun_Core_Light", 'POINT', energy=800_000, color=(1.0, 0.96, 0.88), location=(0, 0, 0), size=50.0)
    make_light("Outer_Fill_Light", 'POINT', energy=150_000, color=(0.85, 0.90, 1.00), location=(80, 0, 20), size=60.0)
    
    # Disable shadow casting from the Sun visual components
    for name in ("Sun", "The Sun", "Star_Surface", "Solar_Fire",
                 "Corona", "Prominence_01", "Prominence_02", "Prominence_03", "Flare"):
        o = bpy.data.objects.get(name)
        if o:
            o.visible_shadow = False

    # Ambient World
    scene = bpy.context.scene
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.02, 0.03, 0.06, 1.0)
        bg.inputs[1].default_value = 0.02

    # EEVEE Denoising & Bloom adjustments
    eevee = scene.eevee
    if hasattr(eevee, 'use_bloom'):
        eevee.use_bloom       = True
        eevee.bloom_threshold = 3.0
        eevee.bloom_intensity = 0.15
        eevee.bloom_radius    = 5.0
    if hasattr(eevee, 'use_gtao'):
        eevee.use_gtao = False

    # Saturn & All Rings Dot & Specular fixes
    for mat in bpy.data.materials:
        if "RingMat" not in mat.name or not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs["Roughness"].default_value          = 1.0
                node.inputs["Specular IOR Level"].default_value = 0.0
                node.inputs["Metallic"].default_value           = 0.0
            if node.type == 'EMISSION':
                node.inputs["Strength"].default_value = 0.0

    # Uranus: pale cyan-teal, visible, transparency fixed
    uranus = bpy.data.objects.get("Uranus")
    if uranus:
        uranus.hide_viewport = False
        uranus.hide_render   = False
        
        image = None
        if uranus.data.materials:
            for n in (uranus.data.materials[0].node_tree.nodes
                      if uranus.data.materials[0] and uranus.data.materials[0].use_nodes
                      else []):
                if n.type == 'TEX_IMAGE' and n.image:
                    image = n.image; break
                    
        mat = (uranus.data.materials[0]
               if uranus.data.materials else bpy.data.materials.new("Uranus_Mat"))
        if not uranus.data.materials:
            uranus.data.materials.append(mat)
            
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        out  = nodes.new("ShaderNodeOutputMaterial")
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        crv  = nodes.new("ShaderNodeRGBCurve")
        ramp = nodes.new("ShaderNodeValToRGB")
        bw   = nodes.new("ShaderNodeRGBToBW")
        tex  = nodes.new("ShaderNodeTexImage")
        coord= nodes.new("ShaderNodeTexCoord")
        
        if image: tex.image = image
        bsdf.inputs["Roughness"].default_value          = 0.82
        bsdf.inputs["Specular IOR Level"].default_value = 0.04
        bsdf.inputs["Metallic"].default_value           = 0.0
        
        cr = ramp.color_ramp
        cr.interpolation = 'EASE'
        cr.elements[0].position = 0.00; cr.elements[0].color = (0.25, 0.72, 0.75, 1.0)
        cr.elements[1].position = 1.00; cr.elements[1].color = (0.62, 0.93, 0.93, 1.0)
        mid = cr.elements.new(0.50);    mid.color            = (0.42, 0.84, 0.86, 1.0)
        
        c = crv.mapping.curves[3]
        c.points[0].location = (0.0, 0.0)
        c.points[1].location = (1.0, 1.0)
        c.points.new(0.3, 0.22); c.points.new(0.7, 0.82)
        crv.mapping.update()
        
        links.new(coord.outputs["UV"],   tex.inputs["Vector"])
        links.new(tex.outputs["Color"],  bw.inputs["Color"])
        links.new(bw.outputs["Val"],     ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], crv.inputs["Color"])
        links.new(crv.outputs["Color"],  bsdf.inputs["Base Color"])
        links.new(bsdf.outputs["BSDF"],  out.inputs["Surface"])
        
    for mat in bpy.data.materials:
        if "URing" not in mat.name or not mat.use_nodes:
            continue
        try:    mat.surface_render_method  = 'BLENDED'
        except: pass
        try:
            mat.blend_method           = 'BLEND'
            mat.shadow_method          = 'NONE'
            mat.show_transparent_back  = False
            mat.use_backface_culling   = False
        except: pass
        for node in list(mat.node_tree.nodes):
            if node.type == 'HOLDOUT':
                mat.node_tree.nodes.remove(node)
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs["Roughness"].default_value          = 1.0
                node.inputs["Specular IOR Level"].default_value = 0.0
                node.inputs["Alpha"].default_value = min(node.inputs["Alpha"].default_value, 0.15)

    # Neptune: Deep Cobalt Blue color curves
    neptune = bpy.data.objects.get("Neptune")
    if neptune:
        neptune.hide_viewport = False
        neptune.hide_render   = False
        
        image = None
        if neptune.data.materials:
            for n in (neptune.data.materials[0].node_tree.nodes
                      if neptune.data.materials[0] and neptune.data.materials[0].use_nodes
                      else []):
                if n.type == 'TEX_IMAGE' and n.image:
                    image = n.image; break
                    
        mat = (neptune.data.materials[0]
               if neptune.data.materials else bpy.data.materials.new("Neptune_Mat"))
        if not neptune.data.materials:
            neptune.data.materials.append(mat)
            
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        out  = nodes.new("ShaderNodeOutputMaterial")
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        crv  = nodes.new("ShaderNodeRGBCurve")
        ramp = nodes.new("ShaderNodeValToRGB")
        bw   = nodes.new("ShaderNodeRGBToBW")
        tex  = nodes.new("ShaderNodeTexImage")
        coord= nodes.new("ShaderNodeTexCoord")
        
        if image: tex.image = image
        bsdf.inputs["Roughness"].default_value          = 0.80
        bsdf.inputs["Specular IOR Level"].default_value = 0.04
        bsdf.inputs["Metallic"].default_value           = 0.0
        
        cr = ramp.color_ramp
        cr.interpolation = 'EASE'
        cr.elements[0].position = 0.00; cr.elements[0].color = (0.01, 0.06, 0.40, 1.0)
        cr.elements[1].position = 1.00; cr.elements[1].color = (0.05, 0.32, 0.88, 1.0)
        mid = cr.elements.new(0.50);    mid.color            = (0.02, 0.17, 0.62, 1.0)
        
        c = crv.mapping.curves[3]
        c.points[0].location = (0.0, 0.0)
        c.points[1].location = (1.0, 1.0)
        c.points.new(0.3, 0.22); c.points.new(0.7, 0.82)
        crv.mapping.update()
        
        links.new(coord.outputs["UV"],   tex.inputs["Vector"])
        links.new(tex.outputs["Color"],  bw.inputs["Color"])
        links.new(bw.outputs["Val"],     ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], crv.inputs["Color"])
        links.new(crv.outputs["Color"],  bsdf.inputs["Base Color"])
        links.new(bsdf.outputs["BSDF"],  out.inputs["Surface"])

    # All planet material specular caps
    planet_mats = {
        "Saturn_Mat":        (0.85, 0.04),
        "Jupiter_Cinematic": (0.82, 0.03),
        "Mars_Mat":          (0.90, 0.02),
        "Mercury_Mat":       (0.92, 0.01),
        "Moon_Mat":          (0.90, 0.01),
        "Pluto_Mat":         (0.90, 0.01),
        "Venus_Mat":         (0.80, 0.05),
        "Earth_Mat":         (0.75, 0.08),
    }
    for mat_name, (rough, spec) in planet_mats.items():
        m = bpy.data.materials.get(mat_name)
        if m and m.use_nodes:
            for node in m.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    node.inputs["Roughness"].default_value          = rough
                    node.inputs["Specular IOR Level"].default_value = spec
                    
    # Cap Earth and Jupiter emission spikes
    emit_caps = {"Earth_Emit": 0.25, "Jupiter_Emit": 0.03}
    for mat in bpy.data.materials:
        if not mat.use_nodes: continue
        for node in mat.node_tree.nodes:
            if node.type == 'EMISSION':
                for key, cap in emit_caps.items():
                    if key in node.name or key in mat.name:
                        if node.inputs["Strength"].default_value > cap:
                            node.inputs["Strength"].default_value = cap

    # Cap Orbit trails emission
    for mat in bpy.data.materials:
        if not mat.use_nodes: continue
        if not any(kw in mat.name for kw in ["Trail_", "OrbitMat", "NANTA"]):
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'EMISSION':
                old = node.inputs["Strength"].default_value
                if old > 0.3:
                    node.inputs["Strength"].default_value = 0.3
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs["Specular IOR Level"].default_value = 0.0
                
    print("  ✓ Ambient lighting, specular and EEVEE bloom updates completed.")

# ─────────────────────────────────────────────────────────────────────────────
# 4. UNIVERSAL LABEL RAY VISIBILITY OVERRIDES (Disable Label Reflections.py)
# ─────────────────────────────────────────────────────────────────────────────

def disable_label_reflections():
    """Universal disabler for glossy, diffuse, shadow, transmission, and volume scatter for labels."""
    print("\n🚫 Overriding ray visibility constraints for text labels...")
    count = 0
    for obj in bpy.data.objects:
        is_label = (
            obj.type == 'FONT' or 
            obj.name.startswith("Text_") or 
            "label" in obj.name.lower() or 
            obj.name == "SpaceStation_Pointer"
        )
        if is_label:
            obj.visible_glossy = False
            obj.visible_diffuse = False
            obj.visible_shadow = False
            obj.visible_transmission = False
            obj.visible_volume_scatter = False
            count += 1
    print(f"  ✓ Universal label reflection disabled for {count} text objects.")

# ─────────────────────────────────────────────────────────────────────────────
# 5. PARTICLE SYSTEM TRAIL CLEANER (Blue Spots - Remover.py)
# ─────────────────────────────────────────────────────────────────────────────

def remove_redundant_trails():
    """Removes redundant particle system modifiers from planets and the moon."""
    print("\n☄️ Removing redundant particle modifier trails...")
    planets = ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Moon"]
    removed_count = 0
    for name in planets:
        obj = bpy.data.objects.get(name)
        if not obj:
            continue
        mods_to_remove = [mod for mod in obj.modifiers if mod.type == 'PARTICLE_SYSTEM' and "Trail" in mod.name]
        for mod in mods_to_remove:
            obj.modifiers.remove(mod)
            removed_count += 1
    print(f"  ✓ Successfully removed {removed_count} redundant particle system trails.")

# ─────────────────────────────────────────────────────────────────────────────
# 6. CAMERA CINEMATIC TOUR TIMELINE (Cinematic Tour.py)
# ─────────────────────────────────────────────────────────────────────────────

def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def lerp_v(a, b, t):
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t

def push_outside_sun(pos, min_r):
    xy = math.sqrt(pos.x ** 2 + pos.y ** 2)
    if xy <= 1e-6:
        return Vector((min_r, 0.0, pos.z))
    if xy < min_r:
        s = min_r / xy
        return Vector((pos.x * s, pos.y * s, pos.z))
    return Vector(pos)

def safe_arc(a, b, n, min_r, min_z):
    out = []
    for i in range(n + 1):
        t   = i / max(1, n)
        raw = lerp_v(a, b, ease(t))
        raw = Vector((raw.x, raw.y, max(raw.z, min_z)))
        raw = push_outside_sun(raw, min_r)
        out.append(raw)
    return out

def get_world_pos(obj_name, frame):
    obj = bpy.data.objects.get(obj_name)
    if obj is None:
        return Vector((0.0, 0.0, 0.0))
    bpy.context.scene.frame_set(frame)
    return obj.matrix_world.to_translation().copy()

def unit_xy(v):
    l = math.sqrt(v.x**2 + v.y**2)
    if l < 1e-6:
        return Vector((1.0, 0.0, 0.0))
    return Vector((v.x / l, v.y / l, 0.0))

def cam_for_phase(ph, frame):
    R    = ph["cam_radius"]
    dZ   = ph["cam_height"]
    a0   = ph["angle_start"]
    sw   = ph["sweep"]
    sf   = ph["sf"]
    ef   = ph["ef"]
    mode = ph["mode"]

    t      = (frame - sf) / max(1, ef - sf)
    angle  = a0 + t * sw
    target = get_world_pos(ph["obj"], frame)

    if mode == "sun":
        cam = target + Vector((R * math.cos(angle), R * math.sin(angle), dZ))
        return target, cam

    if mode == "belt":
        LABEL_POS = Vector((-33.0, 37.0, 0.0))
        label_r   = math.sqrt(LABEL_POS.x**2 + LABEL_POS.y**2)
        label_dir = Vector((LABEL_POS.x / label_r, LABEL_POS.y / label_r, 0.0))
        perp  = Vector((-label_dir.y, label_dir.x, 0.0))
        drift = perp * (R * 0.15 * math.sin(angle))
        cam = LABEL_POS - label_dir * R + drift + Vector((0.0, 0.0, dZ))
        return LABEL_POS, cam

    if mode == "kuiper":
        LABEL_POS = Vector((-113.0, 140.0, 0.0))
        label_r   = 200.0
        label_dir = Vector((LABEL_POS.x / label_r, LABEL_POS.y / label_r, 0.0))
        perp  = Vector((-label_dir.y, label_dir.x, 0.0))
        drift = perp * (R * 0.15 * math.sin(angle))
        cam = LABEL_POS - label_dir * R + drift + Vector((0.0, 0.0, dZ))
        return LABEL_POS, cam

    if mode == "outer_face":
        sun_to_planet = unit_xy(target)
        perp = Vector((-sun_to_planet.y, sun_to_planet.x, 0.0))
        outward = sun_to_planet * (R * 0.5)
        side    = perp        * (R * 0.85)
        sweep   = perp        * (R * 0.12 * math.sin(angle))
        cam = target + outward + side + sweep + Vector((0.0, 0.0, dZ))
        return target, cam

    if mode == "side_chase":
        sun_to_planet = unit_xy(target)
        perp = Vector((-sun_to_planet.y, sun_to_planet.x, 0.0))
        alpha = angle
        cam_dir = perp * math.cos(alpha) - sun_to_planet * math.sin(alpha)
        cam_base = target + cam_dir * R
        cam = cam_base + Vector((0.0, 0.0, dZ))
        return target, cam

    if mode == "outer_voyager":
        sun_to_planet = unit_xy(target)
        cam_base = target + sun_to_planet * R
        perp = Vector((-sun_to_planet.y, sun_to_planet.x, 0.0))
        lateral = perp * (R * 0.25 * math.sin(angle))
        cam = cam_base + lateral + Vector((0.0, 0.0, dZ))
        return target, cam

    sun_to_planet = unit_xy(target)
    cam_base = target - sun_to_planet * R
    perp = Vector((-sun_to_planet.y, sun_to_planet.x, 0.0))
    lateral = perp * (R * 0.25 * math.sin(angle))
    cam = cam_base + lateral + Vector((0.0, 0.0, dZ))
    return target, cam

def smooth_fcurves(obj):
    if not (obj.animation_data and obj.animation_data.action):
        return
    action = obj.animation_data.action
    def _s(fcs):
        for fc in fcs:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
    if hasattr(action, "fcurves"):
        _s(action.fcurves)
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in getattr(layer, "strips", []):
                cbs = getattr(strip, "channelbags", [])
                if hasattr(cbs, "values"):
                    cbs = cbs.values()
                for cb in cbs:
                    if hasattr(cb, "fcurves"):
                        _s(cb.fcurves)

def setup_cinematic_tour():
    """Builds camera targets, keyframes, transitions, and Bezier interpolations for full tour."""
    print("\n🎬 Setting up camera cinematic flight tour schedule...")
    scene = bpy.context.scene

    camera = bpy.data.objects.get("Camera")
    if not camera:
        camera = scene.camera
    if not camera:
        cd     = bpy.data.cameras.new("Camera")
        camera = bpy.data.objects.new("Camera", cd)
        bpy.context.collection.objects.link(camera)
    scene.camera           = camera
    camera.data.clip_start = 0.1
    camera.data.clip_end   = 5000.0

    tgt = bpy.data.objects.get("Camera_Target")
    if not tgt:
        tgt = bpy.data.objects.new("Camera_Target", None)
        tgt.empty_display_type = 'PLAIN_AXES'
        tgt.empty_display_size = 1.0
        bpy.context.collection.objects.link(tgt)

    scene.frame_start   = 1
    scene.frame_end     = TOUR_END + 60
    scene.frame_current = 1

    for obj in (camera, tgt):
        if obj.animation_data:
            obj.animation_data_clear()
    camera.constraints.clear()

    track            = camera.constraints.new('TRACK_TO')
    track.target     = tgt
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis    = 'UP_Y'

    camera.animation_data_create()
    tgt.animation_data_create()

    keys = []   # (frame, target_vec, cam_vec)

    def kf(f, t_pos, c_pos):
        safe_c = push_outside_sun(Vector(c_pos), SUN_SAFE_RADIUS)
        keys.append((int(f), Vector(t_pos), safe_c))

    # INTRO: wide view to Sun orbit
    sun_ph = PHASES[0]
    t0_tgt, t0_cam = cam_for_phase(sun_ph, sun_ph["sf"])
    arc_c = safe_arc(WIDE_LOC,    t0_cam, INTRO_END, SUN_SAFE_RADIUS, t0_cam.z * 0.6)
    arc_t = safe_arc(WIDE_TARGET, t0_tgt, INTRO_END, 0.0, -9999)
    for i, f in enumerate(range(1, INTRO_END + 1)):
        kf(f, arc_t[i], arc_c[i])

    # Phase Dwells and Transitions
    for idx, ph in enumerate(PHASES):
        sf = ph["sf"]
        ef = ph["ef"]

        for f in range(sf, ef + 1):
            t_pos, c_pos = cam_for_phase(ph, f)
            kf(f, t_pos, c_pos)

        if idx < len(PHASES) - 1:
            nph      = PHASES[idx + 1]
            trans_sf = ef + 1
            trans_ef = nph["sf"] - 1
            n        = trans_ef - trans_sf + 1
            if n < 1:
                continue

            mid_f = (trans_sf + trans_ef) // 2
            tA, cA = cam_for_phase(ph,  mid_f)
            tB, cB = cam_for_phase(nph, mid_f)

            min_z = max(cA.z, cB.z) * 0.7
            c_arc = safe_arc(cA, cB, n, SUN_SAFE_RADIUS, min_z)
            t_arc = safe_arc(tA, tB, n, 0.0, -9999)

            for i, f in enumerate(range(trans_sf, trans_ef + 1)):
                kf(f, t_arc[i], c_arc[i])

    # OUTRO: Pluto to wide view
    last_ph = PHASES[-1]
    lZ_tgt, lZ_cam = cam_for_phase(last_ph, last_ph["ef"])
    n_out  = TOUR_END - OUTRO_START + 1
    c_out  = safe_arc(lZ_cam, WIDE_LOC,    n_out, SUN_SAFE_RADIUS, WIDE_LOC.z * 0.5)
    t_out  = safe_arc(lZ_tgt, WIDE_TARGET, n_out, 0.0, -9999)
    for i, f in enumerate(range(OUTRO_START, TOUR_END + 1)):
        kf(f, t_out[i], c_out[i])

    kf(TOUR_END + 1,  WIDE_TARGET, WIDE_LOC)
    kf(TOUR_END + 60, WIDE_TARGET, WIDE_LOC)

    print(f"  ✓ Generated {len(keys)} keyframe coordinates.")
    for (f, t_pos, c_pos) in keys:
        tgt.location    = t_pos
        camera.location = c_pos
        tgt.keyframe_insert(data_path="location", frame=f)
        camera.keyframe_insert(data_path="location", frame=f)

    for obj in (camera, tgt):
        smooth_fcurves(obj)

    print("  ✓ Cinematic camera flight tour keys baked successfully.")

# ─────────────────────────────────────────────────────────────────────────────
# RUN ALL
# ─────────────────────────────────────────────────────────────────────────────

def run_all():
    print("\n" + "=" * 65)
    print("🎬 SCENE AND RENDERING PIPELINE SETUP")
    print("=" * 65)
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
        
    setup_space_camera()
    setup_space_background()
    # apply_firefly_fixes() -- Removed to preserve custom viewport lighting and planet materials
    disable_label_reflections()
    remove_redundant_trails()
    setup_cinematic_tour()
    
    print("\n" + "=" * 65)
    print("✨ Scene and Rendering Consolidation Setup Complete!")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    run_all()
