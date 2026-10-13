"""Build the single-file zipapp with scripts/build_zipapp.py and run it."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from relnote import __version__
from tests.test_monorepo import _commit
from tests.test_output import _git, _init_repo

ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = ROOT / "scripts" / "build_zipapp.py"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


class ZipappTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.dist = Path(cls._tmp.name) / "dist"
        result = _run([sys.executable, str(BUILD_SCRIPT), "--dist", str(cls.dist)], cwd=ROOT)
        if result.returncode != 0:
            raise AssertionError(f"build failed: {result.stderr}")
        cls.exe = cls.dist / "relnote"
        cls.pyz = cls.dist / "relnote.pyz"
        # Invoke the shebang directly where the OS honours it; Windows needs the interpreter.
        cls.cmd = [str(cls.exe)] if os.name == "posix" else [sys.executable, str(cls.pyz)]

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_files_and_checksums(self) -> None:
        self.assertEqual(self.exe.read_bytes(), self.pyz.read_bytes())
        self.assertTrue(self.exe.read_bytes().startswith(b"#!/usr/bin/env python3\n"))
        if os.name == "posix":
            self.assertTrue(os.access(self.exe, os.X_OK))
        sums = (self.dist / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        digest = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        self.assertEqual(sums, [f"{digest}  relnote", f"{digest}  relnote.pyz"])

    def test_version(self) -> None:
        result = _run([*self.cmd, "--version"], cwd=Path(tempfile.gettempdir()))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"relnote {__version__}")

    def test_notes_and_next_version_outside_source_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _init_repo(repo)
            _git(["tag", "v1.0.0"], repo)
            _commit(repo, "a.txt", "fix(cli): handle empty ranges")
            _commit(repo, "b.txt", "feat: add --next-version")

            notes = _run(self.cmd, cwd=repo)
            self.assertEqual(notes.returncode, 0, notes.stderr)
            self.assertIn("### Features", notes.stdout)
            self.assertIn("add --next-version", notes.stdout)
            self.assertIn("handle empty ranges", notes.stdout)
            self.assertIn("`v1.0.0`", notes.stdout)

            elsewhere = Path(tmp)
            nxt = _run([*self.cmd, "--repo", str(repo), "--next-version"], cwd=elsewhere)
            self.assertEqual(nxt.returncode, 0, nxt.stderr)
            self.assertEqual(nxt.stdout, "v1.1.0\n")


if __name__ == "__main__":
    unittest.main()
