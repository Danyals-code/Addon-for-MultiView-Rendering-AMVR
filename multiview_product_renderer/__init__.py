bl_info = {
    "name": "MultiView Product Renderer",
    "author": "Danyal Sarfraz",
    "version": (1, 10, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > MultiView",
    "description": "Import CAD and mesh files, set up cameras and studio lighting, batch render products across views.",
    "category": "Render",
}

import bpy
import blf
import os
import re
import csv
import json
import math
import struct
import subprocess
import tempfile
import shutil
import time
import traceback
import zlib
from contextlib import contextmanager
from datetime import datetime
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from bpy.props import (
    StringProperty, EnumProperty, BoolProperty, FloatProperty,
    IntProperty, FloatVectorProperty, BoolVectorProperty, CollectionProperty,
    PointerProperty,
)
from bpy.types import (
    Operator, Panel, PropertyGroup, AddonPreferences, UIList,
)
from bpy_extras.io_utils import ImportHelper


VIEWS_ALL = [
    ("Front",     "ortho",  ( 0, -1,  0)),
    ("Back",      "ortho",  ( 0,  1,  0)),
    ("Top",       "ortho",  ( 0,  0,  1)),
    ("Bottom",    "ortho",  ( 0,  0, -1)),
    ("Right",     "ortho",  ( 1,  0,  0)),
    ("Left",      "ortho",  (-1,  0,  0)),
    ("Persp_FTR", "persp",  ( 1, -1,  0.9)),
    ("Persp_FTL", "persp",  (-1, -1,  0.9)),
    ("Persp_BTR", "persp",  ( 1,  1,  0.9)),
]
VIEW_SETS = {
    "ALL":   VIEWS_ALL,
    "ORTHO": VIEWS_ALL[:6],
    "STD":   [VIEWS_ALL[0], VIEWS_ALL[2], VIEWS_ALL[4], VIEWS_ALL[6]],
    "MIN":   [VIEWS_ALL[0], VIEWS_ALL[2], VIEWS_ALL[4]],
}

FRONT_AXIS_ANGLES = {'-Y': 0.0, '+X': 90.0, '+Y': 180.0, '-X': 270.0}

LIGHTING_PRESETS = {
    "STUDIO_SOFT": {
        "label": "Studio Soft",
        "lights": [
            {"name": "Key",  "pos": ( 1.5, -1.2, 1.6), "size": 3.0, "energy": 800, "color": (1, 1, 1)},
            {"name": "Fill", "pos": (-1.8, -0.8, 1.0), "size": 4.0, "energy": 300, "color": (1, 1, 1)},
            {"name": "Rim",  "pos": ( 0.0,  2.0, 2.0), "size": 2.0, "energy": 600, "color": (1, 1, 1)},
        ],
    },
    "STUDIO_HARD": {
        "label": "Studio Hard",
        "lights": [
            {"name": "Key",  "pos": ( 1.4, -1.2, 1.4), "size": 0.8, "energy": 1200, "color": (1, 1, 1)},
            {"name": "Fill", "pos": (-1.6, -0.6, 0.9), "size": 1.5, "energy":  350, "color": (1, 1, 1)},
            {"name": "Rim",  "pos": ( 0.0,  2.2, 2.2), "size": 0.6, "energy":  900, "color": (1, 1, 1)},
        ],
    },
    "DRAMATIC": {
        "label": "Dramatic",
        "lights": [
            {"name": "Key",  "pos": ( 2.0, -1.5, 1.8), "size": 1.2, "energy": 1500, "color": (1.0, 0.98, 0.94)},
            {"name": "Fill", "pos": (-2.0, -0.5, 0.6), "size": 2.5, "energy":  120, "color": (0.85, 0.9, 1.0)},
            {"name": "Rim",  "pos": (-0.5,  2.5, 2.5), "size": 0.8, "energy": 1000, "color": (1, 1, 1)},
        ],
    },
    "HIGH_KEY": {
        "label": "High Key",
        "lights": [
            {"name": "Key",  "pos": ( 1.2, -1.2, 1.8), "size": 4.0, "energy": 1000, "color": (1, 1, 1)},
            {"name": "Fill", "pos": (-1.4, -1.0, 1.4), "size": 4.0, "energy":  800, "color": (1, 1, 1)},
            {"name": "Rim",  "pos": ( 0.0,  1.8, 2.4), "size": 3.5, "energy":  900, "color": (1, 1, 1)},
        ],
    },
    "NONE": {
        "label": "No Lights (HDRI only)",
        "lights": [],
    },
}

# Saved lighting presets are tagged with this prefix in the enum, so they can
# never collide with a built-in key.
USER_PRESET_PREFIX = "USER:"
LIGHT_RIG = "MV_LightRig"

MATERIAL_PRESETS = {
    "MATTE_PLASTIC":  {"label": "Matte Plastic",  "inputs": {"Roughness": 0.55}},
    "GLOSSY_PLASTIC": {"label": "Glossy Plastic", "inputs": {"Roughness": 0.12, "Coat Weight": 0.4}},
    "RUBBER":         {"label": "Rubber",         "inputs": {"Roughness": 0.9}},
    "BRUSHED_METAL":  {"label": "Brushed Metal",  "inputs": {"Metallic": 1.0, "Roughness": 0.35,
                                                             "Anisotropic": 0.8}},
    "POLISHED_METAL": {"label": "Polished Metal", "inputs": {"Metallic": 1.0, "Roughness": 0.06}},
    "GLASS":          {"label": "Glass",          "inputs": {"Roughness": 0.02, "IOR": 1.45,
                                                             "Transmission Weight": 1.0}},
}
MATERIAL_ITEMS = [(k, v["label"], f"Render with a {v['label'].lower()} material")
                  for k, v in MATERIAL_PRESETS.items()]
MATERIAL_MOD = "MV_Material"
MATERIAL_GROUP = "MV_SetMaterial"

UNIT_ITEMS = [("mm", "Millimetres", ""), ("cm", "Centimetres", ""), ("m", "Metres", ""),
              ("in", "Inches", ""), ("ft", "Feet", "")]
UNIT_TO_MM = {"um": 0.001, "mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "ft": 304.8}

# Object types that put something in front of a camera. Lights and cameras
# are not here; neither are empties, which only carry a transform.
GEOMETRY_TYPES = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}

CAMERA_COLL = "MV_Cameras"
LIGHT_COLL = "MV_Lighting"
PRODUCT_COLL = "MV_Products"
STAGE_COLL = "MV_Stage"
WORLD_NAME = "MV_World"
GROUND_NAME = "MV_Ground"

GUIDE_LINES = [
    "1. Scene Setup: pick lighting (or save your own with +), a colour or",
    "   HDRI background and a ground, then Apply. Materials sets preset",
    "   materials for Full renders, for the batch or one product.",
    "2. Import: add files or a whole folder, then click Import. STEP and",
    "   IGES need FreeCAD (STEP can use STEPper); STL, OBJ, PLY, glTF,",
    "   FBX and 3MF are meshes and import directly. Each file becomes a",
    "   collection under MV_Products; STEP parts keep names and colours.",
    "   You can also create empty product collections and drop meshes in.",
    "3. Standardize: centre and scale every product, to one size each or",
    "   keeping their real proportions, and fix the faceted shading a CAD",
    "   tessellation arrives with. Fit on Import does it as each file lands.",
    "4. Cameras: pick a view set (or Custom and tick views), front axis,",
    "   click Build. Then use Orient Products to walk the batch one at a",
    "   time: Auto Orient lays products flat, Reset undoes any turning.",
    "5. Render: set output folder, mode (full/clay/both), starting index,",
    "   tick the products you want, then Render All or Render Active.",
    "   Pre-flight checks the batch first and offers one-click fixes.",
    "   Esc stops after the current image; Skip Existing resumes.",
    "   Cameras are reframed first. Files are named PREFIX_NN_Product_View,",
    "   or however the Naming templates say.",
    "   Optional extras under Batch Render: contact sheets, turntables",
    "   (MP4/GIF), post-processed copies, and a CSV/JSON manifest.",
    "   Annotations adds cameras.json/transforms.json, depth, normals,",
    "   part IDs, COCO and BOP for building datasets.",
    "",
    "Headless: blender -b --python multiview_product_renderer/cli.py",
    "  -- --config job.json   (see README, Command line)",
    "   Only products are hidden between shots, so anything outside",
    "   MV_Products lands in every image. The panel warns you first.",
    "",
    "Render engine, samples, resolution and file format stay under your",
    "control in Blender's Output and Render properties.",
]


class MV_AddonPreferences(AddonPreferences):
    bl_idname = __name__

    step_import_mode: EnumProperty(
        name="STEP Import Mode",
        description="How STEP files are turned into meshes. STL files are meshes "
                    "already and ignore this, importing straight through Blender",
        items=[
            ('AUTO', "Auto", "Try STEPper first, then FreeCAD"),
            ('STEPPER', "STEPper Addon", "Use the STEPper addon"),
            ('FREECAD', "FreeCAD Subprocess", "Convert STEP to OBJ with FreeCAD"),
        ],
        default='AUTO',
    )
    freecad_path: StringProperty(
        name="FreeCAD Executable",
        subtype='FILE_PATH',
        description="Path to freecadcmd.exe (Windows) or freecadcmd (Linux/Mac). "
                    "STEP files only",
        default="",
    )
    tessellation_deflection: FloatProperty(
        name="Tessellation Deflection",
        description="Lower = finer mesh (FreeCAD mode)",
        default=0.1, min=0.001, max=5.0,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "step_import_mode")
        layout.prop(self, "freecad_path")
        layout.prop(self, "tessellation_deflection")


# Set by the command line, which can run the add-on straight from its folder
# without it being installed, and so without add-on preferences to read.
PREFS_OVERRIDE = None


def addon_prefs(context):
    if PREFS_OVERRIDE is not None:
        return PREFS_OVERRIDE
    addon = context.preferences.addons.get(__name__)
    if addon is not None:
        return addon.preferences
    from types import SimpleNamespace
    return SimpleNamespace(step_import_mode='AUTO', freecad_path="",
                           tessellation_deflection=0.1)


# What the last Render All did, for the command line's summary and exit code.
LAST_RENDER = {}


class MV_StepFileItem(PropertyGroup):
    path: StringProperty(name="Path", subtype='FILE_PATH')


class MV_CustomView(PropertyGroup):
    enabled: BoolProperty(
        name="Enabled",
        description="Build a camera for this view and render it",
        default=True,
    )
    name: StringProperty(name="Name", default="CustomView")
    dir_x: FloatProperty(name="X", default=1.0)
    dir_y: FloatProperty(name="Y", default=-1.0)
    dir_z: FloatProperty(name="Z", default=1.0)
    is_ortho: BoolProperty(name="Ortho", default=False)


def user_preset_dir(create=False):
    return bpy.utils.user_resource(
        'SCRIPTS', path=os.path.join("presets", "multiview_lighting"), create=create)


def user_lighting_presets():
    """{enum key: (label, path)} for every saved lighting preset.

    Kept in Blender's user scripts folder rather than in the .blend, so a rig
    saved once is there in every file, the way Blender's own presets are.
    """
    folder = user_preset_dir()
    found = {}
    if folder and os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith(".json"):
                stem = name[:-5]
                found[USER_PRESET_PREFIX + stem] = (stem, os.path.join(folder, name))
    return found


# Blender keeps only pointers to the strings a dynamic enum returns, so the
# list has to outlive the callback or the labels turn to garbage.
_lighting_items = []


def lighting_preset_items(self, context):
    # Built-ins keep the numbers they had as a fixed enum (0, 1, 2, ...), so
    # files saved before presets could be added still open on their choice.
    # Saved ones get a number from their name, which stays put as others are
    # added and removed around them.
    items = [(k, v["label"], v["label"], i) for i, (k, v) in enumerate(LIGHTING_PRESETS.items())]
    for key, (label, path) in user_lighting_presets().items():
        items.append((key, label, f"Saved preset: {path}",
                      1000 + zlib.crc32(key.encode("utf-8")) % 1000000))
    _lighting_items[:] = items
    return _lighting_items


def lighting_specs(key):
    """The light list for a preset key, or None if it cannot be read."""
    if key in LIGHTING_PRESETS:
        return LIGHTING_PRESETS[key]["lights"]
    entry = user_lighting_presets().get(key)
    if entry is None:
        return None
    try:
        with open(entry[1], encoding="utf-8") as f:
            lights = json.load(f)["lights"]
        for spec in lights:
            Vector(spec["pos"])
            float(spec["energy"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return lights


class MV_Issue(PropertyGroup):
    severity: StringProperty()
    message: StringProperty()
    product: StringProperty()
    fix: StringProperty()


def _update_isolate(self, context):
    """Apply the isolate toggle the moment it is ticked, rather than waiting
    for the next rotate or step.

    Defined up here because the property below references it while the class
    body runs; the helpers it calls are resolved at call time, so they can live
    further down the file with the rest of the product code.
    """
    coll, _ = active_product(context)
    isolate_product(context, coll.name if (self.isolate_active and coll) else None)


def _update_active_product(self, context):
    """Picking a product in the render list makes it the one being oriented,
    so isolation follows the click the same way it follows Previous/Next."""
    if self.isolate_active:
        coll, _ = active_product(context)
        if coll is not None:
            isolate_product(context, coll.name)


def _update_view_set(self, context):
    """Copy a preset into the per-view checkboxes, so switching to Custom
    afterwards starts from the views you were just looking at rather than
    from a blank or stale selection."""
    if self.view_set == 'CUSTOM':
        return
    names = {v[0] for v in VIEW_SETS[self.view_set]}
    self.views_enabled = [v[0] in names for v in VIEWS_ALL]


class MV_Settings(PropertyGroup):
    step_files: CollectionProperty(type=MV_StepFileItem)
    step_files_index: IntProperty(default=0)

    view_set: EnumProperty(
        name="Views",
        items=[
            ("ALL",   "All",          "Front, Back, Top, Bottom, Right, Left, three perspectives"),
            ("ORTHO", "Orthographic", "Front, Back, Top, Bottom, Right, Left"),
            ("STD",   "Standard",     "Front, Top, Side, Perspective"),
            ("MIN",   "Minimal",      "Front, Top, Side"),
            ("CUSTOM", "Custom",      "Tick the views you want individually"),
        ],
        default="ALL",
        update=_update_view_set,
    )
    views_enabled: BoolVectorProperty(
        name="Views",
        description="Which of the standard views get a camera when View Set is Custom",
        size=len(VIEWS_ALL),
        default=(True,) * len(VIEWS_ALL),
    )

    front_axis: EnumProperty(
        name="Front Axis",
        description="World axis pointing out of the front of your product",
        items=[
            ('+X', "+X", "Front camera looks along -X (matches most CAD exports)"),
            ('-Y', "-Y", "Blender default"),
            ('+Y', "+Y", ""),
            ('-X', "-X", ""),
        ],
        default='+X',
    )

    lighting_preset: EnumProperty(
        name="Lighting",
        description="Light rig to build. Saved presets appear after the built-in ones",
        items=lighting_preset_items,
        default=0,
    )
    lighting_intensity: FloatProperty(
        name="Intensity",
        description="Multiplier on preset light energies",
        default=1.0, min=0.0, soft_max=5.0,
    )
    lights_follow_camera: BoolProperty(
        name="Lights Follow Camera",
        description="Turn the light rig with each camera while rendering, so every view "
                    "is lit the way Front is. Off, the lights stay put and views from "
                    "behind or below are lit mostly by the rim light",
        default=True,
    )

    world_mode: EnumProperty(
        name="Background",
        items=[('COLOR', "Color", "A flat colour behind the product"),
               ('HDRI', "HDRI", "An environment image that lights the product and, "
                                "optionally, shows behind it")],
        default='COLOR',
    )
    transparent_bg: BoolProperty(name="Transparent Background", default=False)
    bg_color: FloatVectorProperty(
        name="Background Color", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.5, 0.5, 0.5, 1.0),
    )
    hdri_path: StringProperty(
        name="HDRI", subtype='FILE_PATH',
        description="Environment image, usually .hdr or .exr",
    )
    hdri_strength: FloatProperty(name="Strength", default=1.0, min=0.0, soft_max=10.0)
    hdri_rotation: FloatProperty(
        name="Rotation", description="Turn the environment about the vertical axis",
        default=0.0, subtype='ANGLE',
    )
    hdri_visible: BoolProperty(
        name="Show HDRI",
        description="See the environment behind the product. Off, it still lights and "
                    "reflects in the product but the camera sees the background colour",
        default=False,
    )

    ground_mode: EnumProperty(
        name="Ground",
        description="Something for the product to stand on in Full renders",
        items=[('NONE', "None", "The product floats"),
               ('SHADOW', "Shadow Catcher", "An invisible floor that only shows the "
                                            "product's shadow. Cycles only"),
               ('FLOOR', "Floor", "A visible floor in the colour below")],
        default='NONE',
    )
    ground_color: FloatVectorProperty(
        name="Floor Color", subtype='COLOR', size=3,
        min=0.0, max=1.0, default=(0.8, 0.8, 0.8),
    )
    ground_roughness: FloatProperty(
        name="Roughness", description="Lower makes the floor reflect the product",
        default=0.5, min=0.0, max=1.0, subtype='FACTOR',
    )

    material_preset: EnumProperty(
        name="Material",
        description="Material every product renders with in Full renders, unless the "
                    "product picks its own",
        items=[('KEEP', "Keep Own", "Use the materials the products already have")]
              + MATERIAL_ITEMS,
        default='KEEP',
    )
    material_color: FloatVectorProperty(
        name="Color", subtype='COLOR', size=3,
        min=0.0, max=1.0, default=(0.8, 0.8, 0.8),
    )

    render_output_dir: StringProperty(
        name="Output Directory", subtype='DIR_PATH', default="//renders/",
    )
    render_mode: EnumProperty(
        name="Render Mode",
        items=[
            ('FULL', "Full Render", "Standard render using your current engine"),
            ('CLAY', "Clay (Workbench)", "Viewport-style clay render"),
            ('BOTH', "Both", "Save both a full render and a clay render"),
        ],
        default='CLAY',
    )
    clay_color: FloatVectorProperty(
        name="Clay Color", subtype='COLOR', size=3,
        min=0.0, max=1.0, default=(0.75, 0.75, 0.75),
    )
    pass_lines: BoolProperty(
        name="Line Art",
        description="Also write a technical-drawing image per view: outlines and creases "
                    "drawn as lines. Named with mode 'lines'",
        default=False,
    )
    pass_mask: BoolProperty(
        name="Mask",
        description="Also write a silhouette per view: white product on black. "
                    "Named with mode 'mask'",
        default=False,
    )
    pass_ao: BoolProperty(
        name="AO",
        description="Also write an ambient occlusion image per view: white product "
                    "darkened in its creases and contact areas. Needs Cycles. Named "
                    "with mode 'ao'",
        default=False,
    )
    lines_angle: FloatProperty(
        name="Crease Angle",
        description="Edges where faces meet more sharply than this are drawn",
        default=math.radians(30.0), min=math.radians(1.0), max=math.radians(179.0),
        subtype='ANGLE',
    )
    lines_width: IntProperty(name="Line Width", description="In pixels", default=2, min=1, max=12)
    lines_color: FloatVectorProperty(
        name="Line Color", subtype='COLOR', size=3,
        min=0.0, max=1.0, default=(0.0, 0.0, 0.0),
    )
    lines_fill: EnumProperty(
        name="Fill",
        items=[('WHITE', "White", "Black lines on white: a technical drawing"),
               ('CLAY', "Clay", "Lines drawn over the clay render"),
               ('NONE', "None", "Lines only, on transparency")],
        default='WHITE',
    )
    pass_depth: BoolProperty(
        name="Depth",
        description="Write a depth map per view: 32-bit EXR, distance along the view "
                    "axis in scene units. Needs Cycles. Mode 'depth'",
        default=False,
    )
    pass_normal: BoolProperty(
        name="Normals",
        description="Write a camera-space normal map per view: 32-bit EXR, OpenGL axes. "
                    "Needs Cycles. Mode 'normal'",
        default=False,
    )
    pass_parts: BoolProperty(
        name="Part IDs",
        description="Write a 16-bit PNG per view saying which part each pixel shows: 0 is "
                    "background, the rest number the parts as listed in cameras.json. "
                    "Needs Cycles. Mode 'parts'",
        default=False,
    )
    export_cameras: BoolProperty(
        name="Cameras",
        description="Write each product's camera intrinsics and poses (cameras.json) and "
                    "a nerfstudio-style transforms.json for its perspective views and "
                    "turntable",
        default=True,
    )
    export_coco: BoolProperty(
        name="COCO",
        description="Write coco.json with one instance mask per visible part per image. "
                    "Turns on Part IDs",
        default=False,
    )
    export_bop: BoolProperty(
        name="BOP",
        description="Write a BOP-format dataset (bop/) from the perspective views: RGB, "
                    "depth in mm, masks, object poses and models. Turns on Depth",
        default=False,
    )
    shard_suffix: StringProperty(
        description="Added to manifest, COCO and BOP model-info file names by the "
                    "command line, so shards rendered in parallel do not overwrite "
                    "each other's lists",
        default="", options={'HIDDEN'},
    )
    ao_samples: IntProperty(name="AO Samples", default=32, min=1, max=4096)
    ao_distance: FloatProperty(
        name="AO Distance",
        description="How far occlusion reaches, as a fraction of the product's size",
        default=0.5, min=0.001, soft_max=2.0,
    )
    preflight_on_render: BoolProperty(
        name="Check Before Rendering",
        description="Run the pre-flight check when Render All is pressed. Errors stop the "
                    "render; warnings ask before going ahead",
        default=True,
    )
    preflight_issues: CollectionProperty(type=MV_Issue)
    preflight_time: StringProperty()
    skip_existing: BoolProperty(
        name="Skip Existing",
        description="Leave images that are already in the output folder alone and "
                    "render only the missing ones. Use it to resume a batch that "
                    "crashed or was cancelled. Turn it off to overwrite after "
                    "changing a setting",
        default=False,
    )
    reframe_on_render: BoolProperty(
        name="Reframe Before Rendering",
        description="Rebuild the cameras from the current view settings and product "
                    "positions when a render starts, so rotating a product or changing "
                    "resolution never leaves a stale framing. Turn off to keep cameras "
                    "you have adjusted by hand",
        default=True,
    )

    file_template: StringProperty(
        name="File Name",
        description="Name of each image, without extension. Tokens: {label} (AA_01), "
                    "{prefix} (AA), {number} (01), {product}, {view}, {mode} (render, "
                    "clay, or nothing for Full Render). A token that comes out empty "
                    "takes one separator next to it with it",
        default="{label}_{product}_{view}_{mode}",
    )
    folder_template: StringProperty(
        name="Folder",
        description="Folder each image goes in, under the output directory. Same tokens "
                    "as the file name; use / to nest folders, or leave empty to put "
                    "everything straight in the output directory",
        default="{label}_{product}",
    )

    sheet_enabled: BoolProperty(
        name="Contact Sheet",
        description="After each product, lay all its views out on one labelled image",
        default=False,
    )
    sheet_columns: IntProperty(
        name="Columns",
        description="Views per row. 0 picks a roughly square grid",
        default=0, min=0, max=16,
    )
    sheet_cell_width: IntProperty(
        name="Cell Width",
        description="Width in pixels each view is scaled to on the sheet",
        default=512, min=64, max=4096,
    )
    sheet_labels: BoolProperty(
        name="Labels",
        description="Print the product name across the top and the view name under each image",
        default=True,
    )
    sheet_bg: FloatVectorProperty(
        name="Background", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(1.0, 1.0, 1.0, 1.0),
    )
    sheet_text_color: FloatVectorProperty(
        name="Text", subtype='COLOR', size=3,
        min=0.0, max=1.0, default=(0.1, 0.1, 0.1),
    )

    turntable_enabled: BoolProperty(
        name="Turntable",
        description="Also render each product spinning a full turn, one frame per step",
        default=False,
    )
    turntable_frames: IntProperty(
        name="Frames",
        description="Frames in one full turn",
        default=36, min=4, max=720,
    )
    turntable_elevation: FloatProperty(
        name="Elevation",
        description="How far above the product the turntable camera looks down from",
        default=math.radians(20.0), min=math.radians(-89.0), max=math.radians(89.0),
        subtype='ANGLE',
    )
    turntable_style: EnumProperty(
        name="Style",
        items=[('CLAY', "Clay", "Fast Workbench clay, like the clay stills"),
               ('FULL', "Full Render", "Your current engine and materials")],
        default='CLAY',
    )
    turntable_mp4: BoolProperty(
        name="MP4",
        description="Encode the frames into an H.264 video",
        default=True,
    )
    turntable_gif: BoolProperty(
        name="GIF",
        description="Encode the frames into a looping animated GIF",
        default=False,
    )
    turntable_fps: IntProperty(name="FPS", default=24, min=1, max=60)
    turntable_gif_size: IntProperty(
        name="GIF Size",
        description="Longest edge of the GIF in pixels. GIFs get large fast",
        default=480, min=64, max=2048,
    )

    post_enabled: BoolProperty(
        name="Post-Processing",
        description="Write a processed copy of every image: trimmed, padded, resized "
                    "or converted. The original renders are kept as they are",
        default=False,
    )
    post_folder: StringProperty(
        name="Folder",
        description="Subfolder of the output directory the processed copies go in. "
                    "It mirrors the folder layout of the originals",
        default="processed",
    )
    post_trim: BoolProperty(
        name="Trim to Content",
        description="Crop away the empty background around the product. Each image "
                    "then fills its own frame, so views no longer share one scale",
        default=False,
    )
    post_margin: FloatProperty(
        name="Margin",
        description="Space left around the product after trimming, as a fraction of its size",
        default=0.05, min=0.0, max=0.5, subtype='FACTOR',
    )
    post_square: BoolProperty(
        name="Pad to Square",
        description="Extend the shorter side with background so the image is square",
        default=False,
    )
    post_flatten: BoolProperty(
        name="Flatten Transparency",
        description="Put transparent renders on a solid colour. JPEG always does this",
        default=False,
    )
    post_bg_color: FloatVectorProperty(
        name="Flatten Color", subtype='COLOR', size=3,
        min=0.0, max=1.0, default=(1.0, 1.0, 1.0),
    )
    post_format: EnumProperty(
        name="Format",
        items=[('PNG', "PNG", "Lossless, keeps transparency"),
               ('JPEG', "JPEG", "Small, no transparency"),
               ('WEBP', "WebP", "Small, keeps transparency")],
        default='PNG',
    )
    post_quality: IntProperty(
        name="Quality", description="JPEG and WebP quality",
        default=90, min=1, max=100, subtype='PERCENTAGE',
    )
    post_max_size: IntProperty(
        name="Max Size",
        description="Shrink so the longest edge is at most this many pixels. 0 keeps the size",
        default=0, min=0, max=16384,
    )
    post_extra_sizes: StringProperty(
        name="Extra Sizes",
        description="Also write smaller copies with these longest edges, e.g. '1024, 256'. "
                    "Each gets the size added to its name: AA_01_Widget_Front_256",
        default="",
    )

    manifest_format: EnumProperty(
        name="Manifest",
        description="List every output with its product, view, size and source file, "
                    "in the output directory",
        items=[('NONE', "None", "Do not write a manifest"),
               ('CSV', "CSV", "manifest.csv"),
               ('JSON', "JSON", "manifest.json"),
               ('BOTH', "CSV + JSON", "manifest.csv and manifest.json")],
        default='BOTH',
    )

    start_prefix: StringProperty(
        name="Start Prefix",
        description="Letter the first product group is labelled with. The "
                    "label repeats it (AA, BB, ...), so only the first "
                    "character is read -- typing AB gives AA",
        default="AA", maxlen=3,
    )
    start_number: IntProperty(
        name="Start Number",
        description="Number for the first product in this batch (1-50)",
        default=1, min=1, max=50,
    )
    products_per_letter: IntProperty(
        name="Products per Letter",
        description="Bump to the next letter pair after this many products",
        default=50, min=1, max=999,
    )

    frame_padding_factor: FloatProperty(
        name="Framing Padding", default=1.4, min=1.0, max=5.0,
    )

    custom_views: CollectionProperty(type=MV_CustomView)
    custom_views_index: IntProperty(default=0)

    recenter: BoolProperty(
        name="Recenter",
        description="Move each product's bounding box centre onto the world origin, "
                    "keeping its parts in their relative positions",
        default=True,
    )
    rescale: BoolProperty(
        name="Rescale",
        description="Uniformly scale every product to fit inside a cube of Target Size",
        default=True,
    )
    target_size: FloatProperty(
        name="Target Size",
        description="Max dimension (m) each product is scaled to fit within",
        default=1.0, min=0.0001, soft_max=10.0,
    )
    auto_smooth: BoolProperty(
        name="Auto Smooth",
        description="Clear the sharp edges and split normals a CAD tessellation "
                    "imports with, then shade smooth under the angle threshold",
        default=True,
    )
    smooth_angle: FloatProperty(
        name="Smooth Angle",
        description="Faces meeting at a sharper angle than this keep a hard edge",
        default=math.radians(30.0), min=0.0, max=math.radians(180.0),
        subtype='ANGLE',
    )
    scale_mode: EnumProperty(
        name="Scale",
        items=[('FIT', "Fit Each", "Every product is scaled to Target Size, so all of them "
                                   "fill the frame the same"),
               ('RELATIVE', "Keep Proportions", "The biggest product is scaled to Target "
                                                "Size and the rest keep their real size "
                                                "relative to it")],
        default='FIT',
    )
    rest_on_floor: BoolProperty(
        name="Rest on Floor",
        description="Recenter puts the bottom of each product at the origin instead of "
                    "its middle, so it stands on the ground",
        default=False,
    )
    mesh_units: EnumProperty(
        name="Mesh Units",
        description="Unit the numbers in STL, OBJ, PLY, glTF and FBX files are in. Only "
                    "used to report real sizes and to scale products against each "
                    "other; STEP, IGES and 3MF know their own",
        items=UNIT_ITEMS,
        default='mm',
    )
    orient_method: EnumProperty(
        name="Method",
        items=[('FLAT', "Lay Flat", "Rest the product on its largest flat face, longest "
                                    "side across the Front view"),
               ('PCA', "Principal Axes", "Line the product's longest spread up across the "
                                         "Front view and its thinnest upright. Better for "
                                         "rounded shapes with no flat face")],
        default='FLAT',
    )
    fit_on_import: BoolProperty(
        name="Fit on Import",
        description="Straight after importing, scale each product to fit inside a cube of "
                    "Target Size and centre it on the world origin",
        default=True,
    )

    show_products_list: BoolProperty(default=False)

    active_product_index: IntProperty(
        name="Active Product",
        description="Which product the orientation buttons and Render Active act on",
        default=0, min=0,
        update=_update_active_product,
    )
    isolate_active: BoolProperty(
        name="Isolate Active Product",
        description="Show only the product being oriented and hide the rest. "
                    "Batch renders are unaffected either way",
        default=True,
        update=_update_isolate,
    )
    rotate_step: FloatProperty(
        name="Rotate Step",
        description="How far one press of Left/Right/Up/Down turns the product",
        default=math.radians(90.0),
        min=math.radians(1.0), max=math.radians(180.0),
        subtype='ANGLE',
    )


def ensure_collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def get_products_root():
    """The MV_Products collection, created if it is not there yet.

    Only for operators. Panels read the products with get_products(), which
    never creates anything: draw() runs on every redraw, so reaching for the
    root here linked an MV_Products collection into the scene merely because
    someone opened the sidebar, and left their file marked as modified for it.
    """
    return ensure_collection(PRODUCT_COLL)


def get_products():
    """Product collections, or [] when the root does not exist yet.

    Read-only on purpose -- see get_products_root().
    """
    root = bpy.data.collections.get(PRODUCT_COLL)
    return list(root.children) if root else []


def stray_render_objects(context):
    """Renderable geometry that belongs to no product.

    Render All hides the other products while each one is photographed, but
    anything outside MV_Products is left standing in shot. Most often that is
    Blender's startup cube: two metres across, parked on the world origin
    exactly where a fitted product lands, and big enough to swallow it whole.
    The renders come back looking blank and the cause is nowhere near the
    add-on's settings.

    Objects already switched off for rendering are not reported, by their own
    toggle or by every collection holding them. Someone who parked a backdrop
    and disabled it meant to do that, and a warning that fires on deliberate
    staging is one people learn to scroll past.

    Read-only, and reaches for get_products() rather than get_products_root():
    this runs from draw(), which must not create anything.
    """
    products = set()
    for pc in get_products():
        products.update(pc.all_objects)
    # The ground is the add-on's own, placed under each product on purpose.
    stage = bpy.data.collections.get(STAGE_COLL)
    if stage:
        products.update(stage.all_objects)

    strays = []
    for obj in context.view_layer.objects:
        # Straight after objects are deleted the view layer can still list a
        # slot for them, empty until it next resyncs.
        if obj is None or obj.type not in GEOMETRY_TYPES or obj in products or obj.hide_render:
            continue
        # An object linked into several collections still renders as long as
        # one of them is on, so this takes all() rather than any().
        holders = obj.users_collection
        if holders and all(c.hide_render for c in holders):
            continue
        strays.append(obj)
    return strays


def bbox_of(objs):
    lo = Vector((float("inf"),) * 3)
    hi = Vector((float("-inf"),) * 3)
    for o in objs:
        if o.type not in GEOMETRY_TYPES:
            continue
        for corner in o.bound_box:
            world = o.matrix_world @ Vector(corner)
            for i in range(3):
                if world[i] < lo[i]: lo[i] = world[i]
                if world[i] > hi[i]: hi[i] = world[i]
    if lo.x == float("inf"):
        return Vector((0, 0, 0)), Vector((1, 1, 1))
    return (lo + hi) * 0.5, hi - lo


def rotate_dir_z(vec, degrees):
    theta = math.radians(degrees)
    c, s = math.cos(theta), math.sin(theta)
    x, y, z = vec
    return (x * c - y * s, x * s + y * c, z)


def look_at(location, target, up=Vector((0, 0, 1))):
    forward = (target - location).normalized()
    z = -forward
    if abs(z.dot(up)) > 0.999:
        up = Vector((0, 1, 0))
    x = up.cross(z).normalized()
    y = z.cross(x).normalized()
    return Matrix((
        (x.x, y.x, z.x, location.x),
        (x.y, y.y, z.y, location.y),
        (x.z, y.z, z.z, location.z),
        (0.0, 0.0, 0.0, 1.0),
    ))


def clear_collection_objects(coll):
    """Remove a collection's objects along with the data they leave behind.

    objects.remove() drops the object but not its camera or light datablock, so
    every rebuild of the rig orphaned another set and the next one came back as
    MV_Cam_Front.001, .002, ... The file kept growing until a save and reload
    purged them. Data another object still uses, or that is pinned with a fake
    user, is left alone.
    """
    if coll is None:
        return
    for obj in list(coll.objects):
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is None or data.users or data.use_fake_user:
            continue
        if isinstance(data, bpy.types.Camera):
            bpy.data.cameras.remove(data)
        elif isinstance(data, bpy.types.Light):
            bpy.data.lights.remove(data)
        elif isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)


def collection_meshes(coll):
    return [o for o in coll.all_objects if o.type in GEOMETRY_TYPES]


def collection_roots(coll):
    """Objects in coll whose parent lives outside it. Transforming these moves
    the whole assembly once; children follow through their parent."""
    members = set(coll.all_objects)
    return [o for o in members if o.parent is None or o.parent not in members]


IDENTITY_16 = tuple(float(i % 5 == 0) for i in range(16))


def product_to_world(coll):
    """Matrix taking the product's source coordinates (as imported, in its
    source units) to where it sits in the scene now."""
    m = coll.mv_to_world
    return Matrix([m[i * 4:i * 4 + 4] for i in range(4)])


def move_product(coll, xform):
    """Apply a world-space transform to a whole product, and fold it into the
    product's source-to-world record.

    Every move MultiView makes goes through here -- fitting, recentring,
    turning, auto-orienting -- so the record stays exact, and a pixel in any
    render can be traced back to a point in the original CAD file. Baking does
    not move geometry, so it needs no entry. Moves made by hand in the
    viewport are not seen.
    """
    for obj in collection_roots(coll):
        obj.matrix_world = xform @ obj.matrix_world
    total = xform @ product_to_world(coll)
    coll.mv_to_world = [v for row in total for v in row]


def fit_collection(coll, target_size=None, recenter=True, floor=False):
    """Uniformly scale a product so its bounding box fits inside a cube of
    target_size, and optionally move that box onto the world origin.

    Pass target_size=None to only recenter. With floor, recentering puts the
    bottom of the box on the origin rather than its middle, so the product
    stands on the ground plane instead of straddling it. Returns False if the
    collection holds no geometry. The whole product is treated as one rigid
    assembly, so parts keep their relative positions.
    """
    objs = collection_meshes(coll)
    if not objs:
        return False

    center, size = bbox_of(objs)
    factor = 1.0
    if target_size:
        max_dim = max(size.x, size.y, size.z)
        if max_dim > 1e-9:
            factor = target_size / max_dim

    if not recenter:
        dest = center
    elif floor:
        dest = Vector((0.0, 0.0, size.z * factor * 0.5))
    else:
        dest = Vector((0.0, 0.0, 0.0))
    if abs(factor - 1.0) < 1e-9 and (dest - center).length < 1e-9:
        return True

    xform = (Matrix.Translation(dest)
             @ Matrix.Scale(factor, 4)
             @ Matrix.Translation(-center))
    move_product(coll, xform)
    return True


def record_source_size(coll, units):
    """Remember how big a product really is, before anything rescales it.

    Called at import, and by Standardize for products assembled by hand,
    which are measured the first time they are rescaled. Never overwrites a
    size already recorded, since by then the product may have been scaled.
    """
    if any(coll.mv_source_size):
        return
    meshes = collection_meshes(coll)
    if meshes:
        coll.mv_source_size = bbox_of(meshes)[1]
        coll.mv_source_units = units


def real_extent_mm(coll):
    """Largest dimension of the product as imported, in millimetres, or None."""
    size = max(coll.mv_source_size)
    if size <= 0:
        return None
    return size * UNIT_TO_MM.get(coll.mv_source_units, 1.0)


def format_real_size(coll):
    size = coll.mv_source_size
    if not any(size):
        return None
    unit = coll.mv_source_units or "units"
    return " x ".join(f"{v:.4g}" for v in size) + f" {unit}"


def scale_targets(settings, products):
    """The size each product's largest dimension should be scaled to.

    Fit Each gives every product Target Size, which is what makes a screw and
    a housing read the same in the renders. Keep Proportions gives the batch
    one scale instead: the biggest product gets Target Size and the rest keep
    their real size relative to it, so a screw stays a fraction of a housing.
    A product with no recorded size cannot be placed on that scale and falls
    back to Target Size.
    """
    target = settings.target_size
    if settings.scale_mode != 'RELATIVE':
        return {pc.name: target for pc in products}
    extents = {pc.name: real_extent_mm(pc) for pc in products}
    biggest = max((e for e in extents.values() if e), default=None)
    return {name: (target * e / biggest if e and biggest else target)
            for name, e in extents.items()}


def standardize_products(context, products, scale=True, recenter=True):
    """Scale and/or recenter products and bake the result. Returns the names
    of objects whose transform could not be baked."""
    s = context.scene.mv_settings
    for pc in products:
        # Hand-built products are in Blender units, which are metres.
        record_source_size(pc, "m")
    targets = scale_targets(s, products) if scale else {}
    unbaked = set()
    context.view_layer.update()
    for pc in products:
        if fit_collection(pc, targets.get(pc.name), recenter=recenter, floor=s.rest_on_floor):
            _, skipped = bake_product(pc, apply_scale=scale, origin_to_world=recenter)
            unbaked.update(skipped)
    context.view_layer.update()
    return unbaked


# -- orientation ------------------------------------------------------------

HOME_KEY = "mv_home_rotation"


def remember_home(coll):
    """Record each root's rotation as the product's home orientation, unless
    one is recorded already. Reset Orientation returns the product to it."""
    roots = collection_roots(coll)
    if any(HOME_KEY in o for o in roots):
        return
    for obj in roots:
        obj[HOME_KEY] = list(obj.matrix_world.to_quaternion())


def turn_product(coll, rotation):
    """Rotate a product rigidly about its own bounding box centre."""
    objs = collection_meshes(coll)
    if not objs:
        return False
    center, _ = bbox_of(objs)
    xform = (Matrix.Translation(center) @ rotation.to_4x4() @ Matrix.Translation(-center))
    move_product(coll, xform)
    return True


def reset_orientation(coll):
    """Turn a product back to the orientation it had when imported. False if
    no home was ever recorded for it."""
    roots = [o for o in collection_roots(coll) if HOME_KEY in o]
    if not roots:
        return False
    home = Quaternion(roots[0][HOME_KEY])
    now = roots[0].matrix_world.to_quaternion()
    # Every root turned together, so undoing one root's turn undoes them all.
    return turn_product(coll, (home @ now.inverted()).to_matrix())


def world_triangles(coll):
    """(n, 3, 3) array of the product's triangles in world space."""
    chunks = []
    for obj in collection_meshes(coll):
        if obj.type != 'MESH' or not len(obj.data.polygons):
            continue
        me = obj.data
        me.calc_loop_triangles()
        co = np.empty(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get("co", co)
        idx = np.empty(len(me.loop_triangles) * 3, np.int64)
        me.loop_triangles.foreach_get("vertices", idx)
        m = np.array(obj.matrix_world)
        world = co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]
        chunks.append(world[idx.reshape(-1, 3)])
    return np.concatenate(chunks) if chunks else None


def front_axes(settings):
    """World directions of the Front view: across it, and towards its camera."""
    angle = FRONT_AXIS_ANGLES[settings.front_axis]
    return (np.array(rotate_dir_z((1.0, 0.0, 0.0), angle)),
            np.array(rotate_dir_z((0.0, -1.0, 0.0), angle)))


def sample_points(tris, limit=20000):
    pts = tris.reshape(-1, 3)
    if len(pts) > limit:
        pts = pts[np.linspace(0, len(pts) - 1, limit).astype(np.int64)]
    return pts


def flat_rotation(tris):
    """Rotation that lays the product on its largest flat face.

    Triangles are grouped by the way they face, to within a few degrees, and
    the group with the most area wins: for a box that is a large side, for a
    phone its back. That face is turned to point straight down.
    """
    cross = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    area = np.linalg.norm(cross, axis=1)
    keep = area > 1e-12
    normals = cross[keep] / area[keep, None]
    area = area[keep]
    if not len(area):
        return Matrix.Identity(3)
    keys, inverse = np.unique(np.round(normals * 24).astype(np.int64), axis=0,
                              return_inverse=True)
    inverse = inverse.reshape(-1)
    best = np.argmax(np.bincount(inverse, weights=area))
    n = (normals[inverse == best] * area[inverse == best, None]).sum(axis=0)
    n /= max(np.linalg.norm(n), 1e-12)
    return Vector(n).rotation_difference(Vector((0.0, 0.0, -1.0))).to_matrix()


def convex_hull_2d(points):
    """Andrew's monotone chain, counter-clockwise, no repeated end point."""
    pts = [tuple(p) for p in np.unique(np.round(points, 9), axis=0)]
    if len(pts) < 3:
        return np.array(pts)

    def half(seq):
        chain = []
        for p in seq:
            while len(chain) >= 2 and (
                    (chain[-1][0] - chain[-2][0]) * (p[1] - chain[-2][1])
                    - (chain[-1][1] - chain[-2][1]) * (p[0] - chain[-2][0])) <= 0:
                chain.pop()
            chain.append(p)
        return chain

    lower, upper = half(pts), half(reversed(pts))
    return np.array(lower[:-1] + upper[:-1])


def footprint_rotation(points, across):
    """Turn about the vertical so the product's footprint lines up with the
    axes, longest side across the Front view.

    The smallest rectangle around a shape always has a side along one of its
    convex hull's edges, so only those angles need trying, and the answer is
    exact rather than the nearest step of a sweep.
    """
    xy = points[:, :2] - points[:, :2].mean(axis=0)
    hull = convex_hull_2d(xy)
    if len(hull) < 3:
        hull = xy
    edges = np.roll(hull, -1, axis=0) - hull
    candidates = np.unique(np.round(np.mod(-np.arctan2(edges[:, 1], edges[:, 0]),
                                           math.pi / 2), 9))
    best_angle, best_area = 0.0, float("inf")
    for angle in candidates:
        c, s = math.cos(angle), math.sin(angle)
        x = hull[:, 0] * c - hull[:, 1] * s
        y = hull[:, 0] * s + hull[:, 1] * c
        area = np.ptp(x) * np.ptp(y)
        if area < best_area - 1e-12:
            best_angle, best_area = float(angle), area
    turn = Matrix.Rotation(best_angle, 3, 'Z')
    turned = np.asarray(xy) @ np.array(turn)[:2, :2].T
    # Extent along the direction across the Front view, against the other way.
    along = np.ptp(turned @ across[:2])
    other = np.ptp(turned @ np.array((-across[1], across[0])))
    if along < other:
        turn = Matrix.Rotation(best_angle + math.pi / 2, 3, 'Z')
    return turn


def principal_rotation(points, across, towards):
    """Rotation that puts the product's longest spread across the Front view,
    its next longest pointing at the Front camera, and its thinnest upright."""
    centered = points - points.mean(axis=0)
    _, vectors = np.linalg.eigh(np.cov(centered.T))
    small, middle, large = vectors[:, 0], vectors[:, 1], vectors[:, 2]
    source = np.column_stack([large, middle, small])
    target = np.column_stack([across, towards, (0.0, 0.0, 1.0)])
    rot = target @ source.T
    if np.linalg.det(rot) < 0:
        source[:, 1] *= -1
        rot = target @ source.T
    return Matrix(rot.tolist())


def auto_orient(context, coll, method):
    """Turn a product to a sensible resting orientation. False if it has no
    mesh to measure."""
    tris = world_triangles(coll)
    if tris is None or not len(tris):
        return False
    remember_home(coll)
    across, towards = front_axes(context.scene.mv_settings)
    points = sample_points(tris)
    if method == 'PCA':
        rot = principal_rotation(points, across, towards)
    else:
        lay = flat_rotation(tris)
        laid = points @ np.array(lay).T
        rot = footprint_rotation(laid, across) @ lay
    turn_product(coll, rot)
    context.view_layer.update()
    return True


def parent_depth(obj):
    depth, parent = 0, obj.parent
    while parent is not None:
        depth += 1
        parent = parent.parent
    return depth


def push_empty_scale_down(coll):
    """Empties can carry scale but hold no data to bake it into, so a parented
    assembly would keep its fit scale stuck on the root.

    Walk the hierarchy top-down clearing each empty's scale while pinning its
    children's world matrices, which slides the scale onto the meshes at the
    leaves where transform_apply can reach it.
    """
    empties = [o for o in coll.all_objects if o.type == 'EMPTY']
    for empty in sorted(empties, key=parent_depth):
        if all(abs(v - 1.0) < 1e-9 for v in empty.scale):
            continue
        bpy.context.view_layer.update()
        pinned = [(c, c.matrix_world.copy()) for c in empty.children]
        empty.scale = (1.0, 1.0, 1.0)
        bpy.context.view_layer.update()
        for child, world in pinned:
            child.matrix_world = world


def bake_product(coll, apply_scale=True, origin_to_world=True):
    """Fold a fitted product's transform into its data: scale values back to
    1.0, and every object origin parked on the world origin.

    Geometry does not move -- this only changes where the transform is stored,
    so the product keeps the position and size fit_collection gave it while
    reporting clean values in the N panel.

    Blender refuses to edit multi-user or linked data, so those objects are
    returned as skipped rather than silently half-processed.
    """
    ctx = bpy.context
    members = collection_meshes(coll)
    if not members:
        return [], []
    if ctx.mode != 'OBJECT':
        return [], [o.name for o in members]

    editable = [o for o in members
                if o.name in ctx.view_layer.objects
                and o.library is None
                and o.data is not None
                and o.data.library is None
                and o.data.users == 1]
    skipped = [o.name for o in members if o not in editable]
    if not editable:
        return [], skipped

    if apply_scale:
        push_empty_scale_down(coll)

    ctx.view_layer.update()
    cursor = ctx.scene.cursor
    saved_cursor = cursor.location.copy()
    cursor.location = (0.0, 0.0, 0.0)
    try:
        with ctx.temp_override(active_object=editable[0], object=editable[0],
                               selected_objects=editable,
                               selected_editable_objects=editable):
            if apply_scale:
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            if origin_to_world:
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    finally:
        cursor.location = saved_cursor
    return [o.name for o in editable], skipped


def smooth_product(coll, angle):
    """Give a tessellated CAD import the shading it should have had.

    A STEP tessellation arrives faceted twice over: FreeCAD writes per-face
    normals that Blender keeps as custom split normals, and some Blender
    versions additionally mark most edges sharp on import. Either one pins the
    flat look no matter what shading you ask for, which is why the fix needs
    clearing before smoothing rather than smoothing alone.

    Sharpness is then re-derived from the angle between neighbouring faces and
    baked into the mesh, rather than left to a Smooth by Angle modifier: a
    batch here runs to millions of triangles and the modifier would be
    re-evaluated on every render.

    Returns (done, skipped) name lists.
    """
    ctx = bpy.context
    meshes = [o for o in collection_meshes(coll) if o.type == 'MESH']
    if not meshes:
        return [], []
    if ctx.mode != 'OBJECT':
        return [], [o.name for o in meshes]

    editable = [o for o in meshes
                if o.name in ctx.view_layer.objects
                and o.library is None
                and o.data is not None
                and o.data.library is None]
    skipped = [o.name for o in meshes if o not in editable]
    if not editable:
        return [], skipped

    for obj in editable:
        me = obj.data
        if me.has_custom_normals:
            try:
                with ctx.temp_override(object=obj, active_object=obj,
                                       selected_objects=[obj],
                                       selected_editable_objects=[obj]):
                    bpy.ops.mesh.customdata_custom_splitnormals_clear()
            except Exception:
                pass
        if len(me.edges):
            me.edges.foreach_set("use_edge_sharp", [False] * len(me.edges))
        if len(me.polygons):
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.update()

    with ctx.temp_override(object=editable[0], active_object=editable[0],
                           selected_objects=editable,
                           selected_editable_objects=editable):
        if hasattr(bpy.ops.object, "shade_smooth_by_angle"):
            bpy.ops.object.shade_smooth_by_angle(angle=angle)
        else:
            # Blender 4.0 kept auto smooth as a mesh property instead.
            try:
                bpy.ops.object.shade_smooth(use_auto_smooth=True,
                                            auto_smooth_angle=angle)
            except TypeError:
                bpy.ops.object.shade_smooth()
                for obj in editable:
                    if hasattr(obj.data, "use_auto_smooth"):
                        obj.data.use_auto_smooth = True
                        obj.data.auto_smooth_angle = angle
    return [o.name for o in editable], skipped


def find_layer_coll(layer_coll, name):
    if layer_coll.collection.name == name:
        return layer_coll
    for child in layer_coll.children:
        found = find_layer_coll(child, name)
        if found:
            return found
    return None


def isolate_product(context, name):
    """Show one product and exclude the rest from the view layer.

    Deliberately the same mechanism Render All uses rather than a viewport-only
    hide, so stepping through products previews exactly what a batch will
    render. Pass name=None to bring everything back.
    """
    for pc in get_products():
        lc = find_layer_coll(context.view_layer.layer_collection, pc.name)
        if lc:
            lc.exclude = name is not None and pc.name != name


def active_product(context):
    """The product the orientation buttons act on, or None if there are none.

    The stored index is clamped rather than trusted: products get deleted from
    the outliner behind the add-on's back, and a stale index would otherwise
    raise the moment someone pressed Rotate.
    """
    products = get_products()
    if not products:
        return None, -1
    idx = min(max(context.scene.mv_settings.active_product_index, 0), len(products) - 1)
    return products[idx], idx


def view_right_axis(context):
    """World-space axis that reads as horizontal in the camera being used.

    Up and Down tip the product about whatever is horizontal on screen, so the
    buttons behave the same whether you are looking through Front or Top. Falls
    back to world Y when no camera exists to ask.
    """
    cam = context.scene.camera
    if cam is None or cam.type != 'CAMERA':
        cam_coll = bpy.data.collections.get(CAMERA_COLL)
        cams = [o for o in cam_coll.objects if o.type == 'CAMERA'] if cam_coll else []
        cam = cams[0] if cams else None
    if cam is None:
        return Vector((0.0, 1.0, 0.0))
    axis = cam.matrix_world.col[0].xyz
    return axis.normalized() if axis.length > 1e-9 else Vector((0.0, 1.0, 0.0))


def rotate_product(context, coll, direction, step):
    """Turn one product in place, as seen from the current view.

    Left and Right spin about world Z, which is the turntable move that fixes a
    product facing the wrong way. Up and Down tip about the view's horizontal
    axis. Rotation happens around the product's own bounding box centre so it
    does not drift out of frame, and is applied to the collection roots so a
    multi-part assembly turns as one rigid body.
    """
    objs = collection_meshes(coll)
    if not objs:
        return False
    center, _ = bbox_of(objs)
    if direction in {'LEFT', 'RIGHT'}:
        axis = Vector((0.0, 0.0, 1.0))
        angle = -step if direction == 'LEFT' else step
    else:
        axis = view_right_axis(context)
        angle = -step if direction == 'UP' else step
    xform = (Matrix.Translation(center)
             @ Matrix.Rotation(angle, 4, axis)
             @ Matrix.Translation(-center))
    move_product(coll, xform)
    return True


def alpha_pair(idx):
    """Repeated-letter group label: AA..ZZ, then AAA..ZZZ, then AAAA..

    The letter cycles every 26 groups and the label grows a character on each
    wrap, so no two indices share a label. The width has to key off the wrap
    count -- an earlier version restarted at two letters after ZZ, which handed
    index 26 the same 'AA' as index 0 and pointed two products at one output
    folder, where the second silently overwrote the first.
    """
    idx = max(0, idx)
    return chr(ord('A') + idx % 26) * (2 + idx // 26)


def alpha_pair_to_idx(prefix):
    prefix = (prefix or "AA").strip().upper()
    if not prefix:
        return 0
    return max(0, ord(prefix[0]) - ord('A'))


def label_index(position, coll):
    """Where a product's label is counted from: its own recorded index when
    the command line has set one, otherwise its place in MV_Products."""
    fixed = getattr(coll, "mv_label_index", -1)
    return fixed if fixed >= 0 else position


def product_label(start_prefix, start_number, offset, per_letter):
    base = alpha_pair_to_idx(start_prefix)
    linear = (max(1, start_number) - 1) + offset
    bumps = linear // per_letter
    num = (linear % per_letter) + 1
    return f"{alpha_pair(base + bumps)}_{num:02d}"


# Characters Windows refuses outright, plus the separators that would quietly
# redirect a write into some other directory.
BAD_PATH_CHARS = '<>:"/\\|?*'
RESERVED_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def safe_name(name, fallback="unnamed"):
    """A collection or view name reduced to one usable path component.

    These names are free text and usually arrive from a STEP filename, so they
    carry whatever the CAD export happened to contain. A trailing space is the
    one that bites: asked for 'BICON ', Windows quietly creates 'BICON', then
    refuses to write 'BICON \\shot.png' because that directory really does not
    exist, and the render dies on the first product with 'cannot save'. The
    mismatch hides well, because os.path.isdir strips the same trailing space
    on the way in and cheerfully agrees the folder is there.
    """
    cleaned = "".join(
        "_" if c in BAD_PATH_CHARS or ord(c) < 32 else c for c in str(name)
    )
    # The name we ask for has to match the name the filesystem will hand back,
    # or every later write into it misses.
    cleaned = cleaned.strip().rstrip(" .")
    if cleaned.split(".")[0].upper() in RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned or fallback


STEP_EXTENSIONS = {".step", ".stp"}
IGES_EXTENSIONS = {".iges", ".igs"}
CAD_EXTENSIONS = STEP_EXTENSIONS | IGES_EXTENSIONS

# Each format lists its importers newest first. Blender has renamed several
# of them (4.2 replaced the Python STL importer with a C++ one under a new
# name), and calling an operator Blender does not have raises rather than
# returning, so a missing name just falls through to the next.
#
# Axes are spelled out only for STL and PLY, which have no up axis of their
# own and come out of CAD Z-up: forward Y / up Z is the identity mapping, and
# it is passed explicitly rather than trusting an importer default to stay
# put. OBJ, glTF and FBX carry or imply their own up axis, and the importers'
# defaults already convert it.
MESH_IMPORTERS = {
    ".stl": (("wm.stl_import", {"forward_axis": 'Y', "up_axis": 'Z'}),
             ("import_mesh.stl", {"axis_forward": 'Y', "axis_up": 'Z'})),
    ".ply": (("wm.ply_import", {"forward_axis": 'Y', "up_axis": 'Z'}),
             ("import_mesh.ply", {})),
    ".obj": (("wm.obj_import", {}), ("import_scene.obj", {})),
    ".gltf": (("import_scene.gltf", {}),),
    ".glb": (("import_scene.gltf", {}),),
    ".fbx": (("import_scene.fbx", {}),),
}
MESH_EXTENSIONS = set(MESH_IMPORTERS) | {".3mf"}
SUPPORTED_EXTENSIONS = CAD_EXTENSIONS | MESH_EXTENSIONS
FILE_FILTER = ";".join(f"*{e};*{e.upper()}" for e in sorted(SUPPORTED_EXTENSIONS))

# Imported alongside the geometry by glTF and FBX, but a camera or lamp inside
# a product would light or frame every render of it.
NON_PRODUCT_TYPES = {'CAMERA', 'LIGHT', 'LIGHT_PROBE', 'SPEAKER'}

def file_ext(path):
    return os.path.splitext(path)[1].lower()


def run_importer(candidates, path):
    """True only on a real success from the first importer Blender has."""
    for op_path, axes in candidates:
        module, func = op_path.split(".", 1)
        mod = getattr(bpy.ops, module, None)
        op = getattr(mod, func, None) if mod else None
        if op is None:
            continue
        try:
            try:
                return 'FINISHED' in op(filepath=path, **axes)
            except TypeError:
                return 'FINISHED' in op(filepath=path)
        except Exception:
            continue
    return False


def import_mesh_file(path):
    """Import a mesh file straight into the scene: (success, units or None).

    A mesh needs neither STEPper nor the FreeCAD round trip a STEP file goes
    through. Everything after this point -- the product collection, fitting,
    standardizing, rendering -- treats what lands here exactly like a
    converted STEP file. Only 3MF says what unit it is in.
    """
    ext = file_ext(path)
    if ext == ".3mf":
        return import_3mf(path)
    return run_importer(MESH_IMPORTERS.get(ext, ()), path), None


def srgb_to_linear(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def color_material(rgb):
    """One shared material per colour a CAD or 3MF file asked for.

    The colours arrive as display values, so they are linearized for Base
    Color, and also set as the viewport colour so Solid mode shows them.
    """
    rgb = tuple(max(0.0, min(1.0, float(c))) for c in rgb[:3])
    name = "MV_Color_%02X%02X%02X" % tuple(int(round(c * 255)) for c in rgb)
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    linear = tuple(srgb_to_linear(c) for c in rgb) + (1.0,)
    mat.diffuse_color = linear
    tree = node_tree_of(mat)
    bsdf = next((n for n in tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None:
        tree.nodes.clear()
        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = tree.nodes.new("ShaderNodeOutputMaterial")
        out.location = (300, 0)
        tree.links.new(bsdf.outputs[0], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = linear
    return mat


# -- 3MF ----------------------------------------------------------------------

NS_3MF = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
UNITS_3MF = {"micron": "um", "millimeter": "mm", "centimeter": "cm",
             "inch": "in", "foot": "ft", "meter": "m"}


def matrix_3mf(text):
    """A 3MF transform as a Blender matrix.

    3MF writes twelve numbers for a row-vector matrix (point times matrix,
    translation in the last row); Blender's are column vectors, so it is the
    transpose.
    """
    if not text:
        return Matrix.Identity(4)
    m = [float(v) for v in text.split()]
    return Matrix(((m[0], m[3], m[6], m[9]),
                   (m[1], m[4], m[7], m[10]),
                   (m[2], m[5], m[8], m[11]),
                   (0.0, 0.0, 0.0, 1.0)))


def color_3mf(text):
    text = (text or "").lstrip("#")
    if len(text) < 6:
        return None
    try:
        return tuple(int(text[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return None


def import_3mf(path):
    """A small 3MF reader: meshes, components, build transforms and base
    material colours. Blender has no 3MF importer of its own.

    Each mesh object the build places becomes a Blender object, positioned by
    the build item's and any component's transforms. Vertex values are kept in
    the file's unit, the same as an STL, so its size is recorded as is.
    """
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(path) as z:
            model = "3D/3dmodel.model"
            try:
                rels = ET.fromstring(z.read("_rels/.rels"))
                for rel in rels:
                    if rel.get("Type", "").endswith("/3dmodel"):
                        model = rel.get("Target", model).lstrip("/")
            except KeyError:
                pass
            root = ET.fromstring(z.read(model))
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError):
        return False, None

    units = UNITS_3MF.get(root.get("unit", "millimeter"), "mm")
    resources = root.find(NS_3MF + "resources")
    build = root.find(NS_3MF + "build")
    if resources is None or build is None:
        return False, None

    colours = {}
    for group in resources.findall(NS_3MF + "basematerials"):
        for i, base in enumerate(group.findall(NS_3MF + "base")):
            colours[(group.get("id"), str(i))] = color_3mf(base.get("displaycolor"))
    objects = {o.get("id"): o for o in resources.findall(NS_3MF + "object")}
    stem = os.path.splitext(os.path.basename(path))[0]
    made = []

    def make_mesh(node, matrix, name):
        mesh = node.find(NS_3MF + "mesh")
        verts = [(float(v.get("x")), float(v.get("y")), float(v.get("z")))
                 for v in mesh.find(NS_3MF + "vertices")]
        tris, keys = [], []
        default = (node.get("pid"), node.get("pindex"))
        for t in mesh.find(NS_3MF + "triangles"):
            tris.append((int(t.get("v1")), int(t.get("v2")), int(t.get("v3"))))
            pid = t.get("pid", default[0])
            keys.append((pid, t.get("p1", default[1] if pid == default[0] else "0")))
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], tris)
        slots = []
        for key in keys:
            if key not in slots:
                slots.append(key)
        if any(colours.get(k) for k in slots):
            for key in slots:
                me.materials.append(color_material(colours.get(key) or (0.8, 0.8, 0.8)))
            me.polygons.foreach_set("material_index", [slots.index(k) for k in keys])
        me.update()
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        obj.matrix_world = matrix
        made.append(obj)

    def place(obj_id, matrix, depth=0):
        node = objects.get(obj_id)
        if node is None or depth > 32:
            return
        name = node.get("name") or stem
        if node.find(NS_3MF + "mesh") is not None:
            make_mesh(node, matrix, name)
        comps = node.find(NS_3MF + "components")
        if comps is not None:
            for comp in comps.findall(NS_3MF + "component"):
                place(comp.get("objectid"), matrix @ matrix_3mf(comp.get("transform")), depth + 1)

    try:
        for item in build.findall(NS_3MF + "item"):
            place(item.get("objectid"), matrix_3mf(item.get("transform")))
    except (TypeError, ValueError, AttributeError):
        for obj in made:
            bpy.data.objects.remove(obj, do_unlink=True)
        return False, None
    return bool(made), units


def has_geometry(objs):
    """True when at least one of these objects carries geometry worth keeping.

    Object count alone is not enough. Blender's STL importer reports success on
    a file that is not an STL at all and hands back an empty mesh, and a
    FreeCAD OBJ can arrive the same way. An empty product collection is not a
    harmless no-op: it picks up a camera rig, joins the batch, and renders as
    blank frames across every view rather than being reported as a bad file.
    """
    for obj in objs:
        data = getattr(obj, "data", None)
        if data is None:
            continue
        if obj.type == 'MESH':
            if len(data.vertices):
                return True
        elif obj.type == 'CURVE':
            if len(data.splines):
                return True
        elif obj.type in {'SURFACE', 'META', 'FONT'}:
            return True
    return False


STEPPER_OPERATORS = (
    "import_scene.occ_import_step",
    "import_scene.occ",
    "wm.stepper_import",
    "import_scene.stepper",
)

# Wall-clock ceiling for one FreeCAD conversion. Generous, because Esc now
# cancels an import that is genuinely wedged.
FREECAD_TIMEOUT = 900.0


def try_stepper_import(filepath):
    """True only if a STEPper-style operator actually reported success.

    Blender operators signal failure by RETURNING {'CANCELLED'} rather than
    raising, so the result set has to be inspected. Not doing that made AUTO
    mode read a cancelled import as a success and skip the FreeCAD fallback.
    """
    for op_path in STEPPER_OPERATORS:
        module, func = op_path.split(".", 1)
        mod = getattr(bpy.ops, module, None)
        op = getattr(mod, func, None) if mod else None
        if op is None:
            continue
        for kw in ("filepath", "filename"):
            try:
                if 'FINISHED' in op(**{kw: filepath}):
                    return True
            except TypeError:
                continue
            except Exception:
                break
    return False


STEP_ENTITY = re.compile(r"#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*?)\)\s*;", re.S)
STEP_REF = re.compile(r"#(\d+)")
STEP_SOLIDS = {"MANIFOLD_SOLID_BREP", "BREP_WITH_VOIDS", "SHELL_BASED_SURFACE_MODEL",
               "FACETED_BREP"}
STEP_SHELLS = {"CLOSED_SHELL", "OPEN_SHELL"}
STEP_FACES = {"ADVANCED_FACE", "FACE_SURFACE"}
STEP_REPS = {"ADVANCED_BREP_SHAPE_REPRESENTATION", "MANIFOLD_SURFACE_SHAPE_REPRESENTATION",
             "SHAPE_REPRESENTATION", "FACETED_BREP_SHAPE_REPRESENTATION"}
STEP_STYLE_CHAIN = {"PRESENTATION_STYLE_ASSIGNMENT", "SURFACE_STYLE_USAGE", "SURFACE_SIDE_STYLE",
                    "SURFACE_STYLE_FILL_AREA", "FILL_AREA_STYLE", "FILL_AREA_STYLE_COLOUR",
                    "COLOUR_RGB", "DRAUGHTING_PRE_DEFINED_COLOUR"}
STEP_NEEDED = (STEP_SOLIDS | STEP_SHELLS | STEP_FACES | STEP_REPS | STEP_STYLE_CHAIN
               | {"STYLED_ITEM", "OVER_RIDING_STYLED_ITEM", "SHAPE_DEFINITION_REPRESENTATION",
                  "SHAPE_REPRESENTATION_RELATIONSHIP", "PRODUCT_DEFINITION_SHAPE",
                  "PRODUCT_DEFINITION", "PRODUCT_DEFINITION_FORMATION",
                  "PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE", "PRODUCT"})
STEP_NAMED_COLOURS = {"red": (1, 0, 0), "green": (0, 1, 0), "blue": (0, 0, 1),
                      "yellow": (1, 1, 0), "magenta": (1, 0, 1), "cyan": (0, 1, 1),
                      "black": (0, 0, 0), "white": (1, 1, 1)}


def step_string(args):
    """The first quoted string in a STEP argument list, unescaped."""
    m = re.match(r"\s*'((?:[^']|'')*)'", args)
    if not m:
        return ""
    text = m.group(1).replace("''", "'")
    text = re.sub(r"\\X2\\((?:[0-9A-F]{4})+)\\X0\\",
                  lambda g: "".join(chr(int(g.group(1)[i:i + 4], 16))
                                    for i in range(0, len(g.group(1)), 4)), text)
    return re.sub(r"\\X\\([0-9A-F]{2})", lambda g: chr(int(g.group(1), 16)), text)


def step_colors(path):
    """Colours a STEP file gives its parts and faces, keyed by product name.

    {name: {"color": (r, g, b) or None, "faces": {face index: (r, g, b)}}}

    FreeCAD reads STEP colours only into its GUI, so a console conversion
    loses every one of them. They are read here instead, from the text: each
    STYLED_ITEM points at a solid or a face, a solid belongs to a shape
    representation, and the representation leads through the product
    definition to the PRODUCT whose name FreeCAD gives the part. Face indices
    count through the solid's shells in file order, which is the order the
    faces come out of FreeCAD in.

    Best effort: anything unexpected yields fewer colours, never an error.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return {}
    if "STYLED_ITEM" not in text:
        return {}

    ents = {}
    for m in STEP_ENTITY.finditer(text):
        if m.group(2) in STEP_NEEDED:
            ents[int(m.group(1))] = (m.group(2), m.group(3))
    refs = {i: [int(r) for r in STEP_REF.findall(args)] for i, (_, args) in ents.items()}

    def kind(i):
        return ents.get(i, ("", ""))[0]

    def colour_of(i, depth=0):
        t = kind(i)
        if t == "COLOUR_RGB":
            nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", ents[i][1].split(",", 1)[-1])
            return tuple(float(v) for v in nums[-3:]) if len(nums) >= 3 else None
        if t == "DRAUGHTING_PRE_DEFINED_COLOUR":
            return STEP_NAMED_COLOURS.get(step_string(ents[i][1]).lower())
        if t not in STEP_STYLE_CHAIN or depth > 8:
            return None
        for r in refs[i]:
            found = colour_of(r, depth + 1)
            if found:
                return found
        return None

    # Solid -> its faces in order, and face -> (solid, index).
    solid_faces, face_home = {}, {}
    for i in ents:
        if kind(i) not in STEP_SOLIDS:
            continue
        faces = []
        for shell in refs[i]:
            if kind(shell) in STEP_SHELLS:
                faces.extend(f for f in refs[shell] if kind(f) in STEP_FACES)
        solid_faces[i] = faces
        for n, face in enumerate(faces):
            face_home.setdefault(face, (i, n))

    # Solid -> product name, through representation and product definition.
    rep_of = {}
    for i in ents:
        if kind(i) in STEP_REPS:
            for item in refs[i]:
                if kind(item) in STEP_SOLIDS:
                    rep_of.setdefault(item, i)
    rep_links = {}
    for i in ents:
        if kind(i) == "SHAPE_REPRESENTATION_RELATIONSHIP" and len(refs[i]) >= 2:
            a, b = refs[i][-2], refs[i][-1]
            rep_links.setdefault(a, []).append(b)
            rep_links.setdefault(b, []).append(a)
    pds_of = {}
    for i in ents:
        if kind(i) == "SHAPE_DEFINITION_REPRESENTATION" and len(refs[i]) >= 2:
            pds_of[refs[i][1]] = refs[i][0]

    def product_name(rep):
        for candidate in [rep] + rep_links.get(rep, []):
            pds = pds_of.get(candidate)
            if pds is None or kind(pds) != "PRODUCT_DEFINITION_SHAPE":
                continue
            for pd in refs[pds]:
                if kind(pd) != "PRODUCT_DEFINITION":
                    continue
                for pdf in refs[pd]:
                    if kind(pdf).startswith("PRODUCT_DEFINITION_FORMATION"):
                        for product in refs[pdf]:
                            if kind(product) == "PRODUCT":
                                return step_string(ents[product][1])
        return None

    per_solid, per_face = {}, {}
    # Plain styles first, so an over-riding style wins where both apply.
    for t in ("STYLED_ITEM", "OVER_RIDING_STYLED_ITEM"):
        for i in ents:
            if kind(i) != t or not refs[i]:
                continue
            colour = next((c for c in (colour_of(r) for r in refs[i][:-1]) if c), None)
            target = refs[i][-1]
            if t == "OVER_RIDING_STYLED_ITEM" and len(refs[i]) >= 2:
                target = next((r for r in refs[i] if kind(r) in STEP_SOLIDS | STEP_FACES), target)
            if colour is None:
                continue
            if kind(target) in STEP_SOLIDS:
                per_solid[target] = colour
            elif kind(target) in STEP_SHELLS:
                for solid, faces in solid_faces.items():
                    if target in refs[solid]:
                        per_solid[solid] = colour
            elif target in face_home:
                per_face[target] = colour

    result = {}
    for solid, faces in solid_faces.items():
        name = product_name(rep_of.get(solid))
        if name is None:
            continue
        entry = result.setdefault(name, {"colors": []})
        base = per_solid.get(solid)
        entry["colors"].extend(per_face.get(face, base) for face in faces)
    out = {}
    for name, entry in result.items():
        colours = entry["colors"]
        if not any(colours):
            continue
        if len(set(colours)) == 1:
            out[name] = {"color": colours[0], "faces": {}}
        else:
            out[name] = {"color": None,
                         "faces": {str(n): c for n, c in enumerate(colours) if c}}
    return out


# The script FreeCAD runs. It reads its settings from job.json beside it, so
# no path or name is ever pasted into code: a path holding an apostrophe --
# C:\Users\Dan's Files\part.step -- once closed a string early and surfaced as
# a bare "conversion failed".
FREECAD_SCRIPT = r'''
import json, os, re, sys, traceback
import FreeCAD, Part, MeshPart, Import

here = os.path.dirname(os.path.abspath(__file__))
job = json.load(open(os.path.join(here, "job.json"), encoding="utf-8"))
Import.open(job["source"])
doc = FreeCAD.ActiveDocument
colors = job.get("colors", {})


def shaped(o):
    return (o.isDerivedFrom("Part::Feature") and o.Shape and not o.Shape.isNull()
            and len(o.Shape.Faces) > 0)


# Leaves only. A STEP assembly arrives as an App::Part container whose shape
# is all of its children combined, plus origin planes with shapes of their
# own; meshing everything with a shape doubled every part.
leaves = [o for o in doc.Objects if shaped(o) and not any(shaped(c) for c in o.OutList)] if doc else []
if not leaves:
    # Console FreeCAD opens IGES into an empty document. Reading the shape
    # directly works for it, and for anything else Import.open passes over.
    doc = FreeCAD.newDocument("MV")
    whole = doc.addObject("Part::Feature", os.path.splitext(os.path.basename(job["source"]))[0])
    whole.Shape = Part.read(job["source"])
    leaves = [whole] if shaped(whole) else []


def world_shape(o):
    shape = o.Shape.copy()
    try:
        shape.Placement = o.getGlobalPlacement()
    except Exception:
        pass
    return shape


def mesh(shape):
    return MeshPart.meshFromShape(Shape=shape, LinearDeflection=job["deflection"],
                                  AngularDeflection=0.5, Relative=False)


def colour_info(label):
    if label in colors:
        return colors[label]
    return colors.get(re.sub(r"\d{3}$", "", label), {})


try:
    parts = []
    for i, o in enumerate(leaves):
        shape = world_shape(o)
        info = colour_info(o.Label)
        base = tuple(info["color"]) if info.get("color") else None
        face_colors = info.get("faces") or {}
        groups = {}
        if face_colors:
            for n, face in enumerate(shape.Faces):
                key = tuple(face_colors.get(str(n)) or base or ()) or None
                groups.setdefault(key, []).append(face)
        else:
            groups[base] = None
        files = []
        for g, (colour, faces) in enumerate(groups.items()):
            piece = shape if faces is None else Part.makeCompound(faces)
            name = "part_%04d_%d.obj" % (i, g)
            m = mesh(piece)
            if m.CountFacets:
                m.write(os.path.join(here, name))
                files.append({"file": name, "color": list(colour) if colour else None})
        if files:
            parts.append({"name": o.Label, "files": files})
    json.dump({"parts": parts}, open(os.path.join(here, "parts.json"), "w", encoding="utf-8"))
except Exception:
    # Whatever went wrong, still hand back the geometry in one piece.
    traceback.print_exc()
    merged = None
    for o in leaves:
        try:
            m = mesh(world_shape(o))
        except Exception as e:
            print("mesh failed", o.Name, e)
            continue
        if merged is None:
            merged = m
        else:
            merged.addMesh(m)
    if merged is not None:
        merged.write(os.path.join(here, "model.obj"))
'''


def freecad_prepare(source, freecad_exe, deflection, colors=None):
    """Write the conversion job for one STEP or IGES file. None if FreeCAD is
    not configured. Nothing is launched yet."""
    if not freecad_exe or not os.path.isfile(freecad_exe):
        return None
    tmp_dir = tempfile.mkdtemp(prefix="mv_step_")
    with open(os.path.join(tmp_dir, "job.json"), "w", encoding="utf-8") as f:
        json.dump({"source": source, "deflection": float(deflection),
                   "colors": colors or {}}, f)
    script_path = os.path.join(tmp_dir, "convert.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(FREECAD_SCRIPT)
    return {"tmp_dir": tmp_dir, "script": script_path,
            "log": os.path.join(tmp_dir, "freecad.log"), "exe": freecad_exe,
            "proc": None, "handle": None}


def freecad_start(job):
    """Launch freecadcmd without waiting on it.

    stdin is closed rather than inherited: a FreeCAD build that stops to ask a
    question used to sit there holding Blender hostage for the whole timeout.
    Output goes to a file, not a pipe, so a chatty conversion cannot deadlock
    against a pipe buffer nobody is draining while we poll.
    """
    handle = open(job["log"], "w", encoding="utf-8", errors="replace")
    job["handle"] = handle
    job["proc"] = subprocess.Popen(
        [job["exe"], job["script"]],
        stdin=subprocess.DEVNULL,
        stdout=handle,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return job


def freecad_running(job):
    proc = job.get("proc")
    return proc is not None and proc.poll() is None


def freecad_collect(job):
    """Reap a finished job: (result or None, whatever FreeCAD printed).

    The result is {"parts": [{"name", "files": [{"path", "color"}]}]}: one
    entry per part, each split by colour. A conversion that could not split
    the parts falls back to a single merged OBJ, which comes back as one
    nameless part.
    """
    if job.get("handle") is not None:
        job["handle"].close()
        job["handle"] = None
    log = ""
    try:
        with open(job["log"], "r", encoding="utf-8", errors="replace") as f:
            log = f.read()
    except OSError:
        pass
    here = job["tmp_dir"]
    try:
        with open(os.path.join(here, "parts.json"), encoding="utf-8") as f:
            parts = json.load(f)["parts"]
        for part in parts:
            for entry in part["files"]:
                entry["path"] = os.path.join(here, entry["file"])
        if parts:
            return {"parts": parts}, log
    except (OSError, ValueError, KeyError, TypeError):
        pass
    merged = os.path.join(here, "model.obj")
    if file_ok(merged):
        return {"parts": [{"name": None, "files": [{"path": merged, "color": None}]}]}, log
    return None, log


def kill_process_tree(proc):
    """Stop the converter and anything it spawned.

    proc.kill() only signals the immediate child. A launcher that re-execs
    leaves the real worker alive, still holding the temp dir open, so a
    cancelled import would leak its scratch directory every time.
    """
    if proc is None or proc.poll() is not None:
        return
    if os.name == 'nt':
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            pass
    if proc.poll() is None:
        try:
            proc.kill()
        except Exception:
            pass
    try:
        proc.wait(timeout=5)
    except Exception:
        pass


def freecad_cleanup(job):
    kill_process_tree(job.get("proc"))
    if job.get("handle") is not None:
        job["handle"].close()
        job["handle"] = None
    # Windows keeps the log file locked for a moment after the writer dies.
    tmp_dir = job["tmp_dir"]
    for _ in range(5):
        if not os.path.isdir(tmp_dir):
            return
        try:
            shutil.rmtree(tmp_dir)
            return
        except OSError:
            time.sleep(0.1)
    shutil.rmtree(tmp_dir, ignore_errors=True)


def import_obj_file(path):
    """FreeCAD works Z-up, so tell the OBJ importer that instead of letting it
    apply its Y-up default and silently rotating every product 90 degrees."""
    if hasattr(bpy.ops.wm, "obj_import"):
        try:
            bpy.ops.wm.obj_import(filepath=path, forward_axis='Y', up_axis='Z')
        except TypeError:
            bpy.ops.wm.obj_import(filepath=path)
        return True
    if hasattr(bpy.ops.import_scene, "obj"):
        try:
            bpy.ops.import_scene.obj(filepath=path, axis_forward='Y', axis_up='Z')
        except TypeError:
            bpy.ops.import_scene.obj(filepath=path)
        return True
    return False


def import_freecad_result(result):
    """Bring a converted STEP or IGES into the scene, one object per part.

    A part with faces in several colours arrives as one OBJ per colour; those
    are joined back into a single object with a material slot per colour, and
    named after the part, so the outliner reads like the CAD tree.
    """
    for part in result["parts"]:
        pieces = []
        for entry in part["files"]:
            before = set(bpy.data.objects)
            if not import_obj_file(entry["path"]):
                continue
            new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
            if entry.get("color"):
                mat = color_material(entry["color"])
                for obj in new:
                    obj.data.materials.clear()
                    obj.data.materials.append(mat)
            pieces.extend(new)
        if not pieces:
            continue
        if len(pieces) > 1:
            with bpy.context.temp_override(active_object=pieces[0], object=pieces[0],
                                           selected_objects=pieces,
                                           selected_editable_objects=pieces):
                bpy.ops.object.join()
        obj = pieces[0]
        if part.get("name"):
            obj.name = part["name"]
            obj.data.name = part["name"]


PERSP_LENS = 50.0
SENSOR_WIDTH = 36.0


def image_aspect(scene):
    """Effective pixel dimensions of the render, including pixel aspect."""
    r = scene.render
    rx = max(r.resolution_x * r.pixel_aspect_x, 1e-6)
    ry = max(r.resolution_y * r.pixel_aspect_y, 1e-6)
    return rx, ry


def sensor_tangents(rx, ry, lens=PERSP_LENS, sensor=SENSOR_WIDTH):
    """Half-FOV tangents on the image x and y axes, for sensor_fit='AUTO'.

    Blender fits the sensor width to the LONGER image axis, so the shorter axis
    sees a proportionally smaller sensor and a narrower field of view.
    """
    if rx >= ry:
        sx, sy = sensor, sensor * ry / rx
    else:
        sx, sy = sensor * rx / ry, sensor
    lens = max(lens, 1e-6)
    return (sx * 0.5) / lens, (sy * 0.5) / lens


def view_extents(basis, center, corners):
    """Where the product sits in one camera's frame: half-width, half-height,
    how far it reaches toward the camera, and the per-corner coordinates.

    Only the rotation of `basis` matters -- sliding a camera along its own view
    axis never changes where a point lands horizontally or vertically in frame.
    """
    right, up, back = basis.col[0].xyz, basis.col[1].xyz, basis.col[2].xyz
    ex = ey = 0.0
    depth = -float("inf")
    local = []
    for p in corners:
        rel = p - center
        cx, cy, cz = abs(rel.dot(right)), abs(rel.dot(up)), rel.dot(back)
        ex = max(ex, cx)
        ey = max(ey, cy)
        depth = max(depth, cz)
        local.append((cx, cy, cz))
    return ex, ey, depth, local


def ortho_span(ex, ey, rx, ry):
    """Half-extent ortho_scale has to cover.

    ortho_scale spans the LONGER image axis, so the shorter axis gets
    proportionally less room. Ignoring that is what made the old
    `ortho_scale = max_dim * pad` crop every view at 16:9.
    """
    if rx >= ry:
        return max(ex, ey * rx / ry)
    return max(ey, ex * ry / rx)


def persp_distance(local, tan_x, tan_y, pad):
    """Closest distance at which every corner still clears both frame edges."""
    distance = 0.0
    for cx, cy, cz in local:
        distance = max(distance, pad * cx / tan_x + cz, pad * cy / tan_y + cz)
    return distance


def planned_views(settings):
    """(name, kind, direction) for every view a camera should be built for.

    A preset is read from VIEW_SETS rather than from the checkboxes, so a file
    saved before the checkboxes existed still gets exactly the views it chose.
    """
    if settings.view_set == 'CUSTOM':
        views = [v for v, on in zip(VIEWS_ALL, settings.views_enabled) if on]
    else:
        views = list(VIEW_SETS[settings.view_set])
    for cv in settings.custom_views:
        if cv.enabled:
            views.append((cv.name, "ortho" if cv.is_ortho else "persp",
                          (cv.dir_x, cv.dir_y, cv.dir_z)))
    return views


def build_cameras(context):
    settings = context.scene.mv_settings
    coll = ensure_collection(CAMERA_COLL)
    clear_collection_objects(coll)

    objs = []
    for pc in get_products():
        objs.extend(list(pc.all_objects))
    if not objs:
        objs = [o for o in bpy.data.objects if o.type == 'MESH']

    center, size = bbox_of(objs)
    half = size * 0.5
    corners = [center + Vector((x, y, z))
               for x in (-half.x, half.x)
               for y in (-half.y, half.y)
               for z in (-half.z, half.z)]
    diag = max(max((p - center).length for p in corners), 1e-3)
    pad = max(settings.frame_padding_factor, 1.0)
    rx, ry = image_aspect(context.scene)
    tan_x, tan_y = sensor_tangents(rx, ry)

    angle = FRONT_AXIS_ANGLES[settings.front_axis]
    views = planned_views(settings)

    # Pass 1: measure every view and take the worst case, so one ortho framing
    # and one perspective framing cover the whole set. Sizing each camera to its
    # own silhouette would frame tighter but make the product change apparent
    # size from view to view, which defeats the point of a multiview sheet.
    plan = []
    skipped = []
    ortho_scale = 0.0
    persp_dist = 0.0
    reach = -float("inf")
    for name, kind, direction in views:
        d = Vector(rotate_dir_z(direction, angle))
        if d.length < 1e-9:
            skipped.append(name)
            continue
        d.normalize()
        ex, ey, depth, local = view_extents(look_at(center + d, center), center, corners)
        reach = max(reach, depth)
        if kind == "ortho":
            ortho_scale = max(ortho_scale, 2.0 * pad * ortho_span(ex, ey, rx, ry))
        else:
            persp_dist = max(persp_dist, persp_distance(local, tan_x, tan_y, pad))
        plan.append((name, kind, d))

    if not plan:
        return skipped
    ortho_scale = max(ortho_scale, 1e-4)
    ortho_dist = reach + diag
    persp_dist = max(persp_dist, reach + diag * 0.1)

    # Pass 2: build them on the shared framing.
    for name, kind, d in plan:
        cam_data = bpy.data.cameras.new(f"MV_Cam_{name}")
        if kind == "ortho":
            cam_data.type = 'ORTHO'
            cam_data.ortho_scale = ortho_scale
            distance = ortho_dist
        else:
            cam_data.type = 'PERSP'
            cam_data.lens = PERSP_LENS
            distance = persp_dist
        cam_data.clip_start = max(distance * 0.01, 1e-5)
        # Far enough for the ground, which runs fifty product sizes out; any
        # shorter and a perspective view sees the floor stop before the horizon.
        cam_data.clip_end = (distance + diag) * 100.0

        cam_obj = bpy.data.objects.new(f"MV_Cam_{name}", cam_data)
        cam_obj.matrix_world = look_at(center + d * distance, center)
        coll.objects.link(cam_obj)

    # What this framing was measured from, for the pre-flight's stale check.
    coll["mv_framing"] = framing_signature(context)
    return skipped


def batch_extent():
    """Centre and largest dimension of the whole batch, which is what the light
    rig and the ground are sized from."""
    objs = []
    for pc in get_products():
        objs.extend(collection_meshes(pc))
    if not objs:
        objs = [o for o in bpy.data.objects
                if o.type == 'MESH' and o.name != GROUND_NAME]
    center, size = bbox_of(objs)
    return center, max(size.x, size.y, size.z, 1e-3)


def front_basis(settings, center):
    """Rotation of the Front camera, which every preset is laid out against."""
    d = Vector(rotate_dir_z((0.0, -1.0, 0.0), FRONT_AXIS_ANGLES[settings.front_axis]))
    return look_at(center + d, center).to_3x3()


def build_lighting(context, preset_key):
    """Rebuild MV_Lighting from a preset. False if the preset cannot be read.

    Every light hangs off one empty at the batch centre, MV_LightRig. Turning
    that empty turns the whole rig about the product, which is how the lights
    follow the camera without anything being rebuilt per view.
    """
    settings = context.scene.mv_settings
    specs = lighting_specs(preset_key)
    if specs is None:
        return False
    coll = ensure_collection(LIGHT_COLL)
    clear_collection_objects(coll)

    center, max_dim = batch_extent()
    angle = FRONT_AXIS_ANGLES[settings.front_axis]
    turn = Matrix.Rotation(math.radians(angle), 4, 'Z')
    intensity = settings.lighting_intensity

    rig = bpy.data.objects.new(LIGHT_RIG, None)
    rig.empty_display_type = 'SPHERE'
    rig.empty_display_size = max_dim * 0.15
    rig.matrix_world = Matrix.Translation(center)
    coll.objects.link(rig)

    for spec in specs:
        kind = spec.get("type", 'AREA')
        name = f"MV_Light_{spec.get('name', 'Light')}"
        ld = bpy.data.lights.new(name, type=kind)
        size = spec.get("size", 1.0) * max_dim * 0.5
        if kind == 'AREA':
            ld.size = size
            if "shape" in spec:
                ld.shape = spec["shape"]
                ld.size_y = spec.get("size_y", spec.get("size", 1.0)) * max_dim * 0.5
        elif kind in {'POINT', 'SPOT'}:
            ld.shadow_soft_size = size
        if kind == 'SPOT':
            ld.spot_size = spec.get("spot_size", ld.spot_size)
            ld.spot_blend = spec.get("spot_blend", ld.spot_blend)
        if kind == 'SUN':
            ld.angle = spec.get("angle", ld.angle)
            # Sun strength is irradiance, which does not grow with the product.
            ld.energy = spec["energy"] * intensity
        else:
            ld.energy = spec["energy"] * max_dim * intensity
        ld.color = spec.get("color", (1.0, 1.0, 1.0))

        obj = bpy.data.objects.new(name, ld)
        coll.objects.link(obj)
        obj.parent = rig
        pos = center + Vector(rotate_dir_z(spec["pos"], angle)) * max_dim
        if "rot" in spec:
            rot = turn @ Quaternion(spec["rot"]).to_matrix().to_4x4()
            obj.matrix_world = Matrix.Translation(pos) @ rot
        else:
            obj.matrix_world = look_at(pos, center)
    return True


def orient_light_rig(context, camera):
    """Turn the rig so it stands to camera the way it stands to Front."""
    rig = bpy.data.objects.get(LIGHT_RIG)
    if rig is None or camera is None:
        return
    center = rig.matrix_world.translation.copy()
    turn = camera.matrix_world.to_3x3().normalized() @ front_basis(
        context.scene.mv_settings, center).transposed()
    rig.matrix_world = Matrix.Translation(center) @ turn.to_4x4()


def reset_light_rig():
    rig = bpy.data.objects.get(LIGHT_RIG)
    if rig is not None:
        rig.matrix_world = Matrix.Translation(rig.matrix_world.translation.copy())


def capture_lighting(context):
    """MV_Lighting's lights as preset specs, in the units presets are written in:
    positions and sizes as multiples of the batch's size, laid out against the
    Front view with Front Axis taken back out, energy before Intensity.

    Read back through build_lighting, a rig saved here comes out the same on a
    product of any size and any front axis.
    """
    settings = context.scene.mv_settings
    coll = bpy.data.collections.get(LIGHT_COLL)
    lights = [o for o in coll.objects if o.type == 'LIGHT'] if coll else []
    if not lights:
        return []
    center, max_dim = batch_extent()
    rig = bpy.data.objects.get(LIGHT_RIG)
    # Measured against the rig rather than the world, so saving straight after
    # a render, with the rig still turned for the last view, still works.
    frame = rig.matrix_world.copy() if rig else Matrix.Translation(center)
    untilt = Matrix.Rotation(-math.radians(FRONT_AXIS_ANGLES[settings.front_axis]), 4, 'Z')
    intensity = settings.lighting_intensity or 1.0

    specs = []
    for obj in lights:
        local = untilt @ frame.inverted() @ obj.matrix_world
        ld = obj.data
        spec = {
            "name": obj.name.replace("MV_Light_", "") or "Light",
            "type": ld.type,
            "pos": [round(v / max_dim, 5) for v in local.translation],
            "rot": [round(v, 6) for v in local.to_quaternion().normalized()],
            "color": [round(v, 5) for v in ld.color],
            "energy": round(ld.energy / (intensity * (1.0 if ld.type == 'SUN' else max_dim)), 5),
        }
        if ld.type == 'AREA':
            spec["size"] = round(ld.size / (max_dim * 0.5), 5)
            spec["shape"] = ld.shape
            spec["size_y"] = round(ld.size_y / (max_dim * 0.5), 5)
        elif ld.type in {'POINT', 'SPOT'}:
            spec["size"] = round(ld.shadow_soft_size / (max_dim * 0.5), 5)
        if ld.type == 'SPOT':
            spec["spot_size"] = round(ld.spot_size, 5)
            spec["spot_blend"] = round(ld.spot_blend, 5)
        if ld.type == 'SUN':
            spec["angle"] = round(ld.angle, 5)
        specs.append(spec)
    return specs


def node_tree_of(idblock):
    """The node tree of a material or world, switching nodes on only where
    that is still a setting. Blender 5 always uses nodes and warns about the
    flag, which it plans to remove."""
    if idblock.node_tree is None or (bpy.app.version < (5, 0, 0) and not idblock.use_nodes):
        idblock.use_nodes = True
    return idblock.node_tree


def build_ground(context):
    """Rebuild MV_Stage's ground to match the settings, or clear it for None."""
    s = context.scene.mv_settings
    stage = bpy.data.collections.get(STAGE_COLL)
    if s.ground_mode == 'NONE':
        if stage:
            clear_collection_objects(stage)
        return None
    stage = ensure_collection(STAGE_COLL)
    clear_collection_objects(stage)

    center, max_dim = batch_extent()
    half = max_dim * 50.0
    mesh = bpy.data.meshes.new(GROUND_NAME)
    mesh.from_pydata([(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)],
                     [], [(0, 1, 2, 3)])
    mat = bpy.data.materials.get(GROUND_NAME) or bpy.data.materials.new(GROUND_NAME)
    tree = node_tree_of(mat)
    tree.nodes.clear()
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    tree.links.new(bsdf.outputs[0], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*s.ground_color, 1.0)
    bsdf.inputs["Roughness"].default_value = s.ground_roughness
    mesh.materials.append(mat)

    ground = bpy.data.objects.new(GROUND_NAME, mesh)
    ground.location = (center.x, center.y, center.z)
    ground.is_shadow_catcher = s.ground_mode == 'SHADOW'
    stage.objects.link(ground)
    return ground


def apply_world(context):
    """Point the scene at the add-on's own world and rewrite that one.

    Returns an error message, or None.

    This used to reuse whatever world the scene already had and clear its node
    tree, so pressing Apply Background on a file with a hand-built HDRI setup
    destroyed it with no warning and no undo. The add-on now owns a single
    MV_World, the same way it owns MV_Cameras and MV_Lighting. Any other world
    keeps its nodes and stays selectable from World properties.
    """
    settings = context.scene.mv_settings
    scene = context.scene
    image = None
    if settings.world_mode == 'HDRI':
        path = bpy.path.abspath(settings.hdri_path)
        if not os.path.isfile(path):
            return f"HDRI file not found: '{settings.hdri_path}'"
        try:
            image = bpy.data.images.load(path, check_existing=True)
        except RuntimeError as exc:
            return f"Cannot read HDRI '{path}': {exc}"

    world = bpy.data.worlds.get(WORLD_NAME) or bpy.data.worlds.new(WORLD_NAME)
    scene.world = world
    tree = node_tree_of(world)
    nodes = tree.nodes
    links = tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    out.location = (600, 0)
    flat = nodes.new("ShaderNodeBackground")
    flat.location = (100, -200)
    flat.inputs["Color"].default_value = settings.bg_color
    flat.inputs["Strength"].default_value = 1.0
    scene.render.film_transparent = settings.transparent_bg

    if image is None:
        links.new(flat.outputs["Background"], out.inputs["Surface"])
        return None

    coords = nodes.new("ShaderNodeTexCoord")
    coords.location = (-700, 150)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-500, 150)
    mapping.inputs["Rotation"].default_value[2] = settings.hdri_rotation
    env = nodes.new("ShaderNodeTexEnvironment")
    env.location = (-250, 150)
    env.image = image
    hdri = nodes.new("ShaderNodeBackground")
    hdri.location = (100, 100)
    hdri.inputs["Strength"].default_value = settings.hdri_strength
    links.new(coords.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    links.new(env.outputs["Color"], hdri.inputs["Color"])
    if settings.hdri_visible:
        links.new(hdri.outputs["Background"], out.inputs["Surface"])
        return None

    # The camera sees the flat colour; everything else (lighting, reflections)
    # sees the HDRI.
    path = nodes.new("ShaderNodeLightPath")
    path.location = (100, 400)
    mix = nodes.new("ShaderNodeMixShader")
    mix.location = (350, 0)
    links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(hdri.outputs["Background"], mix.inputs[1])
    links.new(flat.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return None


def product_material_choice(settings, coll):
    """(preset, colour) a product renders with, or None to keep its own."""
    preset = getattr(coll, "mv_material", 'DEFAULT')
    if preset == 'DEFAULT':
        preset, color = settings.material_preset, settings.material_color
    else:
        color = coll.mv_material_color
    if preset not in MATERIAL_PRESETS:
        return None
    return preset, tuple(color)


def preset_material(name, preset, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    tree = node_tree_of(mat)
    tree.nodes.clear()
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    tree.links.new(bsdf.outputs[0], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    for key, value in MATERIAL_PRESETS[preset]["inputs"].items():
        socket = bsdf.inputs.get(key)
        if socket is not None:
            socket.default_value = value
    return mat


def material_node_group():
    """A Geometry Nodes group that sets one material on everything.

    A modifier carrying it swaps the material for rendering without touching
    the product's own material slots, so removing the modifier is a complete
    undo, and a mesh with no slots at all (every STL) still gets the material.
    """
    group = bpy.data.node_groups.get(MATERIAL_GROUP)
    if group is not None and group.bl_idname == 'GeometryNodeTree':
        return group
    group = bpy.data.node_groups.new(MATERIAL_GROUP, 'GeometryNodeTree')
    group.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket("Material", in_out='INPUT', socket_type='NodeSocketMaterial')
    group.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gin = group.nodes.new("NodeGroupInput")
    gout = group.nodes.new("NodeGroupOutput")
    gout.location = (400, 0)
    setter = group.nodes.new("GeometryNodeSetMaterial")
    setter.location = (200, 0)
    group.links.new(gin.outputs[0], setter.inputs["Geometry"])
    group.links.new(gin.outputs[1], setter.inputs["Material"])
    group.links.new(setter.outputs["Geometry"], gout.inputs[0])
    return group


def apply_product_material(settings, coll):
    """Give a product its preset material for rendering. False when it keeps its own."""
    choice = product_material_choice(settings, coll)
    if choice is None:
        return False
    mat = preset_material(f"MV_Material_{coll.name}", *choice)
    group = material_node_group()
    socket = next(item.identifier for item in group.interface.items_tree
                  if getattr(item, "in_out", None) == 'INPUT'
                  and getattr(item, "socket_type", None) == 'NodeSocketMaterial')
    for obj in collection_meshes(coll):
        if obj.type != 'MESH' or obj.library is not None:
            continue
        mod = obj.modifiers.new(MATERIAL_MOD, 'NODES')
        mod.node_group = group
        mod[socket] = mat
    return True


def remove_product_materials():
    """Take every preset material back off, wherever it was left."""
    for obj in bpy.data.objects:
        for mod in [m for m in obj.modifiers
                    if m.type == 'NODES' and m.name.startswith(MATERIAL_MOD)]:
            obj.modifiers.remove(mod)


class MV_OT_AddStepFile(Operator, ImportHelper):
    """Add CAD or mesh files to the import list"""
    bl_idname = "mv.add_step_file"
    bl_label = "Add Files"
    filter_glob: StringProperty(default=FILE_FILTER, options={'HIDDEN'})
    files: CollectionProperty(type=bpy.types.OperatorFileListElement)
    directory: StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        s = context.scene.mv_settings
        if self.files:
            for f in self.files:
                if not f.name:
                    continue
                item = s.step_files.add()
                item.path = os.path.join(self.directory, f.name)
        elif self.filepath:
            item = s.step_files.add()
            item.path = self.filepath
        return {'FINISHED'}


class MV_OT_RemoveStepFile(Operator):
    bl_idname = "mv.remove_step_file"
    bl_label = "Remove"
    index: IntProperty()

    def execute(self, context):
        s = context.scene.mv_settings
        if 0 <= self.index < len(s.step_files):
            s.step_files.remove(self.index)
        return {'FINISHED'}


class MV_OT_ClearStepFiles(Operator):
    bl_idname = "mv.clear_step_files"
    bl_label = "Clear List"

    def execute(self, context):
        context.scene.mv_settings.step_files.clear()
        return {'FINISHED'}


class MV_OT_AddFolder(Operator):
    """Add every CAD and mesh file in a folder to the import list"""
    bl_idname = "mv.add_folder"
    bl_label = "Add Folder"

    directory: StringProperty(subtype='DIR_PATH')
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})
    recursive: BoolProperty(
        name="Include Subfolders",
        description="Also add files from every folder inside this one",
        default=True,
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        s = context.scene.mv_settings
        folder = bpy.path.abspath(self.directory)
        if not os.path.isdir(folder):
            self.report({'ERROR'}, f"Not a folder: '{folder}'")
            return {'CANCELLED'}
        found = []
        for current, dirs, files in os.walk(folder):
            dirs.sort()
            found.extend(os.path.join(current, f) for f in sorted(files)
                         if file_ext(f) in SUPPORTED_EXTENSIONS)
            if not self.recursive:
                break
        # A folder added twice, or overlapping one added before, would import
        # the same file twice as two products.
        listed = {os.path.normcase(os.path.abspath(bpy.path.abspath(i.path)))
                  for i in s.step_files}
        added = 0
        for path in found:
            key = os.path.normcase(os.path.abspath(path))
            if key in listed:
                continue
            listed.add(key)
            s.step_files.add().path = path
            added += 1
        if not found:
            self.report({'WARNING'}, "No supported files in that folder.")
        else:
            skipped = len(found) - added
            self.report({'INFO'}, f"Added {added} file(s)"
                        + (f", {skipped} already in the list." if skipped else "."))
        return {'FINISHED'}


class MV_OT_ImportAllSteps(Operator):
    """Import every file in the list, one at a time.

    STEP files are converted first, by STEPper or by FreeCAD, and IGES by
    FreeCAD. Mesh files (STL, OBJ, PLY, glTF, FBX, 3MF) skip both and go
    straight through Blender's own importers; from the product collection
    onwards they are all indistinguishable.

    Runs modally: the conversion subprocess is polled between timer ticks
    instead of being waited on, so Blender keeps redrawing, the status bar
    shows which file is in flight, and Esc aborts. Called from a script it
    falls back to running straight through.
    """
    bl_idname = "mv.import_all_steps"
    bl_label = "Import Files"
    bl_options = {'REGISTER', 'UNDO'}

    def _setup(self, context):
        s = context.scene.mv_settings
        if not s.step_files:
            self.report({'ERROR'}, "No files in the list.")
            return False
        self._prefs = addon_prefs(context)
        self._queue = [bpy.path.abspath(item.path) for item in s.step_files]
        self._total = len(self._queue)
        self._done = 0
        self._imported = 0
        self._problems = []
        self._unbaked = set()
        self._job = None
        self._job_path = None
        self._job_started = 0.0
        self._before = set()
        self._timer = None
        self._cancelled = False
        self._rescale_batch = False
        return True

    # -- one file ---------------------------------------------------------
    def _fail(self, path, reason):
        self._problems.append(f"{os.path.basename(path)}: {reason}")
        self._done += 1

    def _discard(self, objs):
        """Throw away what a rejected import left in the scene.

        The objects were never linked into a product collection, so without
        this an empty mesh from a bad file would sit loose in the scene
        collection with the file's name on it, looking like it had worked.
        """
        for obj in objs:
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except (ReferenceError, RuntimeError):
                pass

    def _link_new(self, context, path, new_objs, units):
        # Always a fresh collection. Looking the name up first meant two
        # files sharing a basename -- partA/housing.step and partB/housing.step
        # -- landed in one collection and rendered as a single product, and an
        # unrelated collection that happened to be called "housing" would have
        # the geometry dropped into it. Blender resolves the clash itself by
        # suffixing .001, which keeps the two products separate.
        root = get_products_root()
        base = os.path.splitext(os.path.basename(path))[0]
        product_coll = bpy.data.collections.new(base)
        root.children.link(product_coll)
        for obj in new_objs:
            for c in list(obj.users_collection):
                c.objects.unlink(obj)
            product_coll.objects.link(obj)

        # Measured before fitting, which is the last moment the real size is
        # known. The manifest reports it next to the renders.
        context.view_layer.update()
        s = context.scene.mv_settings
        product_coll.mv_source = path
        record_source_size(product_coll, units or s.mesh_units)

        if s.fit_on_import:
            if s.scale_mode == 'RELATIVE':
                # The shared scale depends on the biggest product, which may
                # not have arrived yet; the whole batch is scaled together at
                # the end instead.
                fit_collection(product_coll, None, recenter=True, floor=s.rest_on_floor)
                self._rescale_batch = True
            elif fit_collection(product_coll, s.target_size, recenter=True,
                                floor=s.rest_on_floor):
                _, unbaked = bake_product(product_coll)
                self._unbaked.update(unbaked)
        context.view_layer.update()
        remember_home(product_coll)
        self._imported += 1
        self._done += 1

    def _import_ready_file(self, context, path, units, what):
        """Link what a finished import added, or reject it as empty."""
        new = self._new_objects()
        strays = [o for o in new if o.type in NON_PRODUCT_TYPES]
        self._discard(strays)
        new = [o for o in new if o not in strays]
        if has_geometry(new):
            self._link_new(context, path, new, units)
        else:
            self._discard(new)
            self._fail(path, f"{what} contained no geometry")

    def _new_objects(self):
        return [o for o in bpy.data.objects if o not in self._before]

    def _start_file(self, context, path):
        self._job_path = path
        if not os.path.isfile(path):
            self._fail(path, "file not found")
            return
        self._before = set(bpy.data.objects)
        ext = file_ext(path)
        label = ext.lstrip(".").upper()

        if ext in MESH_EXTENSIONS:
            # Nothing to convert, so no importer preference applies and no
            # subprocess is started: the file lands now and _advance moves on
            # to the next one on the same tick.
            ok, units = import_mesh_file(path)
            if not ok:
                self._discard(self._new_objects())
                self._fail(path, f"{label} import failed")
                return
            self._import_ready_file(context, path, units, label)
            return
        if ext not in CAD_EXTENSIONS:
            self._fail(path, "not a supported file type")
            return

        mode = self._prefs.step_import_mode
        is_step = ext in STEP_EXTENSIONS

        if is_step and mode in {'AUTO', 'STEPPER'} and try_stepper_import(path):
            new = self._new_objects()
            if has_geometry(new):
                # STEPper does its own unit handling, so the size it lands at
                # is not known to be in any particular unit.
                self._link_new(context, path, new, "")
                return
            self._discard(new)
            if mode == 'STEPPER':
                self._fail(path, "STEPper reported success but added no geometry")
                return

        if mode == 'STEPPER':
            self._fail(path, "STEPper import failed" if is_step
                       else "IGES needs FreeCAD; STEPper reads STEP only")
            return

        job = freecad_prepare(path, self._prefs.freecad_path,
                              self._prefs.tessellation_deflection,
                              step_colors(path) if is_step else None)
        if job is None:
            self._fail(path, "no importer available (set the FreeCAD path in preferences)")
            return
        freecad_start(job)
        self._job = job
        self._job_started = time.monotonic()

    def _collect_job(self, context):
        job, self._job = self._job, None
        path = self._job_path
        result, log = freecad_collect(job)
        if result:
            import_freecad_result(result)
            # FreeCAD tessellates in millimetres whatever the file was drawn in.
            self._import_ready_file(context, path, "mm", "converted mesh")
        else:
            tail = " ".join(log.split())[-160:]
            self._fail(path, "FreeCAD conversion failed"
                             + (f" - {tail}" if tail else " (no output)"))
        freecad_cleanup(job)

    # -- driver -----------------------------------------------------------
    def _advance(self, context, blocking):
        """One slice of work. False once everything is finished."""
        if self._job is not None:
            if blocking:
                # Bounded even here. A bare wait() meant a wedged FreeCAD hung
                # a scripted or headless run forever, with only the modal path
                # honouring the timeout. Same deadline either way, measured
                # from when the process started.
                remaining = FREECAD_TIMEOUT - (time.monotonic() - self._job_started)
                try:
                    self._job["proc"].wait(timeout=max(remaining, 0.0))
                except subprocess.TimeoutExpired:
                    job, self._job = self._job, None
                    freecad_cleanup(job)
                    self._fail(self._job_path,
                               f"FreeCAD exceeded {int(FREECAD_TIMEOUT)}s and was stopped")
                    return bool(self._queue)
            elif freecad_running(self._job):
                if time.monotonic() - self._job_started > FREECAD_TIMEOUT:
                    job, self._job = self._job, None
                    freecad_cleanup(job)
                    self._fail(self._job_path,
                               f"FreeCAD exceeded {int(FREECAD_TIMEOUT)}s and was stopped")
                return True
            self._collect_job(context)
            return bool(self._queue)
        if not self._queue:
            return False
        self._start_file(context, self._queue.pop(0))
        return True

    def _status(self):
        name = os.path.basename(self._job_path) if self._job_path else ""
        waiting = " (converting)" if self._job is not None else ""
        return f"MultiView: {self._done}/{self._total}  {name}{waiting}  -  Esc to cancel"

    def _report_result(self):
        if self._rescale_batch:
            self._rescale_batch = False
            unbaked = standardize_products(bpy.context, get_products(), scale=True,
                                           recenter=False)
            self._unbaked.update(unbaked)
        if self._cancelled:
            level, msg = {'WARNING'}, f"Import cancelled after {self._imported} file(s)."
        elif not self._imported:
            level, msg = {'ERROR'}, "Nothing imported."
        else:
            level, msg = {'INFO'}, f"Imported {self._imported} of {self._total} file(s)."
        if self._unbaked:
            msg += (f" {len(self._unbaked)} object(s) kept their transform "
                    "(multi-user or linked data).")
        if self._problems:
            level = {'WARNING'} if self._imported else {'ERROR'}
            msg += " " + " | ".join(self._problems[:2])
            if len(self._problems) > 2:
                msg += f" | +{len(self._problems) - 2} more (see system console)"
            for problem in self._problems:
                print("[MultiView] " + problem)
        self.report(level, msg)
        return {'FINISHED'} if self._imported else {'CANCELLED'}

    def _teardown(self, context):
        wm = context.window_manager
        if self._timer is not None:
            wm.event_timer_remove(self._timer)
            self._timer = None
        wm.progress_end()
        try:
            context.workspace.status_text_set(None)
        except AttributeError:
            pass
        if self._job is not None:
            freecad_cleanup(self._job)
            self._job = None
        return self._report_result()

    # -- entry points -----------------------------------------------------
    def execute(self, context):
        if not self._setup(context):
            return {'CANCELLED'}
        while self._advance(context, blocking=True):
            pass
        return self._report_result()

    def invoke(self, context, event):
        if not self._setup(context):
            return {'CANCELLED'}
        wm = context.window_manager
        wm.progress_begin(0, self._total)
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'ESC' and event.value == 'PRESS':
            self._cancelled = True
            return self._teardown(context)
        if event.type != 'TIMER':
            # Swallow everything else: the scene is mid-edit, so letting clicks
            # through here would be a good way to corrupt it.
            return {'RUNNING_MODAL'}

        more = self._advance(context, blocking=False)
        context.window_manager.progress_update(self._done)
        try:
            context.workspace.status_text_set(self._status())
        except AttributeError:
            pass
        if not more:
            return self._teardown(context)
        return {'RUNNING_MODAL'}


class MV_OT_ApplySceneSetup(Operator):
    bl_idname = "mv.apply_scene_setup"
    bl_label = "Apply Scene Setup"

    def execute(self, context):
        s = context.scene.mv_settings
        problems = []
        error = apply_world(context)
        if error:
            problems.append(error)
        if not build_lighting(context, s.lighting_preset):
            problems.append("Lighting preset could not be read.")
        build_ground(context)
        if get_products():
            build_cameras(context)
        if problems:
            self.report({'WARNING'}, " ".join(problems))
        else:
            self.report({'INFO'}, "Lighting, background, ground and cameras updated.")
        return {'FINISHED'}


class MV_OT_BuildCameras(Operator):
    bl_idname = "mv.build_cameras"
    bl_label = "Build Cameras"

    def execute(self, context):
        if not planned_views(context.scene.mv_settings):
            self.report({'ERROR'}, "No views selected. Tick at least one view.")
            return {'CANCELLED'}
        skipped = build_cameras(context)
        if skipped:
            self.report({'WARNING'},
                        "Skipped custom view(s) with a zero direction vector: "
                        + ", ".join(skipped))
        return {'FINISHED'}


class MV_OT_BuildLighting(Operator):
    bl_idname = "mv.build_lighting"
    bl_label = "Rebuild Lighting"

    def execute(self, context):
        if not build_lighting(context, context.scene.mv_settings.lighting_preset):
            self.report({'ERROR'}, "Lighting preset could not be read.")
            return {'CANCELLED'}
        return {'FINISHED'}


class MV_OT_ApplyWorld(Operator):
    bl_idname = "mv.apply_world"
    bl_label = "Apply Background"

    def execute(self, context):
        error = apply_world(context)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}
        build_ground(context)
        return {'FINISHED'}


class MV_OT_SaveLightingPreset(Operator):
    """Save the lights in MV_Lighting, including any you have added or moved,
    as a preset available in every file"""
    bl_idname = "mv.save_lighting_preset"
    bl_label = "Save Lighting Preset"

    name: StringProperty(name="Name", default="My Studio")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        specs = capture_lighting(context)
        if not specs:
            self.report({'ERROR'}, f"No lights in '{LIGHT_COLL}' to save.")
            return {'CANCELLED'}
        stem = safe_name(self.name, fallback="Preset")
        folder = user_preset_dir(create=True)
        path = os.path.join(folder, stem + ".json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"label": self.name, "lights": specs}, f, indent=2)
        except OSError as exc:
            self.report({'ERROR'}, f"Could not save preset: {exc}")
            return {'CANCELLED'}
        context.scene.mv_settings.lighting_preset = USER_PRESET_PREFIX + stem
        self.report({'INFO'}, f"Saved {len(specs)} light(s) as '{stem}'.")
        return {'FINISHED'}


class MV_OT_DeleteLightingPreset(Operator):
    """Delete the selected saved lighting preset. Built-in presets cannot be deleted"""
    bl_idname = "mv.delete_lighting_preset"
    bl_label = "Delete Lighting Preset"

    @classmethod
    def poll(cls, context):
        return context.scene.mv_settings.lighting_preset.startswith(USER_PRESET_PREFIX)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        s = context.scene.mv_settings
        entry = user_lighting_presets().get(s.lighting_preset)
        if entry is None:
            self.report({'ERROR'}, "That preset is not on disk any more.")
            return {'CANCELLED'}
        try:
            os.remove(entry[1])
        except OSError as exc:
            self.report({'ERROR'}, f"Could not delete preset: {exc}")
            return {'CANCELLED'}
        s.lighting_preset = 'STUDIO_SOFT'
        self.report({'INFO'}, f"Deleted lighting preset '{entry[0]}'.")
        return {'FINISHED'}


class MV_OT_AddCustomView(Operator):
    bl_idname = "mv.add_custom_view"
    bl_label = "Add Custom View"

    def execute(self, context):
        cv = context.scene.mv_settings.custom_views.add()
        cv.name = f"Custom_{len(context.scene.mv_settings.custom_views)}"
        return {'FINISHED'}


class MV_OT_RemoveCustomView(Operator):
    bl_idname = "mv.remove_custom_view"
    bl_label = "Remove"
    index: IntProperty()

    def execute(self, context):
        s = context.scene.mv_settings
        if 0 <= self.index < len(s.custom_views):
            s.custom_views.remove(self.index)
        return {'FINISHED'}


class MV_OT_Standardize(Operator):
    bl_idname = "mv.standardize"
    bl_label = "Standardize Products"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.mv_settings
        products = get_products()
        if not products:
            self.report({'ERROR'}, "No products to standardize.")
            return {'CANCELLED'}

        if not (s.recenter or s.rescale or s.auto_smooth):
            self.report({'WARNING'}, "Enable Recenter, Rescale or Auto Smooth first.")
            return {'CANCELLED'}

        context.view_layer.update()
        done = sum(1 for pc in products if collection_meshes(pc))
        unbaked = set()
        smoothed = 0
        if s.recenter or s.rescale:
            unbaked.update(standardize_products(context, products, scale=s.rescale,
                                                recenter=s.recenter))
        for pc in products:
            if s.auto_smooth:
                shaded, skipped_objs = smooth_product(pc, s.smooth_angle)
                smoothed += len(shaded)
                unbaked.update(skipped_objs)

        empty = len(products) - done
        msg = f"Standardized {done} product(s)."
        if s.auto_smooth:
            msg += f" Smoothed {smoothed} mesh(es)."
        if empty:
            msg += f" Skipped {empty} with no geometry."
        if unbaked:
            msg += (f" {len(unbaked)} object(s) kept their transform "
                    "(multi-user or linked data).")
        self.report({'INFO'} if not unbaked else {'WARNING'}, msg)
        return {'FINISHED'}


class MV_OT_RotateProduct(Operator):
    """Turn the active product 90 degrees so it faces the way the view set expects"""
    bl_idname = "mv.rotate_product"
    bl_label = "Rotate Product"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        items=[('LEFT', "Left", "Spin left about the vertical axis"),
               ('RIGHT', "Right", "Spin right about the vertical axis"),
               ('UP', "Up", "Tip the front face up"),
               ('DOWN', "Down", "Tip the front face down")],
        default='LEFT',
    )

    def execute(self, context):
        coll, _ = active_product(context)
        if coll is None:
            self.report({'ERROR'}, f"No product collections under '{PRODUCT_COLL}'.")
            return {'CANCELLED'}
        s = context.scene.mv_settings
        # Isolate first, not after. Rotating reads matrices off the product, so
        # it has to be in the view layer before the maths runs -- and it means
        # you are looking at the thing you are turning while you turn it.
        if s.isolate_active:
            isolate_product(context, coll.name)
            context.view_layer.update()
        step = s.rotate_step
        # The way it faced before the first turn is what Reset goes back to.
        remember_home(coll)
        if not rotate_product(context, coll, self.direction, step):
            self.report({'WARNING'}, f"'{coll.name}' has no geometry to rotate.")
            return {'CANCELLED'}
        self.report({'INFO'},
                    f"Rotated {coll.name} {self.direction.lower()} "
                    f"{math.degrees(step):.0f} degrees.")
        return {'FINISHED'}


def _orient_targets(context, all_products):
    """The products an orientation button acts on, made visible to act on."""
    s = context.scene.mv_settings
    if all_products:
        isolate_product(context, None)
        context.view_layer.update()
        return get_products()
    coll, _ = active_product(context)
    if coll is None:
        return []
    if s.isolate_active:
        isolate_product(context, coll.name)
        context.view_layer.update()
    return [coll]


class MV_OT_AutoOrient(Operator):
    """Turn products to a resting orientation: on their largest flat face, or
    along their principal axes, with the longest side across the Front view"""
    bl_idname = "mv.auto_orient"
    bl_label = "Auto Orient"
    bl_options = {'REGISTER', 'UNDO'}

    all_products: BoolProperty(name="All Products", default=False)

    def execute(self, context):
        s = context.scene.mv_settings
        products = _orient_targets(context, self.all_products)
        if not products:
            self.report({'ERROR'}, f"No product collections under '{PRODUCT_COLL}'.")
            return {'CANCELLED'}
        turned = sum(1 for pc in products if auto_orient(context, pc, s.orient_method))
        if self.all_products:
            # Showing everything was only so they could be measured.
            if s.isolate_active:
                coll, _ = active_product(context)
                isolate_product(context, coll.name if coll else None)
        if not turned:
            self.report({'WARNING'}, "No mesh geometry to orient.")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Oriented {turned} product(s).")
        return {'FINISHED'}


class MV_OT_ResetOrientation(Operator):
    """Turn products back to the orientation they had when imported"""
    bl_idname = "mv.reset_orientation"
    bl_label = "Reset Orientation"
    bl_options = {'REGISTER', 'UNDO'}

    all_products: BoolProperty(name="All Products", default=False)

    def execute(self, context):
        s = context.scene.mv_settings
        products = _orient_targets(context, self.all_products)
        if not products:
            self.report({'ERROR'}, f"No product collections under '{PRODUCT_COLL}'.")
            return {'CANCELLED'}
        reset = sum(1 for pc in products if reset_orientation(pc))
        context.view_layer.update()
        if self.all_products and s.isolate_active:
            coll, _ = active_product(context)
            isolate_product(context, coll.name if coll else None)
        if not reset:
            self.report({'WARNING'}, "Nothing to reset: not turned since import.")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Reset {reset} product(s).")
        return {'FINISHED'}


class MV_OT_ProductStep(Operator):
    """Show the next or previous product on its own, hiding the others"""
    bl_idname = "mv.product_step"
    bl_label = "Step Product"
    bl_options = {'REGISTER', 'UNDO'}

    delta: IntProperty(default=1)

    def execute(self, context):
        products = get_products()
        if not products:
            self.report({'ERROR'}, f"No product collections under '{PRODUCT_COLL}'.")
            return {'CANCELLED'}
        s = context.scene.mv_settings
        _, idx = active_product(context)
        # Wraps, so a review pass round a batch never dead-ends on the last one.
        idx = (idx + self.delta) % len(products)
        s.active_product_index = idx
        if s.isolate_active:
            isolate_product(context, products[idx].name)
        self.report({'INFO'}, f"{products[idx].name}  ({idx + 1}/{len(products)})")
        return {'FINISHED'}


class MV_OT_ShowAllProducts(Operator):
    """Turn isolation off and bring every product back into the view layer"""
    bl_idname = "mv.show_all_products"
    bl_label = "Show All"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        products = get_products()
        if not products:
            self.report({'ERROR'}, f"No product collections under '{PRODUCT_COLL}'.")
            return {'CANCELLED'}
        # Clears the toggle as well as the state. Only unhiding would leave the
        # next rotate to isolate again, which reads as the button not working.
        context.scene.mv_settings.isolate_active = False
        isolate_product(context, None)
        self.report({'INFO'}, f"Showing all {len(products)} product(s).")
        return {'FINISHED'}


class MV_OT_AddProductCollection(Operator):
    bl_idname = "mv.add_product_collection"
    bl_label = "Add Empty Product Collection"
    name: StringProperty(name="Name", default="Product")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # Create unconditionally and report the name that came back. Skipping
        # when the name was taken made the button look broken on the second
        # press -- no collection, no message, nothing in the outliner.
        root = get_products_root()
        coll = bpy.data.collections.new(self.name or "Product")
        root.children.link(coll)
        self.report({'INFO'}, f"Added product collection '{coll.name}'.")
        return {'FINISHED'}


class MV_OT_SetProductsRender(Operator):
    """Tick or untick every product for the next batch render"""
    bl_idname = "mv.set_products_render"
    bl_label = "Set Products Render"
    bl_options = {'REGISTER', 'UNDO'}

    state: BoolProperty(default=True)

    def execute(self, context):
        for pc in get_products():
            pc.mv_render = self.state
        return {'FINISHED'}


def _do_full_render(scene, filepath):
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)


def _do_clay_render(scene, filepath, clay_color):
    saved = {
        'engine': scene.render.engine,
        'shading_type': scene.display.shading.type,
        'light': scene.display.shading.light,
        'color_type': scene.display.shading.color_type,
        'single_color': tuple(scene.display.shading.single_color),
        'show_specular': scene.display.shading.show_specular_highlight,
        'show_cavity': scene.display.shading.show_cavity,
    }
    try:
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.display.shading.type = 'SOLID'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'SINGLE'
        scene.display.shading.single_color = clay_color
        scene.display.shading.show_specular_highlight = False
        scene.display.shading.show_cavity = True
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
    finally:
        scene.render.engine = saved['engine']
        scene.display.shading.type = saved['shading_type']
        scene.display.shading.light = saved['light']
        scene.display.shading.color_type = saved['color_type']
        scene.display.shading.single_color = saved['single_color']
        scene.display.shading.show_specular_highlight = saved['show_specular']
        scene.display.shading.show_cavity = saved['show_cavity']


NORMAL_MATCAP = "check_normal+y.exr"


@contextmanager
def temporarily(*changes):
    """Set (owner, attribute, value) triples, and put every one back on the way
    out, in reverse, even when the body raises. Settings that depend on each
    other (file format before colour depth, light before studio light) are
    set in the order given and restored in the opposite one."""
    saved = []
    try:
        for owner, attr, value in changes:
            old = getattr(owner, attr)
            if not isinstance(old, (str, bytes)) and hasattr(old, "__len__") \
                    and not isinstance(old, bpy.types.ID):
                old = tuple(old)
            saved.append((owner, attr, old))
            setattr(owner, attr, value)
        yield
    finally:
        for owner, attr, old in reversed(saved):
            try:
                setattr(owner, attr, old)
            except (AttributeError, TypeError, ValueError):
                pass


def _png_output(scene):
    image = scene.render.image_settings
    return ((image, "file_format", 'PNG'), (image, "color_mode", 'RGBA'),
            (image, "color_depth", '8'))


def _neutral_view(scene):
    """Display values straight through, so white is white and a normal reads
    back as the number it was."""
    view = scene.view_settings
    return ((view, "view_transform", 'Standard'), (view, "look", 'None'),
            (view, "exposure", 0.0), (view, "gamma", 1.0))


def _render_to(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return written_path(scene, path)


def _save_like_render(scene, px, filepath):
    """Write a computed image where, and in the format, a render would have."""
    image = scene.render.image_settings
    save_pixels(px, written_path(scene, filepath), image.file_format, image.quality)
    scene.render.filepath = filepath


def srgb_decode(rgb):
    rgb = np.clip(rgb, 0.0, 1.0)
    return np.where(rgb <= 0.04045, rgb / 12.92, np.power((rgb + 0.055) / 1.055, 2.4))


def line_mask(normals, crease_angle, width):
    """Where to draw lines, from a render of view-space normals.

    A line goes wherever neighbouring normals differ by more than the crease
    angle, and along every silhouette. Pixels two apart are compared as well
    as adjacent ones, because antialiasing blends one pixel between two faces
    and halves the step each side of it: a 40 degree crease would otherwise
    read as two 20 degree ones and slip under a 30 degree threshold.
    """
    inside = normals[..., 3] > 0.5
    n = srgb_decode(normals[..., :3]) * 2.0 - 1.0
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    limit = math.cos(crease_angle)
    edges = np.zeros(inside.shape, bool)
    for step in (1, 2):
        for axis in (0, 1):
            a = [slice(None)] * 2
            b = [slice(None)] * 2
            a[axis], b[axis] = slice(None, -step), slice(step, None)
            a, b = tuple(a), tuple(b)
            crease = inside[a] & inside[b] & ((n[a] * n[b]).sum(axis=-1) < limit)
            edges[b] |= crease
            if step == 1:
                rim = inside[a] != inside[b]
                edges[a] |= rim & inside[a]
                edges[b] |= rim & inside[b]
    thick = edges.copy()
    for i in range(1, width):
        thick[i:, :] |= edges[:-i, :]
        thick[:, i:] |= edges[:, :-i]
    return thick, inside


def _do_lines_render(scene, filepath, options):
    """Technical-drawing pass: outlines and creases as lines.

    Workbench renders the product with a matcap that colours each pixel by its
    view-space normal, plus object outlines so separate parts that touch still
    get a line between them. The lines are found from that image rather than
    with Freestyle or Line Art, which keeps the pass a fast Workbench render
    and independent of the engine the full render uses.
    """
    angle, width, color, fill, clay_color = options
    work = tempfile.mkdtemp(prefix="mv_lines_")
    try:
        base = None
        if fill == 'CLAY':
            clay = os.path.join(work, "clay")
            _do_clay_render(scene, clay, clay_color)
            base = load_pixels(written_path(scene, clay))
        shading = scene.display.shading
        transparent = scene.render.film_transparent
        with temporarily(
                (scene.render, "engine", 'BLENDER_WORKBENCH'),
                (shading, "type", 'SOLID'),
                (shading, "light", 'MATCAP'),
                (shading, "studio_light", NORMAL_MATCAP),
                (shading, "show_cavity", False),
                (shading, "show_shadows", False),
                (shading, "show_specular_highlight", False),
                (shading, "show_object_outline", True),
                (shading, "object_outline_color", (0.0, 0.0, 0.0)),
                (scene.render, "film_transparent", True),
                (scene.render, "filepath", scene.render.filepath),
                *_neutral_view(scene), *_png_output(scene)):
            normals = load_pixels(_render_to(scene, os.path.join(work, "normals")))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    lines, inside = line_mask(normals, angle, width)
    if base is None:
        base = np.ones(normals.shape, np.float32)
        if fill == 'NONE':
            base[..., 3] = 0.0
        elif transparent:
            base[..., 3] = inside | lines
    ink = np.zeros(normals.shape, np.float32)
    ink[..., :3] = color
    ink[..., 3] = lines
    paste_over(base, ink, 0, 0)
    _save_like_render(scene, base, filepath)


def _do_mask_render(scene, filepath):
    """Silhouette pass: white where the product is, black elsewhere, with
    antialiased edges so it works as a matte."""
    work = tempfile.mkdtemp(prefix="mv_mask_")
    shading = scene.display.shading
    try:
        with temporarily(
                (scene.render, "engine", 'BLENDER_WORKBENCH'),
                (shading, "type", 'SOLID'),
                (shading, "light", 'FLAT'),
                (shading, "color_type", 'SINGLE'),
                (shading, "single_color", (1.0, 1.0, 1.0)),
                (shading, "show_cavity", False),
                (shading, "show_shadows", False),
                (shading, "show_object_outline", False),
                (scene.render, "film_transparent", True),
                (scene.render, "filepath", scene.render.filepath),
                *_png_output(scene)):
            px = load_pixels(_render_to(scene, os.path.join(work, "mask")))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    out = np.empty_like(px)
    out[..., :3] = px[..., 3:4]
    out[..., 3] = 1.0
    _save_like_render(scene, out, filepath)


def _ao_material(distance):
    mat = bpy.data.materials.get("MV_AO") or bpy.data.materials.new("MV_AO")
    tree = node_tree_of(mat)
    tree.nodes.clear()
    ao = tree.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 16
    ao.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    ao.inputs["Distance"].default_value = distance
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.location = (200, 0)
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    tree.links.new(ao.outputs["Color"], emit.inputs["Color"])
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def _ao_world():
    world = bpy.data.worlds.get("MV_AO_World") or bpy.data.worlds.new("MV_AO_World")
    tree = node_tree_of(world)
    tree.nodes.clear()
    bg = tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    out = tree.nodes.new("ShaderNodeOutputWorld")
    tree.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return world


def _do_ao_render(scene, filepath, options):
    """Ambient occlusion pass: Cycles with every surface swapped for a white
    emitter darkened by its own occlusion, so light and materials play no part
    and only the shape shows."""
    samples, distance = options
    if not hasattr(scene, "cycles"):
        raise RuntimeError("the AO pass needs the Cycles add-on enabled")
    with temporarily(
            (scene.render, "engine", 'CYCLES'),
            (scene.cycles, "samples", samples),
            (bpy.context.view_layer, "material_override", _ao_material(distance)),
            (scene, "world", _ao_world()),
            *_neutral_view(scene)):
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)


# -- data passes ------------------------------------------------------------
#
# Depth, normals and part IDs are measurements, not pictures. Each is a Cycles
# render of one sample with every surface swapped for an emitter that outputs
# the number wanted, written as 32-bit EXR so nothing is colour managed,
# clamped or quantized. One sample with a near-zero pixel filter puts every
# pixel on exactly one surface: no antialiasing to average a foreground depth
# with the background, or blend two part IDs into a third that does not exist.

def write_png16(path, values):
    """Write a 2D array of 0-65535 as a 16-bit greyscale PNG, top row first.

    Blender's image API saves 8 bits from Python, which caps a label map at
    255 parts and a depth map at 255 steps, so this writes the file directly.
    """
    values = np.ascontiguousarray(np.clip(values, 0, 65535).astype(">u2"))
    h, w = values.shape
    rows = b"".join(b"\x00" + values[y].tobytes() for y in range(h))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 0, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(rows, 6)))
        f.write(chunk(b"IEND", b""))


def read_png16(path):
    """Read back a 16-bit greyscale PNG written by write_png16."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            w, h, depth, colour = struct.unpack(">IIBB", body[:10])
            if depth != 16 or colour != 0:
                raise ValueError("not a 16-bit greyscale PNG")
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(h, 1 + w * 2)
    if raw[:, 0].any():
        raise ValueError("row filters other than None are not supported")
    return raw[:, 1:].copy().view(">u2").astype(np.uint16)


def _black_world():
    world = bpy.data.worlds.get("MV_Data_World") or bpy.data.worlds.new("MV_Data_World")
    tree = node_tree_of(world)
    tree.nodes.clear()
    bg = tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bg.inputs["Strength"].default_value = 0.0
    out = tree.nodes.new("ShaderNodeOutputWorld")
    tree.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return world


def _data_material(kind):
    """An emitter whose colour is the measurement itself."""
    name = f"MV_Data_{kind}"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    tree = node_tree_of(mat)
    tree.nodes.clear()
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    if kind == "depth":
        cam = tree.nodes.new("ShaderNodeCameraData")
        cam.location = (-300, 0)
        tree.links.new(cam.outputs["View Z Depth"], emit.inputs["Color"])
    elif kind == "normal":
        # World space here; _do_normal_render turns it into camera space with
        # the camera's own matrix. Cycles' "camera space" points Z the other
        # way from OpenGL, so relying on it would flip every normal.
        geo = tree.nodes.new("ShaderNodeNewGeometry")
        geo.location = (-300, 0)
        tree.links.new(geo.outputs["Normal"], emit.inputs["Color"])
    else:
        info = tree.nodes.new("ShaderNodeObjectInfo")
        info.location = (-300, 0)
        tree.links.new(info.outputs["Object Index"], emit.inputs["Color"])
    return mat


def _render_data(scene, filepath, kind, extra=()):
    if not hasattr(scene, "cycles"):
        raise RuntimeError(f"the {kind} pass needs the Cycles add-on enabled")
    image = scene.render.image_settings
    with temporarily(
            (scene.render, "engine", 'CYCLES'),
            (scene.cycles, "samples", 1),
            (scene.cycles, "use_denoising", False),
            (scene.cycles, "use_adaptive_sampling", False),
            (scene.cycles, "filter_width", 0.01),
            (scene.render, "use_motion_blur", False),
            (scene.render, "film_transparent", True),
            (scene.render, "use_file_extension", True),
            (bpy.context.view_layer, "material_override", _data_material(kind)),
            (scene, "world", _black_world()),
            (image, "file_format", 'OPEN_EXR'),
            (image, "color_mode", 'RGBA'),
            (image, "color_depth", '32'),
            *_neutral_view(scene),
            *extra):
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
    return filepath + ".exr"


def _do_depth_render(scene, filepath):
    """Distance along the camera's view axis, in scene units, in R, G and B;
    0 and alpha 0 where nothing was hit."""
    _render_data(scene, filepath, "depth")


def save_exr(px, path):
    """Write float RGBA pixels (rows bottom to top) to a 32-bit EXR as is."""
    h, w = px.shape[:2]
    img = bpy.data.images.new("MV_Data", w, h, alpha=True, float_buffer=True)
    try:
        img.pixels.foreach_set(np.ascontiguousarray(px, dtype=np.float32).ravel())
        img.filepath_raw = path
        img.file_format = 'OPEN_EXR'
        img.save()
    finally:
        bpy.data.images.remove(img)


def _do_normal_render(scene, filepath):
    """Shading normals in camera space, OpenGL convention: +X right, +Y up,
    +Z towards the camera. Values in -1..1, not remapped."""
    work = tempfile.mkdtemp(prefix="mv_normal_")
    try:
        px = load_pixels(_render_data(scene, os.path.join(work, "world"), "normal"), raw=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    to_cam = np.array(scene.camera.matrix_world.to_3x3().normalized().transposed())
    hit = px[..., 3] > 0.5
    px[..., :3] = np.where(hit[..., None], px[..., :3] @ to_cam.T, 0.0)
    save_exr(px, filepath + ".exr")
    scene.render.filepath = filepath


def _do_parts_render(scene, filepath, part_map):
    """Which part every pixel shows, as a 16-bit PNG: 0 is background, n is
    the n-th part in the product's part list. Returns the label array.

    Part numbers go in through each object's pass index, set only for the
    render and put back afterwards.
    """
    extra = []
    for name, part_id in part_map.items():
        obj = bpy.data.objects.get(name)
        if obj is not None:
            extra.append((obj, "pass_index", part_id))
    work = tempfile.mkdtemp(prefix="mv_parts_")
    try:
        exr = _render_data(scene, os.path.join(work, "ids"), "ids", extra)
        px = load_pixels(exr, raw=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    labels = np.where(px[..., 3] > 0.5, np.rint(px[..., 0]), 0).astype(np.int64)
    labels = np.clip(labels, 0, 65535)[::-1]
    write_png16(filepath + ".png", labels)
    scene.render.filepath = filepath
    return labels


# (name, render function, file extension). Unlike the image modes these are
# never post-processed or put on a contact sheet: they are data.
def data_modes(settings):
    s = settings
    modes = []
    if s.pass_depth or s.export_bop:
        modes.append(("depth", _do_depth_render, ".exr"))
    if s.pass_normal:
        modes.append(("normal", _do_normal_render, ".exr"))
    if s.pass_parts or s.export_coco:
        modes.append(("parts", _do_parts_render, ".png"))
    return modes


def part_list(coll):
    """The product's parts, numbered from 1 in name order, as written into
    the part-ID images and cameras.json."""
    meshes = sorted((o for o in collection_meshes(coll) if o.type == 'MESH'),
                    key=lambda o: o.name)
    return {o.name: i + 1 for i, o in enumerate(meshes)}


# -- cameras --------------------------------------------------------------------

def render_resolution(scene):
    r = scene.render
    return (int(r.resolution_x * r.resolution_percentage / 100),
            int(r.resolution_y * r.resolution_percentage / 100))


def camera_record(scene, cam):
    """Everything needed to project the scene into one of this camera's images.

    Extrinsics come in both conventions in use: camera-to-world in OpenGL axes
    (Blender's own, and nerfstudio's: +Y up, looking down -Z) and
    world-to-camera in OpenCV axes (+Y down, looking down +Z; COLMAP and BOP).
    Perspective cameras get a pinhole K. Orthographic ones get the size of a
    pixel in scene units instead, since no K describes them.
    """
    r = scene.render
    w, h = render_resolution(scene)
    data = cam.data
    c2w = cam.matrix_world.normalized()
    flip = Matrix(((1, 0, 0, 0), (0, -1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))
    w2c_cv = flip @ c2w.inverted()
    pax, pay = r.pixel_aspect_x, r.pixel_aspect_y
    fit = data.sensor_fit
    if fit == 'AUTO':
        fit = 'HORIZONTAL' if w * pax >= h * pay else 'VERTICAL'
    aspect = pay / pax
    across = w if fit == 'HORIZONTAL' else h * aspect
    record = {
        "camera": cam.name,
        "width": w, "height": h,
        "c2w_opengl": [list(row) for row in c2w],
        "w2c_opencv": [list(row) for row in w2c_cv],
    }
    if data.type == 'ORTHO':
        size = data.ortho_scale / across
        record.update(projection="orthographic", ortho_scale=data.ortho_scale,
                      pixel_size=[size, size * aspect],
                      principal_point=[w / 2 - data.shift_x * across,
                                       h / 2 + data.shift_y * across / aspect])
    else:
        sensor = data.sensor_height if fit == 'VERTICAL' else data.sensor_width
        fx = data.lens / sensor * across
        fy = fx / aspect
        cx = w / 2 - data.shift_x * across
        cy = h / 2 + data.shift_y * across / aspect
        record.update(projection="perspective", lens_mm=data.lens,
                      K=[[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]])
    record["clip"] = [data.clip_start, data.clip_end]
    return record


def written_path(scene, path):
    """Where render.render(write_still=True) puts an image asked for at path.

    Blender appends the format's extension itself while File Extensions is on,
    so a skip check that looked for the bare path would never find anything and
    a resumed batch would quietly render everything again.
    """
    r = scene.render
    return path + r.file_extension if r.use_file_extension else path


def file_ok(path):
    """True for a file worth keeping. An empty one is what a crash mid-write
    leaves behind, and is exactly the file a resume is for."""
    return os.path.isfile(path) and os.path.getsize(path) > 0


def format_duration(seconds):
    seconds = max(int(round(seconds)), 0)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


# -- naming ---------------------------------------------------------------

DEFAULT_FILE_TEMPLATE = "{label}_{product}_{view}_{mode}"
DEFAULT_FOLDER_TEMPLATE = "{label}_{product}"
TEMPLATE_TOKEN = re.compile(r"\{(\w+)\}")
TEMPLATE_SEPARATORS = "_-. "


def expand_template(template, values):
    """Fill {token}s from values.

    An empty value takes one neighbouring separator with it, so the blank
    {mode} of a Full Render turns 'AA_01_Widget_Front_{mode}' into
    'AA_01_Widget_Front' rather than leaving a dangling underscore. Unknown
    tokens are left exactly as typed, so a typo shows up in the panel preview
    instead of silently vanishing from every filename.
    """
    out = ""
    pos = 0
    eat_next = False
    for m in TEMPLATE_TOKEN.finditer(template):
        literal = template[pos:m.start()]
        if eat_next and literal and literal[0] in TEMPLATE_SEPARATORS:
            literal = literal[1:]
        eat_next = False
        out += literal
        key = m.group(1)
        if key not in values:
            out += m.group(0)
        elif values[key]:
            out += values[key]
        elif out and out[-1] in TEMPLATE_SEPARATORS:
            out = out[:-1]
        else:
            eat_next = True
        pos = m.end()
    literal = template[pos:]
    if eat_next and literal and literal[0] in TEMPLATE_SEPARATORS:
        literal = literal[1:]
    return out + literal


def name_values(settings, index, product, view, mode):
    label = product_label(settings.start_prefix, settings.start_number, index,
                          settings.products_per_letter)
    prefix, _, number = label.rpartition("_")
    return {"label": label, "prefix": prefix, "number": number,
            "product": product, "view": view, "mode": mode}


def output_folder(settings, values):
    """Folder under the output directory, from the folder template.

    Each / separated level is sanitized on its own, so a template can nest
    folders but a product name can never climb out of the output directory:
    '..' sanitizes to nothing and the level is dropped.
    """
    levels = []
    for part in re.split(r"[\\/]+", settings.folder_template or ""):
        level = safe_name(expand_template(part, values), fallback="")
        if level:
            levels.append(level)
    return os.path.join(*levels) if levels else ""


def output_basename(settings, values):
    return safe_name(expand_template(settings.file_template or DEFAULT_FILE_TEMPLATE, values))


class _NameClash(Exception):
    """Two outputs of one batch would be written to the same file."""


# -- image buffers ----------------------------------------------------------
#
# Everything below works on float32 RGBA arrays shaped (height, width, 4), in
# 0-1, with rows bottom to top as Blender stores them. Values are the encoded
# 8-bit display values straight out of the file, never linearized, so an image
# read and written back is byte for byte what Render wrote.

POST_FORMATS = {'PNG': ".png", 'JPEG': ".jpg", 'WEBP': ".webp"}


def srgb_encode(rgb):
    rgb = np.clip(rgb, 0.0, None)
    return np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)


def load_pixels(path, raw=False):
    """RGBA pixels of an image file. raw keeps float data exactly as stored,
    for depth, normal and ID passes where the numbers are measurements."""
    img = bpy.data.images.load(path, check_existing=False)
    try:
        w, h = img.size
        if not w or not h:
            raise RuntimeError("Blender could not read the image")
        px = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        px = px.reshape(h, w, 4)
        if raw:
            return px
        if img.is_float:
            # 16-bit PNG and EXR come in as scene-linear floats. Encode them
            # back to display values so they sit with everything else; EXR
            # skips the view transform a PNG would have had baked in.
            px[..., :3] = srgb_encode(px[..., :3])
        return np.clip(px, 0.0, 1.0)
    finally:
        bpy.data.images.remove(img)


def image_size(path):
    try:
        img = bpy.data.images.load(path, check_existing=False)
    except RuntimeError:
        return None, None
    try:
        w, h = img.size
        return (w, h) if w and h else (None, None)
    finally:
        bpy.data.images.remove(img)


def save_pixels(px, path, file_format, quality=90):
    h, w = px.shape[:2]
    img = bpy.data.images.new("MV_Output", w, h, alpha=True, float_buffer=False)
    try:
        img.pixels.foreach_set(np.ascontiguousarray(np.clip(px, 0.0, 1.0), dtype=np.float32).ravel())
        img.filepath_raw = path
        img.file_format = file_format
        try:
            img.save(quality=quality)
        except TypeError:
            img.save()
    finally:
        bpy.data.images.remove(img)


def bilinear(px, new_w, new_h):
    h, w = px.shape[:2]
    ys = (np.arange(new_h) + 0.5) * h / new_h - 0.5
    xs = (np.arange(new_w) + 0.5) * w / new_w - 0.5
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    wy = np.clip(ys - y0, 0.0, 1.0)[:, None, None]
    wx = np.clip(xs - x0, 0.0, 1.0)[None, :, None]
    y1 = np.clip(y0 + 1, 0, h - 1)
    x1 = np.clip(x0 + 1, 0, w - 1)
    y0 = np.clip(y0, 0, h - 1)
    x0 = np.clip(x0, 0, w - 1)
    top = px[y0][:, x0] * (1 - wx) + px[y0][:, x1] * wx
    bottom = px[y1][:, x0] * (1 - wx) + px[y1][:, x1] * wx
    return (top * (1 - wy) + bottom * wy).astype(np.float32)


def resize_pixels(px, new_w, new_h):
    """Resample with alpha premultiplied, so transparent pixels' colour cannot
    bleed a dark fringe into the edge of the product."""
    h, w = px.shape[:2]
    new_w, new_h = max(int(new_w), 1), max(int(new_h), 1)
    if (w, h) == (new_w, new_h):
        return px
    alpha = px[..., 3:4]
    pm = np.concatenate([px[..., :3] * alpha, alpha], axis=-1)
    # Box-average whole factors first: bilinear alone only samples four
    # pixels, which aliases badly when shrinking a 4K render to a thumbnail.
    fy, fx = max(1, h // new_h), max(1, w // new_w)
    if fx > 1 or fy > 1:
        hh, ww = (h // fy) * fy, (w // fx) * fx
        pm = pm[:hh, :ww].reshape(hh // fy, fy, ww // fx, fx, 4).mean(axis=(1, 3))
    pm = bilinear(pm, new_w, new_h)
    alpha = pm[..., 3:4]
    rgb = pm[..., :3] / np.maximum(alpha, 1e-6)
    rgb = np.where(alpha > 1e-6, rgb, 0.0)
    return np.concatenate([rgb, alpha], axis=-1).astype(np.float32)


def fit_long_edge(px, size):
    h, w = px.shape[:2]
    scale = size / max(w, h)
    return resize_pixels(px, round(w * scale), round(h * scale))


def flatten(px, color):
    out = np.empty_like(px)
    alpha = px[..., 3:4]
    out[..., :3] = px[..., :3] * alpha + np.asarray(color[:3], np.float32) * (1 - alpha)
    out[..., 3] = 1.0
    return out


def has_transparency(px):
    return bool(px[..., 3].min() < 0.99)


def background_of(px):
    """The colour a product sits on: transparent when there is alpha to use,
    otherwise whatever the four corners agree on."""
    if has_transparency(px):
        return np.zeros(4, np.float32)
    corners = np.stack([px[0, 0], px[0, -1], px[-1, 0], px[-1, -1]])
    return np.median(corners, axis=0).astype(np.float32)


def content_box(px, background):
    """(x0, y0, x1, y1) around everything that is not background, or None."""
    if has_transparency(px):
        mask = px[..., 3] > 0.02
    else:
        mask = np.abs(px[..., :3] - background[:3]).max(axis=-1) > 0.02
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if not rows.size:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def pad_pixels(px, left, right, bottom, top, fill):
    h, w = px.shape[:2]
    out = np.empty((h + bottom + top, w + left + right, 4), np.float32)
    out[:] = fill
    out[bottom:bottom + h, left:left + w] = px
    return out


def paste_over(canvas, src, x, y):
    """Composite src onto canvas with its bottom-left corner at (x, y)."""
    h, w = src.shape[:2]
    big_h, big_w = canvas.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, big_w), min(y + h, big_h)
    if x0 >= x1 or y0 >= y1:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    d = canvas[y0:y1, x0:x1]
    sa, da = s[..., 3:4], d[..., 3:4]
    out_a = sa + da * (1 - sa)
    rgb = (s[..., :3] * sa + d[..., :3] * da * (1 - sa)) / np.maximum(out_a, 1e-6)
    canvas[y0:y1, x0:x1] = np.concatenate([rgb, out_a], axis=-1)


def post_process(px, settings):
    """Trim, pad and resize one image the way the Post-Processing panel asks."""
    background = background_of(px)
    if settings.post_trim:
        box = content_box(px, background)
        if box is not None:
            x0, y0, x1, y1 = box
            px = px[y0:y1, x0:x1]
            margin = int(round(settings.post_margin * max(x1 - x0, y1 - y0)))
            if margin:
                px = pad_pixels(px, margin, margin, margin, margin, background)
    if settings.post_square:
        h, w = px.shape[:2]
        if w != h:
            side = max(w, h)
            left, bottom = (side - w) // 2, (side - h) // 2
            px = pad_pixels(px, left, side - w - left, bottom, side - h - bottom, background)
    # JPEG has no alpha channel. Dropping it unflattened leaves the RGB that
    # transparent pixels happen to hold, which for a render is black.
    if settings.post_flatten or settings.post_format == 'JPEG':
        px = flatten(px, settings.post_bg_color)
    if settings.post_max_size and max(px.shape[:2]) > settings.post_max_size:
        px = fit_long_edge(px, settings.post_max_size)
    return px


def parse_sizes(text):
    sizes = {int(v) for v in re.findall(r"\d+", text or "") if int(v) >= 8}
    return sorted(sizes, reverse=True)


# -- contact sheets -----------------------------------------------------------

def text_mask(text, size, tmp_dir):
    """Coverage (height, width) of text in Blender's UI font, or None on a
    Blender that cannot draw text into an image buffer."""
    if not hasattr(blf, "bind_imbuf"):
        return None
    import imbuf
    font = 0
    blf.size(font, size)
    width, _ = blf.dimensions(font, text)
    buf = imbuf.new((max(int(width) + 4, 1), int(size * 1.5) + 4))
    with blf.bind_imbuf(font, buf):
        blf.color(font, 1.0, 1.0, 1.0, 1.0)
        blf.position(font, 2, int(size * 0.35) + 2, 0)
        blf.draw_buffer(font, text)
    # imbuf has no pixel access from Python, so the text goes through a file.
    path = os.path.join(tmp_dir, "mv_text.png")
    imbuf.write(buf, filepath=path)
    return load_pixels(path)[..., 0]


def contact_sheet(cells, title, settings, tmp_dir):
    """Lay out [(caption, pixels)] on one canvas, captions under each view and
    the product's name across the top. Cells arrive already scaled to the
    sheet's cell width."""
    cell_w = settings.sheet_cell_width
    cell_h = max(px.shape[0] for _, px in cells)
    n = len(cells)
    cols = min(settings.sheet_columns or math.ceil(math.sqrt(n)), n)
    rows = math.ceil(n / cols)
    gap = max(8, cell_w // 24)
    caption_size = max(11, cell_w // 20)
    title_size = int(caption_size * 1.5)
    labels = settings.sheet_labels and hasattr(blf, "bind_imbuf")
    caption_h = int(caption_size * 1.8) if labels else 0
    title_h = int(title_size * 2.0) if labels else 0

    width = cols * cell_w + (cols + 1) * gap
    height = title_h + rows * (cell_h + caption_h) + (rows + 1) * gap
    canvas = np.empty((height, width, 4), np.float32)
    canvas[:] = settings.sheet_bg
    ink = np.asarray(settings.sheet_text_color, np.float32)

    def draw_text(text, size, x, y_top, max_w):
        mask = text_mask(text, size, tmp_dir)
        if mask is None:
            return
        mask = mask[:, :max_w]
        layer = np.empty(mask.shape + (4,), np.float32)
        layer[..., :3] = ink
        layer[..., 3] = mask
        paste_over(canvas, layer, x, height - y_top - mask.shape[0])

    if labels:
        draw_text(title, title_size, gap, int(title_size * 0.4), width - 2 * gap)
    for i, (caption, px) in enumerate(cells):
        row, col = divmod(i, cols)
        x = gap + col * (cell_w + gap)
        y_top = title_h + gap + row * (cell_h + caption_h + gap)
        offset = (cell_h - px.shape[0]) // 2
        # Rows are stored bottom up, so a top-down layout position flips.
        paste_over(canvas, px, x, height - (y_top + offset) - px.shape[0])
        if labels:
            draw_text(caption, caption_size, x, y_top + cell_h + int(caption_size * 0.2), cell_w)
    return canvas


# -- turntables ---------------------------------------------------------------

TURNTABLE_CAM = "MV_Turntable_Cam"


def build_turntable_camera(context):
    """A perspective camera that keeps every product in frame at every angle.

    Each product spins about its own centre, so the framing is a cylinder
    around the batch centre wide enough for the product that reaches furthest
    from it, measured from all sides at once.
    """
    scene = context.scene
    s = scene.mv_settings
    boxes = []
    for pc in get_products():
        objs = collection_meshes(pc)
        if objs:
            boxes.append(bbox_of(objs))
    if not boxes:
        return None
    lo = Vector([min(c[i] - sz[i] / 2 for c, sz in boxes) for i in range(3)])
    hi = Vector([max(c[i] + sz[i] / 2 for c, sz in boxes) for i in range(3)])
    center = (lo + hi) * 0.5
    radius = 0.0
    for c, sz in boxes:
        reach = Vector((c.x - center.x, c.y - center.y)).length
        radius = max(radius, reach + 0.5 * Vector((sz.x, sz.y)).length)
    steps = 24
    # A polygon through the circle's points would cut inside it between them.
    radius = max(radius, 1e-3) / math.cos(math.pi / steps)
    corners = [center + Vector((radius * math.cos(a), radius * math.sin(a), z - center.z))
               for a in (2 * math.pi * k / steps for k in range(steps))
               for z in (lo.z, hi.z)]

    elevation = s.turntable_elevation
    d = Vector(rotate_dir_z((0.0, -math.cos(elevation), math.sin(elevation)),
                            FRONT_AXIS_ANGLES[s.front_axis])).normalized()
    _, _, depth, local = view_extents(look_at(center + d, center), center, corners)
    rx, ry = image_aspect(scene)
    tan_x, tan_y = sensor_tangents(rx, ry)
    pad = max(s.frame_padding_factor, 1.0)
    diag = max((hi - lo).length * 0.5, 1e-3)
    distance = max(persp_distance(local, tan_x, tan_y, pad), depth + diag * 0.1)

    data = bpy.data.cameras.new(TURNTABLE_CAM)
    data.lens = PERSP_LENS
    data.clip_start = max(distance * 0.01, 1e-5)
    data.clip_end = (distance + diag) * 100.0
    cam = bpy.data.objects.new(TURNTABLE_CAM, data)
    cam.matrix_world = look_at(center + d * distance, center)
    # Linked to the scene, not MV_Cameras, so it is never mistaken for a view.
    scene.collection.objects.link(cam)
    return cam


def remove_object(obj):
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if isinstance(data, bpy.types.Camera) and not data.users:
        bpy.data.cameras.remove(data)


def encode_mp4(frames, out_path, fps, background, tmp_dir):
    """H.264 from a list of frame files, through a throwaway sequencer scene.

    Frames are flattened onto the background first, because H.264 has no alpha
    and the sequencer would otherwise put a transparent render on black, and
    cropped to even dimensions, which the codec requires.
    """
    work = tempfile.mkdtemp(prefix="mv_mp4_", dir=tmp_dir)
    names = []
    width = height = None
    try:
        for i, frame in enumerate(frames):
            px = flatten(load_pixels(frame), background)
            if width is None:
                height, width = px.shape[:2]
                width -= width % 2
                height -= height % 2
            name = f"frame_{i + 1:04d}.png"
            save_pixels(px[:height, :width], os.path.join(work, name), 'PNG')
            names.append(name)

        scene = bpy.data.scenes.new("MV_Encode")
        try:
            r = scene.render
            r.resolution_x, r.resolution_y = width, height
            r.resolution_percentage = 100
            r.pixel_aspect_x = r.pixel_aspect_y = 1.0
            r.fps, r.fps_base = int(fps), 1.0
            scene.frame_start, scene.frame_end = 1, len(names)
            editor = scene.sequence_editor_create()
            # Blender 4.4 renamed sequences to strips. Not getattr(...) or:
            # a new editor's strips is empty, which reads as false.
            strips = editor.strips if hasattr(editor, "strips") else editor.sequences
            strip = strips.new_image(name="MV_Frames", filepath=os.path.join(work, names[0]),
                                     channel=1, frame_start=1)
            for name in names[1:]:
                strip.elements.append(name)
            image = r.image_settings
            if hasattr(image, "media_type"):
                image.media_type = 'VIDEO'
            image.file_format = 'FFMPEG'
            r.ffmpeg.format = 'MPEG4'
            r.ffmpeg.codec = 'H264'
            r.ffmpeg.constant_rate_factor = 'HIGH'
            # The frames are display values already; a second view transform
            # on the way out would wash them out.
            scene.view_settings.view_transform = 'Standard'
            scene.view_settings.look = 'None'
            r.use_sequencer = True
            r.use_compositing = False
            r.filepath = os.path.join(work, "turntable")
            # Blender 5 takes the range from the operator, and left unset it
            # reads the window's scene: 250 frames, 242 of them black.
            kwargs = {}
            props = bpy.ops.render.render.get_rna_type().properties
            if "frame_start" in props:
                kwargs = {"frame_start": 1, "frame_end": len(names)}
            bpy.ops.render.render(animation=True, scene=scene.name, **kwargs)
        finally:
            bpy.data.scenes.remove(scene)

        produced = [n for n in os.listdir(work) if n.lower().endswith(".mp4")]
        if not produced:
            raise RuntimeError("Blender's FFmpeg wrote no video")
        os.replace(os.path.join(work, produced[0]), out_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return width, height


def gif_lzw(data):
    """GIF's variable-width LZW over 8-bit palette indices, packed into the
    255-byte sub-blocks the format wants."""
    clear, end = 256, 257
    out = bytearray()
    buf = nbits = 0
    size = 9
    table = {}
    next_code = 258

    buf |= clear << nbits
    nbits += size
    it = iter(data)
    prefix = next(it)
    for byte in it:
        key = (prefix << 8) | byte
        code = table.get(key)
        if code is not None:
            prefix = code
            continue
        buf |= prefix << nbits
        nbits += size
        while nbits >= 8:
            out.append(buf & 0xFF)
            buf >>= 8
            nbits -= 8
        if next_code < 4096:
            table[key] = next_code
            next_code += 1
            if next_code > (1 << size) and size < 12:
                size += 1
        else:
            # Table full: start over rather than coding on with a stale one.
            buf |= clear << nbits
            nbits += size
            table.clear()
            next_code = 258
            size = 9
        prefix = byte
    for code in (prefix, end):
        buf |= code << nbits
        nbits += size
        while nbits >= 8:
            out.append(buf & 0xFF)
            buf >>= 8
            nbits -= 8
    if nbits:
        out.append(buf & 0xFF)

    blocks = bytearray()
    for i in range(0, len(out), 255):
        chunk = out[i:i + 255]
        blocks.append(len(chunk))
        blocks += chunk
    blocks.append(0)
    return bytes(blocks)


def encode_gif(frames, out_path, fps, max_size, background):
    """Looping GIF from frame files.

    One palette for the whole animation, from the colours used most across
    every frame, so the background does not shimmer from frame to frame the
    way per-frame palettes make it.
    """
    images = []
    for frame in frames:
        px = flatten(load_pixels(frame), background)
        if max_size and max(px.shape[:2]) > max_size:
            px = fit_long_edge(px, max_size)
        # GIF stores rows top down.
        images.append((px[::-1, :, :3] * 255 + 0.5).astype(np.uint8))
    height, width = images[0].shape[:2]

    # 6 bits a channel keeps 64 levels of grey for a clay render's shading.
    keys = []
    for rgb in images:
        q = (rgb >> 2).astype(np.uint32)
        keys.append((q[..., 0] << 12) | (q[..., 1] << 6) | q[..., 2])
    used, counts = np.unique(np.concatenate([k.ravel() for k in keys]), return_counts=True)
    top = used[np.argsort(counts)[::-1][:256]]

    def expand(k):
        return np.stack([(k >> 12) & 63, (k >> 6) & 63, k & 63], axis=-1).astype(np.int32) * 4 + 2

    palette = expand(top)
    lut = np.empty(len(used), np.uint8)
    colours = expand(used)
    for i in range(0, len(used), 4096):
        dist = ((colours[i:i + 4096, None, :] - palette[None, :, :]) ** 2).sum(axis=-1)
        lut[i:i + 4096] = dist.argmin(axis=1)

    table = np.zeros((256, 3), np.uint8)
    table[:len(palette)] = np.clip(palette, 0, 255)
    out = bytearray(b"GIF89a")
    out += struct.pack("<HHBBB", width, height, 0xF7, 0, 0)
    out += table.tobytes()
    out += b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00"
    delay = max(2, int(round(100 / max(fps, 1))))
    for k in keys:
        indices = lut[np.searchsorted(used, k.ravel())]
        out += b"\x21\xF9\x04\x04" + struct.pack("<H", delay) + b"\x00\x00"
        out += b"\x2C" + struct.pack("<HHHHB", 0, 0, width, height, 0)
        out += b"\x08" + gif_lzw(indices.tobytes())
    out += b"\x3B"
    with open(out_path, "wb") as f:
        f.write(out)
    return width, height


# -- manifest -----------------------------------------------------------------

MEASURABLE_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".exr", ".tif", ".tiff", ".bmp"}
MANIFEST_FIELDS = ("label", "product", "kind", "view", "mode", "path",
                   "width", "height", "source_file", "source_size", "source_units")


def read_manifest(out_root, name="manifest"):
    json_path = os.path.join(out_root, name + ".json")
    csv_path = os.path.join(out_root, name + ".csv")
    try:
        if os.path.isfile(json_path):
            with open(json_path, encoding="utf-8") as f:
                return list(json.load(f).get("images", []))
        if os.path.isfile(csv_path):
            with open(csv_path, encoding="utf-8", newline="") as f:
                return list(csv.DictReader(f))
    except (OSError, ValueError, AttributeError):
        pass
    return []


def write_manifest(out_root, records, labels, fmt, name="manifest"):
    """Merge this run's outputs into manifest.json / manifest.csv.

    Rows for products this run did not touch are carried over, so rendering
    one product does not wipe the rest of the batch from the list. Rows for
    files that are no longer on disk are dropped.
    """
    rows = [r for r in read_manifest(out_root, name) if r.get("label") not in labels]
    for rec in records:
        if not file_ok(rec["path"]):
            continue
        width, height = rec.get("width"), rec.get("height")
        if width is None and file_ext(rec["path"]) in MEASURABLE_IMAGES:
            width, height = image_size(rec["path"])
        row = {k: rec.get(k) for k in MANIFEST_FIELDS}
        row.update(path=os.path.relpath(rec["path"], out_root).replace("\\", "/"),
                   width=width, height=height)
        rows.append(row)
    rows = [r for r in rows if file_ok(os.path.join(out_root, str(r.get("path", ""))))]
    rows.sort(key=lambda r: (str(r.get("label")), str(r.get("kind")), str(r.get("path"))))

    if fmt in {'JSON', 'BOTH'}:
        with open(os.path.join(out_root, name + ".json"), "w", encoding="utf-8") as f:
            json.dump({"generated": datetime.now().isoformat(timespec="seconds"),
                       "images": rows}, f, indent=2)
    if fmt in {'CSV', 'BOTH'}:
        with open(os.path.join(out_root, name + ".csv"), "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                size = row.get("source_size")
                if isinstance(size, (list, tuple)):
                    row = dict(row, source_size=" x ".join(f"{v:g}" for v in size))
                writer.writerow(row)
    return len(rows)


def render_modes(settings):
    """(mode, render function, extra arguments) for every image each view gets."""
    s = settings
    clay = (tuple(s.clay_color),)
    modes = list({
        'FULL': (("", _do_full_render, ()),),
        'CLAY': (("clay", _do_clay_render, clay),),
        'BOTH': (("render", _do_full_render, ()), ("clay", _do_clay_render, clay)),
    }[s.render_mode])
    if s.pass_lines:
        modes.append(("lines", _do_lines_render,
                      ((s.lines_angle, s.lines_width, tuple(s.lines_color),
                        s.lines_fill, tuple(s.clay_color)),)))
    if s.pass_mask:
        modes.append(("mask", _do_mask_render, ()))
    if s.pass_ao:
        # Relative to the batch, like the rest of the rig: the same setting
        # suits a screw and a housing scaled to one Target Size.
        modes.append(("ao", _do_ao_render,
                      ((s.ao_samples, s.ao_distance * batch_extent()[1]),)))
    return modes


# -- pre-flight -----------------------------------------------------------------

def framing_signature(context):
    """Everything a camera rig's framing depends on, rounded, as one string.

    Stored on MV_Cameras when the rig is built and compared before a render,
    so cameras left over from before a product was turned, rescaled or added,
    or before the resolution or views changed, are caught instead of cropping
    a whole batch.
    """
    s = context.scene.mv_settings
    objs = []
    for pc in get_products():
        objs.extend(pc.all_objects)
    center, size = bbox_of(objs)
    rx, ry = image_aspect(context.scene)
    return json.dumps({
        "box": [round(v, 4) for v in (*center, *size)],
        "views": [(name, kind, [round(c, 4) for c in d]) for name, kind, d in planned_views(s)],
        "front": s.front_axis, "pad": round(s.frame_padding_factor, 4),
        "aspect": round(rx / ry, 4),
    }, sort_keys=True)


def normal_problems(obj):
    """(edges where neighbouring faces disagree, mesh is inside out) for a mesh.

    Two faces sharing an edge should run along it in opposite directions; where
    they run the same way one of them is flipped. A closed mesh whose faces all
    agree but enclose a negative volume is flipped as a whole.
    """
    me = obj.data
    n_loops, n_polys = len(me.loops), len(me.polygons)
    if not n_polys:
        return 0, False
    verts = np.empty(n_loops, np.int64)
    me.loops.foreach_get("vertex_index", verts)
    starts = np.empty(n_polys, np.int64)
    totals = np.empty(n_polys, np.int64)
    me.polygons.foreach_get("loop_start", starts)
    me.polygons.foreach_get("loop_total", totals)
    following = np.arange(1, n_loops + 1)
    following[starts + totals - 1] = starts
    a, b = verts, verts[following]
    key = np.minimum(a, b) * max(len(me.vertices), 1) + np.maximum(a, b)
    order = np.argsort(key, kind="stable")
    key, forward = key[order], (a < b)[order]
    _, first, counts = np.unique(key, return_index=True, return_counts=True)
    pairs = first[counts == 2]
    disagree = int((forward[pairs] == forward[pairs + 1]).sum())
    if disagree or (counts == 1).any():
        return disagree, False
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    tri = np.empty(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", tri)
    p = co.reshape(-1, 3)[tri.reshape(-1, 3)]
    volume = np.einsum("ij,ij->i", p[:, 0], np.cross(p[:, 1], p[:, 2])).sum()
    volume *= np.sign(obj.matrix_world.to_3x3().determinant()) or 1.0
    return 0, bool(volume < 0)


def fix_normals(coll):
    """Make every face of a product point outwards. Returns meshes changed."""
    import bmesh
    fixed = 0
    for obj in collection_meshes(coll):
        if obj.type != 'MESH' or obj.library or obj.data.library:
            continue
        bm = bmesh.new()
        try:
            bm.from_mesh(obj.data)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(obj.data)
        finally:
            bm.free()
        obj.data.update()
        fixed += 1
    return fixed


def _names_clash(settings, targets, views, modes):
    seen = set()
    for idx, pc in targets:
        for view in views:
            for mode in modes:
                values = name_values(settings, idx, pc.name, view, mode)
                key = os.path.normcase(os.path.join(output_folder(settings, values),
                                                    output_basename(settings, values)))
                if key in seen:
                    return True
                seen.add(key)
    return False


def _issue(issues, severity, message, product="", fix=""):
    issues.append({"severity": severity, "message": message, "product": product, "fix": fix})


def preflight(context, only_active=False):
    """Everything likely to waste a render, found before any render time is
    spent. A list of {"severity", "message", "product", "fix"}.

    ERROR means the batch cannot produce what was asked for and Render All
    will not start. WARNING means it will run but some images will come out
    wrong. "fix" names a one-click repair the panel offers, if there is one.
    """
    scene = context.scene
    s = scene.mv_settings
    issues = []
    products = get_products()

    # What will be rendered.
    if not products:
        _issue(issues, 'ERROR', f"No products under {PRODUCT_COLL}")
        return issues
    if only_active:
        coll, idx = active_product(context)
        targets = [(label_index(idx, coll), coll)]
    else:
        targets = [(label_index(i, pc), pc) for i, pc in enumerate(products) if pc.mv_render]
        if not targets:
            _issue(issues, 'ERROR', "No products are ticked for rendering")
            return issues

    # Output.
    image = scene.render.image_settings
    if image.file_format == 'FFMPEG' or getattr(image, "media_type", 'IMAGE') == 'VIDEO':
        _issue(issues, 'ERROR', "Output format is video, not image")
    raw = s.render_output_dir
    # Absolute before probing: in an unsaved file // resolves to a relative
    # path, whose parent is "" and would read as unwritable.
    out = os.path.abspath(bpy.path.abspath(raw))
    if raw.startswith("//") and not bpy.data.filepath:
        _issue(issues, 'WARNING', "Unsaved file: // output path", fix='SAVE_HINT')
    if os.path.exists(out) and not os.path.isdir(out):
        _issue(issues, 'ERROR', "Output path is a file, not a folder")
    else:
        probe = out
        while probe and not os.path.isdir(probe):
            parent = os.path.dirname(probe.rstrip("\\/"))
            if parent == probe:
                break
            probe = parent
        if not probe or not os.path.isdir(probe) or not os.access(probe, os.W_OK):
            _issue(issues, 'ERROR', "Output folder cannot be written")
        elif probe != out and not os.path.isdir(out):
            _issue(issues, 'WARNING', "Output folder does not exist yet", fix='FOLDER')

    # Cameras and views.
    if s.reframe_on_render:
        if not [v for v in planned_views(s) if Vector(v[2]).length >= 1e-9]:
            _issue(issues, 'ERROR', "No views selected")
    else:
        cam_coll = bpy.data.collections.get(CAMERA_COLL)
        if not cam_coll or not [o for o in cam_coll.objects if o.type == 'CAMERA']:
            _issue(issues, 'ERROR', "No cameras (build, or Reframe)", fix='CAMERAS')
        elif cam_coll.get("mv_framing") != framing_signature(context):
            _issue(issues, 'WARNING', "Cameras out of date: may crop",
                   fix='CAMERAS')

    # Names.
    views = ([v[0] for v in planned_views(s)] if s.reframe_on_render else
             [o.name.replace("MV_Cam_", "") for o in
              getattr(bpy.data.collections.get(CAMERA_COLL), "objects", [])
              if o.type == 'CAMERA'])
    if _names_clash(s, targets, views + (["Sheet"] if s.sheet_enabled else []),
                    [m for m, _, _ in render_modes(s)] + [m for m, _, _ in data_modes(s)]):
        _issue(issues, 'ERROR', "Template gives two images one name")

    # Engine-specific passes and staging.
    if s.pass_ao and not hasattr(scene, "cycles"):
        _issue(issues, 'ERROR', "AO pass needs the Cycles add-on")
    if data_modes(s) and not hasattr(scene, "cycles"):
        _issue(issues, 'ERROR', "Depth/normal/part passes need Cycles")
    if s.export_bop:
        if s.reframe_on_render:
            persp = [v for v in planned_views(s) if v[1] == "persp"]
        else:
            persp = [o for o in getattr(bpy.data.collections.get(CAMERA_COLL), "objects", [])
                     if o.type == 'CAMERA' and o.data.type == 'PERSP']
        if not persp:
            _issue(issues, 'WARNING', "BOP uses perspective views; none selected")
    full = any(fn is _do_full_render for _, fn, _ in render_modes(s)) or (
        s.turntable_enabled and s.turntable_style == 'FULL')
    if full and s.ground_mode == 'SHADOW' and scene.render.engine != 'CYCLES':
        _issue(issues, 'WARNING', "Shadow Catcher needs Cycles")
    if full and s.world_mode == 'HDRI' and not os.path.isfile(bpy.path.abspath(s.hdri_path)):
        _issue(issues, 'WARNING', "HDRI file not found")
    if full and scene.render.engine != 'BLENDER_WORKBENCH' and s.world_mode != 'HDRI' \
            and not any(o.type == 'LIGHT' for o in context.view_layer.objects):
        _issue(issues, 'WARNING', "No lights: Full renders will be dark", fix='LIGHTING')
    if s.lights_follow_camera and bpy.data.collections.get(LIGHT_COLL) \
            and bpy.data.objects.get(LIGHT_RIG) is None:
        _issue(issues, 'WARNING', "Rebuild lighting to follow camera",
               fix='LIGHTING')

    # The products themselves.
    extents = []
    for _, pc in targets:
        meshes = collection_meshes(pc)
        if not meshes:
            _issue(issues, 'WARNING', "Empty: will be skipped", pc.name)
            continue
        center, size = bbox_of(meshes)
        extents.append((center, max(size)))
        flipped = inside_out = 0
        for obj in meshes:
            if obj.type == 'MESH':
                disagree, out_flag = normal_problems(obj)
                flipped += disagree
                inside_out += out_flag
        if flipped:
            _issue(issues, 'WARNING', f"Normals flipped on {flipped} edge(s)", pc.name,
                   fix='NORMALS')
        if inside_out:
            _issue(issues, 'WARNING', f"{inside_out} mesh(es) inside out", pc.name,
                   fix='NORMALS')
    if len(extents) > 1:
        # Framing covers the whole batch, so products spread around the scene
        # each come out as a speck in the middle of an empty frame.
        biggest = max(e for _, e in extents)
        spread = max((c - extents[0][0]).length for c, _ in extents)
        if spread > biggest * 0.5:
            _issue(issues, 'WARNING', "Products not centred: render small",
                   fix='RECENTER')

    strays = stray_render_objects(context)
    if strays:
        _issue(issues, 'WARNING', f"{len(strays)} stray object(s) in every shot",
               fix='STRAYS')
    return issues


def store_issues(context, issues):
    s = context.scene.mv_settings
    s.preflight_issues.clear()
    for issue in issues:
        item = s.preflight_issues.add()
        for key, value in issue.items():
            setattr(item, key, value)
    s.preflight_time = time.strftime("%H:%M:%S")


class MV_OT_Preflight(Operator):
    """Check the batch for anything that would waste a render: empty products,
    flipped normals, stale cameras, an unwritable output folder and more"""
    bl_idname = "mv.preflight"
    bl_label = "Check Batch"

    def execute(self, context):
        issues = preflight(context)
        store_issues(context, issues)
        errors = sum(1 for i in issues if i["severity"] == 'ERROR')
        if not issues:
            self.report({'INFO'}, "Pre-flight: all clear.")
        else:
            self.report({'ERROR'} if errors else {'WARNING'},
                        f"Pre-flight: {errors} error(s), {len(issues) - errors} warning(s).")
        return {'FINISHED'}


class MV_OT_PreflightFix(Operator):
    """Repair what this pre-flight issue found"""
    bl_idname = "mv.preflight_fix"
    bl_label = "Fix"
    bl_options = {'REGISTER', 'UNDO'}

    fix: StringProperty()
    product: StringProperty()

    @classmethod
    def description(cls, context, properties):
        return {
            'NORMALS': "Recalculate this product's normals to point outwards",
            'CAMERAS': "Rebuild the cameras for the batch as it is now",
            'FOLDER': "Create the output folder",
            'LIGHTING': "Rebuild the lighting rig from the selected preset",
            'RECENTER': "Move every product's centre onto the origin",
            'STRAYS': "Switch off rendering for the objects outside products",
            'SAVE_HINT': "Save the .blend file so // has somewhere to point",
        }.get(properties.fix, "Repair this issue")

    def execute(self, context):
        s = context.scene.mv_settings
        if self.fix == 'NORMALS':
            coll = bpy.data.collections.get(self.product)
            if coll is not None:
                fix_normals(coll)
        elif self.fix == 'CAMERAS':
            build_cameras(context)
        elif self.fix == 'FOLDER':
            try:
                os.makedirs(bpy.path.abspath(s.render_output_dir), exist_ok=True)
            except OSError as exc:
                self.report({'ERROR'}, f"Could not create the folder: {exc}")
                return {'CANCELLED'}
        elif self.fix == 'LIGHTING':
            build_lighting(context, s.lighting_preset)
        elif self.fix == 'RECENTER':
            standardize_products(context, get_products(), scale=False, recenter=True)
        elif self.fix == 'STRAYS':
            for obj in stray_render_objects(context):
                obj.hide_render = True
        elif self.fix == 'SAVE_HINT':
            # The file browser takes over from here; check again once saved.
            bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT')
            return {'FINISHED'}
        store_issues(context, preflight(context))
        return {'FINISHED'}


class MV_OT_RenderPreflightPrompt(Operator):
    """Pre-flight found problems; render anyway?"""
    bl_idname = "mv.render_preflight_prompt"
    bl_label = "Pre-flight Warnings"

    only_active: BoolProperty(options={'SKIP_SAVE', 'HIDDEN'})

    def invoke(self, context, event):
        try:
            return context.window_manager.invoke_props_dialog(
                self, width=420, title="Pre-flight found problems",
                confirm_text="Render Anyway")
        except TypeError:
            return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        col = self.layout.column(align=True)
        issues = context.scene.mv_settings.preflight_issues
        for item in list(issues)[:10]:
            text = f"{item.product}: {item.message}" if item.product else item.message
            col.label(text=text, icon='ERROR')
        if len(issues) > 10:
            col.label(text=f"+{len(issues) - 10} more in the Pre-flight panel")

    def execute(self, context):
        return bpy.ops.mv.render_all('INVOKE_DEFAULT', only_active=self.only_active,
                                     skip_preflight=True)


# -- the batch ----------------------------------------------------------------

class MV_OT_RenderAll(Operator):
    """Render every ticked product from every camera.

    Runs modally, one job per timer tick: Blender redraws between images, the
    status bar shows progress and the time left, and Esc stops the batch after
    the job in flight. Called from a script it runs straight through.

    A job is one rendered image, one post-process of an image already on disk,
    one contact sheet, one turntable frame or one turntable encode.
    """
    bl_idname = "mv.render_all"
    bl_label = "Render All"

    skip_preflight: BoolProperty(options={'SKIP_SAVE', 'HIDDEN'})
    only_active: BoolProperty(
        name="Active Only",
        description="Render only the active product, whether it is ticked or not",
        default=False,
        options={'SKIP_SAVE'},
    )

    @classmethod
    def description(cls, context, properties):
        if properties.only_active:
            return "Render only the active product, from every camera"
        return "Render every ticked product, from every camera"

    # -- state ------------------------------------------------------------
    def _save_state(self, context, products):
        scene = context.scene
        self._saved_hide = {}
        for pc in products:
            lc = find_layer_coll(context.view_layer.layer_collection, pc.name)
            if lc:
                self._saved_hide[pc.name] = lc.exclude
        # By name, not by reference. Reframing deletes and rebuilds the rig, so
        # a scene looking through MV_Cam_Front would be holding a removed
        # object by the time it was put back.
        self._saved_cam = scene.camera.name if scene.camera else None
        self._saved_path = scene.render.filepath

    def _restore(self, context):
        scene = context.scene
        self._end_turntable_pose()
        cam = bpy.data.objects.get(TURNTABLE_CAM)
        if cam is not None:
            remove_object(cam)
        reset_light_rig()
        remove_product_materials()
        ground = bpy.data.objects.get(GROUND_NAME)
        if ground is not None and getattr(self, "_ground_home", None) is not None:
            ground.location = self._ground_home
            ground.hide_render = False
        for pc in get_products():
            lc = find_layer_coll(context.view_layer.layer_collection, pc.name)
            if lc and pc.name in self._saved_hide:
                lc.exclude = self._saved_hide[pc.name]
        scene.camera = bpy.data.objects.get(self._saved_cam) if self._saved_cam else None
        scene.render.filepath = self._saved_path
        if self._tmp_dir:
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
            self._tmp_dir = None

    def _tmp(self):
        if not self._tmp_dir:
            self._tmp_dir = tempfile.mkdtemp(prefix="mv_render_")
        return self._tmp_dir

    def _isolate(self, context, product):
        if self._isolated != product:
            isolate_product(context, product)
            self._isolated = product
            # Materials go on with the product rather than per image: the
            # clay, line, mask and AO passes ignore them anyway.
            remove_product_materials()
            coll = bpy.data.collections.get(product)
            if coll is not None:
                apply_product_material(context.scene.mv_settings, coll)

    def _stage(self, context, job, camera):
        """Turn the lights to this camera and stand the ground under this
        product, for the image about to be rendered."""
        s = context.scene.mv_settings
        if s.lights_follow_camera:
            orient_light_rig(context, camera)
        ground = bpy.data.objects.get(GROUND_NAME)
        if ground is None:
            return
        floor = self._ground_z.get(job["product"])
        if floor is None:
            center, size = bbox_of(collection_meshes(bpy.data.collections[job["product"]]))
            floor = self._ground_z[job["product"]] = center.z - size.z * 0.5
        ground.location.z = floor
        # Full renders only: clay and the other passes are about the product's
        # shape. A camera at or below the floor would see its underside, which
        # hides the product altogether from Bottom.
        ground.hide_render = (job["render"] is not _do_full_render
                              or camera.matrix_world.translation.z <= floor + 1e-6)

    def _record(self, rec, kind, path, width=None, height=None):
        self._records.append(dict(rec, kind=kind, path=path, width=width, height=height))

    def _render_size(self, scene):
        r = scene.render
        return (int(r.resolution_x * r.resolution_percentage / 100),
                int(r.resolution_y * r.resolution_percentage / 100))

    # -- planning ---------------------------------------------------------
    def _claim(self, path):
        key = os.path.normcase(os.path.abspath(path))
        if key in self._claimed:
            raise _NameClash(path)
        self._claimed.add(key)

    def _meta(self, idx, pc):
        s = bpy.context.scene.mv_settings
        size = list(pc.mv_source_size)
        return {
            "label": product_label(s.start_prefix, s.start_number, idx, s.products_per_letter),
            "product": pc.name,
            "source_file": pc.mv_source or "",
            "source_size": [round(v, 6) for v in size] if any(size) else None,
            "source_units": pc.mv_source_units if any(size) else "",
        }

    def _post_targets(self, rel_dir, base):
        s = bpy.context.scene.mv_settings
        folder = os.path.join(self._out_root, safe_name(s.post_folder, "processed"), rel_dir)
        ext = POST_FORMATS[s.post_format]
        targets = [(os.path.join(folder, base + ext), 0)]
        targets += [(os.path.join(folder, f"{base}_{size}{ext}"), size)
                    for size in parse_sizes(s.post_extra_sizes)]
        return targets

    def _plan(self, context, targets, cameras):
        """Every job this run will do, in order, minus outputs already on disk."""
        scene = context.scene
        s = scene.mv_settings
        root = self._out_root
        modes = render_modes(s)
        data = data_modes(s)
        coco_sources = []

        for idx, pc in targets:
            meta = self._meta(idx, pc)
            self._labels.add(meta["label"])
            name = f"{meta['label']}_{pc.name}"
            first_job = len(self._queue)
            sheet_cells = {mode: [] for mode, _, _ in modes}
            parts = part_list(pc)
            views = []

            for cam in cameras:
                view = cam.name.replace("MV_Cam_", "")
                files = {}
                views.append({"view": view, "camera": cam.name, "files": files})
                for mode, render, ext in data:
                    values = name_values(s, idx, pc.name, view, mode)
                    path = os.path.join(root, output_folder(s, values), output_basename(s, values))
                    self._claim(path)
                    master = path + ext
                    files[mode] = master
                    rec = dict(meta, view=view, mode=mode)
                    if s.skip_existing and file_ok(master):
                        self._skipped += 1
                        self._record(rec, "data", master, *self._render_size(scene))
                        continue
                    self._queue.append({
                        "kind": "render", "product": pc.name, "status": f"{name} {view} {mode}",
                        "camera": cam.name, "render": render, "path": path, "master": master,
                        "post": [], "rec": rec, "record_as": "data",
                        "extra": (parts,) if mode == "parts" else (),
                    })
                for mode, render, extra in modes:
                    values = name_values(s, idx, pc.name, view, mode)
                    rel_dir = output_folder(s, values)
                    base = output_basename(s, values)
                    path = os.path.join(root, rel_dir, base)
                    self._claim(path)
                    master = written_path(scene, path)
                    post = self._post_targets(rel_dir, base) if s.post_enabled else []
                    for target, _ in post:
                        self._claim(target)
                    rec = dict(meta, view=view, mode=mode)
                    files[mode] = master
                    sheet_cells[mode].append((view, post[0][0] if post else master))

                    have_master = s.skip_existing and file_ok(master)
                    if have_master:
                        self._record(rec, "render", master, *self._render_size(scene))
                        if all(file_ok(t) for t, _ in post):
                            self._skipped += 1
                            for target, _ in post:
                                self._record(rec, "processed", target)
                            continue
                    self._queue.append({
                        "kind": "post" if have_master else "render",
                        "product": pc.name, "status": f"{name} {view}",
                        "camera": cam.name, "render": render, "path": path,
                        "master": master, "post": post, "rec": rec,
                        "extra": extra,
                    })

            if s.sheet_enabled:
                touched = len(self._queue) > first_job
                for mode, cells in sheet_cells.items():
                    values = name_values(s, idx, pc.name, "Sheet", mode)
                    path = os.path.join(root, output_folder(s, values),
                                        output_basename(s, values) + ".png")
                    self._claim(path)
                    rec = dict(meta, view="Sheet", mode=mode)
                    if s.skip_existing and not touched and file_ok(path):
                        self._record(rec, "sheet", path)
                        continue
                    title = f"{name}  ({mode})" if mode else name
                    self._queue.append({"kind": "sheet", "status": f"{name} contact sheet",
                                        "path": path, "cells": cells, "title": title,
                                        "rec": rec})

            if s.export_cameras:
                paths = {}
                for kind in ("cameras", "transforms"):
                    values = name_values(s, idx, pc.name, kind, "")
                    paths[kind] = os.path.join(root, output_folder(s, values),
                                               output_basename(s, values) + ".json")
                    self._claim(paths[kind])
                self._queue.append({"kind": "cameras", "product": pc.name,
                                    "status": f"{name} cameras", "path": paths["cameras"],
                                    "transforms": paths["transforms"], "views": views,
                                    "parts": parts, "rec": dict(meta, view="Cameras", mode="")})
            if s.export_bop:
                self._queue.append({"kind": "bop", "product": pc.name, "index": idx,
                                    "status": f"{name} BOP", "path": os.path.join(root, "bop"),
                                    "views": views, "rec": meta})
            if s.export_coco:
                coco_sources.append((idx, pc.name, meta, views, parts))

            if s.turntable_enabled:
                self._plan_turntable(context, idx, pc, meta)

        if coco_sources:
            path = os.path.join(root, f"coco{s.shard_suffix}.json")
            self._claim(path)
            self._queue.append({"kind": "coco", "status": "COCO annotations", "path": path,
                                "sources": coco_sources})

    def _plan_turntable(self, context, idx, pc, meta):
        scene = context.scene
        s = scene.mv_settings
        root = self._out_root
        clay = s.turntable_style == 'CLAY'
        mode = "clay" if clay else ""
        values = name_values(s, idx, pc.name, "Turntable", mode)
        rel_dir = output_folder(s, values)
        base = output_basename(s, values)
        name = f"{meta['label']}_{pc.name}"
        rec = dict(meta, view="Turntable", mode=mode)

        outputs = []
        if s.turntable_mp4:
            outputs.append(("mp4", os.path.join(root, rel_dir, base + ".mp4")))
        if s.turntable_gif:
            outputs.append(("gif", os.path.join(root, rel_dir, base + ".gif")))
        for _, path in outputs:
            self._claim(path)

        n = s.turntable_frames
        frames, missing = [], []
        for k in range(n):
            path = os.path.join(root, rel_dir, "turntable", f"{base}_{k + 1:03d}")
            self._claim(path)
            master = written_path(scene, path)
            frames.append(master)
            if s.skip_existing and file_ok(master):
                if not outputs:
                    self._record(rec, "turntable_frame", master, *self._render_size(scene))
                continue
            missing.append((k, path, master))

        self._skipped += n - len(missing)
        if s.export_cameras:
            path = os.path.join(root, rel_dir, "turntable", f"{base}_transforms.json")
            self._claim(path)
            self._queue.append({"kind": "turn_cameras", "product": pc.name,
                                "status": f"{name} turntable cameras", "path": path,
                                "frames": frames, "rec": dict(rec, view="Turntable cameras")})
        if s.skip_existing and not missing and all(file_ok(p) for _, p in outputs):
            for _, path in outputs:
                self._record(rec, "turntable", path)
            return
        for k, path, master in missing:
            self._queue.append({
                "kind": "turn_frame", "product": pc.name,
                "status": f"{name} turntable {k + 1}/{n}",
                "angle": 2.0 * math.pi * k / n, "path": path, "master": master,
                "render": _do_clay_render if clay else _do_full_render,
                "extra": (tuple(s.clay_color),) if clay else (),
                "rec": rec if not outputs else None,
            })
        if outputs:
            self._queue.append({"kind": "turn_encode", "product": pc.name,
                                "status": f"{name} encoding turntable",
                                "frames": frames, "outputs": outputs, "rec": rec})

    def _setup(self, context):
        """Build the queue. None when there is work to do, otherwise the
        result the operator should return straight away."""
        scene = context.scene
        s = scene.mv_settings
        self._queue = []
        self._failures = []
        self._notes = []
        self._records = []
        self._labels = set()
        self._claimed = set()
        self._skipped = 0
        self._done = 0
        self._landed = 0
        self._renders_done = 0
        self._n_sheets = 0
        self._n_post = 0
        self._n_turntables = 0
        self._total = 0
        self._isolated = None
        self._render_time = 0.0
        self._started = time.monotonic()
        self._timer = None
        self._tmp_dir = None
        self._turn_pose = None
        self._ground_z = {}
        self._ground_home = None
        self._cancelled = False
        self._aborted = False

        products = get_products()
        if not products:
            self.report({'ERROR'}, f"No product collections under '{PRODUCT_COLL}'.")
            return {'CANCELLED'}

        if self.only_active:
            coll, idx = active_product(context)
            targets = [(label_index(idx, coll), coll)]
        else:
            # Index into the whole batch, not the ticked subset: the label is
            # the product's identity on disk, and unticking AA_02 must not turn
            # AA_03 into a second AA_02.
            targets = [(label_index(i, pc), pc) for i, pc in enumerate(products) if pc.mv_render]
            if not targets:
                self.report({'ERROR'}, "No products are ticked for rendering.")
                return {'CANCELLED'}

        # An empty product would only ever render blank frames.
        empty = [pc.name for _, pc in targets if not collection_meshes(pc)]
        if empty:
            targets = [(i, pc) for i, pc in targets if pc.name not in empty]
            self._notes.append(f"Skipped {len(empty)} empty product(s): {', '.join(empty[:3])}"
                               + ("..." if len(empty) > 3 else "") + ".")
            if not targets:
                self.report({'ERROR'}, "Every product to render is empty.")
                return {'CANCELLED'}

        if s.reframe_on_render and not planned_views(s):
            self.report({'ERROR'}, "No views selected. Tick at least one view.")
            return {'CANCELLED'}

        self._out_root = bpy.path.abspath(s.render_output_dir)
        try:
            os.makedirs(self._out_root, exist_ok=True)
        except OSError as exc:
            self.report({'ERROR'}, f"Cannot use output folder '{self._out_root}': {exc}")
            return {'CANCELLED'}

        self._save_state(context, products)
        # Every product into the view layer before anything is measured. One
        # hidden by isolation is not evaluated, so a child part of an assembly
        # rotated or fitted while it was excluded can still report where it
        # used to be. The restore at the end puts the user's hiding back.
        isolate_product(context, None)
        # Anything a crashed run left on the products goes before measuring.
        remove_product_materials()
        context.view_layer.update()

        # Rebuilt every run so it always matches the panel, and so Ground set
        # to None clears one an earlier run left behind.
        if s.ground_mode != 'NONE' or bpy.data.objects.get(GROUND_NAME):
            ground = build_ground(context)
            if ground is not None:
                self._ground_home = ground.location.copy()
                if s.ground_mode == 'SHADOW' and scene.render.engine != 'CYCLES':
                    self._notes.append("Shadow Catcher needs Cycles; other engines "
                                       "show the ground as a plain floor.")
        if s.lights_follow_camera and bpy.data.collections.get(LIGHT_COLL) \
                and bpy.data.objects.get(LIGHT_RIG) is None:
            self._notes.append("Lights Follow Camera needs the lighting rebuilt once "
                               "(Scene Setup > Lighting Only).")

        if s.reframe_on_render:
            # Framing covers the whole batch, ticked or not, so re-rendering a
            # single product later lands at the same scale as its run.
            skipped = build_cameras(context)
            if skipped:
                self._notes.append("Skipped custom view(s) with a zero direction: "
                                   + ", ".join(skipped) + ".")

        cam_coll = bpy.data.collections.get(CAMERA_COLL)
        cameras = [o for o in cam_coll.objects if o.type == 'CAMERA'] if cam_coll else []
        if not cameras:
            self._restore(context)
            self.report({'ERROR'}, "No cameras. Build cameras first.")
            return {'CANCELLED'}

        try:
            self._plan(context, targets, cameras)
        except _NameClash as clash:
            self._restore(context)
            self.report({'ERROR'}, f"Two outputs would share the name "
                                   f"'{os.path.basename(str(clash))}'. Add {{view}} "
                                   "and {mode} to the file name template.")
            return {'CANCELLED'}

        if any(job["kind"] in {"turn_frame", "turn_cameras"} for job in self._queue):
            if build_turntable_camera(context) is None:
                self._queue = [j for j in self._queue
                               if j["kind"] not in {"turn_frame", "turn_encode", "turn_cameras"}]
                self._notes.append("No geometry to frame a turntable around.")

        self._total = len(self._queue)
        if not self._queue:
            self._restore(context)
            self._write_manifest(context)
            self.report({'INFO'}, f"Nothing to render: all {self._skipped} image(s) "
                                  "are already on disk.")
            return {'FINISHED'}
        return None

    # -- jobs -------------------------------------------------------------
    def _fail(self, path, exc):
        """Record one failed job. False when the batch should stop.

        Collected and reported at the end rather than raised, so a single
        unwritable file cannot throw away a long batch that is otherwise fine.
        Before the first success there is nothing to salvage and the cause is
        almost always the setup, so that case stops immediately instead of
        failing the same way for every remaining job.
        """
        note = f"{os.path.basename(path)}: {exc}"
        self._failures.append(note)
        print(f"[MultiView] FAILED {note}")
        if not self._landed:
            self._aborted = True
            self._queue.clear()
            return False
        return bool(self._queue)

    def _render_image(self, context, job, camera):
        scene = context.scene
        self._isolate(context, job["product"])
        os.makedirs(os.path.dirname(job["path"]), exist_ok=True)
        cam = bpy.data.objects.get(camera)
        if cam is None or cam.type != 'CAMERA':
            raise RuntimeError(f"camera '{camera}' no longer exists")
        scene.camera = cam
        self._stage(context, job, cam)
        started = time.monotonic()
        # bpy.ops.render.render raises RuntimeError when the image cannot be
        # written; _advance turns that into a named failure, not a traceback.
        job["render"](scene, job["path"], *job["extra"])
        self._render_time += time.monotonic() - started
        self._renders_done += 1
        self._done += 1
        print(f"[MultiView] {self._processed()}/{self._total}: {scene.render.filepath}")

    def _job_render(self, context, job):
        self._render_image(context, job, job["camera"])
        self._record(job["rec"], job.get("record_as", "render"), job["master"],
                     *self._render_size(context.scene))
        if job["post"]:
            self._job_post(context, job)

    # -- annotations --------------------------------------------------------
    def _write_json(self, path, payload):
        """Write a JSON file, unless it already says exactly this: a resumed
        batch then leaves its camera files untouched, as it does its images."""
        text = json.dumps(payload, indent=2)
        try:
            with open(path, encoding="utf-8") as f:
                if f.read() == text:
                    return
        except OSError:
            pass
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def _job_cameras(self, context, job):
        """cameras.json for every view, and transforms.json for the
        perspective ones, which are the only ones a pinhole model describes."""
        scene = context.scene
        coll = bpy.data.collections.get(job["product"])
        if coll is None:
            raise RuntimeError(f"product '{job['product']}' no longer exists")
        here = os.path.dirname(job["path"])

        def rel(path):
            return os.path.relpath(path, here).replace("\\", "/")

        to_world = product_to_world(coll)
        meta = job["rec"]
        views, frames = [], []
        for entry in job["views"]:
            cam = bpy.data.objects.get(entry["camera"])
            if cam is None or cam.type != 'CAMERA':
                continue
            record = camera_record(scene, cam)
            record["view"] = entry["view"]
            record["images"] = {mode or "render": rel(p) for mode, p in entry["files"].items()}
            views.append(record)
            if record["projection"] != "perspective":
                continue
            image = next((p for m, p in entry["files"].items()
                          if m in {"", "render", "clay"}), None)
            if image is None:
                continue
            (fx, _, cx), (_, fy, cy), _ = record["K"]
            frame = {"file_path": rel(image), "transform_matrix": record["c2w_opengl"],
                     "fl_x": fx, "fl_y": fy, "cx": cx, "cy": cy,
                     "w": record["width"], "h": record["height"]}
            if "mask" in entry["files"]:
                frame["mask_path"] = rel(entry["files"]["mask"])
            frames.append(frame)

        payload = {
            "generator": f"MultiView Product Renderer {'.'.join(map(str, bl_info['version']))}",
            "blender": bpy.app.version_string,
            "label": meta["label"], "product": meta["product"],
            "source_file": meta.get("source_file", ""),
            "source_units": meta.get("source_units", ""),
            "source_size": meta.get("source_size"),
            "model_to_world": [list(row) for row in to_world],
            "conventions": {
                "world": "Blender: +Z up, scene units",
                "c2w_opengl": "camera to world, camera looks down -Z with +Y up",
                "w2c_opencv": "world to camera, camera looks down +Z with +Y down",
                "model_to_world": "source file coordinates (source_units) to world",
                "depth": "EXR, distance along the view axis in scene units",
                "normal": "EXR, camera space, OpenGL axes",
                "parts": "16-bit PNG, 0 = background, n = parts[n-1]",
            },
            "parts": [{"id": i, "name": n} for n, i in sorted(job["parts"].items(),
                                                              key=lambda p: p[1])],
            "views": views,
        }
        self._write_json(job["path"], payload)
        self._record(meta, "cameras", job["path"])
        if frames:
            self._write_json(job["transforms"], {"camera_model": "OPENCV", "frames": frames})
            self._record(meta, "cameras", job["transforms"])

    def _job_turn_cameras(self, context, job):
        """transforms.json for a turntable. The product turns and the camera
        stays put; the same pictures come from a camera circling a still
        product, which is what NeRF-style tools expect, so each frame gets
        that equivalent camera."""
        self._end_turntable_pose()
        scene = context.scene
        cam = bpy.data.objects.get(TURNTABLE_CAM)
        coll = bpy.data.collections.get(job["product"])
        if cam is None or coll is None:
            raise RuntimeError("turntable camera or product missing")
        center, _ = bbox_of(collection_meshes(coll))
        base = camera_record(scene, cam)
        (fx, _, cx), (_, fy, cy), _ = base["K"]
        here = os.path.dirname(job["path"])
        n = len(job["frames"])
        frames = []
        for k, image in enumerate(job["frames"]):
            angle = 2.0 * math.pi * k / n
            orbit = (Matrix.Translation(center) @ Matrix.Rotation(-angle, 4, 'Z')
                     @ Matrix.Translation(-center))
            c2w = orbit @ cam.matrix_world.normalized()
            frames.append({"file_path": os.path.relpath(image, here).replace("\\", "/"),
                           "transform_matrix": [list(row) for row in c2w],
                           "fl_x": fx, "fl_y": fy, "cx": cx, "cy": cy,
                           "w": base["width"], "h": base["height"]})
        self._write_json(job["path"], {"camera_model": "OPENCV", "frames": frames})
        self._record(job["rec"], "cameras", job["path"])

    def _job_bop(self, context, job):
        """One BOP scene per product, from its perspective views.

        Poses are rigid and in millimetres of the source model, as BOP wants,
        although the scene was scaled to fit: the scale is taken back out of
        the camera translation, and the model is exported in its own units.
        """
        scene = context.scene
        s = scene.mv_settings
        coll = bpy.data.collections.get(job["product"])
        if coll is None:
            raise RuntimeError(f"product '{job['product']}' no longer exists")
        root = job["path"]
        obj_id = job["index"] + 1
        units_mm = UNIT_TO_MM.get(coll.mv_source_units, 1.0)
        to_world = product_to_world(coll)
        scale = abs(to_world.to_3x3().determinant()) ** (1.0 / 3.0) or 1.0
        scene_dir = os.path.join(root, "train_pbr", f"{job['index']:06d}")
        for sub in ("rgb", "depth", "mask", "mask_visib"):
            os.makedirs(os.path.join(scene_dir, sub), exist_ok=True)

        cams, gts, infos = {}, {}, {}
        im_id = 0
        for entry in job["views"]:
            cam = bpy.data.objects.get(entry["camera"])
            if cam is None or cam.data.type != 'PERSP':
                continue
            rgb = next((p for m, p in entry["files"].items() if m in {"", "render", "clay"}), None)
            depth_exr = entry["files"].get("depth")
            if not rgb or not depth_exr or not file_ok(rgb) or not file_ok(depth_exr):
                continue
            record = camera_record(scene, cam)
            px = load_pixels(depth_exr, raw=True)[::-1]
            hit = px[..., 3] > 0.5
            depth_mm = np.where(hit, px[..., 0] / scale * units_mm, 0.0)
            depth_scale = max(0.1, math.ceil(depth_mm.max() / 65000.0 * 10) / 10)
            write_png16(os.path.join(scene_dir, "depth", f"{im_id:06d}.png"),
                        np.rint(depth_mm / depth_scale))
            shutil.copyfile(rgb, os.path.join(scene_dir, "rgb", f"{im_id:06d}"
                                              + os.path.splitext(rgb)[1].lower()))
            mask = np.zeros(hit.shape + (4,), np.float32)
            mask[..., :3] = hit[::-1, :, None]
            mask[..., 3] = 1.0
            for sub in ("mask", "mask_visib"):
                save_pixels(mask, os.path.join(scene_dir, sub, f"{im_id:06d}_000000.png"), 'PNG')

            m2c = Matrix(record["w2c_opencv"]) @ to_world
            rot = m2c.to_3x3() * (1.0 / scale)
            t_mm = m2c.translation / scale * units_mm
            ys, xs = np.nonzero(hit)
            bbox = ([int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1),
                     int(ys.max() - ys.min() + 1)] if len(xs) else [-1, -1, 0, 0])
            count = int(hit.sum())
            key = str(im_id)
            cams[key] = {"cam_K": [v for row in record["K"] for v in row],
                         "depth_scale": depth_scale}
            gts[key] = [{"obj_id": obj_id, "cam_R_m2c": [v for row in rot for v in row],
                         "cam_t_m2c": list(t_mm)}]
            infos[key] = [{"bbox_obj": bbox, "bbox_visib": bbox, "px_count_all": count,
                           "px_count_valid": count, "px_count_visib": count,
                           "visib_fract": 1.0 if count else 0.0}]
            im_id += 1
        if not im_id:
            raise RuntimeError("no perspective view with both an image and depth")
        self._write_json(os.path.join(scene_dir, "scene_camera.json"), cams)
        self._write_json(os.path.join(scene_dir, "scene_gt.json"), gts)
        self._write_json(os.path.join(scene_dir, "scene_gt_info.json"), infos)

        first = cams["0"]["cam_K"]
        w, h = render_resolution(scene)
        camera_json = os.path.join(root, "camera.json")
        if not os.path.isfile(camera_json):
            self._write_json(camera_json, {"fx": first[0], "fy": first[4], "cx": first[2],
                                           "cy": first[5], "width": w, "height": h,
                                           "depth_scale": 0.1})
        info = self._export_bop_model(coll, to_world, units_mm,
                                      os.path.join(root, "models", f"obj_{obj_id:06d}.ply"))
        info_path = os.path.join(root, "models", f"models_info{s.shard_suffix}.json")
        try:
            with open(info_path, encoding="utf-8") as f:
                models = json.load(f)
        except (OSError, ValueError):
            models = {}
        models[str(obj_id)] = info
        self._write_json(info_path, models)
        self._record(job["rec"], "bop", os.path.join(scene_dir, "scene_gt.json"))

    def _export_bop_model(self, coll, to_world, units_mm, path):
        """The product as a binary PLY in source-model millimetres, and its BOP
        models_info entry. The diameter is the largest distance between any
        two of up to 3000 sampled vertices, so it can fall slightly short on
        dense meshes."""
        back = to_world.inverted()
        verts, faces, offset = [], [], 0
        for obj in collection_meshes(coll):
            if obj.type != 'MESH':
                continue
            me = obj.data
            me.calc_loop_triangles()
            co = np.empty(len(me.vertices) * 3, np.float64)
            me.vertices.foreach_get("co", co)
            m = np.array(back @ obj.matrix_world)
            local = (co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]) * units_mm
            tri = np.empty(len(me.loop_triangles) * 3, np.int64)
            me.loop_triangles.foreach_get("vertices", tri)
            verts.append(local)
            faces.append(tri.reshape(-1, 3) + offset)
            offset += len(local)
        verts = np.concatenate(verts).astype(np.float32)
        faces = np.concatenate(faces).astype(np.int32)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {len(verts)}\n"
                     "property float x\nproperty float y\nproperty float z\n"
                     f"element face {len(faces)}\nproperty list uchar int vertex_indices\n"
                     "end_header\n").encode("ascii"))
            f.write(verts.astype("<f4").tobytes())
            rows = np.empty(len(faces), dtype=[("n", "u1"), ("v", "<i4", 3)])
            rows["n"] = 3
            rows["v"] = faces
            f.write(rows.tobytes())
        lo, hi = verts.min(axis=0), verts.max(axis=0)
        sample = verts[np.linspace(0, len(verts) - 1, min(len(verts), 3000)).astype(np.int64)]
        diameter = 0.0
        for i in range(0, len(sample), 500):
            d = np.linalg.norm(sample[i:i + 500, None, :] - sample[None, :, :], axis=-1)
            diameter = max(diameter, float(d.max()))
        return {"diameter": diameter, "min_x": float(lo[0]), "min_y": float(lo[1]),
                "min_z": float(lo[2]), "size_x": float(hi[0] - lo[0]),
                "size_y": float(hi[1] - lo[1]), "size_z": float(hi[2] - lo[2])}

    def _job_coco(self, context, job):
        """coco.json: one instance per visible part per image, with the part's
        name alongside. Categories are the products. Built from the part-ID
        images on disk, so images skipped as already rendered are included,
        and merged with a previous run's file the way the manifest is."""
        root = self._out_root
        images, annotations, categories = [], [], {}
        for idx, product, meta, views, parts in job["sources"]:
            names = {i: n for n, i in parts.items()}
            categories[idx + 1] = {"id": idx + 1, "name": product, "supercategory": "product"}
            for entry in views:
                label_path = entry["files"].get("parts")
                if not label_path or not file_ok(label_path):
                    continue
                labels = read_png16(label_path)
                h, w = labels.shape
                found = []
                for part_id in np.unique(labels):
                    if part_id == 0:
                        continue
                    mask = labels == part_id
                    ys, xs = np.nonzero(mask)
                    flat = mask.flatten(order="F").astype(np.int8)
                    edges = np.flatnonzero(np.diff(flat)) + 1
                    counts = np.diff(np.concatenate([[0], edges, [flat.size]])).tolist()
                    if flat[0]:
                        counts = [0] + counts
                    found.append({
                        "category_id": idx + 1, "iscrowd": 0, "area": int(mask.sum()),
                        "bbox": [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1),
                                 int(ys.max() - ys.min() + 1)],
                        "segmentation": {"size": [h, w], "counts": counts},
                        "part_id": int(part_id), "part_name": names.get(int(part_id), ""),
                    })
                for mode, path in entry["files"].items():
                    if mode not in {"", "render", "clay"} or not file_ok(path):
                        continue
                    image_id = len(images) + 1
                    images.append({"id": image_id, "width": w, "height": h,
                                   "file_name": os.path.relpath(path, root).replace("\\", "/"),
                                   "mv_label": meta["label"], "view": entry["view"],
                                   "mode": mode})
                    for ann in found:
                        annotations.append(dict(ann, image_id=image_id))
        # Carry over images of products this run did not touch.
        try:
            with open(job["path"], encoding="utf-8") as f:
                old = json.load(f)
        except (OSError, ValueError):
            old = {}
        mine = {m["label"] for _, _, m, _, _ in job["sources"]}
        remap = {}
        for image in old.get("images", []):
            if image.get("mv_label") in mine:
                continue
            remap[image["id"]] = len(images) + 1
            images.append(dict(image, id=remap[image["id"]]))
        for ann in old.get("annotations", []):
            if ann.get("image_id") in remap:
                annotations.append(dict(ann, image_id=remap[ann["image_id"]]))
        for cat in old.get("categories", []):
            categories.setdefault(cat["id"], cat)
        for i, ann in enumerate(annotations):
            ann["id"] = i + 1
        self._write_json(job["path"], {
            "info": {"description": "MultiView Product Renderer part instances",
                     "date_created": datetime.now().isoformat(timespec="seconds")},
            "images": images, "annotations": annotations,
            "categories": sorted(categories.values(), key=lambda c: c["id"]),
        })

    def _job_post(self, context, job):
        s = context.scene.mv_settings
        px = post_process(load_pixels(job["master"]), s)
        fmt = s.post_format
        for target, size in job["post"]:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            out = fit_long_edge(px, size) if size and max(px.shape[:2]) > size else px
            save_pixels(out, target, fmt, s.post_quality)
            self._record(job["rec"], "processed", target, out.shape[1], out.shape[0])
        self._n_post += 1

    def _job_sheet(self, context, job):
        s = context.scene.mv_settings
        cells = []
        for caption, path in job["cells"]:
            if file_ok(path):
                px = load_pixels(path)
                h, w = px.shape[:2]
                cells.append((caption, resize_pixels(px, s.sheet_cell_width,
                                                     round(h * s.sheet_cell_width / w))))
        if not cells:
            raise RuntimeError("none of its images are on disk")
        sheet = contact_sheet(cells, job["title"], s, self._tmp())
        os.makedirs(os.path.dirname(job["path"]), exist_ok=True)
        save_pixels(sheet, job["path"], 'PNG')
        self._record(job["rec"], "sheet", job["path"], sheet.shape[1], sheet.shape[0])
        self._n_sheets += 1

    def _pose_turntable(self, context, product, angle):
        """Spin one product about its own centre to angle, measured from where
        it stood before the turntable began. Absolute, so skipped frames and
        rounding never accumulate into drift."""
        if self._turn_pose and self._turn_pose["product"] != product:
            self._end_turntable_pose()
        if self._turn_pose is None:
            coll = bpy.data.collections.get(product)
            if coll is None:
                raise RuntimeError(f"product '{product}' no longer exists")
            center, _ = bbox_of(collection_meshes(coll))
            self._turn_pose = {
                "product": product, "center": center,
                "saved": {o.name: o.matrix_world.copy() for o in collection_roots(coll)},
            }
        pose = self._turn_pose
        spin = (Matrix.Translation(pose["center"])
                @ Matrix.Rotation(angle, 4, 'Z')
                @ Matrix.Translation(-pose["center"]))
        for name, matrix in pose["saved"].items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.matrix_world = spin @ matrix

    def _end_turntable_pose(self):
        pose, self._turn_pose = getattr(self, "_turn_pose", None), None
        if not pose:
            return
        for name, matrix in pose["saved"].items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.matrix_world = matrix

    def _job_turn_frame(self, context, job):
        self._isolate(context, job["product"])
        self._pose_turntable(context, job["product"], job["angle"])
        self._render_image(context, job, TURNTABLE_CAM)
        if job["rec"] is not None:
            self._record(job["rec"], "turntable_frame", job["master"],
                         *self._render_size(context.scene))

    def _job_turn_encode(self, context, job):
        self._end_turntable_pose()
        s = context.scene.mv_settings
        frames = [f for f in job["frames"] if file_ok(f)]
        if len(frames) < 2:
            raise RuntimeError("fewer than two turntable frames on disk")
        background = tuple(s.bg_color[:3])
        errors = []
        for kind, path in job["outputs"]:
            # Each format on its own, so a video codec problem does not also
            # cost the GIF.
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if kind == "mp4":
                    size = encode_mp4(frames, path, s.turntable_fps, background, self._tmp())
                else:
                    size = encode_gif(frames, path, s.turntable_fps, s.turntable_gif_size,
                                      background)
            except (RuntimeError, OSError, ValueError) as exc:
                errors.append(f"{kind.upper()}: {exc}")
                continue
            self._record(job["rec"], "turntable", path, *size)
        if len(errors) < len(job["outputs"]):
            self._n_turntables += 1
        if errors:
            raise RuntimeError("; ".join(errors))

    def _advance(self, context):
        """Run the next job. False once the batch is over."""
        if not self._queue:
            return False
        job = self._queue.pop(0)
        handler = {
            "render": self._job_render, "post": self._job_post,
            "sheet": self._job_sheet, "turn_frame": self._job_turn_frame,
            "turn_encode": self._job_turn_encode, "cameras": self._job_cameras,
            "turn_cameras": self._job_turn_cameras, "bop": self._job_bop,
            "coco": self._job_coco,
        }[job["kind"]]
        try:
            handler(context, job)
        except Exception as exc:
            if not isinstance(exc, (RuntimeError, OSError)):
                # Not a write failure: a bug, so keep the trace for a report.
                traceback.print_exc()
            target = job.get("path") or job["outputs"][0][1]
            return self._fail(target, exc)
        self._landed += 1
        return bool(self._queue)

    # -- progress ---------------------------------------------------------
    def _processed(self):
        return self._total - len(self._queue)

    def _status(self):
        text = f"MultiView: {self._processed()}/{self._total}"
        if self._queue:
            text += f"  {self._queue[0]['status']}"
        if self._renders_done:
            left = sum(1 for j in self._queue if j["kind"] in {"render", "turn_frame"})
            text += f"  ~{format_duration(self._render_time / self._renders_done * left)} left"
        return text + "  -  Esc to cancel"

    def _write_manifest(self, context):
        fmt = context.scene.mv_settings.manifest_format
        if fmt == 'NONE' or not self._records:
            return
        try:
            write_manifest(self._out_root, self._records, self._labels, fmt,
                           "manifest" + context.scene.mv_settings.shard_suffix)
        except (OSError, ValueError) as exc:
            self._notes.append(f"Manifest not written: {exc}.")

    def _report_result(self):
        elapsed = format_duration(time.monotonic() - self._started)
        extras = []
        if self._n_post:
            extras.append(f"post-processed {self._n_post}")
        if self._n_sheets:
            extras.append(f"{self._n_sheets} contact sheet(s)")
        if self._n_turntables:
            extras.append(f"{self._n_turntables} turntable(s)")
        made = f"Wrote {self._done} image(s)" + (f", {', '.join(extras)}" if extras else "")
        skipped = (f" Skipped {self._skipped} already on disk."
                   if self._skipped else "")
        notes = (" " + " ".join(self._notes)) if self._notes else ""

        if self._aborted:
            # Nothing landed at all, so the batch stopped at the first failure
            # rather than burning render time failing the same way every time.
            self.report({'ERROR'}, f"Nothing rendered. {self._failures[0]}")
            return {'CANCELLED'}
        if self._cancelled:
            self.report({'WARNING'},
                        f"Render cancelled after {self._processed()} of {self._total} "
                        f"job(s). {made} in {elapsed}.{skipped} Tick Skip Existing "
                        "to resume.")
            return {'FINISHED'} if self._landed else {'CANCELLED'}
        if self._failures:
            self.report({'WARNING'},
                        f"{made} in {elapsed}. {len(self._failures)} failed, first: "
                        f"{self._failures[0]}. Full list in the System Console."
                        f"{skipped}{notes}")
            return {'FINISHED'}
        self.report({'WARNING'} if self._notes else {'INFO'},
                    f"{made} in {elapsed}.{skipped}{notes}")
        return {'FINISHED'}

    def _finish(self, context):
        self._restore(context)
        self._write_manifest(context)
        result = self._report_result()
        LAST_RENDER.clear()
        LAST_RENDER.update(
            images=self._done, jobs=self._processed(), total=self._total,
            skipped=self._skipped, failures=list(self._failures), notes=list(self._notes),
            cancelled=self._cancelled, aborted=self._aborted, output=self._out_root,
            finished='FINISHED' in result)
        return result

    def _teardown(self, context):
        wm = context.window_manager
        if self._timer is not None:
            wm.event_timer_remove(self._timer)
            self._timer = None
        wm.progress_end()
        try:
            context.workspace.status_text_set(None)
        except AttributeError:
            pass
        return self._finish(context)

    # -- entry points -----------------------------------------------------
    def _preflight_errors(self, context, issues):
        errors = [i for i in issues if i["severity"] == 'ERROR']
        if not errors:
            return None
        first = errors[0]
        where = f"{first['product']}: " if first["product"] else ""
        more = f" (+{len(errors) - 1} more, see the Pre-flight panel)" if len(errors) > 1 else ""
        self.report({'ERROR'}, f"Pre-flight: {where}{first['message']}{more}.")
        return {'CANCELLED'}

    def execute(self, context):
        # Scripts get the same hard stops as the button but no question:
        # warnings go into the report instead.
        if not self.skip_preflight and context.scene.mv_settings.preflight_on_render:
            issues = preflight(context, self.only_active)
            store_issues(context, issues)
            stop = self._preflight_errors(context, issues)
            if stop:
                return stop
        result = self._setup(context)
        if result is not None:
            return result
        try:
            while self._advance(context):
                pass
        except BaseException:
            self._restore(context)
            raise
        return self._finish(context)

    def invoke(self, context, event):
        if not self.skip_preflight and context.scene.mv_settings.preflight_on_render:
            issues = preflight(context, self.only_active)
            store_issues(context, issues)
            stop = self._preflight_errors(context, issues)
            if stop:
                return stop
            if issues:
                # Asked in a dialog of its own, which starts the render again
                # with the check skipped if the answer is to go ahead.
                bpy.ops.mv.render_preflight_prompt('INVOKE_DEFAULT', only_active=self.only_active)
                return {'CANCELLED'}
        result = self._setup(context)
        if result is not None:
            return result
        wm = context.window_manager
        wm.progress_begin(0, self._total)
        # Short, because each tick blocks for a whole render anyway. All the
        # interval decides is how long Blender idles between two jobs.
        self._timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        try:
            context.workspace.status_text_set(self._status())
        except AttributeError:
            pass
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'ESC' and event.value == 'PRESS':
            self._cancelled = True
            return self._teardown(context)
        if event.type != 'TIMER':
            # Swallow everything else: products are being hidden, shown and
            # spun under the user's feet, so a click in the outliner mid-batch
            # would be saved over by the restore at the end.
            return {'RUNNING_MODAL'}

        try:
            more = self._advance(context)
        except Exception:
            # Leave the scene the way it was found before the traceback, rather
            # than stuck on one product with the timer still firing.
            self._teardown(context)
            raise
        context.window_manager.progress_update(self._processed())
        try:
            context.workspace.status_text_set(self._status())
        except AttributeError:
            pass
        if not more:
            return self._teardown(context)
        return {'RUNNING_MODAL'}


class MV_UL_StepFiles(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.label(text=os.path.basename(item.path) or "(empty)", icon='FILE')
        row.operator("mv.remove_step_file", text="", icon='X').index = index


class MV_UL_CustomViews(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row = row.row(align=True)
        row.active = item.enabled
        row.prop(item, "name", text="")
        row.prop(item, "dir_x", text="X")
        row.prop(item, "dir_y", text="Y")
        row.prop(item, "dir_z", text="Z")
        row.prop(item, "is_ortho", text="", icon='VIEW_ORTHO' if item.is_ortho else 'VIEW_PERSPECTIVE')
        row.operator("mv.remove_custom_view", text="", icon='X').index = index


class MV_UL_Products(UIList):
    """MV_Products' children, each with its render tick and the label its
    files will carry. The label is worked out from the product's place in the
    whole batch, which is also what Render All uses, so unticking a product
    never renumbers the ones after it."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        s = context.scene.mv_settings
        row = layout.row(align=True)
        row.prop(item, "mv_render", text="")
        sub = row.row(align=True)
        sub.active = item.mv_render
        label = product_label(s.start_prefix, s.start_number, label_index(index, item),
                              s.products_per_letter)
        sub.label(text=f"{label}  {item.name}", icon='OUTLINER_COLLECTION')


class MV_PT_Guide(Panel):
    bl_label = "Guide"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MultiView"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        for line in GUIDE_LINES:
            box.label(text=line)


class MV_PT_SceneSetup(Panel):
    bl_label = "Scene Setup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MultiView"

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings

        col = layout.column(align=True)
        col.label(text="Lighting:")
        row = col.row(align=True)
        row.prop(s, "lighting_preset", text="")
        row.operator("mv.save_lighting_preset", text="", icon='ADD')
        row.operator("mv.delete_lighting_preset", text="", icon='REMOVE')
        col.prop(s, "lighting_intensity", slider=True)
        layout.prop(s, "lights_follow_camera")

        col = layout.column(align=True)
        col.label(text="Background:")
        col.row(align=True).prop(s, "world_mode", expand=True)
        if s.world_mode == 'HDRI':
            col.prop(s, "hdri_path", text="")
            row = col.row(align=True)
            row.prop(s, "hdri_strength")
            row.prop(s, "hdri_rotation")
            col.prop(s, "hdri_visible")
        col.prop(s, "transparent_bg")
        row = col.row()
        # The colour still shows behind an HDRI the camera is not shown.
        row.enabled = not s.transparent_bg and not (s.world_mode == 'HDRI' and s.hdri_visible)
        row.prop(s, "bg_color", text="")

        col = layout.column(align=True)
        col.label(text="Ground (Full renders):")
        col.prop(s, "ground_mode", text="")
        if s.ground_mode == 'FLOOR':
            row = col.row(align=True)
            row.prop(s, "ground_color", text="")
            row.prop(s, "ground_roughness")
        elif s.ground_mode == 'SHADOW' and context.scene.render.engine != 'CYCLES':
            col.label(text="Shadow Catcher needs Cycles.", icon='ERROR')

        layout.separator()
        layout.operator("mv.apply_scene_setup", icon='SCENE_DATA')

        row = layout.row(align=True)
        row.operator("mv.build_lighting", text="Lighting Only", icon='LIGHT')
        row.operator("mv.apply_world", text="Background Only", icon='WORLD')


class MV_PT_SceneMaterials(Panel):
    bl_label = "Materials"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MultiView"
    bl_parent_id = "MV_PT_SceneSetup"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        layout.label(text="Whole batch:")
        row = layout.row(align=True)
        row.prop(s, "material_preset", text="")
        sub = row.row(align=True)
        sub.active = s.material_preset != 'KEEP'
        sub.prop(s, "material_color", text="")

        coll, _ = active_product(context)
        if coll is None:
            return
        layout.label(text=f"{coll.name}:", icon='OUTLINER_COLLECTION')
        row = layout.row(align=True)
        row.prop(coll, "mv_material", text="")
        sub = row.row(align=True)
        sub.active = coll.mv_material not in {'DEFAULT', 'KEEP'}
        sub.prop(coll, "mv_material_color", text="")
        layout.label(text="Full renders only. Pick a product in", icon='INFO')
        layout.label(text="Products to render to set its own.")


class MV_PT_Import(Panel):
    bl_label = "Import Products"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MultiView"

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        addon = context.preferences.addons.get(__name__)

        box = layout.box()
        box.label(text="STEP / IGES Importer:")
        if addon is not None:
            prefs = addon.preferences
            box.prop(prefs, "step_import_mode", text="Mode")
            col = box.column()
            col.enabled = prefs.step_import_mode in {'AUTO', 'FREECAD'}
            col.prop(prefs, "freecad_path", text="FreeCAD")
        box.label(text="IGES always uses FreeCAD.", icon='INFO')
        box.label(text="Mesh files (STL, OBJ, ...) are in:")
        box.prop(s, "mesh_units", text="")

        layout.separator()
        row = layout.row()
        row.template_list("MV_UL_StepFiles", "", s, "step_files", s, "step_files_index", rows=3)
        col = row.column(align=True)
        col.operator("mv.add_step_file", text="", icon='ADD')
        col.operator("mv.add_folder", text="", icon='FILE_FOLDER')
        col.operator("mv.clear_step_files", text="", icon='TRASH')
        layout.label(text="STEP IGES STL OBJ PLY glTF FBX 3MF", icon='FILE')

        layout.operator("mv.import_all_steps", icon='IMPORT')
        layout.operator("mv.add_product_collection", icon='OUTLINER_COLLECTION')

        prods = get_products()
        header = layout.row(align=True)
        header.prop(s, "show_products_list", text="",
                    icon='TRIA_DOWN' if s.show_products_list else 'TRIA_RIGHT', emboss=False)
        header.label(text=f"Products under '{PRODUCT_COLL}' ({len(prods)})")
        if s.show_products_list:
            box = layout.box()
            if not prods:
                box.label(text="(none)", icon='INFO')
            else:
                for pc in prods:
                    box.label(text=f"{pc.name}  ({len(pc.all_objects)} objs)", icon='OUTLINER_COLLECTION')


class MV_PT_Standardize(Panel):
    bl_label = "Standardize"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MultiView"

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings

        layout.prop(s, "fit_on_import")
        layout.label(text="Runs as each file lands.", icon='INFO')

        layout.separator()
        row = layout.row(align=True)
        row.prop(s, "recenter", toggle=True)
        row.prop(s, "rescale", toggle=True)
        col = layout.column(align=True)
        col.enabled = s.rescale or s.fit_on_import
        col.row(align=True).prop(s, "scale_mode", expand=True)
        col.prop(s, "target_size")
        sub = layout.row()
        sub.enabled = s.recenter or s.fit_on_import
        sub.prop(s, "rest_on_floor")

        row = layout.row(align=True)
        row.prop(s, "auto_smooth", toggle=True)
        sub = row.row()
        sub.enabled = s.auto_smooth
        sub.prop(s, "smooth_angle", text="")

        layout.separator()
        layout.operator("mv.standardize", icon='FULLSCREEN_EXIT')

        coll, _ = active_product(context)
        if coll is not None:
            real = format_real_size(coll)
            col = layout.column(align=True)
            col.label(text=f"{coll.name}, as imported:", icon='OUTLINER_COLLECTION')
            col.label(text=real or "size not recorded yet")


class MV_PT_Cameras(Panel):
    bl_label = "Cameras / Views"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MultiView"

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        layout.prop(s, "view_set")

        # A preset is drawn from VIEW_SETS, not from the checkboxes, because
        # that is what build_cameras reads for it. Only Custom edits them.
        custom = s.view_set == 'CUSTOM'
        preset = set() if custom else {v[0] for v in VIEW_SETS[s.view_set]}
        ortho = layout.grid_flow(row_major=True, columns=3, even_columns=True, align=True)
        persp = layout.row(align=True)
        persp.label(text="Persp:")
        for i, (name, kind, _) in enumerate(VIEWS_ALL):
            # Perspective names are too long for a third of the sidebar, so
            # they get their own row and drop the shared prefix.
            cell = (ortho if kind == "ortho" else persp).row()
            text = name.replace("Persp_", "")
            if custom:
                cell.prop(s, "views_enabled", index=i, text=text)
            else:
                cell.enabled = False
                cell.label(text=text,
                           icon='CHECKBOX_HLT' if name in preset else 'CHECKBOX_DEHLT')

        layout.prop(s, "front_axis")
        layout.prop(s, "frame_padding_factor")

        layout.label(text="Custom Views (direction from target):")
        row = layout.row()
        row.template_list("MV_UL_CustomViews", "", s, "custom_views", s, "custom_views_index", rows=2)
        row.column(align=True).operator("mv.add_custom_view", text="", icon='ADD')

        layout.operator("mv.build_cameras", icon='CAMERA_DATA')

        layout.separator()
        box = layout.box()
        box.label(text="Orient Products:")

        products = get_products()
        if not products:
            box.label(text="No products to orient.", icon='INFO')
            return

        coll, idx = active_product(context)
        box.label(text=f"{coll.name}  ({idx + 1}/{len(products)})",
                  icon='OUTLINER_COLLECTION')
        box.prop(s, "isolate_active")
        box.prop(s, "rotate_step")

        col = box.column(align=True)
        row = col.row(align=True)
        row.operator("mv.rotate_product", text="Left", icon='TRIA_LEFT').direction = 'LEFT'
        row.operator("mv.rotate_product", text="Right", icon='TRIA_RIGHT').direction = 'RIGHT'
        row = col.row(align=True)
        row.operator("mv.rotate_product", text="Up", icon='TRIA_UP').direction = 'UP'
        row.operator("mv.rotate_product", text="Down", icon='TRIA_DOWN').direction = 'DOWN'

        col = box.column(align=True)
        col.prop(s, "orient_method", text="")
        row = col.row(align=True)
        row.operator("mv.auto_orient", text="Auto Orient", icon='ORIENTATION_GLOBAL').all_products = False
        row.operator("mv.auto_orient", text="All").all_products = True
        row = col.row(align=True)
        row.operator("mv.reset_orientation", text="Reset", icon='LOOP_BACK').all_products = False
        row.operator("mv.reset_orientation", text="All").all_products = True

        row = box.row(align=True)
        row.operator("mv.product_step", text="Previous", icon='FRAME_PREV').delta = -1
        row.operator("mv.product_step", text="Next", icon='FRAME_NEXT').delta = 1
        box.operator("mv.show_all_products", icon='HIDE_OFF')
        if s.reframe_on_render:
            box.label(text="Render reframes the cameras itself.", icon='INFO')
        else:
            box.label(text="Rebuild cameras after rotating to reframe.", icon='INFO')


class MV_PT_Render(Panel):
    bl_label = "Batch Render"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MultiView"

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        layout.prop(s, "render_output_dir")
        layout.prop(s, "render_mode")
        if s.render_mode in {'CLAY', 'BOTH'} or (s.pass_lines and s.lines_fill == 'CLAY'):
            layout.prop(s, "clay_color")
        layout.label(text="Extra passes:")
        row = layout.row(align=True)
        row.prop(s, "pass_lines", toggle=True)
        row.prop(s, "pass_mask", toggle=True)
        row.prop(s, "pass_ao", toggle=True)
        col = layout.column(align=True)
        col.prop(s, "skip_existing")
        col.prop(s, "reframe_on_render")

        # Read-only lookup: draw() must not create the root.
        root = bpy.data.collections.get(PRODUCT_COLL)
        prods = get_products()
        if prods:
            layout.label(text="Products to render:")
            row = layout.row()
            row.template_list("MV_UL_Products", "", root, "children",
                              s, "active_product_index", rows=4)
            col = row.column(align=True)
            col.operator("mv.set_products_render", text="", icon='CHECKBOX_HLT').state = True
            col.operator("mv.set_products_render", text="", icon='CHECKBOX_DEHLT').state = False

        strays = stray_render_objects(context)
        if strays:
            box = layout.box()
            box.label(text=f"{len(strays)} object(s) outside {PRODUCT_COLL}", icon='ERROR')
            box.label(text="appear in every render:")
            col = box.column(align=True)
            for obj in strays[:4]:
                col.label(text=obj.name, icon='OBJECT_DATA')
            if len(strays) > 4:
                col.label(text=f"+{len(strays) - 4} more")
            box.label(text="Delete them, move them into a")
            box.label(text="product, or switch off their")
            box.label(text="render visibility (camera icon).")

        ticked = sum(1 for pc in prods if pc.mv_render)
        row = layout.row(align=True)
        row.scale_y = 1.3
        row.operator("mv.render_all", icon='RENDER_STILL',
                     text="Render All" if ticked == len(prods) else f"Render {ticked} Ticked",
                     ).only_active = False
        row.operator("mv.render_all", text="Render Active",
                     icon='RESTRICT_RENDER_OFF').only_active = True

        if s.reframe_on_render:
            # What Render All is about to build, not what is in MV_Cameras now.
            n_cams = sum(1 for v in planned_views(s) if Vector(v[2]).length >= 1e-9)
        else:
            cam_coll = bpy.data.collections.get(CAMERA_COLL)
            n_cams = len([o for o in cam_coll.objects if o.type == 'CAMERA']) if cam_coll else 0
        mult = ((2 if s.render_mode == 'BOTH' else 1) + s.pass_lines + s.pass_mask + s.pass_ao
                + len(data_modes(s)))
        layout.label(text=f"{ticked} products x {n_cams} views x {mult} = {ticked * n_cams * mult} images")
        if s.turntable_enabled:
            layout.label(text=f"+ {ticked} turntable(s) x {s.turntable_frames} frames")
        layout.label(text="Esc stops after the image in progress.", icon='INFO')
        layout.label(text="Engine/samples/resolution/format: Blender Output props", icon='INFO')


class _RenderSubPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MultiView"
    bl_parent_id = "MV_PT_Render"
    bl_options = {'DEFAULT_CLOSED'}


class MV_PT_RenderPreflight(_RenderSubPanel, Panel):
    bl_label = "Pre-flight"
    bl_options = set()

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        row = layout.row(align=True)
        row.operator("mv.preflight", icon='CHECKMARK')
        row.prop(s, "preflight_on_render", text="On Render", toggle=True)
        if not s.preflight_time:
            layout.label(text="Not checked yet.")
            return
        if not s.preflight_issues:
            layout.label(text=f"All clear ({s.preflight_time})", icon='CHECKMARK')
            return
        layout.label(text=f"Checked {s.preflight_time}:")
        col = layout.column(align=True)
        for item in list(s.preflight_issues)[:12]:
            row = col.row(align=True)
            text = f"{item.product}: {item.message}" if item.product else item.message
            row.label(text=text, icon='CANCEL' if item.severity == 'ERROR' else 'ERROR')
            if item.fix:
                op = row.operator("mv.preflight_fix", text="",
                                  icon='FILE_TICK' if item.fix == 'SAVE_HINT' else 'TOOL_SETTINGS')
                op.fix = item.fix
                op.product = item.product
        if len(s.preflight_issues) > 12:
            col.label(text=f"+{len(s.preflight_issues) - 12} more")


class MV_PT_RenderNaming(_RenderSubPanel, Panel):
    bl_label = "Naming"
    bl_options = set()

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        row = layout.row(align=True)
        row.prop(s, "start_prefix")
        row.prop(s, "start_number")
        layout.prop(s, "products_per_letter")
        layout.prop(s, "folder_template")
        layout.prop(s, "file_template")
        col = layout.column(align=True)
        col.label(text="Tokens: {label} {prefix} {number}")
        col.label(text="{product} {view} {mode}")

        # The first image of the batch, as it will actually be written.
        prods = get_products()
        views = planned_views(s)
        mode = {'FULL': "", 'CLAY': "clay", 'BOTH': "render"}[s.render_mode]
        values = name_values(s, 0, prods[0].name if prods else "Product",
                             views[0][0] if views else "Front", mode)
        folder = output_folder(s, values).replace(os.sep, "/")
        col = layout.column(align=True)
        col.label(text=f"{folder}/" if folder else "(output directory)", icon='FILE_FOLDER')
        col.label(text=output_basename(s, values) + context.scene.render.file_extension,
                  icon='FILE_IMAGE')


class MV_PT_RenderSheet(_RenderSubPanel, Panel):
    bl_label = "Contact Sheet"

    def draw_header(self, context):
        self.layout.prop(context.scene.mv_settings, "sheet_enabled", text="")

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        layout.active = s.sheet_enabled
        row = layout.row(align=True)
        row.prop(s, "sheet_columns")
        row.prop(s, "sheet_cell_width")
        layout.prop(s, "sheet_bg")
        layout.prop(s, "sheet_labels")
        sub = layout.row()
        sub.active = s.sheet_labels
        sub.prop(s, "sheet_text_color")
        if s.sheet_labels and not hasattr(blf, "bind_imbuf"):
            layout.label(text="Labels need a newer Blender.", icon='ERROR')
        if s.post_enabled:
            layout.label(text="Built from the processed copies.", icon='INFO')


class MV_PT_RenderTurntable(_RenderSubPanel, Panel):
    bl_label = "Turntable"

    def draw_header(self, context):
        self.layout.prop(context.scene.mv_settings, "turntable_enabled", text="")

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        layout.active = s.turntable_enabled
        layout.prop(s, "turntable_style")
        row = layout.row(align=True)
        row.prop(s, "turntable_frames")
        row.prop(s, "turntable_fps")
        layout.prop(s, "turntable_elevation")
        row = layout.row(align=True)
        row.prop(s, "turntable_mp4", toggle=True)
        row.prop(s, "turntable_gif", toggle=True)
        sub = layout.row()
        sub.active = s.turntable_gif
        sub.prop(s, "turntable_gif_size")
        layout.label(text="Frames are kept in a turntable folder.", icon='INFO')


class MV_PT_RenderPost(_RenderSubPanel, Panel):
    bl_label = "Post-Processing"

    def draw_header(self, context):
        self.layout.prop(context.scene.mv_settings, "post_enabled", text="")

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        layout.active = s.post_enabled
        layout.prop(s, "post_folder")
        row = layout.row(align=True)
        row.prop(s, "post_trim")
        sub = row.row(align=True)
        sub.active = s.post_trim
        sub.prop(s, "post_margin")
        layout.prop(s, "post_square")
        row = layout.row(align=True)
        row.prop(s, "post_flatten", text="Flatten")
        sub = row.row(align=True)
        sub.active = s.post_flatten or s.post_format == 'JPEG'
        sub.prop(s, "post_bg_color", text="")
        row = layout.row(align=True)
        row.prop(s, "post_format", text="")
        sub = row.row(align=True)
        sub.active = s.post_format != 'PNG'
        sub.prop(s, "post_quality")
        layout.prop(s, "post_max_size")
        layout.label(text="Extra sizes, e.g. 1024, 256:")
        layout.prop(s, "post_extra_sizes", text="")


class MV_PT_RenderPasses(_RenderSubPanel, Panel):
    bl_label = "Extra Passes"

    @classmethod
    def poll(cls, context):
        s = context.scene.mv_settings
        return s.pass_lines or s.pass_ao

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        if s.pass_lines:
            layout.label(text="Line Art:")
            layout.prop(s, "lines_angle")
            row = layout.row(align=True)
            row.prop(s, "lines_width")
            row.prop(s, "lines_color", text="")
            layout.prop(s, "lines_fill")
        if s.pass_ao:
            layout.label(text="Ambient Occlusion:")
            row = layout.row(align=True)
            row.prop(s, "ao_samples", text="Samples")
            row.prop(s, "ao_distance", text="Distance")
            if not hasattr(context.scene, "cycles"):
                layout.label(text="Needs the Cycles add-on.", icon='ERROR')


class MV_PT_RenderAnnotations(_RenderSubPanel, Panel):
    bl_label = "Annotations"

    def draw(self, context):
        layout = self.layout
        s = context.scene.mv_settings
        col = layout.column(align=True)
        col.prop(s, "export_cameras", text="Cameras (cameras.json, transforms.json)")
        layout.label(text="Data passes (Cycles, EXR / 16-bit PNG):")
        row = layout.row(align=True)
        row.prop(s, "pass_depth", toggle=True)
        row.prop(s, "pass_normal", toggle=True)
        row.prop(s, "pass_parts", toggle=True)
        layout.label(text="Dataset formats:")
        row = layout.row(align=True)
        row.prop(s, "export_coco", toggle=True)
        row.prop(s, "export_bop", toggle=True)
        if s.export_coco and not s.pass_parts:
            layout.label(text="COCO renders Part IDs too.", icon='INFO')
        if s.export_bop:
            if not s.pass_depth:
                layout.label(text="BOP renders Depth too.", icon='INFO')
            layout.label(text="BOP uses perspective views only.", icon='INFO')
        if data_modes(s) and not hasattr(context.scene, "cycles"):
            layout.label(text="Needs the Cycles add-on.", icon='ERROR')


class MV_PT_RenderManifest(_RenderSubPanel, Panel):
    bl_label = "Manifest"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene.mv_settings, "manifest_format", text="Write")
        layout.label(text="Saved in the output directory.", icon='INFO')


classes = (
    MV_AddonPreferences,
    MV_StepFileItem,
    MV_Issue,
    MV_CustomView,
    MV_Settings,
    MV_OT_AddStepFile,
    MV_OT_RemoveStepFile,
    MV_OT_ClearStepFiles,
    MV_OT_AddFolder,
    MV_OT_ImportAllSteps,
    MV_OT_ApplySceneSetup,
    MV_OT_BuildCameras,
    MV_OT_BuildLighting,
    MV_OT_ApplyWorld,
    MV_OT_SaveLightingPreset,
    MV_OT_DeleteLightingPreset,
    MV_OT_AddCustomView,
    MV_OT_RemoveCustomView,
    MV_OT_AddProductCollection,
    MV_OT_Standardize,
    MV_OT_RotateProduct,
    MV_OT_AutoOrient,
    MV_OT_ResetOrientation,
    MV_OT_ProductStep,
    MV_OT_ShowAllProducts,
    MV_OT_SetProductsRender,
    MV_OT_Preflight,
    MV_OT_PreflightFix,
    MV_OT_RenderPreflightPrompt,
    MV_OT_RenderAll,
    MV_UL_StepFiles,
    MV_UL_CustomViews,
    MV_UL_Products,
    # Panels draw in the sidebar in the order they are registered.
    MV_PT_Guide,
    MV_PT_SceneSetup,
    MV_PT_SceneMaterials,
    MV_PT_Import,
    MV_PT_Standardize,
    MV_PT_Cameras,
    MV_PT_Render,
    MV_PT_RenderPreflight,
    MV_PT_RenderNaming,
    MV_PT_RenderSheet,
    MV_PT_RenderTurntable,
    MV_PT_RenderPasses,
    MV_PT_RenderPost,
    MV_PT_RenderAnnotations,
    MV_PT_RenderManifest,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.mv_settings = PointerProperty(type=MV_Settings)
    # Stored on the collection itself, so the tick travels with the product
    # when it is renamed, reordered or appended into another file.
    bpy.types.Collection.mv_render = BoolProperty(
        name="Render",
        description="Include this product when rendering. Unticked products keep "
                    "their label, so the rest of the batch is not renumbered",
        default=True,
    )
    bpy.types.Collection.mv_material = EnumProperty(
        name="Material",
        description="Material this product renders with in Full renders",
        items=[('DEFAULT', "Batch Default", "Use the batch's material setting"),
               ('KEEP', "Keep Own", "Use the materials this product already has")]
              + MATERIAL_ITEMS,
        default='DEFAULT',
    )
    bpy.types.Collection.mv_material_color = FloatVectorProperty(
        name="Color", subtype='COLOR', size=3,
        min=0.0, max=1.0, default=(0.8, 0.8, 0.8),
    )
    bpy.types.Collection.mv_source = StringProperty(
        name="Source File",
        description="The CAD file this product was imported from",
        subtype='FILE_PATH',
    )
    bpy.types.Collection.mv_source_size = FloatVectorProperty(
        name="Source Size",
        description="Bounding box of the product as imported, before Fit on Import "
                    "scaled it, in the source file's units",
        size=3,
    )
    bpy.types.Collection.mv_to_world = FloatVectorProperty(
        name="Source to World",
        description="Row-major 4x4 matrix from the product's source coordinates to the "
                    "scene, accumulated from every move MultiView has made to it",
        size=16, default=IDENTITY_16,
    )
    bpy.types.Collection.mv_label_index = IntProperty(
        name="Label Index",
        description="Position in the batch this product's label is taken from. -1 uses "
                    "its place in MV_Products; the command line sets it so shards "
                    "rendered separately still get labels that do not collide",
        default=-1, min=-1,
    )
    bpy.types.Collection.mv_source_units = StringProperty(
        name="Source Units",
        description="Unit Source Size is in: mm, cm, m, in or ft. Empty when not known",
    )


def unregister():
    del bpy.types.Collection.mv_label_index
    del bpy.types.Collection.mv_to_world
    del bpy.types.Collection.mv_source_units
    del bpy.types.Collection.mv_source_size
    del bpy.types.Collection.mv_source
    del bpy.types.Collection.mv_material_color
    del bpy.types.Collection.mv_material
    del bpy.types.Collection.mv_render
    del bpy.types.Scene.mv_settings
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
