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
