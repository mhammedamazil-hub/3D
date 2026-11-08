#!/usr/bin/env python3
"""Kerala photoreal revision v2. Native editable Blender scene, no photo backplate.
Run: sh scripts/blender-py scripts/build_kerala_photoreal.py
Preserves the v1 house destination (path ends at the tharavad steps) while replacing
sparse procedural crowns with CC0 library/sapling trees, scanned PBR wear, finer rice,
a wet footprinted bund, timber drain crossing, rocky mist-layered Ghats and HDRI light.
"""
import json, math, random, sys, time, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from kerala_config import *
from kerala_helpers import *
from kerala_materials import build_materials
from kerala_vegetation import blade_mesh, make_palms, make_bananas
from kerala_house import build_house
from kerala_photoreal import *

T0=time.time();REV='kerala-v2.0-photoreal';BLEND2=OUTPUT/'Kerala_Photoreal.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.name='Monsoon Light — Kerala Photoreal'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
scene.render.resolution_x=RES_X;scene.render.resolution_y=RES_Y;scene.render.resolution_percentage=100
scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=1
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Base Contrast'
except Exception:pass
scene.view_settings.exposure=.20
scene['revision']=REV;scene['seed']=SEED;scene['units']='1 Blender unit = 1 metre'
scene['reference_provenance']='User references image_cccffb39.jpg and image_94158290.jpg analyzed only; never used as backplates or projected photos.'
M=upgrade_materials(build_materials())
terrain=collection('COL_Terrain');paddy=collection('COL_Paddies');waterc=collection('COL_Water');pathc=collection('COL_Path_and_Bunds');veg=collection('COL_FieldVegetation');mount=collection('COL_Mountains');atmo=collection('COL_Atmosphere');lights=collection('COL_Lights');cams=collection('COL_Cameras');helpers=collection('COL_Helpers')
box('SM_Regional_Ground_Base',(0,55,-.24),(360,210,.22),terrain,M['paddy_mud'])

# Fine transplanted rice: narrower blades, denser irregular rows, young monsoon tips.
rice_lib=collection('COL_Library_RiceClumps',collection('COL_AssetLibrary'))
for i in range(9):
    rng=random.Random(SEED+100+i)
    blade_mesh(f'SM_Rice_FineClump_v{i:02d}',rng,rice_lib,[M['rice'],M['rice_light']],blades=12,hmin=.22,hmax=.48,width=.010,lean=.22,segs=4)
grass_lib=collection('COL_Library_BundGrass',collection('COL_AssetLibrary'))
for i in range(6):
    rng=random.Random(SEED+200+i)
    blade_mesh(f'SM_Bund_FineGrass_v{i:02d}',rng,grass_lib,[M['grass'],M['rice_light']],blades=9,hmin=.05,hmax=.18,width=.006,lean=.10,segs=3)
rice_ng=scatter_group('GN_Scatter_FinePaddyRows_v02',rice_lib,9)
grass_ng=scatter_group('GN_Scatter_FineBundGrass_v02',grass_lib,6)

def plot_bounds(y,side):
    px=path_x(y)
    if side=='L0':return -FIELD_HALF_WIDTH,-28.0
    if side=='L1':return -26.8,px-1.18
    if side=='R1':return px+1.18,27.0
    return 28.2,FIELD_HALF_WIDTH

