import os
import sys
from pathlib import Path

import pytest

from pipeline import tools

BLENDER_OUTPUT = "Blender 5.2.2 LTS\n\tbuild date: 2026-09-15\n\tbuild hash: d13f752e3b9c\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (BLENDER_OUTPUT, (5, 2, 2, True, "5.2")),
        ("Blender 4.5.14 LTS (hash x)", (4, 5, 14, True, "4.5")),
        ("Blender 5.1.0\n", (5, 1, 0, False, "5.1")),
        ("Blender 5.3", (5, 3, 0, False, "5.3")),
    ],
)
def test_parse_blender_version(text, expected):
    version = tools.parse_blender_version(text)
    assert (version.major, version.minor, version.patch, version.lts, version.series) == expected


def test_parse_blender_version_rejects_other_output():
    assert tools.parse_blender_version("command not found") is None
    assert tools.parse_blender_version(None) is None
    assert str(tools.parse_blender_version(BLENDER_OUTPUT)) == "5.2.2 LTS"


def test_parse_ffmpeg_version():
    assert tools.parse_ffmpeg_version("ffmpeg version 7.0.2-static https://x") == "7.0.2-static"
    assert tools.parse_ffmpeg_version("ffprobe version n7.1 Copyright") == "n7.1"
    assert tools.parse_ffmpeg_version("") is None


def test_blender_candidates_order(tmp_path):
    tools_dir = tmp_path / ".tools"
    for name in ("blender-5.2.2-linux-x64", "blender-5.10.0-linux-x64"):
        (tools_dir / name).mkdir(parents=True)
        (tools_dir / name / "blender").write_text("")
    override = tmp_path / "custom" / "blender"
    found = tools.blender_candidates(
        environ={"CC_BLENDER": str(override), "PATH": ""},
        platform="linux",
        tools_dir=tools_dir,
        home=tmp_path,
    )
    assert found[0] == override
    assert found[1].parent.name == "blender-5.10.0-linux-x64"  # version-aware, newest first
    assert found[2].parent.name == "blender-5.2.2-linux-x64"
    assert Path("/usr/bin/blender") in found


def test_blender_candidates_macos_and_windows_locations(tmp_path):
    mac = tools.blender_candidates(environ={"PATH": ""}, platform="darwin", tools_dir=tmp_path)
    assert Path("/Applications/Blender.app/Contents/MacOS/Blender") in mac
    windows_root = tmp_path / "Program Files"
    exe = windows_root / "Blender Foundation" / "Blender 5.2" / "blender.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    win = tools.blender_candidates(
        environ={"PATH": "", "ProgramFiles": str(windows_root)},
        platform="win32",
        tools_dir=tmp_path,
    )
    assert exe in win


def test_find_blender_skips_missing_and_wrong_programs(tmp_path):
    fake = tmp_path / "blender"
    fake.write_text("")
    impostor = tmp_path / "not-blender"
    impostor.write_text("")
    outputs = {fake: BLENDER_OUTPUT, impostor: "hello"}
    tool, version = tools.find_blender(
        [tmp_path / "missing", impostor, fake], runner=lambda path, args: outputs[path]
    )
    assert tool.path == fake and version.series == "5.2"


@pytest.mark.skipif(sys.platform.startswith("win"), reason="uses a shell script as fake Blender")
def test_find_blender_runs_a_real_executable(tmp_path):
    fake = tmp_path / "blender"
    fake.write_text('#!/bin/sh\necho "Blender 5.2.2 LTS"\n')
    os.chmod(fake, 0o755)
    tool, version = tools.find_blender([fake])
    assert str(version) == "5.2.2 LTS" and tool.version == "5.2.2 LTS"


def test_ffmpeg_features_parses_listings(tmp_path):
    listings = {
        "-encoders": " V....D libx264  libx264 H.264\n A....D aac  AAC\n",
        "-filters": " ... loudnorm  A->A  EBU R128\n ... subtitles V->V  libass\n",
    }
    features = tools.ffmpeg_features(tmp_path / "ffmpeg", runner=lambda p, args: listings[args[1]])
    assert features == {
        "libx264": True,
        "aac": True,
        "loudnorm": True,
        "ebur128": False,
        "subtitles": True,
        "rubberband": False,
    }


def test_ffmpeg_candidates_prefer_override_then_tools_dir(tmp_path):
    found = tools.ffmpeg_candidates(
        "ffprobe",
        environ={"CC_FFPROBE": "/opt/x/ffprobe", "PATH": ""},
        platform="linux",
        tools_dir=tmp_path,
    )
    assert found[:2] == [Path("/opt/x/ffprobe"), tmp_path / "ffmpeg-static" / "ffprobe"]
