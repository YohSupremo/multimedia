"""
Pluto Moon System — Charon, Styx, Nix, Kerberos, Hydra
=========================================================
Blender 4+/5  |  Based on Uranus moon reference pattern.

HOW TO USE:
  1. Run your Pluto script first (so Pluto exists in scene)
  2. Create 5 UV Sphere objects named exactly:
       Charon, Nix, Styx, Hydra, Kerberos
  3. Run this script in Scripting tab

Real facts:
  - Charon:   largest — half the size of Pluto itself, tidally locked.
               Grey surface, dark reddish polar cap (Mordor Macula).
               Orbit: 17,536 km | Period: 6.387 days (same as Pluto's rotation)
  - Styx:     tiny, elongated, faint. Innermost small moon.
               Orbit: 42,656 km | Period: 20.16 days
  - Nix:      small, potato-shaped, reddish tinge.
               Orbit: 48,694 km | Period: 24.85 days
  - Kerberos: faintest, double-lobed shape, dark surface.
               Orbit: 57,783 km | Period: 32.17 days
  - Hydra:    outermost small moon, elongated, brightest of small four.
               Orbit: 64,738 km | Period: 38.20 days

  All 5 moons orbit Pluto's equatorial plane.
  Pluto-Charon is a true binary system — both orbit a common barycenter
  outside Pluto's surface (~17,536 km from Pluto center).
  For simplicity this script treats Pluto as the fixed center.

RECORDING_MODE = True  → compressed orbits, all moons visible in one shot
RECORDING_MODE = False → realistic relative distances
"""

import bpy
import math
from mathutils import Matrix

# ── TOGGLE ────────────────────────────────────────────────────────────────────
RECORDING_MODE = True

# ── SETTINGS ──────────────────────────────────────────────────────────────────
PLUTO_RADIUS_BU  = 3.00          # must match your Pluto script
SEGMENTS         = 128
RINGS            = 64
ANIM_END         = 250

# ── Real size ratios (moon radius / Pluto radius) ─────────────────────────────
# Pluto radius: 1188.3 km
CHARON_SIZE_RATIO   =  606.0 / 1188.3   # ~0.510 — enormous relative to Pluto
STYX_SIZE_RATIO     =    8.0 / 1188.3   # ~0.007 — tiny
NIX_SIZE_RATIO      =   25.0 / 1188.3   # ~0.021
KERBEROS_SIZE_RATIO =   14.0 / 1188.3   # ~0.012
HYDRA_SIZE_RATIO    =   30.5 / 1188.3   # ~0.026

# ── Real orbit ratios (orbit radius / Pluto radius) ───────────────────────────
CHARON_ORBIT_RATIO   =  17536.0 / 1188.3   # ~14.76
STYX_ORBIT_RATIO     =  42656.0 / 1188.3   # ~35.90
NIX_ORBIT_RATIO      =  48694.0 / 1188.3   # ~40.98
KERBEROS_ORBIT_RATIO =  57783.0 / 1188.3   # ~48.63
HYDRA_ORBIT_RATIO    =  64738.0 / 1188.3   # ~54.48

# ── Orbital periods (days) ────────────────────────────────────────────────────
CHARON_PERIOD_DAYS   =  6.387
STYX_PERIOD_DAYS     = 20.162
NIX_PERIOD_DAYS      = 24.854
KERBEROS_PERIOD_DAYS = 32.168
HYDRA_PERIOD_DAYS    = 38.202

# ── Frame periods — Charon as base ────────────────────────────────────────────
BASE_FRAMES            = 60    # frames for Charon's orbit
CHARON_ORBIT_FRAMES    = BASE_FRAMES
STYX_ORBIT_FRAMES      = round(BASE_FRAMES * (STYX_PERIOD_DAYS     / CHARON_PERIOD_DAYS))
NIX_ORBIT_FRAMES       = round(BASE_FRAMES * (NIX_PERIOD_DAYS      / CHARON_PERIOD_DAYS))
KERBEROS_ORBIT_FRAMES  = round(BASE_FRAMES * (KERBEROS_PERIOD_DAYS / CHARON_PERIOD_DAYS))
HYDRA_ORBIT_FRAMES     = round(BASE_FRAMES * (HYDRA_PERIOD_DAYS    / CHARON_PERIOD_DAYS))