rice_points=[];plot_count=0
for bi,(y0,y1) in enumerate(PADDY_BANDS):
    for side in ['L0','L1','R1','R0']:
        plot_count+=1;nx=10;ny=14;verts=[];faces=[];top=.006+bi*.0015
        for j in range(ny+1):
            y=y0+(y1-y0)*j/ny;l,r=plot_bounds(y,side)
            for i in range(nx+1):verts.append((l+(r-l)*i/nx,y,top))
        for j in range(ny):
            for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
        w=mesh_obj(f'SM_Paddy_Water_Plot_{bi}_{side}',verts,faces,waterc,M['water'],True)
        sol=w.modifiers.new('Closed shallow water boundary 7 cm','SOLIDIFY');sol.thickness=.07;sol.offset=-1;sol.use_rim=True;w['IOR']=1.333;w['depth_m']=.07
        mesh_obj(f'SM_Paddy_Mud_Bottom_{bi}_{side}',[(x,y,z-.10) for x,y,z in verts],faces,paddy,M['paddy_mud'],True)
        l0,r0=plot_bounds(y0,side);l1,r1=plot_bounds(y1,side);avg=((r0-l0)+(r1-l1))/2
        sx=.245 if y1<44 else .32;sy=.225 if y1<44 else .30;cols=max(2,int(avg/sx));rng=random.Random(SEED+bi*20+ord(side[0]))
        y=y0+.30
        while y<y1-.25:
            l,r=plot_bounds(y,side)
            for k in range(cols):
                u=(k+.5)/cols;x=l+(r-l)*u+rng.uniform(-.020,.020)
                if rng.random()<.035:continue
                rice_points.append((x+rng.uniform(-.015,.015),y+rng.uniform(-.020,.020),-.065))
            y+=sy
rice=scatter_points('SM_Paddy_FineRice_RowInstances',rice_points,veg,rice_ng,SEED+700,1.,.80,1.22)
rice['planting']='Denser curved row-following fine clumps, seeded skips, rooted below shallow water; non-realized GN instances.'

# Worn muddy bund with real shallow footprints and irregular wet shoulders.
rng=random.Random(SEED+710);footprints=[]
for j in range(105):
    y=-18+j*.70;cx=path_x(y);footprints.append((cx+(-.17 if j%2 else .17)+rng.uniform(-.05,.05),y+rng.uniform(-.08,.08)))
verts=[];faces=[];ny=420;nx=20;y0,y1=-22,55.8
for j in range(ny+1):
    y=y0+(y1-y0)*j/ny;cx=path_x(y);width=1.76+.09*math.sin(y*.13)+.04*fbm(y*.3,0,3)
    for i in range(nx+1):
        u=-1+2*i/nx;x=cx+u*width/2;z=.065+.155*(1-u*u)+.014*fbm(x*3,y*3,8)
        for fx,fy in footprints:
            dy=y-fy
            if abs(dy)<.45:z-=.030*math.exp(-((x-fx)/.105)**2-(dy/.21)**2)
        verts.append((x,y,z))
for j in range(ny):
    for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
mesh_obj('SM_Wet_Footprinted_Earthen_Footpath',verts,faces,pathc,M['mud'],True)
path_pts=[];y=y0
while y<y1:
    cx=path_x(y)
    for k in range(6):path_pts.append((cx+rng.uniform(-.25,.25),y+rng.uniform(-.06,.06),.205))
    for s in [-1,1]:path_pts.append((cx+s*rng.uniform(.72,.92),y+rng.uniform(-.08,.08),.095))
    y+=.10
for by in [3.7,23.75,43.75,55.0,67.7]:
    verts=[];faces=[]
    for j in range(221):
        x=-55+j*.5
        for i in range(7):u=-1+2*i/6;verts.append((x,by+u*.48,.05+.13*(1-u*u)+.015*fbm(x*2,by*2,5)))
    for j in range(220):
        for i in range(6):a=j*7+i;faces.append((a,a+7,a+8,a+1))
    mesh_obj(f'SM_Transverse_Bund_{by}',verts,faces,pathc,M['mud'],True)
    for x in [i*.20-55 for i in range(550)]:
        if abs(x-path_x(by))>1.0:path_pts.append((x+rng.uniform(-.06,.06),by+rng.uniform(-.36,.36),.155))
scatter_points('SM_Bund_FineGrass_Instances',path_pts,veg,grass_ng,SEED+720,1.,.7,1.35)
for i in range(34):
    y=rng.uniform(40,55);x=path_x(y)+rng.choice([-1,1])*rng.uniform(.55,.88)
    box(f'SM_Worn_Laterite_EdgeStone_{i}',(x,y,.15),(rng.uniform(.14,.30),rng.uniform(.12,.24),.06),pathc,M['laterite'],.02,rot=(0,0,rng.uniform(0,3)))
