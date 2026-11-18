# <NAME> — parameters and pitfalls

This file is the detailed version of SKILL.md, for the agent or developer who
needs to tune parameters deeply or change the implementation. SKILL.md only
covers when to use the skill and how; the detail lives here.

## Parameter table

TODO list every knob from `references/params.yaml`: name, default, range, the
qa metrics it affects and its side effect. Keep it consistent with the output
of `python aicut.py params --effect <NAME>`.

## Acceptance thresholds

TODO state the metrics this effect cares about and their sensible ranges.
Follow the metric names in `lib/qa.py`, and cover at least one brightness
metric (V / dark_pct / bright_pct) and one sharpness metric (laplacian_var /
motion_p90).

## Known pitfalls

TODO write the limits of the ffmpeg build in use, the material requirements
and the easy mistakes. Global limits live in `lib/doctor.py`.

## Current implementation boundary

TODO state which parameters do not take effect yet, which visual results are
not implemented and how this differs from the reference cut. Do not leave it
empty, and do not describe a simplified implementation as a complete one.
