# OSC Controller for Blender

Advanced control of Blender properties over OSC.
Drive shape keys, bones and arbitrary properties in real time from tools like TouchDesigner, Pure Data, Max, etc.

## Features
- Receive OSC messages over UDP and map them to:
    - Shape keys (facial blenshape and other deformations)
    - Bone rotations (Euler or Quaternion)
    - Generic Blender properties via data paths (`bpy.data.*`, `bpy.context.*`, node inputs, etc.)
- Right-click on any property in Blender to create an OSC mapping automatically.
- Auto-key option to record incoming OSC values as keyframes on the timeline.
- Bundled `python-osc` library (no separate installation required).

## Requirements
- Blender 4 or newer
- OS: anything supported by Blender and Python.

## Installation
1. Download the repo.
2. In Blender:
    - Edit -> Preferences -> Add-ons -> Install from disk.
    - Select the ZIP file.
    - Enable the "OSC Controller" add-on in the list.
3. The panel appears in the 3D View -> N-panel -> "OSC" tab.

The add-on bundles `python-osc` under `vendors/pythonosc`, so no extra pip installation is required.

## Quick Start
1. Install and enable the add-on as described above.
2. Open the 3D View -> N-panel -> "OSC" tab.
3. In the "OSC Control" section:
    - Set `IP` (usually `0.0.0.0` to listen on all interfaces).
    - Set `Port` (default `9000`, must match yout OSC sender).
    - Optionally enable `Auto Key` if you want incoming OSC data to insert keyframes.
4. Click Start to launch the OSC server.
5. From your OSC tool (TouchDesigner, Pure Data, etc.), send messages to `IP:Port` with appropriate addresses.

*Creating mappings*

There are two main ways to create mappings:
1. from the panel (manual)
    - Shape Key Mappings:
        - Click "Add Shape Key Mapping" or "Add 50 Face Shape Key Mappings" (if you for example a character with the 52 AR-Kit blendshapes already setup in Blender)
        - Set `address`, `object_name` and `shapekey_name`.
    - Generic Property Mappings:
        - Click "Add Generic Mapping".
        - Set `address` and `data_path` (e.G. `bpy.data.objects['Cube'].location[0]` to control the X location of the default cube).
2. From a right-clik on any property
    - Right-click on a property on any Blender panel.
    - Choose "Create OSC Mapping" from the context menu.
    - A new "Generic Property Mapping entry is automatically created with:
        - A generated OSC address (based on object and property).
        - A valid `data_path` pointing to that property.

The mapping ranges (`Min In`, `Max In`, `Min Out`, `Max Out`) determine how OSC values are normalized and remapped before being applied.

## OSC Server Details
- Protocol: UDP.
- Library: `python-osc` (bundled, pure Python).
- The server runs in a background thread and pushes incoming messages to a thread-safe queue.
- A Blender timer (`bpy.app.timers`) periodically:
    - Consumes messages from the queue.
    - Resolves them to one or more mappings.
    - Applies all changes in one batch, then triggers a single view layer update.

If the serve cannot start (e.g. port already in use), a nerror is shown in Blender's satus bar and the console.

## Auto-Keyframing
When `Auto-Key` is enabled in the OSC panel:

- Shape keys:
    - Values are keyframed on the shape key’s `value` property (group “OSC”).
- Bones:
    - Rotations are keyframed on `rotation_euler` or `rotation_quaternion` depending on the mapping.
- Shader nodes / Node groups:
    - Node input sockets are keyframed on `default_value` at the current frame.
- Generic `bpy.data.*` properties:
    - Appropriate datablocks (objects, cameras, lights, etc.) get keyframes on the resolved data path, with automatic creation of actions such as `MyCamera_CameraAction`, `MyLight_LightAction`, or `MyObject_OSCAction`.

This is useful for recording live performance driven by OSC directly into Blender's timeline.

## Third-Party Libraries
This add-on bundles the following third-party library:

- python-osc
    - Pure Python OSC server/clinet implementation.
    - Distributed under the Unlicense (public domain / "do what you want" license).
    - The original license file is included under `vendors/pythonosc/`.

The add-on code itself is licensed under the GNU GPL, version 3 or later (see below).

## License
- The add-on is licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).
- See the `LICENSE` file at the root of the repository for the full terms.

This complies with Blender's requirement that Python add-ons using `bpy` API be GPL-compatible.

You are free to study, modify and redistribute this add-on under the terms of the GPL, including in commercial contexts, as long as you respects the GPL conditions.

    