for i in range(26):
    y=rng.uniform(-14,52);cx=path_x(y);s=rng.choice([-1,1]);px=cx+s*rng.uniform(.50,.74);rx=rng.uniform(.08,.22);ry=rng.uniform(.16,.40);pz=.118
    vv=[(px+rx*math.cos(2*math.pi*k/18),y+ry*math.sin(2*math.pi*k/18),pz) for k in range(18)]
    po=mesh_obj(f'SM_Bund_Rain_Puddle_{i}',vv,[tuple(range(18))],waterc,M['water']);so=po.modifiers.new('Thin closed puddle','SOLIDIFY');so.thickness=.022;so.offset=-1
timber_crossing_and_drain(M,path_x,waterc,pathc)

# Old Kerala tharavad remains the destination at the end of the path.
box('SM_House_Earthen_Court',(HOUSE_X,HOUSE_Y+1,.015),(19,16,.05),terrain,M['mud'],.02)
build_house(M);metal_vent_and_wear(M)
palm_pos=[(-19,9,1.05),(22,16,1.10),(-28,25,.95),(31,32,1.0),(-18,42,.9),(20,48,.95),(-36,55,1.1),(37,60,1.05),(-12,73,.9),(15,76,1.0),(-45,18,.95),(46,24,1.0)]
for i in range(28):
    x=rng.uniform(-75,75);y=rng.uniform(86,118)
    if abs(x-HOUSE_X)<8 and y<98:continue
    palm_pos.append((x,y,rng.uniform(.75,1.15)))
make_palms(M,palm_pos)
make_bananas(M,[(HOUSE_X-8,HOUSE_Y-3),(HOUSE_X+8.5,HOUSE_Y-2),(HOUSE_X-9,HOUSE_Y+4),(HOUSE_X+9,HOUSE_Y+5),(-8,38),(12,46),(-14,52),(18,58),(-22,68),(24,72)])

# Dense irregular tropical canopy: CC0 scanned tree where available + GPL sapling variants.
tree_lib=import_collection(RAW/'island_tree_02','island_tree_02',collection_name='island_tree_02_LOD1')
sap_lib=make_sapling_library(M,6)
tree_pts=[]
for i in range(470):tree_pts.append((rng.uniform(-92,92),rng.uniform(88,134),-.05))
for i in range(150):
    side=rng.choice([-1,1]);tree_pts.append((side*rng.uniform(31,70),rng.uniform(12,88),-.05))
if tree_lib:
    n=len([o for o in tree_lib.all_objects if o.type=='MESH'])
    ng=scatter_group('GN_Scatter_CC0_IslandTree_v02',tree_lib,max(1,n))
    near=[(rng.uniform(-58,58),rng.uniform(74,104),-.05) for _ in range(130)]
    scatter_points('SM_CC0_Library_Tree_Instances',near,veg,ng,SEED+755,1.,2.8,4.2)
ng=scatter_group('GN_Scatter_Sapling_TropicalBelt_v02',sap_lib,6)
scatter_points('SM_Sapling_Tropical_TreeBelt_Instances',tree_pts,veg,ng,SEED+410,1.,.72,1.32)
# Scanned fern/anthurium understory closes the ground plane near the house and bunds.
under=[]
for name in ['fern_02','anthurium_botany_01']:
    c=import_collection(MODELS/name,name)
    if c:under.append(c)
under_pts=[(rng.uniform(-34,34),rng.uniform(48,82),-.03) for _ in range(260)]
under_pts += [(path_x(y)+rng.choice([-1,1])*rng.uniform(1.15,3.0),y,-.02) for y in [rng.uniform(-8,52) for _ in range(70)]]
if under:
    lib=collection('COL_Library_ScannedUnderstory',collection('COL_AssetLibrary'))
    for c in under:lib.children.link(c) if c.name not in lib.children else None
    ng=scatter_group('GN_Scatter_ScannedUnderstory_v02',lib,len(under))
    scatter_points('SM_Scanned_Fern_Anthurium_Understory',under_pts,veg,ng,SEED+760,1.,.45,.95)
