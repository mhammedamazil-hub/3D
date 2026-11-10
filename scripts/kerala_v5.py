"""Kerala v5.2 — a single sun rising from the Ghats with physical god rays.

The rejected v5.0 emissive cones/spotlights and the ineffective v5.1
object-space aperture are gone.  One animated directional sun rises from behind
the ridge.  Its apparent disc and a warm dawn sky are procedural world shaders;
one non-emissive, height-faded mist volume scatters the light.  A world-space,
shadow-only cloud deck blocks the same sun in irregular lanes, so the bright
shafts are genuine shadow-shaped volumetric scattering.  Disabling the sun, the
mist, or the cloud deck removes the effect — see scripts/proof_kerala_v52.py.
"""
import math
import bpy
from mathutils import Vector, Matrix

REVISION = 'kerala-v5.2-sunrise-godrays'
SUN_AZIMUTH_DEG = 20.0
# frame, apparent elevation above the horizon, sun energy, sun colour
SUN_KEYS = [
    (1,   5.0, 16.0, (1.0, .45, .18)),
    (75,  7.0, 16.0, (1.0, .58, .28)),
    (150, 9.5, 18.0, (1.0, .68, .36)),
]
CAMERA_BG_STRENGTH = .35
LIGHTING_BG_STRENGTH = .008
LIGHTING_BG_KEYS = [(1, .025), (20, .018), (60, .008), (150, .008)]
DISC_DOT_EDGE = (.99994, .99998)
DISC_ADD_COLOR = (14.0, 7.0, 2.0, 1.0)
MIST_DENSITY = .0022
MIST_TOP = 45.0
MIST_ANISOTROPY = .76
CLOUD_PHASE_X = .40
CLOUD_NOISE_SCALE = .012
CLOUD_WARP = 1.0
CLOUD_EDGE = (-.35, -.15)
CLOUD_SHADOW_MAX = 1.0


def _sun_apparent_direction(elevation_deg):
    """Unit vector from the scene toward the visible sun."""
    a = math.radians(SUN_AZIMUTH_DEG)
    e = math.radians(elevation_deg)
    return Vector((math.sin(a) * math.cos(e),
                   math.cos(a) * math.cos(e),
                   math.sin(e))).normalized()


def _sun_travel_direction(elevation_deg):
    """Unit vector in which the directional sunlight travels."""
    return -_sun_apparent_direction(elevation_deg)


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
    """Create a ShaderNodeMath and return its output socket."""
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


