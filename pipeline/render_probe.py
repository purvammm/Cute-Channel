"""Find out which Blender render engines work on this machine, then pick one automatically.

Why this exists: this sandbox and GitHub's free runners have no GPU. EEVEE (the guide's engine)
needs OpenGL or Vulkan. On a GPU-less Linux machine it can still run through Mesa's software
rasteriser (llvmpipe), just slowly. Cycles on the CPU works everywhere.

`python cc.py doctor --deep` renders a tiny test scene with each engine, records what works and
how fast, and saves the result in .cache/. The render step (Phase 5) calls `choose_engine()`, so
previews and final renders pick the best engine each machine actually has.
"""

from __future__ import annotations

import json
import platform as _platform
import subprocess
import sys
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path

from . import specs
from .paths import BLENDER_DIR, RENDER_CAPABILITIES_FILE, RENDER_PROBE_DIR

SMOKE_SCRIPT = BLENDER_DIR / "smoke_test.py"
PROBE_RESOLUTION = (270, 480)  # a quarter of 1080x1920 on each side (1/16 of the pixels)
PROBE_SAMPLES = 16
FINAL_SAMPLES = 64  # guide §13.1: EEVEE 32-64 samples
SOFTWARE_RENDERERS = ("llvmpipe", "softpipe", "lavapipe", "swiftshader", "microsoft basic render")
PREVIEW_EEVEE_SLOWDOWN_LIMIT = 3.0  # prefer EEVEE for previews unless it's 3x slower than Cycles


@dataclass(frozen=True)
class Probe:
    label: str
    engine: str  # generic name understood by blender/lib/compat.py: EEVEE, CYCLES, WORKBENCH
    gpu_backend: str | None = None


def default_probes(platform: str | None = None) -> list[Probe]:
    platform = sys.platform if platform is None else platform
    probes = [Probe("cycles-cpu", "CYCLES"), Probe("eevee", "EEVEE")]
    if platform.startswith("linux"):
        # GPU-less Linux (CI) may only have software Vulkan; worth knowing as a backup path.
        probes.append(Probe("eevee-vulkan", "EEVEE", "vulkan"))
    probes.append(Probe("workbench", "WORKBENCH"))
    return probes


@dataclass
class ProbeResult:
    label: str
    engine: str
    gpu_backend: str | None
    ok: bool
    engine_id: str | None = None
    seconds_per_frame: float | None = None
    first_frame_seconds: float | None = None
    resolution: list = field(default_factory=lambda: list(PROBE_RESOLUTION))
    samples: int = PROBE_SAMPLES
    gpu_renderer: str | None = None
    software_gl: bool | None = None
    looks_blank: bool | None = None
    images: list = field(default_factory=list)
    error: str | None = None

    @property
    def usable(self) -> bool:
        return self.ok and not self.looks_blank and self.seconds_per_frame is not None

    @classmethod
    def from_dict(cls, data: Mapping) -> ProbeResult:
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass(frozen=True)
class EngineChoice:
    label: str
    engine: str
    gpu_backend: str | None
    reason: str
    warning: str | None = None


def is_software_renderer(renderer: str | None) -> bool | None:
    if not renderer:
        return None
    lowered = renderer.lower()
    return any(name in lowered for name in SOFTWARE_RENDERERS)


def _tail(text: str, lines: int = 12, limit: int = 1200) -> str:
    kept = [line for line in text.splitlines() if line.strip()][-lines:]
    return "\n".join(kept)[-limit:]


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def probe_command(
    blender: Path,
    probe: Probe,
    out_dir: Path,
    result_file: Path,
    frames: int = 2,
    resolution: tuple = PROBE_RESOLUTION,
    samples: int = PROBE_SAMPLES,
) -> list[str]:
    cmd = [str(blender), "-b", "--factory-startup", "-noaudio"]
    if probe.gpu_backend:
        cmd += ["--gpu-backend", probe.gpu_backend]
    cmd += ["--python-exit-code", "1", "--python", str(SMOKE_SCRIPT), "--"]
    cmd += ["--engine", probe.engine, "--label", probe.label]
    cmd += ["--out", str(out_dir), "--result", str(result_file)]
    cmd += ["--frames", str(frames), "--resolution", f"{resolution[0]}x{resolution[1]}"]
    cmd += ["--samples", str(samples)]
    return cmd


def run_probe(
    blender: Path,
    probe: Probe,
    *,
    out_root: Path = RENDER_PROBE_DIR,
    frames: int = 2,
    resolution: tuple = PROBE_RESOLUTION,
    samples: int = PROBE_SAMPLES,
    timeout: float = 900,
) -> ProbeResult:
    """Render the smoke-test scene with one engine in a fresh Blender process."""
    out_dir = out_root / probe.label
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.iterdir():  # stale images from an earlier run must not fake a pass
        if old.is_file():
            old.unlink()
    result_file = out_dir / "result.json"
    cmd = probe_command(blender, probe, out_dir, result_file, frames, resolution, samples)
    result = ProbeResult(
        probe.label,
        probe.engine,
        probe.gpu_backend,
        ok=False,
        resolution=list(resolution),
        samples=samples,
    )
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, errors="replace", timeout=timeout
        )
    except subprocess.TimeoutExpired:
        result.error = f"timed out after {timeout:.0f} s"
        return result
    except OSError as exc:
        result.error = f"could not start Blender: {exc}"
        return result

    data = _read_json(result_file)
    if not data or not data.get("ok"):
        output = _tail((proc.stdout or "") + (proc.stderr or ""))
        result.error = (data or {}).get("error") or output or f"exit code {proc.returncode}"
        return result

    renderer = (data.get("gpu") or {}).get("renderer")
    result.ok = True
    result.engine_id = data.get("engine_id")
    result.seconds_per_frame = data.get("seconds_per_frame")
    result.first_frame_seconds = (data.get("frame_seconds") or [None])[0]
    result.gpu_renderer = renderer
    result.software_gl = is_software_renderer(renderer)
    result.looks_blank = (data.get("image_check") or {}).get("looks_blank")
    result.images = data.get("images", [])
    return result


