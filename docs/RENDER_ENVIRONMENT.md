# Where can we render? (measured, not assumed)

**Short answer:** EEVEE runs headless on GPU-less machines through Mesa's software graphics,
with no X server needed. It's fast enough for **previews** in CI but far too slow for **final**
renders. Final renders belong on a machine with a real GPU, which normally means your laptop,
overnight.

## Sandbox measurements (2 Oct 2026)

Machine: Amazon Linux 2023, 8 vCPU, 30 GB RAM, **no GPU**. Blender 5.2.2 LTS. Mesa 24.2.6
(llvmpipe for OpenGL 4.5, lavapipe for Vulkan). The scene is the smoke test: a subdivided blob
with subsurface skin, eyes, an area light and DOF.

| Engine (`cc.py doctor --deep` label) | 270×480, 16 samples | 1080×1920, 64 samples | 10 s Reel (300 frames) at full quality |
|---|---|---|---|
| Cycles, CPU (`cycles-cpu`) | 0.59 s/frame | 36.3 s/frame | ≈ 3 h |
| EEVEE, OpenGL via EGL + llvmpipe (`eevee`) | 5.77 s/frame | 70.6 s/frame | ≈ 6 h |
| EEVEE, Vulkan + lavapipe (`eevee-vulkan`) | 5.91 s/frame | not measured | ≈ 6 h |
| Workbench (`workbench`) | 0.20 s/frame | not measured | grey clay only; timing checks |

The first EEVEE frame takes about 15 s longer because shaders compile once per Blender run.
The lines `EGL Error (0x3009): EGL_BAD_MATCH` in the logs are harmless.

How doctor uses these numbers (`pipeline/render_probe.py`, `choose_engine()`):

- **Preview:** EEVEE when it is at most 3× slower than Cycles; otherwise Cycles on the CPU
  (here: Cycles, ~10× faster). If both fail, Workbench, with a warning that only the timing is meaningful.
- **Final:** EEVEE on a real GPU. With software graphics it still picks EEVEE but warns, with a
  time estimate. If EEVEE fails entirely, it uses Cycles and warns that the look differs.
- Looks that use EEVEE-only toon shading (guide §9.2) set `require_eevee`, so Cycles is never picked.

## GitHub Actions (free runners, no GPU)

`.github/workflows/blender-smoke.yml` runs the same probes on `ubuntu-latest` and puts the timings
in the job summary and log, with the frames as an artifact. First runs on the Phase 0 PR
(ubuntu-24.04, 2 Oct 2026). Setup took about 2.5 min, and the four probes took about 1.5 min:

| Engine | 270×480, 16 samples | Doctor's choice |
|---|---|---|
| Cycles, CPU | 1.36 s/frame | **preview** |
| EEVEE, OpenGL (llvmpipe) | 9.77 s/frame | |
| EEVEE, Vulkan (lavapipe) | 7.70 s/frame | **final** (≈ 7.8 h per 10 s Reel, so not practical) |
| Workbench | 0.20 s/frame | |

**Verdict for CI:** quarter-resolution previews are fine. A 10 s preview with Cycles at 16
samples is about 300 × 1.4 s ≈ 7 min. Final renders aren't practical on free runners.

## Your laptop

Unknown until you run `python cc.py doctor --deep` and paste the output (issue H01). For scale:
the guide's own estimate for EEVEE on a mid-range laptop is 3–10 s per final frame
(§13.3), so 15–50 min for a 10 s Reel.

## Options for final renders (no paid service chosen)

1. **Your laptop, overnight (recommended, free).** `python cc.py render E001 --final` (Phase 5)
   renders a resumable PNG sequence, so a crash or a closed lid loses nothing.
2. **CI with software EEVEE (free, slow).** About 6+ hours for one 10 s Reel on 8 vCPUs, and
   probably more on a 4-vCPU runner. It also eats your runner minutes if the repo goes private. Only as
   a last resort.
3. **Self-hosted runner on your laptop (free, not recommended while the repo is public).** On a
   public repo, anyone's fork PR could run code on your machine. Only consider it if the repo
   goes private.
4. **Cloud GPU (paid).** Not evaluated yet. Phase 5 will list current options and prices, and
   nothing will be bought without your explicit approval.
