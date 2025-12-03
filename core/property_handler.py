"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
core/property_handler.py

Single entry point for applying a numeric OSC value to a generic Blender
property given by a data_path.

The function apply_generic_value handles several special cases:

- Timeline control (frame current and play/pause)
- Shader node parameters on materials and textures
- Standalone node groups (bpy.data.node_groups)
- Generic bpy.data.* properties (objects, cameras, lights, etc.)
  with automatic keyframing support (osc_autokey).

All updates are done on Blender's main thread and can be combined with
osc_server.py, which calls this function for GenericOSCMapping entries.
"""

import bpy
import re


def apply_generic_value(data_path: str, value: float) -> bool:
    """
    Apply a numeric value to a generic Blender property described by data_path.

    The function expects data_path to be a full Python expression starting
    with 'bpy.' (e.g. 'bpy.data.objects[\"Cube\"].location[0]') and will:

    - Detect special cases (timeline, playback toggle, nodes, bpy.data.*)
    - Assign the provided value
    - Optionally insert keyframes if osc_autokey is enabled on the Scene
    - Return True on success, False on failure or unsupported data_path
    """
    try:
        print(f"Attempting to apply {value} to {data_path}")
        
        # For safety, only allow paths that explicitly start with 'bpy.'
        if not data_path.startswith('bpy.'):
            return False
        
        # ----------------------------------------------------------------------------------------------
        # Special case: timeline frame control (frame_current)
        # ----------------------------------------------------------------------------------------------
        if 'frame_current' in data_path:
            try:
                frame_value = int(round(value))

                # Avoid fighting with live playback: only set frame when stopped
                if not bpy.context.screen.is_animation_playing:
                    bpy.context.scene.frame_set(frame_value)

                return True

            except Exception as e:
                print(f"❌ Timeline error: {e}")
                return False

        # ----------------------------------------------------------------------------------------------
        # Special case: Play/Pause the timeline
        # ----------------------------------------------------------------------------------------------
        if (
            'is_animation_playing' in data_path 
            or data_path == 'bpy.context.screen.is_animation_playing'
        ):
            try:
                # Any value > 0.5 is treated as "play", otherwise "pause"
                should_play = bool(value > 0.5)
                is_playing = bpy.context.screen.is_animation_playing
                
                if should_play and not is_playing:
                    # Start playback
                    bpy.ops.screen.animation_play()
                    print(f"▶️ Timeline PLAY")

                elif not should_play and is_playing:
                    # Stop playback without restoring the initial frame
                    bpy.ops.screen.animation_cancel(restore_frame=False)
                    print(f"⏸️ Timeline PAUSE")
                
                return True

            except Exception as e:
                print(f"❌ Error play/pause: {e}")
                return False

        # ----------------------------------------------------------------------------------------------
        # Special case: shader nodes (materials / textures)
        #
        # Example: bpy.data.materials['Mat'].node_tree.nodes["MyNode"].inputs[0].default_value
        # ----------------------------------------------------------------------------------------------
        if (
            '.node_tree.nodes[' in data_path 
            and (
                'bpy.data.materials[' in data_path 
                or 'bpy.data.textures[' in data_path
            )
        ):
            try:
                # Direct assignment using the data_path expression
                exec(f"{data_path} = {value}")
                
                # Auto-keying for shader nodes if enabled
                if bpy.context.scene.osc_autokey:
                    try:
                        current_frame = bpy.context.scene.frame_current
                        
                        # Extract material or texture name
                        mat_match = re.search(
                            r"(?:materials|textures)\['([^']+)'\]", data_path
                        )
                        if mat_match:
                            obj_name = mat_match.group(1)
                            target_tree = None
                            
                            if 'materials' in data_path:
                                mat = bpy.data.materials.get(obj_name)
                                target_tree = mat.node_tree if mat else None

                            elif 'textures' in data_path:
                                tex = bpy.data.textures.get(obj_name)
                                target_tree = tex.node_tree if tex else None
                            
                            if target_tree: 
                                # Extract the node and input index
                                node_match = re.search(
                                    r'nodes\[(?:\"([^\"]+)\"|\'([^\']+)\')\]\.inputs\[(\d+)\]\.default_value', 
                                    data_path
                                )
                                if node_match:
                                    node_name = node_match.group(1) or node_match.group(2) 
                                    input_index = int(node_match.group(3))
                                    
                                    node = target_tree.nodes.get(node_name)
                                    if node and input_index < len(node.inputs):
                                        socket = node.inputs[input_index]
                                        
                                        # Ensure animation_data and an Action exist
                                        if target_tree.animation_data is None:  
                                            target_tree.animation_data_create()

                                        if target_tree.animation_data.action is None:  
                                            action_name = f"{obj_name}_ShaderAction"
                                            target_tree.animation_data.action = bpy.data.actions.new(name=action_name)
                                        
                                        # Insert keyframe on the socket
                                        socket.keyframe_insert(
                                            data_path="default_value", 
                                            frame=current_frame, 
                                            group="OSC"
                                        )
                                        print(
                                            f"🔴 Keyframe inserted: "
                                            f"{node_name}.inputs[{input_index}] at frame {current_frame}"
                                        )
                    
                    except Exception as ke:
                        print(f"⚠️ Autokey shader node failed: {ke}")
                
                print(f"✅ Shader node update: {data_path} = {value}")
                return True
            
            except Exception as e:
                print(f"❌ Shader node error: {e}")
                return False

        # ----------------------------------------------------------------------------------------------
        # Special case: standalone node_groups (bpy.data.node_groups)
        #
        # Example: bpy.data.node_groups['Group'].nodes["Node"].inputs[0].default_value
        # ----------------------------------------------------------------------------------------------
        if (
            'bpy.data.node_groups[' in data_path 
            and '.nodes[' in data_path 
            and '.inputs[' in data_path
        ):
            try:
                # Direct assignment on the node group input
                exec(f"{data_path} = {value}")
                
                # Auto-keying for node group sockets
                if bpy.context.scene.osc_autokey:
                    try:
                        current_frame = bpy.context.scene.frame_current
                        
                        # Extract the node_group name
                        ng_match = re.search(
                            r"node_groups\['([^']+)'\]", data_path
                        )
                        if ng_match:
                            ng_name = ng_match.group(1)
                            node_group = bpy.data.node_groups.get(ng_name)
                            
                            if node_group:
                                # Extract node name and input index
                                node_match = re.search(
                                    r'nodes\[(?:\"([^\"]+)\"|\'([^\']+)\')\]\.inputs\[(\d+)\]\.default_value', 
                                    data_path
                                )
                                if node_match:
                                    node_name = node_match.group(1) or node_match.group(2)
                                    input_index = int(node_match.group(3))
                                    
                                    node = node_group.nodes.get(node_name)
                                    if node and input_index < len(node.inputs):
                                        socket = node.inputs[input_index]
                                        
                                        # Ensure animation_data and an Action exist
                                        if node_group.animation_data is None:
                                            node_group.animation_data_create()

                                        if node_group.animation_data.action is None:
                                            action_name = f"{ng_name}_NodesAction"
                                            node_group.animation_data.action = bpy.data.actions.new(name=action_name)
                                        
                                        # Insert keyframe on the socket
                                        socket.keyframe_insert(
                                            data_path="default_value", 
                                            frame=current_frame, 
                                            group="OSC"
                                        )
                                        print(
                                            f"🔴 Keyframe inserted: "
                                            f"{ng_name}.{node_name}.inputs[{input_index}] "
                                            f"at frame {current_frame}")
                    
                    except Exception as ke:
                        print(f"⚠️ Autokey node_group failed: {ke}")
                
                print(f"✅ Node group node update: {data_path} = {value}")
                return True
            
            except Exception as e:
                print(f"❌ Error node_group node: {e}")
                return False

        # ----------------------------------------------------------------------------------------------
        # Special case: generic bpy.data.* properties
        #
        # Handles objects, cameras, lights, etc. and supports autokeying
        #
        #   bpy.data.objects['Cube'].location[0]
        #   bpy.data.objects['Camera'].data.lens
        #   bpy.data.cameras['Camera'].lens
        # ----------------------------------------------------------------------------------------------
        if 'bpy.data.' in data_path:
            try:
                # Direct assignment on any bpy.data.* path
                exec(f"{data_path} = {value}")
                
                if bpy.context.scene.osc_autokey:
                    try:
                        # Extract the object/datablock name between ['...']
                        if '[' in data_path:
                            obj_name = data_path.split("['")[1].split("']")[0]
                            
                            target_obj = None
                            relative_path = None
                            
                            # Case: bpy.data.objects['Name'].something
                            if 'objects' in data_path:
                                target_obj = bpy.data.objects.get(obj_name)
                                
                                # Path after "objects['Name']."
                                full_remaining = data_path.split(f"objects['{obj_name}'].")[1]
                                
                                # Special handling for ".data.<prop>"
                                if full_remaining.startswith('data.'):
                                    # For cameras and lights, keyframe the datablock
                                    if target_obj and target_obj.type == 'CAMERA':
                                        target_obj = target_obj.data
                                        relative_path = full_remaining.replace('data.', '')

                                    elif target_obj and target_obj.type == 'LIGHT':
                                        target_obj = target_obj.data
                                        relative_path = full_remaining.replace('data.', '')

                                    else:
                                         # Other objects: keep .data in the path
                                        relative_path = full_remaining
                                else:
                                    # Normal case without ".data"
                                    relative_path = full_remaining

                            # Case: bpy.data.cameras['Name'].something
                            elif 'cameras' in data_path:
                                cam_data = bpy.data.cameras.get(obj_name)
                                if cam_data:
                                    target_obj = cam_data
                                    relative_path = data_path.split(f"cameras['{obj_name}'].")[1]
                            
                            # Insert keyframe on the resolved target_obj and path
                            if target_obj and relative_path:
                                current_frame = bpy.context.scene.frame_current
                                
                                # Ensure animation_data and an Action exist
                                if target_obj.animation_data is None:
                                    target_obj.animation_data_create()

                                if target_obj.animation_data.action is None:
                                    # Use a more descriptive Action name depending on type
                                    if isinstance(target_obj, bpy.types.Camera):
                                        action_name = f"{target_obj.name}_CameraAction"
                                    elif isinstance(target_obj, bpy.types.Light):
                                        action_name = f"{target_obj.name}_LightAction"
                                    else:
                                        action_name = f"{target_obj.name}_OSCAction"
                                    target_obj.animation_data.action = bpy.data.actions.new(name=action_name)

                                # Detect array-like paths (e.g. location[0])
                                index_match = re.match(
                                    r'(.+)\[(\d+)\]$', 
                                    relative_path
                                )

                                if index_match:
                                    # Path with index: location[0], rotation_euler[2], etc.
                                    base_path = index_match.group(1)
                                    index = int(index_match.group(2))

                                    target_obj.keyframe_insert(
                                        data_path=base_path, 
                                        index=index, 
                                        frame=current_frame, 
                                        group="OSC"
                                    )
                                    print(
                                        f"🔴 Keyframe insert: {base_path}[{index}] "
                                        f"at frame {current_frame}"
                                    )
                                else:
                                     # Simple property path without index: lens, hide_viewport, etc.
                                    target_obj.keyframe_insert(
                                        data_path=relative_path, 
                                        frame=current_frame, 
                                        group="OSC"
                                    )
                                    print(
                                        f"🔴 Keyframe insert: {relative_path} "
                                        f"at frame {current_frame}"
                                    )
                                
                    except Exception as ke:
                        print(f"⚠️ Autokey bpy.data failed: {ke}")
                
                # Tag objects/datablocks as updated so the depsgraph knows to refresh
                if '[' in data_path:
                    obj_name = data_path.split("['")[1].split("']")[0]

                    # If we modified bpy.data.objects['Name'], update that object
                    if 'objects' in data_path:
                        obj = bpy.data.objects.get(obj_name)
                        if obj:
                            obj.update_tag()

                    # If we modified bpy.data.cameras['Name'], update any scene object
                    # that uses this camera datablock        
                    elif 'cameras' in data_path:
                        cam_data = bpy.data.cameras.get(obj_name)
                        for obj in bpy.context.scene.objects:
                            if obj.type == 'CAMERA' and obj.data == cam_data:
                                obj.update_tag()
                
                print(f"✅ bpy.data updated: {data_path} = {value}")
                return True
            
            except Exception as e:
                print(f"❌ Error bpy.data: {e}")
                return False    

        # Special case for Geometry Nodes modifiers
        if '.modifiers[' in data_path and '][' in data_path:
            try:
                parts = data_path.split('].modifiers[')
                obj_part = parts[0] + ']'
                modifier_part = parts[1]
                
                modifier_name = modifier_part.split("']['")[0].strip("'\"")
                socket_name = modifier_part.split("']['")[1].rstrip("']").strip("'\"")
                
                obj = eval(obj_part)
                modifier = obj.modifiers.get(modifier_name)
                
                if modifier:
                    try:
                        current_value = modifier[socket_name]
                        
                        # Proper type conversion
                        if isinstance(current_value, bool):
                            new_value = bool(value > 0.5)
                        elif isinstance(current_value, int):
                            new_value = int(round(value))
                        else:
                            new_value = float(value)
                        
                        # Apply value
                        modifier[socket_name] = new_value
                        
                        # Auto-keying for modifiers
                        if bpy.context.scene.osc_autokey:
                            current_frame = bpy.context.scene.frame_current
                            
                            # Ensure that the animation_data exists
                            if obj.animation_data is None:
                                obj.animation_data_create()
                            if obj.animation_data.action is None:
                                action_name = f"{obj.name}_OSCAction"
                                obj.animation_data.action = bpy.data.actions.new(name=action_name)
                            
                            # Insert keyframe on the modifier
                            modifier.keyframe_insert(data_path=f'["{socket_name}"]', frame=current_frame, group="OSC")
                            print(f"✅ Keyframe added on the modifier {modifier_name}[{socket_name}] at frame {current_frame}")
                        
                        return True
                        
                    except KeyError:
                        print(f"Socket '{socket_name}' not found in the modifier")
                        return False
                else:
                    print(f"Modifier '{modifier_name}' not found")
                    return False
                    
            except Exception as e:
                print(f"Geometry Nodes Modifier Error: {e}")
                return False
        
        # Special case for Geometry Nodes in the editor
        elif '.node_groups[' in data_path and '.nodes[' in data_path:
            try:
                print(f"🔧 Geometry Node detected in editor: {data_path}")
                
                parts = data_path.split('.')
                prop_name = parts[-1]
                parent_path = '.'.join(parts[:-1])
                parent_obj = eval(parent_path)
                
                # Change value
                if hasattr(parent_obj, prop_name):
                    current_value = getattr(parent_obj, prop_name)
                    if isinstance(current_value, bool):
                        setattr(parent_obj, prop_name, value > 0.5)
                    else:
                        setattr(parent_obj, prop_name, value)
                    
                    # Auto-keying for nodes
                    if bpy.context.scene.osc_autokey:
                        current_frame = bpy.context.scene.frame_current
                        
                        # Extract the node_group from the data_path
                        node_group_match = re.search(r"node_groups\['([^']+)'\]", data_path)
                        if node_group_match:
                            node_group_name = node_group_match.group(1)
                            node_group = bpy.data.node_groups.get(node_group_name)
                            
                            if node_group:
                                if node_group.animation_data is None:
                                    node_group.animation_data_create()
                                if node_group.animation_data.action is None:
                                    action_name = f"{node_group_name}_NodesAction"
                                    node_group.animation_data.action = bpy.data.actions.new(name=action_name)
                                
                                # Construct the relative data_path
                                relative_path = data_path.split(f"node_groups['{node_group_name}'].")[1]
                                
                                # Insert keyframe
                                node_group.keyframe_insert(data_path=relative_path, frame=current_frame, group="OSC")
                                print(f"✅ Keyframe added on the node_group '{node_group_name}' at frame {current_frame}")
                    
                    return True
                else:
                    print(f"❌ Property {prop_name} not found")
                    return False
                    
            except Exception as e:
                print(f"Geometry node error: {e}")
                return False
        
        # Standard method for classical properties
        else:
            parts = data_path.split('.')
            prop_name = parts[-1]
            obj_path = '.'.join(parts[:-1])
            
            try:
                obj = eval(obj_path)
            except Exception as e:
                print(f"Impossible to assess the path {obj_path}: {e}")
                return False
            
            try:
                # Custom properties detection
                if prop_name.startswith('["') and prop_name.endswith('"]'):
                    custom_prop_name = prop_name[2:-2]
                    obj[custom_prop_name] = value
                    
                    if bpy.context.scene.osc_autokey:
                        current_frame = bpy.context.scene.frame_current
                        
                        if obj.animation_data is None:
                            obj.animation_data_create()
                        if obj.animation_data.action is None:
                            action_name = f"{obj.name}_OSCAction"
                            obj.animation_data.action = bpy.data.actions.new(name=action_name)
                        
                        obj.keyframe_insert(data_path=prop_name, frame=current_frame, group="OSC")
                        print(f"✅ Custom property '{custom_prop_name}' keyframed at frame {current_frame}")
                    
                    return True
                
                # Handling arrays with indexes (e.g. location[0])
                array_match = re.match(r'(\w+)\[(\d+)\]', prop_name)
                if array_match:
                    base_prop = array_match.group(1)
                    index = int(array_match.group(2))
                    
                    # Modify only the specific index
                    current_array = getattr(obj, base_prop)
                    if hasattr(current_array, '__len__') and index < len(current_array):
                        current_array[index] = value
                        
                        if bpy.context.scene.osc_autokey:
                            current_frame = bpy.context.scene.frame_current
                            
                            if obj.animation_data is None:
                                obj.animation_data_create()
                            if obj.animation_data.action is None:
                                action_name = f"{obj.name}_OSCAction"
                                obj.animation_data.action = bpy.data.actions.new(name=action_name)
                            
                            # Keyframe with specific index
                            obj.keyframe_insert(data_path=base_prop, index=index, frame=current_frame, group="OSC")
                            print(f"✅ {base_prop}[{index}] keyframed at frame {current_frame}")
                        
                        return True
                
                # Simple properties
                else:
                    current_value = getattr(obj, prop_name)
                    
                    if isinstance(current_value, bool):
                        setattr(obj, prop_name, value > 0.5)
                    elif hasattr(current_value, '__len__') and not isinstance(current_value, str):
                        # Array without index - we put the same value everywhere
                        new_value = [value] * len(current_value)
                        setattr(obj, prop_name, new_value)
                    else:
                        setattr(obj, prop_name, value)
                    
                    if bpy.context.scene.osc_autokey:
                        current_frame = bpy.context.scene.frame_current
                        
                        if obj.animation_data is None:
                            obj.animation_data_create()
                        if obj.animation_data.action is None:
                            action_name = f"{obj.name}_OSCAction"
                            obj.animation_data.action = bpy.data.actions.new(name=action_name)
                        
                        # Keyframe across the entire property
                        obj.keyframe_insert(data_path=prop_name, frame=current_frame, group="OSC")
                        print(f"✅ {prop_name} keyframed at frame {current_frame}")
                
                return True
                
            except Exception as e:
                print(f"Error assigning property {prop_name}: {e}")
                return False
            
    except Exception as e:
        print(f"General error when applying the value to {data_path}: {e}")
        return False
