"""Schematic character sheets drawn from brand/*.json (`python cc.py brand-sheets`).

Writes to docs/brand/sheets/:
  character_sheet.png   both characters to scale, proportion guides, palette, personality
  turnaround.png        front / three-quarter / side / back
  expressions.png       every emotion in brand/emotions.json, on each character
  thumbnail_test.png    the same faces at 96x170 px: the guide's thumbnail test (§2)

These are flat 2D schematics, so the design can be reviewed before any 3D exists. The Blender
model (Phase 2) is the source of truth; if they disagree, the model wins. Everything is drawn
from the JSON files, so changing a number there and re-running keeps every sheet consistent.
"""

from __future__ import annotations

import math
from pathlib import Path
from xml.sax.saxutils import escape

from . import brand
from .paths import DOCS_DIR, REPO_ROOT

OUT_DIR = DOCS_DIR / "brand" / "sheets"
FONT_FILE = REPO_ROOT / "assets" / "fonts" / "Baloo2-Variable.ttf"
FONT = "'Baloo 2', sans-serif"
THUMB_SIZE = (96, 170)  # guide §2 / MASTER_PROMPT Phase 2: does it read this small?


# --- colour helpers ------------------------------------------------------------------------


class Palette:
    def __init__(self, data: dict):
        self.colors = data["colors"]

    def hex(self, name: str) -> str:
        return self.colors[name]["hex"]

    def alpha(self, name: str) -> float:
        return self.colors[name].get("alpha", 1.0)


def mix(hex_a: str, hex_b: str, t: float) -> str:
    """Blend two hex colours: t=0 gives a, t=1 gives b."""
    a = [int(hex_a[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b, strict=True))


def f(value: float) -> str:
    """Short number formatting keeps the SVG small and diff-friendly."""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def text(x, y, content, size, color, weight=400, anchor="start") -> str:
    return (
        f'<text x="{f(x)}" y="{f(y)}" font-family="{FONT}" font-size="{f(size)}" '
        f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(content)}</text>'
    )


def wrap(content: str, max_chars: int) -> list[str]:
    """Greedy word wrap (no mid-word breaks)."""
    lines, current = [], ""
    for word in content.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + ([current] if current else [])


def paragraph(x, y, content, size, color, max_chars, line_height=1.35, weight=400):
    """Wrapped text block. Returns (svg, y below the block)."""
    lines = wrap(content, max_chars)
    svg = "".join(
        text(x, y + i * size * line_height, line, size, color, weight)
        for i, line in enumerate(lines)
    )
    return svg, y + len(lines) * size * line_height


def heart_path(cx: float, cy: float, size: float) -> str:
    s = size / 2
    return (
        f"M{f(cx)},{f(cy + s * 0.9)} "
        f"C{f(cx - s * 1.6)},{f(cy - s * 0.1)} {f(cx - s * 0.7)},{f(cy - s * 1.2)} "
        f"{f(cx)},{f(cy - s * 0.45)} "
        f"C{f(cx + s * 0.7)},{f(cy - s * 1.2)} {f(cx + s * 1.6)},{f(cy - s * 0.1)} "
        f"{f(cx)},{f(cy + s * 0.9)} Z"
    )


def spiral_path(cx: float, cy: float, radius: float, turns: float = 2.2) -> str:
    points = []
    steps = 40
    for i in range(steps + 1):
        t = i / steps
        angle = t * turns * 2 * math.pi
        r = radius * t
        points.append(f"{f(cx + r * math.cos(angle))},{f(cy + r * math.sin(angle))}")
    return "M" + " L".join(points)


def star_path(cx: float, cy: float, r: float) -> str:
    """A four-point sparkle."""
    q = r * 0.28
    return (
        f"M{f(cx)},{f(cy - r)} Q{f(cx + q)},{f(cy - q)} {f(cx + r)},{f(cy)} "
        f"Q{f(cx + q)},{f(cy + q)} {f(cx)},{f(cy + r)} Q{f(cx - q)},{f(cy + q)} "
        f"{f(cx - r)},{f(cy)} Q{f(cx - q)},{f(cy - q)} {f(cx)},{f(cy - r)} Z"
    )


# --- face parts ----------------------------------------------------------------------------


