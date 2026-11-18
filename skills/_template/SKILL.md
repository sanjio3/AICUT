---
name: aicut-<NAME>
description: >-
  TODO one sentence on what this effect does and when a user would want it.
  This skill should be used when the user asks for <NAME>, e.g. the user says
  "TODO trigger phrase 1" or "TODO trigger phrase 2". The tunable parameter
  table must be reported before rendering, and the user confirms before
  anything is rendered.
version: 0.1.0
api_version: 1
uses: [_geom]
agent_created: true
allowed-tools: Bash, Read, Write, Edit
triggers: ["TODO trigger 1", "TODO trigger 2"]
---

# <NAME>

TODO describe the visual result, the part of a cut it suits and any material
it needs, in two or three sentences. Do not write a tutorial; say what the
viewer sees.

## When to use

Load this skill when the user says any of the words in `triggers`, or when
their request matches this effect. Load only this directory, do not read the
other skills.

## How to use

1. Run every command from the AICUT repository root (`$AICUT_ROOT`). Start
   with `python aicut.py params --effect <NAME>` and report the parameter
   table to the user: current value, range, affected metrics, side effects.
2. After the user answers, write the effect name into the switch that
   actually enables it: `python aicut.py plan --run <id> --effects <NAME>`.
3. `python aicut.py render --run <id>` to render, then
   `python aicut.py qa --run <id>` for the metrics.
4. Parameter details live in `references/params.yaml`, version limits and
   acceptance thresholds in `references/pitfalls.md`.

## Parameter table to report before rendering

TODO list the knobs this effect exposes, their defaults, ranges and the
metrics each one affects. Run `python aicut.py params --effect <NAME>` for the
merged current values and report them one by one. Use defaults only when the
user has not stated a preference.

## Acceptance

TODO state which metrics in `qa.json` matter for this effect and their
thresholds. At least one brightness metric and one sharpness metric. Run
`python aicut.py qa --run <id>` once and fill in the measured numbers.

## Known pitfalls

TODO write the ffmpeg version limits, the material requirements and the easy
mistakes. Write "none" if there are none. Global limits live in
`lib/doctor.py`; do not guess from memory what a machine supports.

## Current implementation boundary

TODO state which parameters do not take effect yet, which visual results are
not implemented and how this differs from the reference cut. This section must
not be left empty, and a simplified implementation must never be described as
a complete one, because the next person reads this file to decide whether it
can be reused.
