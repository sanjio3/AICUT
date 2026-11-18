---
name: aicut
display_name: "AICUT — beat-synced video editing for AI agents"
description: >-
  AICUT gives an AI agent the ability to cut beat-synced, effects-driven video.
  This skill should be used when the user asks for an AMV, a beat-synced cut, a
  燃向 / 卡点 edit, a music-driven montage, or when they name a specific effect
  (fire transition, comic panel split, ending dissolve, scanline glitch) and want
  it applied to their footage.
  AICUT 会询问用户想怎么剪，确认后才渲染；每次出片都回传可调参数与验收指标。
  Use AICUT when the user wants an AI agent to plan, render and tune video
  edits that follow the beat. AICUT never renders without the user's
  confirmation of the cut.
description_zh: "卡点燃向剪辑插件：先问用户怎么剪 → 回传参数 → 用户确认 → 渲染 → 指标 diff"
description_en: "Beat-synced effect editing: ask the user how to cut, confirm, render, report metrics"
category: video
version: 0.4.0
agent_created: true
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# AICUT

AICUT is an agent skill, not an application. The host agent is the runtime:
there is no service, no port, no frontend, no daemon. The repository provides
three things — this entry point, the standard skills under `skills/`, and the
thin execution kernel under `lib/`.

## The one rule that matters

**Never render before the user has approved the cut.**

This is enforced in code, not just written here. `render` refuses to run
unless `plan.json` carries a confirmation record whose hash still matches the
current plan. The only way to produce that record is `aicut.py confirm`, which
needs the plan hash that `plan` printed. So the agent cannot skip the
conversation — it would have to invent a hash, and an invented hash does not
match the plan on disk.

The intended shape of every editing session:

```
propose  ->  ask  ->  wait for the answer  ->  confirm  ->  render  ->  report
```

If the user is terse ("just do it"), treat that as approval of the proposed
plan: still show the plan summary in one or two lines, then proceed. If the
user is specific, follow their answer exactly and record it with `--note`.

## Repository layout

```
skills/<name>/SKILL.md               standard skill: frontmatter + when to use
skills/<name>/scripts/build.py       build(shot, params, caps), a pure function
skills/<name>/references/params.yaml tunable knobs, machine readable
skills/<name>/references/pitfalls.md parameter table, thresholds, known limits
install.py                           installs skills/ into a host skills path
```

`skills/` is the source of truth; installing is a copy. `python install.py
--dry-run` shows where a skill would go, `python install.py` installs into
`~/.workbuddy/skills/`, and `--project <dir>` installs into
`<dir>/.workbuddy/skills/`.

## How effects get selected

**Routing is the host's job.** Each skill's `description` states when it
applies and the words a user would use. The host reads those descriptions and
decides which skill to load. `triggers` is an optional accelerator; when it is
missing, the words are derived from the description.

`python aicut.py catalog` lists the discoverable skills. `catalog --say "add a
fire transition"` is an offline simulation used to check that descriptions are
clear and that no two skills claim the same phrase. **It is not the runtime
router.**

Loading a skill does not enable it. Only names written into `selection.effects`
actually enter the rotation.

## Working with the user

Step 1 — find out what they have. Run `python aicut.py prepare`. It scans the
video directory for duration, frame rate, brightness and dark spans, discovers
overlay material, and analyses the background music for BPM, beats, downbeats
and section boundaries. If the user has no media yet, synthetic demo clips are
generated automatically so there is always something to work with. Then run
`python aicut.py doctor` to see which ffmpeg filters the host machine has.

Step 2 — propose. Ask the user, in their language, what they want: which
effects, how long, which part of the music to follow, and what look they do
not want. Use `python aicut.py params --effect <name>` to show the tunable
knobs with their current values, ranges, affected metrics and side effects.
Show the parameter table before rendering, not after.

Step 3 — plan. `python aicut.py plan --run <id> --effects <names>` writes
`plan.json` plus a confirmation block holding the questions still to be
answered and the plan hash. The command prints those questions and the hash.

Step 4 — confirm. Once the user has answered, record it:

```
python aicut.py confirm --run <id> --hash <hash> --note "<what the user decided>"
```

Step 5 — render. `python aicut.py render --run <id>`. Per-shot content-hash
caching means only the shots whose inputs actually changed are re-rendered.

Step 6 — report. `python aicut.py qa --run <id>` produces `qa.json` and the
per-second comparison sheet. `python aicut.py diff --a <id1> --b <id2>` shows
which keys changed and how the metrics moved. The gate only warns; it never
rolls back on its own. Whether the result looks right is the user's call.

If the user is not happy, go back to step 2. Adjusting a knob only invalidates
the shots that use that effect, so iterating is cheap.

## Command reference

Every command is invoked directly by the host agent. Nothing starts a service.
All paths expand through `${ENV:-default}` in `params.yaml`, so no absolute
local path is stored in the repository.

- `python aicut.py prepare` — scan media, discover overlays, analyse the music
- `python aicut.py doctor` — ffmpeg version and filter capability matrix
- `python aicut.py catalog [--say "..."]` — list discoverable skills
- `python aicut.py new-effect <name>` — scaffold a standard skill
- `python aicut.py validate-effect [--all]` — check skill contracts
- `python aicut.py params --effect <name>` — the tunable parameter table
- `python aicut.py plan --run <id> --effects <a,b>` — build a plan (not renderable yet)
- `python aicut.py confirm --run <id> --hash <hash>` — record the user's approval
- `python aicut.py render --run <id>` — render a confirmed plan
- `python aicut.py qa --run <id>` — metrics and gate verdict
- `python aicut.py diff --a <id1> --b <id2>` — parameter and metric diff
- `python aicut.py install [--dry-run] [--project <dir>] [--force]` — install skills
- `python aicut.py package --effect <name>` — build a distributable zip

## Mapping user language to parameters

The `attribution` section of `params.yaml` maps colloquial feedback to
parameter paths, in English and Chinese. When the user says "too shaky",
"too blurry", "too repetitive" or any equivalent, look the phrase up rather
than guessing. Every run stores `params.yaml`, `plan.json`, `qa.json` and
`feedback.yaml` under `runs/<id>/`, append-only, so the history is replayed
with `diff` instead of re-reading old logs.

Machine-specific pitfalls live in two places: global ffmpeg limitations in
`lib/doctor.py`, per-skill pitfalls in each `references/pitfalls.md`. Both feed
the render cache hash, so moving to a different machine invalidates the cache
automatically.

## Known limitations (global)

The ffmpeg build used during development has no `xfade` and no `gradients`;
`overlay` has no `format` option; `gblur` only accepts a constant sigma;
`rgbashift` has no `c` parameter, only `rh/rv/gh/gv/bh/bv/ah/av/edge`;
`blend all_mode=screen` raises the U/V planes as well and tints the whole frame
purple, so per-plane expressions are required; `zoompan` produces duplicate
frames. Trust `doctor` over memory.

## Current implementation boundary

The three built-in skills — fire-transition, manga-split, ending-dissolve — are
contract-complete, reproducible implementations, not pixel-level recreations of
the reference cut. Text baking, irregular masks, onomatopoeia layout, the
96-frame cross-dissolve sequence and the freeze-flash lightning are not
migrated yet. Each skill's `references/pitfalls.md` states its own gaps.
