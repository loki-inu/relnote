"""CLI tests for --output FILE."""

from __future__ import annotations

import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from relnote.__main__ import main


def _git(args: list[str], cwd: Path) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Ada Lovelace",
        "GIT_AUTHOR_EMAIL": "ada@example.com",
        "GIT_COMMITTER_NAME": "Ada Lovelace",
        "GIT_COMMITTER_EMAIL": "ada@example.com",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    result = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"git {args} failed ({result.returncode}): {result.stderr}"
        )


def _init_repo(root: Path) -> None:
    _git(["init", "--initial-branch=main"], root)
    _git(["config", "user.name", "Ada Lovelace"], root)
    _git(["config", "user.email", "ada@example.com"], root)
    (root / "README").write_text("hello\n", encoding="utf-8")
    _git(["add", "README"], root)
    _git(["commit", "-m", "feat: add readme"], root)


class OutputFlagTests(unittest.TestCase):
    def test_writes_temp_file_and_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _init_repo(repo)
            out = Path(tmp) / "notes.md"
            buf = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err):
                code = main(["--repo", str(repo), "--output", str(out)])
            self.assertEqual(code, 0, err.getvalue())
            self.assertTrue(out.exists())
            file_text = out.read_text(encoding="utf-8")
            stdout_text = buf.getvalue()
            self.assertEqual(file_text, stdout_text)
            self.assertIn("add readme", file_text)
            self.assertTrue(file_text.endswith("\n"))
            self.assertEqual(err.getvalue(), "")

    def test_missing_parent_exits_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _init_repo(repo)
            missing = Path(tmp) / "no-such-dir" / "notes.md"
            buf = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err):
                code = main(["--repo", str(repo), "--output", str(missing)])
            self.assertEqual(code, 1)
            self.assertFalse(missing.exists())
            self.assertIn("does not exist", err.getvalue())
            self.assertEqual(buf.getvalue(), "")

    def test_quiet_with_output_writes_file_stdout_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _init_repo(repo)
            out = Path(tmp) / "notes.md"
            buf = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err):
                code = main(["--repo", str(repo), "--output", str(out), "--quiet"])
            self.assertEqual(code, 0, err.getvalue())
            self.assertTrue(out.exists())
            file_text = out.read_text(encoding="utf-8")
            self.assertIn("add readme", file_text)
            self.assertTrue(file_text.endswith("\n"))
            self.assertEqual(buf.getvalue(), "")
            self.assertEqual(err.getvalue(), "")

    def test_quiet_without_output_exits_2(self) -> None:
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = main(["--quiet"])
        self.assertEqual(code, 2)
        self.assertIn("relnote: --quiet requires --output", err.getvalue())
        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
