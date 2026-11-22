---
name: aicut-crt-scanline
display_name: "老电视扫描线"
display_name_en: "CRT scanline"
description: "CRT scanline effect: overlays fine horizontal dark scanlines across the whole frame and sweeps one soft bright band from top to bottom at a constant speed, with a mild contrast and saturation lift, for a CRT / old VHS / surveillance monitor look. This skill should be used when the user asks for 老电视 / 扫描线 / CRT / 复古电视 / 录像带质感 / 监控画面 / crt scanline / retro tv / scan lines. The tunable parameter table must be reported before rendering, and the user confirms before anything is rendered."
description_zh: "老电视扫描线特效：整幅画面铺上细密横向暗扫描线，一条柔和亮带自上而下匀速扫过，配合轻度对比度与饱和度提升，做出 CRT / 老录像带 / 监控屏观感。当用户说老电视、扫描线、CRT、复古电视、录像带质感、监控画面、crt scanline、retro tv、scan lines 时使用。渲染前必须回传可调参数表，用户确认后才渲染。"
version: 0.1.0
author: Haaan327
api_version: 1
uses: []
agent_created: true
allowed-tools: Bash, Read, Write, Edit
triggers: ["老电视", "扫描线", "CRT", "复古电视", "录像带质感", "监控画面", "crt scanline", "retro tv", "scan lines"]
---

# CRT scanline

A pure-filter effect: fine dark horizontal lines cover the frame while one
semi-transparent white band travels from top to bottom at a fixed speed, with
a small contrast/saturation lift. No overlay or audio material is read;
`extra_inputs` is always empty.

## When to use

Load this skill when the user says any of the words in `triggers`, or when
their request matches this effect. Load only this directory, do not read the
other skills.

## How to use

1. Run every command from the AICUT repository root (`$AICUT_ROOT`). Start
   with `python aicut.py params --effect crt-scanline` and report the parameter
   table to the user: current value, range, affected metrics, side effects.
2. After the user answers, write the effect name into the switch that
   actually enables it: `python aicut.py plan --run <id> --effects crt-scanline`.
3. `python aicut.py render --run <id>` to render, then
   `python aicut.py qa --run <id>` for the metrics.
4. Parameter meanings, acceptance thresholds, pitfalls and boundaries live in
   `references/pitfalls.md`; knob definitions live in `references/params.yaml`.

## Parameter table to report before rendering

Execute `python aicut.py params --effect crt-scanline` to get the merged
current values and report each one: current value, range, affected metrics,
side effects. Use defaults only when the user has not stated a preference.

- `line_gap` defaults to 6, range 3–12, step 1, affects `laplacian_var` /
  `dark_pct`. Below 3px the lines cause moire and inflate `laplacian_var`.
- `line_alpha` defaults to 0.25, range 0.10–0.7, step 0.05, affects `V` /
  `dark_pct`. The default looks faint; above 0.4 the lines are obvious but the
  frame is visibly darkened, so be careful on dark material.
- `scan_speed` defaults to 300, range 60–600, step 20, affects `dup_pct` /
  `motion_p50`. Below 60 the band moves too little between frames and
  `dup_pct` rises.

Hardcoded, not tunable: line thickness 2px, band height 20px (2.8% at 720p,
under 3% of frame height), band white alpha 0.14, `eq` contrast 1.06 /
saturation 1.12 / brightness 0.01 (a tiny compensation only; never used to
fake the V metric, so CRT blacks stay black), output `yuv420p`.

## Acceptance

After rendering run `python aicut.py qa --run <id>`. At least one brightness
and one sharpness metric:

- Brightness: `V` 100–160, `dark_pct < 2.0`, `bright_pct < 8.0`.
- Motion/duplication: `dup_pct < 6.0`.
- Sharpness: `laplacian_var` is a two-sided band — not below 80% and not above
  250% of the same-material no-effect baseline. Above 250% means the lines are
  too dense or too dark: lower `line_alpha` first, then `line_gap`.
- Always report the triple "baseline V / effected V / drop"; the effected V
  alone cannot tell whether the effect darkened the frame too far.

Measured with `brightness` fixed at 0.01:

| run | baseline V | effected V | drop | dark_pct | bright_pct | dup_pct | laplacian_var (of baseline) | gate |
|---|---|---|---|---|---|---|---|---|
| `demo` (3s / 72 frames, `line_alpha=0.25`) | 123.01 (`demo-base`) | 106.77 | 16.24 (13.2%) | 0.00% | 0.00% | 0.00% | 1757.0 (1430.0, 122.9%) | PASS |
| `demo-long` (9s / 216 frames, `line_alpha=0.25`) | 126.78 (`demo-long-base`) | 110.08 | 16.70 (13.2%) | 0.00% | 0.00% | 7.44% | 1353.6 (947.1, 142.9%) | WARN |

Both `laplacian_var` values sit inside the 80%–250% band. The `demo-long`
WARN is `dup_pct=7.44 exceeds dup_pct_max=6.00`; the no-effect control
`demo-long-base` is 7.91%, so the repeated frames come from the material/pool
rather than this effect, and no global gate was changed for it.

## Known pitfalls

- `drawbox` has no frame-number variable `n`; its Y position must use the time
  expression `t`. Using `n` raises `Undefined constant`.
- The comma inside an expression must be wrapped in single quotes around the
  whole expression, e.g. `y='mod(t*300,ih-20)'`; backslash escaping is not
  reliable inside `filter_complex`.
- Keep line gap at or above 3px to avoid moire; keep the band at or below 3%
  of frame height (hardcoded 20px here).
- The band Y uses `mod(t*speed,ih-20)` rather than `mod(t*speed,ih)`, otherwise
  the band is clipped by the frame edge at the bottom of its travel.
- Use only legacy filters (`drawgrid`, `drawbox`, `eq`, `format`) for 2018
  build compatibility; do not use `zoompan` (creates duplicate frames) or
  `blend all_mode=screen` (raises U/V and tints the frame purple).
- Every filter was checked against `ffmpeg -h filter=<name>` before use. Local
  9.1 parameter names happen to match the older build; that does not make new
  filters safe.
- Scanlines artificially raise `laplacian_var`, so it cannot judge sharpness
  on its own here — it is mostly a proxy for line density and line strength.
- At the current default `line_alpha=0.25` the effect drops V by about 16
  (demo-base 123.01 → demo 106.77). When the baseline V is below roughly 123,
  lower `line_alpha` in advance or the result approaches the 100 gate. Run a
  no-effect control to read V before putting dark material into the cut.
- Full detail lives in `references/pitfalls.md`.

## Current implementation boundary

Only horizontal scanlines and one constant-speed bright band; no phosphor
triad dots, no vertical lines, no barrel distortion, no random rolling jitter.
At the default `line_alpha=0.25` the lines are faint on dark material: in a
dark backdrop they are only barely visible and are mostly read via highlights
and faces. That is a deliberate default trade-off and alpha was not raised
back for it. Band colour, alpha, height and line thickness are all hardcoded
and do not follow the three tunable parameters; `eq` contrast 1.06,
saturation 1.12 and brightness 0.01 are fixed, and `brightness` takes no
parameter. It reads neither `_assets` nor `_overlays`, `extra_inputs` is
always empty, and there is no material-level overlay at all. The band is not
aligned to beats and there is no per-shot variation. The no-effect baseline
must be measured separately with a `--effects base` run.
