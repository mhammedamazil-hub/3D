"""Build compact botanical library for Kerala v3 from verified Infinigen probes.
Requires vendor/sources/infinigen/infinigen-main/src on PYTHONPATH.
Keeps broadleaf branch/leaf instancing live; does NOT decimate leaf source meshes
(an earlier .45 decimate collapsed leaves). Coconut GN is excluded after OOM.
"""
import bpy,os,sys,json,time,math,random
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'assets/quality/botanical_library.blend';OUT.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
lib=bpy.data.collections.new('Kerala_Botanical_Library');bpy.context.scene.collection.children.link(lib)
manifest={'source':'Princeton Infinigen BSD-3-Clause','source_commit':'edac8171aac4a34974c7bcd5c5652a3b59e89880','assets':[]}
sys.path.insert(0,str(ROOT/'vendor/sources/infinigen/infinigen-main/src'))
from infinigen.assets.objects.trees.generate import TreeFactory
from infinigen.assets.objects.monocot.banana import BananaMonocotFactory
# Generate the verified safe broadleaf tree inline (live instancing; no leaf decimation).
class TropicalTreeFactory(TreeFactory):
 n_leaf=5;n_twig=2
 @staticmethod
 def get_leaf_type(season):return ['leaf_broadleaf']
 def __init__(self,seed,**kw):super().__init__(seed,season='summer',fruit_chance=0.0,realize=False,**kw)
fac=TropicalTreeFactory(9917);ph=fac.create_placeholder(0,loc=(0,0,0),rot=(0,0,0));fac.finalize_placeholders([ph]);o=fac.create_asset(ph,face_size=.05,distance=30)
o.name='LIB_Broadleaf_Infinigen';ph.hide_render=True;ph.hide_set(True);lib.objects.link(o)
manifest['assets'].append({'name':'LIB_Broadleaf_Infinigen','type':'procedural broadleaf tree, live instancing','seed':9917,'height_m':6.8})
# Generate 3 banana clump stems with verified modified BananaMonocotFactory.
mat=bpy.data.materials.new('Banana_Leaf_Veins');mat.use_nodes=True;nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.46
attr=nt.nodes.new('ShaderNodeAttribute');attr.attribute_name='distance';mix=nt.nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.035,.12,.018,1);mix.inputs[2].default_value=(.11,.27,.045,1);nt.links.new(attr.outputs['Fac'],mix.inputs[0]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=90;bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.006;nt.links.new(noise.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
trans=nt.nodes.new('ShaderNodeBsdfTranslucent');trans.inputs[0].default_value=(.18,.32,.07,1);mixsh=nt.nodes.new('ShaderNodeMixShader');mixsh.inputs[0].default_value=.22;nt.links.new(bs.outputs[0],mixsh.inputs[1]);nt.links.new(trans.outputs[0],mixsh.inputs[2]);nt.links.new(mixsh.outputs[0],nt.nodes.get('Material Output').inputs['Surface'])
for i,seed in enumerate([5511,5521,5531]):
 fac=BananaMonocotFactory(seed);fac.count=12+i*2;fac.leaf_range=(.18,1);fac.min_y_angle=-.15;fac.max_y_angle=1.2;fac.z_drag=.16;fac.z_scale=1.0+i*.06;fac.bend_angle=.22;fac.twist_angle=.12;fac.radius=.075;fac.stem_offset=.85
 o=fac.create_asset(face_size=.02);o.name=f'LIB_Banana_{i+1:02d}';o.data.materials.clear();o.data.materials.append(mat);lib.objects.link(o);o.location=(i*4,0,0)
 manifest['assets'].append({'name':o.name,'type':'procedural banana monocot','seed':seed,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'height_m':o.dimensions.z})
# Hide library source objects from render by default; build will instance them.
for o in lib.objects:o.hide_render=True;o.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
(ROOT/'docs/BOTANICAL_LIBRARY_V3.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2));sys.stdout.flush();os._exit(0)
