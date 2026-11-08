"""Import, normalize and shade the user-supplied coconut GLB for Kerala v4.
The uploaded trunk/frond meshes are preserved; only metric scale, materials and
small coconut fruit clusters are added. CC BY 4.0 attribution is required.
"""
import math,random
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
GLB=ROOT/'assets/models/user/coconut_tree_low_poly.glb'

def _collection(name,parent=None):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name);(parent or bpy.context.scene.collection).children.link(c)
    return c

def _move(o,c):
    for old in list(o.users_collection):old.objects.unlink(o)
    c.objects.link(o)

def import_user_coconut(parent=None,scale=.1,seed=4407):
    """Return (collection, scene_mats, export_mats). Dimensions are metres."""
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    new=[o for o in bpy.data.objects if o not in before]
    meshes=[o for o in new if o.type=='MESH']
    c=_collection('COL_User_Coconut_Asset',parent)
    rng=random.Random(seed)
    trunk=leaf=None
    for o in meshes:
        mw=o.matrix_world.copy();o.parent=None;o.matrix_world=mw
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        for v in o.data.vertices:v.co*=scale
        o.data.update()
        if 'palm02' in [m.name for m in o.data.materials if m]:
            o.name='SM_UserCoconut_Trunk';trunk=o
        else:
            o.name='SM_UserCoconut_Fronds';leaf=o
        _move(o,c)
    for o in new:
        if o.type!='MESH' and o.name in bpy.data.objects:bpy.data.objects.remove(o,do_unlink=True)
    # Scene materials: keep the uploaded atlases/UVs, add restrained thin-leaf scatter.
    leaf_mat=bpy.data.materials.get('date_palm_leaf');trunk_mat=bpy.data.materials.get('palm02')
    if leaf_mat:
        nt=leaf_mat.node_tree;p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
        # Identify base-color vs normal by existing links.
        base_tex=None;norm_tex=None
        for n in nt.nodes:
            if n.type=='TEX_IMAGE':
                if any(l.to_node==p and l.to_socket.name=='Base Color' for l in nt.links):pass
                for l in nt.links:
                    if l.from_node==n and l.to_node==p and l.to_socket.name=='Base Color':base_tex=n
                if any(l.from_node==n and l.to_node.type=='NORMAL_MAP' for l in nt.links):norm_tex=n
        if base_tex:
            hs=nt.nodes.new('ShaderNodeHueSaturation');hs.inputs['Saturation'].default_value=.82;hs.inputs['Value'].default_value=1.08
            nt.links.new(base_tex.outputs['Color'],hs.inputs['Color']);nt.links.new(hs.outputs['Color'],p.inputs['Base Color'])
            tr=nt.nodes.new('ShaderNodeBsdfTranslucent');nt.links.new(hs.outputs['Color'],tr.inputs['Color'])
            mx=nt.nodes.new('ShaderNodeMixShader');mx.inputs[0].default_value=.18
            nt.links.new(p.outputs['BSDF'],mx.inputs[1]);nt.links.new(tr.outputs['BSDF'],mx.inputs[2]);nt.links.new(mx.outputs['Shader'],out.inputs['Surface'])
        p.inputs['Roughness'].default_value=.58
        if 'Specular IOR Level' in p.inputs:p.inputs['Specular IOR Level'].default_value=.25
        leaf_mat.blend_method='CLIP';leaf_mat.alpha_threshold=.494;leaf_mat.use_backface_culling=False
    if trunk_mat:
        nt=trunk_mat.node_tree;p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
        base_tex=next((l.from_node for l in nt.links if l.to_node==p and l.to_socket.name=='Base Color' and l.from_node.type=='TEX_IMAGE'),None)
        if base_tex:
            hs=nt.nodes.new('ShaderNodeHueSaturation');hs.inputs['Saturation'].default_value=.62;hs.inputs['Value'].default_value=.82
            nt.links.new(base_tex.outputs['Color'],hs.inputs['Color']);nt.links.new(hs.outputs['Color'],p.inputs['Base Color'])
        p.inputs['Roughness'].default_value=.92
    # Small fruit clusters below the crown; the uploaded crown starts around 9.2 m.
    fruit_mats=[]
    for name,col in [('MAT_Coconut_Green',(.12,.20,.045)),('MAT_Coconut_Ochre',(.28,.22,.065))]:
        m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*col,1);b.inputs['Roughness'].default_value=.72
        nt=m.node_tree;n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=35;bp=nt.nodes.new('ShaderNodeBump');bp.inputs['Strength'].default_value=.18;bp.inputs['Distance'].default_value=.012;nt.links.new(n.outputs['Fac'],bp.inputs['Height']);nt.links.new(bp.outputs['Normal'],b.inputs['Normal']);fruit_mats.append(m)
    for cl,ang in enumerate([.3,2.35,4.4]):
        cx=math.cos(ang)*.24;cy=math.sin(ang)*.24;cz=11.9+rng.uniform(-.2,.2)
        for k in range(5):
            a=rng.uniform(0,6.28);r=rng.uniform(.04,.18);loc=(cx+r*math.cos(a),cy+r*math.sin(a),cz-rng.uniform(0,.32))
            bpy.ops.mesh.primitive_uv_sphere_add(segments=14,ring_count=10,radius=.125,location=loc)
            o=bpy.context.object;o.name=f'SM_UserCoconut_Fruit_{cl}_{k}';o.scale=(1,1,1.14);o.data.materials.append(fruit_mats[(cl+k)%2]);_move(o,c)
    # glTF-compatible export materials: Principled + texture alpha, no Cycles-only mix.
    def export_mat(name,src,alpha=False):
        m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;p=nt.nodes['Principled BSDF']
        if src:
            snt=src.node_tree
            for n in snt.nodes:
                if n.type=='TEX_IMAGE' and n.image:
                    is_norm=any(l.from_node==n and l.to_node.type=='NORMAL_MAP' for l in snt.links)
                    t=nt.nodes.new('ShaderNodeTexImage');t.image=n.image
                    if is_norm:
                        nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.8;nt.links.new(t.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],p.inputs['Normal'])
                    else:
                        nt.links.new(t.outputs['Color'],p.inputs['Base Color'])
                        if alpha:
                            gt=nt.nodes.new('ShaderNodeMath');gt.operation='GREATER_THAN';gt.inputs[1].default_value=.494;nt.links.new(t.outputs['Alpha'],gt.inputs[0]);nt.links.new(gt.outputs[0],p.inputs['Alpha'])
        p.inputs['Roughness'].default_value=.58 if alpha else .92
        if 'Specular IOR Level' in p.inputs:p.inputs['Specular IOR Level'].default_value=.25
        if alpha:m.blend_method='CLIP';m.alpha_threshold=.494;m.use_backface_culling=False
        return m
    ex_leaf=export_mat('GLB_UserCoconut_Leaf',leaf_mat,True);ex_trunk=export_mat('GLB_UserCoconut_Trunk',trunk_mat,False)
    scene_mats={'leaf':leaf_mat,'trunk':trunk_mat};export_mats={'leaf':ex_leaf,'trunk':ex_trunk}
    c['source']='User upload: Coconut Tree Low poly by Pixel_Monster / ar.jethin, CC BY 4.0'
    c['source_url']='https://sketchfab.com/3d-models/coconut-tree-low-poly-8c5d6b661b2f4c37834d87cd187eb907'
    c['normalization']='Uploaded meshes preserved; uniform 0.1 scale to metres; fruit clusters added.'
    return c,scene_mats,export_mats