else:
    ng=scatter_group('GN_Scatter_SaplingUnderstory_v02',sap_lib,6);scatter_points('SM_Sapling_Understory',under_pts,veg,ng,SEED+760,1.,.18,.34)

# Western Ghat mesh ridges with scanned rock/forest slope shading and separated mist banks.
def ghat_height(x,y,y0,y1,peaks,seed):
    t=(y-y0)/(y1-y0);edge=math.sin(math.pi*max(0,min(1,t)))**.72
    h=0.
    for cx,cy,ht,wx,wy in peaks:h+=ht*math.exp(-((x-cx)/wx)**2-((y-cy)/wy)**2)
    wx=x+22*fbm(x*.008,y*.008,seed+2,3);wy=y+18*fbm(x*.009,y*.009,seed+5,3)
    n=fbm(wx*.014,wy*.014,seed,5);rr=1-abs(fbm(wx*.030,wy*.030,seed+9,4))
    spur=18*math.exp(-((x+70)/90)**2-((y-(y0+y1)/2)/70)**2)+14*math.exp(-((x-110)/85)**2-((y-(y0+y1)/2)/65)**2)
    return max(-.2,.48*edge*(h*(.62+.38*rr)+24*n+9*fbm(wx*.075,wy*.075,seed+4,4)+8*(rr-.5)+.65*spur))
FOOT_PEaks=[(-150,188,48,150,65),(135,205,58,170,70),(0,220,32,130,60)]
def ridge(name,y0,y1,peaks,mat,nx=220,ny=95,seed=0):
    verts=[];faces=[]
    for j in range(ny+1):
        y=y0+(y1-y0)*j/ny;t=j/ny;edge=math.sin(math.pi*t)**.72
        for i in range(nx+1):
            x=-680+1360*i/nx;z=ghat_height(x,y,y0,y1,peaks,seed)
            verts.append((x,y,z))
    for j in range(ny):
        for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    o=mesh_obj(name,verts,faces,mount,mat,True)
    tx=bpy.data.textures.new(name+'_Crag_Clouds','CLOUDS');tx.noise_scale=26 if seed<20 else 40;tx.noise_depth=4
    md=o.modifiers.new('Editable rocky ridge displacement','DISPLACE');md.texture=tx;md.strength=4.0 if seed<20 else (8.0 if seed<30 else 12.0);md.mid_level=.46;md.direction='NORMAL'
    return o
ridge('SM_Forested_Foothills',125,265,FOOT_PEaks,M['rock'],210,85,11)
ridge('SM_Middle_Ghat_Ridge',245,455,[(-205,340,132,170,95),(170,365,150,190,100),(25,395,104,135,85)],M['rock'],230,100,22)
ridge('SM_Far_Ghat_Massifs',430,780,[(-260,585,185,230,150),(230,610,205,250,160),(40,650,172,170,130)],M['far_rock'],230,105,33)
foot_pts=[]
for i in range(2400):
    x=rng.uniform(-205,205);y=rng.uniform(128,202);z=ghat_height(x,y,125,265,FOOT_PEaks,11)-.35
    if 1.2<z<46:foot_pts.append((x,y,z))
ngf=scatter_group('GN_Scatter_Foothill_Forest_v02',sap_lib,6)
scatter_points('SM_Foothill_Forest_Instances',foot_pts,veg,ngf,SEED+780,1.,.55,1.05)
mist_banks(atmo)
setup_hdri_world(scene)
sun_data=bpy.data.lights.new('LGT_Key_SoftMonsoonSun','SUN');sun_data.energy=1.05;sun_data.angle=math.radians(8.0);sun_data.color=(1.0,.93,.82)
sun=bpy.data.objects.new('LGT_Key_SoftMonsoonSun',sun_data);lights.objects.link(sun);sun.location=(80,90,120);sun.rotation_euler=Vector((-.42,-.55,-.72)).to_track_quat('-Z','Y').to_euler()
fill_data=bpy.data.lights.new('LGT_Fill_SkyBounce','AREA');fill_data.energy=60;fill_data.shape='DISK';fill_data.size=38;fill_data.color=(.74,.83,1.0)
fill=bpy.data.objects.new('LGT_Fill_SkyBounce',fill_data);lights.objects.link(fill);fill.location=(-18,28,24);aim(fill,(3,60,2))

