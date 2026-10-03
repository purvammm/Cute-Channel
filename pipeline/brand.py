"""Load and check the brand files in brand/ (`python cc.py validate`).

There are two layers:
1. JSON Schema: is the file structurally right (types, required fields, ranges)?
2. Brand lint: does it follow the guide's craft rules, and do the cross-references resolve
   (colour names exist in the palette, emotions only use face shapes every character has)?
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import specs
from .paths import BRAND_DIR

SCHEMA_DIR = BRAND_DIR / "schemas"
FILES = {
    "palette": ("palette.json", "palette.schema.json"),
    "character": ("character.json", "character.schema.json"),
    "emotions": ("emotions.json", "emotions.schema.json"),
}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load(name: str, brand_dir: Path = BRAND_DIR) -> dict:
    return json.loads((brand_dir / FILES[name][0]).read_text(encoding="utf-8"))


def load_all(brand_dir: Path = BRAND_DIR) -> dict[str, dict]:
    return {name: load(name, brand_dir) for name in FILES}


def schema_errors(data: dict, schema_file: str) -> list[str]:
    import jsonschema  # imported here so `cc.py doctor` never needs it

    schema = json.loads((SCHEMA_DIR / schema_file).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}" for e in errors]


def lint(data: dict[str, dict]) -> Report:
    """Craft rules from docs/GUIDE_DIGEST.md and cross-file references."""
    report = Report()
    colors = data["palette"]["colors"]
    characters = data["character"]["characters"]
    emotions = data["emotions"]["emotions"]

    def need_color(where: str, ref: str | None) -> None:
        if ref is not None and ref not in colors:
            report.errors.append(f"{where}: colour '{ref}' is not in palette.json")

    heroes = [key for key, c in characters.items() if c["role"] == "hero"]
    if len(heroes) != 1:
        report.errors.append(f"exactly one character must have role 'hero' (found {heroes})")

    low, high = specs.VOICE_PITCH_SEMITONES
    for key, c in characters.items():
        for part in ("eyes", "mouth", "blush", "brow", "material"):
            need_color(f"{key}.{part}", c[part].get("color"))
        need_color(f"{key}.eyes.highlight_color", c["eyes"].get("highlight_color"))

        eyes, mouth = set(c["face_variants"]["eyes"]), set(c["face_variants"]["mouth"])
        if c["eyes"]["rest"] not in eyes:
            report.errors.append(f"{key}: eyes.rest '{c['eyes']['rest']}' isn't in face_variants")
        if c["mouth"]["rest"] not in mouth:
            report.errors.append(f"{key}: mouth.rest '{c['mouth']['rest']}' isn't in face_variants")
        # G30: big, low eyes. The hero's eyes sit below the middle of the face.
        if c["role"] == "hero" and c["eyes"]["center_height"] >= 0.5:
            report.errors.append(f"{key}: hero eyes must sit below the middle (G30)")
        if c["mouth"]["center_height"] >= c["eyes"]["center_height"]:
            report.errors.append(f"{key}: the mouth must sit below the eyes")
        # G33: soft matte skin, a little subsurface, glinting eyes, see-through blush.
        material = c["material"]
        if material["roughness"] < 0.45:
            report.errors.append(f"{key}: roughness {material['roughness']} looks plastic (G33)")
        if material["subsurface_weight"] > 0.2:
            report.warnings.append(f"{key}: subsurface over 0.2 can look waxy (G33)")
        if not 0.05 <= c["eyes"]["roughness"] <= 0.25:
            report.warnings.append(f"{key}: eye roughness 0.1-0.2 catches a glint (G33)")
        if c["blush"]["alpha"] > 0.6:
            report.warnings.append(f"{key}: blush alpha above 0.6 stops looking soft (G33)")
        eye_hex = colors.get(c["eyes"]["color"], {}).get("hex", "#000000").lower()
        if eye_hex in ("#000000", "#000"):
            report.errors.append(f"{key}: eyes must be dark, not pure black (G33)")
        # G17: a fixed, cute voice pitch.
        if not low <= c["voice"]["pitch_semitones"] <= high:
            report.errors.append(f"{key}: voice pitch must be +{low}..+{high} semitones (G17)")

    names = [e["name"] for e in emotions]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        report.errors.append(f"emotions: duplicate names {sorted(duplicates)}")
    for emotion in emotions:
        for key, c in characters.items():
            if emotion["eyes"] not in c["face_variants"]["eyes"]:
                report.errors.append(
                    f"emotion {emotion['name']}: {key} has no eyes '{emotion['eyes']}'"
                )
            if emotion["mouth"] not in c["face_variants"]["mouth"]:
                report.errors.append(
                    f"emotion {emotion['name']}: {key} has no mouth '{emotion['mouth']}'"
                )
        if emotion["min_hold_frames"] < specs.MIN_HOLD_FRAMES:
            report.errors.append(f"emotion {emotion['name']}: hold under 15 frames (G21)")
    return report


def validate(brand_dir: Path = BRAND_DIR) -> Report:
    report = Report()
    data = {}
    for name, (data_file, schema_file) in FILES.items():
        try:
            data[name] = load(name, brand_dir)
        except (OSError, ValueError) as exc:
            report.errors.append(f"{data_file}: cannot read ({exc})")
            continue
        report.errors += [
            f"{data_file}: {message}" for message in schema_errors(data[name], schema_file)
        ]
    if report.ok:
        linted = lint(data)
        report.errors += linted.errors
        report.warnings += linted.warnings
    return report


def main() -> int:
    report = validate()
    for warning in report.warnings:
        print(f"warning: {warning}")
    for error in report.errors:
        print(f"error: {error}")
    if report.ok:
        print("brand/*.json: valid (schema + craft rules)")
        return 0
    print(f"{len(report.errors)} problem(s) in brand/*.json")
    return 1
