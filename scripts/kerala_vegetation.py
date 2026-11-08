import math, random
import bpy
from mathutils import Vector
from kerala_helpers import collection, mesh_obj, tube, linked_copy, scatter_group, scatter_points
from kerala_config import SEED

def blade_mesh(name, rng, c, mats, blades=14, hmin=.30, hmax=.62, width=.018, lean=.30, segs=5):
    verts=[];faces=[];indices=[];wind=[]
    for b in range(blades):
        a=b*2.399963+rng.uniform(-.35,.35); d=Vector((math.cos(a),math.sin(a),0)); side=Vector((-d.y,d.x,0))
        base=d*rng.uniform(.015,.085); h=rng.uniform(hmin,hmax); ln=lean*rng.uniform(.45,1.25); w=width*rng.uniform(.7,1.25)
        start=len(verts); matidx=1 if rng.random()<.24 else 0
        for s in range(segs+1):
            t=s/segs; r=ln*t*t; z=h*(t-.16*t**3); center=base+d*r+Vector((0,0,z))
            ww=w*(.35+.85*math.sin(math.pi*(.10+.88*t)))*(1-t*t*.92)
            for k in [-1,0,1]:
                p=center+side*ww*k+Vector((0,0,.004*(1-abs(k))*(1-t)))
                verts.append(tuple(p));wind.append(t)
        for s in range(segs):
            for k in range(2):
                a0=start+s*3+k;faces.append((a0,a0+1,a0+4,a0+3));indices.append(1 if s>=segs-1 else matidx)
    o=mesh_obj(name,verts,faces,c,materials=mats,indices=indices,smooth=True)
    at=o.data.attributes.new('VC_Wind','FLOAT','POINT')
    for i,v in enumerate(wind):at.data[i].value=v
    return o

def make_rice_library(M):
    lib=collection('COL_Library_RiceClumps',collection('COL_AssetLibrary'))
    for i in range(7):
        rng=random.Random(SEED+100+i)
        blade_mesh(f'SM_Rice_CompoundClump_v{i:02d}',rng,lib,[M['rice'],M['rice_light']],blades=8+i%3,hmin=.18,hmax=.37,lean=.17)
    return lib

def make_grass_library(M):
    lib=collection('COL_Library_BundGrass',collection('COL_AssetLibrary'))
    for i in range(5):
        rng=random.Random(SEED+200+i)
        blade_mesh(f'SM_Bund_GrassTuft_v{i:02d}',rng,lib,[M['grass'],M['rice_light']],blades=7,hmin=.06,hmax=.20,width=.009,lean=.10,segs=3)
    return lib

def append_tube(verts,faces,indices,points,radii,matidx,sides=7):
    pts=[Vector(p) for p in points];start=len(verts)
    for i,p in enumerate(pts):
        tan=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized();ref=Vector((0,0,1)) if abs(tan.z)<.9 else Vector((1,0,0))
        u=tan.cross(ref).normalized();v=tan.cross(u).normalized();r=radii[i] if isinstance(radii,list) else radii
        for j in range(sides):
            a=2*math.pi*j/sides;verts.append(tuple(p+r*(math.cos(a)*u+math.sin(a)*v)))
    for i in range(len(pts)-1):
        for j in range(sides):
            a=start+i*sides+j;b=start+i*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides));indices.append(matidx)

