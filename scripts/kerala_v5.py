"""Kerala v5 lighting/texture/animation upgrade applied on top of v4.
Art direction: post-rain sun break through humid air; visible god rays,
longer soft-but-defined shadows, wetter microdetail, 5 s 30 fps dolly.
"""
import math
import bpy
from mathutils import Vector

def _exclude_libs(lc):
    if lc.collection.name.startswith('LIB_') or lc.collection.name=='COL_AssetLibrary':
        lc.exclude=True
    for ch in lc.children:_exclude_libs(ch)

def _collection(name):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
    return c

def _box(name,loc,dim,c,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object;o.name=name;o.scale=dim;o.data.materials.append(mat)
    for old in list(o.users_collection):old.objects.unlink(o)
    c.objects.link(o);return o

def _aim(o,target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

def _noise_density(nt,base=.0028,lo=.0012,hi=.0042,scale=.08):
    tc=nt.nodes.new('ShaderNodeTexCoord');mp=nt.nodes.new('ShaderNodeMapping');mp.inputs['Scale'].default_value=(scale,scale,scale)
    nz=nt.nodes.new('ShaderNodeTexNoise');nz.inputs['Scale'].default_value=1.0;nz.inputs['Detail'].default_value=5;nz.inputs['Roughness'].default_value=.6
    mr=nt.nodes.new('ShaderNodeMapRange');mr.inputs['From Min'].default_value=.35;mr.inputs['From Max'].default_value=.75;mr.inputs['To Min'].default_value=lo;mr.inputs['To Max'].default_value=hi;mr.clamp=True
    nt.links.new(tc.outputs['Object'],mp.inputs['Vector']);nt.links.new(mp.outputs['Vector'],nz.inputs['Vector']);nt.links.new(nz.outputs['Fac'],mr.inputs['Value']);return mr.outputs['Result']

def _ao_grime(mat,factor=.30):
    nt=mat.node_tree;p=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not p:return
    src=next((l.from_socket for l in nt.links if l.to_node==p and l.to_socket.name=='Base Color'),None)
    if not src:return
    ao=nt.nodes.new('ShaderNodeAmbientOcclusion');ao.samples=8;ao.inputs['Distance'].default_value=.35
    mx=nt.nodes.new('ShaderNodeMixRGB');mx.blend_type='MULTIPLY';mx.inputs[0].default_value=factor
    nt.links.new(src,mx.inputs[1]);nt.links.new(ao.outputs['Color'],mx.inputs[2]);nt.links.new(mx.outputs['Color'],p.inputs['Base Color'])

def _bump_detail(mat,scale=18,strength=.28,distance=.035):
    nt=mat.node_tree;p=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not p:return
    nz=nt.nodes.new('ShaderNodeTexNoise');nz.inputs['Scale'].default_value=scale;nz.inputs['Detail'].default_value=6
    bp=nt.nodes.new('ShaderNodeBump');bp.inputs['Strength'].default_value=strength;bp.inputs['Distance'].default_value=distance
    # chain after existing normal if present
    old=next((l.from_socket for l in nt.links if l.to_node==p and l.to_socket.name=='Normal'),None)
    if old:nt.links.new(old,bp.inputs['Normal'])
    nt.links.new(nz.outputs['Fac'],bp.inputs['Height']);nt.links.new(bp.outputs['Normal'],p.inputs['Normal'])

def apply_v5(samples=24):
    s=bpy.context.scene;s['revision']='kerala-v5.0-godrays-animation'
    s['animation_spec']='150 frames, 30 fps, 1920x1080, 5.000 s dolly'
    s['lighting_note']='Post-rain sun break: warm low sun + forward-scatter humid volume + restrained shaft fills; no 2D ray overlay.'
    _exclude_libs(bpy.context.view_layer.layer_collection)
    lights=_collection('COL_Lights');atmo=_collection('COL_Atmosphere');cams=_collection('COL_Cameras')
    # World: keep sky texture but let the sun dominate.
    for n in s.world.node_tree.nodes:
        if n.type=='BACKGROUND':n.inputs['Strength'].default_value=.20
        if n.type=='HUE_SAT':n.inputs['Value'].default_value=.92
    sun=bpy.data.objects.get('LGT_Q_SoftMonsoonSun')
    if sun:
        sun.data.energy=6.0;sun.data.angle=math.radians(0.8);sun.data.color=(1.0,.91,.78)
        sun.rotation_euler=Vector((.45,-.45,-.77)).to_track_quat('-Z','Y').to_euler()
    fill=bpy.data.objects.get('LGT_Q_Fill_SkyBounce')
    if fill:fill.data.energy=4;fill.data.color=(.78,.85,.95)
    # Restrained shaft fills from behind the house/palms toward camera.
    for i,(loc,tgt,en) in enumerate([((-14,74,22),(-5,4,0),650),((5,88,26),(2,0,0),800),((20,76,23),(9,8,0),600)]):
        ld=bpy.data.lights.new(f'LGT_V5_GodRay_Shaft_{i}','SPOT');ld.energy=en;ld.color=(1,.90,.74);ld.spot_size=math.radians(14);ld.spot_blend=.30;ld.shadow_soft_size=1.6
        lo=bpy.data.objects.new(f'LGT_V5_GodRay_Shaft_{i}',ld);lights.objects.link(lo);lo.location=loc;_aim(lo,tgt)
    # Forward-scattering humid medium for true volumetric shafts.
    vm=bpy.data.materials.new('MAT_V5_GodRay_Medium');vm.use_nodes=True;nt=vm.node_tree;nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial');vs=nt.nodes.new('ShaderNodeVolumeScatter');vs.inputs['Color'].default_value=(.84,.88,.92,1);vs.inputs['Anisotropy'].default_value=.80
    vs.inputs['Density'].default_value=.0012;nt.links.new(vs.outputs['Volume'],out.inputs['Volume'])
    _box('SM_V5_GodRay_Medium',(0,35,17),(150,130,36),atmo,vm)
    for mn in ['MAT_V4_Valley_Haze','MAT_Q_Mist_Bank_Volume']:
        m=bpy.data.materials.get(mn)
        if m:
            for n in m.node_tree.nodes:
                if n.type=='VOLUME_PRINCIPLED':n.inputs['Density'].default_value=.0005 if 'Valley' in mn else .001
                if n.type=='MAP_RANGE' and n.inputs['To Max'].default_value<.03:n.inputs['To Max'].default_value=.010
    # Shadow-only cloud gobo breaks the sun into volumetric shafts.
    gm=bpy.data.materials.new('MAT_V5_Cloud_Gobo');gm.use_nodes=True;gt=gm.node_tree;gt.nodes.clear()
    go=gt.nodes.new('ShaderNodeOutputMaterial');tr=gt.nodes.new('ShaderNodeBsdfTransparent');op=gt.nodes.new('ShaderNodeBsdfDiffuse');op.inputs['Color'].default_value=(.05,.05,.05,1)
    tc=gt.nodes.new('ShaderNodeTexCoord');mp=gt.nodes.new('ShaderNodeMapping');mp.inputs['Scale'].default_value=(.035,.035,.035)
    nz=gt.nodes.new('ShaderNodeTexNoise');nz.inputs['Scale'].default_value=1.0;nz.inputs['Detail'].default_value=6;nz.inputs['Roughness'].default_value=.65
    rp=gt.nodes.new('ShaderNodeValToRGB');rp.color_ramp.elements[0].position=.50;rp.color_ramp.elements[0].color=(0,0,0,1);rp.color_ramp.elements[1].position=.58;rp.color_ramp.elements[1].color=(1,1,1,1)
    mx=gt.nodes.new('ShaderNodeMixShader');gt.links.new(tc.outputs['Object'],mp.inputs['Vector']);gt.links.new(mp.outputs['Vector'],nz.inputs['Vector']);gt.links.new(nz.outputs['Fac'],rp.inputs['Fac']);gt.links.new(rp.outputs['Color'],mx.inputs[0]);gt.links.new(tr.outputs['BSDF'],mx.inputs[1]);gt.links.new(op.outputs['BSDF'],mx.inputs[2]);gt.links.new(mx.outputs['Shader'],go.inputs['Surface'])
    bpy.ops.mesh.primitive_plane_add(size=150,location=(0,45,30));gobo=bpy.context.object;gobo.name='SM_V5_Cloud_Gobo';gobo.data.materials.append(gm);gobo.visible_camera=False;gobo.visible_glossy=False;gobo.visible_transmission=False
    for old in list(gobo.users_collection):old.objects.unlink(o) if False else old.objects.unlink(gobo)
    atmo.objects.link(gobo)
    # Art-directed 3D light-shaft volumes (scattering + faint emission) for readable god rays.
    shm=bpy.data.materials.new('MAT_V5_Light_Shaft');shm.use_nodes=True;st=shm.node_tree;st.nodes.clear()
    so=st.nodes.new('ShaderNodeOutputMaterial');pv=st.nodes.new('ShaderNodeVolumePrincipled');pv.inputs['Color'].default_value=(.95,.90,.78,1);pv.inputs['Anisotropy'].default_value=.6;pv.inputs['Emission Strength'].default_value=.003;pv.inputs['Emission Color'].default_value=(1,.90,.72,1)
    tc=st.nodes.new('ShaderNodeTexCoord');val=st.nodes.new('ShaderNodeValue');val.outputs[0].default_value=.0035;sep=st.nodes.new('ShaderNodeSeparateXYZ');st.links.new(tc.outputs['Generated'],sep.inputs['Vector'])
    sx=st.nodes.new('ShaderNodeMath');sx.operation='SUBTRACT';sx.inputs[1].default_value=.5;st.links.new(sep.outputs['X'],sx.inputs[0])
    sy=st.nodes.new('ShaderNodeMath');sy.operation='SUBTRACT';sy.inputs[1].default_value=.5;st.links.new(sep.outputs['Y'],sy.inputs[0])
    x2=st.nodes.new('ShaderNodeMath');x2.operation='MULTIPLY';st.links.new(sx.outputs[0],x2.inputs[0]);st.links.new(sx.outputs[0],x2.inputs[1])
    y2=st.nodes.new('ShaderNodeMath');y2.operation='MULTIPLY';st.links.new(sy.outputs[0],y2.inputs[0]);st.links.new(sy.outputs[0],y2.inputs[1])
    ad=st.nodes.new('ShaderNodeMath');ad.operation='ADD';st.links.new(x2.outputs[0],ad.inputs[0]);st.links.new(y2.outputs[0],ad.inputs[1])
    sq=st.nodes.new('ShaderNodeMath');sq.operation='SQRT';st.links.new(ad.outputs[0],sq.inputs[0])
    fade=st.nodes.new('ShaderNodeMapRange');fade.inputs['From Min'].default_value=.12;fade.inputs['From Max'].default_value=.5;fade.inputs['To Min'].default_value=1;fade.inputs['To Max'].default_value=0;fade.clamp=True;st.links.new(sq.outputs[0],fade.inputs['Value'])
    mul=st.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';st.links.new(val.outputs[0],mul.inputs[0]);st.links.new(fade.outputs['Result'],mul.inputs[1]);st.links.new(mul.outputs[0],pv.inputs['Density']);st.links.new(pv.outputs['Volume'],so.inputs['Volume'])
    for i,(sky,ground,rb) in enumerate([((-12,70,30),(-6,8,0),3.2),((2,85,32),(1,2,0),4.0),((16,72,30),(8,10,0),3.0),((-22,56,28),(-11,0,0),2.6)]):
        skyV=Vector(sky);gV=Vector(ground);mid=(skyV+gV)/2;axis=skyV-gV;depth=axis.length
        bpy.ops.mesh.primitive_cone_add(vertices=16,radius1=rb,radius2=.35,depth=depth,location=mid)
        sh=bpy.context.object;sh.name=f'SM_V5_Light_Shaft_{i}';sh.rotation_euler=axis.to_track_quat('Z','Y').to_euler();sh.data.materials.append(shm);sh.visible_shadow=False
        for old in list(sh.users_collection):old.objects.unlink(sh)
        atmo.objects.link(sh)
    # Texture/microdetail and contact grime.
    for m in bpy.data.materials:
        n=m.name.lower()
        if any(k in n for k in ['roof','tile','plaster','wood','mud','earth','laterite']):
            _ao_grime(m,.28 if 'roof' in n or 'tile' in n else .20)
            _bump_detail(m,scale=22 if 'mud' in n or 'earth' in n else 14,strength=.22,distance=.03 if 'mud' in n or 'earth' in n else .018)
    water=bpy.data.materials.get('MAT_Q_Paddy_Water_Shallow')
    if water:
        p=next(n for n in water.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Roughness'].default_value=.055
        if 'IOR' in p.inputs:p.inputs['IOR'].default_value=1.333
        nt=water.node_tree;w=nt.nodes.new('ShaderNodeTexWave');w.inputs['Scale'].default_value=2.6;w.inputs['Distortion'].default_value=3.0;w.inputs['Detail'].default_value=3
        bp=nt.nodes.new('ShaderNodeBump');bp.inputs['Strength'].default_value=.10;bp.inputs['Distance'].default_value=.012;nt.links.new(w.outputs['Fac'],bp.inputs['Height']);nt.links.new(bp.outputs['Normal'],p.inputs['Normal'])
    mud=bpy.data.materials.get('MAT_V4_Wet_Scanned_Earth')
    if mud:
        nt=mud.node_tree;p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
        nz=nt.nodes.new('ShaderNodeTexNoise');nz.inputs['Scale'].default_value=5;mr=nt.nodes.new('ShaderNodeMapRange');mr.inputs['To Min'].default_value=.22;mr.inputs['To Max'].default_value=.58;mr.clamp=True;nt.links.new(nz.outputs['Fac'],mr.inputs['Value']);nt.links.new(mr.outputs['Result'],p.inputs['Roughness'])
    # Cycles shadow/volume quality.
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=samples;s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.05;s.cycles.adaptive_min_samples=4
    s.cycles.use_denoising=True;s.cycles.denoiser='OPENIMAGEDENOISE'
    try:s.cycles.denoising_input_passes='RGB_ALBEDO'
    except Exception:pass
    s.cycles.max_bounces=6;s.cycles.diffuse_bounces=3;s.cycles.glossy_bounces=3;s.cycles.transmission_bounces=4;s.cycles.volume_bounces=2;s.cycles.transparent_max_bounces=12
    s.cycles.caustics_reflective=False;s.cycles.caustics_refractive=False;s.cycles.sample_clamp_indirect=3.0
    s.cycles.volume_step_rate=2.0;s.cycles.volume_max_steps=128;s.cycles.use_light_tree=True
    s.render.use_persistent_data=False;s.render.fps=30;s.frame_start=1;s.frame_end=150
    s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
    s.view_settings.exposure=.0
    try:s.view_settings.look='AgX - Base Contrast'
    except Exception:pass
    # 5-second dolly along the bund toward the house.
    cd=bpy.data.cameras.new('CAM_V5_Dolly_1080p');cd.lens=35;cd.clip_end=1200;cd.dof.use_dof=False
    cam=bpy.data.objects.new('CAM_V5_Dolly_1080p',cd);cams.objects.link(cam);s.camera=cam
    keys=[(1,(-2.8,-15.0,1.48),(3.0,62.0,3.1),35),(75,(-2.0,-11.5,1.55),(3.0,62.0,3.2),35.5),(150,(-1.0,-8.0,1.62),(3.2,63.0,3.4),36)]
    for f,loc,tgt,lens in keys:
        cam.location=loc;_aim(cam,tgt);cd.lens=lens
        cam.keyframe_insert('location',frame=f);cam.keyframe_insert('rotation_euler',frame=f);cd.keyframe_insert('lens',frame=f)
    for fc in cam.animation_data.action.fcurves:
        for kp in fc.keyframe_points:kp.interpolation='BEZIER';kp.easing='EASE_IN_OUT'
    for fc in cd.animation_data.action.fcurves:
        for kp in fc.keyframe_points:kp.interpolation='BEZIER';kp.easing='EASE_IN_OUT'
    s.frame_set(75)
    return s
