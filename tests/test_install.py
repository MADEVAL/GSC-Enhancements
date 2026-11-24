#!/usr/bin/env python3
"""Installer round-trip tests: install, check, detect drift, dry run."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.py"
SKILL_NAME = "gsc-enhancements"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(INSTALL), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
    )


class InstallTests(unittest.TestCase):
    def test_install_and_check_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            install = run("--target", "project", cwd=workdir)
            self.assertEqual(install.returncode, 0, install.stderr)

            target = workdir / ".opencode" / "skills" / SKILL_NAME
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertTrue((target / "scripts" / "analyze_export.py").is_file())
            self.assertTrue((target / "LICENSE").is_file())
            self.assertFalse((target / "docs").exists())
            self.assertFalse((target / "tests").exists())
            self.assertFalse((target / "evals").exists())

            check = run("--target", "project", "--check", cwd=workdir)
            self.assertEqual(check.returncode, 0, check.stdout)

            (target / "SKILL.md").write_text("drifted\n", encoding="utf-8")
            drifted = run("--target", "project", "--check", cwd=workdir)
            self.assertEqual(drifted.returncode, 1)
            self.assertIn("changed", drifted.stdout)

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            result = run("--target", "project", "--dry-run", cwd=workdir)
            self.assertEqual(result.returncode, 0)
            self.assertFalse((workdir / ".opencode").exists())
            self.assertIn("would install", result.stdout)

    def test_list_shows_all_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run("--list", cwd=Path(tmp))
            self.assertEqual(result.returncode, 0)
            for name in ("claude", "opencode", "agents", "codex", "project"):
                self.assertIn(name, result.stdout)


if __name__ == "__main__":
    unittest.main()
