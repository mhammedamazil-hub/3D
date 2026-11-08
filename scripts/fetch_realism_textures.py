#!/usr/bin/env python3
import json,sys,urllib.request,hashlib,time
from pathlib import Path
OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True);records=[]
def get(u):
 with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Kerala-Blender/2'}),timeout=90) as f:return f.read()
def j(u):return json.loads(get(u))
def save(u,rel,aid):
 d=get(u);p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(d);records.append({'path':str(rel),'url':u,'source':'https://polyhaven.com/a/'+aid,'license':'CC0-1.0','bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()});print('SAVED',rel,len(d))
# One actual CC0 broadleaf tree model library asset (1K blend). Keep under 45 MB.
for aid in ['island_tree_02']:
 try:
  files=j('https://api.polyhaven.com/files/'+aid);b=files.get('blend',{}).get('1k',{}).get('blend') or files.get('blend',{}).get('2k',{}).get('blend')
  if b:
   d=get(b['url'])
   if len(d)<=45_000_000:save(b['url'],f'models/{aid}/{aid}.blend',aid)
   else:print('SKIP large blend',aid,len(d))
   for inc,o in b.get('include',{}).items():
    # textures already fetched in realism2; only save missing small includes
    p=OUT/'models'/aid/inc
    if not p.exists():
     dd=get(o['url'])
     if len(dd)<=8_000_000:save(o['url'],f'models/{aid}/{inc}',aid)
 except Exception as e:print('FAIL model',aid,repr(e))
ids=['brown_mud','clay_roof_tiles','bark_brown_02','worn_plaster_wall','rock_face','red_laterite_soil_stones','wood_planks','corrugated_iron_02','aerial_rocks_02','forest_ground_04']
for aid in ids:
 try:
  files=j('https://api.polyhaven.com/files/'+aid);meta=j('https://api.polyhaven.com/info/'+aid);(OUT/aid).mkdir(parents=True,exist_ok=True);(OUT/aid/'metadata.json').write_text(json.dumps(meta,indent=2))
  for ch in ['Diffuse','Rough','Displacement','nor_gl','AO','Metal']:
   node=files.get(ch,{})
   res=node.get('1k') or node.get('2k')
   if not isinstance(res,dict):continue
   fmt=next((k for k in ['jpg','png','exr'] if k in res and isinstance(res[k],dict) and 'url' in res[k]),None)
   if not fmt:continue
   url=res[fmt]['url'];ext=url.split('?')[0].rsplit('.',1)[-1];save(url,f'{aid}/{ch}.{ext}',aid)
 except Exception as e:print('FAIL',aid,repr(e))
(OUT/'manifest.json').write_text(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':records},indent=2));print('DONE',len(records))
