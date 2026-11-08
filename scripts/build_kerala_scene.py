#!/usr/bin/env python3
"""Reproducible build for Monsoon Light — Kerala. Run with scripts/blender-py."""
import json, math, random, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from kerala_config import *
from kerala_helpers import *
from kerala_materials import build_materials
from kerala_vegetation import *
from kerala_house import build_house

T0=time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.name=SCENE_NAME
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
scene.render.resolution_x=RES_X;scene.render.resolution_y=RES_Y;scene.render.resolution_percentage=100
scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=1
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except Exception:pass
scene.view_settings.exposure=0.0
scene['revision']=REVISION;scene['seed']=SEED;scene['units']='1 Blender unit = 1 metre'
scene['reference_provenance']='User-supplied image-1.jpeg (Shutterstock watermarked) and image-2.jpeg; analysis only, never used as backplates.'
scene['sky_disclosure']='Procedural Nishita sky + procedural cloud shader; mountains and landscape are true 3D mesh geometry.'
M=build_materials()
terrain=collection('COL_Terrain');paddy=collection('COL_Paddies');waterc=collection('COL_Water');pathc=collection('COL_Path_and_Bunds');veg=collection('COL_FieldVegetation');mount=collection('COL_Mountains');atmo=collection('COL_Atmosphere');lights=collection('COL_Lights');cams=collection('COL_Cameras');helpers=collection('COL_Helpers')

# Ground and shallow paddy plots with closed water volumes and separate mud bottoms.
box('SM_Regional_Ground_Base',(0,55,-.24),(360,210,.22),terrain,M['paddy_mud'])
rice_lib=make_rice_library(M);grass_lib=make_grass_library(M)
rice_ng=scatter_group('GN_Scatter_Paddy_RowClumps_v01',rice_lib,7)
grass_ng=scatter_group('GN_Scatter_Bund_GrassTufts_v01',grass_lib,5)
rice_points=[];plot_count=0

def plot_bounds(y,side):
    px=path_x(y)
    if side=='L0':return -FIELD_HALF_WIDTH,-28.0
    if side=='L1':return -26.8,px-1.18
    if side=='R1':return px+1.18,27.0
    return 28.2,FIELD_HALF_WIDTH

for bi,(y0,y1) in enumerate(PADDY_BANDS):
    for side in ['L0','L1','R1','R0']:
        plot_count+=1;nx=10;ny=14;verts=[];faces=[];top=.006+bi*.0015
        for j in range(ny+1):
            y=y0+(y1-y0)*j/ny;l,r=plot_bounds(y,side)
            for i in range(nx+1):verts.append((l+(r-l)*i/nx,y,top))
        for j in range(ny):
            for i in range(nx):
                a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
        w=mesh_obj(f'SM_Paddy_Water_Plot_{bi}_{side}',verts,faces,waterc,M['water'],True)
        sol=w.modifiers.new('Closed shallow water boundary 9 cm','SOLIDIFY');sol.thickness=.09;sol.offset=-1;sol.use_rim=True
        w['IOR']=1.333;w['depth_m']=.09
        bv=[(x,y,z-.115) for x,y,z in verts]
        mesh_obj(f'SM_Paddy_Mud_Bottom_{bi}_{side}',bv,faces,paddy,M['paddy_mud'],True)
        # transplant rows run down the plot, with seeded jitter and wider far spacing
        l0,r0=plot_bounds(y0,side);l1,r1=plot_bounds(y1,side);avg=((r0-l0)+(r1-l1))/2
        sx=.38 if y1<44 else .45;sy=.32 if y1<44 else .38;cols=max(2,int(avg/sx));rng=random.Random(SEED+bi*20+ord(side[0]))
        y=y0+.35
        while y<y1-.30:
            l,r=plot_bounds(y,side)
            for k in range(cols):
                u=(k+.5)/cols;x=l+(r-l)*u+rng.uniform(-.024,.024)
                rice_points.append((x+rng.uniform(-.018,.018),y+rng.uniform(-.025,.025),-.075))
            y+=sy
rice=scatter_points('SM_Paddy_Rice_RowInstances',rice_points,veg,rice_ng,SEED+700,1.,.78,1.20)
rice['planting']='Curved row-following clumps; rooted below shallow water; non-realized GN instances.'

def bund_strip(name,y0,y1,x0,x1,width,steps=100):
    verts=[];faces=[];pts=[]
    for j in range(steps+1):
        y=y0+(y1-y0)*j/steps
        cx=path_x(y) if x0 is None else (x0+x1)/2
        for i in range(9):
            u=-1+2*i/8;x=cx+u*width/2;z=.055+.135*(1-u*u)+.018*fbm(x*2,y*2,3)
            verts.append((x,y,z))
        if j%2==0:
            for k in range(3):pts.append((cx+random.Random(SEED+j*7+k).uniform(-width*.42,width*.42),y,.16))
    for j in range(steps):
        for i in range(8):a=j*9+i;faces.append((a,a+1,a+10,a+9))
    mesh_obj(name,verts,faces,pathc,M['mud'],True)
    return pts

# Main curved earthen bund/path. Wider foreground, wet edges, grassy spine.
path_pts=[];verts=[];faces=[];ny=360;nx=16;y0,y1=-22,55.8
rng=random.Random(SEED+710)
for j in range(ny+1):
    y=y0+(y1-y0)*j/ny;cx=path_x(y);width=1.78+.10*math.sin(y*.12)
    for i in range(nx+1):
        u=-1+2*i/nx;x=cx+u*width/2;z=.065+.155*(1-u*u)+.016*fbm(x*3,y*3,8);verts.append((x,y,z))
for j in range(ny):
    for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
mesh_obj('SM_Curved_Earthen_Footpath',verts,faces,pathc,M['mud'],True)
y=y0
while y<y1:
    cx=path_x(y)
    for k in range(7):path_pts.append((cx+rng.uniform(-.26,.26),y+rng.uniform(-.06,.06),.215))
    for s in [-1,1]:path_pts.append((cx+s*rng.uniform(.72,.90),y+rng.uniform(-.08,.08),.10))
    y+=.11
# horizontal maintenance bunds between paddy bands
for by in [3.7,23.75,43.75,55.0,67.7]:
    verts=[];faces=[]
    for j in range(221):
        x=-55+j*.5
        for i in range(7):
            u=-1+2*i/6;verts.append((x,by+u*.48,.05+.13*(1-u*u)+.015*fbm(x*2,by*2,5)))
    for j in range(220):
        for i in range(6):a=j*7+i;faces.append((a,a+7,a+8,a+1))
    mesh_obj(f'SM_Transverse_Bund_{by}',verts,faces,pathc,M['mud'],True)
    for x in [i*.22-55 for i in range(500)]:
        if abs(x-path_x(by))>1.0:path_pts.append((x+rng.uniform(-.06,.06),by+rng.uniform(-.36,.36),.16))
scatter_points('SM_Bund_Grass_Instances',path_pts,veg,grass_ng,SEED+720,1.,.7,1.35)
# a few worn laterite fragments near the approach, not a paved highway
for i in range(22):
    y=rng.uniform(43,55);x=path_x(y)+rng.choice([-1,1])*rng.uniform(.55,.85)
    box(f'SM_Worn_Laterite_EdgeStone_{i}',(x,y,.16),(rng.uniform(.18,.34),rng.uniform(.14,.26),.07),pathc,M['laterite'],.025,rot=(0,0,rng.uniform(0,3)))
# shallow rain puddles on the worn bund shoulders
for i in range(16):
    y=rng.uniform(-14,50);cx=path_x(y);s=rng.choice([-1,1]);px=cx+s*rng.uniform(.52,.72);rx=rng.uniform(.10,.24);ry=rng.uniform(.18,.42);pz=.128
    vv=[(px+rx*math.cos(2*math.pi*k/18),y+ry*math.sin(2*math.pi*k/18),pz) for k in range(18)]
    po=mesh_obj(f'SM_Bund_Rain_Puddle_{i}',vv,[tuple(range(18))],waterc,M['water'])
    so=po.modifiers.new('Thin closed puddle','SOLIDIFY');so.thickness=.025;so.offset=-1
