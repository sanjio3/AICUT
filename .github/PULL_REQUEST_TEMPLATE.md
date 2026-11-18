## What this changes

One sentence about what changed, with the related issue number.

## Checklist before submitting

- [ ] `python aicut.py validate-effect <name>` reports PASS
- [ ] `python aicut.py catalog` has no CONFLICTS and the new effect is listed
- [ ] `python aicut.py install --dry-run` shows it
- [ ] `python aicut.py package --effect <name>` produces a valid archive
- [ ] `python tests/smoke.py` passes
- [ ] `python -m compileall -q .` reports no syntax errors
- [ ] Only files under `skills/<name>/` changed. If `lib/`, `SKILL.md` or
      `params.yaml` had to change, explain why below and tag the maintainer
- [ ] SKILL.md has the four required sections (Parameter table to report before
      rendering / Acceptance / Known pitfalls / Current implementation
      boundary), with the measured numbers filled into "Acceptance"
- [ ] Every key in `references/params.yaml` has a `default`, has a `step`
      whenever it has `min`/`max`, and its `note` describes the side effect
- [ ] `references/pitfalls.md` is filled in and no TODO is left
- [ ] The SKILL.md frontmatter has `name`, `description`, `version` and
      `agent_created: true`
- [ ] The description says when to use the skill in the third person, and the
      trigger phrases cover both English and Chinese
- [ ] No media, rendered output, `.env`, `__pycache__` or anything under
      `runs/` was committed
- [ ] If a dependency or third-party code was added, `requirements.txt`,
      `pyproject.toml` and `NOTICE` were updated accordingly

## Measurements

Paste the key numbers from `qa.json` (at least V, dark_pct, dup_pct and
cut_rate) and say whether they got better or worse than before the change.
Do not hide a WARN from the gate; explain it.

- A pulled frame of the result (attach the file or give the path):
- What is still not implemented:
