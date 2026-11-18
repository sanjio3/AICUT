---
name: New or claimed effect
about: Collect and package a new editing effect as a standard skill under skills/<name>/
title: "[effect] "
labels: effect
assignees: ''
---

## Difficulty tier

The maintainer decides the tier, do not pick it yourself.

- **Tier A (parameter tier)**: only change `references/params.yaml`, prepare
  the material, and write `SKILL.md` and `references/pitfalls.md`.
  `scripts/build.py` keeps the default implementation from the template.
  Suitable for someone who has just started.
- **Tier B (filter tier)**: requires writing a `filter_complex` chain, so
  `scripts/build.py` changes. Confirm with the maintainer before starting.

## Basic information

- Effect name (lowercase English with hyphens, for example `sparkle-cut`):
- How a user would ask for it (list 2 to 5 trigger phrases, in English and in
  Chinese):
- Where the reference comes from (link / file name / timecode):
- Which part of a cut it suits (opening / verse / chorus / ending / whole):
- Whether the effect needs any overlay material:

## Parameter draft

Run `python aicut.py new-effect <name>` to scaffold the standard skill first,
then fill this in.

- How many knobs to expose (3 to 7 is a good number, the rest go into presets):
- The default, range and affected `qa.json` metric of each knob:
- Any locked values, and why they are locked:

## Acceptance

- [ ] `python aicut.py validate-effect <name>` reports PASS
- [ ] `python aicut.py catalog` shows the new effect with no CONFLICTS
- [ ] `python aicut.py install --dry-run` lists it
- [ ] `python aicut.py package --effect <name>` produces a valid archive
- [ ] `python tests/smoke.py` passes
- [ ] `plan / render / qa` was run once and the measured numbers are written
      into the "Acceptance" section of SKILL.md
- [ ] The "Known pitfalls" and "Current implementation boundary" sections are
      honest, and no simplified implementation is described as a complete one
- [ ] A screenshot or a pulled frame of the result is attached

## Boundaries

Only change files under `skills/<name>/`. Do not change `lib/`, `SKILL.md`,
`params.yaml`, `pyproject.toml` or another contributor's skill directory. If
the kernel really has to change, open a separate issue for the maintainer.

Contributor:
