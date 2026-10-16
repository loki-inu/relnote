"""Output encoding: never crash on a non-UTF-8 stdout (Windows cp1252 pipes)."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from relnote import git as relnote_git
from relnote.__main__ import _use_utf8_stdio

ROOT = Path(__file__).resolve().parents[1]


def _git(args: list[str], cwd: Path) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Ada Lovelace",
        "GIT_AUTHOR_EMAIL": "ada@example.com",
        "GIT_COMMITTER_NAME": "Ada Lovelace",
        "GIT_COMMITTER_EMAIL": "ada@example.com",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


class Cp1252Pipe(io.TextIOWrapper):
    def isatty(self) -> bool:  # pragma: no cover - trivial
        return False


class Cp1252Tty(io.TextIOWrapper):
    def isatty(self) -> bool:  # pragma: no cover - trivial
        return True


class EncodingTests(unittest.TestCase):
    def test_pipe_switches_to_utf8(self) -> None:
        raw = io.BytesIO()
        stream = Cp1252Pipe(raw, encoding="cp1252")
        with mock.patch.object(sys, "stdout", stream):
            _use_utf8_stdio()
            sys.stdout.write("Range: `v1` \u2192 `HEAD` \u2014 caf\u00e9 \u65e5\u672c\n")
            sys.stdout.flush()
        self.assertEqual(stream.encoding.lower().replace("_", "-"), "utf-8")
        self.assertIn("\u2192".encode("utf-8"), raw.getvalue())

    def test_tty_keeps_encoding_but_replaces(self) -> None:
        raw = io.BytesIO()
        stream = Cp1252Tty(raw, encoding="cp1252")
        with mock.patch.object(sys, "stdout", stream):
            _use_utf8_stdio()
            sys.stdout.write("a \u2192 b\n")
            sys.stdout.flush()
        self.assertEqual(stream.encoding, "cp1252")
        self.assertEqual(raw.getvalue(), b"a ? b\n")

    def test_stream_without_reconfigure_is_left_alone(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            _use_utf8_stdio()
            self.assertIs(sys.stdout, buf)

    def test_git_output_is_decoded_as_utf8(self) -> None:
        with mock.patch.object(relnote_git.subprocess, "run") as run:
            relnote_git.run_git(["--version"])
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs.get("encoding"), "utf-8")
        self.assertEqual(kwargs.get("errors"), "replace")

    def _run(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
        env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONPATH": str(ROOT)}
        env.pop("PYTHONUTF8", None)
        return subprocess.run(
            [sys.executable, "-m", "relnote", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
        )

    def test_help_under_cp1252_pipe(self) -> None:
        result = self._run(["--help"], ROOT)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        self.assertIn("\u2192".encode("utf-8"), result.stdout)

    def test_notes_under_cp1252_pipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _git(["init", "-q", "-b", "main"], repo)
            _git(["commit", "-q", "--allow-empty", "-m", "feat: first"], repo)
            _git(["tag", "v0.1.0"], repo)
            _git(["commit", "-q", "--allow-empty", "-m", "feat: add caf\u00e9 \u2192 \u65e5\u672c export"], repo)
            _git(["commit", "-q", "--allow-empty", "-m", "fix: handle empty input"], repo)
            result = self._run([], repo)
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
            out = result.stdout.decode("utf-8")
            self.assertIn("caf\u00e9 \u2192 \u65e5\u672c export", out)
            self.assertIn("handle empty input", out)


if __name__ == "__main__":
    unittest.main()
