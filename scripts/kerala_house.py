import math, random
import bpy
from mathutils import Vector
from kerala_helpers import collection, box, mesh_obj, tube
from kerala_config import HOUSE_X, HOUSE_Y, SEED

def roof_plane(name,A,B,C,D,c,M,rng,tiles=True):
    A,B,C,D=map(Vector,(A,B,C,D)); U=(B-A).normalized(); V0=((C+D)/2-(A+B)/2); L=V0.length; V=V0.normalized(); N=U.cross(V).normalized()
    if N.z<0:N=-N
    base_half=(B-A).length/2; top_half=(D-C).length/2
    # solid under-roof prevents pinholes between overlapping tiles
    mesh_obj(name+'_UnderRoof',[tuple(A),tuple(B),tuple(D),tuple(C)],[(0,1,2,3)],c,M['darkwood'])
    if not tiles:return
    verts=[];faces=[];idx=[]; step=.315; tw=.235; rows=int(L/step)+1
    for r in range(rows):
        v=min(L-.05,(r+.35)*step);t=v/L;half=base_half*(1-t)+top_half*t;center=(A+B)/2+V*v
        cols=int(2*half/tw)+1
        for col in range(cols):
            u=-half+tw*(col+.5)
            if abs(u)>half-.03:continue
            base=center+U*u;st=len(verts);tilt=rng.uniform(-.008,.008)
            for le in [0,.39]:
                for ax in [-.115,-.065,0,.065,.115]:
                    h=.045*(1-(ax/.115)**2)+.018*math.sin(le*4)+tilt
                    p=base+U*ax+V*le+N*h;verts.append(tuple(p))
            for q in range(4):
                faces.append((st+q,st+q+1,st+q+6,st+q+5));idx.append(1 if rng.random()<(0.16 if r<4 else .07) else 0)
    mesh_obj(name+'_IndividualOverlappingTiles',verts,faces,c,materials=[M['tile'],M['tile_moss']],indices=idx,smooth=True)

def lathe(name,profile,loc,c,mat,segments=24):
    v=[];f=[]
    for r,z in profile:
        for i in range(segments):
            a=2*math.pi*i/segments;v.append((r*math.cos(a),r*math.sin(a),z))
    for j in range(len(profile)-1):
        for i in range(segments):
            a=j*segments+i;b=j*segments+(i+1)%segments;f.append((a,b,b+segments,a+segments))
    o=mesh_obj(name,v,f,c,mat,True);o.location=loc;return o

