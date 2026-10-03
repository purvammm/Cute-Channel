# State (update at the end of every session)

_Last updated: 2 Oct 2026, session 1 (Phases 0 and 1)._

## Done

- `main` seeded with the owner's `docs/guide.html` and `docs/MASTER_PROMPT.md`, transcribed
  verbatim from the chat attachments (the repo was empty).
- **Phase 0, PR #3** (`feat/phase-0-bootstrap`): skeleton, `cc.py doctor`, `pipeline/` (doctor,
  specs, tools, render probe), `blender/` (compat, colors, smoke test), `setup_env.sh`, CI
  (`lint-test`, `blender-smoke`, both green), templates, 18 labels, docs. Headless rendering was
  measured in the sandbox and on GitHub runners (`docs/RENDER_ENVIRONMENT.md`).
- **Phase 1, PR #6 (`feat/phase-1-brand`)** (stacked on Phase 0): decisions 001–006 (Chuski the
  chai drop, Shakkar the sugar cube, the windowsill, the name and handles, strategy, voice),
  `brand/*.json` + JSON Schemas + `cc.py validate`, `cc.py brand-sheets` (4 PNG sheets, all
  inspected), `FIRST_12_EPISODES.md`, `growth/idea_bank.csv` (75 ideas), `growth/calendar.csv`,
  and `BRAND_ONE_PAGER.md`. 82 tests.

## Next

1. Owner merges **#3 first**, then #6. Its diff shrinks to Phase 1 once #3 is in.
2. `docs/TOOLING_OPTIONS.md` (MASTER_PROMPT §7), as a small PR.
3. **Phase 2:** `blender/build_character.py` builds Chuski and Shakkar from `character.json`,
   with front/side/¾ renders and a 96×170 thumbnail test, inspected. Also check the poop-emoji
   silhouette risk from decision 001.

## Open human tasks

#1 laptop + Blender + `doctor --deep` · #2 branch protection · #4 handles and accounts · #5 foley
and voice recordings. Details in `docs/HUMAN_TASKS.md`.

## Known issues and gotchas

- `download.blender.org` serves a Cloudflare challenge to scripts, so use the mirrors in
  `scripts/versions.env` (SHA-256 checked).
- Headless EEVEE logs `EGL_BAD_MATCH` errors that are harmless.
- In background mode the engine enum lists one engine only; `compat.resolve_engine()` handles it.
- `Material.use_nodes` is deprecated in 5.2; use `compat.new_material()`.
- resvg needs a *quoted* family name in SVG (`font-family="'Baloo 2'"`), or text silently disappears.
- Python's `csv` writes CRLF; git normalises it (harmless warning). Use `lineterminator="\n"` next time.
- CI artifacts and logs can't be downloaded from the sandbox (401). Read CI results through
  `gh api repos/.../actions/jobs/<id>/logs` instead.
- Sandbox only: `/tmp` is wiped between commands, system `python3` is 3.9 (use `.venv/`), and
  background jobs die when the command ends.
- Untested: the macOS branch of `setup_env.sh` and any Windows install path.

## Environment facts

Sandbox: Amazon Linux 2023, 8 vCPU, no GPU. Blender 5.2.2 LTS in `.tools/` (bundled Python
3.13). ffmpeg 7.0.2 static in `.tools/ffmpeg-static/`. Mesa 24.2.6 llvmpipe. CI runner:
ubuntu-24.04, ffmpeg 6.1.1 from apt.
