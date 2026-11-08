#!/usr/bin/env python3
"""Independent v4 verification: uploaded coconut use, hashes, receipts, disclosures.
Run: sh scripts/blender-py scripts/verify_kerala_v4.py
"""
import bpy,os,sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
blend=ROOT/'output/Kerala_Coconut_Realism.blend'
imgs=[ROOT/'output/Kerala_Coconut_Realism_900p.png',ROOT/'output/Kerala_Coconut_Realism_House_Detail_540p.png',ROOT/'output/Kerala_Coconut_Realism_Coconut_Detail.png']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
bpy.ops.wm.open_mainfile(filepath=str(blend));s=bpy.context.scene
user_inst=[o for o in bpy.data.objects if o.type=='EMPTY' and o.instance_collection and o.instance_collection.name=='COL_User_Coconut_Asset']
rice=bpy.data.objects.get('SM_Paddy_Q_RowInstances');house_root=bpy.data.objects.get('SM_Tharavad_House_Root');path=bpy.data.objects.get('SM_V4_Irregular_Muddy_Footpath')
def excluded(name):
    def walk(lc):
        if lc.collection.name==name:return lc.exclude
        for ch in lc.children:
            r=walk(ch)
            if r is not None:return r
        return None
    return walk(bpy.context.view_layer.layer_collection)
rt=ROOT/'docs/COCONUT_GLB_ROUNDTRIP_V4.json';rtj=json.loads(rt.read_text()) if rt.exists() else {}
conv=ROOT/'docs/COCONUT_GLB_CONVERSION.json';convj=json.loads(conv.read_text()) if conv.exists() else {}
src=ROOT/'assets/models/user/coconut_tree_low_poly.glb';glb=ROOT/'output/Coconut_Tree_Scene_Ready.glb'
ref_readme=ROOT/'output/References/README.md'
checks={
 'blend_exists':blend.exists(),'all_renders_exist':all(p.exists() for p in imgs),
 'revision':s.get('revision'),'engine':s.render.engine,'device':s.cycles.device,
 'resolution':[s.render.resolution_x,s.render.resolution_y],'samples_max':s.cycles.samples,
 'camera':s.camera.name if s.camera else None,'units':s.unit_settings.system,
 'user_coconut_instances':len(user_inst),'rice_instance_points':rice.get('instance_points') if rice else None,
 'v4_path_present':path is not None,'house_root_present':house_root is not None,
 'packed_images':sum(1 for im in bpy.data.images if im.packed_file),'materials':len(bpy.data.materials),'objects':len(bpy.data.objects),
 'asset_library_excluded':excluded('COL_AssetLibrary') is True,'source_libs_excluded':all(excluded(c.name) is True for c in bpy.data.collections if c.name.startswith('LIB_')),
 'source_glb_sha_match':sha(src)==convj.get('sha256') or sha(src)==convj.get('glb_sha256'),
 'scene_ready_glb_exists':glb.exists(),'glb_roundtrip_pass':rtj.get('pass') is True,'glb_leaf_alpha_mask':rtj.get('leaf_alphaMode')=='MASK',
 'generated_references_disclosed':ref_readme.exists() and 'ai-generated' in ref_readme.read_text().lower(),
 'reference_disclosure_prop':bool(s.get('generated_reference_disclosure')),
}
receipts={}
for p in imgs:
    r=Path(str(p)+'.receipt.json')
    if r.exists():receipts[p.name]=json.loads(r.read_text())
    checks[p.stem+'_receipt_scene_hash_match']=receipts.get(p.name,{}).get('blend_sha256')==sha(blend)
required=[checks['blend_exists'],checks['all_renders_exist'],checks['revision']=='kerala-v4.0-user-coconut',checks['engine']=='CYCLES',checks['user_coconut_instances']>=20,checks['rice_instance_points'] and checks['rice_instance_points']>50000,checks['house_root_present'],checks['packed_images']>20,checks['asset_library_excluded'],checks['source_libs_excluded'],checks['scene_ready_glb_exists'],checks['glb_roundtrip_pass'],checks['glb_leaf_alpha_mask'],checks['generated_references_disclosed']]
required += [checks[p.stem+'_receipt_scene_hash_match'] for p in imgs]
result={'pass':all(required),'blend_sha256':sha(blend),'image_sha256':{p.name:sha(p) for p in imgs},'checks':checks,'receipts':receipts}
(ROOT/'docs/KERALA_VALIDATION_V4.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));sys.stdout.flush();os._exit(0 if result['pass'] else 1)
