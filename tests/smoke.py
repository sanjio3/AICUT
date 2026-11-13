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
        files = [os.path.join(ROOT, "aicut.py")]
        lib = os.path.join(ROOT, "lib")
        files += [os.path.join(lib, f) for f in sorted(os.listdir(lib))
                  if f.endswith(".py")]
        for f in files:
            py_compile.compile(f, doraise=True)
        return True, "%d python files" % len(files)

    check("catalog scans effects without trigger conflicts", c_catalog)
    check("user phrase maps to the right effects", c_lookup)
    check("all built-in effects pass validate-effect", c_validate)
    check("selection.effects really restricts the rotation", c_selection)
    check("parameter override wins over local defaults", c_merge)
    check("python sources compile", c_compile)

    print("%d/%d checks passed" % (sum(results), len(results)))
    return 0 if all(results) and results else 1


if __name__ == "__main__":
    sys.exit(main())
