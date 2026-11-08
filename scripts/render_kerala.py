#!/usr/bin/env python3
"""Render the frozen Kerala scene with measured, receipt-backed presets.
Usage: scripts/blender-py scripts/render_kerala.py PRESET [--camera NAME] [--out PATH] [--size W H] [--samples N]
"""
import argparse, hashlib, json, sys, time
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from kerala_config import BLEND, REVIEW, OUTPUT, REVISION

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def apply_preset(name,samples=None):
    s=bpy.context.scene
    s.render.threads_mode='FIXED';s.render.threads=2;s.render.use_persistent_data=True
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB'
    if name=='clay':
        # Composition proxy: hide expensive field instances so software Workbench is usable.
        for cn in ['COL_FieldVegetation','COL_Banana_Clumps','COL_TreeLine','COL_Atmosphere','COL_SkyDome']:
            c=bpy.data.collections.get(cn)
            if c:c.hide_render=True
        s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=960;s.render.resolution_y=540
        d=s.display.shading;d.light='STUDIO';d.studio_light='paint.sl';d.color_type='SINGLE';d.single_color=(.62,.64,.63);d.show_shadows=True;d.show_cavity=True;d.cavity_type='BOTH';d.curvature_ridge_factor=1.2;d.curvature_valley_factor=1.0;d.cavity_ridge_factor=1.0;d.cavity_valley_factor=1.0;d.background_type='VIEWPORT';d.background_color=(.68,.73,.76)
        s.use_nodes=False
    elif name.startswith('eevee'):
        if name=='eevee_fast':
            # Measured software-GL LOD: fewer instances, no volume/ray tracing.
            for ob in bpy.data.objects:
                for md in ob.modifiers:
                    if md.type=='NODES' and md.node_group:
                        for sock in md.node_group.interface.items_tree:
                            if sock.item_type=='SOCKET' and sock.in_out=='INPUT' and sock.name=='Density':
                                f=.30 if 'Paddy' in ob.name else (.45 if 'Tree' in ob.name or 'Understory' in ob.name or 'Foothill' in ob.name else .55)
                                md[sock.identifier]=max(0.0,min(1.0,md.get(sock.identifier,1.0)*f))
            bpy.data.collections['COL_Atmosphere'].hide_render=True
        s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=samples or (16 if 'preview' in name else 32)
        s.eevee.use_raytracing=(name!='eevee_fast');s.eevee.ray_tracing_method='SCREEN';s.eevee.shadow_ray_count=1;s.eevee.shadow_step_count=4;s.eevee.volumetric_samples=16 if name=='eevee_fast' else 32;s.eevee.use_volumetric_shadows=False;s.eevee.use_shadows=True
        s.eevee.fast_gi_quality=.5;s.eevee.fast_gi_ray_count=2;s.eevee.fast_gi_step_count=8
        s.render.resolution_x=960 if 'preview' in name else 1920;s.render.resolution_y=540 if 'preview' in name else 1080
    else:
        s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.use_denoising=True;s.cycles.denoiser='OPENIMAGEDENOISE';s.cycles.use_adaptive_sampling=True
        if name=='cycles_preview':s.cycles.samples=samples or 12;s.cycles.adaptive_threshold=.10;s.cycles.adaptive_min_samples=4;s.render.resolution_x=640;s.render.resolution_y=360
        elif name=='cycles_bench':s.cycles.samples=samples or 24;s.cycles.adaptive_threshold=.06;s.cycles.adaptive_min_samples=8;s.render.resolution_x=960;s.render.resolution_y=540
        else:s.cycles.samples=samples or 96;s.cycles.adaptive_threshold=.03;s.cycles.adaptive_min_samples=24;s.render.resolution_x=1920;s.render.resolution_y=1080
        s.cycles.max_bounces=6;s.cycles.diffuse_bounces=3;s.cycles.glossy_bounces=3;s.cycles.transmission_bounces=4;s.cycles.volume_bounces=1;s.cycles.caustics_reflective=False;s.cycles.caustics_refractive=False;s.cycles.blur_glossy=1.0
    return s

def main():
    ap=argparse.ArgumentParser();ap.add_argument('preset');ap.add_argument('--blend',default=str(BLEND));ap.add_argument('--camera',default='CAM_Hero_LeadingBund');ap.add_argument('--out');ap.add_argument('--size',nargs=2,type=int);ap.add_argument('--samples',type=int);ap.add_argument('--no-volume',action='store_true');a=ap.parse_args()
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    s=apply_preset(a.preset,a.samples)
    if a.size:s.render.resolution_x,s.render.resolution_y=a.size
    if a.no_volume:bpy.data.collections['COL_Atmosphere'].hide_render=True
    cam=bpy.data.objects.get(a.camera)
    if cam is None:raise SystemExit('Unknown camera '+a.camera)
    s.camera=cam;s.frame_set(1)
    out=Path(a.out) if a.out else (REVIEW if ('preview' in a.preset or a.preset in ['clay','cycles_bench'] or 'bench' in a.preset) else OUTPUT)/f'{a.preset}_{a.camera}.png'
    out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix('.tmp.png');s.render.filepath=str(tmp)
    t0=time.time();bpy.ops.render.render(write_still=True);dt=time.time()-t0
    if not tmp.exists() or tmp.stat().st_size<1000:raise SystemExit('Render did not produce a valid PNG')
    tmp.replace(out)
    volume_on=(not a.no_volume) and ('COL_Atmosphere' not in bpy.data.collections or not bpy.data.collections['COL_Atmosphere'].hide_render)
    receipt={'revision':REVISION,'preset':a.preset,'scene_sha256':sha(a.blend),'blender':bpy.app.version_string,'engine':s.render.engine,'camera':a.camera,'resolution':[s.render.resolution_x,s.render.resolution_y],'samples':getattr(s.cycles,'samples',None) if s.render.engine=='CYCLES' else getattr(s.eevee,'taa_render_samples',None),'seconds':round(dt,3),'image_sha256':sha(out),'image':str(out),'volume':volume_on,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    out.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2));print('RECEIPT '+json.dumps(receipt))
if __name__=='__main__':main()
