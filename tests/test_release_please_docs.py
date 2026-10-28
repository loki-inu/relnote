"""The one-click release workflow on docs/release-please-alternative.html, run for real.

The last step's run: script is taken from the page and executed with bash in a
scratch repository (push goes to a local bare repo, gh is a stub that records
its arguments). The page's CHANGELOG.md and Release body blocks must match.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from relnote import __version__
from tests.test_output import _git

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "release-please-alternative.html"
HASH = re.compile(r"\(`[0-9a-f]{7,}`\)")
DATE = re.compile(r"\] - \d{4}-\d{2}-\d{2}")


def _blocks() -> list[str]:
    text = PAGE.read_text(encoding="utf-8")
    return [html.unescape(b) for b in re.findall(r"<pre><code>(.*?)</code></pre>", text, re.S)]


def _block(start: str) -> str:
    for block in _blocks():
        if block.startswith(start):
            return block
    raise AssertionError(f"no <pre> block starting with {start!r} in {PAGE.name}")


def _mask(text: str) -> str:
    return DATE.sub("] - DATE", HASH.sub("(`HASH`)", text)).strip()


def _release_step() -> str:
    workflow = _block("name: Release")
    tail = workflow.split("- name: Bump, changelog, tag, publish", 1)[1]
    script = tail.split("        run: |\n", 1)[1]
    return textwrap.dedent(script)


@unittest.skipIf(shutil.which("bash") is None, "bash not available")
class ReleasePleaseAlternativePageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.repo, self.remote, self.bin, self.runner_temp = (
            base / "repo", base / "remote.git", base / "bin", base / "runner")
        for d in (self.repo, self.bin, self.runner_temp):
            d.mkdir()
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True)
        shutil.copy(ROOT / "examples" / "release.sh", self.runner_temp / "release.sh")
        self.gh_log = base / "gh.log"
        self._script("relnote", f'#!/bin/sh\nexec "{sys.executable}" -m relnote "$@"\n')
        self._script("gh", f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{self.gh_log}"\n')

        _git(["init", "--initial-branch=main"], self.repo)
        _git(["remote", "add", "origin", "https://github.com/you/project.git"], self.repo)
        _git(["remote", "set-url", "--push", "origin", str(self.remote)], self.repo)
        (self.repo / "pyproject.toml").write_text(
            '[project]\nname = "project"\nversion = "1.3.2"\n', encoding="utf-8")
        _git(["add", "."], self.repo)
        _git(["commit", "-m", "chore: init"], self.repo)
        _git(["tag", "v1.3.2"], self.repo)
        _git(["commit", "--allow-empty", "-m", "feat: add --json output (#12)"], self.repo)
        _git(["commit", "--allow-empty", "-m", "fix: handle empty config (#13)"], self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _script(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _run_step(self) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "PYTHONPATH": str(ROOT),
            "RUNNER_TEMP": str(self.runner_temp),
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        for key in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
            env.pop(key, None)
        return subprocess.run(["bash", "-c", _release_step()], cwd=self.repo, env=env,
                              capture_output=True, text=True)

    def test_page_pins_current_version(self) -> None:
        workflow = _block("name: Release")
        self.assertIn(f"loki-inu/relnote@v{__version__}", workflow)
        self.assertIn(f"V: v{__version__}", workflow)

    def test_step_bumps_tags_pushes_and_publishes(self) -> None:
        result = self._run_step()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('version = "1.4.0"', (self.repo / "pyproject.toml").read_text(encoding="utf-8"))
        tags = subprocess.run(["git", "--git-dir", str(self.remote), "tag"],
                              capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(tags, ["v1.4.0"])
        subject = subprocess.run(["git", "log", "-1", "--format=%s %an"], cwd=self.repo,
                                 capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(subject, "chore(release): v1.4.0 github-actions[bot]")
        notes_file = self.runner_temp / "notes.md"
        self.assertEqual(self.gh_log.read_text(encoding="utf-8").strip(),
                         f"release create v1.4.0 --title v1.4.0 --notes-file {notes_file}")

        notes = notes_file.read_text(encoding="utf-8")
        self.assertEqual(_mask(notes), _mask(_block("## What's changed")))
        self.assertIn("compare/v1.3.2...v1.4.0", notes)
        self.assertNotIn("chore(release)", notes)

        changelog = (self.repo / "CHANGELOG.md").read_text(encoding="utf-8")
        section = changelog[changelog.index("## [v1.4.0]"):]
        self.assertEqual(_mask(section), _mask(_block("## [v1.4.0]")))
        self.assertNotIn("...HEAD", section)

    def test_second_run_is_a_no_op(self) -> None:
        self.assertEqual(self._run_step().returncode, 0)
        again = self._run_step()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("nothing to release", again.stdout)
        self.assertEqual(len(self.gh_log.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