def palm_variant(i,M,parent):
    rng=random.Random(SEED+300+i); col=collection(f'COL_Library_Coconut_v{i:02d}',parent)
    h=12.5+i*1.35+rng.uniform(-.6,.6); bend=.7+i*.18; pts=[];rad=[]
    for s in range(55):
        t=s/54;pts.append((bend*t*t,.22*math.sin(t*2.1),h*t));rad.append((.25-.105*t)*(1+.065*math.sin(s*2.5))*(1+.35*math.exp(-t*18)))
    tube(f'SM_Coconut_Trunk_v{i:02d}',pts,rad,col,M['trunk'],10)
    top=Vector(pts[-1]);verts=[];faces=[];indices=[]
    for f in range(14):
        a=2*math.pi*f/14+rng.uniform(-.16,.16);d=Vector((math.cos(a),math.sin(a),0));side=Vector((-d.y,d.x,0));L=rng.uniform(3.4,4.9);droop=rng.uniform(.8,1.8)
        dry=f>=12; mi=1 if dry else 0
        rach=[]
        for s in range(13):
            t=s/12;rach.append(top+d*(L*t)+Vector((0,0,.85*math.sin(math.pi*t*.85)-droop*t*t)))
        append_tube(verts,faces,indices,rach,[.055*(1-s/15) for s in range(13)],mi,5)
        for k in range(2,38):
            t=k/39; anchor=top+d*(L*t)+Vector((0,0,.85*math.sin(math.pi*t*.85)-droop*t*t))
            ll=(.98*math.sin(math.pi*t)**.55+.12)*rng.uniform(.85,1.1)
            for sign in [-1,1]:
                ld=(side*sign+d*.38+Vector((0,0,-.30-.35*t))).normalized();sw=Vector((-ld.y,ld.x,0)).normalized();st=len(verts)
                for q in range(4):
                    u=q/3;cen=anchor+ld*ll*u+Vector((0,0,-.16*u*u));ww=.030*math.sin(math.pi*(.08+.88*u))*(1-u*.5)
                    for z in [-1,0,1]:verts.append(tuple(cen+sw*ww*z*1.35+Vector((0,0,.010*(1-abs(z))))))
                for q in range(3):
                    for z in range(2):
                        a0=st+q*3+z;faces.append((a0,a0+1,a0+4,a0+3));indices.append(mi)
    mesh_obj(f'SM_Coconut_Fronds_v{i:02d}',verts,faces,col,materials=[M['palm_leaf'],M['palm_dry']],indices=indices,smooth=True)
    for k in range(7):
        a=k*2.4;p=top+Vector((.24*math.cos(a),.24*math.sin(a),-.22-.08*(k%3)))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=6,radius=.13,location=p)
        o=bpy.context.object;o.name=f'SM_Coconut_Fruit_v{i:02d}_{k}';o.data.materials.append(M['palm_dry']);
        for cc in list(o.users_collection):cc.objects.unlink(o)
        col.objects.link(o)
    return col

def make_palms(M,positions):
    parent=collection('COL_Library_CoconutPalms',collection('COL_AssetLibrary'))
    variants=[palm_variant(i,M,parent) for i in range(4)]
    dest=collection('COL_CoconutPalms');rng=random.Random(SEED+330)
    for i,(x,y,s) in enumerate(positions):
        e=bpy.data.objects.new(f'SM_Coconut_InstanceOf_{i:03d}',None);dest.objects.link(e);e.instance_type='COLLECTION';e.instance_collection=variants[i%4];e.location=(x,y,0);e.scale=(s,s,s);e.rotation_euler.z=rng.uniform(0,6.283)

