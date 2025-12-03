"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
operators/osc_server.py

Simple operators to:
- Start the OSC server with the IP/port stored on the Scene
- Install the Blender timer that pulls messages from the OSC queue
- Stop the OSC server cleanly

These operators are typically called from UI buttons in the N-panel.
"""

import bpy

from ..core.osc_server import start_server, stop_server, osc_timer_step_extended


class OSC_OT_Start(bpy.types.Operator):
    """
    Start the OSC server and register the timer callback.

    Uses the IP and port stored on the current Scene (osc_ip, osc_port)
    and installs a bpy.app.timers callback (osc_timer_step_extended) to
    process incoming OSC messages on the main thread.
    """

    bl_idname = "osc_server.start"
    bl_label = "Start OSC Server"

    def execute(self, context):
        scn = context.scene

        # Try to start the underlying OSC server
        err = start_server(scn.osc_ip, scn.osc_port)
        if err:
            # start_server returns a string on error (e.g. port in use)
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        
        # Install the timer handler once per scene to drive OSC updates
        if not getattr(scn, "_osc_timer_installed", False):
            bpy.app.timers.register(osc_timer_step_extended, first_interval=0.01, persistent=True)
            # Use a custom property on the Scene to remember that the timer is active
            scn["_osc_timer_installed"] = True
        
        self.report({'INFO'}, f"OSC server listening on {scn.osc_ip}:{scn.osc_port}")
        return {'FINISHED'}

class OSC_OT_Stop(bpy.types.Operator):
    """
    Stop the OSC server.

    This calls the core.stop_server() helper, which signals the OSC
    thread to shut down and clears its internal message queue.
    """

    bl_idname = "osc_server.stop"
    bl_label = "Stop OSC Server"

    def execute(self, context):
        stop_server()
        self.report({'INFO'}, "OSC stopped")
        return {'FINISHED'}

# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------

classes = (
    OSC_OT_Start,
    OSC_OT_Stop,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            # Safe guard in case of partial registration
            pass
