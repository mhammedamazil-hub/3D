#!/usr/bin/env python3
"""Kerala quality-first v3. Native editable Blender scene, no photo backplate.
Run: sh scripts/blender-py scripts/build_kerala_quality.py
Preserves the old Kerala house at the path end and paddy/mountain composition while
replacing lawn-like rice, concrete bunds, cartoon palms/bananas and repeated saplings
with row-planted paddy over open water, earthen bunds, detailed coconut palms,
Infinigen banana/broadleaf assets, scanned CC0 trees/rocks and higher-resolution PBR.
"""
import json, math, random, sys, time, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from kerala_config import *
from kerala_helpers import *
from kerala_materials import build_materials
from kerala_vegetation import blade_mesh
from kerala_house import build_house
from kerala_photoreal import metal_vent_and_wear, import_collection
from kerala_quality import *
T0=time.time();REV='kerala-v3.0-quality';BLEND3=OUTPUT/'Kerala_Quality.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.name='Monsoon Light — Kerala Quality'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
scene.render.resolution_x=2560;scene.render.resolution_y=1440;scene.render.resolution_percentage=100
scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=1
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except Exception:pass
scene.view_settings.exposure=.0
scene['revision']=REV;scene['seed']=SEED;scene['units']='1 Blender unit = 1 metre'
scene['reference_provenance']='User references image_cccffb39.jpg and image_94158290.jpg analyzed only; never used as backplates or projected photos.'
M=quality_materials(build_materials())
terrain=collection('COL_Terrain');paddy=collection('COL_Paddies');waterc=collection('COL_Water');pathc=collection('COL_Path_and_Bunds');veg=collection('COL_FieldVegetation');mount=collection('COL_Mountains');atmo=collection('COL_Atmosphere');lights=collection('COL_Lights');cams=collection('COL_Cameras');helpers=collection('COL_Helpers');props=collection('COL_House_Props_Quality')
lib_parent=collection('COL_AssetLibrary')
box('SM_Regional_Ground_Base',(0,55,-.26),(380,230,.22),terrain,M['paddy_mud'])

# --- Row-planted rice with visible shallow water -----------------------------
rice_lib=collection('COL_Library_RiceClumps',lib_parent)
for i in range(8):
    rng=random.Random(SEED+100+i)
    blade_mesh(f'SM_Rice_Q_Clump_v{i:02d}',rng,rice_lib,[M['rice'],M['rice_light']],blades=10+i%2,hmin=.48,hmax=.82,width=.008,lean=.24,segs=4)
grass_lib=collection('COL_Library_BundGrass',lib_parent)
for i in range(5):
    rng=random.Random(SEED+200+i)
    blade_mesh(f'SM_Bund_Q_Grass_v{i:02d}',rng,grass_lib,[M['grass'],M['rice_light']],blades=7,hmin=.05,hmax=.16,width=.005,lean=.08,segs=3)
rice_ng=scatter_group('GN_Scatter_Q_PaddyRows',rice_lib,8)
grass_ng=scatter_group('GN_Scatter_Q_BundGrass',grass_lib,5)

def plot_bounds(y,side):
    px=path_x(y)
    if side=='L0':return -FIELD_HALF_WIDTH,-28.0
    if side=='L1':return -26.8,px-.82
    if side=='R1':return px+.82,27.0
    return 28.2,FIELD_HALF_WIDTH
