# -*- coding: utf-8 -*-
"""Install skills/ into a path the host scans. Equivalent to
`python aicut.py install`.

Usage:
  python install.py --dry-run            show where it would go, write nothing
  python install.py                      install into ~/.workbuddy/skills/
  python install.py --project <dir>      install into <dir>/.workbuddy/skills/
  python install.py --only fire-transition
  python install.py --force              overwrite an existing copy
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib import install  # noqa: E402

if __name__ == "__main__":
    sys.exit(install.main())
