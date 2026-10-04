# Cute Channel

> **New here? Start with the step-by-step guide:** [open it as a web page](https://htmlpreview.github.io/?https://github.com/purvammm/Cute-Channel/blob/main/docs/START_HERE.html)
> (the file is [`docs/START_HERE.html`](docs/START_HERE.html)). It covers every click and command on your Windows laptop and iPhone, in order.

Automation for a one-person cute 3D micro-animation channel (Instagram Reels + YouTube Shorts).
You make the taste calls and learn animation; the scripts handle the rest: character build,
animation blocking, rendering, sound sync, captions, QA and publishing, each behind your approval.

- **Craft source of truth:** [`docs/guide.html`](docs/guide.html), your guide (Blender 5.2 LTS, 26 Sept 2026)
- **The plan:** [`docs/MASTER_PROMPT.md`](docs/MASTER_PROMPT.md), with progress tracked in [`docs/ROADMAP.md`](docs/ROADMAP.md)
- **Your to-do list:** [`docs/HUMAN_TASKS.md`](docs/HUMAN_TASKS.md)
- **Where things stand:** [`docs/STATE.md`](docs/STATE.md)

## Make an episode in 5 commands

This is the target workflow. Each command arrives in the phase shown; today only `doctor` works.

```bash
python cc.py new-episode "waits for chai to cool, sidekick drinks it"  # idea -> storyboard + episode.yaml (Phase 4)
python cc.py compile E004            # episode.yaml -> animated .blend + events.json      (Phase 4)
python cc.py render E004 --preview   # quick look; use --final overnight on your laptop   (Phase 5)
python cc.py finish E004             # sound mix, captions, cover, QA                     (Phases 6-7)
python cc.py package E004            # phone-ready folder: IG + YT videos, caption, checklist (Phase 9)
```

Run `python cc.py --help` for every command and the phase that builds it.

## Set up your laptop

1. **Blender:** install **5.2 LTS** from [blender.org/download](https://www.blender.org/download/),
   or **4.5 LTS** on an Intel Mac (guide §3.1, §6.1).
2. **Python 3.10+** ([python.org](https://www.python.org/downloads/); 3.11 recommended) and **git**.
3. Get the code: `git clone https://github.com/purvammm/Cute-Channel.git && cd Cute-Channel`
4. Install everything else:
   - **macOS / Linux:** `bash scripts/setup_env.sh`. This installs ffmpeg and the Python packages and,
     if Blender isn't in Applications, a pinned portable copy. The macOS path is untested so far.
   - **Windows:** for now, `winget install Gyan.FFmpeg`, then `py -3.11 -m pip install -r requirements.txt`.
     A proper Windows script follows once Kiro knows your laptop (task H01).
5. Check: `python cc.py doctor`, then `python cc.py doctor --deep`, which test-renders with each
   engine (1–5 min). Paste the output into issue #1.

## How we work together (GitHub is the control panel)

- **PRs:** Kiro opens one PR per phase. Each PR description says what was built, how to run it,
  what was tested, and what you need to do. **Merging is your approval.**
- **Issues:** tasks for you are labelled `needs-human`. Use the issue forms to propose an episode or report a bug.
- **Labels:** `needs-human` · `approved` (unlocks publishing) · `rendering` · `ready-to-publish` ·
  `published` · `phase-0` … `phase-11`. To recreate them: `python scripts/sync_labels.py`.
- **Veto any creative decision:** comment `veto: <why>` on its PR (see `docs/decisions/README.md`).
- **Safety rules:** nothing publishes, spends money or messages anyone without your explicit
  approval. Secrets never enter the repo (`docs/SETUP_SECRETS.md`). Every asset's licence is
  logged (`assets/LICENCES.md`).

## Folder map

| Folder | What's in it |
|---|---|
| `cc.py` | the single command line |
| `pipeline/` | everything outside Blender: doctor, specs, render-engine probe; later sound, captions, QA |
| `blender/` | scripts that run inside Blender (`lib/compat.py` keeps them working across versions) |
| `brand/` | machine-readable character bible, palette, emotions (Phase 1+) |
| `episodes/` | one folder per episode: `episode.yaml`, storyboard, events |
| `assets/` | sound effects, music, props, characters, plus `LICENCES.md` |
| `growth/` | idea bank, calendar, teardowns, stats (CSV, opens in Google Sheets) |
| `publish/`, `analytics/` | approval-gated posting (Phase 9) and reports (Phase 10) |
| `docs/` | guide, plan, roadmap, decisions, digest of the guide's rules, setup notes |
| `scripts/` | `setup_env.sh`, pinned `versions.env`, `sync_labels.py` |

## Repository settings to turn on (5 minutes)

Settings → Branches → **Add branch protection rule** (or **Rulesets**) for `main`: require a pull
request before merging, and require the **lint-test** status check to pass. See issue #2.

## For developers (and future AI sessions)

```bash
bash scripts/setup_env.sh && source .venv/bin/activate
ruff check . && ruff format --check . && python -m pytest -q
```

Read `docs/STATE.md` first. It says what's done, what's next and what's blocked.