def _make_sunrise_world():
    """Replace the HDRI world with a dawn gradient and an animated sun disc."""
    s = bpy.context.scene
    w = s.world
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')

    geo = nt.nodes.new('ShaderNodeNewGeometry')
    up = nt.nodes.new('ShaderNodeVectorMath')
    up.operation = 'DOT_PRODUCT'
    up.inputs[1].default_value = (0.0, 0.0, -1.0)  # Incoming = -view direction
    nt.links.new(geo.outputs['Incoming'], up.inputs[0])
    sky_h = nt.nodes.new('ShaderNodeMapRange')
    sky_h.inputs['From Min'].default_value = -.05
    sky_h.inputs['From Max'].default_value = .32
    sky_h.clamp = True
    nt.links.new(up.outputs['Value'], sky_h.inputs['Value'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .0
    ramp.color_ramp.elements[0].color = (.68, .30, .18, 1)
    mid = ramp.color_ramp.elements.new(.34)
    mid.color = (.42, .29, .32, 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (.11, .14, .23, 1)
    nt.links.new(sky_h.outputs['Result'], ramp.inputs['Fac'])
    gradient = ramp.outputs['Color']

    # World-space sun direction, keyed with the lamp so the disc really rises.
    disc_vec = nt.nodes.new('ShaderNodeCombineXYZ')
    dot = nt.nodes.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    nt.links.new(geo.outputs['Incoming'], dot.inputs[0])
    nt.links.new(disc_vec.outputs['Vector'], dot.inputs[1])
    disc = nt.nodes.new('ShaderNodeMapRange')
    disc.inputs['From Min'].default_value = DISC_DOT_EDGE[0]
    disc.inputs['From Max'].default_value = DISC_DOT_EDGE[1]
    disc.inputs['To Min'].default_value = 0.0
    disc.inputs['To Max'].default_value = 1.0
    disc.clamp = True
    nt.links.new(dot.outputs['Value'], disc.inputs['Value'])
    disc_add = nt.nodes.new('ShaderNodeMixRGB')
    disc_add.blend_type = 'ADD'
    nt.links.new(disc.outputs['Result'], disc_add.inputs[0])
    nt.links.new(gradient, disc_add.inputs[1])
    disc_add.inputs[2].default_value = DISC_ADD_COLOR

    bg_camera = nt.nodes.new('ShaderNodeBackground')
    bg_camera.inputs['Strength'].default_value = CAMERA_BG_STRENGTH
    nt.links.new(disc_add.outputs['Color'], bg_camera.inputs['Color'])
    bg_light = nt.nodes.new('ShaderNodeBackground')
    bg_light.name = 'V52_Lighting_Background'
    bg_light.inputs['Strength'].default_value = LIGHTING_BG_STRENGTH
    nt.links.new(gradient, bg_light.inputs['Color'])
    lp = nt.nodes.new('ShaderNodeLightPath')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0])
    nt.links.new(bg_light.outputs['Background'], mix.inputs[1])
    nt.links.new(bg_camera.outputs['Background'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])

    for frame, elev, _energy, _colour in SUN_KEYS:
        v = -_sun_apparent_direction(elev)  # Incoming points back toward camera
        for axis, value in zip('XYZ', v):
            sock = disc_vec.inputs[axis]
            sock.default_value = value
            sock.keyframe_insert(data_path='default_value', frame=frame)
    for frame, strength in LIGHTING_BG_KEYS:
        sock = bg_light.inputs['Strength']
        sock.default_value = strength
        sock.keyframe_insert(data_path='default_value', frame=frame)
    if nt.animation_data and nt.animation_data.action:
        for fc in nt.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    return nt


def _make_mist(atmo):
    m = bpy.data.materials.new('MAT_V52_Sunrise_Mist')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    scatter = nt.nodes.new('ShaderNodeVolumeScatter')
    scatter.inputs['Color'].default_value = (.92, .88, .82, 1)
    scatter.inputs['Anisotropy'].default_value = MIST_ANISOTROPY
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
    h = nt.nodes.new('ShaderNodeMapRange')
    h.name = 'V52_Mist_Density'
    h.inputs['From Min'].default_value = .15
    h.inputs['From Max'].default_value = MIST_TOP
    h.inputs['To Min'].default_value = MIST_DENSITY
    h.inputs['To Max'].default_value = 0.0
    h.clamp = True
    nt.links.new(sep.outputs['Z'], h.inputs['Value'])
    nt.links.new(h.outputs['Result'], scatter.inputs['Density'])
    nt.links.new(scatter.outputs['Volume'], out.inputs['Volume'])
    if hasattr(m, 'volume_sampling'):
        m.volume_sampling = 'MULTIPLE_IMPORTANCE'
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 100, 25))
    o = bpy.context.object
    o.name = 'SM_V52_Sunrise_MistDomain'
    o.scale = (280, 320, 50)  # x -140..140, y -60..260, z 0..50
    o.data.materials.append(m)
    o.display_type = 'WIRE'
    _move(o, atmo)
    return o


