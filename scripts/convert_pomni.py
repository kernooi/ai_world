"""Convert MengGe_KKD's licensed source to the bundled browser model.

Run with Blender 4.5, --background --disable-autoexec SOURCE.blend --python
scripts/convert_pomni.py -- OUTPUT.glb. Source scripts are never executed.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion

output = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
output.parent.mkdir(parents=True, exist_ok=True)
rig = bpy.data.objects['DEV_Armature']
bpy.context.view_layer.objects.active = rig
rig.hide_set(False)
rig.animation_data_clear()
for bone in rig.pose.bones:
    for constraint in list(bone.constraints):
        bone.constraints.remove(constraint)
    bone.rotation_mode = 'QUATERNION'
    bone.matrix_basis.identity()

# Export only visible character geometry, excluding camera and rig widgets.
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig and not o.hide_render]
for obj in bpy.context.view_layer.objects:
    obj.select_set(False)
for obj in meshes:
    obj.hide_set(False)
    obj.select_set(True)
    if obj.data.shape_keys:
        obj.data.shape_keys.animation_data_clear()
        for key in obj.data.shape_keys.key_blocks:
            key.value = 0
    for mod in obj.modifiers:
        if mod.type == 'SUBSURF':
            mod.levels = mod.render_levels = 0
        if mod.type == 'UV_WARP':
            mod.show_viewport = mod.show_render = False
rig.select_set(True)

# The eye alternatives are Blender shader mixes. Select the creator's default
# pinwheel texture and express it as standard glTF PBR.
for material in {slot.material for obj in meshes for slot in obj.material_slots if slot.material}:
    nodes = material.node_tree.nodes
    output_node = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
    principled = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    material.node_tree.links.new(principled.outputs['BSDF'], output_node.inputs['Surface'])
    principled.inputs['Roughness'].default_value = .34 if material.name == 'Eyes' else .62
    if material.name == 'Eyes':
        image = next(n for n in nodes if n.type == 'TEX_IMAGE' and n.image.name == 'Eyes_1')
        material.node_tree.links.new(image.outputs['Color'], principled.inputs['Base Color'])
    # These three source images are absent from the creator's packed blend.
    if material.name in {'Eyelid', 'Eyelash', 'Eyebrow'}:
        for link in list(principled.inputs['Base Color'].links):
            material.node_tree.links.remove(link)
        principled.inputs['Base Color'].default_value = (0.93, .88, .79, 1) if material.name == 'Eyelid' else (.018, .009, .026, 1)

def rotation(name, axis, angle):
    bone = rig.pose.bones[name]
    bone.rotation_quaternion = Quaternion(axis, angle)

# Skin deformation bones use local axes inherited from the creator's rig.
# Lower the T-pose arms and author small, in-place cycles with bent knees.
animated = ['Arm.L', 'Arm.R', 'Elbow.L', 'Elbow.R', 'Leg.L', 'Leg.R',
            'Knee.L', 'Knee.R', 'Head', 'Spine_2', 'Hat_2.L', 'Hat_2.R']
for name in ['Idle', 'Walk', 'Talk', 'Reach']:
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    for frame in range(1, 50, 2):
        phase = (frame - 1) / 48 * math.tau
        walk = 1 if name == 'Walk' else 0
        for side, sign in [('L', 1), ('R', -1)]:
            swing = math.sin(phase) * sign
            rotation('Arm.' + side, (0, 0, 1), -sign * 1.30)
            arm = rig.pose.bones['Arm.' + side]
            arm.rotation_quaternion @= Quaternion((1, 0, 0), swing * .30 * walk)
            if side == 'R' and name in {'Talk', 'Reach'}:
                arm.rotation_quaternion @= Quaternion((1, 0, 0), -.65 if name == 'Reach' else -.35 + math.sin(phase) * .12)
            rotation('Elbow.' + side, (1, 0, 0), .14 + (.3 if name in {'Talk', 'Reach'} and side == 'R' else 0))
            rotation('Leg.' + side, (0, 0, 1), swing * .32 * walk)
            rotation('Knee.' + side, (0, 0, 1), -max(0, -swing) * .43 * walk)
            rotation('Hat_2.' + side, (1, 0, 0), math.sin(phase + sign * .6) * (.045 if walk else .012))
        rotation('Head', (0, 0, 1), math.sin(phase) * (.04 if name == 'Talk' else .018))
        rotation('Spine_2', (1, 0, 0), math.sin(phase) * .015)
        for bone_name in animated:
            rig.pose.bones[bone_name].keyframe_insert('rotation_quaternion', frame=frame, group=bone_name)
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
rig.animation_data.action = bpy.data.actions['Idle']
bpy.context.scene.render.fps = 30
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 49
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()

bpy.ops.export_scene.gltf(
    filepath=str(output), export_format='GLB', use_selection=True,
    export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
    export_def_bones=True, export_morph=True, export_morph_normal=False,
    export_skins=True, export_cameras=False, export_lights=False,
    export_extras=False, export_yup=True,
)
print('EXPORTED', output, output.stat().st_size)
