#!/usr/bin/env python3
"""Build five pure procedural 3D Blender worlds with bpy — no image datablocks.

This is Five Worlds Blender v3. The generated reference JPGs are used only as
external visual guides; this script never loads, packs, samples or links them.
Every surface, atmosphere, light, camera and animated element is native bpy
geometry or a procedural shader node network. The saved .blend files must have
zero bpy.data.images and zero image/environment texture nodes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261112
REVISION = "five-worlds-blender-v3-pure-3d"
IMAGE_NODE_TYPES = {
    "ShaderNodeTexImage", "ShaderNodeTexEnvironment", "GeometryNodeImageTexture",
    "CompositorNodeImage", "ShaderNodeTexIES",
}

REFS = [
    {
        "index": 1, "name": "Alpine Lake", "slug": "AlpineLake",
        "reference": "assets/references/v6/01_alpine_lake_16x9.jpg",
        "reference_original": "assets/references/v6/01_alpine_lake.jpg",
        "motion": "animated lake ripples, drifting mist, golden-hour dolly",
        "palette": ["#0f110c", "#cbc5be", "#50565a", "#98928d", "#313636", "#ecdcc7"],
        "camera_lens": 35.0,
    },
    {
        "index": 2, "name": "Neon Rain Alley", "slug": "NeonRainAlley",
        "reference": "assets/references/v6/02_neon_rain_alley_16x9.jpg",
        "reference_original": "assets/references/v6/02_neon_rain_alley.jpg",
        "motion": "looping rain, flickering neon, wet reflections, tracking move",
        "palette": ["#030708", "#141817", "#5d646d", "#213034", "#443f40", "#a5abaa"],
        "camera_lens": 32.0,
    },
    {
        "index": 3, "name": "Sahara Dunes", "slug": "SaharaDunes",
        "reference": "assets/references/v6/03_sahara_dunes_16x9.jpg",
        "reference_original": "assets/references/v6/03_sahara_dunes.jpg",
        "motion": "wind-blown dust, rippled dune geometry, lateral drift",
        "palette": ["#613328", "#97553c", "#b76b44", "#e1c4b8", "#f7dec5", "#ce9474"],
        "camera_lens": 32.0,
    },
    {
        "index": 4, "name": "Iceland Aurora", "slug": "IcelandAurora",
        "reference": "assets/references/v6/04_iceland_aurora_16x9.jpg",
        "reference_original": "assets/references/v6/04_iceland_aurora.jpg",
        "motion": "animated aurora, surf foam, stars, slow tilt up",
        "palette": ["#0b1214", "#3e5a64", "#527f7d", "#2b3d49", "#1c292d", "#76b79f"],
        "camera_lens": 28.0,
    },
    {
        "index": 5, "name": "Rainforest Temple", "slug": "RainforestTemple",
        "reference": "assets/references/v6/05_rainforest_temple_16x9.jpg",
        "reference_original": "assets/references/v6/05_rainforest_temple.jpg",
        "motion": "waterfall spray, floating dust, canopy shade, slow dolly",
        "palette": ["#14180c", "#5d5d3a", "#29341a", "#868257", "#413f25", "#bbb388"],
        "camera_lens": 35.0,
    },
]


# ---------------------------------------------------------------------------
# Deterministic procedural noise and small math helpers
# ---------------------------------------------------------------------------

def hash2(i: int, j: int, seed: int) -> float:
    n = (i * 374761393 + j * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n = n ^ (n >> 16)
    return (n & 0xFFFFFFFF) / 0xFFFFFFFF


def value_noise(x: float, y: float, seed: int) -> float:
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    u, v = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = hash2(i, j, seed)
    b = hash2(i + 1, j, seed)
    c = hash2(i, j + 1, seed)
    d = hash2(i + 1, j + 1, seed)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def fbm(x: float, y: float, seed: int, octaves: int = 4) -> float:
    total, amp, freq = 0.0, 0.5, 1.0
    for _ in range(octaves):
        total += amp * value_noise(x * freq, y * freq, seed)
        freq *= 2.0
        amp *= 0.5
    return total


def smoothstep(a: float, b: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def try_set(obj, attr, value):
    try:
        setattr(obj, attr, value)
    except Exception:
        pass


def set_input(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def linearize_fcurves(owner):
    anim = getattr(owner, "animation_data", None)
    action = getattr(anim, "action", None)
    if not action:
        return
    for fc in action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def make_cycles(owner):
    anim = getattr(owner, "animation_data", None)
    action = getattr(anim, "action", None)
    if not action:
        return
    for fc in action.fcurves:
        for mod in list(fc.modifiers):
            if mod.type == "CYCLES":
                fc.modifiers.remove(mod)
        mod = fc.modifiers.new("CYCLES")
        try_set(mod, "mode_before", "REPEAT")
        try_set(mod, "mode_after", "REPEAT")


# ---------------------------------------------------------------------------
# Scene organization
# ---------------------------------------------------------------------------

def collection(name: str):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def move_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def make_collections():
    return {
        "environment": collection("COL_Environment"),
        "hero": collection("COL_Geo_Hero"),
        "background": collection("COL_Geo_Background"),
        "props": collection("COL_Props"),
        "atmosphere": collection("COL_Atmosphere"),
        "lights": collection("COL_Lights"),
        "cameras": collection("COL_Cameras"),
        "assets": collection("COL_Assets_Hidden"),
    }


def disable_shadows(obj):
    for attr in ("visible_shadow", "visible_diffuse", "visible_glossy",
                 "visible_transmission", "visible_volume_scatter"):
        try_set(obj, attr, False)
    try_set(obj, "is_shadow_catcher", False)
    try_set(obj, "visible_camera", True)


def smooth_mesh(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True


def scale_mesh_vertices(obj, sx, sy, sz):
    for v in obj.data.vertices:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    obj.data.update()


def join_objects(objects, name, col):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    try:
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    except Exception:
        pass
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    move_to(obj, col)
    return obj


# ---------------------------------------------------------------------------
# Primitive and mesh helpers
# ---------------------------------------------------------------------------

def mesh_object(name, verts, faces, material, col, *, smooth=True, uv_bounds=None):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    move_to(obj, col)
    obj.data.materials.append(material)
    if uv_bounds:
        x0, x1, y0, y1 = uv_bounds
        uv = mesh.uv_layers.new(name="UVMap")
        for poly in mesh.polygons:
            for li in poly.loop_indices:
                co = mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv = ((co.x - x0) / (x1 - x0), (co.y - y0) / (y1 - y0))
    if smooth:
        smooth_mesh(obj)
    return obj


def grid_mesh(name, x_range, y_range, nx, ny, height_fn, material, col, *, uv_bounds=None, smooth=True):
    verts = []
    for j in range(ny + 1):
        y = y_range[0] + (y_range[1] - y_range[0]) * j / ny
        for i in range(nx + 1):
            x = x_range[0] + (x_range[1] - x_range[0]) * i / nx
            verts.append((x, y, height_fn(x, y)))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return mesh_object(name, verts, faces, material, col, smooth=smooth,
                       uv_bounds=uv_bounds or (x_range[0], x_range[1], y_range[0], y_range[1]))


def ribbon_mesh(name, x_range, z_range, y, nx, nz, wave_fn, material, col):
    verts, faces = [], []
    for j in range(nz + 1):
        t = j / nz
        z = z_range[0] + (z_range[1] - z_range[0]) * t
        for i in range(nx + 1):
            u = i / nx
            x = x_range[0] + (x_range[1] - x_range[0]) * u
            verts.append((x, y + wave_fn(u, t), z))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    obj = mesh_object(name, verts, faces, material, col, smooth=True)
    uv = obj.data.uv_layers.new(name="UVMap")
    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            co = obj.data.vertices[obj.data.loops[li].vertex_index].co
            uv.data[li].uv = ((co.x - x_range[0]) / (x_range[1] - x_range[0]),
                              (co.z - z_range[0]) / (z_range[1] - z_range[0]))
    return obj


def cube(name, location, scale, material, col, *, bevel=0.0, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    move_to(obj, col)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        try:
            obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
        except Exception:
            pass
    return obj


def cylinder(name, location, radius, depth, material, col, *, vertices=12,
             bevel=0.0, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                        depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    move_to(obj, col)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def cone(name, location, radius1, radius2, depth, material, col, *, vertices=12):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1,
                                    radius2=radius2, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    move_to(obj, col)
    smooth_mesh(obj)
    return obj


def ico(name, location, radius, material, col, *, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions,
                                          radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    move_to(obj, col)
    smooth_mesh(obj)
    return obj


def plane(name, location, rotation, scale, material, col, *, no_shadow=False):
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    obj.scale = scale
    obj.data.materials.append(material)
    move_to(obj, col)
    if no_shadow:
        disable_shadows(obj)
    return obj


def curve_object(name, points, material, col, *, bevel_depth=0.02):
    data = bpy.data.curves.new(name + "Curve", type="CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.bevel_depth = bevel_depth
    data.bevel_resolution = 0
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1.0)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    move_to(obj, col)
    data.materials.append(material)
    return obj


def multi_curve(name, segments, material, col, *, bevel_depth=0.01):
    data = bpy.data.curves.new(name + "Curve", type="CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.bevel_depth = bevel_depth
    data.bevel_resolution = 0
    for a, b in segments:
        spline = data.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (*a, 1.0)
        spline.points[1].co = (*b, 1.0)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    move_to(obj, col)
    data.materials.append(material)
    return obj


def text_object(name, body, location, rotation, size, material, col):
    data = bpy.data.curves.new(name + "Curve", type="FONT")
    data.body = body
    data.size = size
    data.align_x = "CENTER"
    data.align_y = "CENTER"
    data.extrude = 0.012
    data.bevel_depth = 0.006
    data.bevel_resolution = 1
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    obj.rotation_euler = rotation
    bpy.context.scene.collection.objects.link(obj)
    move_to(obj, col)
    data.materials.append(material)
    return obj


def duplicate_linked(proto, name, location, col, *, rotation=(0, 0, 0), scale=(1, 1, 1)):
    obj = proto.copy()
    obj.data = proto.data
    obj.name = name
    obj.location = location
    obj.rotation_euler = rotation
    obj.scale = scale
    col.objects.link(obj)
    return obj


def displace(obj, name, strength, scale):
    tex = bpy.data.textures.new(name, type="CLOUDS")
    try_set(tex, "noise_scale", scale)
    try_set(tex, "noise_depth", 2)
    mod = obj.modifiers.new("ProceduralDisplace", "DISPLACE")
    mod.texture = tex
    mod.strength = strength
    mod.mid_level = 0.0
    return mod


# ---------------------------------------------------------------------------
# Materials (all procedural; no image datablocks)
# ---------------------------------------------------------------------------

def new_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (560, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nt, bsdf, out


def time_value(nt, frames=300, start=0.0, end=10.0):
    val = nt.nodes.new("ShaderNodeValue")
    val.name = "FW_Time"
    val.label = "Animated time (seconds)"
    val.location = (-1100, -600)
    val.outputs[0].default_value = start
    val.outputs[0].keyframe_insert(data_path="default_value", frame=1)
    val.outputs[0].default_value = end
    val.outputs[0].keyframe_insert(data_path="default_value", frame=frames)
    linearize_fcurves(nt)
    return val


def emission_material(name, color, strength=1.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emission = nt.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1.0)
    emission.inputs["Strength"].default_value = strength
    if alpha >= 0.999:
        nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])
    else:
        transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = alpha
        nt.links.new(transparent.outputs["BSDF"], mix.inputs[1])
        nt.links.new(emission.outputs["Emission"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def noise_material(name, color_a, color_b, *, scale=5.0, roughness=0.7,
                   bump_strength=0.12, frames=300, animate=False, detail=3.0,
                   distortion=0.0, coord_source="Object", transmission=0.0,
                   ior=1.45, coat=0.0, subsurface=0.0, metallic=0.0):
    mat, nt, bsdf, out = new_material(name)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-1100, 120)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    noise.inputs["Roughness"].default_value = 0.65
    noise.inputs["Distortion"].default_value = distortion
    noise.location = (-850, 120)
    nt.links.new(coord.outputs[coord_source], noise.inputs["Vector"])
    if animate:
        tv = time_value(nt, frames=frames, start=0.0, end=10.0)
        nt.links.new(tv.outputs[0], noise.inputs["W"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-520, 160)
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (*color_a, 1.0)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*color_b, 1.0)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (180, -180)
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.08
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, "IOR", ior)
    set_input(bsdf, "Transmission Weight", transmission)
    set_input(bsdf, "Coat Weight", coat)
    set_input(bsdf, "Coat Roughness", 0.06)
    set_input(bsdf, "Subsurface Weight", subsurface)
    return mat, {"noise": noise, "ramp": ramp, "bsdf": bsdf, "coord": coord, "nt": nt}


def height_snow_material(name, z_min, z_max, *, frames=300):
    mat, nodes = noise_material(
        name, (0.055, 0.065, 0.075), (0.34, 0.36, 0.37),
        scale=9.0, roughness=0.86, bump_strength=0.28,
        coord_source="Generated", detail=5.0,
    )
    nt, bsdf, ramp = nodes["nt"], nodes["bsdf"], nodes["ramp"]
    for link in list(nt.links):
        if link.to_socket == bsdf.inputs["Base Color"]:
            nt.links.remove(link)
    geom = nt.nodes.new("ShaderNodeNewGeometry")
    geom.location = (-1100, 500)
    pos = nt.nodes.new("ShaderNodeSeparateXYZ")
    pos.location = (-850, 520)
    nt.links.new(geom.outputs["Position"], pos.inputs["Vector"])
    height = nt.nodes.new("ShaderNodeMapRange")
    height.location = (-600, 520)
    height.data_type = "FLOAT"
    height.interpolation_type = "SMOOTHSTEP"
    height.inputs[1].default_value = z_min
    height.inputs[2].default_value = z_max
    height.inputs[3].default_value = 0.0
    height.inputs[4].default_value = 1.0
    nt.links.new(pos.outputs["Z"], height.inputs[0])
    norm = nt.nodes.new("ShaderNodeSeparateXYZ")
    norm.location = (-850, 300)
    nt.links.new(geom.outputs["Normal"], norm.inputs["Vector"])
    slope = nt.nodes.new("ShaderNodeMapRange")
    slope.location = (-600, 300)
    slope.data_type = "FLOAT"
    slope.interpolation_type = "SMOOTHSTEP"
    slope.inputs[1].default_value = 0.42
    slope.inputs[2].default_value = 0.86
    slope.inputs[3].default_value = 0.0
    slope.inputs[4].default_value = 1.0
    nt.links.new(norm.outputs["Z"], slope.inputs[0])
    mult = nt.nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    mult.location = (-350, 420)
    nt.links.new(height.outputs["Result"], mult.inputs[0])
    nt.links.new(slope.outputs["Result"], mult.inputs[1])
    snow = nt.nodes.new("ShaderNodeMixRGB")
    snow.blend_type = "MIX"
    snow.location = (80, 220)
    snow.inputs[2].default_value = (0.88, 0.91, 0.94, 1.0)
    nt.links.new(mult.outputs[0], snow.inputs[0])
    nt.links.new(ramp.outputs["Color"], snow.inputs[1])
    nt.links.new(snow.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def water_material(name, *, frames=300):
    mat, nodes = noise_material(
        name, (0.010, 0.045, 0.065), (0.040, 0.13, 0.16),
        scale=1.8, roughness=0.025, bump_strength=0.08, frames=frames,
        animate=True, detail=3.0, distortion=0.12, coord_source="Generated",
        transmission=0.12, ior=1.333, coat=0.75,
    )
    nt, bsdf, coord = nodes["nt"], nodes["bsdf"], nodes["coord"]
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.location = (-850, -260)
    wave.wave_type = "BANDS"
    wave.bands_direction = "DIAGONAL"
    wave.inputs["Scale"].default_value = 2.0
    wave.inputs["Distortion"].default_value = 2.0
    wave.inputs["Detail"].default_value = 2.0
    nt.links.new(coord.outputs["Generated"], wave.inputs["Vector"])
    bump2 = nt.nodes.new("ShaderNodeBump")
    bump2.location = (180, -360)
    bump2.inputs["Strength"].default_value = 0.07
    bump2.inputs["Distance"].default_value = 0.02
    nt.links.new(wave.outputs["Fac"], bump2.inputs["Height"])
    # Chain the existing bump through the second wave bump.
    existing = next((l.from_node for l in nt.links if l.to_socket == bsdf.inputs["Normal"]), None)
    if existing:
        nt.links.new(existing.outputs["Normal"], bump2.inputs["Normal"])
        for l in list(nt.links):
            if l.to_socket == bsdf.inputs["Normal"]:
                nt.links.remove(l)
    nt.links.new(bump2.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def wet_asphalt_material(name):
    mat, nodes = noise_material(
        name, (0.012, 0.016, 0.02), (0.075, 0.082, 0.09),
        scale=7.0, roughness=0.22, bump_strength=0.12,
        coord_source="Generated", detail=4.0,
        ior=1.45, coat=0.65,
    )
    nt, bsdf, noise = nodes["nt"], nodes["bsdf"], nodes["noise"]
    rough_ramp = nt.nodes.new("ShaderNodeValToRGB")
    rough_ramp.location = (-300, -260)
    rough_ramp.color_ramp.elements[0].position = 0.30
    rough_ramp.color_ramp.elements[0].color = (0.035, 0.035, 0.035, 1)
    rough_ramp.color_ramp.elements[1].position = 0.70
    rough_ramp.color_ramp.elements[1].color = (0.34, 0.34, 0.34, 1)
    nt.links.new(noise.outputs["Fac"], rough_ramp.inputs["Fac"])
    for link in list(nt.links):
        if link.to_socket == bsdf.inputs["Roughness"]:
            nt.links.remove(link)
    nt.links.new(rough_ramp.outputs["Color"], bsdf.inputs["Roughness"])
    return mat


def sand_material(name):
    mat, nodes = noise_material(
        name, (0.30, 0.10, 0.035), (0.96, 0.53, 0.24),
        scale=5.0, roughness=0.78, bump_strength=0.14,
        coord_source="Generated", detail=5.0,
    )
    nt, bsdf, coord = nodes["nt"], nodes["bsdf"], nodes["coord"]
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.location = (-850, -260)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.wave_profile = "SIN"
    wave.inputs["Scale"].default_value = 18.0
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 3.0
    nt.links.new(coord.outputs["UV"], wave.inputs["Vector"])
    bump2 = nt.nodes.new("ShaderNodeBump")
    bump2.location = (180, -360)
    bump2.inputs["Strength"].default_value = 0.22
    bump2.inputs["Distance"].default_value = 0.045
    nt.links.new(wave.outputs["Fac"], bump2.inputs["Height"])
    existing = next((l.from_node for l in nt.links if l.to_socket == bsdf.inputs["Normal"]), None)
    if existing:
        nt.links.new(existing.outputs["Normal"], bump2.inputs["Normal"])
        for l in list(nt.links):
            if l.to_socket == bsdf.inputs["Normal"]:
                nt.links.remove(l)
    nt.links.new(bump2.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def stone_moss_material(name):
    return noise_material(
        name, (0.16, 0.17, 0.13), (0.28, 0.36, 0.17),
        scale=4.5, roughness=0.88, bump_strength=0.24,
        coord_source="Generated", detail=5.0, distortion=0.2,
    )[0]


def leaf_material(name, dark=(0.025, 0.09, 0.025), light=(0.18, 0.35, 0.08)):
    return noise_material(
        name, dark, light, scale=8.0, roughness=0.46,
        bump_strength=0.06, coord_source="Generated", detail=3.0,
        subsurface=0.08, transmission=0.04,
    )[0]


def soft_edge_factor(nt, uv_output, *, edge=0.22, location=(-700, 0)):
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (location[0], location[1] + 160)
    nt.links.new(uv_output, sep.inputs["Vector"])

    def ramp(socket, lo, hi, pos):
        node = nt.nodes.new("ShaderNodeMapRange")
        node.location = pos
        node.data_type = "FLOAT"
        node.interpolation_type = "SMOOTHSTEP"
        node.clamp = True
        node.inputs[1].default_value = lo
        node.inputs[2].default_value = hi
        node.inputs[3].default_value = 0.0
        node.inputs[4].default_value = 1.0
        nt.links.new(socket, node.inputs[0])
        return node.outputs["Result"]

    def subtract_from_one(socket, pos):
        node = nt.nodes.new("ShaderNodeMath")
        node.operation = "SUBTRACT"
        node.location = pos
        node.inputs[0].default_value = 1.0
        nt.links.new(socket, node.inputs[1])
        return node.outputs[0]

    def multiply(a, b, pos):
        node = nt.nodes.new("ShaderNodeMath")
        node.operation = "MULTIPLY"
        node.location = pos
        nt.links.new(a, node.inputs[0])
        nt.links.new(b, node.inputs[1])
        return node.outputs[0]

    u0 = ramp(sep.outputs["X"], 0.0, edge, (location[0] + 180, location[1] + 260))
    u1 = ramp(subtract_from_one(sep.outputs["X"], (location[0] + 180, location[1] + 80)),
              0.0, edge, (location[0] + 360, location[1] + 260))
    v0 = ramp(sep.outputs["Y"], 0.0, edge, (location[0] + 180, location[1] - 80))
    v1 = ramp(subtract_from_one(sep.outputs["Y"], (location[0] + 180, location[1] - 260)),
              0.0, edge, (location[0] + 360, location[1] - 80))
    ux = multiply(u0, u1, (location[0] + 560, location[1] + 180))
    vy = multiply(v0, v1, (location[0] + 560, location[1] - 120))
    return multiply(ux, vy, (location[0] + 760, location[1] + 20))


def soft_alpha_emission_material(name, color_a, color_b, *, alpha_scale=0.4,
                                 strength=1.2, noise_scale=4.0, frames=300,
                                 contrast=(0.32, 0.78), soft_edges=True,
                                 edge=0.22, vertical_streaks=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (1100, 0)
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    transparent.location = (650, -220)
    emission = nt.nodes.new("ShaderNodeEmission")
    emission.location = (650, 140)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.location = (880, 0)
    nt.links.new(transparent.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emission.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-1300, 200)
    tv = time_value(nt, frames=frames, start=0.0, end=10.0)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.location = (-1050, 180)
    noise.inputs["Scale"].default_value = noise_scale
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.7
    noise.inputs["Distortion"].default_value = 0.45
    nt.links.new(coord.outputs["Generated"], noise.inputs["Vector"])
    nt.links.new(tv.outputs[0], noise.inputs["W"])
    alpha_ramp = nt.nodes.new("ShaderNodeValToRGB")
    alpha_ramp.location = (-780, -100)
    alpha_ramp.color_ramp.elements[0].position = contrast[0]
    alpha_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    alpha_ramp.color_ramp.elements[1].position = contrast[1]
    alpha_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(noise.outputs["Fac"], alpha_ramp.inputs["Fac"])
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    bw.location = (-560, -100)
    nt.links.new(alpha_ramp.outputs["Color"], bw.inputs["Color"])
    if soft_edges:
        mask = soft_edge_factor(nt, coord.outputs["UV"], edge=edge, location=(-1200, -420))
        masked = nt.nodes.new("ShaderNodeMath")
        masked.operation = "MULTIPLY"
        masked.location = (-320, -120)
        nt.links.new(bw.outputs["Val"], masked.inputs[0])
        nt.links.new(mask, masked.inputs[1])
        alpha_source = masked.outputs[0]
    else:
        alpha_source = bw.outputs["Val"]
    if vertical_streaks:
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.location = (-1050, -360)
        wave.wave_type = "BANDS"
        wave.bands_direction = "X"
        wave.wave_profile = "SIN"
        wave.inputs["Scale"].default_value = 11.0
        wave.inputs["Distortion"].default_value = 2.5
        wave.inputs["Detail"].default_value = 2.0
        nt.links.new(coord.outputs["UV"], wave.inputs["Vector"])
        phase = nt.nodes.new("ShaderNodeMath")
        phase.operation = "MULTIPLY"
        phase.location = (-1050, -560)
        phase.inputs[1].default_value = 0.16
        nt.links.new(tv.outputs[0], phase.inputs[0])
        nt.links.new(phase.outputs[0], wave.inputs["Phase Offset"])
        streak_ramp = nt.nodes.new("ShaderNodeValToRGB")
        streak_ramp.location = (-780, -360)
        streak_ramp.color_ramp.elements[0].position = 0.20
        streak_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        streak_ramp.color_ramp.elements[1].position = 0.80
        streak_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
        nt.links.new(wave.outputs["Fac"], streak_ramp.inputs["Fac"])
        streak_bw = nt.nodes.new("ShaderNodeRGBToBW")
        streak_bw.location = (-560, -360)
        nt.links.new(streak_ramp.outputs["Color"], streak_bw.inputs["Color"])
        streaked = nt.nodes.new("ShaderNodeMath")
        streaked.operation = "MULTIPLY"
        streaked.location = (-120, -260)
        nt.links.new(alpha_source, streaked.inputs[0])
        nt.links.new(streak_bw.outputs["Val"], streaked.inputs[1])
        alpha_source = streaked.outputs[0]
    scale = nt.nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.location = (50, -120)
    scale.inputs[1].default_value = alpha_scale
    nt.links.new(alpha_source, scale.inputs[0])
    nt.links.new(scale.outputs[0], mix.inputs[0])
    color_ramp = nt.nodes.new("ShaderNodeValToRGB")
    color_ramp.location = (-780, 220)
    color_ramp.color_ramp.elements[0].position = 0.18
    color_ramp.color_ramp.elements[0].color = (*color_a, 1.0)
    color_ramp.color_ramp.elements[1].position = 0.82
    color_ramp.color_ramp.elements[1].color = (*color_b, 1.0)
    nt.links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
    nt.links.new(color_ramp.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = strength
    return mat


# ---------------------------------------------------------------------------
# Lighting, camera, world, compositor and render settings
# ---------------------------------------------------------------------------

def aim(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


def sun_light(name, color, energy, direction, cols):
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 20))
    obj = bpy.context.object
    obj.name = name
    obj.data.color = color
    obj.data.energy = energy
    obj.data.angle = math.radians(2.0)
    obj.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    move_to(obj, cols["lights"])
    return obj


def area_light(name, color, energy, location, target, size, cols):
    bpy.ops.object.light_add(type="AREA", location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.color = color
    obj.data.energy = energy
    obj.data.shape = "RECTANGLE"
    obj.data.size = size
    obj.data.size_y = size * 0.6
    aim(obj, target)
    move_to(obj, cols["lights"])
    return obj


def flicker(light, base_energy, rng, frames=300):
    for frame in range(1, frames + 1, 30):
        light.data.energy = base_energy * (0.78 + 0.22 * rng.random())
        light.data.keyframe_insert(data_path="energy", frame=frame)
    linearize_fcurves(light.data)


def sky_world(scene, *, elevation, rotation, strength, air=1.0, dust=1.0,
              ozone=1.0, sun_intensity=1.0, sun_disc=False):
    world = bpy.data.worlds.new("FW_ProceduralSky")
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(elevation)
    sky.sun_rotation = math.radians(rotation)
    sky.sun_intensity = sun_intensity
    sky.air_density = air
    sky.dust_density = dust
    sky.ozone_density = ozone
    try_set(sky, "sun_disc", sun_disc)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    scene.world = world
    return world


def camera(scene, name, positions, targets, lens, cols, *, fstop=8.0, frames=300):
    bpy.ops.object.camera_add(location=positions[0][1])
    cam = bpy.context.object
    cam.name = name
    cam.data.lens = lens
    cam.data.sensor_width = 36.0
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.clip_start = 0.1
    cam.data.clip_end = 500.0
    target = bpy.data.objects.new("EMPTY_CamTarget_" + name.replace("CAM_", ""), None)
    target.empty_display_type = "PLAIN_AXES"
    target.empty_display_size = 0.3
    target.location = targets[0][1]
    cols["cameras"].objects.link(target)
    move_to(cam, cols["cameras"])
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = target
    cam.data.dof.aperture_fstop = fstop
    for frame, loc in positions:
        cam.location = loc
        cam.keyframe_insert(data_path="location", frame=frame)
    for frame, loc in targets:
        target.location = loc
        target.keyframe_insert(data_path="location", frame=frame)
    linearize_fcurves(cam)
    linearize_fcurves(target)
    scene.camera = cam
    return cam


def compositor(scene, *, glare=False):
    scene.use_nodes = True
    nt = scene.node_tree
    nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers")
    comp = nt.nodes.new("CompositorNodeComposite")
    rl.location = (-300, 0)
    comp.location = (400, 0)
    if glare:
        g = nt.nodes.new("CompositorNodeGlare")
        g.location = (50, 0)
        g.glare_type = "FOG_GLOW"
        g.quality = "MEDIUM"
        g.threshold = 1.1
        g.mix = -0.88
        g.size = 7
        nt.links.new(rl.outputs["Image"], g.inputs["Image"])
        nt.links.new(g.outputs["Image"], comp.inputs["Image"])
    else:
        nt.links.new(rl.outputs["Image"], comp.inputs["Image"])
    scene.render.use_compositing = True
    scene.render.use_sequencer = False


def render_settings(scene, *, width, height, samples, fps, frames):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.08
    scene.cycles.use_denoising = True
    try_set(scene.cycles, "denoiser", "OPENIMAGEDENOISE")
    try_set(scene.cycles, "denoising_input_passes", "RGB_ALBEDO_NORMAL")
    try_set(scene.cycles, "max_bounces", 4)
    try_set(scene.cycles, "diffuse_bounces", 2)
    try_set(scene.cycles, "glossy_bounces", 2)
    try_set(scene.cycles, "transmission_bounces", 2)
    try_set(scene.cycles, "transparent_max_bounces", 4)
    try_set(scene.cycles, "volume_bounces", 0)
    try_set(scene.cycles, "caustics_reflective", False)
    try_set(scene.cycles, "caustics_refractive", False)
    try_set(scene.cycles, "use_light_tree", True)
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.use_persistent_data = True
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = frames
    scene.frame_step = 1
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.render.film_transparent = False
    scene.render.use_overwrite = True
    scene.render.use_placeholder = False
    scene.render.use_file_extension = True
    scene.render.use_motion_blur = False
    scene.render.use_simplify = True
    scene.render.simplify_subdivision = 1
    scene.render.filepath = "//frames_v3/frame_"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.unit_settings.system = "METRIC"
    scene.render.use_stamp = False


# ---------------------------------------------------------------------------
# Geometry Nodes scatter and reusable 3D assets
# ---------------------------------------------------------------------------

def asset_collection(name, cols):
    col = bpy.data.collections.new(name)
    cols["assets"].children.link(col)
    return col


def hide_asset(obj):
    obj.hide_render = True
    obj.hide_set(True)
    return obj


def scatter(source, branches, name):
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes, links = ng.nodes, ng.links
    inp = nodes.new("NodeGroupInput")
    inp.location = (-1200, 0)
    out = nodes.new("NodeGroupOutput")
    out.location = (1200, 0)
    join = nodes.new("GeometryNodeJoinGeometry")
    join.location = (900, 0)
    links.new(inp.outputs["Geometry"], join.inputs["Geometry"])
    for bi, branch in enumerate(branches):
        col, density, seed, scale_min, scale_max = branch
        y = 500 - bi * 420
        dist = nodes.new("GeometryNodeDistributePointsOnFaces")
        dist.location = (-900, y)
        dist.inputs["Density"].default_value = density
        dist.inputs["Seed"].default_value = seed
        links.new(inp.outputs["Geometry"], dist.inputs["Mesh"])
        ci = nodes.new("GeometryNodeCollectionInfo")
        ci.location = (-900, y - 220)
        ci.inputs["Collection"].default_value = col
        ci.inputs["Separate Children"].default_value = True
        ci.inputs["Reset Children"].default_value = True
        idx = nodes.new("FunctionNodeRandomValue")
        idx.location = (-900, y - 420)
        idx.data_type = "INT"
        idx.inputs[4].default_value = 0
        idx.inputs[5].default_value = max(0, len(col.objects) - 1)
        idx.inputs[8].default_value = seed + 17
        scale = nodes.new("FunctionNodeRandomValue")
        scale.location = (-620, y - 300)
        scale.data_type = "FLOAT"
        scale.inputs[2].default_value = scale_min
        scale.inputs[3].default_value = scale_max
        scale.inputs[8].default_value = seed + 31
        rot_rand = nodes.new("FunctionNodeRandomValue")
        rot_rand.location = (-620, y - 500)
        rot_rand.data_type = "FLOAT"
        rot_rand.inputs[2].default_value = 0.0
        rot_rand.inputs[3].default_value = 2 * math.pi
        rot_rand.inputs[8].default_value = seed + 47
        rot = nodes.new("ShaderNodeCombineXYZ")
        rot.location = (-360, y - 500)
        links.new(rot_rand.outputs[1], rot.inputs["Z"])
        iops = nodes.new("GeometryNodeInstanceOnPoints")
        iops.location = (-100, y - 120)
        iops.inputs["Pick Instance"].default_value = True
        links.new(dist.outputs["Points"], iops.inputs["Points"])
        links.new(ci.outputs["Instances"], iops.inputs["Instance"])
        links.new(idx.outputs[2], iops.inputs["Instance Index"])
        links.new(scale.outputs[1], iops.inputs["Scale"])
        links.new(rot.outputs["Vector"], iops.inputs["Rotation"])
        real = nodes.new("GeometryNodeRealizeInstances")
        real.location = (260, y - 120)
        links.new(iops.outputs["Instances"], real.inputs["Geometry"])
        links.new(real.outputs["Geometry"], join.inputs["Geometry"])
    links.new(join.outputs["Geometry"], out.inputs["Geometry"])
    mod = source.modifiers.new(name, "NODES")
    mod.node_group = ng
    return mod


def leaf_object(name, length, width, material, col, *, segments=6, thickness=0.008):
    verts, faces = [], []
    for j in range(segments + 1):
        t = j / segments
        y = length * t
        z = 0.12 * math.sin(math.pi * t)
        w = width * max(0.001, math.sin(math.pi * t) ** 0.7)
        verts += [(-w / 2, y, z + thickness / 2), (w / 2, y, z + thickness / 2),
                  (-w / 2, y, z - thickness / 2), (w / 2, y, z - thickness / 2)]
    for j in range(segments):
        a, b = 4 * j, 4 * (j + 1)
        faces.append((a, a + 1, b + 1, b))
        faces.append((a + 2, b + 2, b + 3, a + 3))
        faces.append((a, b, b + 2, a + 2))
        faces.append((a + 1, a + 3, b + 3, b + 1))
    faces.append((0, 2, 3, 1))
    a = 4 * segments
    faces.append((a, a + 1, a + 3, a + 2))
    return mesh_object(name, verts, faces, material, col, smooth=True)


def plant_variant(name, col, leaf_mat, stem_mat, *, height, leaf_len, leaf_width, count, seed):
    rng = random.Random(seed)
    parts = [cylinder(name + "_Stem", (0, 0, height / 2), 0.022, height,
                      stem_mat, col, vertices=8)]
    for k in range(count):
        angle = 2 * math.pi * k / count + rng.uniform(-0.2, 0.2)
        leaf = leaf_object(name + f"_Leaf{k:02d}", leaf_len * rng.uniform(0.8, 1.15),
                           leaf_width, leaf_mat, col)
        leaf.location = (0, 0, height * rng.uniform(0.35, 0.85))
        leaf.rotation_euler = (math.radians(rng.uniform(18, 52)), 0, angle)
        parts.append(leaf)
    return hide_asset(join_objects(parts, name, col))


def pine_variant(name, col, needle_mat, bark_mat, *, height, radius, seed):
    rng = random.Random(seed)
    parts = [cylinder(name + "_Trunk", (0, 0, height * 0.28), radius * 0.12,
                      height * 0.58, bark_mat, col, vertices=10)]
    layers = 7
    for k in range(layers):
        t = k / (layers - 1)
        z = height * (0.22 + 0.72 * t)
        r = radius * (1.0 - 0.72 * t) * rng.uniform(0.92, 1.08)
        d = height * (0.20 - 0.07 * t)
        parts.append(cone(name + f"_Needles{k:02d}", (0, 0, z), r, r * 0.18,
                          d, needle_mat, col, vertices=14))
    return hide_asset(join_objects(parts, name, col))


def rock_variant(name, col, material, seed):
    rng = random.Random(seed)
    obj = ico(name, (0, 0, 0), 1.0, material, col, subdivisions=1)
    scale_mesh_vertices(obj, rng.uniform(0.7, 1.3), rng.uniform(0.6, 1.2), rng.uniform(0.5, 0.9))
    displace(obj, name + "_Clouds", 0.18, 0.45)
    return hide_asset(obj)


def build_asset_collections(cols, kinds):
    result = {}
    needle = noise_material("MAT_Needles", (0.012, 0.045, 0.025), (0.06, 0.14, 0.055),
                            scale=7.0, roughness=0.82, bump_strength=0.12)[0]
    bark = noise_material("MAT_Bark", (0.055, 0.035, 0.022), (0.16, 0.10, 0.06),
                          scale=9.0, roughness=0.9, bump_strength=0.22)[0]
    leaf = leaf_material("MAT_Leaf")
    stem = noise_material("MAT_Stem", (0.05, 0.09, 0.03), (0.16, 0.24, 0.07),
                          scale=8.0, roughness=0.7)[0]
    rock = noise_material("MAT_Rock", (0.10, 0.11, 0.11), (0.34, 0.33, 0.30),
                          scale=8.0, roughness=0.88, bump_strength=0.28, detail=4.0)[0]
    if "pines" in kinds:
        c = asset_collection("ASSET_Pines", cols)
        for k, (h, r) in enumerate([(7.5, 1.5), (9.0, 1.8), (6.2, 1.25)]):
            pine_variant(f"SM_Pine_Var{k+1:02d}", c, needle, bark, height=h, radius=r,
                         seed=SEED + 100 + k)
        result["pines"] = c
    if "plants" in kinds:
        c = asset_collection("ASSET_Broadleaf", cols)
        for k, (h, ll, lw, n) in enumerate([(1.2, 0.9, 0.30, 7), (1.7, 1.2, 0.38, 9), (0.9, 0.7, 0.24, 6)]):
            plant_variant(f"SM_Broadleaf_Var{k+1:02d}", c, leaf, stem, height=h,
                          leaf_len=ll, leaf_width=lw, count=n, seed=SEED + 200 + k)
        result["plants"] = c
    if "ferns" in kinds:
        c = asset_collection("ASSET_Ferns", cols)
        for k, (h, ll, lw, n) in enumerate([(0.75, 0.65, 0.13, 11), (1.0, 0.85, 0.16, 13), (0.6, 0.5, 0.11, 9)]):
            plant_variant(f"SM_Fern_Var{k+1:02d}", c, leaf, stem, height=h,
                          leaf_len=ll, leaf_width=lw, count=n, seed=SEED + 300 + k)
        result["ferns"] = c
    if "rocks" in kinds:
        c = asset_collection("ASSET_Rocks", cols)
        for k in range(4):
            rock_variant(f"SM_Rock_Var{k+1:02d}", c, rock, SEED + 400 + k)
        result["rocks"] = c
    if "sand_rocks" in kinds:
        c = asset_collection("ASSET_SandRocks", cols)
        for k in range(3):
            rock_variant(f"SM_SandRock_Var{k+1:02d}", c, rock, SEED + 500 + k)
        result["sand_rocks"] = c
    return result


# ---------------------------------------------------------------------------
# Particles / atmosphere helpers
# ---------------------------------------------------------------------------

def dust_layer(name, count, bounds, material, cols, rng, frames, *, drift=(2.0, 0.4, 0.0)):
    parent = bpy.data.objects.new(name + "_CTRL", None)
    parent.empty_display_type = "PLAIN_AXES"
    parent.empty_display_size = 0.1
    cols["atmosphere"].objects.link(parent)
    proto = ico(name + "_Proto", (0, 0, 0), 0.018, material, cols["assets"], subdivisions=0)
    hide_asset(proto)
    disable_shadows(proto)
    for k in range(count):
        loc = (rng.uniform(*bounds[0]), rng.uniform(*bounds[1]), rng.uniform(*bounds[2]))
        obj = duplicate_linked(proto, f"{name}_{k:04d}", loc, cols["atmosphere"])
        obj.parent = parent
        disable_shadows(obj)
    parent.location = (0, 0, 0)
    parent.keyframe_insert(data_path="location", frame=1)
    parent.location = drift
    parent.keyframe_insert(data_path="location", frame=frames)
    linearize_fcurves(parent)
    make_cycles(parent)
    return parent


def rain_layer(name, count, bounds, material, cols, rng, frames, *, fall=9.0, offset=0.0):
    segments = []
    for _ in range(count):
        x = rng.uniform(*bounds[0])
        y = rng.uniform(*bounds[1])
        z = rng.uniform(*bounds[2])
        length = rng.uniform(0.22, 0.62)
        segments.append(((x, y, z), (x + rng.uniform(-0.03, 0.03), y, z - length)))
    obj = multi_curve(name, segments, material, cols["atmosphere"], bevel_depth=0.006)
    disable_shadows(obj)
    obj.location.z = offset
    obj.keyframe_insert(data_path="location", frame=1)
    obj.location.z = offset - fall
    obj.keyframe_insert(data_path="location", frame=frames)
    linearize_fcurves(obj)
    make_cycles(obj)
    return obj


def foam_layer(name, count, y0, material, cols, rng, frames):
    segments = []
    for k in range(count):
        x0 = rng.uniform(-24, 24)
        length = rng.uniform(1.2, 5.0)
        y = y0 + rng.uniform(-0.6, 0.6)
        z = 0.08
        pts = []
        for s in range(5):
            t = s / 4
            pts.append((x0 + length * t, y + 0.25 * math.sin(t * math.pi * 2 + k), z))
        for a, b in zip(pts[:-1], pts[1:]):
            segments.append((a, b))
    obj = multi_curve(name, segments, material, cols["atmosphere"], bevel_depth=0.025)
    disable_shadows(obj)
    obj.location.y = 0
    obj.keyframe_insert(data_path="location", frame=1)
    obj.location.y = -3.0
    obj.keyframe_insert(data_path="location", frame=frames)
    linearize_fcurves(obj)
    make_cycles(obj)
    return obj


def starfield(name, count, material, cols, rng):
    proto = ico(name + "_Proto", (0, 0, 0), 0.20, material, cols["assets"], subdivisions=0)
    hide_asset(proto)
    disable_shadows(proto)
    for k in range(count):
        theta = rng.uniform(0, 2 * math.pi)
        phi = rng.uniform(0.15, 1.35)
        r = 150.0
        loc = (r * math.sin(phi) * math.cos(theta),
               r * math.sin(phi) * math.sin(theta),
               r * math.cos(phi) + 10.0)
        obj = duplicate_linked(proto, f"{name}_{k:04d}", loc, cols["atmosphere"])
        disable_shadows(obj)


# ---------------------------------------------------------------------------
# Scene builders
# ---------------------------------------------------------------------------

def build_alpine(scene, cols, args, rng):
    sky_world(scene, elevation=7.5, rotation=35.0, strength=0.42,
              air=0.85, dust=0.35, ozone=1.0, sun_intensity=1.3, sun_disc=True)
    scene.view_settings.exposure = -0.35
    sun_light("LGT_Key_Sun", (1.0, 0.72, 0.44), 5.0, (0.22, -1.0, -0.16), cols)
    camera(scene, "CAM_Hero_AlpineLake",
           [(1, (0.0, -18.0, 2.6)), (args.frames // 2, (1.1, -14.5, 2.5)),
            (args.frames, (0.2, -11.0, 2.4))],
           [(1, (0.0, 55.0, 8.0)), (args.frames, (1.0, 55.0, 8.5))],
           35.0, cols, fstop=9.0, frames=args.frames)

    snow = height_snow_material("MAT_AlpineRockSnow", 6.0, 14.0, frames=args.frames)

    def mountain_h(x, y):
        ridged = 1.0 - abs(2.0 * fbm(x * 0.055, 0.0, SEED + 17, 4) - 1.0)
        peaks = (
            17.0 * math.exp(-abs(x + 38.0) / 11.0)
            + 24.0 * math.exp(-abs(x + 4.0) / 13.0)
            + 16.0 * math.exp(-abs(x - 34.0) / 10.0)
            + 6.0 * ridged
        )
        return 1.5 + smoothstep(60.0, 88.0, y) * min(33.0, peaks)
    grid_mesh("SM_Mountain_Ridge", (-90, 90), (60, 92), 130, 18,
              mountain_h, snow, cols["background"], uv_bounds=(-90, 90, 60, 92))

    def distant_h(x, y):
        n = fbm(x * 0.025, y * 0.025, SEED + 16, 4)
        ridged = 1.0 - abs(2.0 * n - 1.0)
        return min(14.0, (1.0 + 13.0 * ridged ** 1.8) * smoothstep(105, 125, y))
    grid_mesh("SM_Mountain_DistantRidge", (-110, 110), (105, 145), 80, 12,
              distant_h, snow, cols["background"], uv_bounds=(-110, 110, 105, 145))

    def hill_h(x, y):
        return (1.0 + 3.8 * fbm(x * 0.045, y * 0.045, SEED + 13, 4)) * smoothstep(15, 32, y)
    forest_mat = noise_material("MAT_DistantForest", (0.010, 0.022, 0.015),
                                (0.045, 0.085, 0.045), scale=14.0, roughness=0.9,
                                coord_source="Generated")[0]
    grid_mesh("SM_Forest_Hills", (-75, 75), (15, 52), 95, 30,
              hill_h, forest_mat, cols["background"], uv_bounds=(-75, 75, 15, 52))

    water = water_material("MAT_AlpineLakeWater", frames=args.frames)

    def lake_h(x, y):
        return 0.012 * math.sin(x * 0.45 + y * 0.18) + 0.008 * fbm(x * 0.15, y * 0.15, SEED + 14, 2)
    grid_mesh("SM_Lake_Surface", (-55, 55), (-28, 36), 70, 50,
              lake_h, water, cols["hero"], uv_bounds=(-55, 55, -28, 36))

    ground_mat = noise_material("MAT_ShoreGround", (0.045, 0.042, 0.036),
                                (0.20, 0.18, 0.15), scale=9.0, roughness=0.9,
                                bump_strength=0.28, coord_source="Generated")[0]

    def shore_h(x, y):
        return 0.30 * fbm(x * 0.12, y * 0.12, SEED + 15, 3) + 0.16 * smoothstep(-28, -10, y)
    left = grid_mesh("SM_Shore_Left", (-55, -10), (-28, 34), 45, 55,
                     shore_h, ground_mat, cols["hero"], uv_bounds=(-55, -10, -28, 34))
    right = grid_mesh("SM_Shore_Right", (10, 55), (-28, 34), 45, 55,
                      shore_h, ground_mat, cols["hero"], uv_bounds=(10, 55, -28, 34))
    assets = build_asset_collections(cols, {"pines", "rocks"})
    scatter(left, [(assets["pines"], 0.040, 101, 0.75, 1.45),
                   (assets["rocks"], 0.016, 102, 0.35, 0.95)], "GN_Scatter_AlpineLeft")
    scatter(right, [(assets["pines"], 0.040, 103, 0.75, 1.45),
                    (assets["rocks"], 0.016, 104, 0.35, 0.95)], "GN_Scatter_AlpineRight")

    mist = soft_alpha_emission_material("MAT_AlpineMist", (0.55, 0.57, 0.58),
                                        (0.92, 0.83, 0.70), alpha_scale=0.18,
                                        strength=0.6, noise_scale=3.0,
                                        frames=args.frames, contrast=(0.30, 0.80))
    plane("SM_Mist_Lake", (0, 8, 0.55), (0, 0, 0), (24, 5, 1),
          mist, cols["atmosphere"], no_shadow=True)
    compositor(scene, glare=False)


def build_neon(scene, cols, args, rng):
    sky_world(scene, elevation=-3.0, rotation=0.0, strength=0.13,
              air=1.1, dust=1.2, ozone=1.0, sun_intensity=0.3)
    scene.view_settings.exposure = 0.25
    sun_light("LGT_Key_Sun", (0.16, 0.22, 0.32), 0.35, (0.1, 0.4, -1.0), cols)
    camera(scene, "CAM_Hero_NeonRainAlley",
           [(1, (0.0, -15.0, 1.75)), (args.frames // 2, (0.25, -11.5, 1.8)),
            (args.frames, (0.0, -8.0, 1.85))],
           [(1, (0.0, 28.0, 2.2)), (args.frames, (0.0, 30.0, 2.4))],
           32.0, cols, fstop=5.6, frames=args.frames)

    asphalt = wet_asphalt_material("MAT_WetAsphalt")
    plane("SM_Alley_Ground", (0, 10, 0), (0, 0, 0), (6.2, 32, 1),
          asphalt, cols["hero"])
    concrete = noise_material("MAT_ConcreteFacade", (0.04, 0.045, 0.05),
                              (0.18, 0.19, 0.20), scale=6.0, roughness=0.86,
                              bump_strength=0.20, coord_source="Generated", detail=4.0)[0]
    dark_metal = noise_material("MAT_DarkMetal", (0.015, 0.018, 0.02),
                                (0.08, 0.09, 0.10), scale=10.0, roughness=0.42,
                                metallic=0.65)[0]
    window_mats = [
        emission_material("MAT_Window_Warm", (1.0, 0.55, 0.18), 1.1),
        emission_material("MAT_Window_Cool", (0.25, 0.65, 1.0), 0.9),
        emission_material("MAT_Window_Dark", (0.06, 0.08, 0.10), 0.2),
    ]
    sign_colors = [
        ((1.0, 0.12, 0.18), "RAMEN"), ((0.15, 0.85, 1.0), "HOTEL"),
        ((0.95, 0.35, 0.95), "BAR"), ((0.25, 1.0, 0.55), "24H"),
        ((1.0, 0.72, 0.12), "TOKYO"), ((0.55, 0.35, 1.0), "NEON"),
    ]
    for side, x in [("L", -4.6), ("R", 4.6)]:
        for k in range(7):
            y = -13 + k * 8.2
            h = rng.uniform(10.0, 17.0)
            cube(f"SM_Building_{side}_{k:02d}", (x, y, h / 2),
                 (2.2, 7.6, h), concrete, cols["hero"], bevel=0.04)
            for row in range(4):
                z = 2.1 + row * 2.6
                for col in range(3):
                    wy = y - 2.6 + col * 2.2
                    wx = x + (0.96 if side == "L" else -0.96)
                    mat = rng.choice(window_mats)
                    cube(f"SM_Window_{side}_{k:02d}_{row}_{col}", (wx, wy, z),
                         (0.06, 0.85, 1.25), mat, cols["props"])
            for p in range(2):
                py = y + rng.uniform(-2.5, 2.5)
                cylinder(f"SM_Pipe_{side}_{k:02d}_{p}", (x + (1.05 if side == "L" else -1.05), py, h * 0.45),
                         0.055, h * 0.8, dark_metal, cols["props"], vertices=10)
            cube(f"SM_AC_{side}_{k:02d}", (x + (1.12 if side == "L" else -1.12), y + 2.0, 5.2),
                 (0.18, 0.85, 0.65), dark_metal, cols["props"], bevel=0.03)
    for k, (color, label) in enumerate(sign_colors):
        side = -1 if k % 2 == 0 else 1
        x = side * 3.1
        y = 2.0 + k * 5.5
        z = 3.6 + (k % 3) * 2.1
        mat = emission_material(f"MAT_Sign_{k:02d}", color, 2.8)
        panel_mat = emission_material(f"MAT_SignPanel_{k:02d}", tuple(c * 0.18 for c in color), 0.9)
        rot = (math.radians(90), 0, 0)
        cube(f"SM_SignPanel_{k:02d}", (x, y, z), (1.5, 0.58, 0.06),
             panel_mat, cols["props"], rotation=rot)
        text_object(f"SM_SignText_{k:02d}", label, (x, y - 0.04, z),
                    rot, 0.32, mat, cols["props"])
        light = area_light(f"LGT_Neon_{k:02d}", color, rng.uniform(120, 220),
                           (x, y + 0.3, z), (0, y - 3.0, 1.5), 1.2, cols)
        if k % 3 == 1:
            flicker(light, 170.0, rng, frames=args.frames)
    for k in range(9):
        y = -10 + k * 5.5
        z = 6.0 + (k % 3) * 1.4
        pts = [(-4.2, y, z), (-1.5, y, z - 0.35), (1.5, y, z - 0.4), (4.2, y, z)]
        curve_object(f"SM_Cable_{k:02d}", pts, dark_metal, cols["props"], bevel_depth=0.018)

    rain_mat = emission_material("MAT_RainStreak", (0.65, 0.78, 0.9), 1.2, alpha=0.22)
    rain_layer("SM_Rain_A", 260, ((-6, 6), (-14, 34), (1.0, 13.0)),
               rain_mat, cols, rng, args.frames, fall=9.0, offset=0.0)
    rain_layer("SM_Rain_B", 220, ((-6, 6), (-14, 34), (1.0, 13.0)),
               rain_mat, cols, rng, args.frames, fall=9.0, offset=-4.5)
    steam = soft_alpha_emission_material("MAT_AlleySteam", (0.12, 0.16, 0.19),
                                         (0.55, 0.65, 0.72), alpha_scale=0.22,
                                         strength=0.5, noise_scale=5.0,
                                         frames=args.frames, contrast=(0.34, 0.82))
    plane("SM_Steam_Ground", (0, 9, 0.35), (0, 0, 0), (4.0, 8.0, 1),
          steam, cols["atmosphere"], no_shadow=True)
    compositor(scene, glare=True)


def build_sahara(scene, cols, args, rng):
    sky_world(scene, elevation=6.0, rotation=120.0, strength=0.28,
              air=0.9, dust=0.5, ozone=1.0, sun_intensity=1.6, sun_disc=True)
    scene.view_settings.exposure = -0.25
    sun_light("LGT_Key_Sun", (1.0, 0.60, 0.30), 5.5, (0.70, -0.65, -0.18), cols)
    camera(scene, "CAM_Hero_SaharaDunes",
           [(1, (0.0, -22.0, 8.5)), (args.frames // 2, (3.0, -18.0, 8.0)),
            (args.frames, (6.0, -14.0, 7.5))],
           [(1, (0.0, 35.0, 5.0)), (args.frames, (5.0, 38.0, 5.3))],
           35.0, cols, fstop=10.0, frames=args.frames)
    sand = sand_material("MAT_SaharaSand")

    def dune_h(x, y):
        warp = fbm(x * 0.018, y * 0.018, SEED + 21, 4)
        ridge = math.sin(0.090 * y + 0.025 * x + 3.5 * warp)
        cross = math.sin(0.040 * x + 1.5 * fbm(x * 0.025, y * 0.025, SEED + 22, 3))
        crest = 5.5 * math.exp(-(((x - 6) ** 2) / 700.0 + ((y - 22) ** 2) / 300.0))
        small = 0.9 * fbm(x * 0.14, y * 0.14, SEED + 23, 3)
        return 0.5 + 4.2 * (0.5 + 0.5 * ridge) + 1.6 * (0.5 + 0.5 * cross) + crest + small

    dunes = grid_mesh("SM_Sahara_DuneField", (-75, 75), (-22, 95), 160, 110,
                      dune_h, sand, cols["hero"], uv_bounds=(-75, 75, -22, 95))
    displace(dunes, "T_SaharaMicroRelief", 0.22, 0.5)

    def far_h(x, y):
        return 1.5 + 7.0 * fbm(x * 0.018, y * 0.018, SEED + 24, 4) + 2.5 * math.sin(x * 0.025 + y * 0.012)
    far = grid_mesh("SM_Sahara_FarRidges", (-110, 110), (95, 150), 80, 28,
                    far_h, sand, cols["background"], uv_bounds=(-110, 110, 95, 150))
    # Displaced dune field already supplies the horizon ridge; the distant
    # silhouette grid is offset behind it to avoid a connected flat sky mask.
    far.location.y += 6.0
    far.location.z -= 0.8

    assets = build_asset_collections(cols, {"sand_rocks"})
    scatter(dunes, [(assets["sand_rocks"], 0.0020, 201, 0.18, 0.55)],
            "GN_Scatter_SaharaRocks")
    camel_mat = noise_material("MAT_CaravanSilhouette", (0.035, 0.012, 0.006),
                               (0.15, 0.055, 0.025), scale=8.0,
                               roughness=0.9, coord_source="Generated")[0]
    def caravan_h(cx, cy, scale=1.0):
        z0 = dune_h(cx, cy) - 0.3
        body = ico(f"SM_Caravan_Body_{cx:.1f}", (cx, cy, z0 + 1.25 * scale),
                   0.78 * scale, camel_mat, cols["hero"], subdivisions=1)
        scale_mesh_vertices(body, 1.35, 0.62, 0.65)
        ico(f"SM_Caravan_Hump_{cx:.1f}", (cx - 0.35 * scale, cy, z0 + 1.95 * scale),
            0.45 * scale, camel_mat, cols["hero"], subdivisions=1)
        neck = cylinder(f"SM_Caravan_Neck_{cx:.1f}",
                        (cx + 0.85 * scale, cy, z0 + 1.85 * scale),
                        0.15 * scale, 1.5 * scale, camel_mat, cols["hero"], vertices=8)
        neck.rotation_euler = (0, math.radians(-20), 0)
        ico(f"SM_Caravan_Head_{cx:.1f}",
            (cx + 1.18 * scale, cy, z0 + 2.55 * scale),
            0.22 * scale, camel_mat, cols["hero"], subdivisions=1)
        for leg in range(4):
            lx = cx + (-0.55 if leg % 2 == 0 else 0.48) * scale
            ly = cy + (-0.28 if leg < 2 else 0.28) * scale
            cylinder(f"SM_Caravan_Leg_{cx:.1f}_{leg}",
                     (lx, ly, z0 + 0.55 * scale),
                     0.09 * scale, 1.1 * scale, camel_mat, cols["hero"], vertices=8)
    for k in range(4):
        caravan_h(-8.0 + k * 4.2, 28.0 + k * 1.6, 1.1 + 0.08 * k)
    sun_mat = emission_material("MAT_SunDisc", (1.0, 0.62, 0.28), 2.5)
    ico("SM_SunDisc", (34.0, 110.0, 13.0), 2.4, sun_mat, cols["background"], subdivisions=3)
    dust_mat = emission_material("MAT_SandDust", (0.9, 0.55, 0.28), 0.5, alpha=0.5)
    dust_layer("SM_SandDust", 170, ((-35, 35), (-5, 70), (0.5, 9.0)),
               dust_mat, cols, rng, args.frames, drift=(4.0, 1.0, 0.0))
    compositor(scene, glare=False)


def build_iceland(scene, cols, args, rng):
    sky_world(scene, elevation=-7.0, rotation=210.0, strength=0.13,
              air=0.8, dust=0.6, ozone=1.2, sun_intensity=0.4)
    scene.view_settings.exposure = 0.45
    sun_light("LGT_Key_Sun", (0.28, 0.42, 0.62), 0.9, (0.1, 0.6, -0.8), cols)
    camera(scene, "CAM_Hero_IcelandAurora",
           [(1, (0.0, -14.0, 2.2)), (args.frames // 2, (0.0, -12.0, 2.9)),
            (args.frames, (0.0, -10.0, 3.8))],
           [(1, (0.0, 38.0, 9.0)), (args.frames, (0.0, 42.0, 14.0))],
           28.0, cols, fstop=7.1, frames=args.frames)

    black_sand = noise_material("MAT_BlackSand", (0.006, 0.008, 0.010),
                                (0.055, 0.065, 0.070), scale=10.0,
                                roughness=0.55, bump_strength=0.18,
                                coord_source="Generated", detail=4.0, coat=0.25)[0]
    plane("SM_BlackSand_Beach", (0, -7, 0), (0, 0, 0), (55, 18, 1),
          black_sand, cols["hero"])
    ocean = water_material("MAT_IcelandOcean", frames=args.frames)

    def ocean_h(x, y):
        return 0.16 * math.sin(y * 0.55 + x * 0.08) + 0.06 * fbm(x * 0.18, y * 0.18, SEED + 31, 3)
    grid_mesh("SM_Ocean_Surface", (-65, 65), (8, 95), 80, 55,
              ocean_h, ocean, cols["hero"], uv_bounds=(-65, 65, 8, 95))

    snow = height_snow_material("MAT_IcelandRockSnow", 5.0, 24.0, frames=args.frames)

    def glacier_h(x, y):
        n = fbm(x * 0.025, y * 0.025, SEED + 32, 5)
        ridge = 1.0 - abs(2.0 * n - 1.0)
        return (2.0 + 26.0 * ridge ** 1.5) * smoothstep(55, 80, y)
    grid_mesh("SM_Glacier_Ridge", (-90, 90), (55, 135), 100, 40,
              glacier_h, snow, cols["background"], uv_bounds=(-90, 90, 55, 135))

    basalt = noise_material("MAT_Basalt", (0.015, 0.018, 0.022),
                            (0.10, 0.11, 0.12), scale=12.0, roughness=0.82,
                            bump_strength=0.22, coord_source="Generated", detail=4.0)[0]
    for row in range(4):
        for col in range(7):
            x = -13.0 + col * 1.25 + (0.55 if row % 2 else 0.0)
            y = 1.0 + row * 4.8
            h = rng.uniform(3.5, 8.5)
            cylinder(f"SM_Basalt_{row:02d}_{col:02d}", (x, y, h / 2),
                     0.58, h, basalt, cols["hero"], vertices=6, bevel=0.04)

    aurora_mats = [
        soft_alpha_emission_material("MAT_Aurora_Green", (0.02, 0.40, 0.22),
                                     (0.32, 0.95, 0.52), alpha_scale=0.16,
                                     strength=0.9, noise_scale=1.8,
                                     frames=args.frames, contrast=(0.28, 0.80),
                                     edge=0.18, vertical_streaks=False),
        soft_alpha_emission_material("MAT_Aurora_Violet", (0.16, 0.05, 0.42),
                                     (0.42, 0.28, 0.85), alpha_scale=0.12,
                                     strength=0.7, noise_scale=1.5,
                                     frames=args.frames, contrast=(0.30, 0.82),
                                     edge=0.20, vertical_streaks=False),
    ]
    for k, (mat, y, z0, z1) in enumerate([
        (aurora_mats[0], 85.0, 14.0, 46.0),
        (aurora_mats[1], 98.0, 18.0, 52.0),
        (aurora_mats[0], 110.0, 12.0, 42.0),
    ]):
        def wave(u, t, k=k):
            return 3.4 * math.sin(u * 5.0 + k * 1.7) + 1.8 * math.sin(t * 3.0 + u * 2.0)
        ribbon = ribbon_mesh(f"SM_Aurora_Ribbon_{k:02d}", (-45, 45), (z0, z1),
                             y, 72, 30, wave, mat, cols["atmosphere"])
        disable_shadows(ribbon)
    streak_mat = soft_alpha_emission_material(
        "MAT_Aurora_Streaks", (0.02, 0.35, 0.20), (0.35, 0.95, 0.55),
        alpha_scale=0.22, strength=1.0, noise_scale=2.5,
        frames=args.frames, contrast=(0.34, 0.84), edge=0.18,
        vertical_streaks=True,
    )
    streak = ribbon_mesh("SM_Aurora_Streaks", (-28, 28), (20.0, 48.0), 88.0,
                         70, 30, lambda u, t: 1.5 * math.sin(u * 7.0),
                         streak_mat, cols["atmosphere"])
    disable_shadows(streak)
    star_mat = emission_material("MAT_Star", (0.75, 0.85, 1.0), 3.0)
    starfield("SM_Starfield", 220, star_mat, cols, rng)
    foam_mat = emission_material("MAT_SurfFoam", (0.72, 0.88, 0.92), 0.8, alpha=0.55)
    foam_layer("SM_SurfFoam", 42, 8.5, foam_mat, cols, rng, args.frames)
    area_light("LGT_Aurora_Fill", (0.25, 0.8, 0.55), 260.0,
               (0, 55, 28), (0, 10, 2), 24.0, cols)
    compositor(scene, glare=True)


def build_temple(scene, cols, args, rng):
    sky_world(scene, elevation=9.0, rotation=65.0, strength=0.18,
              air=1.0, dust=1.8, ozone=1.0, sun_intensity=0.9)
    scene.view_settings.exposure = -0.40
    sun_light("LGT_Key_Sun", (1.0, 0.88, 0.62), 3.2, (-0.45, 0.8, -0.35), cols)
    camera(scene, "CAM_Hero_RainforestTemple",
           [(1, (0.0, -14.0, 1.8)), (args.frames // 2, (0.0, -11.0, 1.9)),
            (args.frames, (0.0, -8.0, 2.0))],
           [(1, (0.0, 13.0, 2.3)), (args.frames, (0.0, 14.0, 2.6))],
           35.0, cols, fstop=6.3, frames=args.frames)

    ground_mat = noise_material("MAT_ForestGround", (0.022, 0.035, 0.018),
                                (0.11, 0.17, 0.06), scale=7.0, roughness=0.9,
                                bump_strength=0.26, coord_source="Generated", detail=5.0)[0]
    ground = grid_mesh("SM_Forest_Ground", (-28, 28), (-20, 32), 70, 70,
                       lambda x, y: 0.18 * fbm(x * 0.12, y * 0.12, SEED + 41, 3),
                       ground_mat, cols["hero"], uv_bounds=(-28, 28, -20, 32))
    stone = stone_moss_material("MAT_TempleStone")
    dark = noise_material("MAT_TempleShadow", (0.012, 0.015, 0.012),
                          (0.04, 0.05, 0.035), scale=5.0, roughness=0.9)[0]
    cube("SM_Temple_Pillar_L", (-2.0, 13.0, 2.1), (0.75, 0.75, 4.2),
         stone, cols["hero"], bevel=0.06)
    cube("SM_Temple_Pillar_R", (2.0, 13.0, 2.1), (0.75, 0.75, 4.2),
         stone, cols["hero"], bevel=0.06)
    cube("SM_Temple_Lintel", (0.0, 13.0, 4.35), (5.2, 1.0, 0.65),
         stone, cols["hero"], bevel=0.08)
    cube("SM_Temple_Roof", (0.0, 13.0, 5.0), (6.0, 1.5, 0.45),
         stone, cols["hero"], bevel=0.10)
    cube("SM_Temple_RoofTier2", (0.0, 13.0, 5.55), (4.4, 1.0, 0.38),
         stone, cols["hero"], bevel=0.08)
    cube("SM_Temple_Door", (0.0, 12.62, 1.8), (2.2, 0.12, 3.4),
         dark, cols["hero"], bevel=0.03)
    for k in range(6):
        cube(f"SM_Temple_Step_{k:02d}", (0.0, 10.0 - k * 0.55, 0.12 + k * 0.16),
             (4.4 + k * 0.25, 0.7, 0.28), stone, cols["props"], bevel=0.04)
    for k, (x, z) in enumerate([(-3.2, 2.2), (3.2, 2.2), (-3.2, 3.7), (3.2, 3.7)]):
        cube(f"SM_Temple_CarvedBlock_{k:02d}", (x, 12.9, z), (0.55, 0.55, 0.55),
             stone, cols["props"], bevel=0.05)
    waterfall = soft_alpha_emission_material("MAT_Waterfall", (0.28, 0.48, 0.52),
                                              (0.82, 0.94, 1.0), alpha_scale=0.32,
                                              strength=0.9, noise_scale=3.5,
                                              frames=args.frames, contrast=(0.30, 0.82),
                                              edge=0.18, vertical_streaks=True)
    ribbon_mesh("SM_Waterfall", (-6.0, -3.4), (1.0, 8.8), 9.5, 32, 38,
                lambda u, t: 0.18 * math.sin(u * 9.0 + t * 3.0),
                waterfall, cols["atmosphere"])
    pool = water_material("MAT_TemplePool", frames=args.frames)
    plane("SM_Temple_Pool", (-4.7, 8.8, 0.22), (0, 0, 0), (2.4, 3.2, 1),
          pool, cols["hero"])
    bark = noise_material("MAT_TreeBark", (0.045, 0.030, 0.018),
                          (0.14, 0.10, 0.055), scale=9.0, roughness=0.9,
                          bump_strength=0.24)[0]
    canopy = leaf_material("MAT_Canopy", (0.004, 0.016, 0.006), (0.035, 0.11, 0.022))
    for k in range(18):
        side = -1 if k % 2 == 0 else 1
        x = side * rng.uniform(4.5, 17.0)
        y = rng.uniform(-10.0, 26.0)
        h = rng.uniform(7.0, 13.0)
        cylinder(f"SM_TreeTrunk_{k:02d}", (x, y, h / 2), rng.uniform(0.18, 0.34),
                 h, bark, cols["hero"], vertices=10)
        ico(f"SM_Canopy_{k:02d}", (x, y, h + 1.2), rng.uniform(2.2, 3.8),
            canopy, cols["hero"], subdivisions=2)
    for k in range(44):
        x = rng.uniform(-15, 15)
        y = rng.uniform(-6, 22)
        z = rng.uniform(8.5, 13.0)
        blob = ico(f"SM_CanopyOverhead_{k:02d}", (x, y, z),
                   rng.uniform(2.8, 4.8), canopy, cols["hero"], subdivisions=2)
        scale_mesh_vertices(blob, rng.uniform(0.9, 1.4), rng.uniform(0.9, 1.4), 0.55)
    vine_mat = noise_material("MAT_Vine", (0.03, 0.09, 0.025),
                              (0.15, 0.26, 0.07), scale=7.0, roughness=0.75)[0]
    for k in range(14):
        x = rng.uniform(-5.0, 5.0)
        pts = [(x, 12.0, 6.0), (x + rng.uniform(-0.8, 0.8), 12.2, 4.2),
               (x + rng.uniform(-1.1, 1.1), 12.0, 2.2)]
        curve_object(f"SM_Vine_{k:02d}", pts, vine_mat, cols["props"], bevel_depth=0.025)
    assets = build_asset_collections(cols, {"plants", "ferns", "rocks"})
    scatter(ground, [(assets["plants"], 0.050, 301, 0.7, 1.5),
                     (assets["ferns"], 0.100, 302, 0.6, 1.3),
                     (assets["rocks"], 0.012, 303, 0.25, 0.75)],
            "GN_Scatter_Rainforest")
    dust_mat = emission_material("MAT_ForestDust", (0.9, 0.85, 0.55), 0.35, alpha=0.4)
    dust_layer("SM_ForestDust", 110, ((-10, 10), (-5, 20), (0.6, 7.0)),
               dust_mat, cols, rng, args.frames, drift=(0.8, 0.5, 0.2))
    mist = soft_alpha_emission_material("MAT_ForestMist", (0.35, 0.45, 0.32),
                                        (0.82, 0.88, 0.68), alpha_scale=0.28,
                                        strength=0.65, noise_scale=4.0,
                                        frames=args.frames, contrast=(0.32, 0.80))
    plane("SM_Forest_Mist", (0, 9, 0.7), (0, 0, 0), (8, 5, 1),
          mist, cols["atmosphere"], no_shadow=True)
    shaft_mat = soft_alpha_emission_material(
        "MAT_GodRays", (0.52, 0.48, 0.30), (1.0, 0.88, 0.55),
        alpha_scale=0.16, strength=0.8, noise_scale=2.2,
        frames=args.frames, contrast=(0.34, 0.82), edge=0.20,
    )
    for k, (x, z, w) in enumerate([(-2.0, 7.0, 2.2), (1.5, 6.5, 1.6), (4.0, 7.5, 1.9)]):
        shaft = plane(f"SM_GodRay_{k:02d}", (x, 10.0, z),
                      (math.radians(-72), math.radians(8), 0),
                      (w, 6.0, 1), shaft_mat, cols["atmosphere"], no_shadow=True)
        disable_shadows(shaft)
    area_light("LGT_Temple_Fill", (0.55, 0.8, 0.52), 120.0,
               (-6, 8, 6), (0, 12, 2), 6.0, cols)
    compositor(scene, glare=False)


BUILDERS = {1: build_alpine, 2: build_neon, 3: build_sahara,
            4: build_iceland, 5: build_temple}


# ---------------------------------------------------------------------------
# No-image audit, scene freeze, manifest
# ---------------------------------------------------------------------------

def audit_no_images(scene):
    image_nodes = []
    trees = []
    for mat in bpy.data.materials:
        if mat.use_nodes:
            trees.append(mat.node_tree)
    for world in bpy.data.worlds:
        if world.use_nodes:
            trees.append(world.node_tree)
    for group in bpy.data.node_groups:
        trees.append(group)
    if scene.use_nodes and scene.node_tree:
        trees.append(scene.node_tree)
    for tree in trees:
        for node in tree.nodes:
            if node.bl_idname in IMAGE_NODE_TYPES:
                image_nodes.append(f"{tree.name}:{node.name}:{node.bl_idname}")
    image_textures = [t.name for t in bpy.data.textures if getattr(t, "type", "") == "IMAGE"]
    return {
        "image_datablocks": len(bpy.data.images),
        "image_texture_nodes": len(image_nodes),
        "image_texture_node_details": image_nodes,
        "image_texture_datablocks": len(image_textures),
        "environment_texture_nodes": sum(1 for x in image_nodes if "Environment" in x),
        "linked_libraries": len(bpy.data.libraries),
        "movieclips": len(bpy.data.movieclips),
        "objects": len(bpy.data.objects),
        "meshes": len(bpy.data.meshes),
        "materials": len(bpy.data.materials),
        "lights": len(bpy.data.lights),
        "cameras": len(bpy.data.cameras),
        "node_groups": len(bpy.data.node_groups),
        "textures": len(bpy.data.textures),
        "pass": (len(bpy.data.images) == 0 and not image_nodes
                 and not image_textures and len(bpy.data.libraries) == 0
                 and len(bpy.data.movieclips) == 0),
    }


def build_scene(ref, args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try_set(bpy.context.preferences.filepaths, "save_version", 0)
    scene = bpy.context.scene
    scene.name = f"FW_V3_{ref['index']:02d}_{ref['slug']}"
    cols = make_collections()
    rng = random.Random(SEED + ref["index"] * 1000)
    render_settings(scene, width=args.width, height=args.height,
                    samples=args.samples, fps=args.fps, frames=args.frames)
    BUILDERS[ref["index"]](scene, cols, args, rng)
    audit = audit_no_images(scene)
    if not audit["pass"]:
        raise RuntimeError(f"Scene {ref['index']} contains image data: {audit}")
    for image in list(bpy.data.images):
        bpy.data.images.remove(image)
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    blend = out_dir / f"FiveWorlds_BlenderV3_{ref['index']:02d}_{ref['slug']}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    try:
        blend_rel = str(blend.relative_to(ROOT))
    except ValueError:
        blend_rel = str(blend)
    return {
        "index": ref["index"], "name": ref["name"], "slug": ref["slug"],
        "reference": ref["reference"], "reference_original": ref["reference_original"],
        "reference_sha256": sha256(ROOT / ref["reference"]),
        "reference_original_sha256": sha256(ROOT / ref["reference_original"]),
        "motion": ref["motion"], "palette": ref["palette"],
        "camera_lens": ref["camera_lens"],
        "blend": blend_rel, "blend_bytes": blend.stat().st_size,
        "blend_sha256": sha256(blend),
        "built_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pure_3d_audit": audit,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output")
    ap.add_argument("--manifest", default="docs/FIVE_WORLDS_BLENDER_V3_MANIFEST.json")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--scene", type=int, choices=range(1, 6), default=0,
                    help="Build only one scene (test/proof); default builds all five")
    args = ap.parse_args()
    refs = REFS if args.scene == 0 else [r for r in REFS if r["index"] == args.scene]
    scenes = [build_scene(ref, args) for ref in refs]
    review = json.loads((ROOT / "docs/five_worlds_blender_v3_skill_94_review.json").read_text())
    manifest = {
        "revision": REVISION,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "blender": bpy.app.version_string,
        "seed": SEED,
        "spec": {
            "width": args.width, "height": args.height, "fps": args.fps,
            "frames_per_scene": args.frames,
            "duration_seconds": args.frames / args.fps,
            "scenes": len(scenes), "samples": args.samples,
            "engine": "CYCLES", "device": "CPU",
            "denoising": "OpenImageDenoise RGB_ALBEDO_NORMAL",
            "view_transform": "AgX - Medium High Contrast",
        },
        "image_policy": {
            "image_datablocks": 0, "image_texture_nodes": 0,
            "environment_texture_nodes": 0, "packed_files": 0,
            "reference_usage": "visual_reference_only_not_embedded",
        },
        "reference_usage": "visual_reference_only_not_embedded",
        "reference_usage_note": "Generated JPGs are external visual references only; no bpy image datablock, image texture, environment texture, backplate, HDRI or generated image mask exists in any .blend.",
        "reference_analysis": "docs/FIVE_WORLDS_BLENDER_V3_REFERENCE_ANALYSIS.md",
        "visual_proof": {
            "low_resolution_passes": 10,
            "proof_contact": "review/five_worlds_blender_v3/proof_contact_final.jpg",
            "method": "Five-scene Cycles CPU proof contacts were reviewed after each look-development pass; final 1080p frames are rendered by the 15-shard CI workflow.",
        },
        "skills": {
            "library": "skills/blender-skills/.claude/skills",
            "pinned_skill_count": review["pinned_skill_count"],
            "counts": review["counts"],
            "review_json": "docs/five_worlds_blender_v3_skill_94_review.json",
            "review_markdown": "docs/FIVE_WORLDS_BLENDER_V3_SKILL_94_REVIEW.md",
            "method_document": "docs/FIVE_WORLDS_BLENDER_V3.md",
            "meta_skill": "skills/realistic-blender-production/SKILL.md",
        },
        "scenes": scenes,
    }
    manifest_path = (ROOT / args.manifest).resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    try:
        manifest_display = str(manifest_path.relative_to(ROOT))
    except ValueError:
        manifest_display = str(manifest_path)
    print(json.dumps({
        "revision": REVISION, "scenes": len(scenes),
        "manifest": manifest_display,
        "no_image_audits": [s["pure_3d_audit"]["pass"] for s in scenes],
        "blends": [s["blend"] for s in scenes],
    }, indent=2))


if __name__ == "__main__":
    main()
