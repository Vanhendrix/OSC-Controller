"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
core/osc_server.py

Management of the OSC (threaded) server used by the add-on:
- Creation/stopping of the UDP server
- Distribution of OSC messages to the appropriate handlers
- Periodic state updates via a Blender timer
"""

import bpy
import sys
import threading
import queue
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple

# ------------------------------------------------------------------------------------------------------
# Python-OSC import (bundled vendor package)
# ------------------------------------------------------------------------------------------------------

# Path to the local "vendors" directory that contains the bundled python-osc
VENDOR_DIR = Path(__file__).parent.parent / "vendors"

# Make sure the vendors directory is visible by the Python interpreter
if str(VENDOR_DIR) not in sys.path:
    # Insert at the begining so it has priority over any system-installed version
    sys.path.insert(0, str(VENDOR_DIR))

# External dependency: bundled python-osc (see vendors/pythonosc)
try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import ThreadingOSCUDPServer
except ImportError:
    # If this happens, the vendors/pythonosc folder is probably missing or corrupted
    Dispatcher = None
    ThreadingOSCUDPServer = None

# ------------------------------------------------------------------------------------------------------
# Internal imports: mapping and data application utilities
# ------------------------------------------------------------------------------------------------------

from .mapping import build_mapping_table_extended
from .data_utils import apply_shapekey_value, apply_bone_rotation
from .property_handler import apply_generic_value


# ------------------------------------------------------------------------------------------------------
# Global state container
# ------------------------------------------------------------------------------------------------------

class OSCState:
    """
    Small container for all runtime state related to the OSC server.

    Attributes:
        server_thread: Background thread running the OSC server loop.
        server: The underlying ThreadingOSCUDPServer instance.
        dispatcher: python-osc Dispatcher routing incoming messages.
        msg_queue: Thread-safe queue of (address, args) tuples to be processed by Blender's main thread.
        running: Flag indicating whether the OSC server loop should keep running
    """
    server_thread: Optional[threading.Thread] = None
    server: Optional[ThreadingOSCUDPServer] = None
    dispatcher: Optional[Dispatcher] = None
    msg_queue: "queue.Queue[Tuple[str, List[float]]]" = queue.Queue()
    running: bool = False

# Single global state instance used by the add-on
osc_state = OSCState()


# ------------------------------------------------------------------------------------------------------
# OSC message handler (called from the OSC thread)
# ------------------------------------------------------------------------------------------------------

def osc_handler(address, *args):
    """
    Default handler called by python-osc for every incoming OSC message.

    This function runs in the OSC server thread, so it must be very fast
    and never touch Blnder data directly. It only pushes messages into
    a thread-safe queue to be processed later on the main thread.

    Args:
        address: OSC address string (e.g. '/osc/shape/Smile).
        *args: Variable-length list of OSC arguments (numbers, strings, etc.).
    """
    print(f"OSC MESSAGE: {address} {args}")
    try:
        # Store the message in the queue as (address, list_of_args)
        osc_state.msg_queue.put_nowait((address, list(args)))
    except queue.Full:
        # If the queue is full, silently drop the message to avoid blocking
        pass


# ------------------------------------------------------------------------------------------------------
# Server lifecycle management
# ------------------------------------------------------------------------------------------------------

def start_server(ip: str, port: int) -> Optional[str]:
    """
    Start the OSC UDP server in a dedicated background thread.

    This function is usually called from a Blender operator.
    It configures python-osc, creates the UDP server, and spawns a thread
    that will poll the socket and feed the message queue.

    Args:
        ip: IP address to bind the server (e.g. '127.0.0.1').
        port: UDP port to listen on.

    Returns:
        None on success, or a human-readable error message on failure.
    """
    # Prevent starting two servers at the same time
    if osc_state.running:
        return "Server already started."
    
    # If python-osc could not be imported, we cannot start the server
    if Dispatcher is None or ThreadingOSCUDPServer is None:
        return "python-osc could not be imported (check addon vendors folder)"
    
    try:
        # Create a dispatcher that routes all messages to osc_handler
        disp = Dispatcher()
        disp.set_default_handler(osc_handler, needs_reply_address=False)
        
        # Create the UDP server with a very small timeout so handle_request()
        # does not block for long (better responsiveness in the thread loop).
        server = ThreadingOSCUDPServer((ip, port), disp)
        server.timeout = 0.0001
        
        # Additional socket options to improve stability and thtoughput.
        import socket
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 1MB receive buffer to better handle bursts of OSC messages
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
        server.socket.settimeout(0.0001)
        
        def serve():
            """
            Main loop running in the background thread.

            It repeatedly calls server.handle_request() while osc_state.running
            is True, and the closes the server when the loop exists.
            """
            print("🚀 OSC server started !")
            while osc_state.running:
                try:
                    server.handle_request()
                except:
                    # Ignore timeouts and any non-fatal socket errors
                    continue  
            # Gracefully close the underlying socket
            server.server_close()

        # Store dispatcher and server in the global state
        osc_state.dispatcher = disp
        osc_state.server = server
        osc_state.running = True

        # Start the background thread in daemon mode
        t = threading.Thread(target=serve, daemon=True)
        t.start()
        osc_state.server_thread = t
        
        return None
        
    except OSError as e:
        # Typival case: port already in use or invalid bind address
        osc_state.running = False
        osc_state.server = None
        osc_state.server_thread = None
        return f"socket error: {e}"


def stop_server():
    """
    Stop the OSC server and clean up all runtime state.

    This can be called from a Blender operator or on add-on unregister().
    It signals the background thread to stop, waits a short time, and clears
    the message queue.
    """
    if not osc_state.running:
        return
    
    # Signal the background thread to exit its loop
    osc_state.running = False

    # Give th thread a small amount of time to shut down cleanly
    try:
        time.sleep(0.25)
    except:
        pass

    # restart server-related state
    osc_state.server = None
    osc_state.server_thread = None
    osc_state.dispatcher = None
    
    # Clear any remaining messages in the queue
    with osc_state.msg_queue.mutex:
        osc_state.msg_queue.queue.clear()


# ------------------------------------------------------------------------------------------------------
# Timer step: apply OSC messages on Blender's main thread
# ------------------------------------------------------------------------------------------------------

def osc_timer_step_extended() -> Optional[float]:
    """
    Process a batch of pending OSC messages and apply them to Blender.

    This function is expected to be called regularly from Blender's main
    thread (for example via bpy.app.timers). It:

    - Read messages from the thread-safe queue
    - Resolves them to the corresponding OSC mappings
    - Applies all changes at once (shape keys, bones, generic properties)
    - Triggers a single view layer update

    Returns:
        A float delay (in seconds) for the next timer call, or None to stop.
    """
    if not osc_state.running:
        # If the server is not running, the timer can optionnaly stop
        return None

    # Build the mapping table for the current scene/context
    table = build_mapping_table_extended(bpy.context)

    processed = 0
    max_per_tick = 100 # Safety limit: number of messages processed per tick

    # Collect all messages whithout applying them yet
    messages_batch: List[Tuple[str, List[float]]] = []

    while not osc_state.msg_queue.empty() and processed < max_per_tick:
        try:
            address, args = osc_state.msg_queue.get_nowait()
            messages_batch.append((address, args))
            processed += 1
        except queue.Empty:
            break
    
    # If there are no messages, we can sleep for a short time.
    if not messages_batch:
        return 0.01

    # Prepare a list of concrete updates to apply to Blender data
    updates_to_apply: List[Tuple] = []

    for address, args in messages_batch:
        value = None

        # Find the first numeric argument in the OSC message
        for a in args:
            if isinstance(a, (float, int)):
                value = float(a)
                break

        if value is not None and address in table:
            # Import here to avoid circular imports at module level
            from .mapping import OSCMapping, GenericOSCMapping

            # For each mapping registered on this OSC address
            for m in table[address]:
                v = m.map_value(value)
                
                if isinstance(m, OSCMapping):
                    # Shape key mapping
                    if m.shapekey_name:
                        updates_to_apply.append(
                            ('shapekey', m.object_name, m.shapekey_name, v)
                        )
                    # Bone rotation mapping
                    if m.bone_name and m.armature_name:
                        updates_to_apply.append(
                            (
                                'bone', 
                                m.armature_name, 
                                m.bone_name, 
                                m.rotation_axis, 
                                v, 
                                m.rotation_mode)
                        )
                        
                elif isinstance(m, GenericOSCMapping):
                    # Generic data path mapping (timeline, modifiers, node props, etc.)
                    updates_to_apply.append(
                        ('generic', m.data_path, v)
                     )
    
    # Apply all collected changes in a single pass
    try:
        for update in updates_to_apply:
            if update[0] == 'shapekey':
                _, object_name, shapekey_name, value = update
                apply_shapekey_value(object_name, shapekey_name, value)

            elif update[0] == 'bone':
                _, armature_name, bone_name, rotation_axis, value, rotation_mode = update
                apply_bone_rotation(
                    armature_name, 
                    bone_name, 
                    rotation_axis, 
                    value, 
                    rotation_mode
                )

            elif update[0] == 'generic':
                _, data_path, value = update
                apply_generic_value(data_path, value)

        # One single scene update for all changes (better for performance)
        if updates_to_apply:
            bpy.context.view_layer.update()
    
    except Exception as e:
        # Catch any unexpected error during application to avoid killing the timer
        print(f"⚠️ OSC application error: {e}")

    # Schedule the next timer call in 0.01 seconds
    return 0.01
