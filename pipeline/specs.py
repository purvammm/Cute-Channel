"""Platform specs and craft rules from docs/guide.html, encoded once.

Each constant cites its id in docs/GUIDE_DIGEST.md (G##) and the guide section (§). When a
platform or the guide changes, update the digest and this file together. This module is pure
Python with no dependencies, so Blender's bundled Python can import it too.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# --- G01-G03 · Output (§11.3, §12.1, §15.2) -----------------------------------------------
WIDTH = 1080
HEIGHT = 1920
FPS = 30
VIDEO_CODEC = "h264"
AUDIO_CODEC = "aac"
VIDEO_BITRATE_MBPS = (10, 16)
DURATION_S = (5, 20)  # QA window. The gag structure itself aims for 5-15 s (G40).

# --- G06 · Captions (§18.2; 5-hashtag cap verified 2 Oct 2026) ----------------------------
MAX_HASHTAGS = 5

# --- G10-G12 · Safe zones and on-screen text (§12.2, §15.1) -------------------------------
SAFE_TOP = 0.14  # username, tabs
SAFE_BOTTOM = 0.35  # caption, audio, profile
SAFE_SIDE = 0.06
TEXT_WORDS_PER_SECOND = 3  # guide: "about 1 s per 3-4 words"; 3 is the safe end


@dataclass(frozen=True)
class Rect:
    """Pixel rectangle with the origin at the top-left corner, like image coordinates."""

    x0: int
    y0: int
    x1: int
    y1: int

    def contains(self, other: Rect) -> bool:
        return (
            self.x0 <= other.x0
            and self.y0 <= other.y0
            and other.x1 <= self.x1
            and other.y1 <= self.y1
        )

    def overlaps(self, other: Rect) -> bool:
        return (
            self.x0 < other.x1 and other.x0 < self.x1 and self.y0 < other.y1 and other.y0 < self.y1
        )


def safe_rect(width: int = WIDTH, height: int = HEIGHT) -> Rect:
    """Where faces and text must stay. At 1080x1920 this is Rect(65, 269, 1015, 1248)."""
    side = round(width * SAFE_SIDE)
    return Rect(side, round(height * SAFE_TOP), width - side, height - round(height * SAFE_BOTTOM))


def button_column_rect(width: int = WIDTH, height: int = HEIGHT) -> Rect:
    """The like/comment/share buttons (G11). Faces must avoid it; keep them centred or a bit left.

    The size is read off the guide's diagram, so treat it as approximate.
    """
    side = round(width * SAFE_SIDE)
    return Rect(
        round(width * 0.82), round(height * 0.47), width - side, height - round(height * SAFE_BOTTOM)
    )


def text_hold_seconds(n_words: int) -> float:
    """Minimum time a caption stays on screen (G12). Never less than one second."""
    return max(1.0, n_words / TEXT_WORDS_PER_SECOND)


# --- G13-G17 · Sound (§14.3, §15.1, §15.2) -------------------------------------------------
SFX_OFFSET_FRAMES = (0, 1)  # on the impact frame or one frame after, never before
LOUDNESS_LUFS = -14.0  # integrated; a common short-form target, not a platform rule
TRUE_PEAK_DBTP = -1.0
VOICE_PITCH_SEMITONES = (4, 8)  # choose ONE value per character and keep it forever
VOICE_TEMPO_PERCENT = (5, 10)

# --- G21 · Timing cheat sheet at 30 fps (§11.6) --------------------------------------------
BLINK_FRAMES = (5, 7)
HEAD_TURN_FRAMES = (6, 10)
HEAD_TURN_SETTLE_FRAMES = 4
MIN_HOLD_FRAMES = 15  # an expression must stay this long to be readable
SMALL_HOP_FRAMES = (20, 30)
TAKE_ANTICIPATION_FRAMES = 4
TAKE_TO_EXTREME_FRAMES = (2, 3)
TAKE_MIN_HOLD_FRAMES = 10
STEP_FRAMES = (4, 6)
WIGGLE_FRAMES_PER_DIRECTION = (2, 3)
SLOW_TIMING_MULTIPLIER = 2.0  # sleepy or sad moves take double the frames
FOLLOW_THROUGH_FRAMES = (2, 4)  # G26: ears, hats and props lag the body


# --- G22 · The "jelly hop" key table (§11.4) -----------------------------------------------
@dataclass(frozen=True)
class HopKey:
    frame: int
    pose: str
    loc_z: float  # metres; scale to the character (a good hop is about one body-height)
    scale_xy: float
    scale_z: float


JELLY_HOP = (
    HopKey(1, "rest", 0.0, 1.00, 1.00),
    HopKey(6, "anticipation squash", 0.0, 1.18, 0.78),
    HopKey(9, "launch stretch", 0.3, 0.88, 1.18),
    HopKey(17, "top (hang time)", 1.2, 1.00, 1.00),
    HopKey(23, "falling stretch", 0.25, 0.90, 1.12),
    HopKey(25, "landing squash", 0.0, 1.22, 0.75),
    HopKey(29, "overshoot", 0.0, 0.96, 1.06),
    HopKey(33, "settle", 0.0, 1.00, 1.00),
    HopKey(45, "hold (same pose as frame 1)", 0.0, 1.00, 1.00),
)
JELLY_HOP_VECTOR_FRAMES = (6, 25)  # ground contacts get Vector handles: snappy take-off/impact
JELLY_HOP_BLINK = ((36, 1.0), (38, 0.1), (39, 0.1), (42, 1.0))  # eye Scale Z during the hold

# --- G27 · Emanata "pop" (§11.8) -----------------------------------------------------------
EMANATA_POP_KEYS = ((0, 0.0), (3, 1.25), (5, 1.0))  # (frame offset, scale)
EMANATA_FLOAT_FRAMES = 15
EMANATA_SHRINK_FRAMES = 3


# --- G23 · Frames and loops (§11.3, §11.5) -------------------------------------------------
def seconds_to_frames(seconds: float, fps: int = FPS) -> int:
    """A duration in frames, e.g. 8 s at 30 fps = 240. Rounds half up (not banker's rounding)."""
    return math.floor(seconds * fps + 0.5)


def frame_at(seconds: float, fps: int = FPS) -> int:
    """The Blender frame shown at a moment in time. Frames start at 1, so t = 0 s is frame 1."""
    return 1 + seconds_to_frames(seconds, fps)


def loop_end_frame(last_key_frame: int) -> int:
    """Loop rule: the last key repeats the first pose, so the scene ends one frame earlier."""
    return last_key_frame - 1
