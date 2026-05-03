"""
Neptune — Lighting Fix
=======================
Run this in Blender Scripting tab to update the scene lighting.
Keeps the deep-space feel but makes Neptune and Triton clearly visible.
"""

import bpy
import math


def remove_light(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
    ld = bpy.data.lights.get(name)
    if ld:
        bpy.data.lights.remove(ld)


def add_sun(name, energy, color, rx, ry, rz, shadow=True):
    remove_light(name)
    ld            = bpy.data.lights.new(name=name, type='SUN')
    ld.energy     = energy
    ld.color      = color
    ld.angle      = math.radians(2.0)
    ld.use_shadow = shadow
    obj = bpy.data.objects.new(name=name, object_data=ld)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    return obj


OLD_LIGHTS = [
    "Light_Key", "Light_Fill", "Light_Rim", "Light_Back",
    "Light_Fill_Right", "Light_Fill_Left", "Light_Fill_Top",
    "Light_Fill_Bottom", "Light_Fill_Back", "Light",
]

for n in OLD_LIGHTS:
    remove_light(n)

# ── KEY LIGHT — main Sun direction ────────────────────────────────────────────
# Bright blue-white from upper left — primary illumination
# Gives Neptune its signature lit crescent
add_sun("Light_Key",  6.0, (0.90, 0.95, 1.00), rx=-35, ry=0, rz=-55, shadow=True)

# ── FILL LIGHT — soft from opposite side ──────────────────────────────────────
# Lifts the dark side so it's not pure black — deep blue fill
# This is what was missing — your scene had almost no fill
add_sun("Light_Fill", 1.2, (0.30, 0.50, 0.90), rx=20,  ry=0, rz=130, shadow=False)

# ── RIM LIGHT — back edge highlight ──────────────────────────────────────────
# Thin blue-white rim on the far edge of Neptune — separates it from black space
add_sun("Light_Rim",  0.8, (0.70, 0.85, 1.00), rx=10,  ry=0, rz=80,  shadow=False)

# ── AMBIENT — very subtle global lift ────────────────────────────────────────
# Keeps Triton and the ring system from going completely black
add_sun("Light_Amb",  0.25, (0.20, 0.30, 0.60), rx=60, ry=0, rz=200, shadow=False)

# ── WORLD — pure black background with tiny star ambient ─────────────────────
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
bg.inputs["Color"].default_value    = (0.00, 0.00, 0.02, 1.0)
bg.inputs["Strength"].default_value = 0.08
links.new(bg.outputs["Background"], out.inputs["Surface"])

print("✅ Lighting updated!")
print("   Key:   6.0  — blue-white sun from upper-left")
print("   Fill:  1.2  — deep blue from opposite side")
print("   Rim:   0.8  — back edge highlight")
print("   Amb:   0.25 — global dark lift")
print()
print("   If still too dark: select Light_Key → increase Energy")
print("   If too bright:     select Light_Fill → decrease Energy")