# ── Texture paths ─────────────────────────────────────────────────────────────
TEXTURE_BASE   = r"C:\Users\kelly\Downloads\Blender\textures"
CHARON_TEX     = TEXTURE_BASE + r"\charon_moon.jpg"
NIX_TEX        = TEXTURE_BASE + r"\nix_moon.jpg"
STYX_TEX       = TEXTURE_BASE + r"\styx_moon.jpg"
KERBEROS_TEX   = TEXTURE_BASE + r"\kerberos_moon.jpg"
HYDRA_TEX      = TEXTURE_BASE + r"\hydra_moon.jpg"

# ── Orbit & size calculation ──────────────────────────────────────────────────
if RECORDING_MODE:
    # Compressed but proportionally spaced so all are visible together
    # Charon is close, small moons spread outward
    CHARON_ORBIT_BU    = PLUTO_RADIUS_BU * 3.5    #  ~10.5 BU
    STYX_ORBIT_BU      = PLUTO_RADIUS_BU * 6.5    #  ~19.5 BU
    NIX_ORBIT_BU       = PLUTO_RADIUS_BU * 8.0    #  ~24.0 BU
    KERBEROS_ORBIT_BU  = PLUTO_RADIUS_BU * 10.0   #  ~30.0 BU
    HYDRA_ORBIT_BU     = PLUTO_RADIUS_BU * 12.5   #  ~37.5 BU

    # Charon: genuinely large — keep close to real ratio but boost slightly
    # Small moons: boosted a lot so they're visible
    CHARON_RADIUS_BU   = PLUTO_RADIUS_BU * 0.50   # ~1.50 BU — realistically large
    STYX_RADIUS_BU     = PLUTO_RADIUS_BU * 0.10   # ~0.30 BU — boosted to be visible
    NIX_RADIUS_BU      = PLUTO_RADIUS_BU * 0.13   # ~0.39 BU
    KERBEROS_RADIUS_BU = PLUTO_RADIUS_BU * 0.11   # ~0.33 BU
    HYDRA_RADIUS_BU    = PLUTO_RADIUS_BU * 0.14   # ~0.42 BU
else:
    MOON_SCALE_BOOST   = 400
    CHARON_ORBIT_BU    = PLUTO_RADIUS_BU * CHARON_ORBIT_RATIO
    STYX_ORBIT_BU      = PLUTO_RADIUS_BU * STYX_ORBIT_RATIO
    NIX_ORBIT_BU       = PLUTO_RADIUS_BU * NIX_ORBIT_RATIO
    KERBEROS_ORBIT_BU  = PLUTO_RADIUS_BU * KERBEROS_ORBIT_RATIO
    HYDRA_ORBIT_BU     = PLUTO_RADIUS_BU * HYDRA_ORBIT_RATIO

    CHARON_RADIUS_BU   = PLUTO_RADIUS_BU * CHARON_SIZE_RATIO              # realistic — no boost
    STYX_RADIUS_BU     = PLUTO_RADIUS_BU * STYX_SIZE_RATIO     * MOON_SCALE_BOOST
    NIX_RADIUS_BU      = PLUTO_RADIUS_BU * NIX_SIZE_RATIO      * MOON_SCALE_BOOST
    KERBEROS_RADIUS_BU = PLUTO_RADIUS_BU * KERBEROS_SIZE_RATIO * MOON_SCALE_BOOST
    HYDRA_RADIUS_BU    = PLUTO_RADIUS_BU * HYDRA_SIZE_RATIO    * MOON_SCALE_BOOST


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


def bake_rotation_z(obj, period_frames, tilt_deg, total_frames):
    obj.animation_data_clear()
    obj.rotation_mode = 'XYZ'
    ix = math.radians(tilt_deg)
    for frame in range(1, total_frames + 1):
        t       = (frame - 1) % period_frames
        angle_z = (t / period_frames) * math.tau
        obj.rotation_euler = (ix, 0, angle_z)
        obj.keyframe_insert("rotation_euler", frame=frame)
    _set_linear(obj.animation_data.action if obj.animation_data else None)


def fix_mesh(obj):
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


def make_orbit_ring(name, radius_bu, color, tilt_deg=0.0):
    ring_name = f"Orbit_Ring_{name}"
    remove_if_exists(ring_name)
    bpy.ops.curve.primitive_nurbs_circle_add(radius=radius_bu, location=(0, 0, 0))
    ring = bpy.context.active_object
    ring.name              = ring_name
    ring.hide_render       = True
    ring.rotation_euler[0] = math.radians(tilt_deg)
    ring.data.bevel_depth  = 0.04 if RECORDING_MODE else 0.02
    ring.data.use_fill_caps = False

    mat_name = f"OrbitMat_{name}"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em  = mat.node_tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value    = (*color, 1.0)
    em.inputs["Strength"].default_value = 1.2
    mat.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    ring.data.materials.clear()
    ring.data.materials.append(mat)


