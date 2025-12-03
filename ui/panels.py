"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
ui/panels.py

Defines the main OSC UI panel in the 3D View (N-panel):

- Server section: IP / Port / Auto Key + Start/Stop buttons
- Shape Key mappings section: list of OSCMappingItem entries
- Generic mappings section: list of GenericOSCMappingItem entries
- Helper tip about right-click context menu mapping creation
"""

import bpy

from ..core.osc_server import osc_state


class OSC_PT_Panel_Extended(bpy.types.Panel):
    """
    Main panel for controlling the OSC add-on.

    Appears in:
        3D View > N-panel > "OSC" tab

    Provides:
        - OSC server configuration and start/stop controls
        - Shape Key mapping list and controls
        - Generic property mapping list and controls
    """

    bl_label = "OSC Control"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "OSC"

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        # --------------------------------------------------------------
        # OSC Server settings and controls
        # --------------------------------------------------------------
        col = layout.column(align=True)
        col.prop(scn, "osc_ip")
        col.prop(scn, "osc_port")
        col.prop(scn, "osc_autokey")

        row = col.row(align=True)
        if osc_state.running:
            # When server is running, show a "Stop" button
            row.operator("osc_server.stop", text="Stop", icon="PAUSE")
        else:
            # When server is stopped, show a "Start" button
            row.operator("osc_server.start", text="Start", icon="PLAY")

        layout.separator()
        
        # --------------------------------------------------------------
        # Section: Shape Key mappings
        # --------------------------------------------------------------
        layout.label(text="Shape Key Mappings", icon="SHAPEKEY_DATA")

        for i, item in enumerate(scn.osc_mappings):
            box = layout.box()

            # Row header with fold toggle, labels and actions
            header = box.row(align=True)

            # Triangle icon indicates folded/expanded state
            icon = "TRIA_RIGHT" if item.fold else "TRIA_DOWN"
            op = header.operator("osc_mapping.toggle_fold", text="", icon=icon, emboss=False)
            op.index = i

            # Display OSC address, object name and shape key name as quick overview
            header.label(text=item.address if item.address else "/param")
            header.label(text=item.object_name if item.object_name else "(Object)")
            header.label(text=item.shapekey_name if item.shapekey_name else "(ShapeKey)")

            # Duplicate and remove buttons
            header.operator("osc_mapping.duplicate", text="", icon="DUPLICATE").index = i
            header.operator("osc_mapping.remove", text="", icon="X").index = i

            # If the item is unfolded, show all detailed properties
            if not item.fold:
                box.prop(item, "address")
                box.prop(item, "object_name")
                box.prop(item, "shapekey_name")
                box.prop(item, "armature_name")
                box.prop(item, "bone_name")
                box.prop(item, "rotation_axis")
                box.prop(item, "rotation_mode")

                row = box.row(align=True)
                row.prop(item, "min_in"); row.prop(item, "max_in")

                row = box.row(align=True)
                row.prop(item, "min_out"); row.prop(item, "max_out")

                row = box.row(align=True)
                row.prop(item, "clamp"); row.prop(item, "invert")

        # Button to add a new empty mapping row
        layout.operator("osc_mapping.add", text="Add Shape Key Mapping", icon="ADD")

        # Convenience button to create a full set of facial shape key mappings
        layout.operator("osc_mapping.add_bulk", text="Ajouter 50 mappings ShapeKeys", icon="PLUS")
        
        layout.separator()
        
        # --------------------------------------------------------------
        # Section: Generic property mappings
        # --------------------------------------------------------------
        layout.label(text="Generic Property Mappings", icon="PROPERTIES")

        for i, item in enumerate(scn.osc_generic_mappings):
            box = layout.box()

            # Header row with fold toggle, short labels and actions
            header = box.row(align=True)

            icon = "TRIA_RIGHT" if item.fold else "TRIA_DOWN"
            op = header.operator("osc_mapping.toggle_generic_fold", text="", icon=icon, emboss=False)
            op.index = i

            # Show OSC address and a short form of the data_path
            header.label(text=item.address if item.address else "/param")
            short_path = item.data_path.split('.')[-1] if item.data_path else "(Property)"
            header.label(text=short_path)

            # Duplicate and remove actions
            header.operator("osc_mapping.duplicate_generic", text="", icon="DUPLICATE").index = i
            header.operator("osc_mapping.remove_generic", text="", icon="X").index = i

            # Detailed editing UI when not folded
            if not item.fold:
                box.prop(item, "address")
                box.prop(item, "data_path")

                row = box.row(align=True)
                row.prop(item, "min_in"); row.prop(item, "max_in")

                row = box.row(align=True)
                row.prop(item, "min_out"); row.prop(item, "max_out")

                row = box.row(align=True)
                row.prop(item, "clamp"); row.prop(item, "invert")

        # Button to add a new generic mapping row
        layout.operator("osc_mapping.add_generic", text="Add Generic Mapping", icon="ADD")
        
        # --------------------------------------------------------------
        # Help / Tip box about right-click mapping
        # --------------------------------------------------------------
        box = layout.box()
        box.label(text="💡 Tip: Right-click on any property", icon="INFO")
        box.label(text="in Blender to create an OSC mapping!")

# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------

classes = (
    OSC_PT_Panel_Extended,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            # In case of partial registration in dev workflows
            pass
