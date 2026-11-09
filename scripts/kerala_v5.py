"""Kerala v5.1 — single-sun, shadow-shaped atmospheric scattering.

Replaces the rejected v5.0 emissive-cone/spotlight rig.  There are no emissive
beam meshes and no shaft spotlights.  One directional sun illuminates one
non-emissive, height-faded mist volume; a shadow-only cloud aperture and the
actual coconut/broadleaf geometry occlude that sun.  The effect disappears when
the mist or the sun is disabled, which is checked in the proof renders.
"""
import math
import bpy
from mathutils import Vector, Matrix

REVISION = 'kerala-v5.1-single-sun-rays'
SUN_DIRECTION = Vector((-.48, -.64, -.60)).normalized()


def _collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def _move(o, c):
    for old in list(o.users_collection):
        old.objects.unlink(o)
    c.objects.link(o)


def _aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()


def _math(nt, op, a=None, b=None):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _ao_grime(mat, factor):
    nt = mat.node_tree
    p = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not p:
        return
    link = next((l for l in nt.links if l.to_node == p and l.to_socket.name == 'Base Color'), None)
    if not link:
        return
    src = link.from_socket
    ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
    ao.samples = 8
    ao.inputs['Distance'].default_value = .35
    mx = nt.nodes.new('ShaderNodeMixRGB')
    mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = factor
    nt.links.new(src, mx.inputs[1])
    nt.links.new(ao.outputs['Color'], mx.inputs[2])
    nt.links.new(mx.outputs['Color'], p.inputs['Base Color'])


def _bump_detail(mat, scale, strength, distance):
    nt = mat.node_tree
    p = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not p:
        return
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = 5
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = distance
    old = next((l.from_socket for l in nt.links if l.to_node == p and l.to_socket.name == 'Normal'), None)
    if old:
        nt.links.new(old, bp.inputs['Normal'])
    nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], p.inputs['Normal'])


def _make_mist(atmo):
    m = bpy.data.materials.new('MAT_V51_SingleSun_Mist')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    scatter = nt.nodes.new('ShaderNodeVolumeScatter')
    scatter.inputs['Color'].default_value = (.88, .91, .94, 1)
    scatter.inputs['Anisotropy'].default_value = .55
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
    # Smooth height falloff: damp air near the paddy, clear above the crowns.
    h = nt.nodes.new('ShaderNodeMapRange')
    h.inputs['From Min'].default_value = .15
    h.inputs['From Max'].default_value = 21.0
    h.inputs['To Min'].default_value = .005
    h.inputs['To Max'].default_value = 0.0
    h.clamp = True
    nt.links.new(sep.outputs['Z'], h.inputs['Value'])
    nt.links.new(h.outputs['Result'], scatter.inputs['Density'])
    nt.links.new(scatter.outputs['Volume'], out.inputs['Volume'])
    if hasattr(m, 'volume_sampling'):
        m.volume_sampling = 'MULTIPLE_IMPORTANCE'
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 35.0, 14.05))
    o = bpy.context.object
    o.name = 'SM_V51_SingleSun_MistDomain'
    o.scale = (180, 130, 27.9)  # z = .10 .. 28.0 m; does not extend underwater
    o.data.materials.append(m)
    o.display_type = 'WIRE'
    _move(o, atmo)
    return o