rice_points=[];plot_count=0
for bi,(y0,y1) in enumerate(PADDY_BANDS):
    for side in ['L0','L1','R1','R0']:
        plot_count+=1;nx=10;ny=14;verts=[];faces=[];top=.004+bi*.001
        for j in range(ny+1):
            y=y0+(y1-y0)*j/ny;l,r=plot_bounds(y,side)
            for i in range(nx+1):verts.append((l+(r-l)*i/nx,y,top))
        for j in range(ny):
            for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
        w=mesh_obj(f'SM_Paddy_Water_Plot_{bi}_{side}',verts,faces,waterc,M['water'],True)
        sol=w.modifiers.new('Closed shallow water 5 cm','SOLIDIFY');sol.thickness=.05;sol.offset=-1;sol.use_rim=True;w['IOR']=1.333;w['depth_m']=.05
        mesh_obj(f'SM_Paddy_Mud_Bottom_{bi}_{side}',[(x,y,z-.085) for x,y,z in verts],faces,paddy,M['paddy_mud'],True)
        l0,r0=plot_bounds(y0,side);l1,r1=plot_bounds(y1,side);avg=((r0-l0)+(r1-l1))/2
        sx=.32 if y1<44 else .38;sy=.30 if y1<44 else .36;cols=max(2,int(avg/sx));rng=random.Random(SEED+bi*20+ord(side[0]))
        y=y0+.32
        while y<y1-.28:
            l,r=plot_bounds(y,side)
            for k in range(cols):
                u=(k+.5)/cols;x=l+(r-l)*u+rng.uniform(-.018,.018)
                if rng.random()<.045:continue
                rice_points.append((x+rng.uniform(-.012,.012),y+rng.uniform(-.018,.018),-.045))
            y+=sy
rice=scatter_points('SM_Paddy_Q_RowInstances',rice_points,veg,rice_ng,SEED+700,1.,.82,1.20)
rice['planting']='Transplanted row clumps with open water between rows; rooted below shallow water; non-realized GN instances.'

# --- Thin irregular earthen bunds / wet muddy path ---------------------------
rng=random.Random(SEED+710)
y0,y1=-20,56;ny=150;verts=[];faces=[]
for j in range(ny+1):
    y=y0+(y1-y0)*j/ny;cx=path_x(y);width=.98+.09*math.sin(y*.17)+.06*fbm(y*.31,0,3)
    for i in range(7):
        t=i/6;x=cx+(t-.5)*width;z=.085+.018*fbm(x*1.7,y*1.3,5)+(.02 if i in {0,6} else 0)
        verts.append((x,y,z))
for j in range(ny):
    for i in range(6):a=j*7+i;faces.append((a,a+1,a+8,a+7))
mesh_obj('SM_Q_Wet_Earthen_Footpath',verts,faces,pathc,M['mud'],True)
path_pts=[];y=y0
while y<y1:
    cx=path_x(y)
    for s in [-1,1]:path_pts.append((cx+s*rng.uniform(.50,.66),y+rng.uniform(-.08,.08),.11))
    y+=.55
for by in [3.7,23.7,43.7,68.2]:
    verts=[];faces=[];col_index={};valid=[]
    for j in range(81):
        x=-55+110*j/80
        if abs(x-path_x(by))<.70:continue
        col_index[j]=len(valid);valid.append(j)
        for i in range(5):
            t=i/4;yy=by+(t-.5)*.46;z=.13+.025*fbm(x*.8,yy*2,7)+(.02 if i in {0,4} else 0)
            verts.append((x,yy,z))
    for jj in range(len(valid)-1):
        j=valid[jj]
        if valid[jj+1]!=j+1:continue
        a=col_index[j]*5
        for i in range(4):faces.append((a+i,a+i+1,a+i+6,a+i+5))
    mesh_obj(f'SM_Q_Transverse_Earthen_Bund_{by}',verts,faces,pathc,M['mud'],True)
    for k in range(160):
        x=rng.uniform(-54,54)
        if abs(x-path_x(by))>1.0:path_pts.append((x+rng.uniform(-.05,.05),by+rng.uniform(-.22,.22),.14))
scatter_points('SM_Q_Bund_Grass_Instances',path_pts,veg,grass_ng,SEED+720,1.,.7,1.3)
# Path puddles and laterite chips.
for i in range(34):
    y=rng.uniform(-16,52);cx=path_x(y);s=rng.choice([-1,1]);px=cx+s*rng.uniform(.18,.42);rx=rng.uniform(.07,.20);ry=rng.uniform(.14,.38);pz=.112
    vv=[(px+rx*math.cos(k*2*math.pi/18),y+ry*math.sin(k*2*math.pi/18),pz) for k in range(18)]
    po=mesh_obj(f'SM_Q_Path_Puddle_{i}',vv,[tuple(range(18))],waterc,M['water']);so=po.modifiers.new('Thin puddle','SOLIDIFY');so.thickness=.018;so.offset=-1
