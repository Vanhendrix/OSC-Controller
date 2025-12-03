"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
properties/__init__.py

Entry point for registering all custom properties used by the add-on.

Currently this just delegates to scene_props, which defines:
- Scene-level settings (IP, port, autokey)
- Collection properties for OSC mappings
"""

# Import the scene_props module (PropertyGroups + Scene properties)
from .scene_props import *

def register():
    """
    Register all PropertyGroups and Scene properties used by the add-on.

    The main add-on __init__.py calls properties.register(), which in turn
    calls scene_props.register().
    """
    scene_props.register()

def unregister():
    """
    Unregister all custom properties defined for the add-on.

    This removes the properties from bpy.types.Scene and unregisters
    the associated PropertyGroup classes.
    """
    scene_props.unregister()
