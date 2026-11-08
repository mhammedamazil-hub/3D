"""Quality-first Kerala v3 helpers: high-res PBR, botanical collection instances,
row paddy with open water, earthen bunds, detailed coconut palms, rocky Ghats.
Native editable Blender geometry; no photo backplate.
"""
import math, random, sys
from pathlib import Path
import bpy
from mathutils import Vector
from kerala_helpers import collection, mesh_obj, box, tube, linked_copy, scatter_group, scatter_points, fbm, aim
from kerala_materials import new_mat, setp, noise_node, ramp, simple, varied, leaf
from kerala_config import SEED, HOUSE_X, HOUSE_Y
ROOT=Path(__file__).resolve().parent.parent
Q=ROOT/'assets/quality'
TEX=Q/'textures'
MODELS=Q/'models'
HDRI=Q/'hdri/overcast_soil_puresky_4k.hdr'

def find_map(aid,*names):
    d=TEX/aid
    if not d.exists():return None
    for n in names:
        for ext in ['jpg','png','exr','hdr']:
            p=d/f'{n}.{ext}'
            if p.exists():return p
    return None

def tex_node(nt,path,scale=1.,noncolor=False,projection='BOX'):
    img=bpy.data.images.load(str(path),check_existing=True)
    if noncolor:
        try:img.colorspace_settings.name='Non-Color'
        except Exception:pass
    t=nt.nodes.new('ShaderNodeTexImage');t.image=img;t.projection=projection
    if hasattr(t,'projection_blend'):t.projection_blend=.25
    tc=nt.nodes.new('ShaderNodeTexCoord');mp=nt.nodes.new('ShaderNodeMapping');mp.inputs['Scale'].default_value=(scale,scale,scale)
    nt.links.new(tc.outputs['Object'],mp.inputs['Vector']);nt.links.new(mp.outputs['Vector'],t.inputs['Vector'])
    return t

