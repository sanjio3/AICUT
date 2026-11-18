## AICUT 0.4.0

Beat-synced, effects-driven video editing for AI agents. An agent that has
this skill asks how you want the cut, reports the tunable parameters, renders
only the shots that actually changed, and hands back the metrics that moved.

### What is in this release

Three skill packages, each a self-contained archive:

| Package | What it does |
|---|---|
| `aicut-fire-transition-market.zip` | Flame overlay snapped to the beat, base plate dimmed |
| `aicut-manga-split-market.zip` | Four offset comic panels with cross dividers |
| `aicut-ending-dissolve-market.zip` | Two blur strengths blended for a continuous soft ending |

Each archive holds the skill and the runtime it needs, so it runs after
unpacking with nothing else installed. The layout is the one the marketplace
uses: a folder named after the skill, with `SKILL.md` inside it.

### Install

Unpack an archive and point the agent at the folder, or upload the archive to
a skill marketplace. Python 3.9 or newer and an `ffmpeg` executable are the
only requirements. There is no media to supply: `prepare` generates synthetic
demo clips when the materials directory is empty.

```
python aicut.py prepare
python aicut.py plan --run mycut --effects fire-transition --duration 6
python aicut.py confirm --run mycut --hash <hash printed by plan>
python aicut.py render --run mycut
python aicut.py qa --run mycut
```

### Rendering waits for you

`render` refuses to run without a confirmation whose hash still matches the
plan, so a cut is never produced that nobody asked for. `plan` prints the
questions and the hash; `confirm` records the answer.

### Notes for this release

- The three effects are contract-complete and reproducible. They are not a
  pixel-level recreation of the reference cut: text baking, irregular masks,
  onomatopoeia layout and the cross-dissolve sequence are not migrated yet.
  Each package states its own boundary.
- Media is not distributed here. You supply your own footage and music.
