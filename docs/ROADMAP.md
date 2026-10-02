# Roadmap

There's one PR per phase (sometimes a few). Merge order matters: each phase builds on the
previous one. Status is kept current here and in `docs/STATE.md`.

| Phase | Goal | Main deliverables | Needs you for | Status |
|---|---|---|---|---|
| **0 · Bootstrap** | Repo, CLI, CI, environment | skeleton, `cc.py doctor`, `setup_env.sh`, CI, templates, labels, `GUIDE_DIGEST.md` | laptop details + Blender install (H01), branch protection (H02) | 🔄 PR open |
| **1 · Brand & creative** | Character, sidekick, world, name, strategy | `docs/decisions/001+`, `brand/*.json` + schemas, character/turnaround/expression sheets, first 12 episodes, 60+ ideas, one-pager | veto anything; check handle availability (H03) | ⏭ next |
| **2 · Parametric character** | Character built from `character.json` | `build_character.py`, `.blend`, front/side/¾ + thumbnail-test renders | nothing | |
| **3 · Rig & emotions** | Movable, expressive character | Level A rig, face system, `emotions.json` (≥ 20), emanata, `cc.py emotion-sheet` | nothing | |
| **4 · Motions & compiler** | Idea → animated `.blend` | `motions.py`, `episode.yaml` schema, `make_episode.py`, `events.json`, `cc.py new-episode`, `ANIMATION_QUALITY.md` | hand-polish key shots (H08) | |
| **5 · Studio & render** | Reusable studio, reliable renders | `build_studio.py`, `render.py` (PNG sequence, `--resume`, `--preview`, `--final`), CI preview MP4s | overnight final renders on the laptop | |
| **6 · Sound** | Auto-synced, mixed soundtrack | SFX manifest, synthetic SFX, voice pipeline, `mix.py` (−14 LUFS), IG/YT audio versions | record foley + voice (H05) | |
| **7 · Finishing & QA** | Postable files | `finish.py` (H.264, captions, cover, loop check), `qa.py`, caption + checklist | final phone check (H07) | |
| **8 · Content engine** | Never run out of ideas | `cc.py ideas`, weekly planner issue, trend fast-path, teardown helper | pick the weekly episode | |
| **9 · Publishing** | One-click, approval-gated posting | `publish/instagram.py`, `publish/youtube.py`, `publish.yml`, `cc.py package` | accounts + API setup (H03, H04), approve each post | |
| **10 · Analytics** | Learn from every post | metrics import, weekly report issue, the 8-shorts gate, A/B tests | read the report | |
| **11 · Money & portfolio** | First paid work | Pages portfolio, rate card, prospect drafts (private), `COMPLIANCE.md` | outreach, contracts, tax (H10) | |

**First publishable episode** needs Phases 1–7. Phase 6 can ship with synthesised sound effects
if your recordings aren't ready yet. Publishing by API (Phase 9) isn't needed for the first post:
you can post the packaged files by hand.

Also due (from MASTER_PROMPT §7): `docs/TOOLING_OPTIONS.md`, which compares Blender with
online/2D/AI alternatives. It's planned alongside Phase 1 so a 2D-first variant is considered before
building more 3D tooling.
