#!/usr/bin/env python3
"""Validator behaviour tests.

The valid repository must pass. The deliberately broken fixture must fail.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "tests" / "validate_skill.py"


def run_validator(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        cwd=ROOT,
    )


class ValidatorTests(unittest.TestCase):
    def test_repository_passes(self) -> None:
        result = run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_broken_fixture_fails(self) -> None:
        bad = ROOT / "tests" / "fixtures" / "bad-skill"
        result = run_validator(bad)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAILED", result.stdout)
        self.assertIn("broken link", result.stdout)
        self.assertIn("empty badge", result.stdout)


if __name__ == "__main__":
    unittest.main()
