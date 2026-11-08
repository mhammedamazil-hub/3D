import bpy

def new_mat(name):
    m=bpy.data.materials.new(name);m.use_nodes=True
    nt=m.node_tree;nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial');out.location=(700,80)
    p=nt.nodes.new('ShaderNodeBsdfPrincipled');p.location=(390,80);nt.links.new(p.outputs['BSDF'],out.inputs['Surface'])
    return m,nt,p,out

def setp(p,name,val):
    if name in p.inputs:p.inputs[name].default_value=val

def noise_node(nt,scale=10,detail=3,rough=.65,loc=(-650,100)):
    n=nt.nodes.new('ShaderNodeTexNoise');n.location=loc;n.inputs['Scale'].default_value=scale;n.inputs['Detail'].default_value=detail;n.inputs['Roughness'].default_value=rough
    tc=nt.nodes.new('ShaderNodeTexCoord');tc.location=(loc[0]-200,loc[1]);nt.links.new(tc.outputs['Object'],n.inputs['Vector'])
    return n

def ramp(nt,src,stops,loc=(-330,160)):
    r=nt.nodes.new('ShaderNodeValToRGB');r.location=loc
    e=r.color_ramp.elements
    while len(e)>2:e.remove(e[-1])
    for i,(pos,col) in enumerate(stops):
        el=e[i] if i<2 else e.new(pos);el.position=pos;el.color=(*col,1)
    nt.links.new(src,r.inputs['Fac']);return r

