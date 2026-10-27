"""The worked example on docs/squash-merge.html, run against a real repository."""

from __future__ import annotations

import html
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_monorepo import _run
from tests.test_output import _git

PAGE = Path(__file__).resolve().parent.parent / "docs" / "squash-merge.html"
HASH = re.compile(r"\(`[0-9a-f]{7,}`\)")


def _blocks() -> list[str]:
    text = PAGE.read_text(encoding="utf-8")
    return [html.unescape(b) for b in re.findall(r"<pre><code>(.*?)</code></pre>", text, re.S)]


def _mask(text: str) -> str:
    return HASH.sub("(`HASH`)", text).strip()


class SquashPageTests(unittest.TestCase):
    """Four squash-merged PRs after v1.2.0, one of them from dependabot."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _git(["init", "--initial-branch=main"], self.repo)
        _git(["remote", "add", "origin", "https://github.com/you/project.git"], self.repo)
        empty = ["commit", "--allow-empty", "-m"]
        _git([*empty, "feat: first release (#1)"], self.repo)
        _git(["tag", "v1.2.0"], self.repo)
        _git([*empty, "feat(api)!: paginate list endpoints (#41)", "-m",
              "* first pass\n* review fixes\n\nCo-authored-by: Grace Hopper <grace@example.com>"],
             self.repo)
        _git([*empty, "fix: handle empty config (#42)"], self.repo)
        _git([*empty, "build(deps): bump actions/checkout from 4 to 5 (#43)",
              "--author", "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>"],
             self.repo)
        _git([*empty, "docs: fix install command (#44)"], self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def relnote(self, *args: str) -> str:
        code, out, err = _run(["--repo", str(self.repo), *args])
        self.assertEqual(code, 0, err)
        return out

    def page_block(self, start: str) -> str:
        for block in _blocks():
            if block.startswith(start):
                return block
        self.fail(f"no <pre> block starting with {start!r} in {PAGE.name}")

    def test_next_version_is_major(self) -> None:
        self.assertEqual(self.relnote("--next-version").strip(), "v2.0.0")

    def test_release_body_matches_page(self) -> None:
        _git(["tag", "v2.0.0"], self.repo)
        out = self.relnote("--no-bots")
        self.assertEqual(_mask(out), _mask(self.page_block("## What's changed")))
        self.assertIn("(#41)", out)
        self.assertNotIn("](https://github.com/you/project/pull/", out)

    def test_changelog_matches_page(self) -> None:
        _git(["tag", "v2.0.0"], self.repo)
        log = self.repo / "CHANGELOG.md"
        self.relnote("--no-bots", "--changelog", str(log), "-q", "--date", "2026-10-27")
        text = log.read_text(encoding="utf-8")
        section = text[text.index("## [v2.0.0]"):]
        self.assertEqual(_mask(section), _mask(self.page_block("## [v2.0.0]")))


if __name__ == "__main__":
    unittest.main()