def export_glb(collection,scene_mats,export_mats,path):
    # The asset may live under an excluded asset-library collection. Temporarily
    # expose only its collection path so the exporter can select its meshes.
    vl=bpy.context.view_layer;saved=[]
    def find_path(lc,target,acc):
        nxt=acc+[lc]
        if lc.collection.name==target:return nxt
        for ch in lc.children:
            r=find_path(ch,target,nxt)
            if r:return r
        return None
    chain=find_path(vl.layer_collection,collection.name,[]) or []
    for lc in chain:
        saved.append((lc,lc.exclude,lc.hide_viewport));lc.exclude=False;lc.hide_viewport=False
    bpy.context.view_layer.update()
    original={}
    for o in collection.objects:
        if o.type!='MESH':continue
        original[o.name]=[m for m in o.data.materials]
        if o.name=='SM_UserCoconut_Fronds':o.data.materials.clear();o.data.materials.append(export_mats['leaf'])
        elif o.name=='SM_UserCoconut_Trunk':o.data.materials.clear();o.data.materials.append(export_mats['trunk'])
    bpy.ops.object.select_all(action='DESELECT')
    for o in collection.objects:
        if o.type=='MESH':o.select_set(True)
    bpy.context.view_layer.objects.active=next(o for o in collection.objects if o.type=='MESH')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_image_format='AUTO',export_extras=True)
    for o in collection.objects:
        if o.name in original:
            o.data.materials.clear()
            for m in original[o.name]:o.data.materials.append(m)
    for lc,ex,hv in saved:lc.exclude=ex;lc.hide_viewport=hv
    bpy.ops.object.select_all(action='DESELECT')
