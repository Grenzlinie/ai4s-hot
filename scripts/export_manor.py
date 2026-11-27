"""Export the original research manor as a compact, animated, Y-up GLB.

Blender --factory-startup --background --python scripts/export_manor.py
Wave and Walk are stationary loops. Move/turn the Scholar root in the client.
"""
from pathlib import Path
import math
import runpy
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.argv.append('--export-scene')
source = runpy.run_path(str(ROOT / 'scripts' / 'render_manor.py'))
scene = bpy.context.scene
scene.render.fps = 24
scene.frame_start, scene.frame_end = 1, 49
for obj in list(scene.objects):
    if obj.type in {'CAMERA', 'LIGHT'} or obj.name == 'Infinite blue studio floor':
        bpy.data.objects.remove(obj, do_unlink=True)


def empty(name, location, parent=None):
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    obj.location = location
    if parent:
        obj.parent = parent
    return obj


def reparent(obj, parent):
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world


bpy.context.view_layer.update()
library = empty('Library', (-1.75, .85, .34))
telescope = empty('Telescope', (2.85, -1.75, .34))
scholar = empty('Scholar', (.02, -2.30, .34))
bpy.context.view_layer.update()
for obj in source['LIBRARY']:
    reparent(obj, library)
for obj in list(scene.objects):
    if obj.type == 'MESH' and ('telescope' in obj.name.lower()):
        reparent(obj, telescope)
for obj in source['CHAR']:
    reparent(obj, scholar)
# Child locations are relative to their named interactive root.
empty('LibraryHotspot', (0, -.15, 3.85), library)
empty('TelescopeHotspot', (0, 0, 2.1), telescope)
empty('ScholarHotspot', (0, 0, 3.35), scholar)

# Arm/leg transforms are below Scholar; animation never translates the root.
def limb(name, world_origin, objects):
    node = empty(name, world_origin)
    bpy.context.view_layer.update()
    reparent(node, scholar)
    for obj in objects:
        reparent(obj, node)
    return node

arms, legs = [], []
for side in [-1, 1]:
    arm_meshes = [o for o in source['CHAR'] if any(o.name.startswith(n) for n in ('Coat sleeve', 'Bent coat cuff', 'Tiny book-holding hand')) and (o.matrix_world.translation.x > .02) == (side > 0)]
    arms.append(limb('ScholarArmL' if side < 0 else 'ScholarArmR', (.02+side*.42, -2.30, 1.68), arm_meshes))
    leg_meshes = [o for o in source['CHAR'] if any(o.name.startswith(n) for n in ('Scholar trouser leg', 'Scholar rounded shoe')) and (o.matrix_world.translation.x > .02) == (side > 0)]
    legs.append(limb('ScholarLegL' if side < 0 else 'ScholarLegR', (.02+side*.22, -2.30, .91), leg_meshes))

# Bake every frame; use matching NLA track names to merge object channels per clip.
def action(node, clip, rotation):
    node.animation_data_create()
    node.animation_data.action = None
    for frame in range(1, 50):
        node.rotation_euler = rotation((frame-1)/48)
        node.keyframe_insert(data_path='rotation_euler', frame=frame, group=clip)
    animation = node.animation_data.action
    animation.name = clip + '_' + node.name
    track = node.animation_data.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, 1, animation)
    strip.action_frame_start, strip.action_frame_end = 1, 49
    node.animation_data.action = None
    track.mute = True
    node.rotation_euler = (0, 0, 0)

# Raised right arm waves next to the face; left arm keeps holding the book.
action(arms[1], 'Wave', lambda t: (-2.05, .45 + .25*math.sin(t*math.tau*3), -.10*math.sin(t*math.tau*3)))
# Quiet walking gait and smaller arm counter-swing; animation is root-motion-free.
for i, node in enumerate(legs):
    action(node, 'Walk', lambda t, i=i: (.38*math.sin(t*math.tau*2 + i*math.pi), 0, 0))
for i, node in enumerate(arms):
    action(node, 'Walk', lambda t, i=i: (-.14*math.sin(t*math.tau*2 + i*math.pi), 0, 0))

# Bake modifiers/curves, then batch static meshes sharing a material and parent.
# Interactive roots and animated limb nodes stay separate.
bpy.ops.object.select_all(action='DESELECT')
for obj in list(scene.objects):
    if obj.type in {'MESH', 'CURVE'}:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target='MESH')
        obj.select_set(False)
from collections import defaultdict
batches = defaultdict(list)
for obj in scene.objects:
    if obj.type == 'MESH':
        material = obj.data.materials[0] if obj.data.materials else None
        batches[(obj.parent, material)].append(obj)
for (parent, mat), objects in batches.items():
    if len(objects) < 2:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    objects[0].name = (parent.name if parent else 'Campus') + '_' + (mat.name if mat else 'Mesh')

# Matte clay remains readable with client hemisphere/directional lighting.
for mat in bpy.data.materials:
    shader = mat.node_tree.nodes.get('Principled BSDF') if mat.use_nodes else None
    if shader:
        shader.inputs['Roughness'].default_value = max(.5, shader.inputs['Roughness'].default_value)
        if shader.inputs['Transmission Weight'].default_value > 0:
            shader.inputs['Transmission Weight'].default_value = 0
            shader.inputs['Alpha'].default_value = .42
            if hasattr(mat, 'surface_render_method'):
                mat.surface_render_method = 'DITHERED'
scene.frame_set(1)
bpy.ops.object.select_all(action='SELECT')
target = ROOT / 'site' / 'static' / 'manor-scene.glb'
bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB',
    export_yup=True, export_cameras=False, export_lights=False,
    export_animations=True, export_animation_mode='NLA_TRACKS',
    export_force_sampling=True, export_frame_range=True,
    export_materials='EXPORT', export_extras=True)
print('MANOR_GLB', target, target.stat().st_size)
