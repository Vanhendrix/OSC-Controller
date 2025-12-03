"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
scene_props.py

Defines all custom properties stored on the Scene:

- Two PropertyGroup types used for OSC mappings:
  * GenericOSCMappingItem: generic data-path mappings
  * OSCMappingItem: shape key / bone mappings
- Scene-level settings for the OSC server (IP, port, autokey)
- Collection properties that hold all mappings in the current Scene
"""

import bpy


# ------------------------------------------------------------------------
# Property groups for OSC mappings
# ------------------------------------------------------------------------

class GenericOSCMappingItem(bpy.types.PropertyGroup):
    """
    PropertyGroup representing a generic OSC mapping that targets
    any Blender property via a RNA data_path.

    These entries are stored in Scene.osc_generic_mappings and are
    typically created either manually in the UI or via the
    "Create Mapping From Property" operator.
    """

    # OSC address, e.g. "/Camera/FocalLength"
    address: bpy.props.StringProperty(name="Address", default="/param")

    # Full Python/RNA path to the target property
    # e.g. "bpy.data.objects['Cube'].location[0]"
    data_path: bpy.props.StringProperty(name="Data Path")

    # Input range expected from the OSC source
    min_in: bpy.props.FloatProperty(name="Min In", default=0.0)
    max_in: bpy.props.FloatProperty(name="Max In", default=1.0)

    # Output range to apply on the Blender property
    min_out: bpy.props.FloatProperty(name="Min Out", default=0.0)
    max_out: bpy.props.FloatProperty(name="Max Out", default=1.0)

    # Clamp the normalized input to [0, 1]
    clamp: bpy.props.BoolProperty(name="Clamp", default=True)

    # Invert the normalized value (1 - t)
    invert: bpy.props.BoolProperty(name="Invert", default=False)

    # UI state: whether this mapping row is folded/collapsed
    fold: bpy.props.BoolProperty(name="Fold", default=False)

class OSCMappingItem(bpy.types.PropertyGroup):
    """
    PropertyGroup representing a character-oriented OSC mapping.

    It can drive:
    - A shape key on a mesh object
    - A bone rotation on an armature (via rotation_axis / rotation_mode)

    These entries are stored in Scene.osc_mappings.
    """

    # OSC address, e.g. "/mouthSmileLeft"
    address: bpy.props.StringProperty(name="Address", default="/param")

    # Target mesh object and shape key
    object_name: bpy.props.StringProperty(name="Object")
    shapekey_name: bpy.props.StringProperty(name="Shape Key")

    # Optional armature and bone for rotation-based mappings
    armature_name: bpy.props.StringProperty(name="Armature")
    bone_name: bpy.props.StringProperty(name="Bone")
    
    # Axis used for the rotation mapping
    rotation_axis: bpy.props.EnumProperty(
        name="Axe",
        items=[('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')],
        default='X'
    )

    # Rotation mode used when applying the value to the bone
    rotation_mode: bpy.props.EnumProperty(
        name="Mode",
        items=[('EULER', 'Euler', ''), ('QUATERNION', 'Quaternion', '')],
        default='EULER'
    )
    
    # Input range expected from the OSC source
    min_in: bpy.props.FloatProperty(name="Min In", default=0.0)
    max_in: bpy.props.FloatProperty(name="Max In", default=1.0)

    # Output range for the shape key value or rotation
    min_out: bpy.props.FloatProperty(name="Min Out", default=0.0)
    max_out: bpy.props.FloatProperty(name="Max Out", default=1.0)

    # Clamp normalized input to [0, 1]
    clamp: bpy.props.BoolProperty(name="Clamp", default=True)

    # Invert normalized value (1 - t)
    invert: bpy.props.BoolProperty(name="Invert", default=False)

    # UI state: whether this mapping row is folded/collapsed
    fold: bpy.props.BoolProperty(name="Fold", default=False)


# ------------------------------------------------------------------------
# Registration helpers
# ------------------------------------------------------------------------

# Classes to register for this module
classes = (
    GenericOSCMappingItem,
    OSCMappingItem,
)

def register():
    """
    Register PropertyGroup classes and attach custom properties to Scene.

    After this function is called, each Scene will have:
        - osc_ip / osc_port: OSC server configuration
        - osc_autokey: global toggle for automatic keyframing
        - osc_mappings: collection of OSCMappingItem
        - osc_generic_mappings: collection of GenericOSCMappingItem
    """
    # Register PropertyGroup classes
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Scene properties (shared by all scenes in the file)
    scn = bpy.types.Scene

    scn.osc_ip = bpy.props.StringProperty(name="IP", default="0.0.0.0")

    scn.osc_port = bpy.props.IntProperty(name="Port", default=9000, min=1, max=65535)

    # Global toggle for automatic keyframing from OSC changes
    scn.osc_autokey = bpy.props.BoolProperty(name="Auto Key", default=False)

    # Collections that store mappings in the Scene
    scn.osc_mappings = bpy.props.CollectionProperty(type=OSCMappingItem)
    scn.osc_generic_mappings = bpy.props.CollectionProperty(type=GenericOSCMappingItem)

def unregister():
    """
    Remove custom properties from Scene and unregister classes.

    This is called from the add-on's main unregister() function.
    """
    # Remove Scene-level properties defined in register()
    scn = bpy.types.Scene
    attrs = ['osc_ip', 'osc_port', 'osc_autokey', 'osc_mappings', 'osc_generic_mappings']

    for attr in attrs:
        if hasattr(scn, attr):
            delattr(scn, attr)
    
    # Unregister PropertyGroup classes in reverse order
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            # In case some class was not registered for any reason
            pass
