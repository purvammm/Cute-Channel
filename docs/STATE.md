# State (update at the end of every session)

_Last updated: 2 Oct 2026, session 1 (Phase 0)._

## Done

- `main` seeded with the owner's `docs/guide.html` and `docs/MASTER_PROMPT.md`, transcribed
  verbatim from the chat attachments (the repo was empty).
- **Phase 0** on branch `feat/phase-0-bootstrap`: repo skeleton, `cc.py` (doctor + planned-command
  stubs), `pipeline/` (doctor, specs, tools, render probe), `blender/` (compat, colors, smoke
  test), `scripts/setup_env.sh`, CI (`lint-test`, `blender-smoke`), issue/PR templates, 18 labels
  (synced to GitHub), 64 unit tests, docs (digest, roadmap, human tasks, secrets, render
  environment, decision 000).
- Verified in the sandbox: headless renders with Cycles CPU, EEVEE (EGL/llvmpipe and
  Vulkan/lavapipe) and Workbench, with frames inspected. `setup_env.sh` tested on the dnf path,
  both when re-run and from a clean copy.

## Next

1. Owner reviews and merges the Phase 0 PR. Then read the `blender-smoke` CI timings into
   `docs/RENDER_ENVIRONMENT.md`.
2. **Phase 1** (brand and creative decisions) on `feat/phase-1-brand`, plus `docs/TOOLING_OPTIONS.md`.

## Open human tasks

H01 (laptop details + Blender + `doctor --deep`, issue #1), H02 (branch protection, issue #2).
Full list in `docs/HUMAN_TASKS.md`.

## Known issues and gotchas

- `download.blender.org` serves a Cloudflare challenge to scripts, so use the mirrors in
  `scripts/versions.env` (SHA-256 checked).
- Headless EEVEE logs `EGL_BAD_MATCH` errors that are harmless.
- In background mode the engine enum lists one engine only; `compat.resolve_engine()` handles it.
- `Material.use_nodes` is deprecated in 5.2; use `compat.new_material()`.
- Sandbox only: `/tmp` is wiped between commands; system `python3` is 3.9 (use `.venv/`); each
  command runs in its own process sandbox, so background jobs die when the command ends.
- The macOS branch of `setup_env.sh` and the Windows install path are untested.

## Environment facts

Sandbox: Amazon Linux 2023, 8 vCPU, no GPU. Blender 5.2.2 LTS in `.tools/` (bundled Python
3.13). ffmpeg 7.0.2 static in `.tools/ffmpeg-static/` (has libx264, aac, loudnorm, libass,
rubberband). Mesa 24.2.6 llvmpipe.
