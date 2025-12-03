"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""


bl_info = {
    "name": "OSC Controller",
    "author": "Guillaume Hervy",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > N-Panel > OSC",
    "description": "Advanced control of Blender properties via OSC (shape keys, bones, generic properties).",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "category": "Animation",
}

import bpy

# Import top-level sub-packages of the add-on
from . import properties
from . import operators
from . import ui

# Ordered list of modules that expose register()/unregister()
modules = [
    properties,
    operators, 
    ui,
]

def register():
    """
    Register the add-on.

    This function is called by Blender when the add-on is enabled.
    It delegates registration to each submodule (properties, operators, ui)
    and prints simple logs to the console for debugging.
    """
    print("🔄 OSC add-on registration...")
    
    # Register all submodules in order
    for module in modules:
        if hasattr(module, 'register'):
            module.register()
            print(f"✅ Module {module.__name__} register")
        else:
            print(f"⚠️ Module {module.__name__} does not have a register function")

def unregister():
    """
    Unregister the add-on.

    This function is called by Blender when the add-on is disabled.
    It unregisters submodules in reverse order and stops the OSC server
    if it is currently running.
    """
    print("🔄 Unregistering the OSC addon...")
    
    # Unregister in reverse order to avoid dependency issues
    for module in reversed(modules):
        if hasattr(module, 'unregister'):
            module.unregister()
            print(f"✅ Module {module.__name__} unregister")
    
    # Stop OSC server if active (safe-guard on import)
    try:
        from .core.osc_server import stop_server

        stop_server()
    except:
        # Avoid raising during add-on disable if server/core is not available
        pass

if __name__ == "__main__":
    register()