def draw_eye(variant, x, y, w, h, side, k, pal, highlights, uid) -> str:
    """One eye centred at (x, y). `side` is -1 for the viewer's left eye; `k` squeezes it
    horizontally when the head is turned (foreshortening)."""
    ink = pal.hex("eye")
    stroke = max(1.0, h * 0.2)
    w = w * k
    line = f'fill="none" stroke="{ink}" stroke-width="{f(stroke)}" stroke-linecap="round" stroke-linejoin="round"'

    def dots(scale=1.0, cx=x, cy=y, ww=w, hh=h):
        return "".join(
            f'<circle cx="{f(cx + hl["x"] * ww)}" cy="{f(cy - hl["y"] * hh)}" '
            f'r="{f(hl["size"] * hh / 2 * scale)}" fill="{pal.hex("highlight")}"/>'
            for hl in highlights
        )

    if variant in ("open", "wide"):
        scale = 1.22 if variant == "wide" else 1.0
        ww, hh = w * scale, h * scale
        body = f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(ww / 2)}" ry="{f(hh / 2)}" fill="{ink}"/>'
        return body + dots(0.8 if variant == "wide" else 1.0, ww=ww, hh=hh)
    if variant == "happy":
        return f'<path d="M{f(x - w / 2)},{f(y + h * 0.15)} Q{f(x)},{f(y - h * 0.6)} {f(x + w / 2)},{f(y + h * 0.15)}" {line}/>'
    if variant == "closed":
        return f'<path d="M{f(x - w / 2)},{f(y - h * 0.05)} Q{f(x)},{f(y + h * 0.45)} {f(x + w / 2)},{f(y - h * 0.05)}" {line}/>'
    if variant == "teary":
        tear = (
            f'<rect x="{f(x - w * 0.2)}" y="{f(y)}" width="{f(w * 0.4)}" height="{f(h * 1.5)}" '
            f'rx="{f(w * 0.2)}" fill="{pal.hex("tear")}" opacity="0.9"/>'
        )
        bar = f'<path d="M{f(x - w * 0.6)},{f(y)} L{f(x + w * 0.6)},{f(y)}" {line}/>'
        return tear + bar
    if variant == "squint":
        tip = -side  # left eye points right (>) and right eye points left (<): >_<
        return (
            f'<path d="M{f(x - tip * w / 2)},{f(y - h * 0.38)} L{f(x + tip * w / 2)},{f(y)} '
            f'L{f(x - tip * w / 2)},{f(y + h * 0.38)}" {line}/>'
        )
    if variant == "heart":
        return f'<path d="{heart_path(x, y, h * 1.15)}" fill="{pal.hex("blush")}"/>' + (
            f'<circle cx="{f(x - w * 0.18)}" cy="{f(y - h * 0.2)}" r="{f(h * 0.1)}" fill="{pal.hex("highlight")}"/>'
        )
    if variant == "half":
        lid = y - h * 0.08
        clip = f"half-{uid}"
        return (
            f'<clipPath id="{clip}"><rect x="{f(x - w)}" y="{f(lid)}" width="{f(w * 2)}" height="{f(h)}"/></clipPath>'
            f'<g clip-path="url(#{clip})"><ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(w / 2)}" ry="{f(h / 2)}" fill="{ink}"/>'
            f"{dots(0.7, cy=y + h * 0.12)}</g>"
            f'<path d="M{f(x - w * 0.62)},{f(lid)} L{f(x + w * 0.62)},{f(lid)}" {line}/>'
        )
    if variant == "spiral":
        return f'<path d="{spiral_path(x, y, h * 0.5)}" fill="none" stroke="{ink}" stroke-width="{f(stroke * 0.7)}" stroke-linecap="round"/>'
    raise ValueError(f"unknown eye variant {variant!r}")


