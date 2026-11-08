"""Photoreal revision helpers: CC0 PBR materials, library import, sapling trees, fine detail.
Run inside Blender 4.2 via scripts/blender-py. Raw large model assets are local/CI-retrieved;
the delivered .blend packs all used images. Provenance: assets/realism/PROVENANCE.json.
"""
import math, random, sys
from pathlib import Path
import bpy
from mathutils import Vector
from kerala_helpers import collection, mesh_obj, box, tube, linked_copy, scatter_group, scatter_points, fbm
from kerala_materials import new_mat, setp, noise_node, ramp, simple, varied, leaf
from kerala_config import SEED, HOUSE_X, HOUSE_Y

ROOT=Path(__file__).resolve().parent.parent
TEX=ROOT/'assets/textures/polyhaven'
MODELS=ROOT/'assets/models/polyhaven'
RAW=ROOT/'assets/models/raw'
HDRI=ROOT/'assets/hdri/kloofendal_48d_partly_cloudy_puresky_2k.hdr'

def find_map(aid,*names):
    d=TEX/aid
    if not d.exists():return None
    for n in names:
        for ext in ['jpg','png','exr','hdr']:
            p=d/f'{n}.{ext}'
            if p.exists():return p
    return None

def tex_node(nt,path,scale=1.0,noncolor=False,projection='BOX'):
    img=bpy.data.images.load(str(path),check_existing=True)
    if noncolor:
        try:img.colorspace_settings.name='Non-Color'
        except Exception:pass
    t=nt.nodes.new('ShaderNodeTexImage');t.image=img;t.projection=projection
    if hasattr(t,'projection_blend'):t.projection_blend=.25
    tc=nt.nodes.new('ShaderNodeTexCoord');mp=nt.nodes.new('ShaderNodeMapping');mp.inputs['Scale'].default_value=(scale,scale,scale)
    nt.links.new(tc.outputs['Object'],mp.inputs['Vector']);nt.links.new(mp.outputs['Vector'],t.inputs['Vector'])
    return t

