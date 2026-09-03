"""Pytest configuration: put the repo root on sys.path so top-level modules
(``logparser``, ``processors``, ...) are importable from the tests."""

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))