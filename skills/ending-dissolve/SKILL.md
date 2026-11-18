---
name: aicut-ending-dissolve
description: >-
  Ending dissolve effect: mixes two blur strengths by a ratio to produce a
  continuously softening and dimming ending rather than a flickering one.
  This skill should be used when the user asks for 结尾溶解 / 结尾模糊 /
  收尾柔化 / ending dissolve / soft fade out / ending blur / dissolve ending /
  dreamy outro, or complains that the ending is too blurry or still
  flickering. The tunable parameter table must be reported before rendering.
version: 0.1.0
api_version: 1
uses: []
agent_created: true
allowed-tools: Bash, Read, Write, Edit
triggers: ["结尾溶解", "结尾模糊", "收尾柔化", "ending dissolve", "soft fade out", "ending blur", "dissolve ending", "dreamy outro", "结尾太糊"]
---

# Ending dissolve

An ending-only effect. `split=2` produces two streams, one lightly blurred and
dimmed, one heavily blurred, and they are blended by a keep/mix ratio. Both
streams are blurred, which is what makes the result continuously soft rather
than alternating between sharp and soft frames; `mix` controls how much of the
heavier blur is blended in.

## When to use

Load this skill when the user says any of the words in `triggers`, or asks for
a soft dissolve at the end of the cut. Load only this directory.

## How to use

1. Run every command from the AICUT repository root (`$AICUT_ROOT`). Start
   with `python aicut.py params --effect ending-dissolve` and report the
   parameter table.
2. After the user answers: `python aicut.py plan --run <id> --effects ending-dissolve`
   (usually together with `base`, in which case it only applies to the tail).
3. Render, then run `qa`. Watch `laplacian_var` dropping and `V` easing down
   without collapsing.

## Parameter table to report before rendering

- `gblur_sigma` defaults to 8 (global group), the range is in the root
  `params.yaml`, and it sets the base blur radius.
- `gamma` defaults to 0.68, range 0.40–1.00, the dimming factor, affects V and
  dark_pct.
- `mix` defaults to 0.28, range 0–0.60, the share of the second blur layer,
  affects motion_p90 and laplacian_var.

## Acceptance

`laplacian_var` should be clearly lower than in the body of the cut; `V`
drops a little but must not create large dark areas (`dark_pct < 2%`). Pull
several consecutive frames to confirm the blur is continuous rather than
alternating between sharp and soft.

## Known pitfalls

Use `blend all_expr` and not `all_mode=screen`, because the latter raises the
U/V planes and tints the frame. Both layers need `format=yuv420p` before they
are blended, otherwise the pixel formats do not match. See
`references/pitfalls.md`.

## Current implementation boundary

A parameterised double blur applied to the shots the planner assigns to this
effect, which is the tail of the cut. The 96-frame cross-dissolve sequence and
the continuous blur rhythm that changes every four frames from the reference
cut are not migrated; `dissolve_frames` is currently only recorded in
plan.json and does not drive the filter chain.
