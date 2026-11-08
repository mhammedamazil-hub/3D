import bpy,os,sys,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'review/v3/infinigen_assets_probe.blend'))
names=['banana_monocot','banana_plant']
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=2
s.render.resolution_x=512;s.render.resolution_y=512;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
s.world=bpy.data.worlds.new('ProbeWorld');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.72,.78,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.7
ld=bpy.data.lights.new('ProbeSun','SUN');ld.energy=2;ld.angle=.2;lo=bpy.data.objects.new('ProbeSun',ld);s.collection.objects.link(lo);lo.rotation_euler=(.6,-.4,-.5)
cd=bpy.data.cameras.new('ProbeCam');cd.type='ORTHO';cam=bpy.data.objects.new('ProbeCam',cd);s.collection.objects.link(cam);s.camera=cam
for name in names:
 for o in bpy.data.objects:o.hide_render=o.name!=name
 o=bpy.data.objects[name];dg=bpy.context.evaluated_depsgraph_get();ev=o.evaluated_get(dg);me=ev.to_mesh();vs=[ev.matrix_world@v.co for v in me.vertices];mn=Vector(tuple(min(v[i] for v in vs) for i in range(3)));mx=Vector(tuple(max(v[i] for v in vs) for i in range(3)));ev.to_mesh_clear();center=(mn+mx)/2;size=max(mx-mn)
 cam.location=center+Vector((4,-7,2.5));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=size*1.35
 s.render.filepath=str(ROOT/f'review/v3/preview_{name}.png');bpy.ops.render.render(write_still=True)
sys.stdout.flush();os._exit(0)