def draw_mouth(variant, x, y, mw, lw, k, pal) -> str:
    ink, tongue = pal.hex("eye"), mix(pal.hex("blush"), "#ffffff", 0.2)
    mw = mw * k
    line = f'fill="none" stroke="{ink}" stroke-width="{f(lw)}" stroke-linecap="round" stroke-linejoin="round"'
    if variant == "smile":
        return f'<path d="M{f(x - mw / 2)},{f(y)} Q{f(x)},{f(y + mw * 0.55)} {f(x + mw / 2)},{f(y)}" {line}/>'
    if variant == "grin":
        g = mw * 1.25
        return (
            f'<path d="M{f(x - g / 2)},{f(y)} Q{f(x)},{f(y + g * 0.95)} {f(x + g / 2)},{f(y)} Z" fill="{ink}"/>'
            f'<ellipse cx="{f(x)}" cy="{f(y + g * 0.3)}" rx="{f(g * 0.2)}" ry="{f(g * 0.1)}" fill="{tongue}"/>'
        )
    if variant == "o":
        return f'<ellipse cx="{f(x)}" cy="{f(y + mw * 0.15)}" rx="{f(mw * 0.26)}" ry="{f(mw * 0.34)}" fill="{ink}"/>'
    if variant == "flat":
        return f'<path d="M{f(x - mw * 0.42)},{f(y)} L{f(x + mw * 0.42)},{f(y)}" {line}/>'
    if variant == "frown":
        return f'<path d="M{f(x - mw / 2)},{f(y + mw * 0.25)} Q{f(x)},{f(y - mw * 0.3)} {f(x + mw / 2)},{f(y + mw * 0.25)}" {line}/>'
    if variant == "wavy":
        q = mw / 4
        return f'<path d="M{f(x - mw / 2)},{f(y)} q{f(q / 2)},{f(-q / 2)} {f(q)},0 t{f(q)},0 t{f(q)},0 t{f(q)},0" {line}/>'
    if variant == "wail":
        g = mw * 1.4
        return (
            f'<path d="M{f(x - g * 0.45)},{f(y - g * 0.05)} Q{f(x)},{f(y - g * 0.22)} {f(x + g * 0.45)},{f(y - g * 0.05)} '
            f"Q{f(x + g * 0.38)},{f(y + g * 0.8)} {f(x)},{f(y + g * 0.8)} Q{f(x - g * 0.38)},{f(y + g * 0.8)} "
            f'{f(x - g * 0.45)},{f(y - g * 0.05)} Z" fill="{ink}"/>'
            f'<ellipse cx="{f(x)}" cy="{f(y + g * 0.55)}" rx="{f(g * 0.2)}" ry="{f(g * 0.12)}" fill="{tongue}"/>'
        )
    raise ValueError(f"unknown mouth variant {variant!r}")


def draw_steam(shape, x0, y0, hs, thickness, pal) -> str:
    """Chuski's steam wisp, its eyebrow. (x0, y0) is where it leaves the head."""
    white = pal.hex("steam")
    under = f'stroke="#8fa9bd" stroke-opacity="0.45" stroke-width="{f(thickness * 1.6)}"'
    over = f'stroke="{white}" stroke-opacity="{pal.alpha("steam") + 0.15:.2f}" stroke-width="{f(thickness)}"'
    common = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    if shape == "gone":
        return ""
    if shape in ("curl", "curl_high"):
        s = 1.3 if shape == "curl_high" else 1.0
        y = y0 - (hs * 0.15 if shape == "curl_high" else 0)
        d = (
            f"M{f(x0)},{f(y)} C{f(x0 - hs * 0.32 * s)},{f(y - hs * 0.28 * s)} {f(x0 + hs * 0.34 * s)},{f(y - hs * 0.5 * s)} "
            f"{f(x0)},{f(y - hs * 0.78 * s)} C{f(x0 - hs * 0.16 * s)},{f(y - hs * 0.92 * s)} {f(x0 + hs * 0.1 * s)},{f(y - hs * 1.04 * s)} "
            f"{f(x0 + hs * 0.16 * s)},{f(y - hs * 0.9 * s)}"
        )
    elif shape == "droop":  # a wilted sprout: up a little, then flopping over the side
        d = f"M{f(x0)},{f(y0)} C{f(x0)},{f(y0 - hs * 0.5)} {f(x0 + hs * 0.55)},{f(y0 - hs * 0.55)} {f(x0 + hs * 0.62)},{f(y0 + hs * 0.08)}"
    elif shape == "zigzag":
        d = (
            f"M{f(x0)},{f(y0)} l{f(hs * 0.13)},{f(-hs * 0.2)} l{f(-hs * 0.22)},{f(-hs * 0.2)} "
            f"l{f(hs * 0.22)},{f(-hs * 0.2)} l{f(-hs * 0.13)},{f(-hs * 0.2)}"
        )
    elif shape == "heart":
        cy = y0 - hs * 0.62
        d = f"M{f(x0)},{f(y0)} L{f(x0)},{f(cy + hs * 0.25)} " + heart_path(x0, cy, hs * 0.55)
    elif shape == "spiral":
        d = f"M{f(x0)},{f(y0)} L{f(x0)},{f(y0 - hs * 0.25)} " + spiral_path(
            x0, y0 - hs * 0.62, hs * 0.32
        )
    elif shape == "puff":
        circles = ""
        for i, (dx, dy, r) in enumerate([(0, 0.25, 0.16), (-0.12, 0.52, 0.13), (0.1, 0.75, 0.11)]):
            circles += (
                f'<circle cx="{f(x0 + dx * hs)}" cy="{f(y0 - dy * hs)}" r="{f(r * hs)}" fill="{white}" '
                f'fill-opacity="{0.95 - i * 0.12:.2f}" stroke="#8fa9bd" stroke-opacity="0.45" stroke-width="{f(thickness * 0.3)}"/>'
            )
        return circles
    else:
        raise ValueError(f"unknown steam shape {shape!r}")
    return f'<path d="{d}" {common} {under}/><path d="{d}" {common} {over}/>'


