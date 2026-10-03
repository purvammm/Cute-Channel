# 003 · The world: the kitchen windowsill

**Status:** decided · **Date:** 2 Oct 2026 · Guide §7.1, §12.4, §17.1

## Decision

Chuski and Shakkar live on **a kitchen windowsill in a small Indian flat**, with rain often on the
window. It's tiny, cosy and cheap to build.

- **Cyclorama colour:** `monsoon` **#CFE3F2**, a cool powder blue that contrasts with Chuski's
  warm peach (§9.3: contrasting pastel background).
- **Reusable props.** All are scripted from primitives in Phase 5, so there are no third-party
  assets and no licence risk:
  1. **Cutting-chai glass**: a short, faceted tumbler. Chuski's home, bed and bathtub.
  2. **Saucer**: a cream disc. The stage, a puddle pool, a hiding place.
  3. **Sugar jar**: a glass jar of cubes. Shakkar's "apartment building" and a hide-and-seek arena.
  4. **Steel spoon**: a funhouse mirror, a seesaw, a stirring tornado.
  5. **Money plant in a bottle**: the window's green, and a hiding spot.
- **Occasional guests** (built when an episode needs them): microwave (the villain), saucepan
  (boil-overs), kettle, phone, laptop.

## Why

- One small world keeps every episode recognisable by colour and setting (§9.3, §1 pattern 6).
- Rain on the window makes monsoon, the most Indian chai moment, available all year.
- Everything is simple geometry, so `build_studio.py` can make it in seconds and the props cost
  nothing to render.
