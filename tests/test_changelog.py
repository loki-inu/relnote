"""Tests for --changelog FILE (prepend a release section)."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from relnote.__main__ import main
from relnote.changelog import (
    ChangelogError,
    link_pr_refs,
    prepend_section,
    section_from_notes,
)
from tests.test_output import _git, _init_repo

NOTES = """## What's changed

### Features

- add widgets (`abc1234`) — Ada

### Fixes

- stop crash (`def5678`) — Ada

---

Range: `v1.0.0` → `v1.1.0`.

**Full changelog:** https://github.com/o/r/compare/v1.0.0...v1.1.0
"""


class PrLinkTests(unittest.TestCase):
    def test_squash_ref_linked(self) -> None:
        line = "- **api:** add paging (#41) (`abc1234`) — Ada"
        self.assertEqual(
            link_pr_refs(line, "o/r"),
            "- **api:** add paging ([#41](https://github.com/o/r/pull/41)) (`abc1234`) — Ada",
        )

    def test_code_span_and_bare_hash_untouched(self) -> None:
        line = "- keep `(#7)` literal, issue #8 too (#9)"
        out = link_pr_refs(line, "o/r")
        self.assertIn("`(#7)`", out)
        self.assertIn("issue #8 too", out)
        self.assertIn("([#9](https://github.com/o/r/pull/9))", out)

    def test_section_links_only_with_repo(self) -> None:
        notes = NOTES.replace("add widgets", "add widgets (#12)")
        self.assertIn("(#12)", section_from_notes(notes, title="v1", date=None))
        out = section_from_notes(notes, title="v1", date=None, repo="o/r")
        self.assertIn("[#12](https://github.com/o/r/pull/12)", out)
        # compare link line unchanged
        self.assertIn("**Full changelog:** https://github.com/o/r/compare", out)


class SectionTests(unittest.TestCase):
    def test_section_drops_heading_and_range_keeps_compare(self) -> None:
        out = section_from_notes(NOTES, title="v1.1.0", date="2026-10-08")
        self.assertTrue(out.startswith("## [v1.1.0] - 2026-10-08\n\n### Features"))
        self.assertNotIn("What's changed", out)
        self.assertNotIn("Range:", out)
        self.assertNotIn("---", out)
        self.assertIn("**Full changelog:** https://github.com/o/r/compare", out)
        self.assertTrue(out.endswith("\n\n"))

    def test_new_file_gets_header(self) -> None:
        sec = section_from_notes(NOTES, title="v1.1.0", date="2026-10-08")
        out = prepend_section(None, sec, title="v1.1.0")
        self.assertTrue(out.startswith("# Changelog\n"))
        self.assertIn("## [v1.1.0] - 2026-10-08", out)

    def test_inserts_above_newest_and_keeps_preamble(self) -> None:
        existing = (
            "# Changelog\n\nPreamble line.\n\n"
            "## [v1.0.0] - 2026-01-01\n\n- first\n"
        )
        sec = section_from_notes(NOTES, title="v1.1.0", date="2026-10-08")
        out = prepend_section(existing, sec, title="v1.1.0")
        self.assertTrue(out.startswith("# Changelog\n\nPreamble line.\n\n## [v1.1.0]"))
        self.assertLess(out.index("[v1.1.0]"), out.index("[v1.0.0]"))
        self.assertTrue(out.endswith("## [v1.0.0] - 2026-01-01\n\n- first\n"))

    def test_header_only_file_appends(self) -> None:
        sec = section_from_notes(NOTES, title="v1.1.0", date=None)
        out = prepend_section("# Changelog", sec, title="v1.1.0")
        self.assertEqual(out.split("\n")[0:3], ["# Changelog", "", "## [v1.1.0]"])

    def test_duplicate_title_refused(self) -> None:
        existing = "# Changelog\n\n## [v1.1.0] - 2026-10-01\n\n- x\n"
        sec = section_from_notes(NOTES, title="v1.1.0", date="2026-10-08")
        with self.assertRaises(ChangelogError):
            prepend_section(existing, sec, title="v1.1.0")

    def test_similar_title_not_treated_as_duplicate(self) -> None:
        existing = "# Changelog\n\n## [v1.1.0-rc1] - 2026-10-01\n\n- x\n"
        sec = section_from_notes(NOTES, title="v1.1.0", date="2026-10-08")
        out = prepend_section(existing, sec, title="v1.1.0")
        self.assertIn("## [v1.1.0] - 2026-10-08", out)


class ChangelogCliTests(unittest.TestCase):
    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        buf, err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = main(argv)
        return code, buf.getvalue(), err.getvalue()

    def test_cli_creates_then_prepends(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _init_repo(repo)
            _git(["tag", "v0.1.0"], repo)
            (repo / "a.txt").write_text("a\n", encoding="utf-8")
            _git(["add", "a.txt"], repo)
            _git(["commit", "-m", "fix: handle empty input"], repo)
            log = repo / "CHANGELOG.md"

            code, out, err = self._run([
                "--repo", str(repo), "--changelog", str(log),
                "--changelog-title", "v0.2.0", "--date", "2026-10-08", "-q",
            ])
            self.assertEqual(code, 0, err)
            self.assertEqual(out, "")
            text = log.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Changelog\n"))
            self.assertIn("## [v0.2.0] - 2026-10-08", text)
            self.assertIn("handle empty input", text)
            self.assertNotIn("add readme", text)

            code, _, err = self._run([
                "--repo", str(repo), "--since", "v0.1.0", "--changelog", str(log),
                "--changelog-title", "v0.2.0", "-q",
            ])
            self.assertEqual(code, 1)
            self.assertIn("already has a section", err)

            code, out, err = self._run([
                "--repo", str(repo), "--since", "HEAD~1", "--until", "HEAD~1",
                "--include-merges", "--changelog", str(log),
            ])
            # empty range -> exit 1, file untouched
            self.assertEqual(code, 1)
            self.assertEqual(log.read_text(encoding="utf-8"), text)

    def test_cli_links_squash_pr_refs_for_github_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _init_repo(repo)
            _git(["tag", "v0.1.0"], repo)
            _git(["commit", "--allow-empty", "-m", "feat: add paging (#41)"], repo)
            log = repo / "CHANGELOG.md"
            argv = [
                "--repo", str(repo), "--changelog", str(log),
                "--changelog-title", "v0.2.0", "--date", "2026-10-27",
            ]
            # no remote: plain ref, and stdout (release body) never rewritten
            code, out, err = self._run(argv)
            self.assertEqual(code, 0, err)
            self.assertIn("add paging (#41)", log.read_text(encoding="utf-8"))
            log.unlink()
            _git(["remote", "add", "origin", "git@github.com:acme/widget.git"], repo)
            code, out, err = self._run(argv)
            self.assertEqual(code, 0, err)
            self.assertIn("add paging (#41)", out)
            self.assertIn(
                "add paging ([#41](https://github.com/acme/widget/pull/41))",
                log.read_text(encoding="utf-8"),
            )

    def _compare_repo(self, tmp: str, remote: str = "https://github.com/acme/widget.git") -> Path:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        _init_repo(repo)
        _git(["remote", "add", "origin", remote], repo)
        _git(["tag", "v1.3.2"], repo)
        _git(["commit", "--allow-empty", "-m", "feat: add json output (#12)"], repo)
        return repo

    def test_version_title_on_untagged_head_ends_compare_at_title(self) -> None:
        # examples/release.sh writes CHANGELOG.md before it creates the tag.
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._compare_repo(tmp)
            log = repo / "CHANGELOG.md"
            code, out, err = self._run([
                "--repo", str(repo), "--changelog", str(log),
                "--changelog-title", "v1.4.0", "--date", "2026-10-28",
            ])
            self.assertEqual(code, 0, err)
            text = log.read_text(encoding="utf-8")
            self.assertIn("compare/v1.3.2...v1.4.0", text)
            self.assertNotIn("...HEAD", text)
            # the Release body on stdout still describes what exists: HEAD
            self.assertIn("compare/v1.3.2...HEAD", out)

    def test_non_version_title_keeps_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._compare_repo(tmp)
            log = repo / "CHANGELOG.md"
            code, _, err = self._run([
                "--repo", str(repo), "--changelog", str(log),
                "--changelog-title", "Next release", "-q",
            ])
            self.assertEqual(code, 0, err)
            self.assertIn("compare/v1.3.2...HEAD", log.read_text(encoding="utf-8"))

    def test_prefixed_version_title_with_tag_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._compare_repo(tmp)
            _git(["tag", "api/v1.0.0", "HEAD~1"], repo)
            log = repo / "CHANGELOG.md"
            code, _, err = self._run([
                "--repo", str(repo), "--tag-prefix", "api/v", "--changelog", str(log),
                "--changelog-title", "api/v1.1.0", "-q",
            ])
            self.assertEqual(code, 0, err)
            self.assertIn("compare/api/v1.0.0...api/v1.1.0", log.read_text(encoding="utf-8"))

    def test_default_title_unreleased_and_stdout_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _init_repo(repo)
            log = repo / "CHANGELOG.md"
            code, out, err = self._run([
                "--repo", str(repo), "--changelog", str(log), "--date", "2026-10-08",
            ])
            self.assertEqual(code, 0, err)
            self.assertIn("## What's changed", out)
            self.assertIn("## [Unreleased] - 2026-10-08", log.read_text(encoding="utf-8"))

    def test_plain_stdout_still_writes_markdown_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _init_repo(repo)
            log = repo / "CHANGELOG.md"
            code, out, err = self._run([
                "--repo", str(repo), "--format", "plain", "--changelog", str(log),
                "--changelog-title", "v1.0.0", "--date", "2026-10-08",
            ])
            self.assertEqual(code, 0, err)
            self.assertTrue(out.startswith("What's changed"))
            text = log.read_text(encoding="utf-8")
            self.assertIn("### Features", text)
            self.assertIn("- add readme", text)

    def test_bad_date_exits_1(self) -> None:
        code, _, err = self._run(["--changelog", "x.md", "--date", "8 Oct"])
        self.assertEqual(code, 1)
        self.assertIn("--date must look like YYYY-MM-DD", err)

    def test_missing_dir_exits_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _init_repo(repo)
            code, _, err = self._run([
                "--repo", str(repo), "--changelog", str(Path(tmp) / "nope" / "C.md"),
            ])
            self.assertEqual(code, 1)
            self.assertIn("does not exist", err)


if __name__ == "__main__":
    unittest.main()
