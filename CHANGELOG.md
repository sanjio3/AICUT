# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-11-18

### Added

- **Render gate.** `render` now refuses to run without a user confirmation
  whose hash still matches the plan. The agent has to put the questions to the
  user and record the answer with `aicut.py confirm`; it cannot produce a
  video nobody asked for.
- **`aicut.py confirm`** writes the confirmation record with a timestamp, the
  plan hash and an optional note about what the user decided.
- **Automatic demo material.** When the materials directory is empty,
  `prepare` generates synthetic demo clips computed pixel by pixel, so a fresh
  clone produces a picture with no setup. The generator works on any ffmpeg
  build, including old ones without the `lavfi` input device.
- **`aicut.py package`** builds a distributable zip per skill, with SKILL.md
  at the root of the archive and a valid frontmatter block, which is what skill
  marketplaces expect.
- **GitHub Actions CI** runs the smoke test, the contract check, the packaging
  and a local-path and credential scan on every pull request, across Python
  3.9, 3.11 and 3.12.
- **`CHANGELOG.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`** and an issue template
  configuration file.

### Changed

- **Every effect is now a standard skill.** `effects/<name>/` with its
  hand-rolled `SKILL.md` plus `run.py` plus `params.yaml` is replaced by
  `skills/<name>/` with native frontmatter, `scripts/build.py` and
  `references/{params.yaml,pitfalls.md}`. The host discovers them by
  description; `triggers` is an optional accelerator.
- **The root SKILL.md is a conversation protocol, not a pipeline.** It states
  that the agent must ask before rendering, and how to run each step.
- **All built-in prompts, CLI output, docstrings and comments are in English.**
  Chinese trigger phrases and the Chinese half of the attribution table are
  kept so Chinese users are matched too.
- **Documentation is bilingual.** `README.md` is the English entry point and
  `README.zh-CN.md` is the Chinese one, linked from each other.
- **English trigger phrases added** to every effect: fire wipe, comic panel
  split, four panel, soft fade out, ending blur, dreamy outro and more.
- The `attribution` table now carries English phrases next to the Chinese
  ones, so "too blurry" and "太模糊" resolve to the same parameter.
- `validate-effect` requires the standard layout, `agent_created: true` and
  the four required sections under their English headings.

### Fixed

- The smoke test now also covers the packaging output and the plan hash, so a
  change that breaks either fails before review.

## [0.3.0] - 2026-11-17

### Added

- Standard skill layout under `skills/`, with `install.py` to install into
  `~/.workbuddy/skills/` or a project-level `.workbuddy/skills/`.
- `lib/catalog.py` scans the skills and reports conflicts.
- `lib/validate.py` checks the skill contract without rendering anything.

### Changed

- The kernel paths moved from `effects/` to `skills/`.
- The render cache key now includes the skill code hash.

## [0.2.0] - 2026-11-13

### Added

- `selection.effects` as the single switch that actually enables an effect.
- `prepare` detects the beat and the dark spans without any manual
  preprocessing.
- Incremental rendering with a content-hash cache shared across runs.

## [0.1.0] - 2026-11-13

### Added

- Initial public release: automatic beat detection, media preprocessing,
  attributable parameters, incremental rendering and acceptance metrics.

[Unreleased]: https://github.com/sanjio3/AICUT/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/sanjio3/AICUT/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/sanjio3/AICUT/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/sanjio3/AICUT/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sanjio3/AICUT/releases/tag/v0.1.0