# understory shrubs close the gaps below the tree belt
shrub_pts=[(rng.uniform(-85,85),rng.uniform(84,96),-.05) for _ in range(220)]
shrub_ng=scatter_group('GN_Scatter_Tropical_Understory_v01',bpy.data.collections.get('COL_Library_BroadleafTrees') or rice_lib,6)
# library is created later; store points and add after forest below
# house earthen court
box('SM_House_Earthen_Court',(HOUSE_X,HOUSE_Y+1,.015),(19,16,.05),terrain,M['mud'],.02)

build_house(M)
# Coconut palms frame the view and punctuate the tree line; none blocks the door.
palm_pos=[(-19,9,1.05),(22,16,1.10),(-28,25,.95),(31,32,1.0),(-18,42,.9),(20,48,.95),(-36,55,1.1),(37,60,1.05),(-12,73,.9),(15,76,1.0),(-45,18,.95),(46,24,1.0)]
for i in range(30):
    x=rng.uniform(-75,75);y=rng.uniform(86,118)
    if abs(x-HOUSE_X)<8 and y<98:continue
    palm_pos.append((x,y,rng.uniform(.75,1.15)))
make_palms(M,palm_pos)
banana_pos=[(HOUSE_X-8,HOUSE_Y-3),(HOUSE_X+8.5,HOUSE_Y-2),(HOUSE_X-9,HOUSE_Y+4),(HOUSE_X+9,HOUSE_Y+5),(-8,38),(12,46),(-14,52),(18,58)]
make_bananas(M,banana_pos)
# Dense dimensional broadleaf belt behind the house and along field edges.
tree_pts=[]
for i in range(430):
    x=rng.uniform(-90,90);y=rng.uniform(89,132);tree_pts.append((x,y,-.05))
for i in range(130):
    side=rng.choice([-1,1]);x=side*rng.uniform(32,68);y=rng.uniform(12,88);tree_pts.append((x,y,-.05))
make_forest(M,tree_pts)
shrub_ng=scatter_group('GN_Scatter_Tropical_Understory_v01',bpy.data.collections['COL_Library_BroadleafTrees'],6)
scatter_points('SM_Tropical_Understory_Instances',shrub_pts,veg,shrub_ng,SEED+740,1.,.22,.42)

# Real mesh Western-Ghat-inspired ridges; rounded massifs, shoulders and ravines, not spikes.
def ridge(name,y0,y1,peaks,mat,nx=220,ny=95,seed=0):
    verts=[];faces=[]
    for j in range(ny+1):
        y=y0+(y1-y0)*j/ny;t=j/ny;edge=math.sin(math.pi*t)**.72
        for i in range(nx+1):
            x=-680+1360*i/nx;h=0.
            for cx,cy,ht,wx,wy in peaks:
                h+=ht*math.exp(-((x-cx)/wx)**2-((y-cy)/wy)**2)
            wx=x+22*fbm(x*.008,y*.008,seed+2,3);wy=y+18*fbm(x*.009,y*.009,seed+5,3)
            n=fbm(wx*.014,wy*.014,seed,5);rr=1-abs(fbm(wx*.030,wy*.030,seed+9,4))
            spur=18*math.exp(-((x+70)/90)**2-((y-(y0+y1)/2)/70)**2)+14*math.exp(-((x-110)/85)**2-((y-(y0+y1)/2)/65)**2)
            z=.48*edge*(h*(.68+.32*rr)+22*n+6*fbm(wx*.07,wy*.07,seed+4,3)+.6*spur);z=max(-.2,z)
            verts.append((x,y,z))
    for j in range(ny):
        for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    return mesh_obj(name,verts,faces,mount,mat,True)