# ─────────────────────────────────────────────────────────────────────────────
# MOON MATERIALS
# ─────────────────────────────────────────────────────────────────────────────

def build_moon_material(obj, mat_name, tex_path,
                        roughness, bump_strength,
                        emit_color, emit_strength,
                        ramp_colors):
    """
    Luminance-remap material — same approach as Pluto:
      1. Load texture (or use noise fallback)
      2. Convert to greyscale
      3. Remap through a color ramp tuned to each moon's real appearance
      4. Bump from luminance for terrain depth
      5. Small emission so dark side stays faintly visible
    ramp_colors: list of (position, (r,g,b)) tuples, sorted 0.0 → 1.0
    """
    import os

    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    def N(t, loc):
        n = nodes.new(t); n.location = loc; return n

    out  = N("ShaderNodeOutputMaterial", (1000,   0))
    bsdf = N("ShaderNodeBsdfPrincipled", (580,    0))
    bsdf.inputs["Roughness"].default_value          = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    bsdf.inputs["Metallic"].default_value           = 0.0

    tex_c   = N("ShaderNodeTexCoord", (-800, 0))
    mapping = N("ShaderNodeMapping",  (-600, 0))

    tex_found = os.path.exists(tex_path)

    if tex_found:
        tex = N("ShaderNodeTexImage", (-370, 120))
        tex.image = bpy.data.images.load(tex_path, check_existing=True)
        print(f"      ✅ Texture: {tex_path}")
        color_source = tex.outputs["Color"]
        links.new(tex_c.outputs["UV"],       mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    else:
        print(f"      ⚠  No texture: {tex_path} — procedural fallback")
        noise = N("ShaderNodeTexNoise", (-370, 120))
        noise.inputs["Scale"].default_value      = 7.0
        noise.inputs["Detail"].default_value     = 14.0
        noise.inputs["Roughness"].default_value  = 0.65
        noise.inputs["Distortion"].default_value = 0.3
        color_source = noise.outputs["Color"]
        links.new(tex_c.outputs["UV"],       mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], noise.inputs["Vector"])

    # Greyscale → ramp → accurate moon color
    rgb_to_bw = N("ShaderNodeRGBToBW", (-100, 120))
    ramp      = N("ShaderNodeValToRGB", (100,  120))
    cr = ramp.color_ramp
    cr.interpolation = 'EASE'

    # Build ramp from provided stops
    # First set the two mandatory endpoints
    cr.elements[0].position = ramp_colors[0][0]
    cr.elements[0].color    = (*ramp_colors[0][1], 1.0)
    cr.elements[1].position = ramp_colors[-1][0]
    cr.elements[1].color    = (*ramp_colors[-1][1], 1.0)
    # Add middle stops
    for pos, col in ramp_colors[1:-1]:
        e = cr.elements.new(pos)
        e.color = (*col, 1.0)

    # Bump for terrain depth
    bump = N("ShaderNodeBump", (350, -150))
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.025

    # Faint emission — keeps moon visible on dark side
    emit   = N("ShaderNodeEmission",  (350, -300))
    add_sh = N("ShaderNodeAddShader", (780, -100))
    emit.inputs["Color"].default_value    = (*emit_color, 1.0)
    emit.inputs["Strength"].default_value = emit_strength

    links.new(color_source,              rgb_to_bw.inputs["Color"])
    links.new(rgb_to_bw.outputs["Val"],  ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"],     bsdf.inputs["Base Color"])
    links.new(rgb_to_bw.outputs["Val"],  bump.inputs["Height"])
    links.new(bump.outputs["Normal"],    bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"],      add_sh.inputs[0])
    links.new(emit.outputs["Emission"],  add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],  out.inputs["Surface"])


def setup_moon(moon, name, orbit_bu, moon_radius_bu, orbit_frames,
               orbit_ring_color, mat_name, tex_path,
               roughness, bump_strength, emit_color, emit_strength,
               ramp_colors):
    empty_name = f"Orbit_Empty_{name}"
    remove_if_exists(empty_name)

    print(f"\n   Setting up {name}...")

    hard_reset_object(moon)
    fix_mesh(moon)
    build_moon_material(moon, mat_name, tex_path,
                        roughness, bump_strength,
                        emit_color, emit_strength,
                        ramp_colors)

    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.0))
    empty = bpy.context.active_object
    empty.name           = empty_name
    empty.rotation_euler = (0.0, 0.0, 0.0)
    empty.location       = (0.0, 0.0, 0.0)

    bpy.ops.object.select_all(action='DESELECT')
    moon.parent                = empty
    moon.matrix_parent_inverse = Matrix.Identity(4)
    moon.location              = (orbit_bu, 0.0, 0.0)
    moon.rotation_euler        = (0.0, 0.0, 0.0)
    moon.scale                 = (moon_radius_bu, moon_radius_bu, moon_radius_bu)

    bake_rotation_z(empty, orbit_frames, 0.0, ANIM_END)

    make_orbit_ring(name, orbit_bu, orbit_ring_color)

    print(f"   ✅ {name} — orbit {orbit_bu:.1f} BU | radius {moon_radius_bu:.2f} BU | {orbit_frames} frames/orbit")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def setup():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = ANIM_END

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    charon   = bpy.data.objects.get("Charon")
    styx     = bpy.data.objects.get("Styx")
    nix      = bpy.data.objects.get("Nix")
    kerberos = bpy.data.objects.get("Kerberos")
    hydra    = bpy.data.objects.get("Hydra")

    missing = [n for n, o in [
        ("Charon", charon), ("Styx", styx), ("Nix", nix),
        ("Kerberos", kerberos), ("Hydra", hydra)
    ] if o is None]
    if missing:
        raise RuntimeError(
            f"❌  Missing objects: {missing}\n"
            f"    Create UV Sphere objects with those exact names and re-run."
        )

    # ── CHARON ────────────────────────────────────────────────────────────────
    # Half the size of Pluto — the largest moon relative to its parent in the
    # solar system. Grey, heavily cratered, dark reddish polar cap (Mordor Macula).
    # New Horizons revealed smooth plains (Vulcan Planum) and a deep canyon system.
    setup_moon(
        moon=charon, name="Charon",
        orbit_bu=CHARON_ORBIT_BU, moon_radius_bu=CHARON_RADIUS_BU,
        orbit_frames=CHARON_ORBIT_FRAMES,
        orbit_ring_color=(0.75, 0.72, 0.70),       # neutral grey ring
        mat_name="Charon_Mat", tex_path=CHARON_TEX,
        roughness=0.94,
        bump_strength=0.55,
        emit_color=(0.55, 0.52, 0.50),
        emit_strength=0.08,
        ramp_colors=[
            # Dark end: Mordor Macula polar cap — deep reddish-brown
            (0.00, (0.12, 0.05, 0.02)),
            # Dark craters and terrain
            (0.22, (0.28, 0.24, 0.22)),
            # Mid grey — general cratered surface
            (0.45, (0.48, 0.44, 0.42)),
            # Lighter grey — plains (Vulcan Planum)
            (0.68, (0.65, 0.62, 0.60)),
            # Bright: icy highlights and crater rims
            (1.00, (0.82, 0.80, 0.78)),
        ],
    )

    # ── STYX ──────────────────────────────────────────────────────────────────
    # Tiny, elongated, faint. Innermost of the small moons.
    # Very little is known — likely a captured KBO, dark grey surface.
    setup_moon(
        moon=styx, name="Styx",
        orbit_bu=STYX_ORBIT_BU, moon_radius_bu=STYX_RADIUS_BU,
        orbit_frames=STYX_ORBIT_FRAMES,
        orbit_ring_color=(0.55, 0.55, 0.58),       # dim grey-blue
        mat_name="Styx_Mat", tex_path=STYX_TEX,
        roughness=0.96,
        bump_strength=0.40,
        emit_color=(0.40, 0.40, 0.44),
        emit_strength=0.06,
        ramp_colors=[
            # Very dark — one of the faintest objects observed
            (0.00, (0.06, 0.06, 0.07)),
            (0.35, (0.22, 0.22, 0.24)),
            (0.65, (0.40, 0.40, 0.42)),
            (1.00, (0.58, 0.58, 0.60)),
        ],
    )

    # ── NIX ───────────────────────────────────────────────────────────────────
    # Potato-shaped, slightly reddish. Brighter than Styx/Kerberos.
    # New Horizons images show it is surprisingly red in places.
    setup_moon(
        moon=nix, name="Nix",
        orbit_bu=NIX_ORBIT_BU, moon_radius_bu=NIX_RADIUS_BU,
        orbit_frames=NIX_ORBIT_FRAMES,
        orbit_ring_color=(0.78, 0.65, 0.55),       # warm tan ring
        mat_name="Nix_Mat", tex_path=NIX_TEX,
        roughness=0.93,
        bump_strength=0.45,
        emit_color=(0.52, 0.44, 0.38),
        emit_strength=0.07,
        ramp_colors=[
            # Dark: reddish-brown patches
            (0.00, (0.14, 0.07, 0.03)),
            (0.28, (0.36, 0.22, 0.12)),
            # Mid: general tan-grey surface
            (0.55, (0.58, 0.48, 0.36)),
            # Bright: lighter icy patches
            (0.78, (0.76, 0.68, 0.56)),
            (1.00, (0.90, 0.84, 0.72)),
        ],
    )

    # ── KERBEROS ──────────────────────────────────────────────────────────────
    # Faintest of the four small moons. Double-lobed (two merged bodies).
    # Very dark surface — unexpectedly so given icy environment.
    setup_moon(
        moon=kerberos, name="Kerberos",
        orbit_bu=KERBEROS_ORBIT_BU, moon_radius_bu=KERBEROS_RADIUS_BU,
        orbit_frames=KERBEROS_ORBIT_FRAMES,
        orbit_ring_color=(0.48, 0.48, 0.52),       # dark grey ring
        mat_name="Kerberos_Mat", tex_path=KERBEROS_TEX,
        roughness=0.97,                            # extremely matte — very dark
        bump_strength=0.38,
        emit_color=(0.36, 0.36, 0.38),
        emit_strength=0.06,
        ramp_colors=[
            # Extremely dark — darkest of the small moons
            (0.00, (0.04, 0.04, 0.05)),
            (0.30, (0.15, 0.15, 0.17)),
            (0.60, (0.30, 0.30, 0.32)),
            (1.00, (0.48, 0.47, 0.50)),
        ],
    )

    # ── HYDRA ─────────────────────────────────────────────────────────────────
    # Outermost and brightest of the small moons. Elongated shape.
    # Surprisingly bright — water ice surface. New Horizons confirmed.
    # Noticeably brighter/whiter than the other small moons.
    setup_moon(
        moon=hydra, name="Hydra",
        orbit_bu=HYDRA_ORBIT_BU, moon_radius_bu=HYDRA_RADIUS_BU,
        orbit_frames=HYDRA_ORBIT_FRAMES,
        orbit_ring_color=(0.82, 0.86, 0.90),       # bright icy-blue ring
        mat_name="Hydra_Mat", tex_path=HYDRA_TEX,
        roughness=0.90,                            # slightly less rough — icy
        bump_strength=0.42,
        emit_color=(0.60, 0.64, 0.68),
        emit_strength=0.08,
        ramp_colors=[
            # Dark patches and craters
            (0.00, (0.12, 0.13, 0.15)),
            (0.25, (0.34, 0.36, 0.40)),
            # Mid: grey-white icy terrain
            (0.50, (0.58, 0.62, 0.66)),
            (0.75, (0.76, 0.80, 0.84)),
            # Bright: fresh water ice — noticeably brighter than other small moons
            (1.00, (0.92, 0.94, 0.96)),
        ],
    )

    scene.frame_set(1)

    print(f"\n🌑 Pluto moon system ready!")
    print(f"   Charon:   {CHARON_ORBIT_BU:.1f} BU  ({CHARON_ORBIT_FRAMES} frames/orbit)  ← true binary partner")
    print(f"   Styx:     {STYX_ORBIT_BU:.1f} BU  ({STYX_ORBIT_FRAMES} frames/orbit)  ← faintest")
    print(f"   Nix:      {NIX_ORBIT_BU:.1f} BU  ({NIX_ORBIT_FRAMES} frames/orbit)  ← reddish")
    print(f"   Kerberos: {KERBEROS_ORBIT_BU:.1f} BU  ({KERBEROS_ORBIT_FRAMES} frames/orbit)  ← darkest")
    print(f"   Hydra:    {HYDRA_ORBIT_BU:.1f} BU  ({HYDRA_ORBIT_FRAMES} frames/orbit)  ← brightest/outermost")
    print(f"   Mode: {'RECORDING (compressed orbits)' if RECORDING_MODE else 'REALISTIC'}")
    print(f"   📷 Camera tip: ~60–80 BU away, FOV ~55°")
    print(f"   Press Space to play ▶")
    print()
    print(f"   NOTE: Rename UV Spheres to exactly:")
    print(f"         Charon, Styx, Nix, Kerberos, Hydra")
    print(f"   Texture paths (optional — procedural fallback if missing):")
    for name, path in [
        ("Charon",   CHARON_TEX),
        ("Styx",     STYX_TEX),
        ("Nix",      NIX_TEX),
        ("Kerberos", KERBEROS_TEX),
        ("Hydra",    HYDRA_TEX),
    ]:
        print(f"         {name}: {path}")


setup()