def simple(name,color,rough=.7,metal=0.,bump=None):
    m,nt,p,out=new_mat(name);setp(p,'Base Color',(*color,1));setp(p,'Roughness',rough);setp(p,'Metallic',metal)
    if bump:
        n=noise_node(nt,bump[0],3);b=nt.nodes.new('ShaderNodeBump');b.location=(160,-160);b.inputs['Strength'].default_value=bump[1];b.inputs['Distance'].default_value=bump[2];nt.links.new(n.outputs['Fac'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
    m.diffuse_color=(*color,1);return m

def varied(name,colors,scale=8,rough=.75,bump_dist=.03,bump_strength=.25,stretch=None):
    m,nt,p,out=new_mat(name);n=noise_node(nt,scale,4)
    if stretch:
        mp=nt.nodes.new('ShaderNodeMapping');mp.location=(-650,100);mp.inputs['Scale'].default_value=stretch
        tc=nt.nodes.new('ShaderNodeTexCoord');tc.location=(-850,100);nt.links.new(tc.outputs['Object'],mp.inputs['Vector']);nt.links.new(mp.outputs['Vector'],n.inputs['Vector']);n.location=(-440,100)
    r=ramp(nt,n.outputs['Fac'],[(.22,colors[0]),(.55,colors[1]),(.82,colors[2])])
    nt.links.new(r.outputs['Color'],p.inputs['Base Color']);setp(p,'Roughness',rough)
    b=nt.nodes.new('ShaderNodeBump');b.location=(160,-160);b.inputs['Strength'].default_value=bump_strength;b.inputs['Distance'].default_value=bump_dist;nt.links.new(n.outputs['Fac'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
    m.diffuse_color=(*colors[1],1);return m

def leaf(name,base):
    m,nt,p,out=new_mat(name)
    setp(p,'Roughness',.48);setp(p,'Specular IOR Level',.28)
    oi=nt.nodes.new('ShaderNodeObjectInfo');oi.location=(-650,250)
    r=ramp(nt,oi.outputs['Random'],[(0,tuple(c*.72 for c in base)),(.5,base),(1,tuple(min(1,c*1.18+.015) for c in base))],(-420,250))
    tr=nt.nodes.new('ShaderNodeBsdfTranslucent');tr.location=(160,-100);nt.links.new(r.outputs['Color'],tr.inputs['Color'])
    nt.links.new(r.outputs['Color'],p.inputs['Base Color'])
    mix=nt.nodes.new('ShaderNodeMixShader');mix.location=(540,80);mix.inputs[0].default_value=.16;nt.links.new(p.outputs['BSDF'],mix.inputs[1])
    nt.links.new(tr.outputs['BSDF'],mix.inputs[2]);nt.links.new(mix.outputs['Shader'],out.inputs['Surface'])
    m.diffuse_color=(*base,1);return m

def build_materials():
    M={}
    M['rice']=leaf('MAT_Rice_LivingBlade',(0.055,.205,.035))
    M['rice_light']=leaf('MAT_Rice_YoungTip',(0.12,.30,.050))
    M['grass']=leaf('MAT_Bund_Grass',(0.10,.22,.035))
    M['palm_leaf']=leaf('MAT_Coconut_PinnateLeaf',(0.075,.20,.035))
    M['palm_dry']=leaf('MAT_Coconut_SenescentFrond',(0.24,.16,.065))
    M['tree_leaf']=leaf('MAT_Tropical_Broadleaf',(0.055,.155,.045))
    M['banana']=leaf('MAT_Banana_Lamina',(0.12,.29,.055))
    M['trunk']=varied('MAT_Coconut_RingedBark',[(.105,.085,.055),(.25,.21,.15),(.38,.34,.25)],12,.9,.045,.45,stretch=(3,3,.35))
    M['wood']=varied('MAT_Old_Teak_Grain',[(.035,.018,.009),(.105,.052,.022),(.20,.115,.052)],5,.62,.018,.25,stretch=(1,1,14))
    M['darkwood']=varied('MAT_Carved_ShadowWood',[(.018,.009,.004),(.055,.025,.01),(.10,.05,.02)],9,.7,.012,.25,stretch=(1,1,12))
    M['tile']=varied('MAT_Fired_Clay_Tiles',[(.115,.032,.016),(.30,.090,.038),(.46,.185,.080)],9,.82,.018,.3)
    M['tile_moss']=varied('MAT_Roof_Lichen_and_Soot',[(.055,.065,.035),(.16,.15,.075),(.30,.23,.13)],14,.95,.02,.35)
    M['plaster']=varied('MAT_Weathered_Lime_Wash',[(.38,.31,.20),(.64,.55,.38),(.78,.70,.53)],4,.91,.025,.3)
    M['laterite']=varied('MAT_Porous_Laterite',[(.14,.055,.028),(.32,.125,.065),(.46,.22,.12)],13,.95,.055,.5)
    M['mortar']=simple('MAT_Lime_Mortar',(.30,.27,.21),.95,bump=(25,.3,.02))
    M['mud']=varied('MAT_Wet_Bund_Earth',[(.025,.014,.007),(.085,.045,.020),(.16,.090,.040)],6,.30,.040,.45)
    M['paddy_mud']=varied('MAT_Paddy_Bathymetry',[(.025,.038,.018),(.075,.095,.040),(.14,.13,.065)],4,.92,.035,.35)
    M['stone']=varied('MAT_Worn_Granite_Steps',[(.12,.13,.12),(.25,.26,.23),(.38,.37,.31)],10,.86,.04,.4)
    M['brass']=simple('MAT_Aged_Brass',(.38,.24,.075),.34,.85,bump=(35,.12,.006))
    M['pot']=varied('MAT_Terracotta_Jar',[(.18,.07,.035),(.34,.14,.07),(.48,.23,.12)],15,.85,.012,.2)
    M['rock']=varied('MAT_Ghat_Rock_and_Forest',[(.018,.055,.032),(.060,.115,.062),(.16,.185,.15)],.11,.96,1.4,.5)
    M['far_rock']=varied('MAT_Distant_Ghat_Massif',[(.055,.105,.10),(.13,.20,.19),(.24,.30,.29)],.035,.98,1.5,.35)
    # Closed shallow dielectric paddy water; mud is separate bathymetry below.
    m,nt,p,out=new_mat('MAT_Paddy_Water_IOR_1p333')
    setp(p,'Base Color',(.68,.76,.66,1));setp(p,'Roughness',.045);setp(p,'Transmission Weight',1.0);setp(p,'IOR',1.333)
    n=noise_node(nt,3.5,2,.55);mp=nt.nodes.new('ShaderNodeMapping');mp.location=(-650,100);mp.inputs['Scale'].default_value=(1.0,3.8,1)
    tc=nt.nodes.new('ShaderNodeTexCoord');tc.location=(-850,100);nt.links.new(tc.outputs['Object'],mp.inputs['Vector']);nt.links.new(mp.outputs['Vector'],n.inputs['Vector']);n.location=(-440,100)
    b=nt.nodes.new('ShaderNodeBump');b.location=(140,-130);b.inputs['Strength'].default_value=.16;b.inputs['Distance'].default_value=.018;nt.links.new(n.outputs['Fac'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],p.inputs['Normal'])
    ab=nt.nodes.new('ShaderNodeVolumeAbsorption');ab.location=(380,-280);ab.inputs['Color'].default_value=(.58,.73,.57,1);ab.inputs['Density'].default_value=.22;nt.links.new(ab.outputs['Volume'],out.inputs['Volume'])
    m.diffuse_color=(.30,.42,.32,1);M['water']=m
    M['lamp']=simple('MAT_Lamp_Wick',(.9,.45,.08),.5);setp(M['lamp'].node_tree.nodes.get('Principled BSDF'),'Emission Color',(.95,.40,.06,1));setp(M['lamp'].node_tree.nodes.get('Principled BSDF'),'Emission Strength',.4)
    return M