ridge('SM_Forested_Foothills',125,265,[(-150,188,48,150,65),(135,205,58,170,70),(0,220,32,130,60)],M['rock'],180,70,11)
ridge('SM_Middle_Ghat_Ridge',245,455,[(-205,340,132,170,95),(170,365,150,190,100),(25,395,104,135,85)],M['rock'],230,100,22)
ridge('SM_Far_Ghat_Massifs',430,780,[(-260,585,185,230,150),(230,610,205,250,160),(40,650,172,170,130)],M['far_rock'],230,105,33)
# forest texture on foothill silhouettes via additional instances near visible front slopes
foot_pts=[]
for i in range(380):
    x=rng.uniform(-220,220);y=rng.uniform(132,190);z=8+12*max(0,fbm(x*.01,y*.01,11,3));foot_pts.append((x,y,z))
# reuse tree belt group with smaller scale
lib=bpy.data.collections['COL_Library_BroadleafTrees'];ng=scatter_group('GN_Scatter_Foothill_Forest_v01',lib,6)
scatter_points('SM_Foothill_Forest_Instances',foot_pts,veg,ng,SEED+730,.8,.55,.95)

# Bounded humid mist only in the distant layer; camera and paddy water stay outside it.
vm=bpy.data.materials.new('MAT_Bounded_Ghat_Mist');vm.use_nodes=True;nt=vm.node_tree;nt.nodes.clear()
out=nt.nodes.new('ShaderNodeOutputMaterial');sc=nt.nodes.new('ShaderNodeVolumeScatter');sc.inputs['Color'].default_value=(.66,.76,.79,1);sc.inputs['Anisotropy'].default_value=.30
tc=nt.nodes.new('ShaderNodeTexCoord');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Generated'],sep.inputs['Vector'])
mr=nt.nodes.new('ShaderNodeMapRange');mr.inputs['From Min'].default_value=0;mr.inputs['From Max'].default_value=1;mr.inputs['To Min'].default_value=.00065;mr.inputs['To Max'].default_value=0;nt.links.new(sep.outputs['Z'],mr.inputs['Value']);nt.links.new(mr.outputs['Result'],sc.inputs['Density']);nt.links.new(sc.outputs['Volume'],out.inputs['Volume'])
mist=box('SM_Distant_Mist_Volume',(0,505,125),(1600,790,250),atmo,vm);mist.display_type='WIRE';mist['bounds']='x ±800 m; y 110–900 m; z 0–250 m; density falls to zero at top'

