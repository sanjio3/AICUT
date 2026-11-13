# -*- coding: utf-8 -*-
"""effect 自检：不跑全片，用静态检查加一次纯函数调用验证三件套契约。

基础弱的贡献者写完一个特效后，用 `python aicut.py validate-effect <name>`
就能知道有没有漏文件、漏字段、写错签名或忘了输出 [out] 标签。
"""
import importlib.util
import inspect
import io
import os
import re

import yaml

from . import catalog

REQUIRED_FILES = ("SKILL.md", "run.py", "params.yaml")
REQUIRED_META = ("name", "description", "version", "triggers")
REQUIRED_SECTIONS = ("渲染前必须回传的参数表", "验收", "已知坑", "当前实现边界")
BANNED_CALLS = ("subprocess", "os.system", "cv2.imwrite", "shutil.copy")


def _front(path):
    return catalog.parse_front(path)


def check(name, root="effects"):
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
    for sec in REQUIRED_SECTIONS:
        if ("## " + sec) not in sk:
            errors.append("SKILL.md missing section '## %s'" % sec)
    if "TODO" in sk:
        warnings.append("SKILL.md still contains TODO placeholders")

    with io.open(os.path.join(d, "params.yaml"), "r", encoding="utf-8") as fh:
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

    src = io.open(os.path.join(d, "run.py"), "r", encoding="utf-8").read()
    for bad in BANNED_CALLS:
        if bad in src:
            warnings.append("run.py references '%s': build() should stay pure" % bad)

    spec = importlib.util.spec_from_file_location(
        "aicut_validate_%s" % re.sub(r"\W", "_", name),
        os.path.join(d, "run.py"))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:                                    # noqa: BLE001
        errors.append("run.py import failed: %s" % exc)
        return {"name": name, "ok": False, "errors": errors, "warnings": warnings}
    fn = getattr(mod, "build", None)
    if fn is None:
        errors.append("run.py must export build(shot, params, caps)")
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
        except Exception as exc:                                # noqa: BLE001
            errors.append("build() raised on a dummy shot: %s" % exc)

    table, conflicts = catalog.routes(root)
    for key, a, b in conflicts:
        if name in (a, b):
            errors.append("trigger '%s' conflicts with %s" %
                          (key, b if a == name else a))
    if not (meta.get("triggers") if meta else None):
        errors.append("no triggers declared")

    return {"name": name, "ok": not errors, "errors": errors,
            "warnings": warnings}


def check_all(root="effects"):
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
