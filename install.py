# -*- coding: utf-8 -*-
"""把 skills/ 安装到宿主扫描路径。等价于 `python aicut.py install`。

用法：
  python install.py --dry-run            看会装到哪，不写入
  python install.py                      装到 ~/.workbuddy/skills/
  python install.py --project <dir>      装到 <dir>/.workbuddy/skills/
  python install.py --only fire-transition
  python install.py --force              覆盖已存在的
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib import install  # noqa: E402

if __name__ == "__main__":
    sys.exit(install.main())