# Timber drain crossing.
y=18.0;cx=path_x(y)
box('SM_Q_Drain_Water',(cx,y,.045),(2.1,.58,.03),waterc,M['water'],.004)
box('SM_Q_Drain_DarkBed',(cx,y,.018),(2.2,.66,.025),pathc,M['paddy_mud'])
for k in range(5):
    x=cx-.72+k*.36
    box(f'SM_Q_Timber_Crossing_Plank_{k}',(x,y,.205+rng.uniform(-.006,.006)),(.32,1.0,.05),pathc,M['wood_planks'],.01,rot=(rng.uniform(-.015,.015),rng.uniform(-.025,.025),rng.uniform(-.03,.03)))
for sx in [-1,1]:tube(f'SM_Q_Timber_Bearer_{sx}',[(cx+sx*.66,y-.44,.15),(cx+sx*.66,y+.44,.15)],[.06,.06],pathc,M['darkwood'],7)

# --- Old Kerala house destination -------------------------------------------
box('SM_Q_House_Earthen_Court',(HOUSE_X,HOUSE_Y+1,.012),(19,16,.045),terrain,M['mud'],.02)
build_house(M);metal_vent_and_wear(M)
# Potted plants on veranda/court (CC0 Poly Haven).
for aid,locs in [('potted_plant_01',[(HOUSE_X-4.6,HOUSE_Y-5.0,.70),(HOUSE_X+4.9,HOUSE_Y-4.9,.70),(HOUSE_X-5.6,HOUSE_Y-3.6,.70),(HOUSE_X+5.7,HOUSE_Y-3.4,.70)])]:
    p=Q/'potted'/f'{aid}.blend'
    if p.exists():
        with bpy.data.libraries.load(str(p),link=False) as (df,dt):dt.objects=list(df.objects)
        for o in dt.objects:
            if o:
                for loc in locs:
                    cp=o.copy();cp.data=o.data;props.objects.link(cp);cp.location=(loc[0]+o.location.x,loc[1]+o.location.y,loc[2]+o.location.z);cp.rotation_euler=o.rotation_euler;cp.scale=o.scale

# --- Western Ghat ridges (defined before forest scattering) ------------------
def ghat_height(x,y,y0,y1,peaks,seed):
    t=(y-y0)/(y1-y0);edge=math.sin(math.pi*max(0,min(1,t)))**.70;h=0.
    for cx,cy,ht,wx,wy in peaks:h+=ht*math.exp(-((x-cx)/wx)**2-((y-cy)/wy)**2)
    wx=x+24*fbm(x*.008,y*.008,seed+2,3);wy=y+20*fbm(x*.009,y*.009,seed+5,3)
    n=fbm(wx*.013,wy*.013,seed,5);rr=1-abs(fbm(wx*.028,wy*.028,seed+9,4));ridge=rr**1.6
    spur=20*math.exp(-((x+70)/90)**2-((y-(y0+y1)/2)/70)**2)+16*math.exp(-((x-110)/85)**2-((y-(y0+y1)/2)/65)**2)
    return max(-.2,.46*edge*(h*(.58+.42*ridge)+26*n+11*fbm(wx*.07,wy*.07,seed+4,4)+10*(ridge-.5)+.70*spur))
FOOT_PEaks=[(-150,250,46,150,65),(135,270,54,170,70),(0,290,32,130,60)]
def ridge(name,y0,y1,peaks,mat,nx=360,ny=140,seed=0):
    verts=[];faces=[]
    for j in range(ny+1):
        y=y0+(y1-y0)*j/ny;t=j/ny;edge=math.sin(math.pi*t)**.70
        for i in range(nx+1):x=-680+1360*i/nx;verts.append((x,y,ghat_height(x,y,y0,y1,peaks,seed)))
    for j in range(ny):
        for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    o=mesh_obj(name,verts,faces,mount,mat,True)
    tx=bpy.data.textures.new(name+'_Crag_Clouds','CLOUDS');tx.noise_scale=24 if seed<20 else 38;tx.noise_depth=4
    md=o.modifiers.new('Editable rocky ridge displacement','DISPLACE');md.texture=tx;md.strength=3.0 if seed<20 else (6.0 if seed<30 else 9.0);md.mid_level=.46;md.direction='NORMAL'
    return o
