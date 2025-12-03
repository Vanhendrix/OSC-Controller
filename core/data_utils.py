"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
core/data_utils.py

Low-level helpers for applying changes to Blender data:

- Shape key lookup and value application
- Bone rotation application (Euler or Quaternion)
- Optional auto-keying when osc_autokey is enabled on the Scene
"""

import bpy


# ------------------------------------------------------------------------------------------------------
# Shape key utilities
# ------------------------------------------------------------------------------------------------------

def get_shapekey_block(obj_name: str, sk_name: str):
    """
    Retrieve the object, its shape key datablock and the specific shape key.

    Args:
        obj_name: Name of the mesh object that owns the shape key.
        sk_name: Name of the shape key to retrieve.

    Returns:
        A tuple (obj, key, block) where:
            obj: The Blender object, or None if not found.
            key: The Object's shape_keys datablock, or None.
            block: The specific key_block for the requested shape key, or None.
    """
    obj = bpy.data.objects.get(obj_name)

    # Validate that the object exists and has shape keys
    if (
        not obj 
        or not obj.data 
        or not hasattr(obj.data, "shape_keys") 
        or not obj.data.shape_keys
    ):
        return None, None, None

    key = obj.data.shape_keys
    block = key.key_blocks.get(sk_name) if key else None

    return obj, key, block

def apply_shapekey_value(obj_name: str, sk_name: str, value: float) -> bool:
    """
    Set the value of a specific shape key and optionally insert a keyframe.

    Args:
        obj_name: Name of the mesh object that owns the shape key.
        sk_name: Name of the shape key to modify.
        value: New value to assign to the shape key (usually in [0, 1]).

    Returns:
        True if the operation succeeded, False otherwise.
    """
    obj, key, block = get_shapekey_block(obj_name, sk_name)

    if block is None:
        # Object or shape key not found
        return False

    # Apply the new shape key value    
    block.value = value

    # Optional auto-keying driven by the add-on (Scene property)
    if bpy.context.scene.osc_autokey:
        block.keyframe_insert(data_path="value", group="OSC")

    return True


# ------------------------------------------------------------------------------------------------------
# Bone rotation utilities
# ------------------------------------------------------------------------------------------------------

def apply_bone_rotation(
    armature_name: str, 
    bone_name: str, 
    axis: str, 
    value: float, 
    mode: str
) -> bool:
    """
    Apply a rotation value to a specific pose bone on a given axis.

    Depending on the rotation mode, this will either modify the
    rotation_quaternion or rotation_euler of the pose bone, and optionally
    insert keyframes if osc_autokey is enabled.

    Args:
        armature_name: Name of the armature object.
        bone_name: Name of the pose bone to modify.
        axis: One of 'X', 'Y', 'Z' indicating which component to set.
        value: Rotation value to apply (radians for Euler, component value for Quaternion).
        mode: Rotation mode, expected values are 'QUATERNION' or 'EULER'.

    Returns:
        True if the rotation was applied, False if the target object/bone
        could not be found or was invalid.
    """
    print(f"Applying rotation to {armature_name}.{bone_name} axis {axis} = {value} mode {mode}")

    obj = bpy.data.objects.get(armature_name)

    # Ensure we found a valid armature object with pose data
    if not obj or obj.type != 'ARMATURE' or not obj.pose:
        return False

    pb = obj.pose.bones.get(bone_name)
    if not pb:
        return False
    
    if mode == 'QUATERNION':
        # Copy the current quaternion and override a single component
        q = pb.rotation_quaternion.copy()
        idx = {'X': 1, 'Y': 2, 'Z': 3}[axis]
        q[idx] = value
        pb.rotation_quaternion = q

        if bpy.context.scene.osc_autokey:
            pb.keyframe_insert(data_path="rotation_quaternion", group="OSC")

    else:
        # Default to Euler rotation (mode 'EULER' or anything else)
        e = pb.rotation_euler.copy()
        idx = {'X': 0, 'Y': 1, 'Z': 2}[axis]
        e[idx] = value
        pb.rotation_euler = e

        if bpy.context.scene.osc_autokey:
            pb.keyframe_insert(data_path="rotation_euler", group="OSC")
            
    return True
