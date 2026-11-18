---
name: Bug report
about: Something does not work as expected
title: "[bug] "
labels: bug
assignees: ''
---

## What happened

TODO describe what you expected and what happened instead.

## How to reproduce

Paste the exact commands, in order:

```
python aicut.py prepare
python aicut.py plan --run ...
python aicut.py render --run ...
```

If the failure happened while rendering, paste the full error output.

## Environment

The output of:

```
python aicut.py doctor
```

Also note your operating system, your Python version, and the ffmpeg version
that `doctor` reports.

## QA numbers

If a run was produced, paste the key numbers from `qa.json`:

- V:
- dark_pct:
- bright_pct:
- dup_pct:
- cut_rate:
- repeat_ratio:

## Checklist

- [ ] I searched the existing issues and this is not a duplicate.
- [ ] I did not include any copyrighted media in this report.
- [ ] I removed local paths or personal information that are not needed to
      reproduce the problem.
