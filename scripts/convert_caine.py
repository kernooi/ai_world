"""Convert zayJax/Coda's Caine Update 5 to a self-contained animated GLB.

Blender 4.5: --background --disable-autoexec SOURCE.blend --python
scripts/convert_caine.py -- OUTPUT.glb. The source's embedded scripts never run.
"""
import math
import sys
from pathlib import Path
import bpy
from mathutils import Quaternion

output = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
rig = bpy.data.objects['CAINE_rig']
rig.hide_set(False)
if rig.animation_data:
    rig.animation_data.action = None
    for track in list(rig.animation_data.nla_tracks):
        rig.animation_data.nla_tracks.remove(track)
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)
for bone in rig.pose.bones:
    bone.rotation_mode = 'QUATERNION'
    bone.matrix_basis.identity()
    # These obsolete action constraints reference deleted expression presets.
    for constraint in list(bone.constraints):
        if constraint.type == 'ACTION':
            bone.constraints.remove(constraint)
for side in ['L', 'R']:
    rig.pose.bones[f'upper_arm_parent.{side}']['IK_FK'] = 1.0
    rig.pose.bones[f'thigh_parent.{side}']['IK_FK'] = 1.0
bpy.context.view_layer.update()

meshes = [o for o in bpy.data.objects if o.type == 'MESH'
          and o.name.startswith('caine_') and o.name != 'caine_creases']
for obj in bpy.context.view_layer.objects:
    obj.select_set(False)
for obj in meshes:
    obj.hide_set(False)
    obj.animation_data_clear()
    obj.hide_render = False
    obj.hide_viewport = False
    # Preserve the artist's color painting using portable vertex colors.
    colors = obj.data.color_attributes.get('Color')
    if colors:
        obj.data.color_attributes.active_color = colors
        obj.data.color_attributes.render_color_index = list(obj.data.color_attributes).index(colors)
    mat = bpy.data.materials.new(obj.name + '_browser')
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    color_node = mat.node_tree.nodes.new('ShaderNodeVertexColor')
    color_node.layer_name = 'Color'
    mat.node_tree.links.new(color_node.outputs['Color'], shader.inputs['Base Color'])
    shader.inputs['Roughness'].default_value = .28 if any(s in obj.name for s in ['teeth', 'hat', 'pupil', 'eye', 'cane']) else .48
    shader.inputs['Metallic'].default_value = .65 if 'cane' in obj.name else 0
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.material_index = 0
    # Remove viewport-only corrections, retaining skin and authored topology.
    for modifier in list(obj.modifiers):
        if modifier.type not in {'ARMATURE', 'SUBSURF'}:
            obj.modifiers.remove(modifier)
    # Subdivide the rest mesh before skinning, preserving interpolated weights.
    bpy.context.view_layer.objects.active = obj
    for modifier in list(obj.modifiers):
        if modifier.type == 'SUBSURF':
            modifier.levels = modifier.render_levels = 2
            while obj.modifiers.find(modifier.name) > 0:
                bpy.ops.object.modifier_move_up(modifier=modifier.name)
            bpy.ops.object.modifier_apply(modifier=modifier.name)
    if obj.parent_type == 'VERTEX_3':
        world = obj.matrix_world.copy()
        obj.parent = rig
        obj.parent_type = 'BONE'
        obj.parent_bone = 'DEF-spine.003'
        obj.matrix_world = world
    if obj.name.startswith('caine_eyeball'):
        # glTF's deform-only export omits bone-parented rigid eyes. Give them
        # explicit skin weights so the actual eyeball geometry travels too.
        eye_bone = obj.parent_bone
        world = obj.matrix_world.copy()
        obj.parent_type = 'OBJECT'
        obj.parent = rig
        obj.matrix_world = world
        group = obj.vertex_groups.new(name=eye_bone)
        group.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
        rig.data.bones[eye_bone].use_deform = True
        modifier = obj.modifiers.new('Browser eye skin', 'ARMATURE')
        modifier.object = rig
    obj.select_set(True)

# Keep Rigify's constraints while authoring FK controls; glTF samples their
# evaluated deformation bones, so the browser needs neither Rigify nor Python.
animated = ['torso', 'head', 'teethTop', 'teethBot', 'hat']
animated += [f'{part}.{side}' for side in ['L','R'] for part in
             ['upper_arm_fk', 'forearm_fk', 'hand_fk', 'thigh_fk', 'shin_fk']]
def rotate(name, axis, angle):
    rig.pose.bones[name].rotation_quaternion = Quaternion(axis, angle)

for clip in ['Idle', 'Fly', 'Talk', 'CheckUp']:
    action = bpy.data.actions.new(clip)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    for frame in range(1, 50, 2):
        phase = (frame-1)/48*math.tau
        for name in animated:
            rig.pose.bones[name].matrix_basis.identity()
        for side, sign in [('L',1),('R',-1)]:
            rotate(f'upper_arm_fk.{side}', (0,0,1), -sign * (1.18 if clip != 'Fly' else .85))
            arm = rig.pose.bones[f'upper_arm_fk.{side}']
            arm.rotation_quaternion @= Quaternion((1,0,0), math.sin(phase)*.045)
            rotate(f'forearm_fk.{side}', (1,0,0), -.12)
            if clip in {'Talk','CheckUp'} and side == 'R':
                arm.rotation_quaternion @= Quaternion((1,0,0), -.45 + math.sin(phase)*.1)
                rotate(f'forearm_fk.{side}', (0,0,1), sign*.6)
            rotate(f'thigh_fk.{side}', (1,0,0), math.sin(phase+sign)*(.09 if clip=='Fly' else .015))
            rotate(f'shin_fk.{side}', (1,0,0), .12 if clip=='Fly' else .025)
        rotate('head',(0,1,0),math.sin(phase)*(.06 if clip=='CheckUp' else .025))
        rotate('hat',(0,1,0),math.sin(phase+.7)*.012)
        rotate('teethTop',(1,0,0),-.04-abs(math.sin(phase*2))*(.12 if clip=='Talk' else .025))
        rotate('teethBot',(1,0,0),abs(math.sin(phase*2))*(.08 if clip=='Talk' else .01))
        rig.pose.bones['torso'].location.z = math.sin(phase)*.004
        for name in animated:
            rig.pose.bones[name].keyframe_insert('rotation_quaternion',frame=frame,group=name)
            rig.pose.bones[name].keyframe_insert('location',frame=frame,group=name)
rig.animation_data.action = bpy.data.actions['Idle']
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.context.scene.render.fps = 30
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 49
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
bpy.ops.export_scene.gltf(filepath=str(output), export_format='GLB', use_selection=True,
    export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
    export_def_bones=True, export_skins=True, export_cameras=False, export_lights=False,
    export_yup=True)
print('EXPORTED', output, output.stat().st_size)