# World: physical sky illumination plus disclosed procedural cloud shader.
world=bpy.data.worlds.new('WORLD_Kerala_Monsoon_Sky');scene.world=world;world.use_nodes=True;nt=world.node_tree;nt.nodes.clear()
out=nt.nodes.new('ShaderNodeOutputWorld');out.location=(1100,80)
# Physical Nishita lighting for diffuse/transmission; art-directed gradient+clouds for camera/glossy rays.
sky=nt.nodes.new('ShaderNodeTexSky');sky.location=(-600,420);sky.sky_type='NISHITA';sky.sun_disc=False;sky.sun_elevation=math.radians(34);sky.sun_rotation=math.radians(132);sky.altitude=.15;sky.air_density=1.05;sky.dust_density=1.1;sky.ozone_density=1.1
bg_light=nt.nodes.new('ShaderNodeBackground');bg_light.location=(360,420);bg_light.inputs['Strength'].default_value=.45;nt.links.new(sky.outputs['Color'],bg_light.inputs['Color'])
Tex=nt.nodes.new('ShaderNodeTexCoord');Tex.location=(-1100,-100)
sep=nt.nodes.new('ShaderNodeSeparateXYZ');sep.location=(-900,-250);nt.links.new(Tex.outputs['Normal'],sep.inputs['Vector'])
gr=nt.nodes.new('ShaderNodeMapRange');gr.location=(-700,-250);gr.inputs['From Min'].default_value=0;gr.inputs['From Max'].default_value=.36;nt.links.new(sep.outputs['Z'],gr.inputs['Value'])
grad=nt.nodes.new('ShaderNodeValToRGB');grad.location=(-480,-250);grad.color_ramp.elements[0].position=0;grad.color_ramp.elements[0].color=(.55,.70,.80,1);grad.color_ramp.elements[1].position=1;grad.color_ramp.elements[1].color=(.12,.28,.50,1);nt.links.new(gr.outputs['Result'],grad.inputs['Fac'])
mapn=nt.nodes.new('ShaderNodeMapping');mapn.location=(-900,-20);mapn.inputs['Scale'].default_value=(4.0,4.0,9.0);nt.links.new(Tex.outputs['Normal'],mapn.inputs['Vector'])
cl=nt.nodes.new('ShaderNodeTexNoise');cl.location=(-700,-20);cl.inputs['Scale'].default_value=2.6;cl.inputs['Detail'].default_value=7;cl.inputs['Roughness'].default_value=.60;nt.links.new(mapn.outputs['Vector'],cl.inputs['Vector'])
cr=nt.nodes.new('ShaderNodeValToRGB');cr.location=(-480,-20);cr.color_ramp.elements[0].position=.52;cr.color_ramp.elements[0].color=(0,0,0,1);cr.color_ramp.elements[1].position=.63;cr.color_ramp.elements[1].color=(1,1,1,1);nt.links.new(cl.outputs['Fac'],cr.inputs['Fac'])
hz=nt.nodes.new('ShaderNodeMapRange');hz.location=(-700,-450);hz.inputs['From Min'].default_value=.005;hz.inputs['From Max'].default_value=.10;nt.links.new(sep.outputs['Z'],hz.inputs['Value'])
mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.location=(-220,-20);nt.links.new(cr.outputs['Color'],mul.inputs[0]);nt.links.new(hz.outputs['Result'],mul.inputs[1])
cmix=nt.nodes.new('ShaderNodeMixRGB');cmix.location=(0,-100);cmix.inputs[2].default_value=(1.25,1.25,1.23,1);nt.links.new(mul.outputs[0],cmix.inputs[0]);nt.links.new(grad.outputs['Color'],cmix.inputs[1])
bg_cam=nt.nodes.new('ShaderNodeBackground');bg_cam.location=(360,-100);bg_cam.inputs['Strength'].default_value=.85;nt.links.new(cmix.outputs['Color'],bg_cam.inputs['Color'])
lp=nt.nodes.new('ShaderNodeLightPath');lp.location=(360,180)
mx=nt.nodes.new('ShaderNodeMath');mx.operation='MAXIMUM';mx.location=(560,180);nt.links.new(lp.outputs['Is Camera Ray'],mx.inputs[0]);nt.links.new(lp.outputs['Is Glossy Ray'],mx.inputs[1])
ms=nt.nodes.new('ShaderNodeMixShader');ms.location=(820,80);nt.links.new(mx.outputs[0],ms.inputs[0]);nt.links.new(bg_light.outputs['Background'],ms.inputs[1]);nt.links.new(bg_cam.outputs['Background'],ms.inputs[2]);nt.links.new(ms.outputs['Shader'],out.inputs['Surface'])
world['disclosure']='World uses Nishita for diffuse lighting. Visible sky is a procedural gradient/cloud shader on a distant dome (camera/glossy only), not volumetric cloud meshes.'
# Distant sky dome guarantees stable art-directed camera/glossy sky across backends.
skyc=collection('COL_SkyDome')
sm=bpy.data.materials.new('MAT_Procedural_SkyDome_CameraGlossy');sm.use_nodes=True;nt=sm.node_tree;nt.nodes.clear()
out=nt.nodes.new('ShaderNodeOutputMaterial');em=nt.nodes.new('ShaderNodeEmission');tr=nt.nodes.new('ShaderNodeBsdfTransparent');ms=nt.nodes.new('ShaderNodeMixShader');lp=nt.nodes.new('ShaderNodeLightPath');mx=nt.nodes.new('ShaderNodeMath');mx.operation='MAXIMUM';nt.links.new(lp.outputs['Is Camera Ray'],mx.inputs[0]);nt.links.new(lp.outputs['Is Glossy Ray'],mx.inputs[1]);nt.links.new(mx.outputs[0],ms.inputs[0]);nt.links.new(tr.outputs['BSDF'],ms.inputs[1]);nt.links.new(em.outputs['Emission'],ms.inputs[2]);nt.links.new(ms.outputs['Shader'],out.inputs['Surface'])
geo=nt.nodes.new('ShaderNodeNewGeometry');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(geo.outputs['Position'],sep.inputs['Vector']);gr=nt.nodes.new('ShaderNodeMapRange');gr.inputs['From Min'].default_value=0;gr.inputs['From Max'].default_value=1000;nt.links.new(sep.outputs['Z'],gr.inputs['Value']);grad=nt.nodes.new('ShaderNodeValToRGB');grad.color_ramp.elements[0].color=(.60,.75,.85,1);grad.color_ramp.elements[1].color=(.15,.33,.58,1);nt.links.new(gr.outputs['Result'],grad.inputs['Fac'])
tc=nt.nodes.new('ShaderNodeTexCoord');mp=nt.nodes.new('ShaderNodeMapping');mp.inputs['Scale'].default_value=(.004,.004,.009);nt.links.new(tc.outputs['Object'],mp.inputs['Vector']);ns=nt.nodes.new('ShaderNodeTexNoise');ns.inputs['Scale'].default_value=1.0;ns.inputs['Detail'].default_value=7;ns.inputs['Roughness'].default_value=.60;nt.links.new(mp.outputs['Vector'],ns.inputs['Vector']);cr=nt.nodes.new('ShaderNodeValToRGB');cr.color_ramp.elements[0].position=.54;cr.color_ramp.elements[1].position=.65;nt.links.new(ns.outputs['Fac'],cr.inputs['Fac']);fade=nt.nodes.new('ShaderNodeMapRange');fade.inputs['From Min'].default_value=25;fade.inputs['From Max'].default_value=140;nt.links.new(sep.outputs['Z'],fade.inputs['Value']);mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';nt.links.new(cr.outputs['Color'],mul.inputs[0]);nt.links.new(fade.outputs['Result'],mul.inputs[1]);cm=nt.nodes.new('ShaderNodeMixRGB');cm.inputs[2].default_value=(1.35,1.35,1.32,1);nt.links.new(mul.outputs[0],cm.inputs[0]);nt.links.new(grad.outputs['Color'],cm.inputs[1]);nt.links.new(cm.outputs['Color'],em.inputs['Color']);em.inputs['Strength'].default_value=1.0
bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=1800,location=(0,150,0))
dome=bpy.context.object;dome.name='SM_SkyDome_ProceduralShader';dome.data.materials.append(sm)
for cc in list(dome.users_collection):cc.objects.unlink(dome)
skyc.objects.link(dome)
dome.visible_diffuse=False;dome.visible_transmission=False;dome.visible_shadow=False;dome.display_type='WIRE'