def _make_cloud_deck(atmo):
    """Shadow-only, world-space cloud lanes; not a light and not emissive.

    Geometry Position is essential: object coordinates on a plane scaled to
    hundreds of metres made the earlier gobos nearly constant.  World-space
    sine lanes, warped by low-frequency noise, give the single sun distinct
    openings to pass through.
    """
    m = bpy.data.materials.new('MAT_V52_CloudDeck')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    transparent = nt.nodes.new('ShaderNodeBsdfTransparent')
    opaque = nt.nodes.new('ShaderNodeBsdfDiffuse')
    opaque.inputs['Color'].default_value = (.02, .02, .02, 1)
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = CLOUD_NOISE_SCALE
    noise.inputs['Detail'].default_value = 2.0
    nt.links.new(geo.outputs['Position'], noise.inputs['Vector'])
    warp = _math(nt, 'MULTIPLY', noise.outputs['Fac'], CLOUD_WARP)
    phase_x = _math(nt, 'MULTIPLY', sep.outputs['X'], CLOUD_PHASE_X)
    phase = _math(nt, 'ADD', phase_x, warp)
    sine = _math(nt, 'SINE', phase)
    edge = nt.nodes.new('ShaderNodeMapRange')
    edge.inputs['From Min'].default_value = CLOUD_EDGE[0]
    edge.inputs['From Max'].default_value = CLOUD_EDGE[1]
    edge.inputs['To Min'].default_value = 0.0
    edge.inputs['To Max'].default_value = CLOUD_SHADOW_MAX
    edge.interpolation_type = 'LINEAR'
    edge.clamp = True
    nt.links.new(sine, edge.inputs['Value'])
    lp = nt.nodes.new('ShaderNodeLightPath')
    shadow_opacity = _math(nt, 'MULTIPLY', edge.outputs['Result'], lp.outputs['Is Shadow Ray'])
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(shadow_opacity, mix.inputs[0])
    nt.links.new(transparent.outputs['BSDF'], mix.inputs[1])
    nt.links.new(opaque.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(60, 320, 55))
    o = bpy.context.object
    o.name = 'SM_V52_CloudDeck'
    o.scale = (500, 700, 1)
    o.data.materials.append(m)
    o.display_type = 'WIRE'
    o.visible_camera = False
    o.visible_diffuse = False
    o.visible_glossy = False
    o.visible_transmission = False
    o.visible_volume_scatter = True
    o.visible_shadow = True
    o['role'] = 'Shadow-only world-space cloud occluder; zero emission; not a light source'
    _move(o, atmo)
    return o


def audit_lighting(scene):
    lights = [o for o in scene.objects if o.type == 'LIGHT']
    suns = [o for o in lights if o.data.type == 'SUN']
    spots = [o for o in lights if o.data.type == 'SPOT']
    fake = [o for o in scene.objects if o.name.startswith((
        'SM_V5_Light_Shaft', 'LGT_V5_GodRay_Shaft', 'SM_V5_GodRay_Medium',
        'SM_V5_Cloud_Gobo', 'SM_V51_CloudShadow'))]
    stray_vents = [o for o in scene.objects if o.name.startswith((
        'SM_Vent_Cap_StandingSeam', 'SM_Vent_Metal_Rib')) and o.parent is None]
    emissive_volumes = []
    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        for n in mat.node_tree.nodes:
            if n.type in {'VOLUME_PRINCIPLED', 'PRINCIPLED_VOLUME'}:
                sock = n.inputs.get('Emission Strength')
                if sock and sock.default_value > 0:
                    emissive_volumes.append(mat.name)
    mist = [o.name for o in scene.objects if o.name == 'SM_V52_Sunrise_MistDomain']
    deck = [o.name for o in scene.objects if o.name == 'SM_V52_CloudDeck']
    result = {
        'revision': scene.get('revision'),
        'sky_type': scene.get('sky_type'),
        'sun_count': len(suns),
        'sun_names': [o.name for o in suns],
        'spot_count': len(spots),
        'fake_shaft_objects': [o.name for o in fake],
        'unparented_vent_parts': [o.name for o in stray_vents],
        'emissive_volume_materials': sorted(set(emissive_volumes)),
        'mist_domains': mist,
        'cloud_deck': deck,
        'volume_bounces': scene.cycles.volume_bounces,
        'sun_azimuth_deg': SUN_AZIMUTH_DEG,
        'sun_elevation_keys_deg': [e for _f, e, _energy, _colour in SUN_KEYS],
        'sun_direction_world_frame75': list(_sun_travel_direction(SUN_KEYS[1][1])),
    }
    result['pass'] = (result['revision'] == REVISION and
                      result['sky_type'] == 'SUNRISE_GRADIENT' and
                      len(suns) == 1 and not spots and not fake and
                      not emissive_volumes and not stray_vents and
                      len(mist) == 1 and len(deck) == 1)
    return result


