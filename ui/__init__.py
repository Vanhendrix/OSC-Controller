"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
ui/__init__.py

Entry point for registering all UI components of the add-on:

- The main OSC panel in the 3D View (N-panel)
- The extra entry in the button context menu (right-click on properties)
"""

from . import panels
from . import context_menu

# List of UI modules that expose register()/unregister()
modules = [panels, context_menu]

def register():
    """
    Register all UI panels and menu extensions.

    The main add-on __init__.py only needs to call ui.register(),
    which in turn delegates to each submodule's register() function.
    """
    for module in modules:
        if hasattr(module, 'register'):
            module.register()

def unregister():
    """
    Unregister all UI components in reverse order.

    Using reversed(modules) helps avoid potential dependency issues
    when removing panels and menu entries.
    """
    for module in reversed(modules):
        if hasattr(module, 'unregister'):
            module.unregister()
