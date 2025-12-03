"""
    Copyright (C) 2025  Guillaume Hervy

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 or later.

    See the LICENSE file or <https://www.gnu.org/licenses/> for details.
"""

"""
core/mapping.py

Defines in-memory mapping objects used by the OSC add-on:

- GenericOSCMapping: maps an OSC address to any Blender data path
- OSCMapping: maps an OSC address to shape keys and/or bone rotations
- build_mapping_table_extended: builds a lookup table from the Scene
  properties so that osc_server.py can resolve incoming OSC messages 
  to concrete mapping instances.
"""

from dataclasses import dataclass
from typing import Dict, List

import bpy


# ------------------------------------------------------------------------------------------------------
# Generic mapping (data-path based)
# ------------------------------------------------------------------------------------------------------

@dataclass
class GenericOSCMapping:
    """
    Represents a generic OSC mapping that targets and arbitrary Blender
    property via a RNA data path (e.G. 'scene.frame_current, object modifiers,
    node properties, etc.).

    Attributes:
        address: OSC address string (e.g. '/timeline/frame').
        data_path: Full RNA data path to the target property.
        min_in, max_in: Input range expected from OSC values.
        min_out, max_out: Output range to apply to the Blender property.
        clamp: If True, clamp the normalized input to [0, 1].
        invert: If True, invert the normalized value (1 - t).
    """

    address: str
    # The full Python/RNA path to the property (e.G. "scene.frame_current")
    data_path: str

    min_in: float = 0.0
    max_in: float = 1.0
    min_out: float = 0.0
    max_out: float = 1.0
    clamp: bool = True
    invert: bool = False
    
    def map_value(self, v: float) -> float:
        """
        Map an incoming OSC value from [min_in, max_in] into [min_out, max_out],
        with optional clamping and inversion.

        Args:
            v: Raw OSC numeric value.

        Returns:
            The mapped float value to be applied to the Blender property.
        """
        # Normalize input into [0, 1]
        if self.max_in != self.min_in:
            t = (v - self.min_in) / (self.max_in - self.min_in)
        else:
            # Avoid division by zero: treat the range as a single point
            t = 0.0

        # Optionally clamp to [0, 1]    
        if self.clamp:
            t = max(0.0, min(1.0, t))

        # Optionally invert the normalized value
        if self.invert:
            t = 1.0 - t
        
        # Remap normalized value into [min_out, max_out]
        return self.min_out + t * (self.max_out - self.min_out)


# ------------------------------------------------------------------------------------------------------
# Specific mapping (shape keys / bones)
# ------------------------------------------------------------------------------------------------------

@dataclass
class OSCMapping:
    """
    Represents a more specific OSC mapping for character-related controls:
    shape keys and/or bone rotations.

    Attributes:
        address: OSC address string (e.g. '/face/mouthSmile').
        object_name: Name of the mesh object that holds the shape key.
        shapekey_name: Name of the shape key to drive (can be empty if using bones only).
        armature_name: Name of the armature object for bone control (optional).
        bone_name: Name of the bone to rotate (optional).
        rotation_axis: Axis used for rotation mapping (e.g. 'X', 'Y', 'Z').
        rotation_mode: Rotation mode (e.g. 'EULER', 'QUATERNION', etc.).
        min_in, max_in: Input range expected from OSC values.
        min_out, max_out: Output range for shape key or rotation.
        clamp: If True, clamp the normalized input to [0, 1].
        invert: If True, invert the normalized value (1 - t).
    """

    # OSC address, for example '/face/mouthSmile'
    address: str 

    # Name of the mesh object containing the shape key
    object_name: str

    # Name of the shape key to drive
    shapekey_name: str

    # Optional armature and bone for rotation-based mappings
    armature_name: str = ""
    bone_name: str = ""

    # Rotation parameters for bone mappings
    rotation_axis: str = "X"
    rotation_mode: str = "EULER"

    # Input/output ranges and options
    min_in: float = 0.0
    max_in: float = 1.0
    min_out: float = 0.0
    max_out: float = 1.0
    clamp: bool = True
    invert: bool = False

    def map_value(self, v: float) -> float:
        """
        Map an incoming OSC value from [min_in, max_in] into [min_out, max_out],
        with optional clamping and inversion, exactly like GenericOSCMapping.

        Args:
            v: Raw OSC numeric value.

        Returns:
            The mapped float value to be applied to the shape key or bone.
        """
        # Normalize input into [0, 1]
        if self.max_in != self.min_in:
            t = (v - self.min_in) / (self.max_in - self.min_in)
        else:
            t = 0.0

        # Optionally clamp to [0, 1]
        if self.clamp:
            t = max(0.0, min(1.0, t))

        # Optionally invert the normalized value
        if self.invert:
            t = 1.0 - t

        # Remap normalized value into [min_out, max_out]
        return self.min_out + t * (self.max_out - self.min_out)


# ------------------------------------------------------------------------------------------------------
# Build mapping table from scene properties
# ------------------------------------------------------------------------------------------------------

def build_mapping_table_extended(ctx) -> Dict[str, List]:
    """
    Build a lookup table that groups all mappings by OSC address.

    The table combines:
    - Character mappings (shape keys / bones) from ctx.scene.osc_mappings
    - Generic mappings (any data path) from ctx.scene.osc_generic_mappings

    This structure is used by osc_server.py to quickly find all mappings
    that should react to a given OSC address.

    Args:
        ctx: Blender context (usually bpy.context).

    Returns:
        A dictionary mapping:
            OSC address (str) -> list of OSCMapping or GenericOSCMapping.
    """
    table: Dict[str, List] = {}
    
    # --------------------------------------------------------------------------------------------------
    # Existing mappings: shape keys and bones
    # --------------------------------------------------------------------------------------------------
    for item in ctx.scene.osc_mappings:
        m = OSCMapping(
            address=item.address.strip(),
            object_name=item.object_name.strip(),
            shapekey_name=item.shapekey_name.strip(),
            armature_name=getattr(item, "armature_name", "").strip(),
            bone_name=getattr(item, "bone_name", "").strip(),
            rotation_axis=getattr(item, "rotation_axis", 'X'),
            rotation_mode=getattr(item, "rotation_mode", 'EULER'),
            min_in=item.min_in,
            max_in=item.max_in,
            min_out=item.min_out,
            max_out=item.max_out,
            clamp=bool(item.clamp),
            invert=bool(item.invert),
        )

         # Group mappings by OSC address
        table.setdefault(m.address, []).append(m)
    
    # --------------------------------------------------------------------------------------------------
    # New generic mappings (any data path)
    # --------------------------------------------------------------------------------------------------
    for item in ctx.scene.osc_generic_mappings:
        m = GenericOSCMapping(
            address=item.address.strip(),
            data_path=item.data_path.strip(),
            min_in=item.min_in,
            max_in=item.max_in,
            min_out=item.min_out,
            max_out=item.max_out,
            clamp=bool(item.clamp),
            invert=bool(item.invert),
        )

        # Group mappings by OSC address
        table.setdefault(m.address, []).append(m)
    
    return table