def draw_lid_line(shape, x, y, w, h, side, k, pal, thickness) -> str:
    """Shakkar's straight brow over one eye. Inner end = the end nearest the face centre."""
    w = w * k * 1.15
    yb = y - h * 0.82
    inner = -side  # which x direction points to the face centre
    lift = {
        "level": (0, 0),
        "raised": (-0.2, -0.2),
        "angry_tilt": (-0.12, 0.16),
        "sad_tilt": (0.12, -0.18),
    }
    outer_dy, inner_dy = lift[shape]
    x_outer, x_inner = x - inner * w / 2, x + inner * w / 2
    return (
        f'<path d="M{f(x_outer)},{f(yb + outer_dy * h)} L{f(x_inner)},{f(yb + inner_dy * h)}" '
        f'stroke="{pal.hex("eye")}" stroke-width="{f(thickness)}" stroke-linecap="round"/>'
    )


def draw_emanata(kinds, cx, base, w, h, pal) -> str:
    out = ""
    top_x, top_y = cx + w * 0.45, base - h * 1.0
    for kind in kinds:
        if kind == "heart":
            out += f'<path d="{heart_path(top_x, top_y, h * 0.2)}" fill="{pal.hex("blush")}"/>'
            out += f'<path d="{heart_path(top_x + h * 0.16, top_y + h * 0.16, h * 0.11)}" fill="{pal.hex("blush")}"/>'
        elif kind == "sparkle":
            out += f'<path d="{star_path(top_x, top_y, h * 0.1)}" fill="{pal.hex("spark")}"/>'
            out += f'<path d="{star_path(cx - w * 0.5, base - h * 0.85, h * 0.06)}" fill="{pal.hex("spark")}"/>'
        elif kind == "sweat_drop":
            sx, sy, r = cx - w * 0.42, base - h * 0.9, h * 0.07
            out += (
                f'<path d="M{f(sx)},{f(sy - r * 1.8)} Q{f(sx + r * 1.1)},{f(sy - r * 0.2)} {f(sx)},{f(sy + r)} '
                f'Q{f(sx - r * 1.1)},{f(sy - r * 0.2)} {f(sx)},{f(sy - r * 1.8)} Z" fill="{pal.hex("tear")}" '
                f'stroke="{pal.hex("eye")}" stroke-width="{f(h * 0.008)}"/>'
            )
        elif kind in ("exclaim", "question"):
            glyph = "!" if kind == "exclaim" else "?"
            out += text(top_x, top_y + h * 0.08, glyph, h * 0.32, pal.hex("eye"), 800, "middle")
        elif kind == "anger_puff":
            r = h * 0.07
            arcs = "".join(
                f'<path d="M{f(top_x + dx * r)},{f(top_y + dy * r)} q{f(-dx * r * 0.6)},{f(-dy * r * 0.1)} {f(-dx * r * 0.2)},{f(-dy * r * 0.9)}" '
                f'fill="none" stroke="#e0566b" stroke-width="{f(h * 0.025)}" stroke-linecap="round"/>'
                for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1))
            )
            out += arcs
        elif kind == "zzz":
            for i, size in enumerate((0.12, 0.16, 0.2)):
                out += text(
                    top_x + i * h * 0.1,
                    top_y + h * 0.1 - i * h * 0.14,
                    "z",
                    h * size,
                    pal.hex("eye"),
                    800,
                )
        elif kind == "music_note":
            out += text(top_x, top_y + h * 0.08, "♪", h * 0.28, pal.hex("eye"), 800, "middle")
        elif kind in ("tear_stream", "steam_burst"):
            continue  # drawn by the eyes / the steam wisp
        else:
            raise ValueError(f"unknown emanata {kind!r}")
    return out


# --- whole characters ----------------------------------------------------------------------


def emotion_by_name(data: dict, name: str) -> dict:
    return next(e for e in data["emotions"]["emotions"] if e["name"] == name)


def rest_emotion(char: dict) -> dict:
    return {
        "name": "rest",
        "eyes": char["eyes"]["rest"],
        "mouth": char["mouth"]["rest"],
        "blush": 0.2,
        "brow": "neutral",
        "pose": {"scale_xy": 1.0, "scale_z": 1.0, "tilt_deg": 0, "offset_z": 0.0},
        "emanata": [],
    }


