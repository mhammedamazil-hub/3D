#!/usr/bin/env python3
"""Kerala v4: use the uploaded coconut GLB and rebuild the weakest realism layers.
Run: sh scripts/blender-py scripts/build_kerala_v4.py
Requires the frozen v3 blend and the attributed user GLB; no photo backplate.
"""
import bpy,os,sys,json,math,random,time,hashlib
from pathlib import Path
from mathutils import Vector,noise
sys.path.insert(0,str(Path(__file__).resolve().parent))
from kerala_helpers import collection,mesh_obj,box,tube,scatter_points,fbm,aim,path_x
from kerala_vegetation import blade_mesh
from coconut_asset_v4 import import_user_coconut,export_glb
ROOT=Path(__file__).resolve().parent.parent;T0=time.time();REV='kerala-v4.0-user-coconut'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/Kerala_Quality.blend'))
s=bpy.context.scene;s.name='Monsoon Light — Kerala v4';s['revision']=REV
s['user_coconut_asset']='Coconut Tree Low poly by Pixel_Monster / ar.jethin, CC BY 4.0; uploaded GLB normalized to metres.'
s['generated_reference_disclosure']='Two AI-generated look-development references were inspected; neither is used as a backplate or projection texture.'
rng=random.Random(2717453)
M={m.name:m for m in bpy.data.materials}
lib=collection('COL_AssetLibrary');veg=collection('COL_FieldVegetation');pathc=collection('COL_Path_and_Bunds');waterc=collection('COL_Water');terrain=collection('COL_Terrain');mount=collection('COL_Mountains');atmo=collection('COL_Atmosphere');lights=collection('COL_Lights');cams=collection('COL_Cameras')
# Source scan libraries must never render at the origin; only collection instances do.
def _exclude_libs(lc):
    if lc.collection.name.startswith('LIB_'):lc.exclude=True;lc.hide_viewport=True
    for ch in lc.children:_exclude_libs(ch)
_exclude_libs(bpy.context.view_layer.layer_collection)
for c in list(s.collection.children):
    if c.name.startswith('LIB_'):s.collection.children.unlink(c)
# The island-tree scan includes a large rock face; use the smaller forest scan instead.
ts=bpy.data.collections.get('LIB_tree_small_02')
if ts:
    for o in bpy.data.objects:
        if o.type=='EMPTY' and o.instance_collection and o.instance_collection.name=='LIB_island_tree_03':
            o.instance_collection=ts;o.scale=tuple(v*2.0 for v in o.scale)
for o in list(bpy.data.objects):
    if o.type=='EMPTY' and o.instance_collection and o.instance_collection.name in {'LIB_rock_face_02','LIB_rock_07','LIB_boulder_01'}:
        bpy.data.objects.remove(o,do_unlink=True)

def remove_names(prefixes):
    for o in list(bpy.data.objects):
        if any(o.name.startswith(p) for p in prefixes):bpy.data.objects.remove(o,do_unlink=True)

def tracked_map(aid,name):
    d=ROOT/'assets/textures/polyhaven'/aid
    for ext in ['jpg','png','exr']:
        p=d/f'{name}.{ext}'
        if p.exists():return p
    return None

def tex(nt,path,scale=1.,noncolor=False):
    img=bpy.data.images.load(str(path),check_existing=True)
    if noncolor:
        try:img.colorspace_settings.name='Non-Color'
        except Exception:pass
    t=nt.nodes.new('ShaderNodeTexImage');t.image=img;t.projection='BOX';t.projection_blend=.25
    tc=nt.nodes.new('ShaderNodeTexCoord');mp=nt.nodes.new('ShaderNodeMapping');mp.inputs['Scale'].default_value=(scale,scale,scale)
    nt.links.new(tc.outputs['Object'],mp.inputs['Vector']);nt.links.new(mp.outputs['Vector'],t.inputs['Vector']);return t

