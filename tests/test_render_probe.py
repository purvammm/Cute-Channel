from pathlib import Path

from pipeline import render_probe
from pipeline.render_probe import ProbeResult


def result(label, engine, spf, *, software=None, ok=True, blank=False, backend=None):
    return ProbeResult(
        label=label,
        engine=engine,
        gpu_backend=backend,
        ok=ok,
        seconds_per_frame=spf if ok else None,
        software_gl=software,
        looks_blank=blank,
    )


# Measured in the sandbox on 2 Oct 2026 (270x480, 16 samples, no GPU).
SANDBOX = [
    result("cycles-cpu", "CYCLES", 0.587),
    result("eevee", "EEVEE", 5.767, software=True),
    result("eevee-vulkan", "EEVEE", 5.912, software=True, backend="vulkan"),
    result("workbench", "WORKBENCH", 0.195, software=True),
]


def test_gpu_less_machine_previews_with_cycles_and_warns_about_finals():
    preview = render_probe.choose_engine(SANDBOX, "preview")
    final = render_probe.choose_engine(SANDBOX, "final")
    assert preview.label == "cycles-cpu"  # software EEVEE is ~10x slower than Cycles here
    assert final.label == "eevee" and "slow" in final.warning


def test_real_gpu_wins_for_finals_and_previews():
    laptop = [result("cycles-cpu", "CYCLES", 2.0), result("eevee", "EEVEE", 0.4, software=False)]
    assert render_probe.choose_engine(laptop, "final").label == "eevee"
    assert render_probe.choose_engine(laptop, "final").warning is None
    assert render_probe.choose_engine(laptop, "preview").label == "eevee"


def test_eevee_preferred_for_previews_unless_much_slower():
    close = [result("cycles-cpu", "CYCLES", 1.0), result("eevee", "EEVEE", 2.5, software=True)]
    assert render_probe.choose_engine(close, "preview").label == "eevee"


def test_fallbacks_when_engines_fail():
    no_eevee = [result("cycles-cpu", "CYCLES", 1.0), result("eevee", "EEVEE", None, ok=False)]
    assert render_probe.choose_engine(no_eevee, "final").label == "cycles-cpu"
    only_workbench = [result("workbench", "WORKBENCH", 0.2), result("cy", "CYCLES", 1, blank=True)]
    choice = render_probe.choose_engine(only_workbench, "preview")
    assert choice.label == "workbench" and choice.warning
    assert render_probe.choose_engine(only_workbench, "final") is None
    assert render_probe.choose_engine([], "preview") is None


def test_require_eevee_never_falls_back():
    assert render_probe.choose_engine(SANDBOX, "preview", require_eevee=True).label == "eevee"
    cycles_only = [result("cycles-cpu", "CYCLES", 1.0)]
    assert render_probe.choose_engine(cycles_only, "final", require_eevee=True) is None


def test_estimate_matches_the_full_resolution_calibration():
    # Full-res, 64-sample frames measured 70.6 s (EEVEE) and 36.3 s (Cycles): ~353 / ~182 min.
    eevee = render_probe.estimate_reel_minutes(SANDBOX[1])
    cycles = render_probe.estimate_reel_minutes(SANDBOX[0])
    assert 300 < eevee < 400
    assert 150 < cycles < 210


def test_is_software_renderer():
    assert render_probe.is_software_renderer("llvmpipe (LLVM 15.0.7, 256 bits)")
    assert render_probe.is_software_renderer("NVIDIA GeForce RTX 4060 Laptop GPU") is False
    assert render_probe.is_software_renderer(None) is None


def test_probe_command_passes_engine_and_backend():
    cmd = render_probe.probe_command(
        Path("/b/blender"),
        render_probe.Probe("eevee-vulkan", "EEVEE", "vulkan"),
        Path("/out"),
        Path("/out/result.json"),
    )
    assert cmd[:4] == ["/b/blender", "-b", "--factory-startup", "-noaudio"]
    assert cmd[cmd.index("--gpu-backend") + 1] == "vulkan"
    assert cmd[cmd.index("--engine") + 1] == "EEVEE"
    assert "--python-exit-code" in cmd


def test_capabilities_round_trip(tmp_path):
    path = tmp_path / "caps.json"
    render_probe.save_capabilities(SANDBOX, Path("/b/blender"), "5.2.2 LTS", path)
    loaded = render_probe.load_capabilities(path)
    assert loaded["blender"]["version"] == "5.2.2 LTS"
    restored = render_probe.results_from_capabilities(loaded)
    assert [r.label for r in restored] == [r.label for r in SANDBOX]
    assert render_probe.choose_engine(restored, "preview").label == "cycles-cpu"