def pbr(name,aid,scale=1.,tint=(1,1,1),rough=.8,metal=0.,bump=.04,tint_fac=.18):
    m,nt,p,out=new_mat(name)
    diff=find_map(aid,'Diffuse','diffuse','diff')
    if diff:
        t=tex_node(nt,diff,scale)
        mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=tint_fac;mix.inputs[2].default_value=(*tint,1)
        nt.links.new(t.outputs['Color'],mix.inputs[1]);nt.links.new(mix.outputs['Color'],p.inputs['Base Color'])
    else:setp(p,'Base Color',(*tint,1))
    r=find_map(aid,'Rough','rough','roughness')
    if r:
        t=tex_node(nt,r,scale,True);mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=rough
        nt.links.new(t.outputs['Color'],mul.inputs[0]);nt.links.new(mul.outputs[0],p.inputs['Roughness'])
    else:setp(p,'Roughness',rough)
    setp(p,'Metallic',metal)
    h=find_map(aid,'Displacement','disp','displacement','Bump') or r
    if h:
        t=tex_node(nt,h,scale,True);b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.30;b.inputs['Distance'].default_value=bump
        nt.links.new(t.outputs['Color'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
    m.diffuse_color=(*tint,1);return m

def upgrade_materials(M):
    M['mud']=pbr('MAT_Wet_Bund_Earth_CC0', 'brown_mud', .55, (.20,.13,.075), .22, bump=.055, tint_fac=.48)
    # Lime wash: warm procedural base with scanned micro-relief, not a stone diffuse.
    m,nt,pr,out=new_mat('MAT_Weathered_Lime_Wash_ScannedRelief')
    n=noise_node(nt,3.2,4);r=ramp(nt,n.outputs['Fac'],[(.2,(.40,.33,.21)),(.55,(.66,.56,.38)),(.82,(.78,.70,.53))]);nt.links.new(r.outputs['Color'],pr.inputs['Base Color']);setp(pr,'Roughness',.93)
    h=find_map('worn_plaster_wall','Displacement','disp')
    if h:
        t=tex_node(nt,h,.7,True);b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.16;b.inputs['Distance'].default_value=.018;nt.links.new(t.outputs['Color'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],pr.inputs['Normal'])
    M['plaster']=m
    M['laterite']=pbr('MAT_Porous_Laterite_CC0','red_laterite_soil_stones',.65,(.55,.26,.14),.96,bump=.075,tint_fac=.20)
    M['wood']=varied('MAT_Old_Teak_Grain_ScannedRough',[(.030,.014,.006),(.095,.046,.018),(.18,.10,.045)],5,.60,.018,.25,stretch=(1,1,14))
    wr=find_map('wood_planks','Rough','rough')
    if wr:
        nt=M['wood'].node_tree;pr=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');t=tex_node(nt,wr,.45,True);nt.links.new(t.outputs['Color'],pr.inputs['Roughness'])
    M['wood_planks']=pbr('MAT_Timber_Crossing_Planks_CC0','wood_planks',.45,(.26,.15,.07),.58,bump=.028,tint_fac=.32)
    M['trunk']=pbr('MAT_Bark_Brown_CC0','bark_brown_02',.8,(.34,.27,.19),.93,bump=.05,tint_fac=.15)
    M['metal']=pbr('MAT_Corrugated_Vent_Metal_CC0','corrugated_iron_02',1.2,(.66,.65,.61),.42,metal=1.,bump=.035,tint_fac=.06)
    # Keep hand-made overlapping tile geometry; add scanned clay micro-relief/roughness.
    m,nt,p,out=new_mat('MAT_Fired_Clay_Tiles_ScannedRelief')
    n=noise_node(nt,9,4);r=ramp(nt,n.outputs['Fac'],[(.2,(.070,.022,.011)),(.55,(.205,.062,.028)),(.82,(.335,.135,.058))]);nt.links.new(r.outputs['Color'],p.inputs['Base Color']);setp(p,'Roughness',.82)
    h=find_map('clay_roof_tiles','Displacement','disp')
    if h:
        t=tex_node(nt,h,2.5,True);b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.18;b.inputs['Distance'].default_value=.018;nt.links.new(t.outputs['Color'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
    M['tile']=m
    M['tile_moss']=varied('MAT_Roof_Lichen_Soot_Dark',[(.030,.040,.022),(.085,.090,.045),(.15,.14,.08)],14,.96,.02,.35)
    M['stone']=varied('MAT_Worn_Granite_Darker',[(.075,.085,.075),(.155,.165,.145),(.235,.235,.205)],10,.86,.04,.4)
    # Position-varied broadleaf shader, avoids one flat green per joined sapling mesh.
    m,nt,p,out=new_mat('MAT_Tropical_Broadleaf_PositionVaried')
    geo=nt.nodes.new('ShaderNodeNewGeometry');ns=nt.nodes.new('ShaderNodeTexNoise');ns.inputs['Scale'].default_value=2.4;ns.inputs['Detail'].default_value=3;nt.links.new(geo.outputs['Position'],ns.inputs['Vector'])
    r=ramp(nt,ns.outputs['Fac'],[(.2,(.025,.075,.022)),(.5,(.065,.17,.045)),(.8,(.14,.28,.07))]);nt.links.new(r.outputs['Color'],p.inputs['Base Color']);setp(p,'Roughness',.46);setp(p,'Specular IOR Level',.30)
    tr=nt.nodes.new('ShaderNodeBsdfTranslucent');nt.links.new(r.outputs['Color'],tr.inputs['Color']);mix=nt.nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.18;nt.links.new(p.outputs['BSDF'],mix.inputs[1]);nt.links.new(tr.outputs['BSDF'],mix.inputs[2]);nt.links.new(mix.outputs['Shader'],out.inputs['Surface'])
    M['tree_leaf']=m
    def pos_leaf(name,stops,rough=.55,trans=.12):
        m,nt,pr,out=new_mat(name);geo=nt.nodes.new('ShaderNodeNewGeometry');ns=nt.nodes.new('ShaderNodeTexNoise');ns.inputs['Scale'].default_value=1.9;ns.inputs['Detail'].default_value=3;nt.links.new(geo.outputs['Position'],ns.inputs['Vector'])
        r=ramp(nt,ns.outputs['Fac'],[(.2,stops[0]),(.55,stops[1]),(.85,stops[2])]);nt.links.new(r.outputs['Color'],pr.inputs['Base Color']);setp(pr,'Roughness',rough);setp(pr,'Specular IOR Level',.26)
        tr=nt.nodes.new('ShaderNodeBsdfTranslucent');nt.links.new(r.outputs['Color'],tr.inputs['Color']);mx=nt.nodes.new('ShaderNodeMixShader');mx.inputs[0].default_value=trans;nt.links.new(pr.outputs['BSDF'],mx.inputs[1]);nt.links.new(tr.outputs['BSDF'],mx.inputs[2]);nt.links.new(mx.outputs['Shader'],out.inputs['Surface']);return m
    M['rice']=pos_leaf('MAT_Rice_LivingBlade_Monsoon',[(.022,.068,.016),(.065,.150,.032),(.150,.225,.055)])
    M['rice_light']=pos_leaf('MAT_Rice_YoungTip_Monsoon',[(.10,.18,.040),(.19,.27,.060),(.28,.34,.085)],.52,.14)
    M['grass']=pos_leaf('MAT_Bund_Grass_Monsoon',[(.035,.090,.022),(.090,.165,.038),(.170,.230,.060)])
    # Slope-aware mountain shader: forested lower slopes, scanned rock on steep/upper faces.
    def mountain(name,aid,scale,forest,rocktint,far=False):
        m,nt,p,out=new_mat(name);geo=nt.nodes.new('ShaderNodeNewGeometry');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(geo.outputs['Normal'],sep.inputs['Vector'])
        mr=nt.nodes.new('ShaderNodeMapRange');mr.inputs['From Min'].default_value=.34;mr.inputs['From Max'].default_value=.74;nt.links.new(sep.outputs['Z'],mr.inputs['Value'])
        inv=nt.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1.0;nt.links.new(mr.outputs['Result'],inv.inputs[1])
        pos=nt.nodes.new('ShaderNodeNewGeometry');pz=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(pos.outputs['Position'],pz.inputs['Vector']);hz=nt.nodes.new('ShaderNodeMapRange');hz.inputs['From Min'].default_value=45 if not far else 70;hz.inputs['From Max'].default_value=120 if not far else 170;nt.links.new(pz.outputs['Z'],hz.inputs['Value']);mx=nt.nodes.new('ShaderNodeMath');mx.operation='MAXIMUM';nt.links.new(inv.outputs[0],mx.inputs[0]);nt.links.new(hz.outputs['Result'],mx.inputs[1])
        fn=noise_node(nt,.09 if not far else .035,4);fr=ramp(nt,fn.outputs['Fac'],[(.2,forest[0]),(.6,forest[1]),(.85,forest[2])])
        diff=find_map(aid,'Diffuse','diffuse');rt=None
        if diff:rt=tex_node(nt,diff,scale)
        mix=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(mx.outputs[0],mix.inputs[0]);nt.links.new(fr.outputs['Color'],mix.inputs[1])
        if rt:
            tint=nt.nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=.35;tint.inputs[2].default_value=(*rocktint,1);nt.links.new(rt.outputs['Color'],tint.inputs[1]);nt.links.new(tint.outputs['Color'],mix.inputs[2])
        else:mix.inputs[2].default_value=(*rocktint,1)
        nt.links.new(mix.outputs['Color'],p.inputs['Base Color']);setp(p,'Roughness',.97)
        h=find_map(aid,'Displacement','disp')
        if h:
            t=tex_node(nt,h,scale,True);b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.45;b.inputs['Distance'].default_value=1.2 if not far else 2.0;nt.links.new(t.outputs['Color'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
        return m
    M['rock']=mountain('MAT_Ghat_ForestRock_CC0','rock_face',.12,[(.014,.042,.024),(.036,.082,.040),(.075,.125,.065)],(.27,.28,.27))
    M['far_rock']=mountain('MAT_Distant_Ghat_CC0','aerial_rocks_02',.045,[(.055,.105,.10),(.095,.155,.145),(.16,.22,.21)],(.24,.30,.32),True)
    return M

def import_collection(asset_dir,name,collection_name=None):
    blend=Path(asset_dir)/f'{name}.blend'
    if not blend.exists():return None
    cname=collection_name or name
    with bpy.data.libraries.load(str(blend),link=False) as (src,dst):
        if cname in src.collections:dst.collections=[cname]
        else:dst.objects=[n for n in src.objects if n.startswith(name)]
    lib=collection('COL_AssetLibrary')
    dest=collection(f'COL_Library_{name}',lib)
    objs=[]
    for c in dst.collections:
        if c:
            dest.children.link(c) if c.name not in dest.children else None
            objs.extend([o for o in c.objects if o.type=='MESH'])
    for o in dst.objects:
        if o and o.type=='MESH':dest.objects.link(o);objs.append(o)
    if not objs:return None
    # Normalize source transforms into a reusable local library at origin.
    for o in objs:
        o.parent=None
        if o.location.length>1e-4:
            mw=o.matrix_world.copy();o.parent=None;o.matrix_world=mw
    dest['source']='Poly Haven CC0';dest['asset_id']=name
    return dest

def make_sapling_library(M,count=6):
    addon=ROOT/'vendor/addons/improved-sapling-tree-generator'
    sys.path.insert(0,str(addon))
    import sapling_4
    if not getattr(sapling_4,'_kerala_registered',False):sapling_4.register();sapling_4._kerala_registered=True
    lib=collection('COL_Library_SaplingBroadleaf',collection('COL_AssetLibrary'))
    made=[]
    for i in range(count):
        before=set(bpy.data.objects)
        bpy.ops.curve.tree_add(do_update=True,bevel=True,bevelRes=1,showLeaves=True,makeMesh=False,levels=4,
            branches=(0,26+i*2,8,6),length=(1,.42,.34,.24),lengthV=(.08,.16,.20,.25),shape='1',shapeS='4',
            baseSize=.27,leaves=20+i*2,leafScale=.19,leafScaleV=.25,leafShape='hex',leafType='0',
            scale=10.5+i*.7,scaleV=1.2,ratio=.022,seed=SEED+800+i)
        new=[o for o in bpy.data.objects if o not in before]
        trunk=next((o for o in new if o.name=='tree'),None);leaves=next((o for o in new if o.name=='leaves'),None)
        if trunk is None:continue
        bpy.ops.object.select_all(action='DESELECT');trunk.select_set(True);bpy.context.view_layer.objects.active=trunk
        if trunk.type=='CURVE':bpy.ops.object.convert(target='MESH')
        trunk=bpy.context.view_layer.objects.active;trunk.name=f'SM_Sapling_Trunk_v{i:02d}';trunk.data.materials.clear();trunk.data.materials.append(M['trunk'])
        if leaves:
            leaves.data.materials.clear();leaves.data.materials.append(M['tree_leaf']);leaves.select_set(True);bpy.context.view_layer.objects.active=trunk;bpy.ops.object.join()
        o=bpy.context.view_layer.objects.active;o.name=f'SM_Sapling_Broadleaf_v{i:02d}'
        for c in list(o.users_collection):c.objects.unlink(o)
        lib.objects.link(o);made.append(o)
        # join() removes the leaves object; avoid touching stale RNA pointers.
    return lib

def setup_hdri_world(scene):
    world=bpy.data.worlds.get('WORLD_Kerala_HDRI') or bpy.data.worlds.new('WORLD_Kerala_HDRI');scene.world=world;world.use_nodes=True
    nt=world.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputWorld');bg=nt.nodes.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=1.12
    if HDRI.exists():
        env=nt.nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(HDRI),check_existing=True)
        tc=nt.nodes.new('ShaderNodeTexCoord');mp=nt.nodes.new('ShaderNodeMapping');mp.inputs['Rotation'].default_value[2]=math.radians(115)
        nt.links.new(tc.outputs['Generated'],mp.inputs['Vector']);nt.links.new(mp.outputs['Vector'],env.inputs['Vector']);hs=nt.nodes.new('ShaderNodeHueSaturation');hs.inputs['Saturation'].default_value=.42;hs.inputs['Value'].default_value=1.22;nt.links.new(env.outputs['Color'],hs.inputs['Color'])
        mw=nt.nodes.new('ShaderNodeMixRGB');mw.inputs[0].default_value=.34;mw.inputs[2].default_value=(.76,.80,.83,1);nt.links.new(hs.outputs['Color'],mw.inputs[1]);nt.links.new(mw.outputs['Color'],bg.inputs['Color'])
        scene['sky_disclosure']='CC0 Poly Haven pure-sky HDRI for lighting/reflections; all landscape/house/vegetation is native 3D geometry, no photo backplate.'
    else:
        bg.inputs['Color'].default_value=(.65,.75,.85,1);scene['sky_disclosure']='Fallback procedural sky color; HDRI missing.'
    nt.links.new(bg.outputs['Background'],out.inputs['Surface'])

def metal_vent_and_wear(M):
    roof=bpy.data.collections.get('COL_House_Roof');walls=bpy.data.collections.get('COL_House_Walls')
    if not roof:return
    for o in list(roof.all_objects):
        if 'Vent_Gable' in o.name or 'Vent_Shadow' in o.name:
            o.data.materials.clear();o.data.materials.append(M['metal'])
    rng=random.Random(SEED+940)
    # Corrugated metal cladding ribs on the ventilator cheeks and cap.
    for sx in [-1,1]:
        for k in range(9):
            y=-2.28+k*.17
            tube(f'SM_Vent_Metal_Rib_{sx}_{k}',[(sx*1.18,y,5.16),(sx*.10,y+.55,5.74)],[.018,.018],roof,M['metal'],5)
    for k in range(10):
        x=-1.12+k*.25
        tube(f'SM_Vent_Cap_StandingSeam_{k}',[(x,-2.32,5.19),(x,-.88,5.19)],[.014,.014],roof,M['metal'],5)
    # Damp splash / porous laterite chips at plinth, subtle and motivated.
    if walls:
        for i in range(26):
            x=rng.uniform(-6.2,6.2);y=-4.72 if i<18 else rng.uniform(-4.4,4.4);z=rng.uniform(.18,.55)
            if i>=18:x=rng.choice([-6.52,6.52])
            box(f'SM_Laterite_Chip_{i}',(x,y,z),(rng.uniform(.08,.22),rng.uniform(.05,.12),rng.uniform(.05,.14)),walls,M['laterite'],.008,rot=(0,0,rng.uniform(0,3)))

def timber_crossing_and_drain(M,path_x,waterc,pathc):
    y=20.0;cx=path_x(y)
    box('SM_Drain_Crossing_Water',(cx,y,.055),(2.35,.62,.035),waterc,M['water'],.005)
    box('SM_Drain_Crossing_DarkBed',(cx,y,.025),(2.45,.72,.03),pathc,M['paddy_mud'])
    rng=random.Random(SEED+950)
    for k in range(6):
        x=cx-0.86+k*.345
        box(f'SM_Timber_Crossing_Plank_{k}',(x,y,.235+rng.uniform(-.008,.008)),(.30,1.08,.055),pathc,M['wood'],.012,rot=(rng.uniform(-.02,.02),rng.uniform(-.03,.03),rng.uniform(-.035,.035)))
    for sx in [-1,1]:
        tube(f'SM_Timber_Crossing_Bearer_{sx}',[(cx+sx*.78,y-.48,.17),(cx+sx*.78,y+.48,.17)],[.07,.07],pathc,M['darkwood'],7)
    # Narrow side drain along part of the bund, with wet banks.
    verts=[];faces=[]
    for j in range(121):
        yy=-8+j*.36;xx=path_x(yy)-1.02
        for i in range(3):verts.append((xx+(i-1)*.13,yy,.035))
    for j in range(120):
        for i in range(2):a=j*3+i;faces.append((a,a+1,a+4,a+3))
    mesh_obj('SM_Side_Drain_Water',verts,faces,waterc,M['water'],True)

def mist_banks(atmo):
    m=bpy.data.materials.new('MAT_Mist_Bank_Volume');m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');vs=nt.nodes.new('ShaderNodeVolumeScatter');vs.inputs['Color'].default_value=(.82,.88,.92,1);vs.inputs['Density'].default_value=.0032;vs.inputs['Anisotropy'].default_value=.55;nt.links.new(vs.outputs['Volume'],out.inputs['Volume'])
    for i,(y0,y1,z0,z1,d) in enumerate([(165,225,14,36,.006),(290,355,28,60,.005),(470,545,50,92,.004)]):
        o=box(f'SM_Mist_Bank_{i}',(0,(y0+y1)/2,(z0+z1)/2),(620,y1-y0,z1-z0),atmo,m)
        o['density_note']=d
