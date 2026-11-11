#!/usr/bin/env python3
"""Build five actual Blender scenes from the generated reference plates.

The references are packed into each .blend and used as emissive matte-painting
backplates plus animated UV-distorted ground/reflection textures. Procedural
3D foreground geometry, physical lights, particles and camera animation are
rendered with Cycles CPU. This is the Blender re-creation requested by the user,
not the earlier WebGL screenshot route.
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
REFS = [
    {
        "index": 1,
        "name": "Alpine Lake",
        "slug": "AlpineLake",
        "reference": "assets/references/v6/01_alpine_lake_16x9.jpg",
        "reference_original": "assets/references/v6/01_alpine_lake.jpg",
        "motion": "mist, rippled lake, pine/rock foreground, golden-hour dolly",
    },
    {
        "index": 2,
        "name": "Neon Rain Alley",
        "slug": "NeonRainAlley",
        "reference": "assets/references/v6/02_neon_rain_alley_16x9.jpg",
        "reference_original": "assets/references/v6/02_neon_rain_alley.jpg",
        "motion": "falling rain, flickering neon, wet pavement, tracking move",
    },
    {
        "index": 3,
        "name": "Sahara Dunes",
        "slug": "SaharaDunes",
        "reference": "assets/references/v6/03_sahara_dunes_16x9.jpg",
        "reference_original": "assets/references/v6/03_sahara_dunes.jpg",
        "motion": "wind-blown sand, dune ripples, heat shimmer, lateral drift",
    },
    {
        "index": 4,
        "name": "Iceland Aurora",
        "slug": "IcelandAurora",
        "reference": "assets/references/v6/04_iceland_aurora_16x9.jpg",
        "reference_original": "assets/references/v6/04_iceland_aurora.jpg",
        "motion": "animated aurora, stars, surf foam, basalt columns, tilt up",
    },
    {
        "index": 5,
        "name": "Rainforest Temple",
        "slug": "RainforestTemple",
        "reference": "assets/references/v6/05_rainforest_temple_16x9.jpg",
        "reference_original": "assets/references/v6/05_rainforest_temple.jpg",
        "motion": "waterfall, floating dust, temple stones, slow dolly",
    },
]
SEED = 20261111
REVISION = "five-worlds-blender-v2-cycles"


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


def new_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (700, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (380, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nt, bsdf, out


def make_time_value(nt, frames=300, start=0.0, end=10.0):
    val = nt.nodes.new("ShaderNodeValue")
    val.name = "FW_Time"
    val.label = "Animated time (seconds)"
    val.location = (-900, -500)
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


def animated_reference_material(name, image, *, uv_scale=(1.0, 1.0), tint=(1.0, 1.0, 1.0),
                                roughness=0.25, coat=0.0, ior=1.45,
                                bump_strength=0.12, noise_scale=18.0,
                                drift=(0.0025, 0.0012), frames=300,
                                mix_color=None, mix_factor=0.0):
    mat, nt, bsdf, out = new_material(name)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-1100, 100)
    time_val = make_time_value(nt, frames=frames, start=0.0, end=10.0)
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MULTIPLY"
    mx.inputs[1].default_value = drift[0]
    mx.location = (-700, -420)
    my = nt.nodes.new("ShaderNodeMath")
    my.operation = "MULTIPLY"
    my.inputs[1].default_value = drift[1]
    my.location = (-700, -580)
    combine = nt.nodes.new("ShaderNodeCombineXYZ")
    combine.location = (-500, -480)
    nt.links.new(time_val.outputs[0], mx.inputs[0])
    nt.links.new(time_val.outputs[0], my.inputs[0])
    nt.links.new(mx.outputs[0], combine.inputs["X"])
    nt.links.new(my.outputs[0], combine.inputs["Y"])
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.location = (-700, 120)
    mapping.inputs["Scale"].default_value = (uv_scale[0], uv_scale[1], 1.0)
    nt.links.new(coord.outputs["UV"], mapping.inputs["Vector"])
    nt.links.new(combine.outputs["Vector"], mapping.inputs["Location"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (-450, 160)
    tex.image = image
    tex.interpolation = "Linear"
    tex.extension = "EXTEND"
    nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    mix_rgb = nt.nodes.new("ShaderNodeMixRGB")
    mix_rgb.blend_type = "MULTIPLY"
    mix_rgb.inputs["Fac"].default_value = 1.0
    mix_rgb.inputs["Color2"].default_value = (*tint, 1.0)
    mix_rgb.location = (-150, 160)
    nt.links.new(tex.outputs["Color"], mix_rgb.inputs["Color1"])
    if mix_color is not None:
        mix_flat = nt.nodes.new("ShaderNodeMixRGB")
        mix_flat.blend_type = "MIX"
        mix_flat.inputs["Fac"].default_value = mix_factor
        mix_flat.inputs["Color2"].default_value = (*mix_color, 1.0)
        mix_flat.location = (80, 160)
        nt.links.new(mix_rgb.outputs["Color"], mix_flat.inputs["Color1"])
        nt.links.new(mix_flat.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        nt.links.new(mix_rgb.outputs["Color"], bsdf.inputs["Base Color"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = noise_scale
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.6
    noise.location = (-450, -180)
    nt.links.new(coord.outputs["Generated"], noise.inputs["Vector"])
    nt.links.new(time_val.outputs[0], noise.inputs["W"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.04
    bump.location = (-100, -160)
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "Metallic", 0.0)
    set_input(bsdf, "Coat Weight", coat)
    set_input(bsdf, "Coat Roughness", 0.08)
    set_input(bsdf, "IOR", ior)
    return mat


def procedural_material(name, color_a, color_b, *, scale=6.0, roughness=0.8,
                        bump_strength=0.15, frames=300, animate=False, detail=3.0):
    mat, nt, bsdf, out = new_material(name)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-900, 100)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    noise.inputs["Roughness"].default_value = 0.65
    noise.location = (-650, 100)
    nt.links.new(coord.outputs["Generated"], noise.inputs["Vector"])
    if animate:
        time_val = make_time_value(nt, frames=frames, start=0.0, end=10.0)
        nt.links.new(time_val.outputs[0], noise.inputs["W"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-400, 120)
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (*color_a, 1.0)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*color_b, 1.0)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.08
    bump.location = (-150, -120)
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "Metallic", 0.0)
    return mat


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def get_soft_edge_mask():
    """Generated 128x128 alpha mask with smoothly faded rectangle edges."""
    name = "FW_SoftEdgeMask"
    image = bpy.data.images.get(name)
    if image is not None:
        return image
    size = 128
    image = bpy.data.images.new(name, width=size, height=size, alpha=True, float_buffer=False)
    image.colorspace_settings.name = "Non-Color"
    image.alpha_mode = "STRAIGHT"
    pixels = []
    for y in range(size):
        v = (y + 0.5) / size
        fy = smoothstep(0.0, 0.28, v) * smoothstep(0.0, 0.28, 1.0 - v)
        for x in range(size):
            u = (x + 0.5) / size
            fx = smoothstep(0.0, 0.28, u) * smoothstep(0.0, 0.28, 1.0 - u)
            pixels.extend((1.0, 1.0, 1.0, fx * fy))
    image.pixels.foreach_set(pixels)
    image.update()
    try:
        image.pack()
    except Exception:
        pass
    return image


def noise_alpha_emission_material(name, color_a, color_b, *, alpha_scale=0.5,
                                  strength=1.5, noise_scale=5.0, frames=300,
                                  contrast=(0.35, 0.75)):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (700, 0)
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    transparent.location = (250, -180)
    emission = nt.nodes.new("ShaderNodeEmission")
    emission.location = (250, 120)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.location = (480, 0)
    nt.links.new(transparent.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emission.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-900, 100)
    time_val = make_time_value(nt, frames=frames, start=0.0, end=10.0)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = noise_scale
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.7
    noise.inputs["Distortion"].default_value = 0.35
    noise.location = (-650, 100)
    nt.links.new(coord.outputs["Generated"], noise.inputs["Vector"])
    nt.links.new(time_val.outputs[0], noise.inputs["W"])
    alpha_ramp = nt.nodes.new("ShaderNodeValToRGB")
    alpha_ramp.location = (-400, -120)
    alpha_ramp.color_ramp.elements[0].position = contrast[0]
    alpha_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    alpha_ramp.color_ramp.elements[1].position = contrast[1]
    alpha_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(noise.outputs["Fac"], alpha_ramp.inputs["Fac"])
    mask_tex = nt.nodes.new("ShaderNodeTexImage")
    mask_tex.image = get_soft_edge_mask()
    mask_tex.interpolation = "Linear"
    mask_tex.extension = "CLIP"
    mask_tex.location = (-650, -320)
    nt.links.new(coord.outputs["UV"], mask_tex.inputs["Vector"])
    mask_mul = nt.nodes.new("ShaderNodeMath")
    mask_mul.operation = "MULTIPLY"
    mask_mul.location = (-350, -280)
    nt.links.new(alpha_ramp.outputs["Color"], mask_mul.inputs[0])
    nt.links.new(mask_tex.outputs["Alpha"], mask_mul.inputs[1])
    alpha_mul = nt.nodes.new("ShaderNodeMath")
    alpha_mul.operation = "MULTIPLY"
    alpha_mul.inputs[1].default_value = alpha_scale
    alpha_mul.location = (-120, -120)
    nt.links.new(mask_mul.outputs[0], alpha_mul.inputs[0])
    nt.links.new(alpha_mul.outputs[0], mix.inputs[0])
    color_ramp = nt.nodes.new("ShaderNodeValToRGB")
    color_ramp.location = (-400, 180)
    color_ramp.color_ramp.elements[0].position = 0.2
    color_ramp.color_ramp.elements[0].color = (*color_a, 1.0)
    color_ramp.color_ramp.elements[1].position = 0.8
    color_ramp.color_ramp.elements[1].color = (*color_b, 1.0)
    nt.links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
    nt.links.new(color_ramp.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = strength
    return mat


def disable_visibility(obj):
    for attr in ("visible_shadow", "visible_diffuse", "visible_glossy",
                 "visible_transmission", "visible_volume_scatter"):
        try_set(obj, attr, False)
    try_set(obj, "is_shadow_catcher", False)
    try_set(obj, "visible_camera", True)


def create_plane(name, location, rotation, scale, material, *, no_shadow=False):
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    obj.scale = scale
    obj.data.materials.append(material)
    if no_shadow:
        disable_visibility(obj)
    return obj


def create_cube(name, location, scale, material, *, bevel=0.0, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        try:
            obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
        except Exception:
            pass
    return obj


def create_cylinder(name, location, radius, depth, material, *, vertices=12, bevel=0.0, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def create_cone(name, location, radius1, radius2, depth, material, *, vertices=8):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def create_ico(name, location, radius, material, *, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def create_grid_mesh(name, x_range, y_range, nx, ny, height_fn, material, *, uv_bounds=None):
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
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    if uv_bounds:
        x0, x1, y0, y1 = uv_bounds
        uv = mesh.uv_layers.new(name="UVMap")
        for poly in mesh.polygons:
            for li in poly.loop_indices:
                vi = mesh.loops[li].vertex_index
                co = mesh.vertices[vi].co
                uv.data[li].uv = ((co.x - x0) / (x1 - x0), (co.y - y0) / (y1 - y0))
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    return obj


def create_curve(name, points, material, *, bevel_depth=0.03):
    curve = bpy.data.curves.new(name + "Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 1
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def keyframe_location(obj, frame_locations, *, linear=True):
    for frame, loc in frame_locations:
        obj.location = loc
        obj.keyframe_insert(data_path="location", frame=frame)
    if linear:
        linearize_fcurves(obj)


def keyframe_light_flicker(light, base_energy, rng, frames=300):
    for frame in range(1, frames + 1, 30):
        light.data.energy = base_energy * (0.72 + 0.28 * rng.random())
        light.data.keyframe_insert(data_path="energy", frame=frame)
    linearize_fcurves(light.data)


def setup_render(scene, *, width, height, samples, fps, frames):
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
    scene.render.filepath = "//frames/frame_"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.unit_settings.system = "METRIC"
    scene.render.use_stamp = False


def create_world(scene, color, strength):
    world = bpy.data.worlds.new("FW_World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (*color, 1.0)
    bg.inputs["Strength"].default_value = strength
    scene.world = world


def create_camera(scene, frames=300):
    bpy.ops.object.camera_add(location=(0.0, -12.0, 3.0))
    cam = bpy.context.object
    cam.name = "FW_Camera"
    cam.data.type = "PERSP"
    cam.data.lens = 35.0
    cam.data.sensor_width = 36.0
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.clip_start = 0.1
    cam.data.clip_end = 200.0
    cam.data.dof.use_dof = False
    target = Vector((0.0, 0.0, 2.5))
    positions = [
        (1, (0.0, -12.0, 3.0)),
        (frames // 2, (0.45, -11.0, 2.9)),
        (frames, (0.0, -10.0, 2.8)),
    ]
    for frame, loc in positions:
        cam.location = loc
        direction = target - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert(data_path="location", frame=frame)
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)
    scene.camera = cam
    return cam


def create_backplate(scene, image, name):
    mat = bpy.data.materials.new(name + "_Emission")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Linear"
    emission = nt.nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.0
    nt.links.new(tex.outputs["Color"], emission.inputs["Color"])
    nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])
    obj = create_plane(
        name,
        (0.0, 30.0, 3.0),
        (math.radians(90), 0.0, 0.0),
        (30.0, 16.875, 1.0),
        mat,
        no_shadow=True,
    )
    return obj


def create_sun(scene, name, color, energy, rotation):
    bpy.ops.object.light_add(type="SUN", location=(0.0, 0.0, 12.0))
    obj = bpy.context.object
    obj.name = name
    obj.data.color = color
    obj.data.energy = energy
    obj.data.angle = math.radians(2.0)
    obj.rotation_euler = rotation
    return obj


def create_area_light(name, color, energy, location, rotation, size=2.0):
    bpy.ops.object.light_add(type="AREA", location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.color = color
    obj.data.energy = energy
    obj.data.shape = "RECTANGLE"
    obj.data.size = size
    obj.data.size_y = size * 2.0
    obj.rotation_euler = rotation
    return obj


def load_reference(path):
    image = bpy.data.images.load(str(path), check_existing=True)
    image.colorspace_settings.name = "sRGB"
    image.alpha_mode = "NONE"
    return image


def create_ground(name, image, *, z=0.0, location=(0.0, 5.0, 0.0), size=(60.0, 40.0),
                  uv_scale=(1.0, 0.5), tint=(1.0, 1.0, 1.0), roughness=0.2,
                  coat=0.5, ior=1.45, bump_strength=0.12, noise_scale=18.0,
                  drift=(0.0025, 0.0012), frames=300):
    mat = animated_reference_material(
        name + "_Material", image, uv_scale=uv_scale, tint=tint,
        roughness=roughness, coat=coat, ior=ior,
        bump_strength=bump_strength, noise_scale=noise_scale,
        drift=drift, frames=frames,
    )
    return create_plane(name, (location[0], location[1], z), (0, 0, 0),
                        (size[0] / 2.0, size[1] / 2.0, 1.0), mat)


def build_alpine(scene, image, rng, frames):
    create_world(scene, (0.18, 0.24, 0.30), 0.35)
    create_sun(scene, "FW_Alpine_Sun", (1.0, 0.78, 0.55), 2.2,
               (math.radians(35), 0.0, math.radians(-35)))
    create_ground("FW_Alpine_Lake", image, z=0.02, uv_scale=(1.0, 0.5),
                  tint=(0.88, 0.94, 1.0), roughness=0.08, coat=1.0,
                  ior=1.33, bump_strength=0.16, noise_scale=24.0,
                  drift=(0.0035, 0.0010))
    rock = procedural_material("FW_Alpine_Rock", (0.10, 0.11, 0.12), (0.34, 0.33, 0.30),
                               scale=9.0, roughness=0.9, bump_strength=0.28)
    pine = procedural_material("FW_Alpine_Pine", (0.012, 0.038, 0.020), (0.04, 0.10, 0.05),
                               scale=7.0, roughness=0.95, bump_strength=0.18)
    trunk = procedural_material("FW_Alpine_Trunk", (0.06, 0.035, 0.02), (0.14, 0.09, 0.05),
                                scale=8.0, roughness=1.0, bump_strength=0.2)
    for i in range(14):
        x = rng.uniform(-14, 14)
        y = rng.uniform(-2, 8)
        s = rng.uniform(0.7, 1.7)
        create_cylinder(f"FW_PineTrunk_{i:02d}", (x, y, s), 0.07 * s, 2.0 * s, trunk, vertices=8)
        for k in range(4):
            cone = create_cone(f"FW_PineCone_{i:02d}_{k}", (x, y, (1.55 + k * 0.72) * s),
                        (0.92 - k * 0.16) * s, 0.0, (2.1 - k * 0.25) * s, pine, vertices=12)
            bpy.context.view_layer.objects.active = cone
            cone.select_set(True)
            bpy.ops.object.shade_smooth()
    for i in range(12):
        x = rng.uniform(-16, 16)
        y = rng.uniform(-3, 4)
        r = rng.uniform(0.18, 0.55)
        obj = create_ico(f"FW_Rock_{i:02d}", (x, y, r * 0.55), r, rock, subdivisions=2)
        obj.scale = (rng.uniform(0.8, 1.6), rng.uniform(0.6, 1.2), rng.uniform(0.4, 0.9))
    mist = noise_alpha_emission_material("FW_Alpine_Mist", (0.55, 0.65, 0.72),
                                          (0.95, 0.97, 1.0), alpha_scale=0.07,
                                          strength=0.6, noise_scale=3.0,
                                          contrast=(0.25, 0.8), frames=frames)
    for i in range(5):
        x = rng.uniform(-12, 12)
        y = rng.uniform(2, 12)
        plane = create_plane(f"FW_MistPlane_{i:02d}", (x, y, rng.uniform(1.2, 3.0)),
                             (math.radians(90), 0, 0),
                             (rng.uniform(5, 10), rng.uniform(1.5, 3.0), 1.0),
                             mist, no_shadow=True)
        keyframe_location(plane, [(1, (x, y, plane.location.z)),
                                  (frames, (x + rng.uniform(-2, 2), y, plane.location.z))])


def build_neon(scene, image, rng, frames):
    create_world(scene, (0.015, 0.02, 0.04), 0.45)
    create_sun(scene, "FW_Neon_Fill", (0.35, 0.45, 0.75), 0.35,
               (math.radians(55), 0.0, math.radians(20)))
    create_ground("FW_Wet_Pavement", image, z=0.02, uv_scale=(1.0, 0.5),
                  tint=(0.72, 0.82, 1.0), roughness=0.045, coat=1.0,
                  ior=1.33, bump_strength=0.07, noise_scale=30.0,
                  drift=(0.0015, 0.0035))
    rain_mat = emission_material("FW_Rain_Streak", (0.72, 0.88, 1.0), strength=1.2, alpha=0.28)
    for i in range(130):
        x = rng.uniform(-16, 16)
        y = rng.uniform(-6, 18)
        z0 = rng.uniform(3, 12)
        length = rng.uniform(0.4, 1.0)
        obj = create_cylinder(f"FW_Rain_{i:03d}", (x, y, z0), 0.006, length, rain_mat,
                              vertices=6)
        obj.scale = (1.0, 1.0, 1.0)
        obj.rotation_euler = (0.0, rng.uniform(-0.05, 0.05), 0.0)
        disable_visibility(obj)
        keyframe_location(obj, [(1, (x, y, z0)), (frames, (x + rng.uniform(-0.4, 0.4), y, -1.0))])
    steam = noise_alpha_emission_material("FW_Neon_Steam", (0.35, 0.45, 0.7),
                                           (0.85, 0.9, 1.0), alpha_scale=0.07,
                                           strength=0.6, noise_scale=4.0,
                                           contrast=(0.3, 0.85), frames=frames)
    for i in range(4):
        x = rng.uniform(-7, 7)
        y = rng.uniform(2, 10)
        plane = create_plane(f"FW_Steam_{i:02d}", (x, y, rng.uniform(1.0, 3.0)),
                             (math.radians(90), 0, 0),
                             (rng.uniform(2.0, 4.5), rng.uniform(1.5, 3.0), 1.0),
                             steam, no_shadow=True)
        keyframe_location(plane, [(1, (x, y, plane.location.z)),
                                  (frames, (x + rng.uniform(-1.5, 1.5), y, plane.location.z + 1.0))])
    colors = [(0.04, 0.65, 1.0), (1.0, 0.08, 0.45), (1.0, 0.48, 0.06), (0.42, 0.12, 0.95)]
    for i, color in enumerate(colors):
        x = rng.choice([-1, 1]) * rng.uniform(4.5, 9.0)
        z = rng.uniform(3.0, 6.5)
        sign_mat = emission_material(f"FW_NeonSign_{i:02d}", color, strength=0.65)
        create_cube(f"FW_NeonSignBox_{i:02d}", (x, 9.0, z),
                    (0.16, 0.06, rng.uniform(1.0, 1.8)), sign_mat, bevel=0.02)
        light = create_area_light(f"FW_NeonLight_{i:02d}", color, 60.0,
                                  (x, 8.0, z), (math.radians(-90), 0, 0), size=1.2)
        keyframe_light_flicker(light, 60.0, rng, frames=frames)


def build_sahara(scene, image, rng, frames):
    create_world(scene, (0.55, 0.35, 0.22), 0.45)
    create_sun(scene, "FW_Sahara_Sun", (1.0, 0.62, 0.32), 2.8,
               (math.radians(18), 0.0, math.radians(-25)))
    dune_mat = animated_reference_material(
        "FW_Sahara_Dune_Material", image, uv_scale=(1.0, 0.5),
        tint=(0.94, 0.94, 0.94), roughness=0.95, coat=0.0, ior=1.4,
        bump_strength=0.28, noise_scale=24.0,
        drift=(0.0025, 0.0006), frames=frames,
        mix_color=(0.52, 0.44, 0.36), mix_factor=0.42,
    )
    def dune_height(x, y):
        return (math.sin(x * 0.22) * 0.9 + math.sin(y * 0.28 + x * 0.08) * 0.55 +
                math.sin(x * 0.6 - y * 0.18) * 0.22 - 0.35)
    create_grid_mesh("FW_Dune_Foreground", (-30, 30), (-6, 24), 90, 45,
                     dune_height, dune_mat, uv_bounds=(-30, 30, -6, 24))
    create_ground("FW_Sahara_Background_Ground", image, z=-0.35,
                  uv_scale=(1.0, 0.5), tint=(1.05, 0.92, 0.78),
                  roughness=0.9, coat=0.0, ior=1.4,
                  bump_strength=0.10, noise_scale=12.0,
                  drift=(0.004, 0.0008))
    sand_particle = emission_material("FW_Sand_Grain", (1.0, 0.72, 0.38),
                                       strength=0.8, alpha=0.55)
    for i in range(90):
        x0 = rng.uniform(-22, 22)
        y = rng.uniform(-2, 16)
        z = rng.uniform(0.3, 3.2)
        obj = create_ico(f"FW_SandGrain_{i:03d}", (x0, y, z),
                         rng.uniform(0.012, 0.032), sand_particle, subdivisions=1)
        disable_visibility(obj)
        keyframe_location(obj, [(1, (x0, y, z)),
                                (frames, (x0 + rng.uniform(18, 32), y + rng.uniform(-1, 1), z))])
    shimmer = noise_alpha_emission_material("FW_Heat_Shimmer", (0.9, 0.6, 0.35),
                                             (1.0, 0.85, 0.55), alpha_scale=0.04,
                                             strength=0.4, noise_scale=8.0,
                                             contrast=(0.35, 0.8), frames=frames)
    plane = create_plane("FW_Heat_Plane", (0.0, 14.0, 2.0),
                         (math.radians(90), 0, 0), (24.0, 5.0, 1.0),
                         shimmer, no_shadow=True)
    keyframe_location(plane, [(1, (0.0, 14.0, 2.0)), (frames, (1.5, 14.0, 2.0))])


def build_iceland(scene, image, rng, frames):
    create_world(scene, (0.02, 0.04, 0.08), 0.55)
    create_sun(scene, "FW_Iceland_Moon", (0.45, 0.65, 0.85), 0.45,
               (math.radians(65), 0.0, math.radians(30)))
    create_ground("FW_Black_Sand", image, z=0.02, uv_scale=(1.0, 0.5),
                  tint=(0.55, 0.68, 0.82), roughness=0.16, coat=0.8,
                  ior=1.33, bump_strength=0.09, noise_scale=22.0,
                  drift=(0.0018, 0.0022))
    basalt = procedural_material("FW_Basalt", (0.025, 0.035, 0.04), (0.18, 0.22, 0.25),
                                  scale=8.0, roughness=0.85, bump_strength=0.25)
    for i in range(11):
        x = -10.0 + i * 0.72 + rng.uniform(-0.12, 0.12)
        y = rng.uniform(-1, 6)
        h = rng.uniform(1.8, 5.2)
        create_cylinder(f"FW_BasaltColumn_{i:02d}", (x, y, h / 2.0),
                        rng.uniform(0.28, 0.46), h, basalt, vertices=8,
                        bevel=0.06, rotation=(0, 0, rng.uniform(0, math.pi)))
    aurora = noise_alpha_emission_material("FW_Aurora_Curtain", (0.25, 0.08, 0.65),
                                            (0.12, 1.0, 0.52), alpha_scale=0.22,
                                            strength=1.5, noise_scale=2.6,
                                            contrast=(0.40, 0.74), frames=frames)
    plane = create_plane("FW_Aurora_Plane", (0.0, 25.0, 10.0),
                         (math.radians(90), 0, 0), (26.0, 9.0, 1.0),
                         aurora, no_shadow=True)
    keyframe_location(plane, [(1, (0.0, 25.0, 10.0)), (frames, (2.0, 25.0, 10.5))])
    star = emission_material("FW_Star", (0.85, 0.92, 1.0), strength=2.5)
    for i in range(110):
        x = rng.uniform(-24, 24)
        y = rng.uniform(18, 29)
        z = rng.uniform(7, 18)
        obj = create_ico(f"FW_Star_{i:03d}", (x, y, z),
                         rng.uniform(0.012, 0.032), star, subdivisions=1)
        disable_visibility(obj)
    foam = emission_material("FW_Foam", (0.78, 0.92, 1.0), strength=0.45, alpha=0.12)
    for j in range(3):
        pts = []
        for i in range(60):
            x = -24.0 + 48.0 * i / 59.0
            pts.append((x, 4.0 + j * 1.6 + math.sin(i * 0.35 + j) * 0.28 + math.sin(i * 0.11 + j * 2) * 0.12, 0.07))
        curve = create_curve(f"FW_FoamLine_{j}", pts, foam, bevel_depth=0.015)
        disable_visibility(curve)
        keyframe_location(curve, [(1, (0.0, 0.0, 0.0)),
                                  (frames, (0.0, -2.0 - j * 0.5, 0.0))])


def build_temple(scene, image, rng, frames):
    create_world(scene, (0.10, 0.16, 0.08), 0.45)
    create_sun(scene, "FW_Temple_Sun", (1.0, 0.86, 0.55), 1.9,
               (math.radians(28), 0.0, math.radians(-40)))
    create_ground("FW_Temple_Floor", image, z=0.0, uv_scale=(1.0, 0.5),
                  tint=(0.82, 0.95, 0.78), roughness=0.78, coat=0.1,
                  ior=1.4, bump_strength=0.14, noise_scale=14.0,
                  drift=(0.0012, 0.0010))
    stone = procedural_material("FW_Temple_Stone", (0.10, 0.11, 0.09), (0.38, 0.36, 0.28),
                                 scale=7.0, roughness=0.9, bump_strength=0.22)
    moss = procedural_material("FW_Temple_Moss", (0.04, 0.12, 0.03), (0.20, 0.42, 0.12),
                                scale=9.0, roughness=1.0, bump_strength=0.2)
    for i in range(14):
        x = rng.uniform(-10, 10)
        y = rng.uniform(-2, 8)
        sx, sy, sz = rng.uniform(0.6, 1.7), rng.uniform(0.3, 0.8), rng.uniform(0.6, 1.5)
        create_cube(f"FW_TempleBlock_{i:02d}", (x, y, sz / 2.0),
                    (sx, sy, sz), stone, bevel=0.05,
                    rotation=(0, 0, rng.uniform(-0.35, 0.35)))
        if rng.random() < 0.6:
            create_plane(f"FW_MossPatch_{i:02d}", (x, y, sz + 0.012),
                         (0, 0, rng.uniform(-0.3, 0.3)),
                         (sx * 0.45, sy * 0.42, 1.0), moss, no_shadow=True)
    for x in (-3.5, 3.5):
        create_cube("FW_TemplePillar", (x, 7.0, 2.0), (0.65, 0.65, 4.0), stone, bevel=0.06)
    create_cube("FW_TempleLintel", (0.0, 7.0, 4.2), (8.0, 0.8, 0.8), stone, bevel=0.06)
    waterfall = noise_alpha_emission_material("FW_Waterfall", (0.35, 0.65, 0.85),
                                               (0.92, 0.98, 1.0), alpha_scale=0.25,
                                               strength=0.8, noise_scale=11.0,
                                               contrast=(0.36, 0.76), frames=frames)
    wf = create_plane("FW_Waterfall_Plane", (-8.0, 18.0, 3.5),
                      (math.radians(90), 0, 0), (2.2, 6.0, 1.0),
                      waterfall, no_shadow=True)
    keyframe_location(wf, [(1, (-8.0, 18.0, 3.5)), (frames, (-7.5, 18.0, 3.2))])
    dust = emission_material("FW_Dust_Mote", (1.0, 0.86, 0.55), strength=1.0, alpha=0.35)
    for i in range(85):
        x = rng.uniform(-12, 12)
        y = rng.uniform(-2, 12)
        z = rng.uniform(0.5, 7.0)
        obj = create_ico(f"FW_Dust_{i:03d}", (x, y, z),
                         rng.uniform(0.012, 0.03), dust, subdivisions=1)
        disable_visibility(obj)
        keyframe_location(obj, [(1, (x, y, z)),
                                (frames // 2, (x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.4, 0.4), z + rng.uniform(-0.3, 0.6))),
                                (frames, (x + rng.uniform(-1.2, 1.2), y + rng.uniform(-0.6, 0.6), z + rng.uniform(-0.5, 0.8)))])


BUILDERS = {
    1: build_alpine,
    2: build_neon,
    3: build_sahara,
    4: build_iceland,
    5: build_temple,
}


def build_scene(ref, args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.name = f"FiveWorlds_{ref['index']:02d}_{ref['slug']}"
    setup_render(scene, width=args.width, height=args.height,
                 samples=args.samples, fps=args.fps, frames=args.frames)
    image = load_reference(ROOT / ref["reference"])
    create_backplate(scene, image, f"FW_Reference_Backplate_{ref['index']:02d}")
    create_camera(scene, frames=args.frames)
    rng = random.Random(SEED + ref["index"] * 997)
    BUILDERS[ref["index"]](scene, image, rng, args.frames)
    scene.frame_set(1)
    bpy.ops.file.pack_all()
    blend_path = args.out / f"FiveWorlds_Blender_{ref['index']:02d}_{ref['slug']}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    return {
        "index": ref["index"],
        "name": ref["name"],
        "slug": ref["slug"],
        "reference": ref["reference"],
        "reference_original": ref["reference_original"],
        "reference_sha256": hashlib.sha256((ROOT / ref["reference"]).read_bytes()).hexdigest(),
        "motion": ref["motion"],
        "blend": str(blend_path.relative_to(ROOT)),
        "blend_bytes": blend_path.stat().st_size,
        "blend_sha256": hashlib.sha256(blend_path.read_bytes()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=int, default=0, help="1-5; 0 builds all")
    parser.add_argument("--out", default=str(ROOT / "output"))
    parser.add_argument("--manifest", default=str(ROOT / "docs/FIVE_WORLDS_BLENDER_MANIFEST.json"))
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--frames", type=int, default=300)
    args = parser.parse_args()
    args.out = Path(args.out).resolve()
    args.manifest = str(Path(args.manifest).resolve())
    args.out.mkdir(parents=True, exist_ok=True)
    selected = REFS if args.scene == 0 else [r for r in REFS if r["index"] == args.scene]
    if not selected:
        raise SystemExit(f"Invalid --scene {args.scene}")
    entries = [build_scene(ref, args) for ref in selected]
    manifest = {
        "revision": REVISION,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "blender": bpy.app.version_string,
        "engine": "CYCLES",
        "device": "CPU",
        "spec": {
            "width": args.width, "height": args.height,
            "fps": args.fps, "frames_per_scene": args.frames,
            "duration_seconds": args.frames / args.fps,
            "samples": args.samples,
            "denoising": "OpenImageDenoise RGB_ALBEDO_NORMAL",
            "view_transform": "AgX - Medium High Contrast",
        },
        "route": "Blender Cycles CPU scenes rendered in 15 GitHub Actions shards, like the Kerala animation workflow",
        "reference_usage": "Packed photographic backplates plus animated UV-distorted ground/reflection textures; procedural 3D foreground geometry and physical lights",
        "scenes": entries,
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"manifest": str(manifest_path), "scenes": [e["blend"] for e in entries]}, indent=2))


if __name__ == "__main__":
    main()