def blush_opacity(char: dict, intensity: float) -> float:
    """Blush fades in above the character's threshold (shy blushers only show strong feelings)."""
    threshold = char["blush"].get("threshold", 0.0)
    level = max(0.0, (intensity - threshold) / (1.0 - threshold))
    return char["blush"]["alpha"] * level


def draw_character(key, char, pal, cx, base, px_per_m, yaw_deg=0.0, emotion=None, uid="c") -> str:
    """One character standing on `base` (pixels), centred on `cx`, seen from `yaw_deg`."""
    emotion = emotion or rest_emotion(char)
    h = char["height_m"] * px_per_m
    body = char["body"]
    pose = emotion["pose"]
    yaw = math.radians(yaw_deg)
    main = pal.hex(char["material"]["color"])
    ink = pal.hex("eye")
    out = []

    if body["shape"] == "cube":
        front_w = h * body["width"] * abs(math.cos(yaw))
        side_w = h * body["depth"] * abs(math.sin(yaw))
        total_w = front_w + side_w
        radius = h * body.get("bevel", 0.1)
        left = cx - total_w / 2
        light, shade = mix(main, "#ffffff", 0.5), mix(main, ink, 0.1)
        shadow_index = len(out)
        out.append(
            f'<ellipse cx="{f(cx)}" cy="{f(base)}" rx="{f(total_w * 0.55)}" ry="{f(h * 0.07)}" fill="{ink}" opacity="0.13"/>'
        )
        out.append(
            f'<rect x="{f(left)}" y="{f(base - h)}" width="{f(total_w)}" height="{f(h)}" rx="{f(radius)}" '
            f'fill="{main}" stroke="{shade}" stroke-width="{f(h * 0.012)}"/>'
        )
        if side_w > 1:
            out.append(
                f'<rect x="{f(left + front_w)}" y="{f(base - h + radius * 0.3)}" width="{f(side_w - radius * 0.3)}" '
                f'height="{f(h - radius * 0.6)}" rx="{f(radius * 0.7)}" fill="{shade}" opacity="0.55"/>'
            )
        out.append(
            f'<rect x="{f(left + h * 0.06)}" y="{f(base - h + h * 0.05)}" width="{f(total_w * 0.45)}" '
            f'height="{f(h * 0.1)}" rx="{f(h * 0.05)}" fill="{light}" opacity="0.7"/>'
        )
        sparkle = char["material"].get("sparkle", 0)
        for i, (sx, sy) in enumerate(
            ((0.18, 0.2), (0.78, 0.33), (0.3, 0.78), (0.86, 0.82), (0.62, 0.12))
        ):
            if i < round(sparkle * 10) + 1:
                out.append(
                    f'<path d="{star_path(left + sx * total_w, base - h + sy * h, h * 0.035)}" fill="#ffffff" opacity="0.95"/>'
                )
        face_visible = math.cos(yaw) > 0.3
        face_cx, k = left + front_w / 2, abs(math.cos(yaw))
    else:  # dome / sphere / bean: an ellipse resting on the floor with its bottom sliced off
        half_w = h * body["width"] / 2
        half_d = h * body["depth"] / 2
        rx = math.hypot(half_w * math.cos(yaw), half_d * math.sin(yaw))
        cut = body.get("flat_bottom", 0.0)
        ry = h / (2 * (1 - cut))
        cy = base - h + ry
        clip = f"floor-{uid}"
        light, shade = mix(main, "#ffffff", 0.45), mix(main, ink, 0.14)
        grad = f"body-{uid}"
        out.append(
            f'<defs><radialGradient id="{grad}" cx="0.36" cy="0.3" r="0.8">'
            f'<stop offset="0" stop-color="{light}"/><stop offset="0.55" stop-color="{main}"/>'
            f'<stop offset="1" stop-color="{shade}"/></radialGradient>'
            f'<clipPath id="{clip}"><rect x="{f(cx - rx * 1.2)}" y="{f(base - h * 1.2)}" '
            f'width="{f(rx * 2.4)}" height="{f(h * 1.2)}"/></clipPath></defs>'
        )
        shadow_index = len(out)
        out.append(
            f'<ellipse cx="{f(cx)}" cy="{f(base)}" rx="{f(rx * 0.95)}" ry="{f(h * 0.07)}" fill="{ink}" opacity="0.13"/>'
        )
        out.append(
            f'<ellipse clip-path="url(#{clip})" cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" '
            f'fill="url(#{grad})" stroke="{shade}" stroke-width="{f(h * 0.01)}"/>'
        )
        face_visible = True
        face_cx, k = cx, 1.0

        def place(x_off: float, height: float) -> tuple[float, float, bool]:
            """Where a face feature lands when the head turns, plus its squeeze and visibility."""
            dy = (base - height * h) - cy
            r_front = half_w * math.sqrt(max(0.0, 1 - (dy / ry) ** 2))
            phi = math.asin(max(-1.0, min(1.0, x_off / r_front))) if r_front else 0.0
            r_view = rx * math.sqrt(max(0.0, 1 - (dy / ry) ** 2))
            return (
                cx + r_view * math.sin(phi + yaw),
                math.cos(phi + yaw),
                math.cos(phi + yaw) > 0.18,
            )

    features = []
    eyes, mouth, blush = char["eyes"], char["mouth"], char["blush"]
    eye_h = eyes["height"] * h
    eye_w = eye_h * eyes["width_ratio"]
    eye_y = base - eyes["center_height"] * h
    if face_visible:
        for side in (-1, 1):
            off = side * eyes["spacing"] * h / 2
            if body["shape"] == "cube":
                ex, squeeze, visible = face_cx + off * k, k, True
            else:
                ex, squeeze, visible = place(off, eyes["center_height"])
            if not visible:
                continue
            boff = side * blush["spacing"] * h / 2
            bx, bk, bvis = (
                (face_cx + boff * k, k, True)
                if body["shape"] == "cube"
                else place(boff, blush["center_height"])
            )
            opacity = blush_opacity(char, emotion["blush"])
            if bvis and opacity > 0.01:
                features.append(
                    f'<ellipse cx="{f(bx)}" cy="{f(base - blush["center_height"] * h)}" rx="{f(blush["size"] * h / 2 * bk)}" '
                    f'ry="{f(blush["size"] * blush["aspect"] * h / 2)}" fill="{pal.hex(blush["color"])}" opacity="{opacity:.2f}"/>'
                )
            features.append(
                draw_eye(
                    emotion["eyes"],
                    ex,
                    eye_y,
                    eye_w,
                    eye_h,
                    side,
                    squeeze,
                    pal,
                    eyes["highlights"],
                    f"{uid}{side}",
                )
            )
            if char["brow"]["kind"] == "lid_line":
                shape = char["brow"]["shapes"][emotion["brow"]]
                features.append(
                    draw_lid_line(
                        shape,
                        ex,
                        eye_y,
                        eye_w,
                        eye_h,
                        side,
                        squeeze,
                        pal,
                        char["brow"]["thickness"] * h,
                    )
                )
        if body["shape"] == "cube":
            mx, mk, mvis = face_cx, k, True
        else:
            mx, mk, mvis = place(0.0, mouth["center_height"])
        if mvis:
            features.append(
                draw_mouth(
                    emotion["mouth"],
                    mx,
                    base - mouth["center_height"] * h,
                    mouth["width"] * h,
                    mouth["line_width"] * h,
                    mk,
                    pal,
                )
            )
    out += features

    if char["brow"]["kind"] == "steam_wisp":
        shape = char["brow"]["shapes"][emotion["brow"]]
        top = base - h - char["brow"].get("float_gap", 0.05) * h
        out.append(
            draw_steam(
                shape, cx, top, char["brow"]["height"] * h, char["brow"]["thickness"] * h, pal
            )
        )

    out.append(draw_emanata(emotion["emanata"], cx, base, h * body["width"], h, pal))

    transform = (
        f"translate({f(cx)} {f(base - pose['offset_z'] * h)}) rotate({f(pose['tilt_deg'])}) "
        f"scale({f(pose['scale_xy'])} {f(pose['scale_z'])}) translate({f(-cx)} {f(-base)})"
    )
    # The floor shadow stays on the floor: it is not tilted or squashed with the pose.
    shadow = out.pop(shadow_index)
    return shadow + f'<g id="{key}-{uid}" transform="{transform}">' + "".join(out) + "</g>"


