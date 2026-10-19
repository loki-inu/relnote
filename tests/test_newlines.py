"""Line endings: relnote must not rewrite a file's CRLF/LF style (any OS)."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from relnote.__main__ import main
from tests.test_output import _git, _init_repo

ROOT = Path(__file__).resolve().parent.parent
# Git for Windows bash (not WSL's System32 bash) on Windows; bash elsewhere.
BASH = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else shutil.which("bash")
OLD = "# Changelog\n\nPreamble.\n\n## [v0.1.0] - 2026-01-01\n\n### Features\n\n- first\n"


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class NewlineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        _init_repo(self.repo)
        _git(["tag", "v0.1.0"], self.repo)
        (self.repo / "a.txt").write_text("a\n", encoding="utf-8")
        _git(["add", "a.txt"], self.repo)
        _git(["commit", "-m", "fix: handle empty input"], self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _changelog(self, log: Path) -> bytes:
        code, _, err = _run([
            "--repo", str(self.repo), "--changelog", str(log),
            "--changelog-title", "v0.2.0", "--date", "2026-10-19", "-q",
        ])
        self.assertEqual(code, 0, err)
        return log.read_bytes()

    def test_lf_changelog_stays_lf(self) -> None:
        log = self.repo / "CHANGELOG.md"
        log.write_bytes(OLD.encode())
        data = self._changelog(log)
        self.assertNotIn(b"\r", data)
        self.assertIn(b"## [v0.2.0] - 2026-10-19\n", data)
        self.assertTrue(data.endswith(OLD.split("## [v0.1.0]")[1].encode()))

    def test_crlf_changelog_stays_crlf(self) -> None:
        log = self.repo / "CHANGELOG.md"
        log.write_bytes(OLD.replace("\n", "\r\n").encode())
        data = self._changelog(log)
        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"))
        self.assertIn(b"## [v0.2.0] - 2026-10-19\r\n", data)
        self.assertIn(b"- first\r\n", data)

    def test_new_changelog_is_lf(self) -> None:
        data = self._changelog(self.repo / "CHANGELOG.md")
        self.assertTrue(data.startswith(b"# Changelog\n"))
        self.assertNotIn(b"\r", data)

    def test_output_file_is_lf_utf8(self) -> None:
        dest = self.repo / "notes.md"
        code, _, err = _run(["--repo", str(self.repo), "--output", str(dest), "-q"])
        self.assertEqual(code, 0, err)
        data = dest.read_bytes()
        self.assertNotIn(b"\r", data)
        self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
        self.assertIn("→".encode(), data)

    @unittest.skipUnless(BASH is not None and Path(BASH).exists(), "needs bash")
    def test_release_script_bump_keeps_line_endings(self) -> None:
        for eol in ("\n", "\r\n"):
            with self.subTest(eol=repr(eol)):
                pkg = self.repo / "package.json"
                pkg.write_bytes(("{" + eol + '  "name": "x",' + eol + '  "version": "0.1.0"' + eol + "}" + eol).encode())
                _git(["add", "package.json"], self.repo)
                _git(["commit", "-m", "chore: add package.json"], self.repo)
                env = {**os.environ, "RELNOTE": f"{Path(sys.executable).as_posix()} -m relnote",
                       "PYTHONPATH": str(ROOT), "GIT_CONFIG_NOSYSTEM": "1"}
                result = subprocess.run(
                    [BASH, (ROOT / "examples" / "release.sh").as_posix(),
                     "--bump-file", "package.json", "--skip-commit"],
                    cwd=self.repo, env=env, capture_output=True, text=True,
                )
                try:
                    self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                    data = pkg.read_bytes()
                    self.assertIn(b'"version": "0.1.1"', data)
                    if eol == "\n":
                        self.assertNotIn(b"\r", data)
                    else:
                        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"))
                finally:
                    _git(["checkout", "--", "."], self.repo)
                    _git(["clean", "-fdq"], self.repo)


if __name__ == "__main__":
    unittest.main()
