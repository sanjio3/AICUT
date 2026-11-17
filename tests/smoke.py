# -*- coding: utf-8 -*-
"""零依赖冒烟测试：python tests/smoke.py

本机与 CI 都无需 pytest、无需素材、无需 ffmpeg，只验证框架契约没被改坏。
同学提交前跑它；负责人改动 lib/ 后也必须跑它。
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

    check("catalog scans skills without trigger conflicts", c_catalog)
    check("user phrase maps to the right effects", c_lookup)
    check("all built-in skills pass validate-effect", c_validate)
    check("each skill follows the standard layout", c_structure)
    check("installer discovers named skills", c_install)
    check("selection.effects really restricts the rotation", c_selection)
    check("parameter override wins over local defaults", c_merge)
    check("python sources compile", c_compile)

    print("%d/%d checks passed" % (sum(results), len(results)))
    return 0 if all(results) and results else 1


if __name__ == "__main__":
    sys.exit(main())
