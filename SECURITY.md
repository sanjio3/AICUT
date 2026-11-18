# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.4.x | yes |
| 0.3.x | yes |
| < 0.3 | no |

## Reporting a vulnerability

Please report security issues privately rather than opening a public issue.

Use GitHub's private reporting at
<https://github.com/sanjio3/AICUT/security/advisories/new>.

Please include:

- what the issue is and which component is affected
- the steps to reproduce it
- the impact you believe it has
- the version or commit you tested against

You can expect an acknowledgement within a week. Once the report is
confirmed, a fix will be prepared and released, and the reporter will be
credited in the release notes unless they prefer to stay anonymous.

## Scope

AICUT is a local plugin. It runs on the user's own machine, reads the media
the user points it at, and shells out to an ffmpeg binary the user supplies.
It opens no network ports and starts no background process.

That means the interesting attack surface is:

- **Path handling.** AICUT builds ffmpeg argument lists from paths that come
  from `params.yaml` and the environment. Injected shell metacharacters must
  never be interpreted; the code passes arguments as a list and does not use a
  shell.
- **The media itself.** Video, audio and image files are untrusted input.
  Parsing them is ffmpeg's job, so a vulnerable ffmpeg build is a vulnerability
  in AICUT's context. Keep ffmpeg up to date.
- **Skill code.** A skill under `skills/` is Python that runs with the user's
  permissions. Installing a skill is equivalent to running it, so only install
  skills you have reviewed.
- **Overlay material.** Files in the overlays directory are opened by ffmpeg
  and are untrusted in the same way.

## Not a vulnerability

- Rendering output that looks wrong. That is a quality problem; please open a
  regular issue instead.
- `gate` reporting WARN rather than refusing to render. The gate only warns on
  purpose, judgement stays with the user.
- The documented ffmpeg version limitations in `lib/doctor.py`. These are
  recorded, tested and handled.
