"""Find and identify the external tools the pipeline drives: Blender and ffmpeg.

Search order, most explicit first:
  1. an override in your environment or `.env` (CC_BLENDER / CC_FFMPEG / CC_FFPROBE)
  2. portable copies in `.tools/` installed by scripts/setup_env.sh
  3. your PATH
  4. the standard install folders for your operating system
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .paths import TOOLS_DIR

_BLENDER_RE = re.compile(r"Blender\s+(\d+)\.(\d+)(?:\.(\d+))?(\s+LTS)?")
_FFMPEG_RE = re.compile(r"(?:ffmpeg|ffprobe) version (\S+)")

Runner = Callable[[Path, list], "str | None"]

# ffmpeg capabilities later phases rely on: feature -> (listing, item name, phase, why)
FFMPEG_FEATURES = {
    "libx264": ("encoders", "libx264", 7, "H.264 video, the Instagram/YouTube spec"),
    "aac": ("encoders", "aac", 7, "AAC audio"),
    "loudnorm": ("filters", "loudnorm", 6, "-14 LUFS loudness normalisation"),
    "ebur128": ("filters", "ebur128", 7, "loudness measurement for QA"),
    "subtitles": ("filters", "subtitles", 7, "burned-in captions (libass)"),
    "rubberband": ("filters", "rubberband", 6, "best voice pitch-shift (optional)"),
}
OPTIONAL_FFMPEG_FEATURES = {"rubberband"}  # Phase 6 can fall back to asetrate+atempo


@dataclass(frozen=True)
class BlenderVersion:
    major: int
    minor: int
    patch: int
    lts: bool

    @property
    def series(self) -> str:
        return f"{self.major}.{self.minor}"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}" + (" LTS" if self.lts else "")


@dataclass(frozen=True)
class Tool:
    """A tool that was found and answered `--version` correctly."""

    name: str
    path: Path
    version: str


def parse_blender_version(text: str | None) -> BlenderVersion | None:
    match = _BLENDER_RE.search(text or "")
    if not match:
        return None
    major, minor, patch, lts = match.groups()
    return BlenderVersion(int(major), int(minor), int(patch or 0), bool(lts))


def parse_ffmpeg_version(text: str | None) -> str | None:
    match = _FFMPEG_RE.search(text or "")
    return match.group(1) if match else None


def run_tool(path: Path, args: list, timeout: float = 60) -> str | None:
    """Run a tool and return its combined output, or None if it cannot run at all."""
    try:
        proc = subprocess.run(
            [str(path), *args], capture_output=True, text=True, errors="replace", timeout=timeout
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return (proc.stdout or "") + (proc.stderr or "")


def _version_key(path: Path) -> tuple[int, ...]:
    """Sort 'blender-5.10.0' after 'blender-5.2.2', which plain string sorting gets wrong."""
    for part in reversed(path.parts):
        numbers = re.findall(r"\d+", part)
        if numbers and part.lower().startswith(("blender", "ffmpeg")):
            return tuple(int(n) for n in numbers)
    return ()


def _unique(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result = []
    for path in paths:
        if str(path) not in seen:
            seen.add(str(path))
            result.append(path)
    return result


def _which(name: str, environ: Mapping[str, str]) -> Path | None:
    found = shutil.which(name, path=environ.get("PATH", ""))
    return Path(found) if found else None


def blender_candidates(
    environ: Mapping[str, str] | None = None,
    platform: str | None = None,
    tools_dir: Path = TOOLS_DIR,
    home: Path | None = None,
) -> list[Path]:
    """Every place Blender might be on this machine, most specific first."""
    environ = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    home = Path.home() if home is None else home
    paths: list[Path] = []
    if environ.get("CC_BLENDER"):
        paths.append(Path(environ["CC_BLENDER"]).expanduser())

    if platform == "darwin":
        pattern = "Blender-*.app/Contents/MacOS/Blender"
    elif platform.startswith("win"):
        pattern = "blender-*/blender.exe"
    else:
        pattern = "blender-*/blender"
    paths += sorted(tools_dir.glob(pattern), key=_version_key, reverse=True)

    on_path = _which("blender", environ)
    if on_path:
        paths.append(on_path)

    if platform == "darwin":
        paths.append(Path("/Applications/Blender.app/Contents/MacOS/Blender"))
        paths.append(home / "Applications/Blender.app/Contents/MacOS/Blender")
    elif platform.startswith("win"):
        program_files = Path(environ.get("ProgramFiles", r"C:\Program Files"))
        installs = (program_files / "Blender Foundation").glob("Blender*/blender.exe")
        paths += sorted(installs, key=_version_key, reverse=True)
    else:
        paths += [Path("/snap/bin/blender"), Path("/usr/bin/blender")]
    return _unique(paths)


def ffmpeg_candidates(
    name: str = "ffmpeg",
    environ: Mapping[str, str] | None = None,
    platform: str | None = None,
    tools_dir: Path = TOOLS_DIR,
) -> list[Path]:
    """Every place ffmpeg (or ffprobe) might be, most specific first."""
    environ = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    exe = f"{name}.exe" if platform.startswith("win") else name
    paths: list[Path] = []
    override = environ.get(f"CC_{name.upper()}")
    if override:
        paths.append(Path(override).expanduser())
    paths.append(tools_dir / "ffmpeg-static" / exe)
    on_path = _which(name, environ)
    if on_path:
        paths.append(on_path)
    if platform == "darwin":  # Homebrew on Apple Silicon, then Intel
        paths += [Path("/opt/homebrew/bin") / name, Path("/usr/local/bin") / name]
    return _unique(paths)


def find_blender(
    candidates: Iterable[Path] | None = None, runner: Runner = run_tool
) -> tuple[Tool | None, BlenderVersion | None]:
    """The first candidate that really is Blender (it must answer `--version`)."""
    for path in blender_candidates() if candidates is None else candidates:
        if not path.is_file():
            continue
        version = parse_blender_version(runner(path, ["--version"]))
        if version:
            return Tool("blender", path, str(version)), version
    return None, None


def find_ffmpeg_tool(
    name: str = "ffmpeg", candidates: Iterable[Path] | None = None, runner: Runner = run_tool
) -> Tool | None:
    for path in ffmpeg_candidates(name) if candidates is None else candidates:
        if not path.is_file():
            continue
        version = parse_ffmpeg_version(runner(path, ["-hide_banner", "-version"]))
        if version:
            return Tool(name, path, version)
    return None


def _listed_names(text: str | None) -> set[str]:
    """Names from `ffmpeg -encoders` / `-filters` output: the second column of each line."""
    names = set()
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            names.add(parts[1])
    return names


def ffmpeg_features(ffmpeg: Path, runner: Runner = run_tool) -> dict[str, bool]:
    """Which of FFMPEG_FEATURES this ffmpeg build supports."""
    listings = {
        kind: _listed_names(runner(ffmpeg, ["-hide_banner", f"-{kind}"]))
        for kind in ("encoders", "filters")
    }
    return {
        feature: item in listings[kind] for feature, (kind, item, _, _) in FFMPEG_FEATURES.items()
    }
