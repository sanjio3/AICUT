# Fire transition — parameters and pitfalls

## Parameter table

| Knob | Default | Range | Affected metrics | Side effect |
|---|---|---|---|---|
| `clip` | fire01 | fire01 / fire02 | shape | Which of the fire overlays discovered by prepare to use |
| `trim_start` | 0.55 | 0–1.50 (step 0.05) | dark_pct | Where in the clip to start; too early lands on black frames |
| `base_dim` | 0.68 | 0.40–1.00 (step 0.02) | V, dark_pct | How much the base plate is dimmed; without it the flame does not read |
| `flame_gain` | 1.95 | 0.80–2.60 (step 0.05) | bright_pct | Above 2.4 it blows out easily |
| `chroma_mix` | 0.28 | 0–1 (step 0.02) | V | Share of the flame in the chroma planes; U/V only, no brightness change |
| `beat_align` | true | boolean | cut_rate | Consumed by `lib/plan.py`; decides whether cuts snap to beats |
| `hue` | 6.0 | locked | — | Rotating hue turns orange into purple, which stops reading as fire |

## Acceptance thresholds

- `bright_pct < 8%`: the flame gain blows out here first.
- `dark_pct < 2%`: triggered when `base_dim` dims too hard or `trim_start` lands on black frames.
- `V` between 100 and 160: overall brightness.
- `laplacian_var` as a sharpness reference; a slight rise after the flame is blended in is normal.

## Known pitfalls

- `blend all_mode=screen` raises the U/V planes as well and tints the whole frame; use per-plane `c0_expr` for luma and `c1_expr`/`c2_expr` for chroma.
- Do not rotate hue on fire shots, orange turns purple and stops reading as fire.
- Flame clips are often shorter than the shot, so `-stream_loop -1` is needed as a fallback, otherwise the last frame freezes.
- `trim_start=0.55` is the working start measured on the reference material; re-measure when the clip changes.
- The 2018 ffmpeg build has no `format` option on `overlay` and `gblur` only accepts a constant. Those limits live in `lib/doctor.py`, do not judge from memory.

## Current implementation boundary

Per-plane blending, clip rotation and full parameterisation. The HUD scan band, neon grid overlay and irregular mask from the reference cut are not migrated. When overlay material is missing, `scripts/build.py` degrades to a mild brightening: the pipeline keeps working but the effect is clearly weaker.
