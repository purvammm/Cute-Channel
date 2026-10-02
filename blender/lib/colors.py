"""Colour helpers shared by Blender scripts and the 2D pipeline (pure Python, no bpy).

Blender's colour sockets expect *linear* RGB. Brand palettes are written as sRGB hex codes,
which is what you see in a colour picker. Converting in one place keeps the 3D render, the SVG
character sheets and the captions on exactly the same palette.
"""

from __future__ import annotations

_HEX_DIGITS = set("0123456789abcdefABCDEF")


def hex_to_srgb(hex_code: str) -> tuple[float, float, float]:
    """'#ff8fb1' -> (1.0, 0.56, 0.69). Also accepts 3-digit codes like '#fab'."""
    digits = hex_code.strip().lstrip("#")
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    if len(digits) != 6 or not set(digits) <= _HEX_DIGITS:
        raise ValueError(f"not a hex colour: {hex_code!r}")
    return tuple(int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))


def srgb_to_linear(channel: float) -> float:
    """The standard sRGB transfer curve (IEC 61966-2-1)."""
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def hex_to_linear(hex_code: str) -> tuple[float, float, float]:
    """A hex colour as the linear RGB values Blender's colour sockets expect."""
    return tuple(srgb_to_linear(c) for c in hex_to_srgb(hex_code))