ridge('SM_Q_Forested_Foothills',180,340,FOOT_PEaks,M['rock'],260,100,11)
ridge('SM_Q_Middle_Ghat_Ridge',340,580,[(-205,450,138,170,95),(170,480,156,190,100),(25,520,110,135,85)],M['rock'],300,115,22)
ridge('SM_Q_Far_Ghat_Massifs',560,950,[(-260,740,192,230,150),(230,780,212,250,160),(40,820,178,170,130)],M['far_rock'],300,120,33)

# --- Botanical / scanned tree library ---------------------------------------
broad_coll,bananas=import_botanical(lib_parent)
palm_variants=build_palm_library(M,lib_parent,4)
jac=import_prepared_model('jacaranda_tree',lib_parent)
small=import_prepared_model('tree_small_02',lib_parent)
island=import_prepared_model('island_tree_03',lib_parent)
rockface=import_prepared_model('rock_face_02',lib_parent)
boulder=import_prepared_model('boulder_01',lib_parent)
stone=import_prepared_model('stone_01',lib_parent)
rock07=import_prepared_model('rock_07',lib_parent)
small_bg=small
island_bg=island
# Light hero LOD reduction keeps scanned silhouettes while controlling file size.
for c,ratio in [(jac,.60),(small,.60),(island,.75)]:
    if not c:continue
    for o in c.objects:
        if o.type=='MESH' and len(o.data.polygons)>120000:
            bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
            md=o.modifiers.new('Hero LOD','DECIMATE');md.ratio=ratio
            try:bpy.ops.object.modifier_apply(modifier=md.name)
            except Exception:o.modifiers.remove(md)
# Palms framing the composition.
palm_pos=[(-16,8,1.0),(20,14,1.05),(-26,24,.95),(29,30,1.0),(-18,42,.9),(22,48,.95),(-34,58,1.05),(36,64,1.0),(-12,76,.9),(16,80,.95),(-44,20,.9),(46,28,.95)]
for i,(x,y,s) in enumerate(palm_pos):collection_instance(f'SM_Q_Coconut_Palm_{i:02d}',palm_variants[i%len(palm_variants)],(x,y,-.05),s,rng.uniform(0,6.28),veg)
# Banana clumps from Infinigen monocots.
banana_pos=[(HOUSE_X-8,HOUSE_Y-3),(HOUSE_X+8.5,HOUSE_Y-2),(HOUSE_X-9,HOUSE_Y+4),(HOUSE_X+9,HOUSE_Y+5),(-8,38),(12,46),(-14,52),(18,58),(-22,68),(24,72)]
if bananas:
    for i,(x,y) in enumerate(banana_pos):
        for k in range(3):
            src=bananas[(i+k)%len(bananas)];o=linked_copy(src,f'SM_Q_Banana_{i}_{k}',(x+rng.uniform(-.45,.45),y+rng.uniform(-.45,.45),-.03),veg,rng.uniform(.85,1.25),rot=(0,0,rng.uniform(0,6.28)))
# Hero scanned trees.
if jac:
    collection_instance('SM_Q_Jacaranda_Left',jac,(-20,32,-.05),.55,rng.uniform(0,6.28),veg)
    collection_instance('SM_Q_Jacaranda_Right',jac,(26,46,-.05),.50,rng.uniform(0,6.28),veg)
if small:
    for i,(x,y,s) in enumerate([(-12,52,1.2),(18,66,1.1),(-30,72,1.3),(32,80,1.2)]):collection_instance(f'SM_Q_TreeSmall_{i}',small,(x,y,-.05),s,rng.uniform(0,6.28),veg)
