---
name: aicut-fire-transition
description: >-
  Fire transition effect: overlays flame footage on top of the cut, snapped to
  the beat, with the base plate dimmed so the flame reads as the focal point.
  This skill should be used when the user asks for a 火焰转场 / 燃烧转场 /
  fire transition / fire wipe / burning transition, or complains that the fire
  is too dark or blown out. The tunable parameter table must be reported
  before rendering, and the user confirms before anything is rendered.
version: 0.1.0
api_version: 1
uses: [_geom, _assets, _overlays]
agent_created: true
allowed-tools: Bash, Read, Write, Edit
triggers: ["火焰转场", "燃烧转场", "fire transition", "fire wipe", "burning transition", "flame cut", "火焰太暗", "火焰过曝"]
---

# Fire transition

A shot-level transition effect: a flame clip is looped, mixed into the shot
with per-plane weighted blending, the base plate is dimmed by a factor and the
flame brightness is raised by a gain. Cut points are snapped to the nearest
beat by `lib/plan.py`.

## When to use

Load this skill when the user says any of the words in `triggers`, or asks for
a burning or flaming cut. Load only this directory.

## How to use

1. Run every command from the AICUT repository root (`$AICUT_ROOT`). Start
   with `python aicut.py params --effect fire-transition` and report the
   parameter table to the user: current value, range, affected metrics and
   side effects.
2. After the user answers, write the effect name into the switch that
   actually enables it: `python aicut.py plan --run <id> --effects fire-transition`.
3. `python aicut.py render --run <id>` to render, then `python aicut.py qa --run <id>`
   for the metrics.
4. Parameter meanings and acceptance thresholds live in
   `references/pitfalls.md`; the knob definitions live in `references/params.yaml`.

## Parameter table to report before rendering

Execute `python aicut.py params --effect fire-transition` to get the merged
current values and report each one: current value, range, affected metrics,
side effects. Use defaults only when the user has not stated a preference.

- `clip` defaults to fire01, options fire01 / fire02, decides the flame shape.
- `trim_start` defaults to 0.55s, range 0–1.5s, too early lands on black frames.
- `base_dim` defaults to 0.68, range 0.40–1.00, dims the base plate, mainly
  affects V and dark_pct.
- `flame_gain` defaults to 1.95, range 0.80–2.60, mainly affects bright_pct;
  above 2.4 it blows out easily.
- `chroma_mix` defaults to 0.28, changes only the U/V planes, not brightness.
- `beat_align` defaults to on, consumed by `lib/plan.py`; when off, cuts stop
  snapping to beats.
- `hue` is locked at 6°.

Precedence, highest first: per-shot override, this skill's
`references/params.yaml`, the global `params.yaml`, built-in defaults.
Adjusting `flame_gain` only invalidates the cache for shots whose effect is
fire-transition; every other shot is reused.

## Acceptance

After rendering run `python aicut.py qa --run <id>`. This effect cares about
`bright_pct < 8%`, `dark_pct < 2%` and `V` between 100 and 160; the global
gate thresholds are in the root `params.yaml`. After changing a parameter use
`python aicut.py diff --a <id1> --b <id2>` to report which keys changed and
how the metrics moved.

## Known pitfalls

See `references/pitfalls.md`. In short: `blend all_mode=screen` raises the U/V
planes as well and tints the whole frame purple, so use per-plane `c0_expr`
for luma and `c1_expr`/`c2_expr` for chroma. Do not rotate hue on fire shots,
orange turns purple. Use `-stream_loop -1` as a fallback because flame clips
are often shorter than the shot.

## Current implementation boundary

This is the runnable 0.1.0 implementation: per-plane blending, clip rotation
and full parameterisation. The HUD scan band, neon grid overlay and irregular
mask from the reference cut are not migrated. When overlay material is
missing, `scripts/build.py` degrades to a mild brightening so the pipeline
does not break, and the difference shows up in the QA `V` value.
