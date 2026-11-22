# crt-scanline — parameters and pitfalls

This file is the detailed version of SKILL.md, for the agent or developer who
needs to tune parameters deeply or change the implementation. SKILL.md only
covers when to use the skill and how; the detail lives here.

## Parameter table

Consistent with `python aicut.py params --effect crt-scanline`.

| key | default | range | step | affects | side effect |
|---|---|---|---|---|---|
| `line_gap` | 6 | 3–12 | 1 | `laplacian_var`, `dark_pct` | Below 3px the lines cause moire and `laplacian_var` is inflated; larger gaps make the CRT look coarse. |
| `line_alpha` | 0.25 | 0.10–0.7 | 0.05 | `V`, `dark_pct` | The default 0.25 is faint. From 0.4 up the lines are obvious but the whole frame is visibly darkened (V drops ~16 at 0.25, ~22–23 at 0.38); dark material is risky. |
| `scan_speed` | 300 | 60–600 | 20 | `dup_pct`, `motion_p50` | Below 60 the band barely moves between frames and `dup_pct` rises; above 600 it reads as a flicker rather than a sweep. |

Hardcoded, not tunable: line thickness 2px, band height `BAND_H = 20` (2.8% at
720p, under 3%), band white alpha 0.14, `eq` contrast 1.06 / saturation 1.12 /
brightness 0.01, output `yuv420p`. `brightness` is a tiny compensation so the
dark lines do not push V under the gate; it is never raised to fake V, which
would turn CRT blacks grey. Changing it is not exposed as a parameter.

## Acceptance thresholds

Follow the metric names in `lib/qa.py`; global gates live in the root
`params.yaml` and are not changed by this skill.

- Brightness: `V` 100–160, `dark_pct < 2.0`, `bright_pct < 8.0`.
- Motion/duplication: `dup_pct < 6.0`.
- Sharpness: `laplacian_var` must be not below 80% and not above 250% of the
  same-material no-effect baseline (`--effects base`). Above 250% means the
  lines are too dense or too dark: lower `line_alpha` first, then `line_gap`.
  A one-sided lower bound is useless here because scanlines push the metric up.
- Always report the triple "no-effect baseline V / effected V / drop" — the
  effected V alone cannot show whether the frame was darkened too far.

Measured with `brightness` fixed at 0.01:

| run | baseline V | effected V | drop | dark_pct | bright_pct | dup_pct | laplacian_var (baseline, share) | gate |
|---|---|---|---|---|---|---|---|---|
| `demo` (3s / 72 frames, `line_alpha=0.25`) | 123.01 (`demo-base`) | 106.77 | 16.24 | 0.00% | 0.00% | 0.00% | 1757.0 (1430.0, 122.9%) | PASS |
| `demo-long` (9s / 216 frames, `line_alpha=0.25`) | 126.78 (`demo-long-base`) | 110.08 | 16.70 | 0.00% | 0.00% | 7.44% | 1353.6 (947.1, 142.9%) | WARN |

Both runs sit inside the 80%–250% `laplacian_var` band. The `demo-long` WARN
is `dup_pct=7.44 exceeds dup_pct_max=6.00`; the no-effect control
`demo-long-base` is 7.91%, so repeated frames come from the material/pool
rather than this effect, and no global gate was changed for it.

## Known pitfalls

- `drawbox` has no frame-number variable `n`; using `n` raises
  `Undefined constant`. Its Y position must use the time expression `t`, e.g.
  `y='mod(t*300,ih-20)'`.
- The comma inside an expression must be wrapped in single quotes around the
  whole expression; backslash escaping is not reliable inside `filter_complex`.
- Keep line gap at or above 3px or moire appears; keep the band height at or
  below 3% of the frame height (hardcoded 20px here).
- The band Y uses `mod(t*speed,ih-20)` rather than `mod(t*speed,ih)`, otherwise
  the band is clipped by the frame edge at the bottom of its travel.
- Use only legacy filters (`drawgrid`, `drawbox`, `eq`, `format`) for 2018
  build compatibility. `zoompan` creates duplicate frames and
  `blend all_mode=screen` raises U/V and tints the frame purple — neither is
  used here.
- Each filter was checked against `ffmpeg -h filter=<name>` before use. Local
  9.1 parameter names match the older build for these filters; that does not
  make newer filters safe to add.
- Scanlines artificially raise `laplacian_var`, so it cannot judge sharpness
  on its own in this effect — it is mostly a proxy for line density and line
  strength.
- At the current default `line_alpha=0.25` this effect drops V by about 16
  (demo-base 123.01 → demo 106.77). If the baseline V is below roughly 123,
  lower `line_alpha` in advance or the result approaches the 100 gate. Run a
  no-effect control to read V before putting dark material into the cut.

## Current implementation boundary

Only horizontal scanlines and one constant-speed bright band; no phosphor
triad dots, no vertical lines, no barrel distortion, no random rolling jitter.
At the default `line_alpha=0.25` the lines are faint on dark material: in a
dark backdrop they are only barely visible and are mostly read via highlights
and faces. That is a deliberate default trade-off and alpha was not raised
back for it. Band colour, alpha, height and line thickness are hardcoded and
do not follow the three tunable parameters; `eq` contrast 1.06, saturation
1.12 and brightness 0.01 are fixed, and `brightness` takes no parameter. It
reads neither `_assets` nor `_overlays`, `extra_inputs` is always empty, and
there is no material-level overlay at all. The band is not aligned to beats
and there is no per-shot variation. The no-effect baseline must be measured
separately with a `--effects base` run.
