# AICUT

**Beat-synced, effects-driven video editing for AI agents.**

You say "add a fire transition". The agent loads that effect's self-contained
skill, reports the tunable parameter table *before* rendering, and asks how you
want the cut. After you answer, it renders only the shots that actually
changed and reports the metrics that moved.

[中文文档](README.zh-CN.md)

AICUT is a skill, not a video editor. There is no frontend, no backend, no
port and no daemon. The repository root is the skill root: put it on the
agent's skill search path and it works. The host agent is the runtime, ffmpeg
produces the pixels.

> AICUT gives an AI assistant beat-synced, effect-driven AMV editing ability.
> Name an effect, the agent loads that effect's skill, asks how you want the
> cut, renders only the affected shots, then reports a QA diff.

## Result

![Key frames from the AICUT demo cut](docs/demo/keyframes.jpg)

[▶ Full demo cut: 48 seconds, 720p, 16 MB](docs/demo/aicut-demo-48s.mp4)

This is what iterating on the method produced: an opening white frame that
embeds the next clip for a delayed transition, comic panels with the
onomatopoeia pushed into the corners from 16 seconds in, and a closing section
that blurs and dims continuously, with brief flashes only on the beat.

To be precise about what this is: the demo comes from the hand-iterated
rendering script that came before AICUT (v30). AICUT is migrating that visual
core into reusable effects one at a time. The three effects in this repository
are contract-complete, independently callable and reproducible simplified
implementations, not a pixel-level recreation of that cut. The gap is listed
under "Current status" at the end.

## What a session looks like

```
you    : cut this track into a hype edit with a fire transition
agent  : matched fire-transition, reporting 8 knobs (current / range / what
         it affects) and asking which effects, how long and which part of the
         music to follow
you    : dim the fire a bit, speed the transitions up
agent  : plan reorders -> render re-renders the 4 affected shots -> qa ->
         reports the metric diff
```

As commands:

```
python aicut.py catalog --say "add a fire transition and some comic panels"
python aicut.py params  --effect fire-transition
python aicut.py plan    --run r1 --effects fire-transition,base --set fire-transition.flame_gain=2.2
python aicut.py confirm --run r1 --hash <hash from plan>
python aicut.py render  --run r1
python aicut.py qa      --run r1
```

`catalog` only maps the user's wording to an effect. What actually decides
which effects a cut uses is `selection.effects`: name a few and only those
rotate, nothing else sneaks in.

**AICUT does not render until you approve the cut.** `render` refuses to run
without a confirmation record whose hash still matches the plan. The agent
cannot skip the conversation, because it would have to invent a hash, and an
invented hash does not match the plan on disk.

## Capabilities

**Automatic beat detection.** `prepare` detects onsets with three-band spectral
flux (low 30–160 Hz, mid 160–1200 Hz, high 1200–7000 Hz), estimates tempo by
autocorrelation and refines the phase with grid scoring. Downbeats follow the
low frequency energy in 4/4, and section boundaries come from changes in RMS
and spectral centroid. It only needs numpy and ffmpeg, no librosa. Without a
background track it falls back to an equal-tempered grid plus
`project.bpm_fallback`: less precise, but the pipeline keeps running.

**Media preprocessing, no manual steps.** `prepare` scans the video directory,
samples each clip at seven points for duration, frame rate and average
brightness, then scans the whole clip for dark spans. Overlay material is
discovered automatically. Everything lands in `runs/_cache/assets.json`, and
`Pool` plus the effects reuse it instead of reopening files.

**Attributable parameters.** Every knob declares `default / min / max / step /
affects / note`, and `params` prints sliders, enums and locked values
differently. "The fire is too dark" maps through the `attribution` table to
`fire-transition.flame_gain` instead of the agent guessing. The table carries
both English and Chinese phrases, so either language works.

**Incremental rendering.** Each shot renders on its own and is then
concatenated, so a failed shot can be re-rendered alone. The per-shot cache is
named by a content hash and lives in `runs/_cache/shots/`. The key covers the
source segment, the speed, the effect name and its parameters, the ffmpeg
capability hash and the skill code hash, so changing one knob only
invalidates the shots that use it.

**Acceptance metrics.** Per-frame statistics at 320×180: mean brightness, dark
frame share, blown-out share, duplicate frames, cut rate, motion percentiles,
Laplacian variance and repeat ratio. The gate compares them against the
thresholds in `params.yaml` and reports PASS or WARN. WARN only warns: whether
the result actually looks good is a human judgement, not something a script
should decide for you.

## Quick start

```bash
git clone https://github.com/sanjio3/AICUT.git
cd AICUT
python -m pip install -r requirements.txt
python aicut.py install          # install the skills into ~/.workbuddy/skills
```

You need Python 3.9 or newer and an ffmpeg executable on `PATH` (or set
`AICUT_FFMPEG`). Nothing else. There is no media to supply: `prepare`
generates synthetic demo clips when the materials directory is empty, so the
first run produces a picture.

To use your own material, point `params.yaml` at it or export the environment
variables:

| Variable | Points at |
|---|---|
| `AICUT_FFMPEG` | the ffmpeg executable |
| `AICUT_VIDEOS` | the directory with your video clips |
| `AICUT_OVERLAYS` | the directory with overlay material such as fire |
| `AICUT_BGM` | the background music file |
| `AICUT_MUSIC_JSON` | a pre-analysed music JSON (optional) |

