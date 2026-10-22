"""The worked example on docs/monorepo.html, run against a real repository."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.test_monorepo import _commit, _run
from tests.test_output import _git


class MonorepoPageTests(unittest.TestCase):
    """Two packages (api, web), shared code, and api/v* + web/v* tags."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _git(["init", "--initial-branch=main"], self.repo)
        _git(["remote", "add", "origin", "https://github.com/acme/shop.git"], self.repo)
        _commit(self.repo, "README.md", "chore: init")
        _commit(self.repo, "packages/api/app.py", "feat(api): first endpoint")
        _commit(self.repo, "packages/web/index.js", "feat(web): landing page")
        _git(["tag", "api/v1.0.0"], self.repo)
        _git(["tag", "web/v0.1.0"], self.repo)
        _commit(self.repo, "packages/api/app.py", "fix(api): handle empty body")
        _commit(self.repo, "packages/web/index.js", "feat(web): dark mode")
        _git(["tag", "web/v0.2.0"], self.repo)
        _commit(self.repo, "packages/api/app.py", "feat(api)!: drop /v1 routes")
        _commit(self.repo, "packages/shared/util.py", "fix(shared): trim whitespace")
        _commit(self.repo, "docs/guide.md", "docs: monorepo guide")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def relnote(self, *args: str) -> tuple[int, str, str]:
        return _run(["--repo", str(self.repo), *args])

    def test_package_notes_start_at_package_tag(self) -> None:
        code, out, err = self.relnote("--path", "packages/api", "--tag-prefix", "api/v")
        self.assertEqual(code, 0, err)
        self.assertIn("drop /v1 routes", out)
        self.assertIn("handle empty body", out)
        self.assertNotIn("trim whitespace", out)
        self.assertNotIn("monorepo guide", out)
        self.assertIn("compare/api/v1.0.0...HEAD", out)

    def test_without_prefix_starts_at_other_package_tag(self) -> None:
        code, out, _ = self.relnote("--path", "packages/api")
        self.assertEqual(code, 0)
        self.assertIn("`web/v0.2.0`", out)
        self.assertNotIn("handle empty body", out)

    def test_unchanged_package_exits_1(self) -> None:
        code, out, err = self.relnote("--path", "packages/web", "--tag-prefix", "web/v")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("no commits in range web/v0.2.0..HEAD", err)

    def test_shared_path_and_next_versions(self) -> None:
        code, out, _ = self.relnote(
            "--path", "packages/web", "--path", "packages/shared", "--tag-prefix", "web/v"
        )
        self.assertEqual(code, 0)
        self.assertIn("trim whitespace", out)
        self.assertEqual(
            self.relnote("--path", "packages/api", "--tag-prefix", "api/v", "--next-version")[:2],
            (0, "api/v2.0.0\n"),
        )
        self.assertEqual(
            self.relnote(
                "--path", "packages/web", "--path", "packages/shared",
                "--tag-prefix", "web/v", "--next-version",
            )[:2],
            (0, "web/v0.2.1\n"),
        )

    def test_changelog_then_tag_push_notes(self) -> None:
        changelog = self.repo / "packages" / "api" / "CHANGELOG.md"
        code, out, err = self.relnote(
            "--path", "packages/api", "--tag-prefix", "api/v",
            "--changelog", str(changelog), "--changelog-title", "api/v2.0.0",
            "--date", "2026-10-22", "-q",
        )
        self.assertEqual((code, out), (0, ""), err)
        text = changelog.read_text(encoding="utf-8")
        self.assertIn("## [api/v2.0.0] - 2026-10-22", text)
        self.assertIn("handle empty body", text)
        _git(["add", "packages/api/CHANGELOG.md"], self.repo)
        _git(["commit", "-m", "chore(release): api/v2.0.0"], self.repo)
        _git(["tag", "api/v2.0.0"], self.repo)
        # On the tag push: the range runs from the previous api/v* tag.
        code, out, _ = self.relnote(
            "--path", "packages/api", "--tag-prefix", "api/v", "--until", "api/v2.0.0"
        )
        self.assertEqual(code, 0)
        self.assertIn("drop /v1 routes", out)
        self.assertIn("compare/api/v1.0.0...api/v2.0.0", out)

    def test_first_release_of_a_package(self) -> None:
        _commit(self.repo, "packages/cli/main.py", "feat(cli): first command")
        self.assertEqual(
            self.relnote("--path", "packages/cli", "--tag-prefix", "cli/v", "--next-version")[:2],
            (0, "cli/v0.1.0\n"),
        )
        self.assertEqual(
            self.relnote(
                "--path", "packages/cli", "--tag-prefix", "@acme/cli@", "--next-version"
            )[:2],
            (0, "@acme/cli@0.1.0\n"),
        )


if __name__ == "__main__":
    unittest.main()