def broadleaf_variant(i,M,lib):
    rng=random.Random(SEED+400+i);verts=[];faces=[];indices=[];h=8.5+i*.65
    append_tube(verts,faces,indices,[(0,0,0),(.12,0,h*.35),(-.1,.1,h*.7),(0,0,h)],[.26,.20,.12,.035],0,8)
    clusters=[]
    for b in range(11):
        a=b*2.399+rng.uniform(-.2,.2);z=h*(.28+.050*b);r=rng.uniform(1.8,3.5)*(1-.22*b/11)
        end=Vector((math.cos(a)*r,math.sin(a)*r,z+rng.uniform(.7,1.8)))
        append_tube(verts,faces,indices,[(0,0,z),tuple(end*.55+Vector((0,0,z*.45))),tuple(end)],[.095,.055,.014],0,6)
        for q in range(3):clusters.append(end+Vector((rng.uniform(-.8,.8),rng.uniform(-.8,.8),rng.uniform(-.3,.8))))
    clusters.append(Vector((0,0,h+.4)))
    for cen in clusters:
        for l in range(42):
            off=Vector((rng.gauss(0,.68),rng.gauss(0,.68),rng.gauss(0,.46)));p=cen+off
            a=rng.uniform(0,6.283);d=Vector((math.cos(a),math.sin(a),rng.uniform(-.45,.35))).normalized();side=Vector((-d.y,d.x,0)).normalized();L=rng.uniform(.34,.62);W=L*.38;st=len(verts)
            verts += [tuple(p),tuple(p+d*L*.45+side*W),tuple(p+d*L),tuple(p+d*L*.45-side*W),tuple(p+d*L*.48+Vector((0,0,.035)))]
            for f in [(0,1,4),(1,2,4),(2,3,4),(3,0,4)]:faces.append(tuple(st+j for j in f));indices.append(1)
    return mesh_obj(f'SM_Tropical_Tree_v{i:02d}',verts,faces,lib,materials=[M['trunk'],M['tree_leaf']],indices=indices,smooth=True)

def make_forest(M,points):
    lib=collection('COL_Library_BroadleafTrees',collection('COL_AssetLibrary'))
    for i in range(6):broadleaf_variant(i,M,lib)
    ng=scatter_group('GN_Scatter_TropicalTreeBelt_v01',lib,6)
    return scatter_points('SM_Tropical_TreeBelt_Instances',points,collection('COL_TreeLine'),ng,SEED+410,1.,.75,1.35)

def banana_variant(i,M,lib):
    rng=random.Random(SEED+500+i);h=1.7+i*.2
    tube(f'SM_Banana_Pseudostem_v{i}',[(0,0,0),(.03,0,h*.5),(0,0,h)],[.14,.12,.08],lib,M['banana'],8)
    verts=[];faces=[]
    for l in range(9):
        a=l*2.399+i;d=Vector((math.cos(a),math.sin(a),0));side=Vector((-d.y,d.x,0));L=rng.uniform(1.3,2.2);W=rng.uniform(.22,.36);st=len(verts)
        for s in range(9):
            t=s/8;cen=Vector((0,0,h))+d*(L*t)+Vector((0,0,1.15*math.sin(math.pi*t*.72)-.32*t*t));ww=W*math.sin(math.pi*(.05+.9*t))**.7
            tear=.62 if s in [3,5,7] and l%2 else (.85 if s in [4,6] else 1.)
            for k in [-1,0,1]:verts.append(tuple(cen+side*ww*k*tear+Vector((0,0,-.07*abs(k)+.025*(1-abs(k))))))
        for s in range(8):
            for k in range(2):a0=st+s*3+k;faces.append((a0,a0+1,a0+4,a0+3))
    mesh_obj(f'SM_Banana_Leaves_v{i}',verts,faces,lib,M['banana'],smooth=True)

def make_bananas(M,positions):
    lib=collection('COL_Library_Banana',collection('COL_AssetLibrary'))
    for i in range(3):banana_variant(i,M,lib)
    objs=list(lib.objects)
    # join each pseudostem/leaf pair into a single source object for collection instancing
    pairs=[]
    for i in range(3):
        stem=bpy.data.objects.get(f'SM_Banana_Pseudostem_v{i}');leaf=bpy.data.objects.get(f'SM_Banana_Leaves_v{i}')
        bpy.ops.object.select_all(action='DESELECT');stem.select_set(True);leaf.select_set(True);bpy.context.view_layer.objects.active=stem;bpy.ops.object.join();pairs.append(bpy.context.object)
    dest=collection('COL_Banana_Clumps');rng=random.Random(SEED+520)
    for i,(x,y) in enumerate(positions):
        src=pairs[i%3];o=linked_copy(src,f'SM_Banana_Clump_{i:02d}',(x,y,0),dest,rng.uniform(.8,1.25),(0,0,rng.uniform(0,6.283)))
    return pairs