if island:
    for i,(x,y,s) in enumerate([(HOUSE_X-11,HOUSE_Y+2,1.4),(HOUSE_X+12,HOUSE_Y+3,1.3),(-6,60,1.2),(14,72,1.3)]):collection_instance(f'SM_Q_IslandTree_{i}',island,(x,y,-.05),s,rng.uniform(0,6.28),veg)
# Infinigen broadleaf generated and retained in library, but live-GN leaf collections
# did not survive view-layer exclusion in scene instances; use scanned trees here.
for i in range(6):
    x=rng.uniform(-55,55);y=rng.uniform(78,112)
    if abs(x-HOUSE_X)<10 and y<80:continue
    c=rng.choice([cc for cc in [small,island] if cc]) if (small or island) else None
    if c:collection_instance(f'SM_Q_MidBroadleaf_{i}',c,(x,y,-.05),rng.uniform(1.1,1.8),rng.uniform(0,6.28),veg)
# Mixed irregular forest belt (not repeated lollipops).
forest_libs=[c for c in [small_bg,island_bg] if c]
tree_pts=[]
if forest_libs:
    for i in range(100):
        x=rng.uniform(-95,95);y=rng.uniform(94,155)
        if abs(x-HOUSE_X)<9 and y<100:continue
        c=rng.choice(forest_libs);s=rng.uniform(.9,1.7)
        collection_instance(f'SM_Q_ForestBelt_{i}',c,(x,y,-.05),s,rng.uniform(0,6.28),veg);tree_pts.append((x,y))
    foot_libs=[c for c in [island_bg] if c]
    for i in range(220):
        x=rng.uniform(-210,210);y=rng.uniform(185,330);z=ghat_height(x,y,180,340,FOOT_PEaks,11)-.35
        if 1.0<z<52:
            c=rng.choice(foot_libs);collection_instance(f'SM_Q_Foothill_Forest_{i}',c,(x,y,z),rng.uniform(.45,.95),rng.uniform(0,6.28),veg);tree_pts.append((x,y))
# Understory fern/anthurium near path/house.
under=[]
for name in ['fern_02','anthurium_botany_01']:
    c=import_collection(ROOT/'assets/models/polyhaven',name)
    if c:under.append(c)
under_pts=[(rng.uniform(-34,34),rng.uniform(48,82),-.03) for _ in range(150)]
under_pts += [(path_x(y)+rng.choice([-1,1])*rng.uniform(1.0,2.6),y,-.02) for y in [rng.uniform(-8,52) for _ in range(40)]]
if under:
    ulib=collection('COL_Library_ScannedUnderstory',lib_parent)
    for c in under:
        if c.name not in ulib.children:ulib.children.link(c)
    ng=scatter_group('GN_Scatter_Q_Understory',ulib,len(under));scatter_points('SM_Q_Scanned_Understory',under_pts,veg,ng,SEED+760,1.,.45,.95)
# Rocky outcrops and path stones.
rock_libs=[c for c in [rockface,boulder,rock07] if c]
if rock_libs:
    for i in range(90):
        x=rng.uniform(-240,240);y=rng.uniform(200,560);z=ghat_height(x,y,180,340,FOOT_PEaks,11) if y<340 else ghat_height(x,y,340,580,[(-205,450,138,170,95),(170,480,156,190,100),(25,520,110,135,85)],22)
        c=rng.choice(rock_libs);s=rng.uniform(.4,1.4)
        collection_instance(f'SM_Q_Ghat_Rock_{i}',c,(x,y,z-.4),s,rng.uniform(0,6.28),mount)
# --- Mist, light, cameras ----------------------------------------------------
def mist_banks_q(atmo):
    m=bpy.data.materials.new('MAT_Q_Mist_Bank_Volume');m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');vs=nt.nodes.new('ShaderNodeVolumeScatter');vs.inputs['Color'].default_value=(.82,.88,.92,1);vs.inputs['Anisotropy'].default_value=.50
    ns=nt.nodes.new('ShaderNodeTexNoise');ns.inputs['Scale'].default_value=.015;ns.inputs['Detail'].default_value=3;mr=nt.nodes.new('ShaderNodeMapRange');mr.inputs['From Min'].default_value=.3;mr.inputs['From Max'].default_value=.8;mr.inputs['To Min'].default_value=.003;mr.inputs['To Max'].default_value=.010;nt.links.new(ns.outputs['Fac'],mr.inputs['Value']);nt.links.new(mr.outputs['Result'],vs.inputs['Density']);nt.links.new(vs.outputs['Volume'],out.inputs['Volume'])
    for i,(y0,y1,z0,z1) in enumerate([(215,300,10,40),(380,480,24,64),(600,720,46,98)]):box(f'SM_Q_Mist_Bank_{i}',(0,(y0+y1)/2,(z0+z1)/2),(640,y1-y0,z1-z0),atmo,m)
