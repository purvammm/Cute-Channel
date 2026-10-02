"""`python cc.py doctor`: is this machine ready to make episodes?

It checks Python, Blender, ffmpeg, rendering and secrets, and says how to fix each problem. It
uses only the standard library, so it works even before `pip install`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform as _platform
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import render_probe, tools
from .credentials import groups
from .env import load_env_file, load_versions, merged_settings
from .paths import ENV_FILE, REPO_ROOT

OK, WARN, FAIL, INFO = "ok", "warn", "fail", "info"
EMOJI = {OK: "✅", WARN: "⚠️ ", FAIL: "❌", INFO: "ℹ️ "}
ASCII = {OK: "[ok]  ", WARN: "[warn]", FAIL: "[FAIL]", INFO: "[info]"}
MIN_PYTHON = (3, 10)
MIN_FREE_GB = 5  # one episode's PNG frames plus temp files fit comfortably


@dataclass
class Check:
    area: str
    status: str
    summary: str
    fix: str | None = None
    details: dict = field(default_factory=dict)


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# --- individual checks ---------------------------------------------------------------------


def check_python(version_info: tuple | None = None) -> Check:
    version_info = tuple(sys.version_info) if version_info is None else version_info
    found = ".".join(str(part) for part in version_info[:3])
    if tuple(version_info[:2]) >= MIN_PYTHON:
        return Check("Python", OK, found, details={"executable": sys.executable})
    return Check(
        "Python",
        FAIL,
        f"{found} is too old (need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)",
        fix="Install Python 3.11+ (python.org), then run `python3.11 cc.py doctor`.",
    )


def check_packages(find_spec: Callable = importlib.util.find_spec) -> Check:
    needed = {"yaml": "PyYAML", "jsonschema": "jsonschema"}
    missing = [package for module, package in needed.items() if find_spec(module) is None]
    if not missing:
        return Check("Python packages", OK, ", ".join(needed.values()))
    return Check(
        "Python packages",
        WARN,
        "missing: " + ", ".join(missing),
        fix="python -m pip install -r requirements.txt   (or: bash scripts/setup_env.sh)",
    )


def check_machine(system: str, machine: str) -> Check:
    summary = f"{system} {machine}"
    if system == "Darwin" and machine == "x86_64":
        return Check(
            "Machine",
            INFO,
            summary + " (Intel Mac: Blender 5.x does not support it, so the pipeline uses 4.5 LTS)",
        )
    return Check("Machine", INFO, summary)


def check_blender(
    tool: tools.Tool | None,
    version: tools.BlenderVersion | None,
    versions: Mapping[str, str],
    *,
    intel_mac: bool = False,
) -> Check:
    pinned = versions.get("BLENDER_VERSION", "?")
    series = versions.get("BLENDER_SERIES", "?")
    if intel_mac:
        pinned = versions.get("BLENDER_INTEL_MAC_VERSION", pinned)
        series = versions.get("BLENDER_INTEL_MAC_SERIES", series)
    if tool is None or version is None:
        return Check(
            "Blender",
            FAIL,
            "not found",
            fix=(
                f"Install Blender {pinned} LTS from https://www.blender.org/download/ "
                "(on Linux/macOS `bash scripts/setup_env.sh` does it), "
                "or put its path in .env as CC_BLENDER=..."
            ),
        )
    where = _display_path(tool.path)
    details = {"path": str(tool.path), "version": str(version), "pinned": pinned}
    if version.series == series:
        note = (
            "" if str(version).startswith(pinned) else f"; pinned {pinned} (LTS updates are safe)"
        )
        return Check("Blender", OK, f"{version}  ({where}){note}", details=details)
    return Check(
        "Blender",
        WARN,
        f"{version} found ({where}), but the pipeline is pinned to {series} LTS",
        fix=f"Install Blender {pinned} LTS; other versions may break the scripts.",
        details=details,
    )


def _ffmpeg_fix(system: str) -> str:
    if system == "Darwin":
        return "brew install ffmpeg   (Homebrew: https://brew.sh)"
    if system == "Windows":
        return "winget install Gyan.FFmpeg   (then open a new terminal)"
    return "sudo apt-get install ffmpeg   (or: bash scripts/setup_env.sh)"


def check_ffmpeg(tool: tools.Tool | None, features: Mapping[str, bool], system: str) -> Check:
    if tool is None:
        return Check("ffmpeg", FAIL, "not found", fix=_ffmpeg_fix(system))
    missing = [f for f, ok in features.items() if not ok]
    required_missing = [f for f in missing if f not in tools.OPTIONAL_FFMPEG_FEATURES]
    details = {"path": str(tool.path), "features": dict(features)}
    summary = f"{tool.version}  ({_display_path(tool.path)})"
    if required_missing:
        needs = ", ".join(
            f"{f} (Phase {tools.FFMPEG_FEATURES[f][2]}: {tools.FFMPEG_FEATURES[f][3]})"
            for f in required_missing
        )
        return Check(
            "ffmpeg",
            WARN,
            f"{summary}; missing {needs}",
            fix="Install a full ffmpeg build: " + _ffmpeg_fix(system),
            details=details,
        )
    if missing:
        summary += "; optional missing: " + ", ".join(missing)
    return Check("ffmpeg", OK, summary, details=details)


def check_ffprobe(tool: tools.Tool | None, system: str) -> Check:
    if tool is None:
        return Check("ffprobe", FAIL, "not found (it ships with ffmpeg)", fix=_ffmpeg_fix(system))
    return Check("ffprobe", OK, f"{tool.version}  ({_display_path(tool.path)})")


def check_render(capabilities: Mapping | None, blender: tools.Tool | None) -> Check:
    if capabilities is None:
        if blender is None:
            return Check("Rendering", INFO, "not tested (Blender not found)")
        return Check(
            "Rendering",
            INFO,
            "not tested yet",
            fix="python cc.py doctor --deep   (renders a tiny scene with each engine, 1-5 min)",
        )
    results = render_probe.results_from_capabilities(capabilities)
    rows = {
        r.label: (f"{r.seconds_per_frame:.2f} s/frame" if r.usable else f"failed: {r.error}")
        for r in results
    }
    tested_with = (capabilities.get("blender") or {}).get("version")
    details = {"probes": rows, "tested_with": tested_with}
    preview = render_probe.choose_engine(results, "preview")
    final = render_probe.choose_engine(results, "final")
    if preview is None or final is None:
        return Check(
            "Rendering",
            FAIL,
            "no render engine works on this machine",
            fix="Read the probe errors (cc.py doctor --format json); docs/RENDER_ENVIRONMENT.md",
            details=details,
        )
    summary = f"preview: {preview.label} · final: {final.label}"
    stale = blender is not None and tested_with and tested_with != blender.version
    if stale:
        return Check(
            "Rendering",
            WARN,
            summary + f" (tested with Blender {tested_with})",
            fix="Blender changed since the test; re-run python cc.py doctor --deep",
            details=details,
        )
    if final.warning:
        return Check(
            "Rendering", WARN, summary, fix=f"Final renders: {final.warning}", details=details
        )
    return Check("Rendering", OK, summary, details=details)


def check_secrets(environ: Mapping[str, str], env_file: Mapping[str, str]) -> list[Check]:
    """One line per integration: how many values are set, and where from. Never the values."""
    checks = []
    for group, credentials in groups().items():
        found = {}
        for credential in credentials:
            if environ.get(credential.key):
                found[credential.key] = "environment"
            elif env_file.get(credential.key):
                found[credential.key] = ".env"
        total = len(credentials)
        phase = min(c.phase for c in credentials)
        optional = all(c.optional for c in credentials)
        details = {"set": found, "missing": [c.key for c in credentials if c.key not in found]}
        if not found:
            when = "optional, only if you opt in" if optional else f"needed from Phase {phase}"
            checks.append(Check(group, INFO, f"0/{total} set ({when})", details=details))
        elif len(found) < total:
            checks.append(
                Check(
                    group,
                    WARN,
                    f"{len(found)}/{total} set; missing {', '.join(details['missing'])}",
                    fix="Add the missing values (docs/SETUP_SECRETS.md)",
                    details=details,
                )
            )
        else:
            checks.append(Check(group, OK, f"{total}/{total} set", details=details))
    return checks


def git_tracks(relative_path: str, cwd: Path = REPO_ROOT) -> bool:
    """True if git is tracking the file, e.g. a `.env` that was committed by accident."""
    try:
        proc = subprocess.run(
            ["git", "ls-files", "--error-unmatch", relative_path],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def check_secrets_file(exists: bool, tracked: bool) -> Check:
    if tracked:
        return Check(
            "Secrets file",
            FAIL,
            ".env is committed to git, so your tokens may be public",
            fix="git rm --cached .env, commit, then ROTATE every token that was in it",
        )
    if not exists:
        return Check("Secrets file", INFO, "no .env yet (copy .env.example when Phase 9 needs it)")
    return Check("Secrets file", OK, ".env present and gitignored")


def check_disk(path: Path = REPO_ROOT, minimum_gb: float = MIN_FREE_GB) -> Check:
    free_gb = shutil.disk_usage(path).free / 1e9
    if free_gb < minimum_gb:
        return Check(
            "Disk space",
            WARN,
            f"{free_gb:.1f} GB free",
            fix=f"Free at least {minimum_gb} GB; rendered frames are big",
        )
    return Check("Disk space", OK, f"{free_gb:.0f} GB free")


# --- the whole run -------------------------------------------------------------------------


def run_doctor(
    *,
    deep: bool = False,
    environ: Mapping[str, str] | None = None,
    progress: Callable[[str], None] | None = None,
) -> list[Check]:
    environ = os.environ if environ is None else environ
    env_file = load_env_file()
    settings = merged_settings(environ, env_file)
    versions = load_versions()
    system, machine = _platform.system(), _platform.machine()

    checks = [check_python(), check_packages(), check_machine(system, machine)]

    blender, blender_version = tools.find_blender(tools.blender_candidates(environ=settings))
    intel_mac = system == "Darwin" and machine == "x86_64"
    checks.append(check_blender(blender, blender_version, versions, intel_mac=intel_mac))

    ffmpeg = tools.find_ffmpeg_tool("ffmpeg", tools.ffmpeg_candidates("ffmpeg", environ=settings))
    features = tools.ffmpeg_features(ffmpeg.path) if ffmpeg else {}
    checks.append(check_ffmpeg(ffmpeg, features, system))
    ffprobe = tools.find_ffmpeg_tool(
        "ffprobe", tools.ffmpeg_candidates("ffprobe", environ=settings)
    )
    checks.append(check_ffprobe(ffprobe, system))

    if deep and blender is not None:
        results = []
        for probe in render_probe.default_probes():
            if progress:
                progress(f"rendering the test scene with {probe.label} ...")
            results.append(render_probe.run_probe(blender.path, probe))
        render_probe.save_capabilities(results, blender.path, blender.version)
    checks.append(check_render(render_probe.load_capabilities(), blender))

    checks.extend(check_secrets(environ, env_file))
    checks.append(check_secrets_file(ENV_FILE.exists(), git_tracks(".env")))
    checks.append(check_disk())
    return checks


def exit_code(checks: list[Check]) -> int:
    return 1 if any(c.status == FAIL for c in checks) else 0


def summary_counts(checks: list[Check]) -> dict[str, int]:
    return {status: sum(c.status == status for c in checks) for status in (OK, WARN, FAIL, INFO)}


# --- output formats ------------------------------------------------------------------------


def _icons(stream) -> dict[str, str]:
    encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
    return EMOJI if encoding == "utf8" else ASCII


def format_text(checks: list[Check], icons: Mapping[str, str] = EMOJI) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"Cute Channel doctor · {stamp}", ""]
    for check in checks:
        lines.append(f"{icons[check.status]} {check.area:<28} {check.summary}")
        if check.fix and check.status != OK:
            lines.append(f"{'':5}{'':<28} fix: {check.fix}")
    lines += ["", "Summary: " + _summary_line(summary_counts(checks))]
    return "\n".join(lines)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def _summary_line(counts: Mapping[str, int]) -> str:
    return (
        f"{counts[OK]} ok · {_plural(counts[WARN], 'warning')} · {_plural(counts[FAIL], 'problem')}"
    )


def format_markdown(checks: list[Check]) -> str:
    rows = ["| | Check | Result | How to fix |", "|---|---|---|---|"]
    for check in checks:
        fix = check.fix if check.fix and check.status != OK else ""
        cells = [EMOJI[check.status].strip(), check.area, check.summary, fix]
        rows.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    rows.append("")
    rows.append(f"**{_summary_line(summary_counts(checks))}**")
    return "### Cute Channel doctor\n\n" + "\n".join(rows)


def format_json(checks: list[Check]) -> str:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": {"system": _platform.system(), "machine": _platform.machine()},
        "checks": [asdict(c) for c in checks],
        "summary": summary_counts(checks),
        "exit_code": exit_code(checks),
    }
    return json.dumps(payload, indent=2, default=str)


def main(deep: bool = False, output_format: str = "text") -> int:
    progress = (
        (lambda message: print(f"  {message}", file=sys.stderr, flush=True)) if deep else None
    )
    checks = run_doctor(deep=deep, progress=progress)
    if output_format == "json":
        print(format_json(checks))
    elif output_format == "markdown":
        print(format_markdown(checks))
    else:
        print(format_text(checks, _icons(sys.stdout)))
    return exit_code(checks)