def build_house(M):
    rng=random.Random(SEED+600)
    rootc=collection('COL_Kerala_House')
    walls=collection('COL_House_Walls',rootc);roof=collection('COL_House_Roof',rootc);ver=collection('COL_House_Veranda',rootc);props=collection('COL_House_Props',rootc)
    root=bpy.data.objects.new('SM_Tharavad_House_Root',None);rootc.objects.link(root);root.location=(HOUSE_X,HOUSE_Y,0);root['style']='Kerala tharavad-inspired; laterite, lime, teak, fired clay'
    # laterite plinth and lime mortar bed
    box('SM_Laterite_Plinth',(0,.1,.30),(13.0,9.4,.60),walls,M['laterite'],.035)
    box('SM_Lime_Plinth_Cap',(0,.1,.61),(13.15,9.5,.09),walls,M['stone'],.02)
    for course in range(2):
        z=.15+course*.28
        for i in range(21):
            x=-6.15+i*.61+(.3 if course%2 else 0)
            if abs(x)<1.35 and course<2:continue
            box(f'SM_Laterite_Block_F_{course}_{i}',(x,-4.63,z),(.58,.16,.25),walls,M['laterite'],.018)
    # front wall with actual door/window openings
    zf=.6;zt=3.30;fy=-3.30
    piers=[(-5.4,-3.82),(-2.58,-.68),(.68,2.58),(3.82,5.4)]
    for i,(a,b) in enumerate(piers):box(f'SM_Lime_FrontPier_{i}',((a+b)/2,fy,(zf+zt)/2),(b-a,.28,zt-zf),walls,M['plaster'],.018)
    for cx in [-3.2,3.2]:
        box(f'SM_Lime_WindowSill_{cx}',(cx,fy,1.0),(1.24,.28,.8),walls,M['plaster'],.015)
        box(f'SM_Lime_WindowLintel_{cx}',(cx,fy,2.95),(1.24,.28,.7),walls,M['plaster'],.015)
    box('SM_Lime_DoorLintel',(0,fy,3.0),(1.36,.28,.6),walls,M['plaster'],.015)
    box('SM_Lime_BackWall',(0,3.9,(zf+zt)/2),(10.8,.28,zt-zf),walls,M['plaster'],.02)
    for sx in [-5.4,5.4]:box(f'SM_Lime_SideWall_{sx}',(sx,.3,(zf+zt)/2),(.28,7.2,zt-zf),walls,M['plaster'],.02)
    box('SM_Dark_Interior_Floor',(0,.3,.64),(10.6,7.0,.08),walls,M['darkwood'])
    box('SM_Interior_Shadow_Back',(0,2.8,1.8),(10.4,.1,2.4),walls,M['darkwood'])
    # veranda deck, turned posts, beams, brackets, balusters
    for i in range(26):
        x=-5.6+i*.44;box(f'SM_Veranda_TeakPlank_{i}',(x,-4.12,.68),(.42,1.65,.07),ver,M['wood'],.008)
    box('SM_Veranda_FrontBeam',(0,-4.67,2.98),(11.7,.18,.23),ver,M['darkwood'],.015)
    for i,x in enumerate([-5.25,-3.15,-1.05,1.05,3.15,5.25]):
        box(f'SM_Post_StoneFoot_{i}',(x,-4.67,.78),(.30,.30,.20),ver,M['stone'],.015)
        prof=[(.13,.88),(.13,1.0),(.095,1.06),(.085,1.25),(.11,1.34),(.09,1.45),(.08,2.55),(.12,2.64),(.12,2.78),(.14,2.84)]
        tube(f'SM_Turned_TeakPost_{i}',[(x,-4.67,z) for _,z in prof],[r for r,_ in prof],ver,M['wood'],10)
        box(f'SM_Post_Capital_{i}',(x,-4.67,2.87),(.34,.30,.14),ver,M['darkwood'],.015)
        for s in [-1,1]:
            tube(f'SM_CurvedBracket_{i}_{s}',[(x+s*.05,-4.67,2.48),(x+s*.28,-4.67,2.72),(x+s*.58,-4.67,2.91)],[.055,.065,.075],ver,M['darkwood'],6)
        if abs(x)>1.2:
            box(f'SM_Veranda_RailTop_{i}',(x,-4.67,1.32),(1.75,.10,.09),ver,M['wood'],.01)
            for k in range(5):box(f'SM_Baluster_{i}_{k}',(x-.68+k*.34,-4.67,1.04),(.055,.055,.52),ver,M['wood'],.006)
    # double door with raised carved panels and brass ring pulls
    for sx in [-1,1]:
        cx=sx*.335;box(f'SM_DoorLeaf_{sx}',(cx,fy-.05,1.67),(.64,.10,2.08),ver,M['darkwood'],.012)
        for pz in [1.08,1.72,2.30]:box(f'SM_Door_RaisedPanel_{sx}_{pz}',(cx,fy-.115,pz),(.46,.045,.46),ver,M['wood'],.02)
        for k in range(3):box(f'SM_Door_CarvedReed_{sx}_{k}',(cx-.16+k*.16,fy-.145,1.72),(.025,.025,1.8),ver,M['wood'],.004)
        bpy.ops.mesh.primitive_torus_add(major_radius=.055,minor_radius=.009,major_segments=16,minor_segments=6,location=(sx*.12,fy-.18,1.62),rotation=(math.pi/2,0,0))
        o=bpy.context.object;o.name=f'SM_Brass_DoorRing_{sx}';o.data.materials.append(M['brass'])
        for cc in list(o.users_collection):cc.objects.unlink(o)
        ver.objects.link(o)
    # windows: dark recess, bars, hinged open shutters
    for cx in [-3.2,3.2]:
        box(f'SM_Window_ShadowRecess_{cx}',(cx,fy+.06,2.02),(1.18,.06,1.18),ver,M['darkwood'])
        box(f'SM_Window_FrameTop_{cx}',(cx,fy-.10,2.64),(1.34,.12,.10),ver,M['wood'],.01)
        box(f'SM_Window_FrameSill_{cx}',(cx,fy-.14,1.40),(1.40,.18,.11),ver,M['wood'],.01)
        for k in range(7):box(f'SM_Window_WoodBar_{cx}_{k}',(cx-.5+k*.166,fy-.10,2.02),(.035,.045,1.16),ver,M['wood'],.005)
        for s in [-1,1]:
            o=box(f'SM_Open_Shutter_{cx}_{s}',(cx+s*.78,fy-.26,2.02),(.40,.055,1.20),ver,M['wood'],.012,rot=(0,0,s*.48))
            for k in range(5):box(f'SM_Shutter_Slat_{cx}_{s}_{k}',(cx+s*.78,fy-.30,1.55+k*.22),(.34,.03,.025),ver,M['darkwood'],.003,rot=(0,0,s*.48))
    # side window suggestion
    for sx in [-5.42,5.42]:
        box(f'SM_SideWindow_Recess_{sx}',(sx,1.1,2.05),(.06,1.1,1.1),ver,M['darkwood'])
        for k in range(6):box(f'SM_SideWindow_Bar_{sx}_{k}',(sx+(-.04 if sx<0 else .04),.65+k*.18,2.05),(.04,.035,1.05),ver,M['wood'],.004)
    # broad hip roof, real overlapping clay tiles, deep eaves
    ez=3.28;rz=5.72;ex=6.72;fy=-5.25;by=4.95;rx=3.05;ry=-.15
    roof_plane('SM_Roof_Front',(-ex,fy,ez),(ex,fy,ez),(-rx,ry,rz),(rx,ry,rz),roof,M,rng)
    roof_plane('SM_Roof_Back',(ex,by,ez),(-ex,by,ez),(rx,ry,rz),(-rx,ry,rz),roof,M,rng)
    roof_plane('SM_Roof_Left',(-ex,by,ez),(-ex,fy,ez),(-rx,ry,rz),(-rx,ry,rz),roof,M,rng)
    roof_plane('SM_Roof_Right',(ex,fy,ez),(ex,by,ez),(rx,ry,rz),(rx,ry,rz),roof,M,rng)
    tube('SM_Ridge_Terracotta_Cap',[(-rx-.18,ry,rz+.04),(rx+.18,ry,rz+.04)],[.13,.13],roof,M['tile'],10)
    for A,B in [((-ex,fy,ez),(-rx,ry,rz)),((ex,fy,ez),(rx,ry,rz)),((-ex,by,ez),(-rx,ry,rz)),((ex,by,ez),(rx,ry,rz))]:
        tube('SM_Hip_Ridge_Cap',[A,B],[.105,.105],roof,M['tile_moss'],8)
    box('SM_Front_Fascia',(0,fy,ez-.06),(13.5,.12,.18),roof,M['darkwood'],.012)
    box('SM_Back_Fascia',(0,by,ez-.06),(13.5,.12,.18),roof,M['darkwood'],.012)
    for i in range(32):
        x=-6.4+i*.413;tube(f'SM_Exposed_RafterTail_{i}',[(x,fy+.12,ez-.13),(x,fy+1.0,ez+.32)],[.045,.045],roof,M['wood'],5)
    # small ventilator dormer with timber louvers and tiled cap
    box('SM_Roof_Vent_Shadow',(0,-1.82,4.86),(2.0,.72,.66),roof,M['darkwood'],.01)
    for k in range(5):box(f'SM_Roof_Vent_Louver_{k}',(0,-2.21,4.61+k*.12),(1.86,.07,.045),roof,M['wood'],.006,rot=(.25,0,0))
    mesh_obj('SM_Vent_Gable_Tile',[(-1.22,-2.35,5.18),(1.22,-2.35,5.18),(0,-1.55,5.82),(0,-.85,5.18),(-1.22,-.85,5.18),(1.22,-.85,5.18)],[(0,1,2),(3,5,2),(3,2,4),(2,5,1)],roof,M['tile'])
    # approach steps
    for i,(y,z,h,w) in enumerate([(-5.05,.50,.20,2.8),(-5.55,.34,.20,3.0),(-6.05,.17,.18,3.2)]):
        box(f'SM_Granite_ApproachStep_{i}',(0,y,z),(w,.58,h),props,M['stone'],.025)
    # lived-in props: water jar, bench, lamp, broom, firewood
    lathe('SM_Terracotta_WaterJar',[(.0,0),(.24,.02),(.34,.18),(.38,.45),(.30,.68),(.18,.78),(.17,.86),(.21,.89)],(4.55,-4.95,.7),props,M['pot'])
    lathe('SM_Small_ClayPot',[(0,0),(.14,.01),(.20,.16),(.17,.30),(.10,.36),(.12,.39)],(5.15,-4.75,.7),props,M['pot'])
    box('SM_Veranda_Bench_Seat',(-3.9,-4.15,1.05),(1.6,.42,.09),props,M['wood'],.02)
    for x in [-4.55,-3.25]:box(f'SM_Bench_Leg_{x}',(x,-4.15,.85),(.10,.34,.38),props,M['darkwood'],.01)
    tube('SM_Lamp_Chain',[(0,-4.1,2.95),(0,-4.1,2.45)],[.009,.009],props,M['brass'],5)
    lathe('SM_Hanging_Brass_Lamp',[(.02,0),(.16,.05),(.22,.12),(.12,.18),(.04,.22)],(0,-4.1,2.23),props,M['brass'])
    lathe('SM_Lamp_Wick',[(.02,0),(.035,.04),(.015,.08)],(0,-4.1,2.43),props,M['lamp'],8)
    tube('SM_Broom_Handle',[(5.0,-4.5,.72),(5.35,-4.45,1.85)],[.018,.018],props,M['wood'],6)
    tube('SM_Broom_Brush',[(5.0,-4.5,.72),(4.88,-4.52,.30)],[.04,.13],props,M['palm_dry'],8)
    for i in range(12):
        tube(f'SM_Stacked_Firewood_{i}',[(6.05,.2+(i%4)*.22,.72+(i//4)*.16),(6.85,.24+(i%4)*.22,.74+(i//4)*.16)],[.07,.065],props,M['wood'],7)
    # weathering skirts: moss/damp at wall foot, not arbitrary all-over noise
    box('SM_Damp_Lime_Skirt_Front',(0,fy-.145,.83),(10.7,.018,.34),walls,M['tile_moss'])
    for sx in [-5.55,5.55]:box(f'SM_Damp_Lime_Skirt_Side_{sx}',(sx,.3,.83),(.018,7.1,.34),walls,M['tile_moss'])
    for o in list(rootc.all_objects):
        if o!=root:o.parent=root
    root['door_height_m']=2.08;root['wall_height_m']=2.70;root['roof_ridge_m']=5.72
    return root
