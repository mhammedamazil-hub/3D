#!/usr/bin/env python3
"""Verify the corrected single-sun Kerala v5.1 MP4 and receipt."""
import json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
mp4=ROOT/'output/Kerala_Coconut_Realism_GodRays_FIXED_1080p30_5s.mp4'
rec=ROOT/'docs/KERALA_ANIMATION_V51_RECEIPT.json'
checks={'mp4_exists':mp4.exists(),'receipt_exists':rec.exists()}
r={}
if rec.exists():
    r=json.loads(rec.read_text())
    checks['sha_match']=mp4.exists() and hashlib.sha256(mp4.read_bytes()).hexdigest()==r.get('sha256')
    st=r.get('ffprobe',{}).get('streams',[{}])[0]
    checks['1920x1080']=st.get('width')==1920 and st.get('height')==1080
    checks['30fps']=st.get('r_frame_rate')=='30/1'
    checks['150_frames']=int(st.get('nb_frames',0))==150
    checks['5_seconds']=abs(float(st.get('duration',0))-5.0)<0.05
    checks['revision']=r.get('revision')=='kerala-v5.1-single-sun-rays'
    a=r.get('lighting_audit',{})
    checks['one_sun']=a.get('sun_count')==1
    checks['no_spot_shafts']=a.get('spot_count')==0
    checks['no_fake_cones']=not a.get('fake_shaft_objects')
    checks['no_emissive_volumes']=not a.get('emissive_volume_materials')
    checks['vent_grid_fixed']=not a.get('unparented_vent_parts')
result={'pass':all(checks.values()),'checks':checks,'mp4_sha256':hashlib.sha256(mp4.read_bytes()).hexdigest() if mp4.exists() else None}
(ROOT/'docs/KERALA_ANIMATION_V51_VALIDATION.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));sys.exit(0 if result['pass'] else 1)
