# 000 · Repo and tooling conventions

**Status:** proposed in the Phase 0 PR · **Date:** 2 Oct 2026

## Decisions

1. **Plain Python 3.10+ and one CLI (`python cc.py ...`, argparse).** No framework to learn.
   `doctor` uses only the standard library, so it works on a broken setup.
2. **Blender pinned to 5.2.2 LTS** (4.5.14 LTS on Intel Macs) in `scripts/versions.env`, with
   SHA-256 checks. CI and the sandbox use a portable copy in `.tools/`. Every machine runs the
   same Python API, and API differences are absorbed in `blender/lib/compat.py`.
3. **Engines are chosen per machine by measurement**, not by assumption. `doctor --deep` tests
   every engine; previews and finals then pick the best one available (`render_probe.choose_engine`).
4. **No renders or videos in git.** PNG frames and MP4s live on your laptop or as CI artifacts
   (kept 14 days). No Git LFS unless you ask for it. Small review images (under 1 MB each, enforced
   by a test) may be committed under `docs/samples/`.
5. **One PR per phase, conventional commits** (`feat:`, `fix:`, `docs:`, `ci:` …). The one
   exception was the **seed commit**: the repo had no `main`, so `main` was created with only your
   two source documents, as the master prompt's own "How to use" steps 2–3 describe. Everything
   since arrives through PRs.
6. **Specs live in one place.** `pipeline/specs.py` holds the platform and craft numbers, and each
   cites its `docs/GUIDE_DIGEST.md` id.
7. **The repo stays public for now:** free CI minutes and a dated record that the character is
   yours. Sensitive business data (client prospects) will never be committed here.

## Consequences

- Final renders need a machine with a GPU, normally your laptop overnight. CI can only make previews
  quickly (see `docs/RENDER_ENVIRONMENT.md`).
- The Windows setup script isn't written yet. That waits for your laptop details (H01).
