# Episodes

There's one folder per episode, for example `E001_<slug>/`:

| File | What it is | Committed? |
|---|---|---|
| `episode.yaml` | The script: beats, motions, emotions, sound cues (Phase 4) | yes |
| `storyboard.md` | The 6-box storyboard in words (guide §16.1) | yes |
| `events.json` | Frame-exact impacts, pops and steps for sound sync (written by the compiler) | yes |
| `render/` | PNG frames | no (gitignored) |
| `out/` | `final_IG.mp4`, `final_YT.mp4`, `caption.md`, `cover.png` | captions and covers only; videos are CI artifacts |
