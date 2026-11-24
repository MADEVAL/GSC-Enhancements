#!/usr/bin/env python3
"""Run the full local test suite. Mirrors the CI workflow."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    validator = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "validate_skill.py")],
        cwd=ROOT,
    )
    if validator.returncode != 0:
        return validator.returncode
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(ROOT / "tests"), pattern="test_*.py"
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