# How render time grows with pixel count, as an exponent: time ~ samples x pixels**k.
# Calibrated on 2 Oct 2026 in the sandbox (8 vCPU, no GPU) by rendering the smoke scene at
# 270x480/16 samples and at 1080x1920/64 samples:
#   Cycles CPU:              0.59 s -> 36.3 s per frame (k = 1.0, linear)
#   EEVEE on llvmpipe (CPU): 5.77 s -> 70.6 s per frame (k = 0.4; per-sample overhead dominates)
PIXEL_SCALING_EXPONENT = {"CYCLES": 1.0, "EEVEE": 0.4, "WORKBENCH": 1.0}


def estimate_reel_minutes(result: ProbeResult, seconds: float = 10.0) -> float | None:
    """Rough time for a full-quality Reel (1080x1920, FINAL_SAMPLES), scaled from the probe.

    The scaling exponents were measured on one machine, so treat the answer as "about".
    """
    if not result.usable:
        return None
    width, height = result.resolution
    pixel_ratio = (specs.WIDTH * specs.HEIGHT) / (width * height)
    exponent = PIXEL_SCALING_EXPONENT.get(result.engine.upper(), 1.0)
    samples_ratio = FINAL_SAMPLES / result.samples if result.engine.upper() != "WORKBENCH" else 1.0
    frames = specs.seconds_to_frames(seconds)
    return result.seconds_per_frame * pixel_ratio**exponent * samples_ratio * frames / 60.0


def _fastest(results: Iterable[ProbeResult]) -> list[ProbeResult]:
    return sorted(results, key=lambda r: r.seconds_per_frame)


def choose_engine(
    results: Iterable[ProbeResult], purpose: str = "preview", require_eevee: bool = False
) -> EngineChoice | None:
    """Pick the best working engine for a 'preview' (fast check) or a 'final' render.

    Set `require_eevee` when the look uses EEVEE-only shading (the toon "Shader to RGB" setup
    from guide §9.2); then Cycles and Workbench are never picked.
    """
    usable = [r for r in results if r.usable]
    eevee = _fastest(r for r in usable if r.engine.upper() == "EEVEE")
    eevee_gpu = [r for r in eevee if r.software_gl is False]
    cycles = [] if require_eevee else _fastest(r for r in usable if r.engine.upper() == "CYCLES")
    workbench = (
        [] if require_eevee else _fastest(r for r in usable if r.engine.upper() == "WORKBENCH")
    )

    def pick(r: ProbeResult, reason: str, warning: str | None = None) -> EngineChoice:
        return EngineChoice(r.label, r.engine, r.gpu_backend, reason, warning)

    if purpose == "final":
        if eevee_gpu:
            return pick(
                eevee_gpu[0], "EEVEE on a real GPU, the engine the guide's look is built for"
            )
        if eevee:
            minutes = estimate_reel_minutes(eevee[0])
            return pick(
                eevee[0],
                "EEVEE through software OpenGL/Vulkan (no GPU found)",
                f"slow: roughly {minutes:.0f} min for a 10 s Reel at full quality; "
                "render overnight, or on a machine with a GPU",
            )
        if cycles:
            return pick(
                cycles[0],
                "Cycles on the CPU (EEVEE is unavailable here)",
                "the look differs a little from EEVEE and full-quality renders are slow",
            )
        return None

    if eevee and (
        not cycles
        or eevee[0].seconds_per_frame <= PREVIEW_EEVEE_SLOWDOWN_LIMIT * cycles[0].seconds_per_frame
    ):
        return pick(eevee[0], "EEVEE: matches the final look")
    if cycles:
        return pick(
            cycles[0], "Cycles on the CPU: the fastest engine here that looks like the final"
        )
    if workbench:
        return pick(
            workbench[0],
            "Workbench only",
            "flat grey shading: fine for checking timing, not the look",
        )
    return None


def save_capabilities(
    results: Iterable[ProbeResult],
    blender_path: Path,
    blender_version: str,
    path: Path = RENDER_CAPABILITIES_FILE,
) -> dict:
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine": {"system": _platform.system(), "machine": _platform.machine()},
        "blender": {"path": str(blender_path), "version": blender_version},
        "results": [asdict(r) for r in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def load_capabilities(path: Path = RENDER_CAPABILITIES_FILE) -> dict | None:
    return _read_json(path)


def results_from_capabilities(data: Mapping | None) -> list[ProbeResult]:
    return [ProbeResult.from_dict(r) for r in (data or {}).get("results", [])]
