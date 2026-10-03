"""Headless render smoke test. Runs inside Blender, not your normal Python.

`python cc.py doctor --deep` runs this once per render engine to learn what this machine can
render and how fast. It builds a tiny pastel scene (a blob with eyes on a floor), renders a few
frames, checks the pictures aren't blank, and writes a JSON result. To run it by hand:

    blender -b --factory-startup -noaudio --python blender/smoke_test.py -- \
        --engine EEVEE --out /abs/path/probe --result /abs/path/probe/result.json

The scene is a placeholder for testing engines. It is not the channel's character.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
from array import array
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make `lib` importable
from lib import colors, compat  # noqa: E402

BODY_HEX = "#ff8fb1"  # placeholder pastels from the guide's page style, not the brand palette
EYE_HEX = "#2f2a3b"
FLOOR_HEX = "#e1f7ef"
WORLD_HEX = "#e3f2ff"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="smoke_test.py")
    parser.add_argument("--engine", default="EEVEE", help="EEVEE, CYCLES or WORKBENCH")
    parser.add_argument("--label", default=None, help="name used for the output files")
    parser.add_argument("--out", required=True, type=Path, help="folder for the PNGs")
    parser.add_argument("--result", required=True, type=Path, help="where to write the JSON")
    parser.add_argument("--frames", type=int, default=2)
    parser.add_argument("--resolution", default="270x480", help="WIDTHxHEIGHT")
    parser.add_argument("--samples", type=int, default=16)
    return parser.parse_args(argv)


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh_object(name, build, material):
    """Build a mesh with bmesh (no bpy.ops, so it works without a UI context)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material)
    return link(bpy.data.objects.new(name, mesh))


def make_material(name, hex_code, roughness, subsurface=0.0):
    material = compat.new_material(name)
    bsdf = compat.principled_node(material)
    compat.set_input(bsdf, ("Base Color",), (*colors.hex_to_linear(hex_code), 1.0))
    compat.set_input(bsdf, ("Roughness",), roughness)
    compat.set_input(bsdf, ("Subsurface Weight", "Subsurface"), subsurface)
    return material


def track_to(obj, target):
    constraint = obj.constraints.new("TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"


def build_scene(width: int, height: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.render.image_settings.file_format = "PNG"

    mesh_object(
        "floor",
        lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=10),
        make_material("floor", FLOOR_HEX, 0.8),
    )

    body = mesh_object(
        "body",
        lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.5),
        make_material("body", BODY_HEX, 0.6, 0.1),
    )
    body.location = (0.0, 0.0, 0.5)
    body.scale = (1.05, 1.0, 0.95)
    subdivision = body.modifiers.new("Subdivision", "SUBSURF")
    subdivision.levels = 2
    subdivision.render_levels = 2
    compat.shade_smooth(body.data)

    eye_material = make_material("eye", EYE_HEX, 0.15)
    for side, x in (("L", 0.17), ("R", -0.17)):
        eye = mesh_object(
            f"eye.{side}",
            lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.07),
            eye_material,
        )
        eye.parent = body
        eye.location = (x, -0.46, -0.04)  # on the front (-Y), a little below the middle
        eye.scale = (1.0, 0.6, 1.25)
        compat.shade_smooth(eye.data)

    key = bpy.data.lights.new("key", "AREA")
    key.energy = 400.0
    key.size = 2.5
    key.color = (1.0, 0.95, 0.9)
    key_light = link(bpy.data.objects.new("key", key))
    key_light.location = (-2.0, -2.5, 3.0)
    track_to(key_light, body)

    camera_data = bpy.data.cameras.new("camera")
    camera_data.lens = 70.0
    camera_data.dof.use_dof = True
    camera_data.dof.focus_object = body
    camera_data.dof.aperture_fstop = 2.8
    camera = link(bpy.data.objects.new("camera", camera_data))
    camera.location = (0.0, -6.0, 1.4)
    track_to(camera, body)
    scene.camera = camera

    compat.set_world_color(scene, colors.hex_to_linear(WORLD_HEX), 0.8)
    return scene, body


def image_check(path: Path) -> dict:
    """Brightness spread of the render: a blank or all-black frame has almost none."""
    image = bpy.data.images.load(str(path))
    values = array("f", [0.0]) * len(image.pixels)
    image.pixels.foreach_get(values)
    luma = [
        0.2126 * values[i] + 0.7152 * values[i + 1] + 0.0722 * values[i + 2]
        for i in range(0, len(values), 4)
    ]
    bpy.data.images.remove(image)
    mean = sum(luma) / len(luma)
    std = math.sqrt(sum((v - mean) ** 2 for v in luma) / len(luma))
    return {"mean": round(mean, 4), "std": round(std, 4), "looks_blank": std < 0.01}


def main() -> None:
    args = parse_args()
    label = args.label or args.engine.lower()
    args.out.mkdir(parents=True, exist_ok=True)
    result = {"ok": False, "label": label, "engine": args.engine}
    try:
        width, height = (int(v) for v in args.resolution.lower().split("x"))
        scene, body = build_scene(width, height)
        result["blender_version"] = bpy.app.version_string
        engine_id = compat.resolve_engine(args.engine, scene)
        compat.configure_engine(scene, engine_id, samples=args.samples)

        times, images = [], []
        for index in range(args.frames):
            frame = 1 + index
            scene.frame_set(frame)
            body.location.z = 0.5 + 0.25 * index  # move between frames so each render differs
            path = args.out / f"{label}_{frame:04d}.png"
            scene.render.filepath = str(path)
            start = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            times.append(time.perf_counter() - start)
            images.append(str(path))

        steady = times[1:] or times  # the first frame includes one-off shader compilation
        result.update(
            ok=True,
            engine_id=engine_id,
            frame_seconds=[round(t, 3) for t in times],
            seconds_per_frame=round(sum(steady) / len(steady), 3),
            images=images,
            gpu=compat.gpu_info(),
            image_check=image_check(Path(images[-1])),
        )
    except Exception:
        result["error"] = traceback.format_exc(limit=6)
        raise
    finally:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, indent=2), encoding="utf-8")


main()
