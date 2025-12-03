"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
ui/context_menu.py

Adds an entry to Blender's standard button context menu (right-click
on any property) to create an OSC mapping for that property.

This integrates with OSC_OT_CreateMappingFromProperty defined in
operators/mapping_operators.py.
"""

import bpy


def draw_osc_context_menu(self, context):
    """
    Callback used to extend Blender's UI_MT_button_context_menu.

    Adds a separator and then our custom 'Create OSC Mapping' entry,
    which calls the osc_mapping.create_from_property operator.
    """
    layout = self.layout
    layout.separator()
    layout.operator("osc_mapping.create_from_property", icon='NETWORK_DRIVE')

def register():
    """
    Register the context menu extension.

    After registration, right-clicking any UI property will show
    the 'Create OSC Mapping' menu item.
    """
    bpy.types.UI_MT_button_context_menu.append(draw_osc_context_menu)

def unregister():
    """
    Remove the context menu extension.

    This is called when disabling the add-on.
    """
    bpy.types.UI_MT_button_context_menu.remove(draw_osc_context_menu)