def pbrq(name,aid,scale=1.,tint=(1,1,1),rough=.8,metal=0.,bump=.04,tint_fac=.18,use_diffuse=True):
    m,nt,p,out=new_mat(name)
    diff=find_map(aid,'Diffuse','diffuse') if use_diffuse else None
    if diff:
        t=tex_node(nt,diff,scale);mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=tint_fac;mix.inputs[2].default_value=(*tint,1)
        nt.links.new(t.outputs['Color'],mix.inputs[1]);nt.links.new(mix.outputs['Color'],p.inputs['Base Color'])
    else:setp(p,'Base Color',(*tint,1))
    r=find_map(aid,'Rough','rough')
    if r:
        t=tex_node(nt,r,scale,True);mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=rough
        nt.links.new(t.outputs['Color'],mul.inputs[0]);nt.links.new(mul.outputs[0],p.inputs['Roughness'])
    else:setp(p,'Roughness',rough)
    setp(p,'Metallic',metal)
    h=find_map(aid,'Displacement','disp') or r
    if h:
        t=tex_node(nt,h,scale,True);b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.35;b.inputs['Distance'].default_value=bump
        nt.links.new(t.outputs['Color'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
    m.diffuse_color=(*tint,1);return m

def quality_materials(M):
    M['mud']=pbrq('MAT_Q_Wet_Earthen_Bund_4K','brown_mud',.42,(.055,.030,.015),.65,bump=.04,tint_fac=.85,use_diffuse=False)
    try:
        _p=next(n for n in M['mud'].node_tree.nodes if n.type=='BSDF_PRINCIPLED');_p.inputs['Specular IOR Level'].default_value=.15
    except Exception:pass
    M['paddy_mud']=pbrq('MAT_Q_Paddy_Mud_Bottom','brown_mud',.5,(.07,.06,.032),.85,bump=.04,tint_fac=.75)
    M['laterite']=pbrq('MAT_Q_Porous_Laterite_4K','red_laterite_soil_stones',.55,(.52,.24,.12),.96,bump=.08,tint_fac=.22)
    M['wood_planks']=pbrq('MAT_Q_Timber_Crossing_2K','wood_planks',.38,(.24,.14,.065),.55,bump=.03,tint_fac=.35)
    M['wood']=pbrq('MAT_Q_Old_Teak_2K','wood_planks',.30,(.20,.11,.045),.58,bump=.022,tint_fac=.42)
    M['trunk']=pbrq('MAT_Q_Bark_2K','bark_brown_02',.7,(.32,.25,.17),.93,bump=.05,tint_fac=.18)
    M['metal']=pbrq('MAT_Q_Corrugated_Vent_2K','corrugated_iron_02',1.1,(.64,.63,.59),.42,metal=1.,bump=.035,tint_fac=.08)
    # Lime wash: warm procedural color + scanned plaster relief.
    m,nt,p,out=new_mat('MAT_Q_Weathered_Lime_Wash')
    n=noise_node(nt,3.0,4);r=ramp(nt,n.outputs['Fac'],[(.2,(.36,.30,.20)),(.55,(.63,.54,.37)),(.82,(.76,.68,.52))]);nt.links.new(r.outputs['Color'],p.inputs['Base Color']);setp(p,'Roughness',.93)
    h=find_map('worn_plaster_wall','Displacement')
    if h:
        t=tex_node(nt,h,.6,True);b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.18;b.inputs['Distance'].default_value=.02;nt.links.new(t.outputs['Color'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
    M['plaster']=m
    # Fired clay tiles: scanned color/roughness/relief on real overlapping geometry.
    m,nt,p,out=new_mat('MAT_Q_Fired_Clay_Tiles_4K')
    diff=find_map('clay_roof_tiles','Diffuse')
    if diff:
        t=tex_node(nt,diff,1.8);mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.35;mix.inputs[2].default_value=(.55,.22,.10,1);nt.links.new(t.outputs['Color'],mix.inputs[1]);nt.links.new(mix.outputs['Color'],p.inputs['Base Color'])
    else:setp(p,'Base Color',(.28,.09,.04,1))
    rr=find_map('clay_roof_tiles','Rough')
    if rr:
        t=tex_node(nt,rr,1.8,True);nt.links.new(t.outputs['Color'],p.inputs['Roughness'])
    else:setp(p,'Roughness',.82)
    h=find_map('clay_roof_tiles','Displacement')
    if h:
        t=tex_node(nt,h,1.8,True);b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.22;b.inputs['Distance'].default_value=.02;nt.links.new(t.outputs['Color'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
    M['tile']=m
    M['stone']=pbrq('MAT_Q_Granite_Steps','rock_face',.8,(.30,.30,.27),.86,bump=.05,tint_fac=.25)
    # Paddy water: shallow, slightly turbid, visible between rows.
    m,nt,p,out=new_mat('MAT_Q_Paddy_Water_Shallow')
    setp(p,'Base Color',(.55,.64,.52,1));setp(p,'Roughness',.075);setp(p,'Transmission Weight',.92);setp(p,'IOR',1.333)
    n=noise_node(nt,4.5,2,.55);b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.10;b.inputs['Distance'].default_value=.012;nt.links.new(n.outputs['Fac'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
    ab=nt.nodes.new('ShaderNodeVolumeAbsorption');ab.inputs['Color'].default_value=(.48,.62,.45,1);ab.inputs['Density'].default_value=.45;nt.links.new(ab.outputs['Volume'],out.inputs['Volume'])
    M['water']=m
    # Rice: darker, narrower, less lawn-like.
    def pos_leaf(name,stops,rough=.55,trans=.14):
        m,nt,pr,out=new_mat(name);geo=nt.nodes.new('ShaderNodeNewGeometry');ns=nt.nodes.new('ShaderNodeTexNoise');ns.inputs['Scale'].default_value=2.2;ns.inputs['Detail'].default_value=3;nt.links.new(geo.outputs['Position'],ns.inputs['Vector'])
        r=ramp(nt,ns.outputs['Fac'],[(.2,stops[0]),(.55,stops[1]),(.85,stops[2])]);nt.links.new(r.outputs['Color'],pr.inputs['Base Color']);setp(pr,'Roughness',rough);setp(pr,'Specular IOR Level',.24)
        tr=nt.nodes.new('ShaderNodeBsdfTranslucent');nt.links.new(r.outputs['Color'],tr.inputs['Color']);mx=nt.nodes.new('ShaderNodeMixShader');mx.inputs[0].default_value=trans;nt.links.new(pr.outputs['BSDF'],mx.inputs[1]);nt.links.new(tr.outputs['BSDF'],mx.inputs[2]);nt.links.new(mx.outputs['Shader'],out.inputs['Surface']);return m
    M['rice']=pos_leaf('MAT_Q_Rice_LivingBlade',[(.018,.055,.014),(.050,.125,.028),(.115,.185,.045)])
    M['rice_light']=pos_leaf('MAT_Q_Rice_YoungTip',[(.075,.145,.032),(.150,.225,.052),(.235,.295,.075)],.52,.16)
    M['grass']=pos_leaf('MAT_Q_Bund_Grass',[(.028,.075,.018),(.070,.140,.032),(.135,.195,.052)])
    M['palm_leaf']=pos_leaf('MAT_Q_Coconut_Leaflet',[(.030,.095,.022),(.070,.170,.040),(.130,.230,.060)],.5,.22)
    M['palm_dry']=pos_leaf('MAT_Q_Coconut_DryTip',[(.16,.115,.040),(.26,.190,.070),(.36,.280,.110)],.68,.10)
    # Mountain: forested lower slopes, scanned rock on steep/upper faces.
    def mountain(name,aid,scale,forest,rocktint,far=False):
        m,nt,p,out=new_mat(name);geo=nt.nodes.new('ShaderNodeNewGeometry');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(geo.outputs['Normal'],sep.inputs['Vector'])
        mr=nt.nodes.new('ShaderNodeMapRange');mr.inputs['From Min'].default_value=.30;mr.inputs['From Max'].default_value=.70;nt.links.new(sep.outputs['Z'],mr.inputs['Value'])
        inv=nt.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1.;nt.links.new(mr.outputs['Result'],inv.inputs[1])
        pos=nt.nodes.new('ShaderNodeNewGeometry');pz=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(pos.outputs['Position'],pz.inputs['Vector']);hz=nt.nodes.new('ShaderNodeMapRange');hz.inputs['From Min'].default_value=40 if not far else 65;hz.inputs['From Max'].default_value=110 if not far else 160;nt.links.new(pz.outputs['Z'],hz.inputs['Value']);mx=nt.nodes.new('ShaderNodeMath');mx.operation='MAXIMUM';nt.links.new(inv.outputs[0],mx.inputs[0]);nt.links.new(hz.outputs['Result'],mx.inputs[1])
        fn=noise_node(nt,.08 if not far else .03,4);fr=ramp(nt,fn.outputs['Fac'],[(.2,forest[0]),(.6,forest[1]),(.85,forest[2])])
        diff=find_map(aid,'Diffuse');rt=tex_node(nt,diff,scale) if diff else None
        mix=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(mx.outputs[0],mix.inputs[0]);nt.links.new(fr.outputs['Color'],mix.inputs[1])
        if rt:
            tint=nt.nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=.35;tint.inputs[2].default_value=(*rocktint,1);nt.links.new(rt.outputs['Color'],tint.inputs[1]);nt.links.new(tint.outputs['Color'],mix.inputs[2])
        else:mix.inputs[2].default_value=(*rocktint,1)
        nt.links.new(mix.outputs['Color'],p.inputs['Base Color']);setp(p,'Roughness',.97)
        h=find_map(aid,'Displacement')
        if h:
            t=tex_node(nt,h,scale,True);b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.5;b.inputs['Distance'].default_value=1.4 if not far else 2.2;nt.links.new(t.outputs['Color'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
        return m
    M['rock']=mountain('MAT_Q_Ghat_ForestRock','rock_face',.10,[(.012,.030,.022),(.025,.055,.038),(.045,.080,.055)],(.18,.19,.18))
    M['far_rock']=mountain('MAT_Q_Distant_Ghat','rock_face',.04,[(.070,.090,.100),(.110,.140,.150),(.170,.200,.210)],(.20,.23,.25),True)
    return M

def import_prepared_model(aid,lib_parent):
    p=MODELS/f'{aid}.blend'
    if not p.exists():return None
    name=aid+'_prepared'
    with bpy.data.libraries.load(str(p),link=False) as (df,dt):
        dt.objects=[n for n in df.objects if n==name]
    objs=[o for o in dt.objects if o]
    if not objs:return None
    c=collection(f'LIB_{aid}',lib_parent)
    for o in objs:
        c.objects.link(o);o.location=(0,0,0);o.rotation_euler=(0,0,0);o.scale=(1,1,1);o.hide_render=False;o.hide_viewport=False
    c['source']='Poly Haven CC0';c['asset_id']=aid
    return c

def import_botanical(lib_parent):
    p=Q/'botanical_library.blend'
    if not p.exists():return None,None
    with bpy.data.libraries.load(str(p),link=False) as (df,dt):
        dt.collections=[n for n in df.collections if n.startswith('assets:')]
        dt.objects=[n for n in df.objects if n.startswith('LIB_Broadleaf') or n.startswith('LIB_Banana')]
    for c in dt.collections:
        if c and c.name not in lib_parent.children:lib_parent.children.link(c)
    broad=None;bananas=[]
    for o in dt.objects:
        if not o:continue
        if o.name.startswith('LIB_Broadleaf'):
            broad=o
        elif o.name.startswith('LIB_Banana'):
            bananas.append(o)
    bc=None
    if broad:
        bc=collection('LIB_Broadleaf_Infinigen_Instance',lib_parent)
        # Include live GN child hierarchy in the instanced collection.
        def add_tree(o):
            if o.name not in bc.objects:bc.objects.link(o)
            o.hide_render=False;o.hide_viewport=False
            for ch in o.children:add_tree(ch)
        add_tree(broad)
        # Hide any placeholder cube descendants.
        for o in bc.objects:
            if o.type=='MESH' and len(o.data.vertices)==8 and o.name.startswith('Cube'):o.hide_render=True
    return bc,bananas

def collection_instance(name,coll,loc,scale,rot_z,c):
    o=bpy.data.objects.new(name,None);c.objects.link(o);o.instance_collection=coll;o.instance_type='COLLECTION';o.location=loc
    s=scale if isinstance(scale,(tuple,list)) else (scale,scale,scale);o.scale=s;o.rotation_euler=(0,0,rot_z);return o

def decimated_variant(src_coll,name,ratio,lib_parent):
    objs=[o for o in src_coll.objects if o.type=='MESH']
    if not objs:return None
    c=collection(name,lib_parent)
    for src in objs:
        me=src.data.copy();o=bpy.data.objects.new(src.name+'_bg',me);c.objects.link(o)
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        md=o.modifiers.new('Background LOD','DECIMATE');md.ratio=ratio
        try:bpy.ops.object.modifier_apply(modifier=md.name)
        except Exception:o.modifiers.remove(md)
    return c

def build_palm_library(M,lib_parent,count=4):
    lib=collection('LIB_CoconutPalms',lib_parent);rng=random.Random(SEED+330)
    variants=[]
    for v in range(count):
        c=collection(f'LIB_Coconut_v{v:02d}',lib);H=10.5+v*1.2+rng.uniform(-.5,.5);lean=Vector((rng.uniform(.4,1.2),rng.uniform(-.4,.4),0));R=16;S=64;verts=[];faces=[]
        for j in range(S+1):
            t=j/S;z=H*t;rad=(.24*(1-t)+.145*t)*(1+.075*math.sin(t*170+v)+.025*math.sin(t*53));cen=lean*t+Vector((.10*math.sin(t*5+v),.07*math.cos(t*7),z))
            for i in range(R):
                a=2*math.pi*i/R;verts.append(tuple(cen+Vector((rad*math.cos(a),rad*math.sin(a),0))))
        for j in range(S):
            for i in range(R):faces.append((j*R+i,j*R+(i+1)%R,(j+1)*R+(i+1)%R,(j+1)*R+i))
        mesh_obj(f'SM_Coconut_Trunk_v{v:02d}',verts,faces,c,M['trunk'],True)
        crown=lean+Vector((.10*math.sin(5+v),.07*math.cos(7),H));lv=[];lf=[];mats=[]
        nf=32+v*2
        for f in range(nf):
            ang=2*math.pi*f/nf+rng.uniform(-.14,.14);elev=rng.uniform(.05,.65);length=rng.uniform(2.8,4.4);droop=rng.uniform(.8,1.8);dirv=Vector((math.cos(ang),math.sin(ang),0))
            def rachis(t):return crown+dirv*(length*t)+Vector((0,0,length*(elev*t-droop*t*t)))
            for seg in range(12):
                t0=seg/12;t1=(seg+1)/12;p0=rachis(t0);p1=rachis(t1);side=dirv.cross(Vector((0,0,1))).normalized()*.022;base=len(lv);lv.extend([tuple(p0-side),tuple(p0+side),tuple(p1+side),tuple(p1-side)]);lf.append((base,base+1,base+2,base+3));mats.append(1 if f>=nf-3 else 0)
            for k in range(64):
                t=.10+.88*k/63;p=rachis(t);tangent=(rachis(min(1,t+.02))-rachis(max(0,t-.02))).normalized();side=dirv.cross(Vector((0,0,1))).normalized()
                for sign in [-1,1]:
                    ll=rng.uniform(.38,.72)*(1-.30*t);w=.045;ldir=(side*sign*.82+tangent*.22+Vector((0,0,-.50))).normalized();fold=Vector((0,0,.025));base=len(lv);pts=[p,p+ldir*ll*.5+fold,p+ldir*ll,p+ldir*ll*.5-fold]
                    for q in range(3):
                        a=pts[q];b=pts[q+1];ww=w*(1-q/3);lv.extend([tuple(a-side*ww),tuple(a+side*ww),tuple(b+side*ww),tuple(b-side*ww)]);lf.append((base+q*4,base+q*4+1,base+q*4+2,base+q*4+3));mats.append(1 if (f>=nf-3 or rng.random()<.06) else 0)
        fr=mesh_obj(f'SM_Coconut_Fronds_v{v:02d}',lv,lf,c,materials=[M['palm_leaf'],M['palm_dry']],indices=mats,smooth=True)
        for i in range(8):
            a=rng.uniform(0,6.28);r=rng.uniform(.12,.26);loc=crown+Vector((r*math.cos(a),r*math.sin(a),-.24-rng.random()*.22));bpy.ops.mesh.primitive_uv_sphere_add(segments=10,ring_count=7,radius=.105,location=loc);o=bpy.context.object;o.name=f'SM_Coconut_Nut_v{v}_{i}';o.data.materials.append(M['palm_dry'])
            for cc in list(o.users_collection):cc.objects.unlink(o)
            c.objects.link(o)
        variants.append(c)
    return variants

def setup_quality_world(scene):
    world=bpy.data.worlds.get('WORLD_Kerala_Quality') or bpy.data.worlds.new('WORLD_Kerala_Quality');scene.world=world;world.use_nodes=True;nt=world.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputWorld');bg=nt.nodes.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.85
    if HDRI.exists():
        env=nt.nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(HDRI),check_existing=True);tc=nt.nodes.new('ShaderNodeTexCoord');mp=nt.nodes.new('ShaderNodeMapping');mp.inputs['Rotation'].default_value[2]=math.radians(140);nt.links.new(tc.outputs['Generated'],mp.inputs['Vector']);nt.links.new(mp.outputs['Vector'],env.inputs['Vector']);hs=nt.nodes.new('ShaderNodeHueSaturation');hs.inputs['Saturation'].default_value=.55;hs.inputs['Value'].default_value=1.1;nt.links.new(env.outputs['Color'],hs.inputs['Color']);nt.links.new(hs.outputs['Color'],bg.inputs['Color'])
        scene['sky_disclosure']='CC0 Poly Haven overcast_soil_puresky 4K HDRI for lighting/reflections only; all landscape/house/vegetation is native 3D geometry, no photo backplate.'
    else:bg.inputs['Color'].default_value=(.65,.72,.78,1)
    nt.links.new(bg.outputs['Background'],out.inputs['Surface'])
