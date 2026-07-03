"""
    Copyright (C) 2026  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
operators/preset_operators.py

Save/load/delete OSC mapping presets (core/presets.py does the file I/O),
clear all current-scene mappings, and generate a ready-made set of Camera
position/rotation generic mappings (its output is just normal
GenericOSCMappingItem entries — no separate storage, it reuses the same
save/load path as any other mapping).
"""

import bpy

from ..core import presets

# UI-only fields, never persisted into a preset file.
_SKIP_FIELDS = {"fold", "selected"}


def _redraw_ui(context):
    wm = context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'UI':
                        region.tag_redraw()


def _entry_to_dict(item, kind):
    d = {"kind": kind}
    for attr in type(item).__annotations__.keys():
        if attr in _SKIP_FIELDS:
            continue
        d[attr] = getattr(item, attr)
    return d


class OSC_OT_SavePreset(bpy.types.Operator):
    bl_idname = "osc_mapping.save_preset"
    bl_label = "Save Preset"
    bl_description = "Save the current mappings (or just the selected ones) as a named preset"
    bl_options = {'REGISTER'}

    preset_name: bpy.props.StringProperty(name="Preset Name", default="")
    selected_only: bpy.props.BoolProperty(default=False)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "preset_name")

    def execute(self, context):
        name = self.preset_name.strip()
        if not name:
            self.report({'ERROR'}, "Preset name cannot be empty")
            return {'CANCELLED'}

        scn = context.scene
        entries = []

        for item in scn.osc_mappings:
            if self.selected_only and not item.selected:
                continue
            entries.append(_entry_to_dict(item, "shapekey"))

        for item in scn.osc_generic_mappings:
            if self.selected_only and not item.selected:
                continue
            entries.append(_entry_to_dict(item, "generic"))

        if not entries:
            self.report({'WARNING'}, "No mappings to save (check your selection)")
            return {'CANCELLED'}

        presets.save_preset(name, entries)
        self.report({'INFO'}, f"Preset '{name}' saved ({len(entries)} mapping(s))")
        _redraw_ui(context)
        return {'FINISHED'}


class OSC_OT_LoadPreset(bpy.types.Operator):
    bl_idname = "osc_mapping.load_preset"
    bl_label = "Load Preset"
    bl_description = "Add every mapping from this preset to the current scene (additive, does not clear existing mappings)"
    bl_options = {'REGISTER', 'UNDO'}

    preset_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        entries = presets.load_preset(self.preset_name)
        if not entries:
            self.report({'ERROR'}, f"Preset '{self.preset_name}' is empty or missing")
            return {'CANCELLED'}

        scn = context.scene
        count = 0

        for entry in entries:
            kind = entry.get("kind")
            collection = scn.osc_mappings if kind == "shapekey" else scn.osc_generic_mappings
            item = collection.add()
            for key, value in entry.items():
                if key == "kind" or not hasattr(item, key):
                    continue
                setattr(item, key, value)
            count += 1

        self.report({'INFO'}, f"Loaded {count} mapping(s) from '{self.preset_name}'")
        _redraw_ui(context)
        return {'FINISHED'}


class OSC_OT_DeletePreset(bpy.types.Operator):
    bl_idname = "osc_mapping.delete_preset"
    bl_label = "Delete Preset"
    bl_description = "Delete this saved preset file"
    bl_options = {'REGISTER'}

    preset_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        presets.delete_preset(self.preset_name)
        self.report({'INFO'}, f"Preset '{self.preset_name}' deleted")
        _redraw_ui(context)
        return {'FINISHED'}


class OSC_OT_ClearAllMappings(bpy.types.Operator):
    bl_idname = "osc_mapping.clear_all_mappings"
    bl_label = "Clear All Mappings"
    bl_description = "Remove every mapping (shape key and generic) from the current scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        scn.osc_mappings.clear()
        scn.osc_generic_mappings.clear()
        _redraw_ui(context)
        return {'FINISHED'}


class OSC_OT_CreateCameraMappings(bpy.types.Operator):
    bl_idname = "osc_mapping.create_camera_mappings"
    bl_label = "Create Camera Mappings"
    bl_description = "Generate 6 generic mappings (position xyz + rotation xyz) for the picked camera"
    bl_options = {'REGISTER', 'UNDO'}

    # Flat, single-leading-slash camelCase — matches the addon's existing
    # convention (cf. OSC_OT_AddBulkMappings: "/mouthSmileLeft" etc.), not
    # a nested path.
    _AXES = ("X", "Y", "Z")

    def execute(self, context):
        scn = context.scene
        camera = scn.osc_camera_preset_target

        if camera is None or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Pick a camera object first")
            return {'CANCELLED'}

        cam_name = camera.name

        for i, axis in enumerate(self._AXES):
            item = scn.osc_generic_mappings.add()
            item.address = f"/camPos{axis}"
            item.data_path = f"bpy.data.objects['{cam_name}'].location[{i}]"
            item.fold = False

        for i, axis in enumerate(self._AXES):
            item = scn.osc_generic_mappings.add()
            item.address = f"/camRot{axis}"
            item.data_path = f"bpy.data.objects['{cam_name}'].rotation_euler[{i}]"
            item.fold = False

        self.report({'INFO'}, f"6 camera mappings created for '{cam_name}'")
        _redraw_ui(context)
        return {'FINISHED'}


classes = (
    OSC_OT_SavePreset,
    OSC_OT_LoadPreset,
    OSC_OT_DeletePreset,
    OSC_OT_ClearAllMappings,
    OSC_OT_CreateCameraMappings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
