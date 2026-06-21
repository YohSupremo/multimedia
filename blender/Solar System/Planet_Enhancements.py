"""
Planet_Enhancements.py
======================
Consolidated script that handles the full material pipelines, texture extractions,
atmospheric glows, surface bump maps, and equatorial ring systems for all planets
and the Moon in the Solar System.

Safe to run multiple times. Rebuilds node networks cleanly without duplication.
"""

import bpy
import math
import os

# ── GLOBAL CONFIGURATION ──────────────────────────────────────────────────────
TEXTURE_BASE = r"C:\Users\kelly\Downloads\Blender\textures"

# Texture Paths
TEX_PATH = {
    "Mercury": os.path.join(TEXTURE_BASE, "mercury.jpg"),
    "Venus":   os.path.join(TEXTURE_BASE, "venus.jpg"),
    "Earth":   os.path.join(TEXTURE_BASE, "earth.jpg"),
    "Clouds":  os.path.join(TEXTURE_BASE, "clouds.jpg"),
    "Night":   os.path.join(TEXTURE_BASE, "night.jpg"),
    "Moon":    os.path.join(TEXTURE_BASE, "moon.jpg"),
    "Mars":    os.path.join(TEXTURE_BASE, "mars.jpg"),
    "Jupiter": os.path.join(TEXTURE_BASE, "jupiter.jpg"),
    "Saturn":  os.path.join(TEXTURE_BASE, "saturn.jpg"),
    "Uranus":  os.path.join(TEXTURE_BASE, "uranus.jpg"),
    "Neptune": os.path.join(TEXTURE_BASE, "neptune.jpg"),
    "Pluto":   os.path.join(TEXTURE_BASE, "pluto.jpg"),
}

# ──────────────────────────────────────────────────────────────────────────────
# CORE HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def remove_if_exists(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)


def _remove_named_nodes(nodes, name_list):
    """Remove enhancement nodes by name so the script is re-runnable."""
    for name in name_list:
        n = nodes.get(name)
        if n:
            try:
                nodes.remove(n)
            except RuntimeError:
                pass


def _load_image(path, colorspace, label):
    """Load an image from disk with the given colorspace, or return None."""
    if os.path.exists(path):
        img = bpy.data.images.load(path, check_existing=True)
        img.colorspace_settings.name = colorspace
        print(f"   ✅ {label} loaded from disk: {path}")
        return img
    print(f"   ⚠  {label} not found at {path}")
    return None


def apply_material_transparency(mat, alpha, planet_type):
    """Ensure proper transparency blend mode settings for eevee/viewport rendering."""
    if planet_type == 'Uranus':
        try:
            if alpha < 0.99:
                mat.surface_render_method = 'DITHERED'
            else:
                mat.surface_render_method = 'BLENDED'
            return
        except AttributeError:
            pass
        try:
            if alpha < 0.99:
                mat.blend_method = 'BLEND'
            else:
                mat.blend_method = 'OPAQUE'
            return
        except AttributeError:
            pass
    else:  # Saturn, Neptune, and others
        try:
            mat.surface_render_method = 'BLENDED'
        except AttributeError:
            pass
        try:
            mat.blend_method = 'BLEND'
        except AttributeError:
            pass