# Fixed motivated sun; soft sky fill. No animated astronomical time lapse.
sun_data=bpy.data.lights.new('LGT_Key_MorningSun','SUN');sun_data.energy=4.5;sun_data.angle=math.radians(1.6);sun_data.color=(1.0,.91,.76)
sun=bpy.data.objects.new('LGT_Key_MorningSun',sun_data);lights.objects.link(sun);sun.location=(80,90,120);sun.rotation_euler=Vector((-.48,-.52,-.70)).to_track_quat('-Z','Y').to_euler()
fill_data=bpy.data.lights.new('LGT_Fill_SkyBounce','AREA');fill_data.energy=150;fill_data.shape='DISK';fill_data.size=35;fill_data.color=(.72,.82,1.0)
fill=bpy.data.objects.new('LGT_Fill_SkyBounce',fill_data);lights.objects.link(fill);fill.location=(-18,28,24);aim(fill,(3,60,2))

# Cameras
cd=bpy.data.cameras.new('CAM_Hero_39mm');cd.lens=LENS_MM;cd.clip_end=2200;cd.dof.use_dof=False
cam=bpy.data.objects.new('CAM_Hero_LeadingBund',cd);cams.objects.link(cam);cam.location=CAMERA_LOC;aim(cam,CAMERA_TARGET);scene.camera=cam
cd2=bpy.data.cameras.new('CAM_House_Detail');cd2.lens=58;cd2.clip_end=1000
cam2=bpy.data.objects.new('CAM_House_Detail',cd2);cams.objects.link(cam2);cam2.location=(HOUSE_X-12,HOUSE_Y-19,3.2);aim(cam2,(HOUSE_X,HOUSE_Y-1,2.8))
cd3=bpy.data.cameras.new('CAM_Foreground_Detail');cd3.lens=50;cd3.clip_end=500
cam3=bpy.data.objects.new('CAM_Foreground_Detail',cd3);cams.objects.link(cam3);cam3.location=(-.5,-7,1.15);aim(cam3,(2,12,.45))
# tiny distant swifts: real body/wing meshes, varied phase, subordinate scale
birds=collection('COL_DistantBirds')
for i in range(6):
    x=-22+i*7+rng.uniform(-2,2);y=135+rng.uniform(-8,8);z=26+rng.uniform(-3,4);ph=rng.uniform(-.4,.4)
    vv=[(0,0,0),(-.45,.05,.12+ph),(-.9,.12,-.05+ph),(0,.18,-.04),(.45,.05,.12-ph),(.9,.12,-.05-ph)]
    ff=[(0,1,3),(1,2,3),(0,3,4),(3,5,4)]
    bo=mesh_obj(f'SM_Distant_Swift_{i}',vv,ff,birds,M['darkwood']);bo.location=(x,y,z);bo.scale=(.55,.55,.55);bo.rotation_euler.z=rng.uniform(-.3,.3)
