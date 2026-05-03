"""
LIGHTING FIX — Black space background + Sun-based fill lights
=============================================================
- Pure black background (real outer space)
- Uses SUN lights for all fill directions (no blue tint bleed)
- Covers all angles so no dark belly/sides on any moon
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


def add_sun(name, energy, color, rx, ry, rz):
    """Sun light — directional, infinite, no falloff. Perfect for space."""
    remove_light(name)
    ld = bpy.data.lights.new(name=name, type='SUN')
    ld.energy     = energy
    ld.color      = color
    ld.angle      = math.radians(3.0)
    ld.use_shadow = False          # fill suns cast no shadow — avoids ugly double shadows
    obj = bpy.data.objects.new(name=name, object_data=ld)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    return obj


def add_sun_shadow(name, energy, color, rx, ry, rz):
    """Key sun — only this one casts shadows for realism."""
    remove_light(name)
    ld = bpy.data.lights.new(name=name, type='SUN')
    ld.energy     = energy
    ld.color      = color
    ld.angle      = math.radians(2.0)
    ld.use_shadow = True
    obj = bpy.data.objects.new(name=name, object_data=ld)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    return obj


def set_black_background():
    """Pure black — true outer space, zero ambient."""
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

    # ── BLACK SPACE BACKGROUND ────────────────────────────────────────────────
    set_black_background()

    # ── 1. KEY SUN — main light, upper left front, casts shadows ─────────────
    # This is the "real sun" equivalent — bright, warm, sharp
    add_sun_shadow(
        name="Light_Key",
        energy=5.0,
        color=(1.00, 0.97, 0.90),   # warm white
        rx=-35, ry=0, rz=-45,
    )

    # ── 2. FILL SUN — right side, opposite key ────────────────────────────────
    # Lifts the shadow side — keep energy low so it doesn't flatten the look
    add_sun(
        name="Light_Fill_Right",
        energy=1.5,
        color=(0.85, 0.90, 1.00),   # slightly cool to contrast warm key
        rx=-10, ry=0, rz=120,
    )

    # ── 3. FILL SUN BOTTOM — points upward, kills the dark belly ─────────────
    # Rotation: pitch +90 = sun rays go straight UP into scene from below
    add_sun(
        name="Light_Fill_Bottom",
        energy=1.2,
        color=(0.80, 0.85, 1.00),   # neutral cool
        rx=90, ry=0, rz=0,          # pointing straight up
    )

    # ── 4. FILL SUN BACK — subtle back fill, stops rear going pure black ──────
    add_sun(
        name="Light_Fill_Back",
        energy=0.8,
        color=(0.75, 0.80, 1.00),
        rx=20, ry=0, rz=160,
    )

    # ── 5. RIM SUN — behind scene, creates bright edge on all spheres ─────────
    # This makes each moon clearly readable against the black background
    add_sun(
        name="Light_Rim",
        energy=2.0,
        color=(0.80, 0.90, 1.00),   # cool blue-white rim
        rx=140, ry=0, rz=40,
    )

    print("✅ Lighting ready — pure black space background")
    print()
    print("   Light_Key          — warm white sun, energy 5.0, shadows ON")
    print("   Light_Fill_Right   — cool sun from right,  energy 1.5")
    print("   Light_Fill_Bottom  — sun pointing UP,       energy 1.2  ← fixes dark belly")
    print("   Light_Fill_Back    — rear fill sun,         energy 0.8")
    print("   Light_Rim          — blue-white rim sun,    energy 2.0")
    print()
    print("   Background: pure black (0,0,0), strength 0.0")
    print()
    print("   Tweak tips:")
    print("   → Still dark on bottom? raise Light_Fill_Bottom energy (try 2.0)")
    print("   → Too flat/washed out? lower Light_Fill_Right energy (try 0.8)")
    print("   → Rim too bright?      lower Light_Rim energy (try 1.2)")


setup_lighting()