mist_banks_q(atmo);setup_quality_world(scene)
sun_data=bpy.data.lights.new('LGT_Q_SoftMonsoonSun','SUN');sun_data.energy=1.25;sun_data.angle=math.radians(4.0);sun_data.color=(1.0,.94,.84)
sun=bpy.data.objects.new('LGT_Q_SoftMonsoonSun',sun_data);lights.objects.link(sun);sun.location=(80,90,120);sun.rotation_euler=Vector((-.42,-.55,-.72)).to_track_quat('-Z','Y').to_euler()
fill_data=bpy.data.lights.new('LGT_Q_Fill_SkyBounce','AREA');fill_data.energy=40;fill_data.shape='DISK';fill_data.size=40;fill_data.color=(.74,.83,1.0)
fill=bpy.data.objects.new('LGT_Q_Fill_SkyBounce',fill_data);lights.objects.link(fill);fill.location=(-18,28,24);aim(fill,(3,60,2))
cd=bpy.data.cameras.new('CAM_Q_Hero_38mm');cd.lens=38;cd.clip_end=3200;cd.dof.use_dof=True;cd.dof.focus_distance=68;cd.dof.aperture_fstop=9.0
cam=bpy.data.objects.new('CAM_Q_Hero_LeadingBund',cd);cams.objects.link(cam);cam.location=(-1.6,-11.5,1.62);aim(cam,(3.0,62.0,3.2));scene.camera=cam
cd2=bpy.data.cameras.new('CAM_Q_House_Detail');cd2.lens=58;cd2.clip_end=1000
cam2=bpy.data.objects.new('CAM_Q_House_Detail',cd2);cams.objects.link(cam2);cam2.location=(HOUSE_X-12,HOUSE_Y-19,3.0);aim(cam2,(HOUSE_X,HOUSE_Y-1,2.8))
cd3=bpy.data.cameras.new('CAM_Q_Foreground_Detail');cd3.lens=50;cd3.clip_end=500
cam3=bpy.data.objects.new('CAM_Q_Foreground_Detail',cd3);cams.objects.link(cam3);cam3.location=(-.5,-6,1.0);aim(cam3,(2,14,.45))
hr=box('SM_Scale_Reference_1p70m',(HOUSE_X-2,HOUSE_Y-6,.85),(.35,.25,1.70),helpers,M['stone']);hr.hide_render=True;hr.hide_set(True)

def find_lc(lc,name):
    if lc.collection.name==name:return lc
    for ch in lc.children:
        r=find_lc(ch,name)
        if r:return r
lib_lc=find_lc(bpy.context.view_layer.layer_collection,'COL_AssetLibrary')
if lib_lc:lib_lc.exclude=True
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=128;scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.012;scene.cycles.adaptive_min_samples=24;scene.cycles.use_denoising=True;scene.cycles.denoiser='OPENIMAGEDENOISE'
scene.cycles.max_bounces=8;scene.cycles.diffuse_bounces=4;scene.cycles.glossy_bounces=4;scene.cycles.transmission_bounces=6;scene.cycles.volume_bounces=1;scene.cycles.transparent_max_bounces=8;scene.cycles.caustics_reflective=False;scene.cycles.caustics_refractive=False;scene.cycles.blur_glossy=1.0
scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.use_persistent_data=False
scene.view_layers[0].use_pass_mist=True;scene.view_layers[0].use_pass_z=True
scene.use_nodes=True;nt=scene.node_tree;nt.nodes.clear();rl=nt.nodes.new('CompositorNodeRLayers');gl=nt.nodes.new('CompositorNodeGlare');gl.glare_type='FOG_GLOW';gl.quality='MEDIUM';gl.threshold=1.9;gl.mix=-.95;gl.size=7;comp=nt.nodes.new('CompositorNodeComposite');nt.links.new(rl.outputs['Image'],gl.inputs['Image']);nt.links.new(gl.outputs['Image'],comp.inputs['Image'])
OUTPUT.mkdir(exist_ok=True);REVIEW.mkdir(exist_ok=True)
for _ in range(3):
    try:bpy.ops.outliner.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
    except Exception:break
