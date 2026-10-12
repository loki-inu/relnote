"""Tests for --path, --tag-prefix, --next-version, and tagged-HEAD ranges."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from relnote.__main__ import main
from relnote.semver import VersionError, bump_kind, next_version
from tests.test_output import _git, _init_repo


def _commit(repo: Path, rel: str, message: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(path.read_text() + "x\n" if path.exists() else "x\n", encoding="utf-8")
    _git(["add", rel], repo)
    _git(["commit", "-m", message], repo)


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class SemverTests(unittest.TestCase):
    def test_bump_kind(self) -> None:
        self.assertEqual(bump_kind(["other", "fixes"]), "patch")
        self.assertEqual(bump_kind(["fixes", "features"]), "minor")
        self.assertEqual(bump_kind(["features", "breaking"]), "major")

    def test_next_version_keeps_v_and_prefix(self) -> None:
        self.assertEqual(next_version("v1.2.3", "minor"), "v1.3.0")
        self.assertEqual(next_version("1.2.3", "patch"), "1.2.4")
        self.assertEqual(next_version("v1.2.3", "major"), "v2.0.0")
        self.assertEqual(next_version("api/v1.2.3", "minor", prefix="api/"), "api/v1.3.0")
        self.assertEqual(next_version("web@2.0.0", "patch", prefix="web@"), "web@2.0.1")

    def test_zero_major_breaking_bumps_minor(self) -> None:
        self.assertEqual(next_version("v0.4.2", "major"), "v0.5.0")

    def test_first_release(self) -> None:
        self.assertEqual(next_version(None, "minor"), "v0.1.0")
        self.assertEqual(next_version(None, "patch", prefix="api/v"), "api/v0.1.0")

    def test_prerelease_base_is_parsed(self) -> None:
        self.assertEqual(next_version("v1.0.0-rc.1", "patch"), "v1.0.1")

    def test_not_semver_raises(self) -> None:
        with self.assertRaises(VersionError):
            next_version("release-2026", "patch")
        with self.assertRaises(VersionError):
            next_version("v1.0.0", "patch", prefix="api/")


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _init_repo(self.repo)
        _git(["tag", "v1.0.0"], self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_next_version_minor_on_feat(self) -> None:
        _commit(self.repo, "a.txt", "fix: one")
        _commit(self.repo, "b.txt", "feat: two")
        code, out, err = _run(["--repo", str(self.repo), "--next-version"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "v1.1.0\n")

    def test_next_version_major_on_breaking(self) -> None:
        _commit(self.repo, "a.txt", "feat!: drop python 3.10")
        code, out, _ = _run(["--repo", str(self.repo), "--next-version"])
        self.assertEqual((code, out), (0, "v2.0.0\n"))

    def test_next_version_no_commits_exits_1(self) -> None:
        code, out, err = _run(["--repo", str(self.repo), "--since", "v1.0.0", "--next-version"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("no commits", err)

    def test_path_filters_commits(self) -> None:
        _commit(self.repo, "packages/api/x.py", "feat(api): new endpoint")
        _commit(self.repo, "packages/web/y.js", "fix(web): button colour")
        code, out, err = _run(["--repo", str(self.repo), "--path", "packages/api"])
        self.assertEqual(code, 0, err)
        self.assertIn("new endpoint", out)
        self.assertNotIn("button colour", out)

    def test_path_repeatable(self) -> None:
        _commit(self.repo, "packages/api/x.py", "feat(api): new endpoint")
        _commit(self.repo, "packages/web/y.js", "fix(web): button colour")
        _commit(self.repo, "docs/z.md", "docs: guide")
        code, out, _ = _run(
            ["--repo", str(self.repo), "--path", "packages/api", "--path", "docs"]
        )
        self.assertEqual(code, 0)
        self.assertIn("new endpoint", out)
        self.assertIn("guide", out)
        self.assertNotIn("button colour", out)

    def test_tag_prefix_picks_package_tag(self) -> None:
        _git(["tag", "api/v0.3.0"], self.repo)
        _commit(self.repo, "packages/api/x.py", "feat(api): one")
        _git(["tag", "v1.1.0"], self.repo)
        _commit(self.repo, "packages/api/x.py", "fix(api): two")
        code, out, err = _run(
            [
                "--repo", str(self.repo),
                "--path", "packages/api",
                "--tag-prefix", "api/v",
            ]
        )
        self.assertEqual(code, 0, err)
        self.assertIn("one", out)
        self.assertIn("two", out)
        self.assertIn("`api/v0.3.0`", out)
        code, out, _ = _run(
            ["--repo", str(self.repo), "--tag-prefix", "api/", "--next-version"]
        )
        self.assertEqual((code, out), (0, "api/v0.4.0\n"))

    def test_tagged_head_uses_previous_tag(self) -> None:
        _commit(self.repo, "a.txt", "feat: shipped thing")
        _git(["tag", "v1.1.0"], self.repo)
        code, out, err = _run(["--repo", str(self.repo)])
        self.assertEqual(code, 0, err)
        self.assertIn("shipped thing", out)
        self.assertIn("`v1.0.0`", out)

    def test_tagged_until_uses_previous_tag(self) -> None:
        _commit(self.repo, "a.txt", "feat: in one-one")
        _git(["tag", "v1.1.0"], self.repo)
        _commit(self.repo, "b.txt", "fix: after")
        code, out, err = _run(["--repo", str(self.repo), "--until", "v1.1.0"])
        self.assertEqual(code, 0, err)
        self.assertIn("in one-one", out)
        self.assertNotIn("after", out)


if __name__ == "__main__":
    unittest.main()