Then run the pipeline:

```bash
python aicut.py prepare
python aicut.py plan --run mycut --effects fire-transition,base --duration 6
python aicut.py confirm --run mycut --hash <hash printed by plan>
python aicut.py render --run mycut
python aicut.py qa --run mycut
```

## Effects

| Skill | What it does | Trigger phrases |
|---|---|---|
| `fire-transition` | Flame overlay snapped to the beat, base plate dimmed | 火焰转场, 燃烧转场, fire transition, fire wipe, burning transition |
| `manga-split` | Four offset comic panels with cross dividers | 漫画分格, 漫画分屏, 分镜, manga split, comic panel split, four panel |
| `ending-dissolve` | Two blur strengths blended for a continuous soft ending | 结尾溶解, 结尾模糊, ending dissolve, soft fade out, ending blur, dreamy outro |

Each effect is a standard skill:

```
skills/<name>/
├── SKILL.md                frontmatter, when to use, required sections
├── scripts/build.py        build(shot, params, caps), a pure function
└── references/
    ├── params.yaml         tunable knobs, machine readable
    └── pitfalls.md         parameters, thresholds, pitfalls, boundaries
```

The host routes by reading the `description` of each skill. `triggers` is an
optional accelerator, not the runtime router.

Adding an effect:

```bash
python aicut.py new-effect my-effect
python aicut.py validate-effect my-effect   # contract check, no render
python aicut.py catalog                      # confirm it is discoverable
python aicut.py package --effect my-effect   # build a distributable zip
```

## Repository layout

- `SKILL.md` the single entry point: the workflow, the command reference and the global pitfalls.
- `params.yaml` the only file users need to edit: paths, global knobs, the attribution table, gate thresholds.
- `skills/<name>/` one standard skill per effect.
- `install.py` installs `skills/` into a path the host scans.
- `lib/` the stateless kernel: `beat.py` beat detection, `assets.py` preprocessing, `plan.py` decisions, `render.py` rendering and caching, `qa.py` metrics, `confirm.py` the render gate, `package.py` archives.
- `runs/<id>/` a snapshot per run, append-only, for diff replay; `runs/_cache/shots/` is the cache shared across runs.
- `tests/smoke.py` a zero-dependency baseline, no pytest, no media, no ffmpeg needed.
- `examples/make_demo_assets.py` generates the synthetic demo clips.
- `.github/` issue and pull request templates, CODEOWNERS, CI.

## Design constraints

Time is recorded in floating point seconds throughout; the conversion to
frames happens only at the last step of rendering. Every `scripts/build.py` is
a pure function that neither writes to disk nor starts a process:

```
build(shot, params, caps) -> (extra_inputs, filter_chain_lines)
```

The base chain input is always labelled `[g]`, extra inputs are numbered from
1, and the last line must output `[out]`. Paths always come from
`params["_overlays"]` / `["_assets"]` / `["_geom"]`; a skill never reads global
config and never looks for files on its own. That contract is what lets each
effect be unit tested, replaced and developed independently.

## Reproducibility boundary

`plan.json` + `effective.yaml` + a fixed material pool seed + the ffmpeg
capability hash + the skill code hash guarantee that **on one machine** every
shot is reproducible: same machine, same material, same parameters, same
result.

Across machines only the rhythm and the parameters can be reproduced, not the
pixels. Material, background music, fonts and the ffmpeg binary are not
distributed with the repository, both because of licensing and because they
should be supplied by the user. The repository packages none of this,
`LICENSE` covers only the code in this repository, and third-party notices are
in `NOTICE`.

## Current status

0.4.0 turns the effects into standard skills and puts the conversation back
into the workflow:

- Every effect is a standard skill with native frontmatter, a `scripts/`
  directory and a `references/` directory. The host loads them by description.
- Rendering is gated on a user confirmation whose hash matches the plan, so an
  agent cannot quietly produce a video nobody asked for.
- A fresh clone produces a result with no media at all: `prepare` generates
  synthetic demo clips.
- All built-in prompts, CLI output and documentation are in English. Chinese
  trigger phrases are kept so Chinese users are matched too.
- `package` builds a marketplace-ready zip per skill, and CI runs the smoke
  test, the contract check and the packaging on every pull request.

The 48 second reference chain measured 138 shots, 104 beats and 48.04
seconds, with 5.3% dark frames, 1.6% duplicate frames and 4.31 cuts per
second. The sample-grade visual core is not migrated yet: text baking,
irregular slanted masks, onomatopoeia layout, the 96-frame cross-dissolve
sequence and the freeze-flash lightning are still in the older rendering
script, and reproducing the reference cut one to one is the next hard
acceptance line.

## Contributing

Contributions do not require you to be able to write code: collecting effect
references, breaking effects into parameters, running the validation and
writing down pitfalls are all real work. The project is developed in the open
with a review culture: `main` only accepts pull requests, and every change
has to pass CI.

See `CONTRIBUTING.md` for the division of work, branch naming and the commit
sequence.

## License

The code is under `LICENSE`. `NOTICE` lists how ffmpeg is invoked, the origin
and relicensing status of `lib/beat.py`, and why media is not distributed.
Confirm third-party media licensing yourself before publishing derivatives.
