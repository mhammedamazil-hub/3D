#!/usr/bin/env python3
"""Independent frozen-v3 verification: hashes, packed images, key scene facts.
Run: sh scripts/blender-py scripts/verify_kerala_v3.py
"""
import bpy,os,sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
blend=ROOT/'output/Kerala_Quality.blend';hero=ROOT/'output/Kerala_Quality_900p.png';house=ROOT/'output/Kerala_Quality_House_Detail_540p.png'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
bpy.ops.wm.open_mainfile(filepath=str(blend));s=bpy.context.scene
rice=bpy.data.objects.get('SM_Paddy_Q_RowInstances');path=bpy.data.objects.get('SM_Q_Wet_Earthen_Footpath');house_root=bpy.data.objects.get('SM_Tharavad_House_Root')
checks={
 'blend_exists':blend.exists(),'hero_exists':hero.exists(),'house_detail_exists':house.exists(),
 'revision':s.get('revision'),'engine':s.render.engine,'device':s.cycles.device,
 'resolution':[s.render.resolution_x,s.render.resolution_y],'samples_max':s.cycles.samples,
 'camera':s.camera.name if s.camera else None,'units':s.unit_settings.system,
 'rice_instance_points':rice.get('instance_points') if rice else None,
 'path_material':path.data.materials[0].name if path and path.data.materials else None,
 'house_root_present':house_root is not None,'house_location':list(house_root.location) if house_root else None,
 'packed_images':sum(1 for im in bpy.data.images if im.packed_file),
 'materials':len(bpy.data.materials),'objects':len(bpy.data.objects),
 'infinigen_broadleaf_collection':bpy.data.collections.get('LIB_Broadleaf_Infinigen_Instance') is not None,
 'scanned_jacaranda':bpy.data.collections.get('LIB_jacaranda_tree') is not None,
 'no_photo_backplate':'no photo backplate' in (s.get('reference_provenance','')+s.get('sky_disclosure','')).lower(),
}
receipts={}
for p in [hero,house]:
 r=p.with_suffix(p.suffix+'.receipt.json')
 if r.exists():receipts[p.name]=json.loads(r.read_text())
checks['hero_receipt_scene_hash_match']=receipts.get(hero.name,{}).get('blend_sha256')==sha(blend) if hero.exists() else False
checks['house_receipt_scene_hash_match']=receipts.get(house.name,{}).get('blend_sha256')==sha(blend) if house.exists() else False
result={'pass':all([checks['blend_exists'],checks['hero_exists'],checks['house_detail_exists'],checks['revision']=='kerala-v3.0-quality',checks['engine']=='CYCLES',checks['rice_instance_points'] and checks['rice_instance_points']>50000,checks['house_root_present'],checks['packed_images']>20,checks['hero_receipt_scene_hash_match'],checks['house_receipt_scene_hash_match']]),'blend_sha256':sha(blend),'hero_sha256':sha(hero),'house_sha256':sha(house),'checks':checks,'receipts':receipts}
(ROOT/'docs/KERALA_VALIDATION_V3.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));sys.stdout.flush();os._exit(0 if result['pass'] else 1)