def make_ring_band(name, inner_bu, outer_bu, color_rgba, emit_strength, parent_obj, planet_type, z_offset=0.0):
    """Constructs a stable equatorial ring band and parents it to the planet."""
    remove_if_exists(name)

    import bmesh
    mesh = bpy.data.meshes.new(name)
    obj  = obj_new = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm        = bmesh.new()
    RING_SEGS = 256

    outer_verts = []
    inner_verts = []
    for i in range(RING_SEGS):
        angle = (i / RING_SEGS) * math.tau
        c, s  = math.cos(angle), math.sin(angle)
        outer_verts.append(bm.verts.new((c * outer_bu, s * outer_bu, 0.0)))
        inner_verts.append(bm.verts.new((c * inner_bu, s * inner_bu, 0.0)))

    bm.verts.ensure_lookup_table()

    for i in range(RING_SEGS):
        j = (i + 1) % RING_SEGS
        bm.faces.new([outer_verts[i], outer_verts[j],
                      inner_verts[j], inner_verts[i]])

    uv_layer = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for loop in face.loops:
            v     = loop.vert
            dist  = math.sqrt(v.co.x**2 + v.co.y**2)
            u     = (dist - inner_bu) / (outer_bu - inner_bu)
            angle = math.atan2(v.co.y, v.co.x) / math.tau
            loop[uv_layer].uv = (u, angle)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for poly in mesh.polygons:
        poly.use_smooth = True

    r, g, b, a = color_rgba
    mat_name = f"RingMat_{name}"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes            = True
    mat.use_backface_culling = False
    mat.diffuse_color        = (r, g, b, a)
    apply_material_transparency(mat, a, planet_type)

    rnodes = mat.node_tree.nodes
    rlinks = mat.node_tree.links
    rnodes.clear()

    rout  = rnodes.new("ShaderNodeOutputMaterial")
    rout.location = (700, 0)

    if planet_type == 'Saturn':
        rbsdf = rnodes.new("ShaderNodeBsdfPrincipled")
        rbsdf.location = (350, 0)
        rbsdf.inputs["Base Color"].default_value         = (r, g, b, 1.0)
        rbsdf.inputs["Alpha"].default_value              = a
        rbsdf.inputs["Roughness"].default_value          = 0.75
        rbsdf.inputs["Specular IOR Level"].default_value = 0.12
        rbsdf.inputs["Metallic"].default_value           = 0.0

        remit = rnodes.new("ShaderNodeEmission")
        remit.location = (350, -120)
        remit.inputs["Color"].default_value    = (r, g, b, 1.0)
        remit.inputs["Strength"].default_value = emit_strength

        radd = rnodes.new("ShaderNodeAddShader")
        radd.location = (550, 0)
        rlinks.new(rbsdf.outputs["BSDF"],      radd.inputs[0])
        rlinks.new(remit.outputs["Emission"],  radd.inputs[1])
        rlinks.new(radd.outputs["Shader"],     rout.inputs["Surface"])
        
    elif planet_type == 'Uranus':
        rbsdf = rnodes.new("ShaderNodeBsdfPrincipled")
        rbsdf.location = (200, 0)
        rbsdf.inputs["Base Color"].default_value         = (r, g, b, 1.0)
        rbsdf.inputs["Alpha"].default_value              = a
        rbsdf.inputs["Roughness"].default_value          = 1.00   # fully matte
        rbsdf.inputs["Specular IOR Level"].default_value = 0.00   # zero reflection
        rbsdf.inputs["Metallic"].default_value           = 0.0

        try:
            rbsdf.inputs["Emission Color"].default_value    = (r * 0.6, g * 0.6, b * 0.6, 1.0)
            rbsdf.inputs["Emission Strength"].default_value = 0.08
        except KeyError:
            rbsdf.inputs["Emission"].default_value          = (r * 0.6, g * 0.6, b * 0.6, 1.0)
            rbsdf.inputs["Emission Strength"].default_value = 0.08

        rlinks.new(rbsdf.outputs["BSDF"], rout.inputs["Surface"])

    elif planet_type == 'Neptune':
        transparent = rnodes.new("ShaderNodeBsdfTransparent")
        transparent.location = (-100,  80)
        transparent.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)

        diffuse = rnodes.new("ShaderNodeBsdfDiffuse")
        diffuse.location = (-100, -60)
        diffuse.inputs["Color"].default_value     = (r * 0.4, g * 0.4, b * 0.4, 1.0)
        diffuse.inputs["Roughness"].default_value = 1.0

        mix_sh = rnodes.new("ShaderNodeMixShader")
        mix_sh.location = (260, 0)
        mix_sh.inputs["Fac"].default_value = a

        rlinks.new(transparent.outputs["BSDF"],  mix_sh.inputs[1])
        rlinks.new(diffuse.outputs["BSDF"],      mix_sh.inputs[2])
        rlinks.new(mix_sh.outputs["Shader"],     rout.inputs["Surface"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)

    # Snaps ring perfectly to parent's equatorial plane
    obj.location       = (0.0, 0.0, z_offset)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale          = (1.0, 1.0, 1.0)

    if parent_obj is not None:
        from mathutils import Matrix
        obj.parent                = parent_obj
        obj.matrix_parent_inverse = Matrix.Identity(4)

    return obj


def fix_retrograde_spin_driver(obj, divisor):
    """Locks the spin driver in place to ensure retrograde (clockwise) rotation."""
    if obj.animation_data and obj.animation_data.drivers:
        for d in obj.animation_data.drivers:
            if d.data_path == "rotation_euler" and d.array_index == 2:
                expr = f"(frame / {divisor}) * 6.283185307179586 * 1"
                d.driver.expression = expr
                print(f"   ✅ Retrograde spin driver configured: {expr}")


def get_material_clean(obj, mat_name):
    """Finds or creates a material, assigns to slot 0, and returns it."""
    if obj.data.materials:
        mat = obj.data.materials[0]
        if mat is None:
            mat = bpy.data.materials.new(mat_name)
            obj.data.materials[0] = mat
    else:
        mat = bpy.data.materials.new(mat_name)
        obj.data.materials.append(mat)
    mat.use_nodes = True
    return mat


def setup_base_nodes(mat):
    """Returns (bsdf, output_node, existing_tex_nodes) for a node tree."""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    out  = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    existing_tex = [n for n in nodes if n.type == 'TEX_IMAGE']

    if bsdf is None:
        nodes.clear()
        out  = nodes.new("ShaderNodeOutputMaterial"); out.location  = (1000, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (  600, 0)
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        existing_tex = []
    if out is None:
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (1000, 0)

    # Disconnect links to Base Color and Normal
    for sock_name in ["Base Color", "Normal"]:
        for lnk in list(bsdf.inputs[sock_name].links):
            links.remove(lnk)
            
    # Disconnect links to Surface Output
    for lnk in list(out.inputs["Surface"].links):
        links.remove(lnk)

    return bsdf, out, existing_tex


# ──────────────────────────────────────────────────────────────────────────────
# ENHANCEMENTS
# ──────────────────────────────────────────────────────────────────────────────

def enhance_mercury(obj):
    mat = get_material_clean(obj, "Mercury_Mat")
    bsdf, out, existing_tex = setup_base_nodes(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf.inputs["Roughness"].default_value          = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    bsdf.inputs["Metallic"].default_value           = 0.0
    try:
        bsdf.inputs["Sheen Weight"].default_value   = 0.04
    except KeyError:
        pass

    _remove_named_nodes(nodes, [
        "Mercury_TexCoord", "Mercury_Mapping", "Mercury_TexImage",
        "Mercury_HueSat", "Mercury_Curves", "Mercury_Tint",
        "Mercury_SepColor", "Mercury_Invert", "Mercury_MixBump", "Mercury_Bump"
    ])

    image = None
    if existing_tex and existing_tex[0].image:
        image = existing_tex[0].image
    else:
        image = _load_image(TEX_PATH["Mercury"], 'sRGB', "Mercury base")

    for tex_n in existing_tex:
        nodes.remove(tex_n)

    def N(t, loc, name=None):
        node = nodes.new(t)
        node.location = loc
        if name:
            node.name = name; node.label = name
        return node

    tex_coord = N("ShaderNodeTexCoord", (-950, 100), "Mercury_TexCoord")
    mapping   = N("ShaderNodeMapping",  (-750, 100), "Mercury_Mapping")
    tex_node  = N("ShaderNodeTexImage", (-500, 120), "Mercury_TexImage")
    if image:
        tex_node.image = image

    links.new(tex_coord.outputs["UV"],   mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

    hue_sat = N("ShaderNodeHueSaturation", (-200, 120), "Mercury_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.52
    hue_sat.inputs["Saturation"].default_value = 0.30
    hue_sat.inputs["Value"].default_value      = 0.85

    curves = N("ShaderNodeRGBCurve", (50, 120), "Mercury_Curves")
    c = curves.mapping.curves[3]
    c.points[0].location = (0.0, 0.00)
    c.points[1].location = (0.4, 0.35)
    c.points.new(0.85, 0.92)
    curves.mapping.update()

    tint = N("ShaderNodeMixRGB", (280, 120), "Mercury_Tint")
    tint.blend_type = 'MULTIPLY'
    tint.inputs["Fac"].default_value    = 0.18
    tint.inputs["Color2"].default_value = (0.72, 0.66, 0.60, 1.0)

    sep = N("ShaderNodeSeparateColor", (-500, -180), "Mercury_SepColor")
    invert = N("ShaderNodeInvert", (-250, -180), "Mercury_Invert")
    invert.inputs["Fac"].default_value = 0.35
    mix_bump = N("ShaderNodeMixRGB", (-50, -180), "Mercury_MixBump")
    mix_bump.blend_type = 'MIX'
    mix_bump.inputs["Fac"].default_value = 0.50

    bump = N("ShaderNodeBump", (200, -180), "Mercury_Bump")
    bump.inputs["Strength"].default_value = 0.80
    bump.inputs["Distance"].default_value = 0.08

    if image:
        links.new(tex_node.outputs["Color"],  hue_sat.inputs["Color"])
        links.new(tex_node.outputs["Color"],  sep.inputs["Color"])

    links.new(mapping.outputs["Vector"],  sep.inputs["Color"])
    links.new(hue_sat.outputs["Color"],   curves.inputs["Color"])
    links.new(curves.outputs["Color"],    tint.inputs["Color1"])
    links.new(tint.outputs["Color"],      bsdf.inputs["Base Color"])

    links.new(sep.outputs["Red"],         invert.inputs["Color"])
    links.new(sep.outputs["Red"],         mix_bump.inputs["Color1"])
    links.new(invert.outputs["Color"],    mix_bump.inputs["Color2"])
    links.new(mix_bump.outputs["Color"],  bump.inputs["Height"])
    links.new(bump.outputs["Normal"],     bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"],       out.inputs["Surface"])
    print("   ✓ Mercury enhanced")


def enhance_venus(obj):
    mat = get_material_clean(obj, "Venus_Mat")
    bsdf, out, existing_tex = setup_base_nodes(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf.inputs["Roughness"].default_value          = 1.00
    bsdf.inputs["Specular IOR Level"].default_value = 0.00
    bsdf.inputs["Metallic"].default_value           = 0.0

    _remove_named_nodes(nodes, [
        "Venus_TexCoord", "Venus_Mapping", "Venus_TexImage",
        "Venus_RGBtoBW", "Venus_Ramp", "Venus_HueSat",
        "Venus_Curves", "Venus_Emit", "Venus_AddShader", "Venus_Bump"
    ])
    for leftover in [n for n in nodes if n.type == 'TEX_IMAGE']:
        nodes.remove(leftover)

    image = None
    if existing_tex and existing_tex[0].image:
        image = existing_tex[0].image
    else:
        image = _load_image(TEX_PATH["Venus"], 'sRGB', "Venus clouds")

    for tex_n in existing_tex:
        nodes.remove(tex_n)

    def N(t, loc, name=None):
        node = nodes.new(t); node.location = loc
        if name: node.name = name; node.label = name
        return node

    tex_coord = N("ShaderNodeTexCoord", (-900, 200), "Venus_TexCoord")
    mapping   = N("ShaderNodeMapping",  (-700, 200), "Venus_Mapping")
    tex_node  = N("ShaderNodeTexImage", (-480, 200), "Venus_TexImage")
    if image:
        tex_node.image = image

    links.new(tex_coord.outputs["UV"],   mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

    rgb_to_bw = N("ShaderNodeRGBToBW", (-220, 200), "Venus_RGBtoBW")

    ramp = N("ShaderNodeValToRGB", (20, 200), "Venus_Ramp")
    cr   = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = 0.00; cr.elements[0].color = (0.38, 0.22, 0.06, 1.0)
    cr.elements[1].position = 1.00; cr.elements[1].color = (0.98, 0.94, 0.78, 1.0)
    e = cr.elements.new(0.30); e.color = (0.70, 0.52, 0.18, 1.0)
    e = cr.elements.new(0.58); e.color = (0.88, 0.76, 0.48, 1.0)
    e = cr.elements.new(0.80); e.color = (0.94, 0.88, 0.66, 1.0)

    hue_sat = N("ShaderNodeHueSaturation", (280, 200), "Venus_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.53
    hue_sat.inputs["Saturation"].default_value = 1.20
    hue_sat.inputs["Value"].default_value      = 1.00

    curves = N("ShaderNodeRGBCurve", (480, 200), "Venus_Curves")
    c = curves.mapping.curves[3]
    c.points[0].location = (0.0, 0.0)
    c.points[1].location = (1.0, 1.0)
    c.points.new(0.30, 0.22)
    c.points.new(0.70, 0.82)
    curves.mapping.update()

    emit = N("ShaderNodeEmission", (550, -100), "Venus_Emit")
    emit.inputs["Color"].default_value    = (1.00, 0.55, 0.12, 1.0)
    emit.inputs["Strength"].default_value = 0.06

    add_sh = N("ShaderNodeAddShader", (750, 100), "Venus_AddShader")

    bump = N("ShaderNodeBump", (550, -250), "Venus_Bump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.020

    if image:
        links.new(tex_node.outputs["Color"], rgb_to_bw.inputs["Color"])
    links.new(rgb_to_bw.outputs["Val"],   ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"],      hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],   curves.inputs["Color"])
    links.new(curves.outputs["Color"],    bsdf.inputs["Base Color"])
    links.new(curves.outputs["Color"],    emit.inputs["Color"])

    links.new(rgb_to_bw.outputs["Val"],   bump.inputs["Height"])
    links.new(bump.outputs["Normal"],     bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"],      add_sh.inputs[0])
    links.new(emit.outputs["Emission"],  add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],  out.inputs["Surface"])

    fix_retrograde_spin_driver(obj, 20)
    print("   ✓ Venus enhanced")


def enhance_earth(obj):
    mat = get_material_clean(obj, "Earth_Mat")
    bsdf, out, existing_tex = setup_base_nodes(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf.inputs["Roughness"].default_value          = 0.75
    bsdf.inputs["Specular IOR Level"].default_value = 0.05
    bsdf.inputs["Metallic"].default_value           = 0.0
    bsdf.inputs["IOR"].default_value                = 1.50

    _remove_named_nodes(nodes, [
        "Earth_TexCoord", "Earth_Mapping", "Earth_TexEarth", "Earth_TexCloud",
        "Earth_TexNight", "Earth_HueSat", "Earth_Curves", "Earth_CloudMix",
        "Earth_Emit", "Earth_AddShader"
    ])

    img_earth = img_cloud = img_night = None
    for tex_n in existing_tex:
        if tex_n.image is None: continue
        fname = os.path.basename(tex_n.image.filepath).lower()
        if "earth" in fname or "day" in fname:
            img_earth = tex_n.image
        elif "cloud" in fname:
            img_cloud = tex_n.image
        elif "night" in fname or "light" in fname:
            img_night = tex_n.image

    if img_earth is None: img_earth = _load_image(TEX_PATH["Earth"], 'sRGB', "Earth base")
    if img_cloud is None: img_cloud = _load_image(TEX_PATH["Clouds"], 'sRGB', "Clouds")
    if img_night is None: img_night = _load_image(TEX_PATH["Night"], 'Non-Color', "Night lights")

    for tex_n in existing_tex:
        nodes.remove(tex_n)

    def N(t, loc, name=None):
        node = nodes.new(t); node.location = loc
        if name: node.name = name; node.label = name
        return node

    tex_coord = N("ShaderNodeTexCoord", (-900, 100), "Earth_TexCoord")
    mapping   = N("ShaderNodeMapping",  (-700, 100), "Earth_Mapping")

    tex_earth = N("ShaderNodeTexImage", (-480,  200), "Earth_TexEarth")
    tex_cloud = N("ShaderNodeTexImage", (-480,  -80), "Earth_TexCloud")
    tex_night = N("ShaderNodeTexImage", (-480, -360), "Earth_TexNight")

    if img_earth: tex_earth.image = img_earth
    if img_cloud: tex_cloud.image = img_cloud
    if img_night: tex_night.image = img_night

    links.new(tex_coord.outputs["UV"],   mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_earth.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_cloud.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_night.inputs["Vector"])

    hue_sat = N("ShaderNodeHueSaturation", (-180, 200), "Earth_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.50
    hue_sat.inputs["Saturation"].default_value = 1.30
    hue_sat.inputs["Value"].default_value      = 1.00

    curves = N("ShaderNodeRGBCurve", (60, 200), "Earth_Curves")
    c = curves.mapping.curves[3]
    c.points[0].location = (0.0, 0.0)
    c.points[1].location = (1.0, 1.0)
    c.points.new(0.25, 0.18)
    c.points.new(0.72, 0.80)
    curves.mapping.update()

    cloud_mix = N("ShaderNodeMixRGB", (320, 160), "Earth_CloudMix")
    cloud_mix.blend_type = 'MIX'
    cloud_mix.inputs["Fac"].default_value = 0.10

    emit = N("ShaderNodeEmission", (320, -200), "Earth_Emit")
    emit.inputs["Strength"].default_value = 0.50

    add_sh = N("ShaderNodeAddShader", (580, 0), "Earth_AddShader")

    if img_earth:
        links.new(tex_earth.outputs["Color"], hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],   curves.inputs["Color"])
    links.new(curves.outputs["Color"],    cloud_mix.inputs["Color1"])
    if img_cloud:
        links.new(tex_cloud.outputs["Color"], cloud_mix.inputs["Color2"])
    links.new(cloud_mix.outputs["Color"], bsdf.inputs["Base Color"])

    if img_night:
        links.new(tex_night.outputs["Color"], emit.inputs["Color"])

    links.new(bsdf.outputs["BSDF"],       add_sh.inputs[0])
    links.new(emit.outputs["Emission"],   add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],   out.inputs["Surface"])
    print("   ✓ Earth enhanced")


def enhance_moon(obj):
    mat = get_material_clean(obj, "Moon_Mat")
    bsdf, out, existing_tex = setup_base_nodes(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf.inputs["Roughness"].default_value          = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    bsdf.inputs["Metallic"].default_value           = 0.0
    try:
        bsdf.inputs["Sheen Weight"].default_value   = 0.04
    except KeyError:
        pass

    _remove_named_nodes(nodes, [
        "Moon_TexCoord", "Moon_Mapping", "Moon_TexImage", "Moon_HueSat",
        "Moon_Curves", "Moon_SepColor", "Moon_MixBump", "Moon_Bump",
        "Moon_LumMath", "Moon_Emit", "Moon_AddShader"
    ])

    image = None
    if existing_tex and existing_tex[0].image:
        image = existing_tex[0].image
    else:
        image = _load_image(TEX_PATH["Moon"], 'sRGB', "Moon base")

    for tex_n in existing_tex:
        nodes.remove(tex_n)

    def N(t, loc, name=None):
        node = nodes.new(t); node.location = loc
        if name: node.name = name; node.label = name
        return node

    tex_coord = N("ShaderNodeTexCoord", (-900, 100), "Moon_TexCoord")
    mapping   = N("ShaderNodeMapping",  (-700, 100), "Moon_Mapping")
    tex_node  = N("ShaderNodeTexImage", (-450, 100), "Moon_TexImage")
    if image:
        tex_node.image = image

    links.new(tex_coord.outputs["UV"],   mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

    hue_sat = N("ShaderNodeHueSaturation", (-150, 100), "Moon_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.58
    hue_sat.inputs["Saturation"].default_value = 0.25
    hue_sat.inputs["Value"].default_value      = 0.95

    curves = N("ShaderNodeRGBCurve", (80, 100), "Moon_Curves")
    c = curves.mapping.curves[3]
    c.points[0].location = (0.0, 0.00)
    c.points[1].location = (0.4, 0.36)
    c.points.new(0.80, 0.85)
    curves.mapping.update()

    sep = N("ShaderNodeSeparateColor", (-450, -200), "Moon_SepColor")
    mix_bump = N("ShaderNodeMixRGB", (-200, -200), "Moon_MixBump")
    mix_bump.blend_type = 'MIX'
    mix_bump.inputs["Fac"].default_value = 0.50

    bump = N("ShaderNodeBump", (80, -200), "Moon_Bump")
    bump.inputs["Strength"].default_value = 0.80
    bump.inputs["Distance"].default_value = 0.08

    lum_math = N("ShaderNodeMath", (-200, -380), "Moon_LumMath")
    lum_math.operation = 'MULTIPLY'
    lum_math.inputs[1].default_value = 0.018

    emit = N("ShaderNodeEmission", (80, -380), "Moon_Emit")
    emit.inputs["Color"].default_value = (0.80, 0.88, 1.00, 1.0)

    add_sh = N("ShaderNodeAddShader", (750, -100), "Moon_AddShader")

    if image:
        links.new(tex_node.outputs["Color"],  hue_sat.inputs["Color"])
        links.new(tex_node.outputs["Color"],  sep.inputs["Color"])

    links.new(hue_sat.outputs["Color"],   curves.inputs["Color"])
    links.new(curves.outputs["Color"],    bsdf.inputs["Base Color"])

    links.new(sep.outputs["Red"],         mix_bump.inputs["Color1"])
    links.new(sep.outputs["Green"],       mix_bump.inputs["Color2"])
    links.new(mix_bump.outputs["Color"],  bump.inputs["Height"])
    links.new(bump.outputs["Normal"],     bsdf.inputs["Normal"])

    links.new(sep.outputs["Red"],         lum_math.inputs[0])
    links.new(lum_math.outputs["Value"],  emit.inputs["Strength"])

    links.new(bsdf.outputs["BSDF"],       add_sh.inputs[0])
    links.new(emit.outputs["Emission"],   add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],   out.inputs["Surface"])
    print("   ✓ Moon enhanced")


def enhance_mars(obj):
    mat = get_material_clean(obj, "Mars_Mat")
    bsdf, out, existing_tex = setup_base_nodes(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf.inputs["Roughness"].default_value          = 0.88
    bsdf.inputs["Specular IOR Level"].default_value = 0.05
    bsdf.inputs["Metallic"].default_value           = 0.0
    try:
        bsdf.inputs["Sheen Weight"].default_value   = 0.08
    except KeyError:
        pass

    _remove_named_nodes(nodes, [
        "Mars_TexCoord", "Mars_Mapping", "Mars_TexImage", "Mars_HueSat",
        "Mars_Curves", "Mars_SepColor", "Mars_MixBump", "Mars_Bump",
        "Mars_LumMath", "Mars_Emit", "Mars_AddShader"
    ])

    image = None
    if existing_tex and existing_tex[0].image:
        image = existing_tex[0].image
    else:
        image = _load_image(TEX_PATH["Mars"], 'sRGB', "Mars base")

    for tex_n in existing_tex:
        nodes.remove(tex_n)

    def N(t, loc, name=None):
        node = nodes.new(t); node.location = loc
        if name: node.name = name; node.label = name
        return node

    tex_coord = N("ShaderNodeTexCoord", (-900, 100), "Mars_TexCoord")
    mapping   = N("ShaderNodeMapping",  (-700, 100), "Mars_Mapping")
    tex_node  = N("ShaderNodeTexImage", (-460, 100), "Mars_TexImage")
    if image:
        tex_node.image = image

    links.new(tex_coord.outputs["UV"],   mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

    hue_sat = N("ShaderNodeHueSaturation", (-160, 100), "Mars_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.50
    hue_sat.inputs["Saturation"].default_value = 1.45
    hue_sat.inputs["Value"].default_value      = 1.05

    curves = N("ShaderNodeRGBCurve", (80, 100), "Mars_Curves")
    c = curves.mapping.curves[3]
    c.points[0].location = (0.0, 0.00)
    c.points[1].location = (0.5, 0.52)
    c.points.new(0.85, 0.90)
    curves.mapping.update()

    sep = N("ShaderNodeSeparateColor", (-460, -200), "Mars_SepColor")
    mix_bump = N("ShaderNodeMixRGB", (-200, -200), "Mars_MixBump")
    mix_bump.blend_type = 'MIX'
    mix_bump.inputs["Fac"].default_value = 0.40

    bump = N("ShaderNodeBump", (80, -200), "Mars_Bump")
    bump.inputs["Strength"].default_value = 0.55
    bump.inputs["Distance"].default_value = 0.05

    lum_math = N("ShaderNodeMath", (-200, -400), "Mars_LumMath")
    lum_math.operation = 'MULTIPLY'
    lum_math.inputs[1].default_value = 0.06

    emit = N("ShaderNodeEmission", (80, -400), "Mars_Emit")
    emit.inputs["Color"].default_value = (1.0, 0.45, 0.15, 1.0)

    add_sh = N("ShaderNodeAddShader", (700, -150), "Mars_AddShader")

    if image:
        links.new(tex_node.outputs["Color"],  hue_sat.inputs["Color"])
        links.new(tex_node.outputs["Color"],  sep.inputs["Color"])
    links.new(hue_sat.outputs["Color"],   curves.inputs["Color"])
    links.new(curves.outputs["Color"],    bsdf.inputs["Base Color"])

    links.new(sep.outputs["Red"],         mix_bump.inputs["Color1"])
    links.new(sep.outputs["Green"],       mix_bump.inputs["Color2"])
    links.new(mix_bump.outputs["Color"],  bump.inputs["Height"])
    links.new(bump.outputs["Normal"],     bsdf.inputs["Normal"])

    links.new(sep.outputs["Red"],         lum_math.inputs[0])
    links.new(lum_math.outputs["Value"],  emit.inputs["Strength"])

    links.new(bsdf.outputs["BSDF"],       add_sh.inputs[0])
    links.new(emit.outputs["Emission"],   add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],   out.inputs["Surface"])
    print("   ✓ Mars enhanced")


def enhance_jupiter(obj):
    # Matches build_jupiter_material cleanly
    mat = get_material_clean(obj, "Jupiter_Cinematic")
    bsdf, out, existing_tex = setup_base_nodes(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf.inputs["Roughness"].default_value          = 0.82
    bsdf.inputs["Specular IOR Level"].default_value = 0.03
    bsdf.inputs["Metallic"].default_value           = 0.0

    nodes.clear()

    def N(t, loc, name=None):
        node = nodes.new(t); node.location = loc
        if name: node.name = name; node.label = name
        return node

    tex_coord = N("ShaderNodeTexCoord", (-900, 0))
    mapping   = N("ShaderNodeMapping",  (-700, 0))
    tex       = N("ShaderNodeTexImage", (-450, 150), "Jupiter_Tex")

    image = _load_image(TEX_PATH["Jupiter"], 'sRGB', "Jupiter base")
    if image:
        tex.image = image

    hue_sat = N("ShaderNodeHueSaturation", (-150, 150), "Jupiter_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.52
    hue_sat.inputs["Saturation"].default_value = 1.55
    hue_sat.inputs["Value"].default_value      = 1.05

    curves = N("ShaderNodeRGBCurve", (100, 150), "Jupiter_Curves")
    c = curves.mapping.curves[3]
    c.points[0].location = (0.0, 0.0)
    c.points[1].location = (1.0, 1.0)
    c.points.new(0.25, 0.18)
    c.points.new(0.75, 0.82)
    curves.mapping.update()

    bsdf = N("ShaderNodeBsdfPrincipled", (380, 80))
    bsdf.inputs["Roughness"].default_value          = 0.82
    bsdf.inputs["Specular IOR Level"].default_value = 0.03
    bsdf.inputs["Metallic"].default_value           = 0.0

    emit = N("ShaderNodeEmission", (380, -130), "Jupiter_Emit")
    emit.inputs["Color"].default_value    = (1.0, 0.65, 0.25, 1.0)
    emit.inputs["Strength"].default_value = 0.06

    add_sh = N("ShaderNodeAddShader", (680, 0), "Jupiter_AddShader")
    out    = N("ShaderNodeOutputMaterial", (900, 0))

    links.new(tex_coord.outputs["UV"],      mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"],    tex.inputs["Vector"])
    links.new(tex.outputs["Color"],         hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],     curves.inputs["Color"])
    links.new(curves.outputs["Color"],      bsdf.inputs["Base Color"])
    links.new(curves.outputs["Color"],      emit.inputs["Color"])
    links.new(bsdf.outputs["BSDF"],         add_sh.inputs[0])
    links.new(emit.outputs["Emission"],     add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],     out.inputs["Surface"])
    print("   ✓ Jupiter enhanced")


def enhance_saturn(obj):
    mat = get_material_clean(obj, "Saturn_Mat")
    bsdf, out, existing_tex = setup_base_nodes(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf.inputs["Roughness"].default_value          = 0.90
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    bsdf.inputs["Metallic"].default_value           = 0.0

    _remove_named_nodes(nodes, [
        "Saturn_HueSat", "Saturn_Curves", "Saturn_Emit",
        "Saturn_AddShader", "Saturn_Mapping", "Saturn_TexCoord",
        "Saturn_TexImage", "Saturn_Ramp", "Saturn_Mix"
    ])
    for leftover in [n for n in nodes if n.type == 'TEX_IMAGE']:
        nodes.remove(leftover)

    image = None
    if existing_tex and existing_tex[0].image:
        image = existing_tex[0].image
    else:
        image = _load_image(TEX_PATH["Saturn"], 'sRGB', "Saturn base")

    for tex_n in existing_tex:
        nodes.remove(tex_n)

    def N(t, loc, name=None):
        node = nodes.new(t); node.location = loc
        if name: node.name = name; node.label = name
        return node

    tex_coord = N("ShaderNodeTexCoord", (-900, 200), "Saturn_TexCoord")
    mapping   = N("ShaderNodeMapping",  (-700, 200), "Saturn_Mapping")
    tex_node  = N("ShaderNodeTexImage", (-480, 200), "Saturn_TexImage")
    if image:
        tex_node.image = image
    links.new(tex_coord.outputs["UV"],   mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

    hue_sat = N("ShaderNodeHueSaturation", (-220, 200), "Saturn_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.57
    hue_sat.inputs["Saturation"].default_value = 3.80
    hue_sat.inputs["Value"].default_value      = 0.95

    ramp = N("ShaderNodeValToRGB", (20, 200), "Saturn_Ramp")
    cr = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = 0.0;  cr.elements[0].color = (0.10, 0.05, 0.00, 1.0)
    cr.elements[1].position = 1.0;  cr.elements[1].color = (1.00, 0.78, 0.18, 1.0)
    e = cr.elements.new(0.35);      e.color = (0.38, 0.20, 0.02, 1.0)
    e = cr.elements.new(0.55);      e.color = (0.72, 0.48, 0.08, 1.0)
    e = cr.elements.new(0.75);      e.color = (0.90, 0.65, 0.14, 1.0)

    mix = N("ShaderNodeMixRGB", (260, 200), "Saturn_Mix")
    mix.blend_type = 'MULTIPLY'
    mix.inputs["Fac"].default_value = 0.65

    emit = N("ShaderNodeEmission", (350, -80), "Saturn_Emit")
    emit.inputs["Color"].default_value    = (1.00, 0.78, 0.18, 1.0)
    emit.inputs["Strength"].default_value = 0.05

    add_sh = N("ShaderNodeAddShader", (600, 100), "Saturn_AddShader")

    if image:
        links.new(tex_node.outputs["Color"], hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],  ramp.inputs["Fac"])
    links.new(hue_sat.outputs["Color"],  mix.inputs["Color1"])
    links.new(ramp.outputs["Color"],     mix.inputs["Color2"])
    links.new(mix.outputs["Color"],      bsdf.inputs["Base Color"])
    links.new(mix.outputs["Color"],      emit.inputs["Color"])

    links.new(bsdf.outputs["BSDF"],     add_sh.inputs[0])
    links.new(emit.outputs["Emission"], add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"], out.inputs["Surface"])

    # Build stable Saturn rings
    print("   Building stable Saturn rings...")
    ring_bands = [
        (1.110, 1.240, (0.12, 0.07, 0.01, 0.55), 0.08),  # D
        (1.240, 1.519, (0.28, 0.14, 0.02, 0.85), 0.10),  # C
        (1.519, 1.950, (0.72, 0.42, 0.04, 1.00), 0.18),  # B
        (1.950, 2.020, (0.00, 0.00, 0.00, 0.04), 0.00),  # Cassini gap
        (2.020, 2.270, (0.55, 0.30, 0.04, 0.95), 0.14),  # A
        (2.330, 2.361, (0.80, 0.58, 0.10, 0.92), 0.20),  # F
    ]
    band_names = ["Ring_D", "Ring_C", "Ring_B", "Ring_Cassini", "Ring_A", "Ring_F"]

    for n in band_names:
        remove_if_exists(n)

    for i, (inner_r, outer_r, color, emit) in enumerate(ring_bands):
        z_offset = i * 0.0005
        make_ring_band(band_names[i], inner_r, outer_r, color, emit, obj, 'Saturn', z_offset)
    print("   ✓ Saturn & rings enhanced")


def enhance_uranus(obj):
    mat = get_material_clean(obj, "Uranus_Mat")
    bsdf, out, existing_tex = setup_base_nodes(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf.inputs["Roughness"].default_value          = 0.85
    bsdf.inputs["Specular IOR Level"].default_value = 0.05
    bsdf.inputs["Metallic"].default_value           = 0.0

    _remove_named_nodes(nodes, [
        "Uranus_TexCoord", "Uranus_Mapping", "Uranus_TexImage", "Uranus_RGBtoBW",
        "Uranus_Ramp", "Uranus_HueSat", "Uranus_Curves", "Uranus_Emit",
        "Uranus_AddShader", "Uranus_Bump"
    ])
    for leftover in [n for n in nodes if n.type == 'TEX_IMAGE']:
        nodes.remove(leftover)

    image = None
    if existing_tex and existing_tex[0].image:
        image = existing_tex[0].image
    else:
        image = _load_image(TEX_PATH["Uranus"], 'sRGB', "Uranus base")

    for tex_n in existing_tex:
        nodes.remove(tex_n)

    def N(t, loc, name=None):
        node = nodes.new(t); node.location = loc
        if name: node.name = name; node.label = name
        return node

    tex_coord = N("ShaderNodeTexCoord", (-900, 200), "Uranus_TexCoord")
    mapping   = N("ShaderNodeMapping",  (-700, 200), "Uranus_Mapping")
    tex_node  = N("ShaderNodeTexImage", (-480, 200), "Uranus_TexImage")
    if image:
        tex_node.image = image

    links.new(tex_coord.outputs["UV"],   mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

    rgb_to_bw = N("ShaderNodeRGBToBW", (-220, 200), "Uranus_RGBtoBW")

    ramp = N("ShaderNodeValToRGB", (20, 200), "Uranus_Ramp")
    cr   = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = 0.00; cr.elements[0].color = (0.18, 0.50, 0.62, 1.0)
    cr.elements[1].position = 1.00; cr.elements[1].color = (0.55, 0.88, 0.92, 1.0)
    e = cr.elements.new(0.38); e.color = (0.28, 0.65, 0.76, 1.0)
    e = cr.elements.new(0.68); e.color = (0.42, 0.78, 0.86, 1.0)

    hue_sat = N("ShaderNodeHueSaturation", (280, 200), "Uranus_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.50
    hue_sat.inputs["Saturation"].default_value = 1.20
    hue_sat.inputs["Value"].default_value      = 0.95

    curves = N("ShaderNodeRGBCurve", (480, 200), "Uranus_Curves")
    c = curves.mapping.curves[3]
    c.points[0].location = (0.0, 0.0)
    c.points[1].location = (1.0, 1.0)
    c.points.new(0.35, 0.28)
    c.points.new(0.68, 0.76)
    curves.mapping.update()

    emit = N("ShaderNodeEmission", (550, -100), "Uranus_Emit")
    emit.inputs["Color"].default_value    = (0.30, 0.80, 0.90, 1.0)
    emit.inputs["Strength"].default_value = 0.03

    add_sh = N("ShaderNodeAddShader", (750, 100), "Uranus_AddShader")

    bump = N("ShaderNodeBump", (550, -250), "Uranus_Bump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.010

    if image:
        links.new(tex_node.outputs["Color"], rgb_to_bw.inputs["Color"])
    links.new(rgb_to_bw.outputs["Val"],   ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"],      hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],   curves.inputs["Color"])
    links.new(curves.outputs["Color"],    bsdf.inputs["Base Color"])
    links.new(curves.outputs["Color"],    emit.inputs["Color"])

    links.new(rgb_to_bw.outputs["Val"],   bump.inputs["Height"])
    links.new(bump.outputs["Normal"],     bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"],      add_sh.inputs[0])
    links.new(emit.outputs["Emission"],  add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],  out.inputs["Surface"])

    # Build stable Uranus rings
    print("   Building stable Uranus rings...")
    ring_bands = [
        (1.5625, 1.6500, (0.02, 0.02, 0.02, 0.15), 0.0),  # Zeta
        (1.6625, 1.6800, (0.03, 0.03, 0.03, 0.70), 0.0),  # 6
        (1.6925, 1.7100, (0.03, 0.03, 0.03, 0.65), 0.0),  # 5
        (1.7225, 1.7400, (0.03, 0.03, 0.03, 0.62), 0.0),  # 4
        (1.7625, 1.7850, (0.04, 0.04, 0.04, 0.75), 0.0),  # Alpha
        (1.8050, 1.8275, (0.04, 0.04, 0.04, 0.72), 0.0),  # Beta
        (1.8475, 1.8650, (0.03, 0.03, 0.03, 0.60), 0.0),  # Eta
        (1.8800, 1.9000, (0.04, 0.04, 0.04, 0.75), 0.0),  # Gamma
        (1.9200, 1.9425, (0.04, 0.04, 0.04, 0.78), 0.0),  # Delta
        (1.9675, 1.9825, (0.02, 0.02, 0.02, 0.30), 0.0),  # Lambda
        (2.0500, 2.1200, (0.08, 0.08, 0.09, 0.92), 0.0),  # Epsilon
        (2.3000, 2.4000, (0.02, 0.02, 0.02, 0.12), 0.0),  # Nu
        (2.5750, 2.7250, (0.02, 0.02, 0.02, 0.08), 0.0),  # Mu
    ]
    band_names = [
        "URing_Zeta", "URing_6", "URing_5", "URing_4", "URing_Alpha",
        "URing_Beta", "URing_Eta", "URing_Gamma", "URing_Delta",
        "URing_Lambda", "URing_Epsilon", "URing_Nu", "URing_Mu"
    ]

    for n in band_names:
        remove_if_exists(n)

    for i, (inner_r, outer_r, color, emit) in enumerate(ring_bands):
        make_ring_band(band_names[i], inner_r, outer_r, color, emit, obj, 'Uranus')

    fix_retrograde_spin_driver(obj, 5)
    print("   ✓ Uranus & rings enhanced")


def enhance_neptune(obj):
    mat = get_material_clean(obj, "Neptune_Mat")
    bsdf, out, existing_tex = setup_base_nodes(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf.inputs["Roughness"].default_value          = 0.80
    bsdf.inputs["Specular IOR Level"].default_value = 0.08
    bsdf.inputs["Metallic"].default_value           = 0.0

    _remove_named_nodes(nodes, [
        "Neptune_TexCoord", "Neptune_Mapping", "Neptune_TexImage", "Neptune_RGBtoBW",
        "Neptune_Ramp", "Neptune_HueSat", "Neptune_Curves", "Neptune_Emit",
        "Neptune_AddShader", "Neptune_Bump"
    ])

    image = None
    if existing_tex and existing_tex[0].image:
        image = existing_tex[0].image
    else:
        image = _load_image(TEX_PATH["Neptune"], 'sRGB', "Neptune base")

    for tex_n in existing_tex:
        nodes.remove(tex_n)

    def N(t, loc, name=None):
        node = nodes.new(t); node.location = loc
        if name: node.name = name; node.label = name
        return node

    tex_coord = N("ShaderNodeTexCoord", (-900, 200), "Neptune_TexCoord")
    mapping   = N("ShaderNodeMapping",  (-700, 200), "Neptune_Mapping")
    tex_node  = N("ShaderNodeTexImage", (-480, 200), "Neptune_TexImage")
    if image:
        tex_node.image = image

    links.new(tex_coord.outputs["UV"],   mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

    rgb_to_bw = N("ShaderNodeRGBToBW", (-220, 200), "Neptune_RGBtoBW")

    ramp = N("ShaderNodeValToRGB", (20, 200), "Neptune_Ramp")
    cr   = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = 0.00; cr.elements[0].color = (0.01, 0.08, 0.45, 1.0)
    cr.elements[1].position = 1.00; cr.elements[1].color = (0.04, 0.28, 0.82, 1.0)
    e = cr.elements.new(0.28); e.color = (0.02, 0.13, 0.56, 1.0)
    e = cr.elements.new(0.60); e.color = (0.03, 0.21, 0.70, 1.0)

    hue_sat = N("ShaderNodeHueSaturation", (280, 200), "Neptune_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.50
    hue_sat.inputs["Saturation"].default_value = 1.25
    hue_sat.inputs["Value"].default_value      = 1.00

    curves = N("ShaderNodeRGBCurve", (480, 200), "Neptune_Curves")
    c = curves.mapping.curves[3]
    c.points[0].location = (0.0, 0.0)
    c.points[1].location = (1.0, 1.0)
    c.points.new(0.28, 0.18)
    c.points.new(0.70, 0.82)
    curves.mapping.update()

    emit = N("ShaderNodeEmission", (550, -100), "Neptune_Emit")
    emit.inputs["Color"].default_value    = (0.10, 0.40, 1.00, 1.0)
    emit.inputs["Strength"].default_value = 0.04

    add_sh = N("ShaderNodeAddShader", (750, 100), "Neptune_AddShader")

    bump = N("ShaderNodeBump", (550, -250), "Neptune_Bump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.012

    if image:
        links.new(tex_node.outputs["Color"], rgb_to_bw.inputs["Color"])
    links.new(rgb_to_bw.outputs["Val"],   ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"],      hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],   curves.inputs["Color"])
    links.new(curves.outputs["Color"],    bsdf.inputs["Base Color"])
    links.new(curves.outputs["Color"],    emit.inputs["Color"])

    links.new(rgb_to_bw.outputs["Val"],   bump.inputs["Height"])
    links.new(bump.outputs["Normal"],     bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"],      add_sh.inputs[0])
    links.new(emit.outputs["Emission"],  add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],  out.inputs["Surface"])

    # Build stable Neptune rings (relative sizes, local unit snaps)
    print("   Building stable Neptune rings...")
    ring_bands = [
        (1.579, 1.763, (0.02, 0.02, 0.03, 0.18), 0.0),  # Galle
        (2.079, 2.118, (0.03, 0.03, 0.04, 0.72), 0.0),  # Le Verrier
        (2.118, 2.263, (0.02, 0.02, 0.03, 0.22), 0.0),  # Lassell
        (2.263, 2.303, (0.03, 0.03, 0.04, 0.65), 0.0),  # Arago
        (2.474, 2.526, (0.06, 0.06, 0.09, 0.90), 0.0),  # Adams
    ]
    band_names = [
        "NRing_Galle", "NRing_LeVerrier", "NRing_Lassell",
        "NRing_Arago", "NRing_Adams"
    ]

    for n in band_names:
        remove_if_exists(n)

    for i, (inner_r, outer_r, color, emit) in enumerate(ring_bands):
        make_ring_band(band_names[i], inner_r, outer_r, color, emit, obj, 'Neptune')
    print("   ✓ Neptune & rings enhanced")


def enhance_pluto(obj):
    mat = get_material_clean(obj, "Pluto_Mat")
    bsdf, out, existing_tex = setup_base_nodes(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf.inputs["Roughness"].default_value          = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    bsdf.inputs["Metallic"].default_value           = 0.0

    _remove_named_nodes(nodes, [
        "Pluto_TexCoord", "Pluto_Mapping", "Pluto_TexImage", "Pluto_RGBtoBW",
        "Pluto_Ramp", "Pluto_HueSat", "Pluto_Curves", "Pluto_Emit",
        "Pluto_AddShader", "Pluto_Bump"
    ])
    for leftover in [n for n in nodes if n.type == 'TEX_IMAGE']:
        nodes.remove(leftover)

    image = None
    if existing_tex and existing_tex[0].image:
        image = existing_tex[0].image
    else:
        image = _load_image(TEX_PATH["Pluto"], 'sRGB', "Pluto base")

    for tex_n in existing_tex:
        nodes.remove(tex_n)

    def N(t, loc, name=None):
        node = nodes.new(t); node.location = loc
        if name: node.name = name; node.label = name
        return node

    tex_coord = N("ShaderNodeTexCoord", (-900, 200), "Pluto_TexCoord")
    mapping   = N("ShaderNodeMapping",  (-700, 200), "Pluto_Mapping")
    tex_node  = N("ShaderNodeTexImage", (-480, 200), "Pluto_TexImage")
    if image:
        tex_node.image = image

    links.new(tex_coord.outputs["UV"],   mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

    rgb_to_bw = N("ShaderNodeRGBToBW", (-220, 200), "Pluto_RGBtoBW")

    ramp = N("ShaderNodeValToRGB", (20, 200), "Pluto_Ramp")
    cr   = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = 0.00; cr.elements[0].color = (0.04, 0.01, 0.00, 1.0)
    cr.elements[1].position = 1.00; cr.elements[1].color = (0.95, 0.92, 0.82, 1.0)
    e = cr.elements.new(0.18); e.color = (0.18, 0.07, 0.02, 1.0)
    e = cr.elements.new(0.38); e.color = (0.40, 0.20, 0.08, 1.0)
    e = cr.elements.new(0.57); e.color = (0.68, 0.46, 0.24, 1.0)
    e = cr.elements.new(0.74); e.color = (0.84, 0.74, 0.56, 1.0)

    hue_sat = N("ShaderNodeHueSaturation", (280, 200), "Pluto_HueSat")
    hue_sat.inputs["Hue"].default_value        = 0.52
    hue_sat.inputs["Saturation"].default_value = 1.35
    hue_sat.inputs["Value"].default_value      = 1.00

    curves = N("ShaderNodeRGBCurve", (480, 200), "Pluto_Curves")
    c = curves.mapping.curves[3]
    c.points[0].location = (0.0, 0.0)
    c.points[1].location = (1.0, 1.0)
    c.points.new(0.30, 0.22)
    c.points.new(0.72, 0.82)
    curves.mapping.update()

    emit = N("ShaderNodeEmission", (550, -100), "Pluto_Emit")
    emit.inputs["Color"].default_value    = (0.90, 0.70, 0.40, 1.0)
    emit.inputs["Strength"].default_value = 0.03

    add_sh = N("ShaderNodeAddShader", (750, 100), "Pluto_AddShader")

    bump = N("ShaderNodeBump", (550, -250), "Pluto_Bump")
    bump.inputs["Strength"].default_value = 0.50
    bump.inputs["Distance"].default_value = 0.025

    if image:
        links.new(tex_node.outputs["Color"], rgb_to_bw.inputs["Color"])
    links.new(rgb_to_bw.outputs["Val"],   ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"],      hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"],   curves.inputs["Color"])
    links.new(curves.outputs["Color"],    bsdf.inputs["Base Color"])
    links.new(curves.outputs["Color"],    emit.inputs["Color"])

    links.new(rgb_to_bw.outputs["Val"],   bump.inputs["Height"])
    links.new(bump.outputs["Normal"],     bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"],      add_sh.inputs[0])
    links.new(emit.outputs["Emission"],  add_sh.inputs[1])
    links.new(add_sh.outputs["Shader"],  out.inputs["Surface"])

    fix_retrograde_spin_driver(obj, 18)
    print("   ✓ Pluto enhanced")


# ──────────────────────────────────────────────────────────────────────────────
# UNIVERSAL RUNNER
# ──────────────────────────────────────────────────────────────────────────────

def enhance_all():
    print("\n🌍 Applying Consolidated Cinematic Planet Enhancements...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')


    planets = [
        ("Mercury", enhance_mercury),
        ("Venus",   enhance_venus),
        ("Earth",   enhance_earth),
        ("Moon",    enhance_moon),
        ("Mars",    enhance_mars),
        ("Jupiter", enhance_jupiter),
        ("Saturn",  enhance_saturn),
        ("Uranus",  enhance_uranus),
        ("Neptune", enhance_neptune),
        ("Pluto",   enhance_pluto),
    ]

    for name, func in planets:
        obj = bpy.data.objects.get(name)
        if obj:
            print(f"🎬 Processing: {name}")
            func(obj)
        else:
            print(f"⚠ Object '{name}' not found. Skipping.")

    print("\n💾 Saving file...")
    try:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
        print("✅ Planet enhancements successfully applied and saved!")
    except Exception as e:
        print(f"❌ Failed to save file: {e}")


if __name__ == "__main__":
    enhance_all()
