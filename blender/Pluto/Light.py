"""
Pluto Scene — Lighting Setup
==============================
Blender 4+/5  |  Standalone lighting script.

HOW TO USE:
  Run this script any time to reset / tweak lighting.
  Can be run independently of the Pluto or moon scripts.
  Run order doesn't matter — lights are always rebuilt from scratch.

LIGHT OVERVIEW:
  Light_Key  — main sun, warm white, strong, casts shadows
  Light_Fill — soft blue-grey fill, dark-side visibility
  Light_Rim  — cool backlight, separates objects from black background
  Light_Amb  — very faint ambient wrap, stops moons going pure black

Tweak the energy values at the top to taste.
"""

import bpy
import math

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS — adjust these to taste
# ─────────────────────────────────────────────────────────────────────────────

KEY_ENERGY  = 12.0   # main sun — increase if scene too dark
FILL_ENERGY =  2.5   # dark-side fill — increase to see more detail in shadow
RIM_ENERGY  =  3.0   # backlight rim — increase to better separate from background
AMB_ENERGY  =  0.4   # ambient wrap — subtle, keeps moons from going fully black

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

OLD_LIGHTS = [
    "Light_Key", "Light_Fill", "Light_Rim", "Light_Amb",
    "Light_Fill_Right", "Light_Fill_Bottom", "Light_Fill_Top",
    "Light_Fill_Back",  "Light_Fill_Left",
]


def remove_light(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
    ld = bpy.data.lights.get(name)
    if ld:
        bpy.data.lights.remove(ld)


def add_sun(name, energy, color, rx, ry, rz, shadow=False):
    remove_light(name)
    ld            = bpy.data.lights.new(name=name, type='SUN')
    ld.energy     = energy
    ld.color      = color
    ld.angle      = math.radians(1.0)   # star-like from Pluto's distance
    ld.use_shadow = shadow
    obj = bpy.data.objects.new(name=name, object_data=ld)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    return obj


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


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def setup():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    print("💡 Setting up Pluto scene lighting...")

    # Remove all old lights
    for name in OLD_LIGHTS:
        remove_light(name)

    set_black_background()

    # ── Key light — the Sun ───────────────────────────────────────────────────
    # From Pluto, the Sun is just a very bright star — no disc visible.
    # Warm white. Main light source, casts shadows.
    # Direction: upper-left front (-30° elevation, -50° azimuth)
    add_sun("Light_Key",  KEY_ENERGY,
            (1.00, 0.98, 0.92),        # warm white
            rx=-30, ry=0, rz=-50,
            shadow=True)

    # ── Fill light — dark-side visibility ────────────────────────────────────
    # Soft cool blue-grey from opposite side.
    # Keeps the shadowed hemisphere readable — moons don't vanish into black.
    add_sun("Light_Fill", FILL_ENERGY,
            (0.60, 0.65, 0.80),        # cool blue-grey
            rx=20, ry=0, rz=140)

    # ── Rim light — edge separation ───────────────────────────────────────────
    # Cool backlight from upper right.
    # Separates Pluto and moons from the pure black background.
    add_sun("Light_Rim",  RIM_ENERGY,
            (0.80, 0.85, 0.90),        # cool white-blue
            rx=10, ry=0, rz=80)

    # ── Ambient wrap — prevents pure black shadows ────────────────────────────
    # Very faint, from below. Stops moons going completely invisible
    # on the far side from the key light.
    add_sun("Light_Amb",  AMB_ENERGY,
            (0.50, 0.52, 0.58),        # neutral cool
            rx=60, ry=0, rz=20)

    print()
    print("✅ Lighting ready!")
    print(f"   Light_Key  (sun):    {KEY_ENERGY}  — warm white, shadows on")
    print(f"   Light_Fill (fill):   {FILL_ENERGY}  — cool blue-grey, dark side")
    print(f"   Light_Rim  (rim):    {RIM_ENERGY}  — cool backlight, edge sep")
    print(f"   Light_Amb  (wrap):   {AMB_ENERGY}  — faint ambient, no pure black")
    print()
    print("   Tip: Adjust KEY_ENERGY / FILL_ENERGY at the top of the script")
    print("        and re-run to tweak brightness without touching other scripts.")


setup()