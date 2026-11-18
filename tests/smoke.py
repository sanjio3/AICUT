# -*- coding: utf-8 -*-
"""Zero-dependency smoke test: python tests/smoke.py

Needs neither pytest, nor media, nor ffmpeg on the host or in CI. It only
verifies that the framework contracts are intact.
Run it before submitting a pull request; whoever changes lib/ must run it too.
"""
import os
import py_compile
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from lib import catalog, ff, music, plan, validate  # noqa: E402


def main():
    results = []

    def check(label, fn):
        try:
            ok, detail = fn()
        except Exception as exc:                                # noqa: BLE001
            ok, detail = False, repr(exc)
        results.append(bool(ok))
        print("%s  %s%s" % ("PASS" if ok else "FAIL", label,
                            ("  -> " + str(detail)) if detail else ""))

    def c_catalog():
        items = catalog.scan()
        table, conflicts = catalog.routes()
        return (len(items) >= 3 and not conflicts,
                "%d effects / %d triggers" % (len(items), len(table)))

    def c_lookup():
        hits = catalog.lookup("加个火焰转场，再要一点漫画分格")
        return (hits == ["fire-transition", "manga-split"] or
                set(hits) == {"fire-transition", "manga-split"},
                ", ".join(hits))

    def c_validate():
        rs = validate.check_all()
        bad = [r["name"] for r in rs if not r["ok"]]
        return (not bad and len(rs) >= 3, "%d/%d passed" %
                (len(rs) - len(bad), len(rs)))

    def c_selection():
        class FakePool(object):
            def take(self, need):
                return "placeholder.mp4", (0.0, need)

            def repeat_ratio(self):
                return 0.0

        cfg = ff.load_config(os.path.join(ROOT, "params.yaml"))
        grid = music.load(cfg)
        pl = plan.build(cfg, grid, FakePool(), overrides={}, duration=2.0,
                        effects=["manga-split"])
        names = set(s["effect"] for s in pl["shots"])
        return (names == {"manga-split"} and len(pl["shots"]) > 0,
                "%d shots, %s" % (len(pl["shots"]), sorted(names)))

    def c_merge():
        cfg = ff.load_config(os.path.join(ROOT, "params.yaml"))
        scalars = plan.merged(cfg, "fire-transition",
                              {"fire-transition.flame_gain": 2.4})
        return (scalars["fire-transition"]["flame_gain"] == 2.4 and
                scalars["card"]["push_px"] == 22,
                "override=%s" % scalars["fire-transition"]["flame_gain"])

    def c_compile():
        files = [os.path.join(ROOT, "aicut.py"),
                 os.path.join(ROOT, "install.py")]
        lib = os.path.join(ROOT, "lib")
        files += [os.path.join(lib, f) for f in sorted(os.listdir(lib))
                  if f.endswith(".py")]
        for f in files:
            py_compile.compile(f, doraise=True)
        return True, "%d python files" % len(files)

    def c_structure():
        items = catalog.scan()
        bad = []
        for name, meta in items.items():
            if not meta.get("agent_created"):
                bad.append("%s:no agent_created" % name)
            if not meta.get("has_scripts"):
                bad.append("%s:no scripts/" % name)
            if not meta.get("has_references"):
                bad.append("%s:no references/" % name)
            if not os.path.exists(os.path.join("skills", name,
                                               "references", "params.yaml")):
                bad.append("%s:no references/params.yaml" % name)
        return (not bad and len(items) >= 3, ", ".join(bad) or "%d standard skills" % len(items))

    def c_install():
        from lib import install as im
        skills = im._skills()
        names = [s[2] for s in skills]
        ok = len(skills) >= 3 and all(n.startswith("aicut-") for n in names)
        return ok, ", ".join(names)

    def c_package():
        import re
        import tempfile
        import zipfile

        import yaml
        from lib import package as pm
        tmp = tempfile.mkdtemp(prefix="aicut_pkg_")
        try:
            results = pm.build_all(tmp)
            if not results:
                return False, "no skills packaged"
            bad = []
            for name, path, problems in results:
                if path is None:
                    bad.append("%s:%s" % (name, "; ".join(problems)))
                    continue
                if problems:
                    bad.append("%s:%s" % (name, "; ".join(problems)))
                    continue
                with zipfile.ZipFile(path) as zf:
                    names = zf.namelist()
                    roots = [n for n in names if n.endswith("SKILL.md")]
                    if not roots:
                        bad.append("%s:no SKILL.md" % name)
                        continue
                    # The marketplace publishes a folder named after the skill,
                    # so SKILL.md sits one level down.
                    if min(n.count("/") for n in roots) != 1:
                        bad.append("%s:SKILL.md is not in a folder" % name)
                        continue
                    txt = zf.read(roots[0]).decode("utf-8")
                    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", txt, re.S)
                    if not m:
                        bad.append("%s:no frontmatter" % name)
                        continue
                    meta = yaml.safe_load(m.group(1)) or {}
                    if not meta.get("name") or not meta.get("description"):
                        bad.append("%s:frontmatter incomplete" % name)
            return (not bad, "; ".join(bad) or
                    "%d skills packaged" % len(results))
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def c_confirm():
        from lib import confirm as cm
        plan = {"project": {"duration": 2.0},
                "shots": [{"effect": "base", "dur": 0.5}],
                "beat_frames": [1, 2], "repeat_ratio": 0.1}
        h1 = cm.plan_hash(plan)
        plan2 = dict(plan)
        plan2["shots"] = [{"effect": "base", "dur": 0.9}]
        h2 = cm.plan_hash(plan2)
        ok = h1 != h2 and len(h1) == 16
        return ok, "%s vs %s" % (h1, h2)

    def c_standalone():
        """A packaged archive must run on its own, without the repository."""
        import shutil
        import subprocess
        import tempfile
        import zipfile

        from lib import package as pm
        tmp = tempfile.mkdtemp(prefix="aicut_standalone_")
        try:
            path, problems = pm.build("manga-split", tmp, market=True,
                                     with_kernel=True)
            if path is None:
                return False, "; ".join(problems)
            work = os.path.join(tmp, "unpacked")
            os.makedirs(work, exist_ok=True)
            with zipfile.ZipFile(path) as zf:
                zf.extractall(work)
            names = zipfile.ZipFile(path).namelist()
            # The archive holds a folder named after the skill, so the kernel
            # and the skill live one level down.
            tops = {n.split("/")[0] for n in names if "/" in n}
            if len(tops) != 1:
                return False, "expected one top folder, got %s" % sorted(tops)
            root = os.path.join(work, tops.pop())
            for needed in ("SKILL.md", "aicut.py", "lib/plan.py"):
                if not os.path.exists(os.path.join(root, needed)):
                    return False, "archive is missing %s" % needed
            env = dict(os.environ)
            env["PYTHONPATH"] = root
            proc = subprocess.run(
                [sys.executable, "aicut.py", "catalog"],
                cwd=root, env=env, capture_output=True, text=True, timeout=120)
            if proc.returncode != 0:
                return False, (proc.stderr or proc.stdout)[-200:]
            if "manga-split" not in proc.stdout:
                return False, "the packaged skill was not discovered"
            return True, "archive runs standalone (%d files)" % len(names)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def c_importable():
        """A packaged archive must survive what a skill importer reads."""
        import re
        import shutil
        import tempfile
        import zipfile

        import yaml
        from lib import package as pm
        tmp = tempfile.mkdtemp(prefix="aicut_import_")
        try:
            ok = True
            detail = []
            for fold in (True, False):
                path, problems = pm.build("manga-split", tmp, market=True,
                                         with_kernel=True, fold=fold)
                if path is None:
                    return False, "; ".join(problems)
                with zipfile.ZipFile(path) as zf:
                    names = zf.namelist()
                    roots = [n for n in names if n.endswith("SKILL.md")]
                    if not roots:
                        return False, "no SKILL.md (fold=%s)" % fold
                    depth = min(n.count("/") for n in roots)
                    if depth > 1:
                        return False, "SKILL.md too deep (fold=%s)" % fold
                    if fold and depth != 1:
                        return False, (
                            "the marketplace shape needs SKILL.md inside a "
                            "folder (fold=%s)" % fold)
                    if not fold and depth != 0:
                        return False, (
                            "the flat shape needs SKILL.md at the root "
                            "(fold=%s)" % fold)
                    text = zf.read(roots[0]).decode("utf-8")
                    raw = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text,
                                   re.S).group(1)
                    meta = yaml.safe_load(raw) or {}
                    if not meta.get("name") or not meta.get("description"):
                        return False, "frontmatter incomplete (fold=%s)" % fold
                    # A strict reader, a naive line reader and a regex reader
                    # must all arrive at the same name and description.
                    for key in ("name", "description"):
                        y = str(meta.get(key) or "")
                        n = ""
                        for line in raw.splitlines():
                            if line.startswith(key + ":"):
                                n = line.split(":", 1)[1].strip()
                                break
                        r = ""
                        mm = re.search(r"^%s:\s*(.+)$" % key, raw, re.M)
                        if mm:
                            r = mm.group(1).strip()
                        for value in (n, r):
                            if len(value) > 1 and value[0] == '"' \
                                    and value[-1] == '"':
                                value = value[1:-1]
                            if value and value != y:
                                return False, (
                                    "a simple reader sees a different '%s' "
                                    "(fold=%s)" % (key, fold))
                    detail.append("fold=%s:%s" % (fold, roots[0]))
            return ok, " | ".join(detail)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    check("catalog scans skills without trigger conflicts", c_catalog)
    check("user phrase maps to the right effects", c_lookup)
    check("all built-in skills pass validate-effect", c_validate)
    check("each skill follows the standard layout", c_structure)
    check("installer discovers named skills", c_install)
    check("every skill packages into a valid archive", c_package)
    check("a packaged archive runs on its own", c_standalone)
    check("a packaged archive is readable by an importer", c_importable)
    check("plan hash changes when the plan changes", c_confirm)
    check("selection.effects really restricts the rotation", c_selection)
    check("parameter override wins over local defaults", c_merge)
    check("python sources compile", c_compile)

    print("%d/%d checks passed" % (sum(results), len(results)))
    return 0 if all(results) and results else 1


if __name__ == "__main__":
    sys.exit(main())
