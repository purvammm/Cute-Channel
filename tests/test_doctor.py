import json
from pathlib import Path

from pipeline import doctor, render_probe, tools

VERSIONS = {
    "BLENDER_SERIES": "5.2",
    "BLENDER_VERSION": "5.2.2",
    "BLENDER_INTEL_MAC_SERIES": "4.5",
    "BLENDER_INTEL_MAC_VERSION": "4.5.14",
}


def blender(text):
    version = tools.parse_blender_version(text)
    return tools.Tool("blender", Path("/x/blender"), str(version)), version


def test_python_check():
    assert doctor.check_python((3, 11, 4)).status == doctor.OK
    assert doctor.check_python((3, 9, 1)).status == doctor.FAIL


def test_packages_check_only_warns():
    check = doctor.check_packages(find_spec=lambda name: None)
    assert check.status == doctor.WARN and "PyYAML" in check.summary


def test_blender_check_versions():
    assert doctor.check_blender(*blender("Blender 5.2.2 LTS"), VERSIONS).status == doctor.OK
    older_patch = doctor.check_blender(*blender("Blender 5.2.0 LTS"), VERSIONS)
    assert older_patch.status == doctor.OK and "pinned 5.2.2" in older_patch.summary
    assert doctor.check_blender(*blender("Blender 5.1.0"), VERSIONS).status == doctor.WARN
    assert doctor.check_blender(None, None, VERSIONS).status == doctor.FAIL


def test_intel_mac_uses_the_45_lts_line():
    intel = doctor.check_blender(*blender("Blender 4.5.14 LTS"), VERSIONS, intel_mac=True)
    assert intel.status == doctor.OK
    assert doctor.check_blender(*blender("Blender 4.5.14 LTS"), VERSIONS).status == doctor.WARN


def test_ffmpeg_check():
    tool = tools.Tool("ffmpeg", Path("/x/ffmpeg"), "7.0")
    full = dict.fromkeys(tools.FFMPEG_FEATURES, True)
    assert doctor.check_ffmpeg(tool, full, "Linux").status == doctor.OK
    assert doctor.check_ffmpeg(tool, {**full, "rubberband": False}, "Linux").status == doctor.OK
    assert doctor.check_ffmpeg(tool, {**full, "libx264": False}, "Linux").status == doctor.WARN
    missing = doctor.check_ffmpeg(None, {}, "Darwin")
    assert missing.status == doctor.FAIL and "brew" in missing.fix


def test_secrets_are_counted_but_never_shown():
    token = "EAAB-super-secret-token-value"
    environ = {"IG_ACCESS_TOKEN": token}
    env_file = {"IG_USER_ID": "1784", "YT_CLIENT_ID": "abc", "YT_CLIENT_SECRET": "s"}
    checks = {c.area: c for c in doctor.check_secrets(environ, env_file)}
    assert checks["Instagram"].status == doctor.WARN  # 2 of 4 set
    assert checks["Instagram"].details["set"] == {
        "IG_ACCESS_TOKEN": "environment",
        "IG_USER_ID": ".env",
    }
    assert checks["YouTube"].status == doctor.WARN
    assert checks["LLM helper (optional, paid)"].status == doctor.INFO
    output = doctor.format_json(list(checks.values())) + doctor.format_text(list(checks.values()))
    assert token not in output and "1784" not in output


def test_committed_env_file_is_a_failure():
    assert doctor.check_secrets_file(exists=True, tracked=True).status == doctor.FAIL
    assert doctor.check_secrets_file(exists=True, tracked=False).status == doctor.OK
    assert doctor.check_secrets_file(exists=False, tracked=False).status == doctor.INFO


def test_render_check_uses_the_engine_choice():
    caps = {
        "blender": {"version": "5.2.2 LTS"},
        "results": [
            {
                "label": "cycles-cpu",
                "engine": "CYCLES",
                "gpu_backend": None,
                "ok": True,
                "seconds_per_frame": 0.6,
                "software_gl": None,
                "looks_blank": False,
            },
            {
                "label": "eevee",
                "engine": "EEVEE",
                "gpu_backend": None,
                "ok": True,
                "seconds_per_frame": 5.8,
                "software_gl": True,
                "looks_blank": False,
            },
        ],
    }
    tool = tools.Tool("blender", Path("/x"), "5.2.2 LTS")
    check = doctor.check_render(caps, tool)
    assert check.status == doctor.WARN and "preview: cycles-cpu" in check.summary
    assert "· eevee: 5.80 s/frame" in doctor.format_text([check])  # per-engine timings in logs
    stale = doctor.check_render(caps, tools.Tool("blender", Path("/x"), "5.2.3 LTS"))
    assert "re-run" in stale.fix
    assert doctor.check_render(None, tool).status == doctor.INFO
    nothing = {"results": [{"label": "eevee", "engine": "EEVEE", "gpu_backend": None, "ok": False}]}
    assert doctor.check_render(nothing, tool).status == doctor.FAIL


def test_run_doctor_without_any_tools(monkeypatch):
    monkeypatch.setattr(tools, "find_blender", lambda *a, **k: (None, None))
    monkeypatch.setattr(tools, "find_ffmpeg_tool", lambda *a, **k: None)
    monkeypatch.setattr(render_probe, "load_capabilities", lambda *a, **k: None)
    checks = doctor.run_doctor(environ={})
    by_area = {c.area: c for c in checks}
    assert by_area["Blender"].status == doctor.FAIL
    assert by_area["ffmpeg"].status == doctor.FAIL
    assert doctor.exit_code(checks) == 1
    payload = json.loads(doctor.format_json(checks))
    assert payload["exit_code"] == 1 and payload["summary"]["fail"] >= 2
    assert "| ❌ | Blender |" in doctor.format_markdown(checks)


def test_ascii_icons_for_non_utf8_consoles():
    class Latin1:
        encoding = "cp1252"

    class Utf8:
        encoding = "UTF-8"

    assert doctor._icons(Latin1()) is doctor.ASCII
    assert doctor._icons(Utf8()) is doctor.EMOJI
