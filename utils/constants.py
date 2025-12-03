"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
utils/constants.py

Central place to define default configuration values used across
the OSC add-on (IP, port, etc.).
"""


# Default UDP port used by the OSC server when a new Scene is created
DEFAULT_OSC_PORT = 9000

# Default IP address to bind to (0.0.0.0 = listen on all interfaces)
DEFAULT_OSC_IP = "0.0.0.0"