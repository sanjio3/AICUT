---
name: aicut-manga-split
display_name: "漫画分格"
display_name_en: "Comic panel split"
description: >-
  Comic panel split effect: cuts one shot into four offset panels and draws
  white cross dividers, two panels desaturated and two highly saturated, for a
  comic panel contrast. This skill should be used when the user asks for
  漫画分格 / 漫画分屏 / 分镜 / manga split / comic panel split / four panel /
  manga panels / comic cut, or wants the frame cut into blocks. The tunable
  parameter table must be reported before rendering.
version: 0.1.0
api_version: 1
uses: [_geom]
agent_created: true
allowed-tools: Bash, Read, Write, Edit
triggers: ["漫画分格", "漫画分屏", "分镜", "manga split", "comic panel split", "four panel", "manga panels", "comic cut", "panel grid"]
---

# Comic panel split

A regular four-panel split. `split=4` produces four streams, each cropped to a
slightly offset region. Cropping the original quadrants and putting them back
in place would restore the original geometry exactly, leaving only a colour
difference that the eye cannot read as a split, so the offsets are essential.
Two panels are desaturated, two are boosted, and white cross dividers are
drawn on top.

## When to use

Load this skill when the user says any of the words in `triggers`, or asks for
the frame to be cut into blocks with a comic panel feel. Load only this
directory.

## How to use

1. Run every command from the AICUT repository root (`$AICUT_ROOT`). Start
   with `python aicut.py params --effect manga-split` and report the parameter
   table to the user.
2. After the user answers: `python aicut.py plan --run <id> --effects manga-split`.
3. `python aicut.py render --run <id>` to render, then `python aicut.py qa --run <id>`
   for the metrics.
4. Details live in `references/pitfalls.md`.

## Parameter table to report before rendering

- `cells` is locked at 4; the current implementation only does regular four panels.
- `mono_sat` defaults to 0.05, range 0–1, saturation of the black and white
  panels, affects V and laplacian_var.
- `color_sat` defaults to 1.40, range 0.5–2.5, saturation of the colour panels,
  affects V.
- `contrast` defaults to 1.25, range 0.9–2.0, contrast shared by all panels,
  affects V and dark_pct.
- `beat_align` defaults to on, consumed by `lib/plan.py`.

## Acceptance

`V` should not swing wildly because of the two-tone contrast, `dark_pct < 2%`
(the black and white panels can go too dark), and a higher `laplacian_var` is
expected because of the dividers. The dividers must be visible: pull one frame
and look at it.

## Known pitfalls

After `split=4` each of the four streams must be cropped to `w//2 x h//2`
before `hstack`/`vstack`, otherwise the sizes do not match and the filter
fails. The offset must stay below half a panel or the crop reaches past the
edge and leaves a black border. See `references/pitfalls.md`.

## Current implementation boundary

Regular four panels only. The irregular slanted mask and randomised panel
shapes from the reference cut are not migrated; those need a pre-generated mask
sequence or dynamic masks with `maskedmerge`, which is the next stage. The
lock on `cells` exists precisely because of that limit.