def apply_v5(samples=32):
    s = bpy.context.scene
    s['revision'] = REVISION
    s['sky_type'] = 'SUNRISE_GRADIENT'
    s['animation_spec'] = '150 frames, 30 fps, 1920x1080, 5.000 s dolly'
    s['lighting_note'] = ('One animated sun rising from behind the Ghats; world-space '
                          'non-emissive mist and shadow-only cloud lanes; no spotlights, '
                          'beam cones, or compositor ray overlays.')
    vl = bpy.context.view_layer
    def exclude(lc):
        if lc.collection.name.startswith('LIB_') or lc.collection.name == 'COL_AssetLibrary':
            lc.exclude = True
        for ch in lc.children:
            exclude(ch)
    exclude(vl.layer_collection)
    atmo = _collection('COL_Atmosphere')
    cams = _collection('COL_Cameras')

    # Defensive cleanup: handles v5.0/v5.1 objects and repeated application.
    for o in list(bpy.data.objects):
        if o.name.startswith(('SM_V5_Light_Shaft', 'LGT_V5_GodRay_Shaft',
                              'SM_V5_GodRay_Medium', 'SM_V5_Cloud_Gobo',
                              'SM_V51_', 'SM_V52_', 'CAM_V5_Dolly_1080p')):
            bpy.data.objects.remove(o, do_unlink=True)

    _make_sunrise_world()
    sun = bpy.data.objects.get('LGT_Q_SoftMonsoonSun')
    if sun is None:
        raise RuntimeError('Expected baseline sun missing')
    sun.name = 'LGT_V52_RisingSun'
    sun.data.angle = math.radians(.53)
    sun.visible_volume_scatter = True
    for frame, elev, energy, colour in SUN_KEYS:
        sun.rotation_euler = _sun_travel_direction(elev).to_track_quat('-Z', 'Y').to_euler()
        sun.data.energy = energy
        sun.data.color = colour
        sun.keyframe_insert('rotation_euler', frame=frame)
        sun.data.keyframe_insert('energy', frame=frame)
        sun.data.keyframe_insert('color', frame=frame)
    for datablock in (sun, sun.data):
        if datablock.animation_data and datablock.animation_data.action:
            for fc in datablock.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'

    fill = bpy.data.objects.get('LGT_Q_Fill_SkyBounce')
    if fill:
        fill.data.color = (.78, .85, .95)
        fill.visible_volume_scatter = False  # fill must not manufacture rays
        for frame, energy in [(1, 22.0), (20, 18.0), (40, 15.0), (75, 12.0), (150, 10.0)]:
            fill.data.energy = energy
            fill.data.keyframe_insert('energy', frame=frame)
        if fill.data.animation_data and fill.data.animation_data.action:
            for fc in fill.data.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'

    # Retire the old opaque fog banks; they caused bright snow-like horizon patches.
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
        if o.name.startswith(('SM_Q_Mist_Bank', 'SM_V4_Valley_Haze')):
            o.hide_render = True
    # Matte distant ridges: no specular low-sun "snow" patches.
    for mn, c0, c1 in [
        ('MAT_Q_Ghat_ForestRock', (.014, .028, .020, 1), (.030, .052, .036, 1)),
        ('MAT_Q_Distant_Ghat', (.040, .054, .060, 1), (.065, .082, .090, 1)),
    ]:
        m = bpy.data.materials.get(mn)
        if m:
            m.use_nodes = True
            nt = m.node_tree; nt.nodes.clear()
            out = nt.nodes.new('ShaderNodeOutputMaterial')
            p = nt.nodes.new('ShaderNodeBsdfPrincipled')
            p.inputs['Roughness'].default_value = 1.0
            p.inputs['Specular IOR Level'].default_value = 0.0
            nz = nt.nodes.new('ShaderNodeTexNoise')
            nz.inputs['Scale'].default_value = .018
            nz.inputs['Detail'].default_value = 2.0
            ramp = nt.nodes.new('ShaderNodeValToRGB')
            ramp.color_ramp.elements[0].color = c0
            ramp.color_ramp.elements[1].color = c1
            nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
            nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
            nt.links.new(p.outputs['BSDF'], out.inputs['Surface'])
    marsh = bpy.data.objects.get('SM_V4_Back_Marsh_Ground')
    if marsh:
        mm = bpy.data.materials.new('MAT_V52_Distant_Marsh'); mm.use_nodes = True
        pb = mm.node_tree.nodes['Principled BSDF']
        pb.inputs['Base Color'].default_value = (.030, .040, .028, 1)
        pb.inputs['Roughness'].default_value = .9
        marsh.data.materials.clear(); marsh.data.materials.append(mm)
    _make_mist(atmo)
    _make_cloud_deck(atmo)
    # Gentler mist before the disc clears the ridge reduces low-sample fireflies,
    # then the full density carries the shadow-shaped rays through the rise.
    mist_h = bpy.data.materials['MAT_V52_Sunrise_Mist'].node_tree.nodes['V52_Mist_Density']
    for frame, density in [(1, 0.0), (20, 0.0), (30, 0.0), (40, .0004), (50, .0013), (60, .0022), (75, .0022), (150, .0022)]:
        mist_h.inputs['To Min'].default_value = density
        mist_h.inputs['To Min'].keyframe_insert(data_path='default_value', frame=frame)
    mnt = bpy.data.materials['MAT_V52_Sunrise_Mist'].node_tree
    if mnt.animation_data and mnt.animation_data.action:
        for fc in mnt.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'

    # Keep the floating black roof-vent grid fixed: parent its loose parts.
    root = bpy.data.objects.get('SM_Tharavad_House_Root')
    if root:
        for o in bpy.data.objects:
            if o.name.startswith(('SM_Vent_Cap_StandingSeam', 'SM_Vent_Metal_Rib')) and o.parent is None:
                o.parent = root
                o.matrix_parent_inverse = Matrix.Identity(4)

    # Keep all 26 uploaded coconuts; clear the sun line and give near crowns headroom.
    for name, loc, scale in [
        ('SM_UserCoconut_Palm_00', (-12.0, 34.0, -.04), .90),
        ('SM_UserCoconut_Palm_01', (13.5, 20.0, -.04), .95),
        ('SM_UserCoconut_Palm_02', (-8.0, 38.0, -.04), .95),
        ('SM_UserCoconut_Palm_03', (32.0, 52.0, -.04), .98),
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
    s.cycles.adaptive_min_samples = 16
    s.cycles.use_denoising = True
    s.cycles.denoiser = 'OPENIMAGEDENOISE'
    # The renderer switches to RGB_ALBEDO_NORMAL for the dark pre-dawn frames;
    # albedo-only denoising keeps the later cloud-shadow shafts crisp.
    s.cycles.denoising_input_passes = 'RGB_ALBEDO'
    s.cycles.denoising_prefilter = 'ACCURATE'
    s.cycles.max_bounces = 6
    s.cycles.diffuse_bounces = 3
    s.cycles.glossy_bounces = 3
    s.cycles.transmission_bounces = 4
    s.cycles.volume_bounces = 0  # crisp single scattering, not glowing multi-scatter cones
    s.cycles.transparent_max_bounces = 16
    s.cycles.caustics_reflective = False
    s.cycles.caustics_refractive = False
    s.cycles.sample_clamp_indirect = 1.5
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
    for frame, exposure in [(1, .40), (20, .25), (40, .12), (75, .0), (150, -.15)]:
        s.view_settings.exposure = exposure
        s.keyframe_insert(data_path='view_settings.exposure', frame=frame)
    if s.animation_data and s.animation_data.action:
        for fc in s.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    try:
        s.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    if s.use_nodes and s.node_tree:
        for n in s.node_tree.nodes:
            if n.type == 'GLARE':
                n.mix = -.92  # restrained highlight bloom; cannot paint rays
                if hasattr(n, 'threshold'):
                    n.threshold = 1.8

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
