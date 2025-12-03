"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
mapping_operators.py

Operators used to manage OSC mappings from the UI:

- Right-click context operator to create a mapping from any property
- Helpers to detect special cases (Geometry Nodes, node editors, etc.)
- Operators to add / duplicate / remove / fold generic mappings
- Operators to add / duplicate / remove / fold shape key mappings
- Bulk operator to create a full set of standard facial shape key mappings
"""

import bpy
import re


# ------------------------------------------------------------------------------------------------------
# Create mapping from right-clicked property
# ------------------------------------------------------------------------------------------------------

class OSC_OT_CreateMappingFromProperty(bpy.types.Operator):
    """
    Operator called from a property context menu (right-click).

    It inspects the UI context (button_pointer / button_prop), builds
    a full Python data_path (e.g. bpy.data.objects['Cube'].location[0]),
    and creates a new Generic OSC mapping in the Scene with a suggested
    OSC address.
    """

    bl_idname = "osc_mapping.create_from_property"
    bl_label = "Create OSC Mapping"
    bl_description = "Create an OSC mapping for this property"
    
    @classmethod
    def poll(cls, context):
        """
        Only enable this operator when Blender provides button_pointer
        and button_prop in the context (i.e. when right-clicking a UI property).
        """
        return hasattr(context, 'button_pointer') and hasattr(context, 'button_prop')
    
    def execute(self, context):
        # These attributes are provided by Blender for the clicked property
        button_pointer = getattr(context, 'button_pointer', None)
        button_prop = getattr(context, 'button_prop', None)
        
        if not button_pointer or not button_prop:
            self.report({'ERROR'}, "Unable to retrieve property information")
            return {'CANCELLED'}
        
        try:
            # Special case: Geometry Nodes modifier sockets
            if self.is_geometry_nodes_modifier(button_pointer):
                full_path, osc_address = self.handle_geometry_nodes_modifier(button_pointer, button_prop)
            else:
                # Generic case: use Blender's RNA path_from_id
                data_path = button_pointer.path_from_id(button_prop.identifier)
                if not data_path:
                    self.report({'ERROR'}, "Unable to obtain the datapath")
                    return {'CANCELLED'}
                
                # Build the full Python path (bpy.data.* or bpy.context.*)
                full_path = self.build_full_path(button_pointer, data_path)

                # Derive a readable OSC address from the path and property name
                osc_address = self.generate_osc_address(full_path, button_prop.identifier)
            
            # Create a new generic mapping entry on the Scene
            scn = context.scene
            item = scn.osc_generic_mappings.add()
            item.address = osc_address
            item.data_path = full_path
            item.fold = False
            
            # Initialize default in/out ranges based on the property metadata
            self.set_default_ranges(item, button_prop)
            
            self.report({'INFO'}, f"Mapping OSC created: {osc_address} -> {full_path}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}
    

    # --------------------------------------------------------------------------------------------------
    # Helper methods for datapath and OSC address generation
    # --------------------------------------------------------------------------------------------------

    def is_geometry_nodes_modifier(self, obj):
        """
        Detect whether the UI pointer refers to a Geometry Nodes modifier.

        Blender exposes different types for Geometry Nodes modifiers depending
        on context, so several checks are used (type name, bl_rna identifier,
        presence of node_group / type == 'NODES').
        """
        type_str = str(type(obj))
        if 'NodesModifier' in type_str:
            return True
        
        if hasattr(obj, 'bl_rna') and hasattr(obj.bl_rna, 'identifier'):
            return 'NodesModifier' in obj.bl_rna.identifier
        
        return (
            hasattr(obj, 'node_group') 
            and hasattr(obj, 'type') 
            and getattr(obj, 'type', '') == 'NODES'
        )

    def handle_geometry_nodes_modifier(self, modifier, button_prop):
        """
        Build a data_path and OSC address specifically for Geometry Nodes
        modifier sockets.

        Returns:
            (full_path, osc_address)
        """
        try:
            obj_id = modifier.id_data if hasattr(modifier, 'id_data') else None
            if not obj_id or not hasattr(obj_id, 'name'):
                raise ValueError("Parent object could not be found")
            
            object_name = obj_id.name
            modifier_name = modifier.name if hasattr(modifier, 'name') else 'GeometryNodes'
            socket_identifier = button_prop.identifier
            
            # Example full_path:
            # bpy.data.objects['Cube'].modifiers['GeometryNodes']["Socket_001"]
            full_path = f"bpy.data.objects['{object_name}'].modifiers['{modifier_name}']['{socket_identifier}']"
            
            # Try to create a cleaner OSC address from the socket name
            clean_socket = socket_identifier.replace('Socket_', '').replace('_', '')
            if not clean_socket:
                clean_socket = f"socket{socket_identifier[-1]}" if socket_identifier[-1].isdigit() else "param"
            
            osc_address = f"/{object_name}/{clean_socket}"
            return full_path, osc_address
            
        except Exception as e:
            raise ValueError(f"Error processing the modify Geometry Nodes: {e}")

    def build_full_path(self, obj, data_path):
        """
        Construct the complete Python data_path with the appropriate prefix.

        Depending on what the pointer refers to (node in a node editor,
        object property, datablock, etc.), this returns something like:

        - bpy.data.node_groups['Group'].nodes["Node"].inputs[0].default_value
        - bpy.data.materials['Mat'].node_tree.nodes["Node"].inputs[0].default_value
        - bpy.data.objects['Cube'].location[0]
        - bpy.context.object.location[0] (fallback)
        """
        obj_id = obj.id_data if hasattr(obj, 'id_data') else obj
        
        # --------------------------------------------------------------
        # Special case: nodes / sockets in a node editor
        # --------------------------------------------------------------
        if hasattr(obj, 'bl_rna') and any(x in str(obj.bl_rna.identifier) for x in ['Node', 'Socket']):
            if hasattr(obj, 'id_data') and hasattr(obj.id_data, 'bl_rna'):
                node_group_name = obj.id_data.name

                # Geometry Node tree in bpy.data.node_groups
                if 'GeometryNodeTree' in str(obj.id_data.bl_rna.identifier):
                    return f"bpy.data.node_groups['{node_group_name}'].{data_path}"
                
                # Shader Node tree: assume it belongs to a material
                elif 'ShaderNodeTree' in str(obj.id_data.bl_rna.identifier):
                    return f"bpy.data.materials['{node_group_name}'].node_tree.{data_path}"
                
                # Fallback: generic node group
                else:
                    return f"bpy.data.node_groups['{node_group_name}'].{data_path}"
        
        # --------------------------------------------------------------
        # Other datablock types (objects, meshes, materials, etc.)
        # --------------------------------------------------------------
        if hasattr(obj_id, 'name'):
            obj_name = obj_id.name

            # If this datablock is used in a scene, we can reference it as an object
            if hasattr(obj_id, 'users_scene') and obj_id.users_scene:
                return f"bpy.data.objects['{obj_name}'].{data_path}"
            
            # Datablocks with a 'type' attribute (MESH, MATERIAL, etc.)
            elif hasattr(obj_id, 'type'):
                type_map = {
                    'MESH': 'meshes',
                    'MATERIAL': 'materials',
                    'TEXTURE': 'textures',
                    'IMAGE': 'images',
                    'ARMATURE': 'armatures'
                }
                collection = type_map.get(obj_id.type, 'objects')
                return f"bpy.data.{collection}['{obj_name}'].{data_path}"

        # Fallback: rely on the active context object
        return f"bpy.context.object.{data_path}"
    
    def generate_osc_address(self, data_path, prop_name):
        """
        Generate a simple OSC address from the data_path and property name.

        Example:
            data_path: bpy.data.objects['Cube'].location[0]
            prop_name: 'location'
            result:    "/Cube/location"
        """
        # First quoted name (e.g. object name) becomes the OSC "target"
        obj_match = re.search(r"[\'\"]([^\'\"]+)[\'\"]", data_path)
        obj_name = obj_match.group(1) if obj_match else "object"

        # Clean the property identifier for a compact OSC path
        clean_prop = prop_name.replace('_', '').replace(' ', '')

        return f"/{obj_name}/{clean_prop}"
    
    def set_default_ranges(self, item, prop):
        """
        Initialize min_out / max_out for a new mapping item based on
        the Blender property's metadata.

        - If soft_min/soft_max exist, use them (typical for floats).
        - If the property is a boolean, map [0, 1] to off/on.
        """
        if hasattr(prop, 'soft_min') and hasattr(prop, 'soft_max'):
            item.min_out = prop.soft_min
            item.max_out = prop.soft_max

        elif hasattr(prop, 'default'):
            # Simple convention for boolean toggles
            if isinstance(prop.default, bool):
                item.min_out = 0.0
                item.max_out = 1.0


# ------------------------------------------------------------------------
# Generic mappings operators (data_path-based)
# ------------------------------------------------------------------------

class OSC_OT_AddGenericMapping(bpy.types.Operator):
    """
    Operator to create an empty generic mapping row.

    This is used from the UI to quickly add a new mapping and then edit
    address and data_path manually.
    """

    bl_idname = "osc_mapping.add_generic"
    bl_label = "Add Generic Mapping"
    
    def execute(self, context):
        item = context.scene.osc_generic_mappings.add()
        item.address = "/param"
        item.data_path = "bpy.context.object.location[0]"
        item.fold = False
        return {'FINISHED'}


class OSC_OT_DuplicateGenericMapping(bpy.types.Operator):
    """
    Duplicate an existing generic mapping entry by index.

    All properties are copied field by field using the PropertyGroup
    annotations, except that the new entry is unfolded by default.
    """

    bl_idname = "osc_mapping.duplicate_generic"
    bl_label = "Duplicate Generic Mapping"

    index: bpy.props.IntProperty(default=-1)
    
    def execute(self, context):
        scn = context.scene
        src_idx = self.index

        if 0 <= src_idx < len(scn.osc_generic_mappings):
            src = scn.osc_generic_mappings[src_idx]
            dst = scn.osc_generic_mappings.add()

            # Copy every annotated property from source to destination            
            for attr in src.__annotations__.keys():
                setattr(dst, attr, getattr(src, attr))
            
            # Ensure the duplicated mapping is visible (unfolded)
            dst.fold = False

        return {'FINISHED'}


class OSC_OT_RemoveGenericMapping(bpy.types.Operator):
    """
    Remove a generic mapping entry by index.
    """

    bl_idname = "osc_mapping.remove_generic"
    bl_label = "Remove Generic Mapping"

    index: bpy.props.IntProperty(default=-1)
    
    def execute(self, context):
        scn = context.scene
        idx = self.index

        if 0 <= idx < len(scn.osc_generic_mappings):
            scn.osc_generic_mappings.remove(idx)

        return {'FINISHED'}


class OSC_OT_ToggleGenericFold(bpy.types.Operator):
    """
    Toggle the 'fold' (collapsed/expanded) state of a generic mapping row.
    """

    bl_idname = "osc_mapping.toggle_generic_fold"
    bl_label = "Toggle Generic Fold"

    index: bpy.props.IntProperty(default=-1)
    
    def execute(self, context):
        scn = context.scene
        i = self.index

        if 0 <= i < len(scn.osc_generic_mappings):
            scn.osc_generic_mappings[i].fold = not scn.osc_generic_mappings[i].fold

        return {'FINISHED'}


# ------------------------------------------------------------------------
# Shape key mappings operators (character facial set, etc.)
# ------------------------------------------------------------------------

class OSC_OT_AddBulkMappings(bpy.types.Operator):
    """
    Create a full set of standard face shape key mappings in one click.

    The list is based on common ARKit/MetaHuman style facial blendshape
    names and targets a user-specified mesh (mesh_name).
    """

    bl_idname = "osc_mapping.add_bulk"
    bl_label = "Add 50 Face Shape Key Mappings"
    bl_description = "Adds all standard face shape key mappings"
    
    mesh_name: bpy.props.StringProperty(
        name="Mesh Name",
        default="HG_Body",
        description="Exact name of the target mesh (see Outliner)"
    )

    def execute(self, context):
        # List of standard face shape key names
        shape_keys = [
            "eyeLookUpLeft", "eyeLookUpRight", "eyeLookDownLeft", "eyeLookDownRight",
            "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
            "eyeBlinkLeft", "eyeBlinkRight", "eyeSquintLeft", "eyeSquintRight",
            "eyeWideLeft", "eyeWideRight", "jawForward", "jawLeft", "jawRight", "jawOpen",
            "mouthClose", "mouthFunnel", "mouthPucker", "mouthLeft", "mouthRight",
            "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight",
            "mouthDimpleLeft", "mouthDimpleRight", "mouthStretchLeft", "mouthStretchRight",
            "mouthRollLower", "mouthRollUpper", "mouthShrugUpper", "mouthShrugLower",
            "mouthPressLeft", "mouthPressRight", "mouthLowerDownLeft", "mouthLowerDownRight",
            "mouthUpperUpLeft", "mouthUpperUpRight", "browDownLeft", "browDownRight",
            "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "cheekPuff",
            "cheekSquintLeft", "cheekSquintRight", "noseSneerLeft", "noseSneerRight"
        ]

        scn = context.scene

        for sk in shape_keys:
            item = scn.osc_mappings.add()
            item.address = "/" + sk
            item.object_name = self.mesh_name
            item.shapekey_name = sk
            item.fold = False

        self.report({'INFO'}, "Mappings shape keys added.")
        return {'FINISHED'}


class OSC_OT_AddMapping(bpy.types.Operator):
    """
    Add a new empty shape key / bone mapping row.

    The user can then configure address, object_name, shapekey_name, etc.
    in the UI.
    """

    bl_idname = "osc_mapping.add"
    bl_label = "Add Mapping"

    def execute(self, context):
        item = context.scene.osc_mappings.add()
        item.address = "/param"
        item.fold = False
        return {'FINISHED'}

class OSC_OT_DuplicateMapping(bpy.types.Operator):
    """
    Duplicate an existing OSCMapping entry (shape key / bone mapping).

    All fields defined in the PropertyGroup annotations are copied.
    The duplicated entry is unfolded for easier editing.
    """

    bl_idname = "osc_mapping.duplicate"
    bl_label = "Duplicate Mapping"

    index: bpy.props.IntProperty(default=-1)
    
    def execute(self, context):
        scn = context.scene
        src_idx = self.index

        if 0 <= src_idx < len(scn.osc_mappings):
            src = scn.osc_mappings[src_idx]
            dst = scn.osc_mappings.add()

            # Copy field by field using annotations as the source of truth
            for attr in src.__annotations__.keys():
                setattr(dst, attr, getattr(src, attr))

            # Make the duplicated mapping unfolded for editing
            dst.fold = False

        return {'FINISHED'}


class OSC_OT_RemoveMapping(bpy.types.Operator):
    """
    Remove a shape key / bone mapping row by index.
    """

    bl_idname = "osc_mapping.remove"
    bl_label = "Remove Mapping"

    index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        scn = context.scene
        idx = self.index

        if 0 <= idx < len(scn.osc_mappings):
            scn.osc_mappings.remove(idx)

        return {'FINISHED'}

class OSC_OT_ToggleFold(bpy.types.Operator):
    """
    Toggle the 'fold' (collapsed/expanded) state of a shape key / bone mapping row.
    """

    bl_idname = "osc_mapping.toggle_fold"
    bl_label = "Toggle Fold"

    index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        scn = context.scene
        i = self.index

        if 0 <= i < len(scn.osc_mappings):
            scn.osc_mappings[i].fold = not scn.osc_mappings[i].fold

        return {'FINISHED'}


# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------

classes = (
    OSC_OT_CreateMappingFromProperty,
    OSC_OT_AddGenericMapping,
    OSC_OT_DuplicateGenericMapping,
    OSC_OT_RemoveGenericMapping,
    OSC_OT_ToggleGenericFold,
    OSC_OT_AddBulkMappings,
    OSC_OT_AddMapping,
    OSC_OT_DuplicateMapping,
    OSC_OT_RemoveMapping,
    OSC_OT_ToggleFold,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            # In case some classes were not registered for any reason
            pass
