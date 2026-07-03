"""
    Copyright (C) 2026  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
core/presets.py

File-based storage for OSC mapping presets (JSON, one file per preset,
under Blender's per-user scripts/presets/osc_controller/ — the standard
Blender preset-storage location, so presets survive addon
updates/reinstalls). Each preset is a flat list of mapping dicts tagged
"kind": "shapekey" or "generic", plus every field of the corresponding
PropertyGroup (properties/scene_props.py). Plain logic, no bpy.types
classes — not registered from __init__.py, same as data_utils.py.
"""

import json
import os

import bpy


def get_presets_dir():
    """Per-user presets directory for this add-on, created if missing."""
    path = bpy.utils.user_resource('SCRIPTS', path=os.path.join("presets", "osc_controller"), create=True)
    return path


def list_presets():
    """Sorted list of saved preset names (no .json extension)."""
    d = get_presets_dir()
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


def save_preset(name, entries):
    """entries: list of dicts, each with a "kind" key ("shapekey"/"generic") plus mapping fields."""
    path = os.path.join(get_presets_dir(), f"{name}.json")
    with open(path, "w") as f:
        json.dump({"mappings": entries}, f, indent=2)


def load_preset(name):
    """Returns the entries list stored under name, or [] if the file is missing/invalid."""
    path = os.path.join(get_presets_dir(), f"{name}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("mappings", [])


def delete_preset(name):
    path = os.path.join(get_presets_dir(), f"{name}.json")
    if os.path.exists(path):
        os.remove(path)
