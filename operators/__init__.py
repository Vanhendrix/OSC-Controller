"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
operators/__init__.py

Entry point for registering all OSC-related operators.

This module imports the individual operator modules (osc_server,
mapping_operators) and exposes a single register()/unregister() pair
used by the main add-on __init__.py.
"""

# Import all operator submodules
from . import osc_server
from . import mapping_operators

# List of operator modules that expose their own register()/unregister()
modules = [osc_server, mapping_operators]


def register():
    """
    Register all operator classes from the submodules.

    The main add-on __init__.py only needs to call operators.register(),
    which in turn delegates to each submodule's register() function.
    """
    for module in modules:
        if hasattr(module, 'register'):
            module.register()


def unregister():
    """
    Unregister operator classes in reverse order.

    Using reversed(modules) helps avoid potential dependency issues
    between modules during unregistration.
    """
    for module in reversed(modules):
        if hasattr(module, 'unregister'):
            module.unregister()