cd=bpy.data.cameras.new('CAM_Hero_42mm');cd.lens=42;cd.clip_end=2200;cd.dof.use_dof=False
cam=bpy.data.objects.new('CAM_Hero_LeadingBund',cd);cams.objects.link(cam);cam.location=(-1.4,-7.5,1.90);aim(cam,(3.0,62.0,3.4));scene.camera=cam
cd2=bpy.data.cameras.new('CAM_House_Detail');cd2.lens=58;cd2.clip_end=1000
cam2=bpy.data.objects.new('CAM_House_Detail',cd2);cams.objects.link(cam2);cam2.location=(HOUSE_X-12,HOUSE_Y-19,3.0);aim(cam2,(HOUSE_X,HOUSE_Y-1,2.8))
cd3=bpy.data.cameras.new('CAM_Foreground_Detail');cd3.lens=50;cd3.clip_end=500
cam3=bpy.data.objects.new('CAM_Foreground_Detail',cd3);cams.objects.link(cam3);cam3.location=(-.5,-5,1.05);aim(cam3,(2,14,.42))
hr=box('SM_Scale_Reference_1p70m',(HOUSE_X-2,HOUSE_Y-6,.85),(.35,.25,1.70),helpers,M['stone']);hr.hide_render=True;hr.hide_set(True)

def find_lc(lc,name):
    if lc.collection.name==name:return lc
    for ch in lc.children:
        r=find_lc(ch,name)
        if r:return r
lib_lc=find_lc(bpy.context.view_layer.layer_collection,'COL_AssetLibrary')
if lib_lc:lib_lc.exclude=True
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.035;scene.cycles.adaptive_min_samples=12;scene.cycles.use_denoising=True;scene.cycles.denoiser='OPENIMAGEDENOISE'
scene.cycles.max_bounces=6;scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=3;scene.cycles.transmission_bounces=4;scene.cycles.volume_bounces=1;scene.cycles.transparent_max_bounces=12;scene.cycles.caustics_reflective=False;scene.cycles.caustics_refractive=False;scene.cycles.blur_glossy=1.0
scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.use_persistent_data=True
scene.view_layers[0].use_pass_mist=True;scene.view_layers[0].use_pass_z=True
scene.use_nodes=True;nt=scene.node_tree;nt.nodes.clear();rl=nt.nodes.new('CompositorNodeRLayers');gl=nt.nodes.new('CompositorNodeGlare');gl.glare_type='FOG_GLOW';gl.quality='MEDIUM';gl.threshold=1.8;gl.mix=-.94;gl.size=7;comp=nt.nodes.new('CompositorNodeComposite');nt.links.new(rl.outputs['Image'],gl.inputs['Image']);nt.links.new(gl.outputs['Image'],comp.inputs['Image'])
OUTPUT.mkdir(exist_ok=True);REVIEW.mkdir(exist_ok=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(BLEND2),compress=True)
unique_tris=sum(sum(len(p.vertices)-2 for p in m.polygons) for m in bpy.data.meshes)
manifest={'revision':REV,'seed':SEED,'build_seconds':round(time.time()-T0,2),'objects':len(bpy.data.objects),'meshes':len(bpy.data.meshes),'materials':len(bpy.data.materials),'unique_mesh_triangles':unique_tris,'rice_instance_points':len(rice_points),'bund_grass_points':len(path_pts),'tree_points':len(tree_pts)+len(foot_pts),'cc0_tree_library':bool(tree_lib),'sapling_variants':len(sap_lib.objects),'understory_points':len(under_pts),'palm_instances':len(palm_pos),'paddy_plots':plot_count,'blend':str(BLEND2),'resolution':[RES_X,RES_Y]}
(REVIEW/'build_manifest_v2.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2));sys.stdout.flush();os._exit(0)