def _make_cloud_aperture(atmo):
    """One irregular cloud opening, visible only to shadow rays.

    This is an occluder, not a light and not an emissive beam.  Its feathered
    opening lets the SAME sun through; palms and forest add finer occlusion.
    """
    m = bpy.data.materials.new('MAT_V51_CloudShadow_Aperture')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    transparent = nt.nodes.new('ShaderNodeBsdfTransparent')
    opaque = nt.nodes.new('ShaderNodeBsdfDiffuse')
    opaque.inputs['Color'].default_value = (.04, .04, .04, 1)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    x = _math(nt, 'DIVIDE', sep.outputs['X'], 46.0)
    y = _math(nt, 'DIVIDE', sep.outputs['Y'], 29.0)
    r2 = _math(nt, 'ADD', _math(nt, 'MULTIPLY', x, x), _math(nt, 'MULTIPLY', y, y))
    r = _math(nt, 'SQRT', r2)
    edge = nt.nodes.new('ShaderNodeMapRange')
    edge.inputs['From Min'].default_value = .72
    edge.inputs['From Max'].default_value = 1.18
    edge.inputs['To Min'].default_value = 0.0
    edge.inputs['To Max'].default_value = 1.0
    edge.clamp = True
    nt.links.new(r, edge.inputs['Value'])
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = .045
    noise.inputs['Detail'].default_value = 3
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    perturb = _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', noise.outputs['Fac'], .5), .16)
    # Irregular parallel cloud gaps, not radial spotlight cones.  The same
    # directional sun passes through these gaps and is blocked between them.
    wave = nt.nodes.new('ShaderNodeTexWave')
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs['Scale'].default_value = .030
    wave.inputs['Distortion'].default_value = 2.0
    wave.inputs['Detail'].default_value = 3
    wave.inputs['Detail Scale'].default_value = .7
    nt.links.new(tc.outputs['Object'], wave.inputs['Vector'])
    opening = nt.nodes.new('ShaderNodeMapRange')
    opening.inputs['From Min'].default_value = .45
    opening.inputs['From Max'].default_value = .85
    opening.inputs['To Min'].default_value = 0.0
    opening.inputs['To Max'].default_value = 1.0
    opening.clamp = True
    nt.links.new(wave.outputs['Fac'], opening.inputs['Value'])
    cloud_between_gaps = _math(nt, 'SUBTRACT', 1.0, opening.outputs['Result'])
    opacity = _math(nt, 'MAXIMUM', _math(nt, 'ADD', edge.outputs['Result'], perturb), cloud_between_gaps)
    opacity = _math(nt, 'MAXIMUM', opacity, 0.0)
    lp = nt.nodes.new('ShaderNodeLightPath')
    # Only occlude the nearby mist/field, not the far Ghats; avoids patchy
    # cloud-shadow blobs on distant ridges while keeping local shafts.
    near = nt.nodes.new('ShaderNodeMapRange')
    near.inputs['From Min'].default_value = 95.0
    near.inputs['From Max'].default_value = 170.0
    near.inputs['To Min'].default_value = 1.0
    near.inputs['To Max'].default_value = 0.0
    near.clamp = True
    nt.links.new(lp.outputs['Ray Length'], near.inputs['Value'])
    shadow_opacity = _math(nt, 'MULTIPLY', _math(nt, 'MULTIPLY', opacity, lp.outputs['Is Shadow Ray']), near.outputs['Result'])
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(shadow_opacity, mix.inputs[0])
    nt.links.new(transparent.outputs['BSDF'], mix.inputs[1])
    nt.links.new(opaque.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    bpy.ops.mesh.primitive_plane_add(size=200, location=(20, 65, 30))
    o = bpy.context.object
    o.name = 'SM_V51_CloudShadow_Aperture'
    o.rotation_euler[2] = math.radians(-18)
    o.data.materials.append(m)
    o.display_type = 'WIRE'
    o.visible_camera = False
    o.visible_diffuse = False
    o.visible_glossy = False
    o.visible_transmission = False
    o.visible_volume_scatter = True
    o.visible_shadow = True
    o['role'] = 'Shadow-only cloud occluder; zero emission; not a light source'
    _move(o, atmo)
    return o


def audit_lighting(scene):
    lights = [o for o in scene.objects if o.type == 'LIGHT']
    suns = [o for o in lights if o.data.type == 'SUN']
    spots = [o for o in lights if o.data.type == 'SPOT']
    fake = [o for o in scene.objects if o.name.startswith(('SM_V5_Light_Shaft', 'LGT_V5_GodRay_Shaft'))]
    stray_vents = [o for o in scene.objects if o.name.startswith(('SM_Vent_Cap_StandingSeam', 'SM_Vent_Metal_Rib')) and o.parent is None]
    emissive_volumes = []
    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        for n in mat.node_tree.nodes:
            if n.type in {'VOLUME_PRINCIPLED', 'PRINCIPLED_VOLUME'}:
                sock = n.inputs.get('Emission Strength')
                if sock and sock.default_value > 0:
                    emissive_volumes.append(mat.name)
    result = {
        'revision': scene.get('revision'),
        'sun_count': len(suns),
        'sun_names': [o.name for o in suns],
        'spot_count': len(spots),
        'fake_shaft_objects': [o.name for o in fake],
        'unparented_vent_parts': [o.name for o in stray_vents],
        'emissive_volume_materials': sorted(set(emissive_volumes)),
        'volume_bounces': scene.cycles.volume_bounces,
        'sun_direction_world': list(SUN_DIRECTION),
    }
    result['pass'] = (result['revision'] == REVISION and len(suns) == 1 and
                      not spots and not fake and not emissive_volumes and not stray_vents)
    return result


def apply_v5(samples=32):
    s = bpy.context.scene
    s['revision'] = REVISION
    s['animation_spec'] = '150 frames, 30 fps, 1920x1080, 5.000 s dolly'
    s['lighting_note'] = 'One directional sun; non-emissive mist; cloud/foliage shadow occlusion; no spotlights or beam cones.'
    vl = bpy.context.view_layer
    def exclude(lc):
        if lc.collection.name.startswith('LIB_') or lc.collection.name == 'COL_AssetLibrary':
            lc.exclude = True
        for ch in lc.children:
            exclude(ch)
    exclude(vl.layer_collection)
    atmo = _collection('COL_Atmosphere')
    cams = _collection('COL_Cameras')

    # Defensive cleanup also handles a file that already contains rejected v5.0.
    for o in list(bpy.data.objects):
        if o.name.startswith(('SM_V5_Light_Shaft', 'LGT_V5_GodRay_Shaft',
                              'SM_V5_GodRay_Medium', 'SM_V5_Cloud_Gobo',
                              'SM_V51_', 'CAM_V5_Dolly_1080p')):
            bpy.data.objects.remove(o, do_unlink=True)

    for n in s.world.node_tree.nodes:
        if n.type == 'BACKGROUND':
            n.inputs['Strength'].default_value = .15
        if n.type == 'HUE_SAT':
            n.inputs['Value'].default_value = .95
    sun = bpy.data.objects.get('LGT_Q_SoftMonsoonSun')
    if sun is None:
        raise RuntimeError('Expected baseline sun missing')
    sun.name = 'LGT_V51_SingleSun'
    sun.data.energy = 8.0
    sun.data.angle = math.radians(.65)
    sun.data.color = (1.0, .93, .82)
    sun.rotation_euler = SUN_DIRECTION.to_track_quat('-Z', 'Y').to_euler()
    sun.visible_volume_scatter = True
    fill = bpy.data.objects.get('LGT_Q_Fill_SkyBounce')
    if fill:
        fill.data.energy = 12
        fill.data.color = (.78, .85, .95)
        fill.visible_volume_scatter = False  # fill must not manufacture rays

    # Reduce the old opaque-looking fog wall; keep distant depth separation.
    for mn, density in [('MAT_V4_Valley_Haze', .0002), ('MAT_Q_Mist_Bank_Volume', .0004)]:
        m = bpy.data.materials.get(mn)
        if m:
            for n in m.node_tree.nodes:
                if n.type in {'VOLUME_PRINCIPLED', 'PRINCIPLED_VOLUME'}:
                    n.inputs['Density'].default_value = density
                    n.inputs['Emission Strength'].default_value = 0
                if n.type == 'MAP_RANGE' and n.inputs['To Max'].default_value < .03:
                    n.inputs['To Max'].default_value = .0012
    for o in bpy.data.objects:
        if o.name.startswith(('SM_Q_Mist_Bank','SM_V4_Valley_Haze')):
            o.hide_render = True  # old hard fog banks caused bright horizon patches
    # Calm distant sunlit ridges/marsh so cloud shadows do not read as white blobs.
    for mn in ['MAT_Q_Ghat_ForestRock', 'MAT_Q_Distant_Ghat']:
        m = bpy.data.materials.get(mn)
        if m and m.use_nodes:
            nt = m.node_tree; p = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if p:
                link = next((l for l in nt.links if l.to_node == p and l.to_socket.name == 'Base Color'), None)
                if link:
                    mx = nt.nodes.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = .55; mx.inputs[2].default_value = (.50, .58, .66, 1)
                    src = link.from_socket; nt.links.new(src, mx.inputs[1]); nt.links.new(mx.outputs['Color'], p.inputs['Base Color'])
    marsh = bpy.data.objects.get('SM_V4_Back_Marsh_Ground')
    if marsh:
        mm = bpy.data.materials.new('MAT_V51_Distant_Marsh'); mm.use_nodes = True
        pb = mm.node_tree.nodes['Principled BSDF']; pb.inputs['Base Color'].default_value = (.030, .040, .028, 1); pb.inputs['Roughness'].default_value = .9
        marsh.data.materials.clear(); marsh.data.materials.append(mm)
    _make_mist(atmo)
    _make_cloud_aperture(atmo)

    # Fix the actual floating black grid: unparented roof-vent ribs/caps were
    # left at the origin instead of under the house root. Parent them correctly.
    root = bpy.data.objects.get('SM_Tharavad_House_Root')
    if root:
        for o in bpy.data.objects:
            if o.name.startswith(('SM_Vent_Cap_StandingSeam', 'SM_Vent_Metal_Rib')) and o.parent is None:
                o.parent = root
                o.matrix_parent_inverse = Matrix.Identity(4)

    # Give near coconut crowns camera headroom.
    # Keep all 26 uploaded coconuts, but give the near crowns camera headroom.
    for name, loc, scale in [
        ('SM_UserCoconut_Palm_00', (-12.0, 34.0, -.04), .90),
        ('SM_UserCoconut_Palm_01', (13.5, 20.0, -.04), .95),
        ('SM_UserCoconut_Palm_02', (-18.0, 40.0, -.04), .95),
        ('SM_UserCoconut_Palm_03', (20.0, 43.0, -.04), .98),
    ]:
        o = bpy.data.objects.get(name)
        if o:
            o.location = loc
            o.scale = (scale, scale, scale)

    # Preserve the v4 texture improvements, without glow tricks.
    for m in bpy.data.materials:
        n = m.name.lower()
        if any(k in n for k in ['roof', 'tile', 'plaster', 'wood', 'mud', 'earth', 'laterite']):
            _ao_grime(m, .26 if 'roof' in n or 'tile' in n else .18)
            wet = 'mud' in n or 'earth' in n
            _bump_detail(m, 22 if wet else 14, .20, .03 if wet else .018)
    water = bpy.data.materials.get('MAT_Q_Paddy_Water_Shallow')
    if water:
        nt = water.node_tree
        p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        p.inputs['Roughness'].default_value = .075
        p.inputs['IOR'].default_value = 1.333
        w = nt.nodes.new('ShaderNodeTexWave')
        w.inputs['Scale'].default_value = 2.6
        w.inputs['Distortion'].default_value = 3.0
        w.inputs['Detail'].default_value = 3
        bp = nt.nodes.new('ShaderNodeBump')
        bp.inputs['Strength'].default_value = .08
        bp.inputs['Distance'].default_value = .010
        nt.links.new(w.outputs['Fac'], bp.inputs['Height'])
        nt.links.new(bp.outputs['Normal'], p.inputs['Normal'])
    mud = bpy.data.materials.get('MAT_V4_Wet_Scanned_Earth')
    if mud:
        nt = mud.node_tree
        p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 5
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['To Min'].default_value = .25
        mr.inputs['To Max'].default_value = .60
        mr.clamp = True
        nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
        nt.links.new(mr.outputs['Result'], p.inputs['Roughness'])

    s.render.engine = 'CYCLES'
    s.cycles.device = 'CPU'
    s.cycles.samples = samples
    s.cycles.use_adaptive_sampling = True
    s.cycles.adaptive_threshold = .035
    s.cycles.adaptive_min_samples = 8
    s.cycles.use_denoising = True
    s.cycles.denoiser = 'OPENIMAGEDENOISE'
    s.cycles.denoising_input_passes = 'RGB_ALBEDO'
    s.cycles.max_bounces = 6
    s.cycles.diffuse_bounces = 3
    s.cycles.glossy_bounces = 3
    s.cycles.transmission_bounces = 4
    s.cycles.volume_bounces = 0  # crisp single scattering, not glowing multi-scatter cones
    s.cycles.transparent_max_bounces = 16
    s.cycles.caustics_reflective = False
    s.cycles.caustics_refractive = False
    s.cycles.sample_clamp_indirect = 3.0
    s.cycles.volume_step_rate = 1.0
    s.cycles.volume_max_steps = 256
    s.cycles.use_light_tree = True
    s.render.use_persistent_data = False
    s.render.fps = 30
    s.frame_start = 1
    s.frame_end = 150
    s.render.resolution_x = 1920
    s.render.resolution_y = 1080
    s.render.resolution_percentage = 100
    s.view_settings.exposure = .0
    try:
        s.view_settings.look = 'AgX - Base Contrast'
    except Exception:
        pass
    if s.use_nodes and s.node_tree:
        for n in s.node_tree.nodes:
            if n.type == 'GLARE':
                n.mix = -.92  # restrained highlight bloom only; cannot paint rays
                if hasattr(n, 'threshold'):
                    n.threshold = 2.0

    cd = bpy.data.cameras.new('CAM_V5_Dolly_1080p')
    cd.lens = 34
    cd.clip_end = 1200
    cd.dof.use_dof = False
    cam = bpy.data.objects.new('CAM_V5_Dolly_1080p', cd)
    cams.objects.link(cam)
    s.camera = cam
    keys = [(1, (-2.8, -15.0, 1.55), (3.0, 62.0, 3.5), 34),
            (75, (-2.0, -11.5, 1.60), (3.0, 62.0, 3.6), 34.5),
            (150, (-1.0, -8.0, 1.65), (3.2, 63.0, 3.7), 35)]
    for f, loc, tgt, lens in keys:
        cam.location = loc
        _aim(cam, tgt)
        cd.lens = lens
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_euler', frame=f)
        cd.keyframe_insert('lens', frame=f)
    for datablock in (cam, cd):
        for fc in datablock.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.easing = 'EASE_IN_OUT'
    s.frame_set(75)
    audit = audit_lighting(s)
    if not audit['pass']:
        raise RuntimeError(f'Lighting audit failed: {audit}')
    return s
