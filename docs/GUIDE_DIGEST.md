# Guide digest: the rules the scripts encode

These are the facts and rules from `docs/guide.html` (revised 26 Sept 2026) that the pipeline
turns into code. Each has an id (G##) that the code cites, plus its guide section (§). If the
guide or a platform changes, update this file and `pipeline/specs.py` together.

**Status:** 📘 craft rule (doesn't go stale) · ✅ re-verified 2 Oct 2026 · ⏳ dated: re-check
before the phase that acts on it · ≈ approximate

## A. Output and platform specs

| ID | Rule | § | Encoded in | Status |
|---|---|---|---|---|
| G01 | Video 1080×1920 (9:16), 30 fps, H.264 + AAC | 11.3, 12.1, 15.2 | `specs.WIDTH/HEIGHT/FPS/…` | 📘 |
| G02 | Video bitrate about 10–16 Mb/s | 15.2 | `specs.VIDEO_BITRATE_MBPS` (Phase 7) | 📘 |
| G03 | Micro-animations run 5–20 s. Reels over 3 min aren't shown to non-followers; Shorts go up to 3 min | hero, 15.2 | `specs.DURATION_S` (QA, Phase 7) | ⏳ Phase 7 |
| G04 | Frame 1 already shows action and a face: the hook lands in the first second | 1, 16.1, 18.2 | compiler + cover check (Phases 4, 7) | 📘 |
| G05 | Upload the clean original MP4, never a downloaded or watermarked repost | 18.2 | publish (Phase 9) | 📘 |
| G06 | At most **5 hashtags** per post. They classify a post, they don't boost reach | 18.2 | `specs.MAX_HASHTAGS` | ✅ cap confirmed by several Dec 2025 reports |
| G07 | Caption = 1 line + a question or call to action + up to 5 specific hashtags | 18.2 | caption generator (Phase 7) | 📘 |
| G08 | Use an Instagram **Creator** account (Business accounts get a smaller music library) | 14.4, 18.1 | human task H03 | ⏳ Phase 9 |
| G09 | YouTube: set "made for kids" on every video; `#shorts` is optional | 18.2, 21 | `publish/youtube.py` (Phase 9) | ⏳ Phase 9 |

## B. Safe zones and on-screen text

| ID | Rule | § | Encoded in | Status |
|---|---|---|---|---|
| G10 | Keep faces and text out of the top 14%, bottom 35% and 6% each side. At 1080×1920 the safe box is x 65–1015, y 269–1248 | 12.2 | `specs.safe_rect()` | ✅ Meta guidance (AdsUploader, Lucid Media) |
| G11 | The like/comment/share column sits on the right, just above the bottom band, so keep faces centred or a bit left. Box ≈ x 886–1015, y 902–1248 | 12.2 | `specs.button_column_rect()` | ≈ read off the guide's diagram |
| G12 | Hook text: rounded bold font, white with a dark outline, inside the safe zone, about 1 s per 3–4 words | 15.1 | `specs.text_hold_seconds()` (Phase 7) | 📘 |

## C. Sound

| ID | Rule | § | Encoded in | Status |
|---|---|---|---|---|
| G13 | Place each SFX on the impact frame or 1 frame after, **never before** | 15.1, 15.2 | `specs.SFX_OFFSET_FRAMES` (Phase 6 mix) | 📘 |
| G14 | When animating to audio, the pose lands 1–2 frames before the accent: the picture leads, the sound follows | 11.7 | trend template (Phase 8) | 📘 |
| G15 | Loudness about −14 LUFS integrated, true peak ≤ −1 dBTP | 15.2 | `specs.LOUDNESS_LUFS`, `TRUE_PEAK_DBTP` | 📘 common target, not a platform rule |
| G16 | Mix: voice loudest, SFX a little under, music well under | 15.2 | `pipeline/mix.py` (Phase 6) | 📘 |
| G17 | Voice = own gibberish, pitched +4…+8 semitones (**one fixed value** per character), tempo +5–10% optional | 14.3 | `specs.VOICE_*`; the chosen value goes in `character.json` | 📘 |
| G18 | Two exports: Instagram without baked licensed music (trending audio is added in-app), YouTube with only own/CC0/YouTube Audio Library sound | 14.1, 14.4, 15.1 | Phases 6–7 + QA | ⏳ Phase 6 |
| G19 | There's no "10-second rule": short clips of copyrighted music are still copyrighted | 14.4 | QA guard (Phase 7) | 📘 |
| G20 | Prefer CC0; CC-BY needs a credit; never CC-BY-NC; keep Pixabay page links; log every asset | 3.4, 14.2, 21 | `assets/LICENCES.md` + QA | 📘 |

## D. Animation timing (30 fps)

| ID | Rule | § | Encoded in | Status |
|---|---|---|---|---|
| G21 | Blink 5–7 f · head turn 6–10 f (+4 to settle) · readable hold ≥ 15 f · small hop 20–30 f · surprised take 4 f anticipation, 2–3 f to the extreme, ≥ 10 f hold · steps 4–6 f each · wiggle 2–3 f per direction · sleepy/sad = double | 11.6 | `specs` timing constants | 📘 |
| G22 | Jelly hop keys at f1/6/9/17/23/25/29/33/45 with the guide's Z and scale values, Vector handles at f6 and f25, End = 44, blink at f36/38/39/42 | 11.4 | `specs.JELLY_HOP*` (Phase 4 `motions.py`) | 📘 |
| G23 | Loop rule: the last key repeats the first pose, and scene End = last key − 1. Use Make Cyclic for endless motion | 11.5, 6.5 | `specs.loop_end_frame()` | 📘 |
| G24 | Workflow: block (Constant) → spline (Bézier) → polish (Vector at contacts, rounded tops) | 11.5 | compiler (Phase 4) | 📘 |
| G25 | Squash and stretch keep volume roughly constant: shorter means wider (e.g. Z 0.8 ↔ XY 1.12) | 10.1, 11.2 | `motions.py` (Phase 4) | 📘 |
| G26 | Follow-through: loose parts lag 2–4 f. Always overshoot and settle; blink or breathe during holds so they never freeze | 11.2, 11.4, 11.5 | `specs.FOLLOW_THROUGH_FRAMES` | 📘 |
| G27 | Emanata pop: scale 0 → 1.25 in 3 f → 1.0 two frames later, float up for ~15 f, shrink to 0 in 3 f, with a pop/ting on the first frame | 11.8 | `specs.EMANATA_*` | 📘 |
| G28 | Lip-sync uses 3 mouth shapes (closed M/B/P, open A, round O/U). Less mouth movement reads cuter | 11.7 | Phases 3–4 | 📘 |
| G29 | Blink = eye Scale Z 1 → 0.1. Shape keys `smile`, `mouth_O`, `sad`, `cheeks_puff`. Expression swap = alternate eyes at Scale 0, swapped with Constant keys on the same frame | 10.4 | Phase 3 rig | 📘 |

## E. Character, modelling, materials

| ID | Rule | § | Encoded in | Status |
|---|---|---|---|---|
| G30 | Baby schema: head ½–⅔ of the height (or all head), big low wide-set eyes with 1–2 highlights, ~80% circles, tiny features, 1 main colour + 1 accent + dark eyes + blush. Must pass the thumbnail test | 2, 7.2 | Phase 1 schema, Phase 2 checks | 📘 |
| G31 | Shape language: circles = friendly, squares = stubborn (good for a grumpy sidekick), triangles = danger | 2 | Phase 1 | 📘 |
| G32 | UV sphere 16 segments × 8 rings, Subdivision 2/2, Shade Smooth, applied scale, origin at the feet, 1–2 m tall. Separate named eyes (`eye.L` on +X) | 8.1–8.3, 10.1 | Phase 2 | 📘 |
| G33 | Principled roughness 0.5–0.7, subsurface weight 0.05–0.2, eyes dark-not-black at roughness 0.1–0.2, blush alpha ≈ 0.5 (raise samples if grainy) | 9.1 | Phase 2 | 📘 |
| G34 | Toon look is EEVEE-only (Shader to RGB → Constant ramp). Inverted-hull outline: Solidify 0.01–0.03, offset 1, flipped normals, material offset 1, backface culling | 9.2 | Phase 2 flag; `choose_engine(require_eevee=True)` | 📘 |
| G35 | Colour management: AgX by default; Standard when colours must match exactly (toon, client brand colours) | 9.3 | Phases 2, 5 | 📘 |

## F. Camera, light, render

| ID | Rule | § | Encoded in | Status |
|---|---|---|---|---|
| G36 | Lens 50–85 mm (20–24 mm for comic close-ups), camera at eye level or a bit above. DOF on, focused on the head, f/1–2.8 | 12.1, 12.5 | `build_studio.py` (Phase 5) | 📘 |
| G37 | Three area lights. Key: front-left and above, 2–3 m in size, warm, 300–600 W. Fill: front-right at ≈⅓ of the key, cool. Rim: behind, ≈ key. Pastel world at 0.5–1 | 12.3 | Phase 5 | 📘 |
| G38 | Cyclorama: plane ×10, back wall extruded 6 m, floor–wall edge bevelled with ~10 segments, shaded smooth | 12.4 | Phase 5 | 📘 |
| G39 | EEVEE at 32–64 samples. Render to a PNG sequence (crash-safe, resumable) at `//render/` | 13.1, 13.3 | `render.py` (Phase 5) | 📘 |

## G. Content and growth

| ID | Rule | § | Encoded in | Status |
|---|---|---|---|---|
| G40 | Structure: hook 0–1 s, setup 1–4 s, twist 4–8 s, payoff 8–12 s, loop bridge in the last 1 s. Storyboard 6 boxes first | 16.1 | episode schema (Phase 4) | 📘 |
| G41 | Eight pillars: trend, relatable, interactive, food/ASMR, seasonal, duo, loops, behind the scenes. Plan seasonal posts 2 weeks early | 16.2 | Phases 1, 8 | 📘 |
| G42 | Hook formulas: "me when…", "POV:", "wait for it…" (only with a real payoff), "send this to your…", "day N of…", "pause at…" | 16.4 | Phases 1, 8 | 📘 |
| G43 | Log per Reel: pillar, length, views, average watch %, sends per reach, saves, follows. Diagnose with skip → hook, watch time → cut or move the twist earlier, sends → more relatable, follows → personality | 18.4 | Phase 10 | 📘 |
| G44 | The 8-shorts gate: continue only if production time per Reel drops, followers/sends grow, or someone asks about paid work. Views alone don't count | 5 | Phase 10 | 📘 |
| G45 | Consistency beats volume. Build a buffer of 2–4 Reels | 17.3 | Phases 1, 8 | 📘 |

## H. Policy, money, legal (dated)

| ID | Rule | § | Encoded in | Status |
|---|---|---|---|---|
| G46 | YouTube "inauthentic content": no generic, repetitive or template-based uploads. Reusing a rig is fine; the same gag in 30 colours is not | 20 | originality guard (Phase 7) | ⏳ Phase 7 |
| G47 | India's IT Rules (from 20 Feb 2026) require labels on realistic synthetic media. Obvious cartoons aren't covered | 20 | disclosure step (Phase 9) | ⏳ Phase 9 |
| G48 | ASCI: disclose brand deals upfront. Put "animated character" in the bio (virtual-influencer rule) | 18.1, 21 | Phase 1 bio, Phase 9 guard | ⏳ Phase 9 |
| G49 | YPP today: 1,000 subs + 4,000 h in 12 months or 10 M Shorts views in 90 days. From **1 Feb 2027**, new applicants need 8,000 h in 365 days or 20 M Shorts views in 90 days, and earning from the Shorts pool each month needs 10 M views over the last 90 days | 19 | Phases 10–11 | ✅ YouTube Help (answer 12843009) |
| G50 | No Instagram per-view pay in India (Reels Play ended 9 Mar 2023). Gifts eligibility varies. GST registration for services above ₹20 lakh (₹10 lakh in special-category states) | 19, 21 | Phase 11 checklists | ⏳ not re-verified; re-check in Phase 11 |

## Stale, unverified, or new findings

- **Blender 5.2.2 LTS** is confirmed as the current LTS (checksum files dated 15 Sept 2026 on two
  official mirrors). The latest **4.5 LTS** for Intel Macs is **4.5.14**. Both are pinned in
  `scripts/versions.env`.
- **CapCut**: confirmed still missing from India's App Store (applecensorship.com monitor). Its
  formal legal status is debated online, but for practical purposes it's unavailable. Ignore it.
- **The guide doesn't mention these (found while testing):**
  - `download.blender.org` blocks scripted downloads with a bot challenge, so setup uses official mirrors and verifies SHA-256.
  - Blender 5.2 renamed the EEVEE engine id back to `BLENDER_EEVEE` (4.2–4.5 used `BLENDER_EEVEE_NEXT`).
  - In background mode the engine enum lists only one engine, so `compat.resolve_engine()` tries each id instead of reading the list.
  - `Material.use_nodes` is deprecated in 5.2 (to be removed in 6.0), so `compat.new_material()` avoids it.
  - Blender 5.2 bundles Python 3.13.
- **EEVEE does run headless without a GPU** (through Mesa's EGL + llvmpipe, or Vulkan + lavapipe)
  with no X server or xvfb needed. It's slow; numbers are in `docs/RENDER_ENVIRONMENT.md`.
- **Broken relative links in the guide:** `2026-solo-builder-economics.md` lives in
  `purvammm/Personal-Finance` under `research/`, not in this repo. The guide is kept verbatim, so
  this is just noted here.
- **"5.2 LTS adds online asset libraries"** (§3.4): unverified, and nothing depends on it.
- **Money and policy facts** (G08, G09, G18, G46–G48, G50) are only as current as the guide. Per
  the working agreement, each is re-checked in the phase that acts on it.