# hidden metric human scale reference
hr=box('SM_Scale_Reference_1p70m',(HOUSE_X-2,HOUSE_Y-6,.85),(.35,.25,1.70),helpers,M['stone']);hr.hide_render=True;hr.hide_set(True)

# Exclude asset sources from view layer; GN/collection instances still provide render geometry.
def find_lc(lc,name):
    if lc.collection.name==name:return lc
    for ch in lc.children:
        r=find_lc(ch,name)
        if r:return r
lib_lc=find_lc(bpy.context.view_layer.layer_collection,'COL_AssetLibrary')
if lib_lc:lib_lc.exclude=True

# Render defaults and reversible compositor
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.04;scene.cycles.adaptive_min_samples=8;scene.cycles.use_denoising=True;scene.cycles.denoiser='OPENIMAGEDENOISE'
scene.cycles.max_bounces=6;scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=3;scene.cycles.transmission_bounces=4;scene.cycles.volume_bounces=1;scene.cycles.transparent_max_bounces=8;scene.cycles.caustics_reflective=False;scene.cycles.caustics_refractive=False;scene.cycles.blur_glossy=1.0
scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.use_persistent_data=True
scene.view_layers[0].use_pass_mist=True;scene.view_layers[0].use_pass_z=True
scene.use_nodes=True;nt=scene.node_tree;nt.nodes.clear();rl=nt.nodes.new('CompositorNodeRLayers');rl.location=(-300,80);gl=nt.nodes.new('CompositorNodeGlare');gl.location=(0,80);gl.glare_type='FOG_GLOW';gl.quality='MEDIUM';gl.threshold=1.6;gl.mix=-.92;gl.size=7;comp=nt.nodes.new('CompositorNodeComposite');comp.location=(260,80);nt.links.new(rl.outputs['Image'],gl.inputs['Image']);nt.links.new(gl.outputs['Image'],comp.inputs['Image'])

# Save exact editable scene
OUTPUT.mkdir(exist_ok=True);REVIEW.mkdir(exist_ok=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),compress=True)
unique_tris=sum(sum(len(p.vertices)-2 for p in m.polygons) for m in bpy.data.meshes)
manifest={'revision':REVISION,'seed':SEED,'build_seconds':round(time.time()-T0,2),'objects':len(bpy.data.objects),'meshes':len(bpy.data.meshes),'materials':len(bpy.data.materials),'unique_mesh_triangles':unique_tris,'rice_instance_points':len(rice_points),'bund_grass_points':len(path_pts),'tree_points':len(tree_pts)+len(foot_pts),'palm_instances':len(palm_pos),'paddy_plots':plot_count,'blend':str(BLEND),'resolution':[RES_X,RES_Y]}
(REVIEW/'build_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