# Keep the delivered blend self-contained but under snapshot budget: recompress
# oversized scans before packing (4K surface maps -> 2K JPEG; tree/rock scans -> 1K).
import io
from PIL import Image
OPT=Q/'optimized';OPT.mkdir(exist_ok=True)
for img in list(bpy.data.images):
    if img.source!='FILE' or not img.size[0]:continue
    nm=(img.name+' '+(img.filepath or '')).lower()
    if any(k in nm for k in ['.hdr','.exr']) and 'overcast' not in nm:continue
    if 'overcast_soil' in nm or 'kloofendal' in nm:
        try:
            img.scale(1024,512);out=OPT/'overcast_soil_1k.hdr';img.filepath_raw=str(out);img.file_format='HDR';img.save()
            if img.packed_file:img.unpack(method='REMOVE')
            img.filepath=str(out);img.reload();img.pack()
        except Exception as e:print('HDRI_OPT_SKIP',repr(e))
        continue
    target=1024
    if any(k in nm for k in ['jacaranda','tree_small','island_tree','rock_face','boulder','coast_rocks','stone_01','rock_07','potted_plant']):target=512
    try:
        if img.packed_file:data=bytes(img.packed_file.data)
        else:
            fp=bpy.path.abspath(img.filepath)
            if not os.path.exists(fp):continue
            data=open(fp,'rb').read()
        im=Image.open(io.BytesIO(data));im.load()
        if max(im.size)>target:im=im.resize((target,target),Image.LANCZOS)
        has_alpha=(im.mode in {'RGBA','LA'}) or ('transparency' in im.info)
        if has_alpha:
            out=OPT/(img.name.replace('/','_')+'.png');im.save(out,optimize=True)
        else:
            im=im.convert('RGB');out=OPT/(img.name.replace('/','_')+'.jpg');im.save(out,quality=90 if 'nor' in nm else 86,optimize=True)
        cs=img.colorspace_settings.name
        if img.packed_file:
            try:img.unpack(method='REMOVE')
            except Exception:pass
        img.filepath=str(out);img.source='FILE';img.reload()
        try:img.colorspace_settings.name=cs
        except Exception:pass
        try:img.pack()
        except Exception as e:print('IMG_PACK_SKIP',img.name,repr(e))
    except Exception as e:
        print('IMG_OPT_SKIP',img.name,repr(e))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(BLEND3),compress=True)
unique_tris=sum(sum(len(p.vertices)-2 for p in m.polygons) for m in bpy.data.meshes)
manifest={'revision':REV,'seed':SEED,'build_seconds':round(time.time()-T0,2),'objects':len(bpy.data.objects),'meshes':len(bpy.data.meshes),'materials':len(bpy.data.materials),'unique_mesh_triangles':unique_tris,'rice_instance_points':len(rice_points),'bund_grass_points':len(path_pts),'tree_instances':len(tree_pts)+len(palm_pos)+6,'palm_instances':len(palm_pos),'banana_clumps':len(banana_pos),'paddy_plots':plot_count,'infinigen_broadleaf':bool(broad_coll),'infinigen_bananas':len(bananas) if bananas else 0,'scanned_trees':[c.name for c in [jac,small,island] if c],'scanned_rocks':[c.name for c in [rockface,boulder,stone,rock07] if c],'blend':str(BLEND3),'resolution':[2560,1440]}
(REVIEW/'build_manifest_v3.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2));sys.stdout.flush();os._exit(0)
