# Blender scripts

Everything here runs inside Blender's own Python, never your system Python:

```bash
blender -b --factory-startup --python blender/<script>.py -- <script options>
```

You normally don't call these directly. `python cc.py ...` finds Blender and runs them for you.

| File | Phase | What it does |
|---|---|---|
| `lib/compat.py` | 0 | Version-tolerant API helpers (engine ids, material sockets, deprecated calls) |
| `lib/colors.py` | 0 | sRGB hex to the linear RGB Blender expects (pure Python, also used by tests) |
| `smoke_test.py` | 0 | Tiny test scene that `cc.py doctor --deep` renders with each engine |
| `build_character.py` | 2 | Builds the character from `brand/character.json` |
| `build_studio.py` | 5 | Cyclorama, 3-point lights, 9:16 camera into `assets/STUDIO_master.blend` |
| `make_episode.py` | 4 | `episode.yaml` to an animated `.blend` plus `events.json` |
| `render.py` | 5 | Crash-safe, resumable PNG-sequence renders (`--preview`, `--final`) |

The pinned version is in `scripts/versions.env` (5.2 LTS; 4.5 LTS on Intel Macs).
