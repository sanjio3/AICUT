# Contributing

AICUT is distributed as a skill directory: the repository root is the skill
root. Before contributing, understand one boundary: the host agent is the
runtime. There is no service, no port, no frontend and no daemon in this
repository, so no new capability should introduce a second execution entry
point.

## Setting up locally

You need Python 3.9 or newer and a working ffmpeg executable. Install the
dependencies with `pip install -r requirements.txt`; the code only uses numpy,
opencv-python and PyYAML.

Copy `.env.example` to `.env` and fill in your local paths. `ff.load_config`
reads it automatically and `.env` is excluded by `.gitignore`. You can also
export the same environment variables directly; an existing process variable
wins over the file, so CI is never overridden by a local configuration.

You do not need any media. `python aicut.py prepare` generates synthetic demo
clips when the materials directory is empty. A background track is optional
too, `music.load` falls back to an equal-tempered grid. The shortest path
through the pipeline is `python aicut.py prepare`, then
`python aicut.py plan --run demo --effects fire-transition,base --duration 6`,
then `confirm`, `render` and `qa`. Any change should at least let those steps
run without an error, and
`python aicut.py diff --a <id1> --b <id2>` should show that a parameter change
is reported back.

Note that rendering requires a confirmed plan. `plan` prints a hash, the agent
has to put the questions to the user, and `python aicut.py confirm --run demo
--hash <hash>` records the approval. `render` refuses to run without it, and
that is deliberate: AICUT must not produce a video the user did not ask for.

## Division of work

The maintainer owns `lib/`, `aicut.py`, `install.py`, the root `SKILL.md`,
`params.yaml`, `tests/`, `examples/`, `.github/`, `NOTICE` and
`pyproject.toml`. Contributors work only inside the `skills/<name>/` directory
they claimed. Routing is done by the host reading each skill's `description`;
`triggers` is only an optional accelerator, so parallel work never collides on
a shared file. `.github/CODEOWNERS` turns this boundary into a review rule.

Effect tasks come in two tiers, decided by the maintainer in the issue. Tier A
is the parameter tier: change `references/params.yaml`, prepare the material
and write `SKILL.md` and `references/pitfalls.md`, while `scripts/build.py`
keeps the scaffold default. Tier B is the filter tier: it needs a
`filter_complex` chain, so `scripts/build.py` changes. Start with tier A.

## Branching and committing

`main` only accepts pull requests; nobody commits to `main` directly. The
maintainer should protect `main` in Settings → Branches with "Require a pull
request before merging" and "Require approvals 1".

Branch names carry a type prefix and a short description, for example
`feat/fire-transition`, `fix/manga-split-cell`, `docs/readme-demo`. Commit
messages use `type(scope): description`, where type is `feat` / `fix` / `docs`
/ `refactor` / `chore`, scope is the effect or module name, and the
description is one sentence in English or Chinese.

The full sequence, one step at a time, do not skip:

```
git switch main
git pull
git switch -c feat/your-effect
git status
git diff
git add skills/your-effect
git commit -m "feat(your-effect): describe what changed"
git push -u origin feat/your-effect
```

After the push, open the pull request from the Compare & pull request link on
the repository page and fill in the description from
`.github/PULL_REQUEST_TEMPLATE.md`. Once it is merged, tidy up locally:

```
git switch main
git pull
git branch -d feat/your-effect
```

When `git pull` reports a conflict, do not force it: run `git rebase --abort`
to get back to a clean state and ask the maintainer. Conflict handling is not
a required skill for a newcomer, so stop when you get stuck.

## Five steps for a newcomer

- Claim a task from the `.github/ISSUE_TEMPLATE/new-effect.md` card and
  confirm the tier, the trigger phrases, the material licensing and the
  acceptance metrics.
- Run `python aicut.py new-effect <name>` to scaffold the standard skill and
  replace the placeholders with real content.
- Fill in `triggers`, `references/params.yaml` and the four sections of
  SKILL.md: "Parameter table to report before rendering", "Acceptance",
  "Known pitfalls" and "Current implementation boundary". A missing section
  is caught by the self-check.
- Run `python aicut.py validate-effect <name>`, then `python aicut.py
  catalog` to confirm it is discoverable with no CONFLICTS, then
  `python tests/smoke.py`.
- Run `plan / confirm / render / qa` once, write the measured numbers back
  into the "Acceptance" section of SKILL.md, attach one pulled frame of the
  result and open the pull request.

`scripts/build.py` must export the pure function
`build(shot, params, caps) -> (extra_inputs, filter_chain_lines)`. It does not
write to disk, does not start processes and does not read global config. The
base chain outputs the label `[g]`, extra inputs are numbered from 1, and the
last line must output `[out]`. Paths and canvas size are injected by the
render layer as `params["_overlays"]`, `params["_assets"]` and
`params["_geom"]`; never assemble absolute paths yourself. `validate-effect`
calls `build()` once with a dummy shot, so a wrong signature, a wrong return
type or a missing `[out]` label is found immediately.

Every tunable key in `params.yaml` needs a `default`; if it has `min`/`max` it
also needs a `step`; `affects` must name a metric that `qa.py` really outputs;
and `note` has to describe the side effect, because the coupling between
parameters is worth more than the parameters themselves. Lock a key with
`locked: true`.

`fire-transition` is the reference implementation: its parameters, automatic
material discovery, pitfalls and boundaries are all complete, so learn the
structure from it. `manga-split` and `ending-dissolve` are simplified
implementations; the "Current implementation boundary" section of each states
which parameters do not take effect yet, so do not copy them as if they were
complete.

Do not modify `lib/` to make a single effect work. When an ffmpeg capability is
missing, open an issue instead; the maintainer records it in the capability
matrix in `lib/doctor.py` so every effect can share it.

## Before you submit

- `git status --porcelain` shows no rendered output, media, `.env` or
  `__pycache__` staged.
- `python tests/smoke.py` passes, and `python aicut.py validate-effect --all`
  reports every skill as PASS.
- `python -m compileall -q .` reports no syntax errors.
- No new code contains an absolute local path, a username or a private
  directory name.
- After changing a skill's `scripts/build.py` there is no need to clear the
  cache by hand, `shot_key` already includes the content hash of that file.
- If a new third-party dependency was introduced, update `requirements.txt`,
  `pyproject.toml` and `NOTICE`.

## About reproducing the reference cut

The full visual core (text baking, irregular slanted masks, onomatopoeia,
the 96-frame cross-dissolve sequence, freeze-flash lightning) has not been
migrated from the reference implementation yet. A cut produced before that
lands is a sample with a correct rhythm and effect pipeline, not a
pixel-level recreation. When you add visual capability, write in the
"Current implementation boundary" section of the effect which parameters do
not take effect yet, so users are not misled.