# --- sheets --------------------------------------------------------------------------------


def svg_document(width, height, background, body) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="{width}" height="{height}" fill="{background}"/>{body}</svg>'
    )


def footnote(width, y, pal) -> str:
    return text(
        width / 2,
        y,
        "Schematic 2D reference drawn from brand/*.json by `python cc.py brand-sheets`. "
        "The 3D model (Phase 2) is the source of truth.",
        20,
        mix(pal.hex("eye"), "#ffffff", 0.35),
        400,
        "middle",
    )


def character_sheet(data: dict, pal: Palette) -> str:
    width, height = 2400, 1500
    chars = data["character"]["characters"]
    ink = pal.hex("eye")
    base, px_per_m = 960, 540
    body = [text(80, 110, "Chuski & Shakkar · character sheet", 64, ink, 800)]
    body.append(
        f'<rect x="60" y="170" width="1200" height="900" rx="40" fill="{pal.hex("monsoon")}"/>'
    )
    body.append(
        f'<line x1="60" y1="{base}" x2="1260" y2="{base}" stroke="{ink}" stroke-opacity="0.25" stroke-width="3"/>'
    )
    positions = {"chuski": 450, "shakkar": 1000}
    for key, cx in positions.items():
        char = chars[key]
        h = char["height_m"] * px_per_m
        half = h * char["body"]["width"] / 2 + 30
        # proportion guides behind the character: middle of the face, and the eye line
        for frac, color in ((0.5, ink), (char["eyes"]["center_height"], pal.hex("cardamom"))):
            y = base - frac * h
            body.append(
                f'<line x1="{f(cx - half)}" y1="{f(y)}" x2="{f(cx + half)}" y2="{f(y)}" stroke="{color}" '
                f'stroke-opacity="0.6" stroke-dasharray="12 9" stroke-width="3"/>'
            )
        body.append(draw_character(key, char, pal, cx, base, px_per_m, uid=f"sheet{key}"))
        body.append(
            text(
                cx,
                base + 55,
                f"{char['name']} · {char['height_m']:.2f} m tall",
                32,
                ink,
                800,
                "middle",
            )
        )
    legend_y = 1048
    body.append(
        f'<line x1="100" y1="{legend_y}" x2="150" y2="{legend_y}" stroke="{ink}" stroke-opacity="0.6" stroke-dasharray="12 9" stroke-width="3"/>'
        + text(160, legend_y + 7, "middle of the face", 22, ink)
        + f'<line x1="380" y1="{legend_y}" x2="430" y2="{legend_y}" stroke="{pal.hex("cardamom")}" stroke-dasharray="12 9" stroke-width="3"/>'
        + text(
            440,
            legend_y + 7,
            "eye line: Chuski's eyes sit below the middle (baby schema, guide §2)",
            22,
            ink,
        )
    )
    y = 230
    for key in positions:
        char = chars[key]
        body.append(
            text(1330, y, f"{char['name']} ({char.get('pronunciation', '')})", 46, ink, 800)
        )
        body.append(text(1330, y + 48, char["species"], 24, ink))
        body.append(
            text(
                1330,
                y + 92,
                " · ".join(char["personality"]),
                34,
                mix(pal.hex("cardamom"), ink, 0.25),
                800,
            )
        )
        cursor = y + 135
        for label, value in (
            ("Flaw", char["flaw"]),
            ("Signature move", char["signature_move"]),
            (
                "Sound",
                f"{char['signature_sound']} · voice +{char['voice']['pitch_semitones']} semitones",
            ),
        ):
            block, cursor = paragraph(1330, cursor, f"{label}: {value}", 23, ink, 78)
            body.append(block)
            cursor += 8
        y = cursor + 50
    swatch_y = 1150
    body.append(text(80, swatch_y - 20, "Palette", 36, ink, 800))
    for i, (name, color) in enumerate(pal.colors.items()):
        x = 80 + (i % 7) * 320
        yy = swatch_y + (i // 7) * 120
        body.append(
            f'<rect x="{x}" y="{yy}" width="90" height="90" rx="18" fill="{color["hex"]}" '
            f'fill-opacity="{color.get("alpha", 1.0)}" stroke="{ink}" stroke-opacity="0.2" stroke-width="2"/>'
        )
        body.append(text(x + 105, yy + 40, name, 26, ink, 800))
        body.append(text(x + 105, yy + 72, color["hex"], 22, ink))
    body.append(footnote(width, height - 30, pal))
    return svg_document(width, height, "#ffffff", "".join(body))


def turnaround(data: dict, pal: Palette) -> str:
    width, height = 2400, 1260
    chars = data["character"]["characters"]
    ink = pal.hex("eye")
    body = [text(80, 100, "Turnaround · front · three-quarter · side · back", 56, ink, 800)]
    views = ((0, "front"), (45, "three-quarter"), (90, "side"), (180, "back"))
    # Sized so the tallest part (Chuski's steam, about 1.45x its height) fits inside the panel.
    for row, (key, px_per_m) in enumerate((("chuski", 290), ("shakkar", 520))):
        base = 560 + row * 560
        body.append(
            f'<rect x="60" y="{base - 450}" width="{width - 120}" height="510" rx="36" fill="{pal.hex("monsoon")}"/>'
        )
        for col, (yaw, label) in enumerate(views):
            cx = 360 + col * 560
            body.append(
                draw_character(
                    key, chars[key], pal, cx, base - 20, px_per_m, yaw_deg=yaw, uid=f"t{key}{col}"
                )
            )
            body.append(text(cx, base + 40, label, 26, ink, 400, "middle"))
        body.append(text(90, base - 400, chars[key]["name"], 40, ink, 800))
    body.append(footnote(width, height - 24, pal))
    return svg_document(width, height, "#ffffff", "".join(body))


def expression_sheet(data: dict, pal: Palette) -> str:
    emotions = data["emotions"]["emotions"]
    chars = data["character"]["characters"]
    ink = pal.hex("eye")
    cell_w, cell_h = 290, 420
    width = 80 + cell_w * len(emotions)
    height = 140 + cell_h * len(chars) + 60
    body = [text(40, 90, "Expressions (brand/emotions.json)", 56, ink, 800)]
    for row, (key, char) in enumerate(chars.items()):
        # fit each character's width (not height) into the cell, leaving room for emanata
        px_per_m = (cell_w * 0.66) / (char["body"]["width"] * char["height_m"])
        top = 140 + row * cell_h
        for col, emotion in enumerate(emotions):
            x = 40 + col * cell_w
            body.append(
                f'<rect x="{x + 6}" y="{top}" width="{cell_w - 12}" height="{cell_h - 20}" rx="28" fill="{pal.hex("monsoon")}"/>'
            )
            body.append(
                draw_character(
                    key,
                    char,
                    pal,
                    x + cell_w / 2,
                    top + cell_h - 90,
                    px_per_m,
                    emotion=emotion,
                    uid=f"e{key}{col}",
                )
            )
            body.append(
                text(
                    x + cell_w / 2,
                    top + cell_h - 40,
                    emotion["name"].replace("_", " "),
                    26,
                    ink,
                    800,
                    "middle",
                )
            )
    body.append(footnote(width, height - 20, pal))
    return svg_document(width, height, "#ffffff", "".join(body))


def thumbnail_test(data: dict, pal: Palette) -> str:
    """Each face drawn into a 96x170 cell, at the size it appears in a phone grid."""
    tw, th = THUMB_SIZE
    chars = data["character"]["characters"]
    picks = ["neutral", "happy", "shocked", "dramatic_sad", "in_love", "grumpy"]
    cells = []
    for row, (key, char) in enumerate(chars.items()):
        for col, name in enumerate(picks):
            emotion = emotion_by_name(data, name)
            x, y = col * tw, row * th
            px_per_m = (tw * 0.62) / char["height_m"]
            cells.append(
                f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" fill="{pal.hex("monsoon")}" stroke="#ffffff" stroke-width="2"/>'
            )
            cells.append(
                draw_character(
                    key,
                    char,
                    pal,
                    x + tw / 2,
                    y + th * 0.78,
                    px_per_m,
                    emotion=emotion,
                    uid=f"th{key}{col}",
                )
            )
    return svg_document(tw * len(picks), th * len(chars), "#ffffff", "".join(cells))


SHEETS = {
    "character_sheet": character_sheet,
    "turnaround": turnaround,
    "expressions": expression_sheet,
    "thumbnail_test": thumbnail_test,
}


def render_png(svg: str) -> bytes:
    import resvg_py  # only needed when actually rasterising

    png = resvg_py.svg_to_bytes(
        svg_string=svg, font_files=[str(FONT_FILE)], skip_system_fonts=True, font_family="Baloo 2"
    )
    return bytes(png)


def build_all(out_dir: Path = OUT_DIR, write_svg: bool = False) -> list[Path]:
    data = brand.load_all()
    pal = Palette(data["palette"])
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, make in SHEETS.items():
        svg = make(data, pal)
        png_path = out_dir / f"{name}.png"
        png_path.write_bytes(render_png(svg))
        written.append(png_path)
        if write_svg:
            svg_path = out_dir / f"{name}.svg"
            svg_path.write_text(svg, encoding="utf-8")
            written.append(svg_path)
    return written


def main(write_svg: bool = False) -> int:
    report = brand.validate()
    if not report.ok:
        print("brand/*.json has problems; run `python cc.py validate` first")
        return 1
    for path in build_all(write_svg=write_svg):
        print(f"wrote {path.relative_to(REPO_ROOT)}  ({path.stat().st_size // 1024} KB)")
    return 0
