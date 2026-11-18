# -*- coding: utf-8 -*-
"""Skill self-check: no full render needed. Static checks plus one real call
to the pure function verify the standard skill contract.

Standard skill layout: SKILL.md + scripts/build.py + references/params.yaml.
After writing an effect, a contributor with little experience can run
`python aicut.py validate-effect <name>` and immediately see whether a file is
missing, a field is absent, the signature is wrong, or the [out] label was
forgotten.
"""
import importlib.util
import inspect
import io
import os
import re

import yaml

from . import catalog

REQUIRED_FILES = ("SKILL.md", "scripts/build.py", "references/params.yaml")
REQUIRED_META = ("name", "description", "version", "agent_created")
REQUIRED_SECTIONS = ("Parameter table to report before rendering",
                     "Acceptance", "Known pitfalls",
                     "Current implementation boundary")
BANNED_CALLS = ("subprocess", "os.system", "cv2.imwrite", "shutil.copy")
BUILD = os.path.join("scripts", "build.py")

# The contract version a skill has to declare. The kernel injects _geom,
# _assets and _overlays and expects build() to accept them and to return
# (extra_inputs, filter_chain_lines). Bumping this number means the kernel
# changed in a way that older skills cannot satisfy.
API_VERSION = 1
REQUIRED_INJECTED = ("_geom", "_assets", "_overlays")


def _front(path):
    return catalog.parse_front(path)


def check(name, root="skills"):
    errors, warnings = [], []
    d = os.path.join(root, name)
    if not os.path.isdir(d):
        return {"name": name, "ok": False,
                "errors": ["directory not found: %s" % d], "warnings": []}

    for fn in REQUIRED_FILES:
        if not os.path.exists(os.path.join(d, fn)):
            errors.append("missing %s" % fn)
    if errors:
        return {"name": name, "ok": False, "errors": errors, "warnings": warnings}

    sk = io.open(os.path.join(d, "SKILL.md"), "r", encoding="utf-8").read()
    meta = _front(os.path.join(d, "SKILL.md"))
    if not meta:
        errors.append("SKILL.md frontmatter missing or invalid YAML")
    else:
        for k in REQUIRED_META:
            if not meta.get(k):
                errors.append("frontmatter missing '%s'" % k)
        if any("TODO" in str(t) for t in (meta.get("triggers") or [])):
            warnings.append("triggers still contain TODO placeholders")
        api = meta.get("api_version")
        if api is None:
            errors.append("frontmatter missing 'api_version' (expected %d)"
                          % API_VERSION)
        else:
            try:
                if int(api) != API_VERSION:
                    errors.append("api_version %s does not match the kernel "
                                  "expectation %d" % (api, API_VERSION))
            except (TypeError, ValueError):
                errors.append("api_version must be an integer, got %r" % api)
    for sec in REQUIRED_SECTIONS:
        if ("## " + sec) not in sk:
            errors.append("SKILL.md missing section '## %s'" % sec)
    if "TODO" in sk:
        warnings.append("SKILL.md still contains TODO placeholders")

    with io.open(os.path.join(d, "references", "params.yaml"), "r",
                 encoding="utf-8") as fh:
        pdoc = yaml.safe_load(fh) or {}
    if not isinstance(pdoc, dict) or not pdoc:
        errors.append("params.yaml must be a non-empty mapping")
        pdoc = {}
    for key, spec in pdoc.items():
        if not isinstance(spec, dict) or "default" not in spec:
            errors.append("param '%s' needs a default" % key)
            continue
        if ("min" in spec or "max" in spec) and "step" not in spec:
            errors.append("param '%s' has min/max but no step" % key)
        if "affects" in spec and not isinstance(spec["affects"], list):
            errors.append("param '%s' affects must be a list" % key)
        if "note" not in spec:
            warnings.append("param '%s' has no note about side effects" % key)

    src = io.open(os.path.join(d, BUILD), "r", encoding="utf-8").read()
    for bad in BANNED_CALLS:
        if bad in src:
            warnings.append("scripts/build.py references '%s': build() should stay pure" % bad)

    spec = importlib.util.spec_from_file_location(
        "aicut_validate_%s" % re.sub(r"\W", "_", name),
        os.path.join(d, BUILD))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:                                    # noqa: BLE001
        errors.append("scripts/build.py import failed: %s" % exc)
        return {"name": name, "ok": False, "errors": errors, "warnings": warnings}
    fn = getattr(mod, "build", None)
    if fn is None:
        errors.append("scripts/build.py must export build(shot, params, caps)")
    else:
        try:
            args = list(inspect.signature(fn).parameters)
        except (TypeError, ValueError):
            args = []
        if len(args) != 3:
            errors.append("build() must take exactly 3 args, got %d" % len(args))

        defaults = {k: (v.get("default") if isinstance(v, dict) else v)
                    for k, v in pdoc.items()}
        defaults.update({"_geom": {"w": 1280, "h": 720, "fps": 24},
                         "_overlays": "./materials/overlays",
                         "_assets": {"overlays": {"fire": []}}})
        shot = {"index": 0, "dur": 0.5, "src": "placeholder.mp4",
                "seg": (0.0, 0.5), "speed": 1.0, "effect": name}
        try:
            extra, lines = fn(shot, defaults, {"filters": {}, "hash": "validate"})
            if not isinstance(extra, list) or not isinstance(lines, list):
                errors.append("build() must return (list, list)")
            elif not lines or "[out]" not in "\n".join(lines):
                errors.append("filter chain must end with [out]")
            elif "[g]" not in "\n".join(lines) and not extra:
                errors.append("filter chain never consumes the base label [g]")
            else:
                # A skill declares which injected keys it relies on, so the
                # check only fires when a declared key is never read.
                declared = meta.get("uses") or []
                if isinstance(declared, str):
                    declared = [declared]
                for key in declared:
                    if key not in REQUIRED_INJECTED:
                        warnings.append("uses declares unknown injected key "
                                        "'%s'" % key)
                    elif key not in src:
                        errors.append("uses declares '%s' but scripts/build.py "
                                      "never reads it" % key)
        except Exception as exc:                                # noqa: BLE001
            errors.append("build() raised on a dummy shot: %s" % exc)

    table, conflicts = catalog.routes(root)
    for key, a, b in conflicts:
        if name in (a, b):
            errors.append("trigger '%s' conflicts with %s" %
                          (key, b if a == name else a))
    if meta and not meta.get("triggers"):
        warnings.append("no triggers declared; host will fall back to description")

    return {"name": name, "ok": not errors, "errors": errors,
            "warnings": warnings}


def check_all(root="skills"):
    out = []
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        if name.startswith(("_", ".")):
            continue
        if os.path.isdir(os.path.join(root, name)):
            out.append(check(name, root))
    return out


def report(results):
    lines = []
    for r in results:
        lines.append("%s  %s" % ("PASS" if r["ok"] else "FAIL", r["name"]))
        for e in r["errors"]:
            lines.append("    ERROR   %s" % e)
        for w in r["warnings"]:
            lines.append("    WARN    %s" % w)
    ok = sum(1 for r in results if r["ok"])
    lines.append("%d/%d effects passed" % (ok, len(results)))
    return "\n".join(lines)