def pbr(name,aid,scale,tint,rough,bump,tint_fac):
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;p=nt.nodes['Principled BSDF']
    d=tracked_map(aid,'Diffuse')
    if d:
        t=tex(nt,d,scale);mx=nt.nodes.new('ShaderNodeMixRGB');mx.blend_type='MULTIPLY';mx.inputs[0].default_value=tint_fac;mx.inputs[2].default_value=(*tint,1);nt.links.new(t.outputs['Color'],mx.inputs[1]);nt.links.new(mx.outputs['Color'],p.inputs['Base Color'])
    else:p.inputs['Base Color'].default_value=(*tint,1)
    r=tracked_map(aid,'Rough')
    if r:
        t=tex(nt,r,scale,True);mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=rough;nt.links.new(t.outputs['Color'],mul.inputs[0]);nt.links.new(mul.outputs[0],p.inputs['Roughness'])
    else:p.inputs['Roughness'].default_value=rough
    h=tracked_map(aid,'Displacement') or r
    if h:
        t=tex(nt,h,scale,True);b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.45;b.inputs['Distance'].default_value=bump;nt.links.new(t.outputs['Color'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
    return m

# --- Replace procedural palms with the uploaded coconut asset -----------------
remove_names(['SM_Q_Coconut_Palm_','SM_Coconut_','SM_Q_IslandTree_','SM_Q_TreeSmall_0','SM_Laterite_Chip_'])
for c in list(bpy.data.collections):
    if c.name.startswith('LIB_Coconut'):
        for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.collections.remove(c)
coconut,sm,em=import_user_coconut(parent=lib,scale=.1)
export_glb(coconut,sm,em,ROOT/'output/Coconut_Tree_Scene_Ready.glb')

def instance(name,loc,scale,rot):
    o=bpy.data.objects.new(name,None);veg.objects.link(o);o.instance_collection=coconut;o.instance_type='COLLECTION';o.location=loc;o.scale=(scale,scale,scale);o.rotation_euler=rot;return o
palm_pos=[(-5.8,-1.0,1.16),(9.6,6.5,1.10),(-14,28,1.02),(16,34,1.06),(-12,55,1.14),(14,58,1.10),(-24,44,.96),(25,50,.98)]
for i in range(18):
    side=rng.choice([-1,1]);x=side*rng.uniform(18,72);y=rng.uniform(74,132);palm_pos.append((x,y,rng.uniform(.78,1.18)))
for i,(x,y,sc) in enumerate(palm_pos):
    instance(f'SM_UserCoconut_Palm_{i:02d}',(x,y,-.04),sc,(rng.uniform(-.035,.035),rng.uniform(-.035,.035),rng.uniform(0,6.28)))

# --- Younger row rice with open water ----------------------------------------
rice_lib=bpy.data.collections['COL_Library_RiceClumps'];tmp=collection('TMP_RiceReplace')
rm=[M['MAT_Q_Rice_LivingBlade'],M['MAT_Q_Rice_YoungTip']]
for i,o in enumerate(sorted([o for o in rice_lib.objects if o.type=='MESH'],key=lambda x:x.name)):
    n=blade_mesh(f'TMP_Rice_{i}',random.Random(900+i),tmp,rm,blades=5+i%3,hmin=.24,hmax=.46,width=.0048,lean=.16,segs=3)
    old=o.data;o.data=n.data;bpy.data.objects.remove(n,do_unlink=True)
    if old.users==0:bpy.data.meshes.remove(old)
bpy.data.collections.remove(tmp)
for mn,cols in [('MAT_Q_Rice_LivingBlade',[(.035,.095,.012),(.095,.20,.025),(.19,.28,.055)]),('MAT_Q_Rice_YoungTip',[(.11,.20,.035),(.20,.29,.06),(.30,.36,.09)])]:
    m=M[mn]
    for n in m.node_tree.nodes:
        if n.type=='VALTORGB':
            for e,c in zip(n.color_ramp.elements,cols):e.color=(*c,1)
        if n.type=='MIX_SHADER':n.inputs[0].default_value=.18

# --- Narrow irregular wet path, low bunds, foreground timber crossing ---------
remove_names(['SM_Q_Wet_Earthen_Footpath','SM_Q_Transverse_Earthen_Bund','SM_Q_Path_Puddle','SM_Q_Drain','SM_Q_Timber','SM_Q_Bund_Grass_Instances','SM_Damp_Lime_Skirt'])
mud=pbr('MAT_V4_Wet_Scanned_Earth','brown_mud',1.1,(.22,.15,.08),.48,.05,.70)
nt=mud.node_tree;mp=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
if 'Specular IOR Level' in mp.inputs:mp.inputs['Specular IOR Level'].default_value=.12
src=next((l.from_socket for l in nt.links if l.to_node==mp and l.to_socket.name=='Base Color'),None)
nz=nt.nodes.new('ShaderNodeTexNoise');nz.inputs['Scale'].default_value=7;nz.inputs['Detail'].default_value=6
rp=nt.nodes.new('ShaderNodeValToRGB');rp.color_ramp.elements[0].color=(.07,.05,.028,1);rp.color_ramp.elements[1].color=(.20,.14,.075,1);nt.links.new(nz.outputs['Fac'],rp.inputs['Fac'])
if src:
    mx=nt.nodes.new('ShaderNodeMixRGB');mx.inputs[0].default_value=.55;nt.links.new(src,mx.inputs[1]);nt.links.new(rp.outputs['Color'],mx.inputs[2]);nt.links.new(mx.outputs['Color'],mp.inputs['Base Color'])
else:nt.links.new(rp.outputs['Color'],mp.inputs['Base Color'])
puddle=bpy.data.materials.new('MAT_V4_Path_Puddle_Water');puddle.use_nodes=True;pb=puddle.node_tree.nodes['Principled BSDF'];pb.inputs['Base Color'].default_value=(.030,.035,.025,1);pb.inputs['Roughness'].default_value=.28
if 'Specular IOR Level' in pb.inputs:pb.inputs['Specular IOR Level'].default_value=.2
wood=pbr('MAT_V4_Wet_Timber','wood_planks',.8,(.22,.14,.07),.68,.022,.42)
y0,y1=-18,56;ny=220;cols=9;verts=[];faces=[]
for j in range(ny+1):
    y=y0+(y1-y0)*j/ny;cx=path_x(y);width=.88+.14*math.sin(y*.21)+.08*fbm(y*.31,0,3)
    for i in range(cols):
        t=i/(cols-1)-.5;x=cx+t*width+.05*fbm(y*.8,t*4,9);z=.025+.030*(1-(2*t)**2)+.014*fbm(x*3,y*3,5);verts.append((x,y,z))
for j in range(ny):
    for i in range(cols-1):a=j*cols+i;faces.append((a,a+1,a+cols+1,a+cols))
path=mesh_obj('SM_V4_Irregular_Muddy_Footpath',verts,faces,pathc,mud,True)
sub=path.modifiers.new('Micro terrain subdivision','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=1;sub.render_levels=1
tx=bpy.data.textures.new('V4_PathMicro','CLOUDS');tx.noise_scale=.18;tx.noise_depth=2;ds=path.modifiers.new('Wet ruts and clods','DISPLACE');ds.texture=tx;ds.strength=.018;ds.mid_level=.5
water=M['MAT_Q_Paddy_Water_Shallow']
for i in range(24):
    y=rng.uniform(-15,52);cx=path_x(y);px=cx+rng.uniform(-.22,.22);rx=rng.uniform(.04,.10);ry=rng.uniform(.08,.20);pz=.045
    vv=[(px+rx*math.cos(k*2*math.pi/16),y+ry*math.sin(k*2*math.pi/16),pz) for k in range(16)]
    po=mesh_obj(f'SM_V4_Path_Puddle_{i}',vv,[tuple(range(16))],waterc,puddle);so=po.modifiers.new('Thin puddle','SOLIDIFY');so.thickness=.01;so.offset=-1
grass_pts=[]
for by in [3.7,23.7,43.7,68.2,88.5]:
    cxp=path_x(by)
    for xa,xb in [(-55,cxp-.55),(cxp+.55,55)]:
        nx=max(8,int((xb-xa)/.45));vv=[];ff=[];cc=7
        for j in range(nx+1):
            x=xa+(xb-xa)*j/nx;w=.34+.05*fbm(x*.4,by,7)
            for i in range(cc):
                t=i/(cc-1)-.5;yy=by+t*w;z=.015+.06*(1-(2*t)**2)+.012*fbm(x*2,yy*3,8);vv.append((x,yy,z))
        for j in range(nx):
            for i in range(cc-1):a=j*cc+i;ff.append((a,a+1,a+cc+1,a+cc))
        mesh_obj(f'SM_V4_Earthen_Bund_{by}_{xa:.0f}',vv,ff,pathc,mud,True)
        for j in range(nx):
            x=xa+(xb-xa)*j/nx
            for sgn in [-1,1]:grass_pts.append((x,by+sgn*.17,.075))
y=-16
while y<54:
    cx=path_x(y)
    for sgn in [-1,1]:grass_pts.append((cx+sgn*.50,y,.05))
    y+=.6
grass_ng=bpy.data.node_groups.get('GN_Scatter_Q_BundGrass')
if grass_ng:scatter_points('SM_V4_Bund_Grass',grass_pts,veg,grass_ng,2718153,1.,.6,1.1)
# Foreground drain and bridge.
by=-3.2;cx=path_x(by)
box('SM_V4_Drain_Water',(cx,by,.022),(2.4,.50,.025),waterc,water,.004)
box('SM_V4_Drain_Bed',(cx,by,.008),(2.5,.58,.02),pathc,M['MAT_Q_Paddy_Mud_Bottom'])
for k in range(6):
    x=cx-.45+k*.18
    box(f'SM_V4_Bridge_Plank_{k}',(x,by,.115+rng.uniform(-.004,.004)),(.168,1.35,.045),pathc,wood,.008,rot=(rng.uniform(-.01,.01),rng.uniform(-.015,.015),rng.uniform(-.02,.02)))
for sx in [-1,1]:tube(f'SM_V4_Bridge_Bearer_{sx}',[(cx+sx*.40,by-.62,.075),(cx+sx*.40,by+.62,.075)],[.05,.05],pathc,wood,7)
for sx in [-1,1]:
    for sy in [-1,1]:box(f'SM_V4_Bridge_Post_{sx}_{sy}',(cx+sx*.48,by+sy*.60,.13),(.07,.07,.24),pathc,wood,.008)
box('SM_V4_Back_Marsh_Ground',(0,108,-.045),(250,44,.09),terrain,M['MAT_Q_Paddy_Mud_Bottom'])

# --- House wear: remove solid green skirts, cluster roof lichen ---------------
moss=M.get('MAT_Roof_Lichen_and_Soot')
if moss:
    for n in moss.node_tree.nodes:
        if n.type=='VALTORGB':
            for e,c in zip(n.color_ramp.elements,[(.045,.047,.028),(.085,.083,.045),(.13,.12,.07)]):e.color=(*c,1)
for o in bpy.data.objects:
    if o.type=='MESH' and 'IndividualOverlappingTiles' in o.name:
        for p in o.data.polygons:
            c=o.matrix_world@p.center;n=noise.noise(Vector((c.x*.35,c.y*.35,c.z*.25)))
            p.material_index=1 if (n>.48 and c.z<4.35) else 0
plaster=M.get('MAT_Q_Weathered_Lime_Wash')
if plaster:
    nt=plaster.node_tree;p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    src=next((l.from_socket for l in nt.links if l.to_node==p and l.to_socket.name=='Base Color'),None)
    if src:
        geo=nt.nodes.new('ShaderNodeNewGeometry');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(geo.outputs['Position'],sep.inputs['Vector'])
        mr=nt.nodes.new('ShaderNodeMapRange');mr.inputs['From Min'].default_value=.65;mr.inputs['From Max'].default_value=1.30;mr.inputs['To Min'].default_value=.32;mr.inputs['To Max'].default_value=0;mr.clamp=True;nt.links.new(sep.outputs['Z'],mr.inputs['Value'])
        mx=nt.nodes.new('ShaderNodeMixRGB');mx.blend_type='MULTIPLY';mx.inputs[2].default_value=(.42,.40,.30,1);nt.links.new(src,mx.inputs[1]);nt.links.new(mr.outputs['Result'],mx.inputs[0]);nt.links.new(mx.outputs['Color'],p.inputs['Base Color'])

# --- Lower, cooler, mistier Ghats; brighter photographic light ----------------
for name,f in [('SM_Q_Forested_Foothills',.85),('SM_Q_Middle_Ghat_Ridge',.70),('SM_Q_Far_Ghat_Massifs',.68)]:
    o=bpy.data.objects.get(name)
    if o:
        for v in o.data.vertices:v.co.z*=f
for o in bpy.data.objects:
    if o.name.startswith('SM_Q_Mist_Bank'):o.location.z*=.75;o.scale.z*=.75
for mn in ['MAT_Q_Ghat_ForestRock','MAT_Q_Distant_Ghat']:
    m=M.get(mn)
    if m:
        nt=m.node_tree;p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');src=next((l.from_socket for l in nt.links if l.to_node==p and l.to_socket.name=='Base Color'),None)
        if src:
            mx=nt.nodes.new('ShaderNodeMixRGB');mx.blend_type='MULTIPLY';mx.inputs[0].default_value=.50;mx.inputs[2].default_value=(.68,.78,.90,1);nt.links.new(src,mx.inputs[1]);nt.links.new(mx.outputs['Color'],p.inputs['Base Color'])
        for n in nt.nodes:
            if n.type=='MAP_RANGE' and n.inputs['To Max'].default_value<.02:n.inputs['To Max'].default_value=.020
w=s.world
for n in w.node_tree.nodes:
    if n.type=='BACKGROUND':n.inputs['Strength'].default_value=.95
sun=bpy.data.objects.get('LGT_Q_SoftMonsoonSun')
if sun:sun.data.energy=1.55;sun.data.angle=math.radians(14);sun.data.color=(1,.96,.89);sun.rotation_euler=Vector((.45,.35,-.82)).to_track_quat('-Z','Y').to_euler()
fill=bpy.data.objects.get('LGT_Q_Fill_SkyBounce')
if fill:fill.data.energy=25
s.view_settings.exposure=.15
try:s.view_settings.look='AgX - Base Contrast'
except Exception:pass
cam=bpy.data.objects['CAM_Q_Hero_LeadingBund'];cam.location=(-2.2,-13.0,1.58);cam.data.lens=36;aim(cam,(3,62,3.0));cam.data.dof.focus_distance=70;cam.data.dof.aperture_fstop=10;s.camera=cam
cd=bpy.data.cameras.new('CAM_V4_Coconut_Detail');cd.lens=50;cd.clip_end=1000;c2=bpy.data.objects.new('CAM_V4_Coconut_Detail',cd);cams.objects.link(c2);c2.location=(-8.5,-7.5,2.0);aim(c2,(-5.8,-1.0,11.5))

# Low valley haze to separate the paddy from the Ghats.
haze=bpy.data.materials.new('MAT_V4_Valley_Haze');haze.use_nodes=True;ht=haze.node_tree;ht.nodes.clear();ho=ht.nodes.new('ShaderNodeOutputMaterial');hv=ht.nodes.new('ShaderNodeVolumePrincipled');hv.inputs['Color'].default_value=(.72,.80,.85,1);hv.inputs['Density'].default_value=.006;hv.inputs['Anisotropy'].default_value=.25;ht.links.new(hv.outputs['Volume'],ho.inputs['Volume'])
box('SM_V4_Valley_Haze',(0,100,5),(260,90,12),atmo,haze)

# --- Render settings / pack ---------------------------------------------------
s.render.resolution_x=1600;s.render.resolution_y=900;s.render.resolution_percentage=100;s.cycles.samples=64;s.cycles.adaptive_threshold=.015;s.cycles.adaptive_min_samples=16;s.cycles.use_denoising=True;s.cycles.denoiser='OPENIMAGEDENOISE'
try:s.cycles.denoising_input_passes='RGB_ALBEDO'
except Exception:pass
try:s.cycles.denoising_prefilter='FAST'
except Exception:pass
s.render.use_persistent_data=False;s.cycles.volume_bounces=1;s.cycles.transparent_max_bounces=8
for _ in range(3):
    try:bpy.ops.outliner.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
    except Exception:break
def _final_exclude(lc):
    if lc.collection.name.startswith('LIB_') or lc.collection.name=='COL_AssetLibrary':lc.exclude=True
    for ch in lc.children:_final_exclude(ch)
_final_exclude(bpy.context.view_layer.layer_collection)
bpy.ops.file.pack_all();out=ROOT/'output/Kerala_Coconut_Realism.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
manifest={'revision':REV,'build_seconds':round(time.time()-T0,2),'blend':str(out.relative_to(ROOT)),'blend_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'user_coconut_instances':len(palm_pos),'rice_instance_points':bpy.data.objects['SM_Paddy_Q_RowInstances'].get('instance_points'),'objects':len(bpy.data.objects),'materials':len(bpy.data.materials),'packed_images':sum(1 for i in bpy.data.images if i.packed_file)}
(ROOT/'review/v4/build_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2));sys.stdout.flush();os._exit(0)
