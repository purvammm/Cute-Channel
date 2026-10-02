import json
import subprocess
import sys

import cc
from pipeline.paths import REPO_ROOT


def run(*args):
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "cc.py"), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=180,
    )


def test_help_lists_every_command():
    proc = run("--help")
    assert proc.returncode == 0
    for name, _phase, _ in cc.PLANNED:
        assert name in proc.stdout
    assert "doctor" in proc.stdout


def test_planned_commands_say_which_phase_builds_them():
    proc = run("render", "E001", "--final")
    assert proc.returncode == 2
    assert "Phase 5" in proc.stderr


def test_no_command_prints_help():
    assert cc.main([]) == 0


def test_doctor_json_runs_on_any_machine():
    proc = run("doctor", "--format", "json")
    assert proc.returncode in (0, 1), proc.stderr  # 1 = something required is missing
    payload = json.loads(proc.stdout)
    areas = {check["area"] for check in payload["checks"]}
    assert {"Python", "Blender", "ffmpeg", "Rendering", "Instagram", "YouTube"} <= areas
    assert payload["exit_code"] == proc.returncode
