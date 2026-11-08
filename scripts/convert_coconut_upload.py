#!/usr/bin/env python3
"""Validate a binary glTF upload and restore its .glb suffix without transcoding.
Usage: python3 scripts/convert_coconut_upload.py /path/to/coconut_tree_low_poly.glb.txt
"""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SRC=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/arena-coding-uploads/coconut_tree_low_poly.glb.txt')
DST=ROOT/'assets/models/user/coconut_tree_low_poly.glb'
b=SRC.read_bytes();assert b[:4]==b'glTF','Upload is not binary glTF'
version,length=struct.unpack_from('<II',b,4);assert version==2 and length==len(b),'Invalid glTF version or byte length'
chunks=[];offset=12
while offset<length:
 n,t=struct.unpack_from('<II',b,offset);offset+=8;assert offset+n<=length,'Truncated GLB chunk'
 chunks.append({'type':{0x4E4F534A:'JSON',0x004E4942:'BIN'}.get(t,hex(t)),'bytes':n});offset+=n
assert offset==length and [x['type'] for x in chunks]==['JSON','BIN']
j=json.loads(b[20:20+chunks[0]['bytes']]);assert j['asset']['version']=='2.0'
assert all('uri' not in x for x in j.get('buffers',[])+j.get('images',[])),'GLB is not self-contained'
DST.parent.mkdir(parents=True,exist_ok=True);DST.write_bytes(b)
r={'original_filename':SRC.name,'original_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'conversion':'Restore .glb suffix; already valid self-contained glTF 2.0 binary. No mesh or texture transcode.','output':str(DST.relative_to(ROOT)),'chunks':chunks,'asset':j['asset'],'counts':{k:len(j.get(k,[])) for k in ['nodes','meshes','materials','textures','images','accessors']}}
(ROOT/'docs/COCONUT_GLB_CONVERSION.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
