"""Tests for examples/release.sh (standard-version style local release)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_monorepo import _commit
from tests.test_output import _git, _init_repo

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "examples" / "release.sh"


def _out(args: list[str], cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True).stdout


@unittest.skipIf(shutil.which("bash") is None, "bash not available")
class ReleaseScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _init_repo(self.repo)
        (self.repo / "package.json").write_text(
            '{\n  "name": "demo",\n  "version": "1.3.2",\n'
            '  "dependencies": {"left-pad": "1.0.0"}\n}\n',
            encoding="utf-8",
        )
        (self.repo / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "1.3.2"\n', encoding="utf-8"
        )
        _git(["add", "."], self.repo)
        _git(["commit", "-m", "chore: init"], self.repo)
        _git(["tag", "v1.3.2"], self.repo)
        _commit(self.repo, "a.txt", "feat: add a")
        _commit(self.repo, "b.txt", "fix(cli): handle b")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            "RELNOTE": f"{sys.executable} -m relnote",
            "PYTHONPATH": str(ROOT),
            "GIT_AUTHOR_NAME": "Ada Lovelace",
            "GIT_AUTHOR_EMAIL": "ada@example.com",
            "GIT_COMMITTER_NAME": "Ada Lovelace",
            "GIT_COMMITTER_EMAIL": "ada@example.com",
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def _tags(self) -> list[str]:
        return _out(["git", "tag"], self.repo).split()

    def test_dry_run_changes_nothing(self) -> None:
        result = self._run("--dry-run", "--bump-file", "package.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("next: v1.4.0", result.stdout)
        self.assertIn("### Features", result.stdout)
        self.assertFalse((self.repo / "CHANGELOG.md").exists())
        self.assertEqual(self._tags(), ["v1.3.2"])
        self.assertIn('"version": "1.3.2"', (self.repo / "package.json").read_text())

    def test_release_bumps_changelog_commits_and_tags(self) -> None:
        result = self._run("--bump-file", "package.json", "--bump-file", "pyproject.toml")
        self.assertEqual(result.returncode, 0, result.stderr)
        package = (self.repo / "package.json").read_text()
        self.assertIn('"version": "1.4.0"', package)
        self.assertIn('"left-pad": "1.0.0"', package)
        self.assertIn('version = "1.4.0"', (self.repo / "pyproject.toml").read_text())
        changelog = (self.repo / "CHANGELOG.md").read_text()
        self.assertIn("## [v1.4.0] - ", changelog)
        self.assertIn("handle b", changelog)
        self.assertEqual(
            _out(["git", "log", "-1", "--format=%s"], self.repo).strip(),
            "chore(release): v1.4.0",
        )
        self.assertIn("v1.4.0", self._tags())
        self.assertEqual(_out(["git", "cat-file", "-t", "v1.4.0"], self.repo).strip(), "tag")
        self.assertEqual(_out(["git", "status", "--porcelain"], self.repo), "")

        again = self._run()
        self.assertEqual(again.returncode, 1)
        self.assertIn("nothing to release", again.stderr)

    def test_release_as_and_skip_tag(self) -> None:
        result = self._run("--release-as", "v2.0.0", "--skip-tag")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## [v2.0.0] - ", (self.repo / "CHANGELOG.md").read_text())
        self.assertNotIn("v2.0.0", self._tags())

    def test_skip_commit_leaves_files_uncommitted(self) -> None:
        result = self._run("--skip-commit")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.repo / "CHANGELOG.md").exists())
        self.assertEqual(
            _out(["git", "log", "-1", "--format=%s"], self.repo).strip(), "fix(cli): handle b"
        )

    def test_dirty_tree_refused(self) -> None:
        (self.repo / "a.txt").write_text("dirty\n", encoding="utf-8")
        result = self._run()
        self.assertEqual(result.returncode, 1)
        self.assertIn("uncommitted changes", result.stderr)

    def test_monorepo_prefix_and_path(self) -> None:
        _git(["tag", "api/v1.0.0"], self.repo)
        _commit(self.repo, "packages/api/f.txt", "feat(api): endpoint")
        _commit(self.repo, "packages/web/f.txt", "fix(web): button")
        result = self._run(
            "--tag-prefix", "api/v", "--changelog", "packages/api/CHANGELOG.md",
            "--", "--path", "packages/api",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("api/v1.1.0", self._tags())
        changelog = (self.repo / "packages/api/CHANGELOG.md").read_text()
        self.assertIn("endpoint", changelog)
        self.assertNotIn("button", changelog)

    def test_missing_bump_version_line_fails(self) -> None:
        (self.repo / "VERSION.md").write_text("no version here\n", encoding="utf-8")
        _git(["add", "VERSION.md"], self.repo)
        _git(["commit", "-m", "docs: version file"], self.repo)
        result = self._run("--bump-file", "VERSION.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no version line", result.stderr)
        self.assertEqual(self._tags(), ["v1.3.2"])


if __name__ == "__main__":
    unittest.main()
