"""The Python package walkthrough on docs/python-package.html, run for real.

Builds the page's pyproject.toml and history in a scratch repository, runs
examples/release.sh --bump-file pyproject.toml, and compares the script
output, version diff, CHANGELOG.md section, and Release body with the page.
The workflow's tag check step is executed against matching and stale tags.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.test_monorepo import _run
from tests.test_output import _git

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "python-package.html"
SCRIPT = ROOT / "examples" / "release.sh"
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


def _tag_check_script() -> str:
    workflow = _block("name: Release")
    tail = workflow.split("- name: Tag matches pyproject.toml", 1)[1]
    script = tail.split("        run: |\n", 1)[1].split("      - run:", 1)[0]
    return textwrap.dedent(script)


@unittest.skipIf(shutil.which("bash") is None, "bash not available")
class PythonPackagePageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.repo, self.bin = base / "repo", base / "bin"
        self.repo.mkdir()
        self.bin.mkdir()
        # The workflow calls `python`; point it at this interpreter.
        shim = self.bin / "python"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
        _git(["init", "--initial-branch=main"], self.repo)
        _git(["remote", "add", "origin", "https://github.com/you/demo.git"], self.repo)
        (self.repo / "pyproject.toml").write_text(
            _block("[build-system]") + "\n", encoding="utf-8", newline="\n")
        _git(["add", "."], self.repo)
        _git(["commit", "-m", "feat: first release"], self.repo)
        _git(["tag", "-a", "v1.2.0", "-m", "v1.2.0"], self.repo)
        history = _block("git log --oneline").splitlines()[1:]
        for subject in reversed(history):
            _git(["commit", "--allow-empty", "-m", subject], self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _env(self, **extra: str) -> dict[str, str]:
        return {
            **os.environ,
            "RELNOTE": f"{sys.executable} -m relnote",
            "PYTHONPATH": str(ROOT),
            "PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "GIT_AUTHOR_NAME": "Ada Lovelace",
            "GIT_AUTHOR_EMAIL": "ada@example.com",
            "GIT_COMMITTER_NAME": "Ada Lovelace",
            "GIT_COMMITTER_EMAIL": "ada@example.com",
            "GIT_CONFIG_NOSYSTEM": "1",
            **extra,
        }

    def _release(self) -> str:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--bump-file", "pyproject.toml"],
            cwd=self.repo, env=self._env(), capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_page_runs_the_pinned_script_with_pyproject(self) -> None:
        self.assertIn("bash release.sh --bump-file pyproject.toml", _block("curl -fsSLO"))

    def test_release_script_output_diff_and_changelog_match_page(self) -> None:
        self.assertEqual(self._release().strip(), _block("next: v1.3.0").strip())
        diff = subprocess.run(["git", "diff", "-U0", "HEAD~1", "--", "pyproject.toml"],
                              cwd=self.repo, capture_output=True, text=True, check=True).stdout
        changed = [l for l in diff.splitlines()
                   if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        self.assertEqual(changed, _block('-version = "1.2.0"').splitlines())
        text = (self.repo / "CHANGELOG.md").read_text(encoding="utf-8")
        section = text[text.index("## [v1.3.0]"):]
        self.assertEqual(_mask(section), _mask(_block("## [v1.3.0]")))

    def test_release_body_on_tag_push_matches_page(self) -> None:
        self._release()
        code, out, err = _run(["--repo", str(self.repo)])
        self.assertEqual(code, 0, err)
        self.assertEqual(_mask(out), _mask(_block("## What's changed")))
        self.assertNotIn("chore(release)", out)

    def _tag_check(self, ref: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["bash", "-e", "-c", _tag_check_script()], cwd=self.repo,
                              env=self._env(GITHUB_REF_NAME=ref),
                              capture_output=True, text=True, check=False)

    @unittest.skipIf(os.name == "nt", "python shim is a POSIX shell script")
    def test_tag_check_step(self) -> None:
        self._release()
        ok = self._tag_check("v1.3.0")
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        stale = self._tag_check("v1.4.0")
        self.assertEqual(stale.returncode, 1)
        self.assertIn("::error::tag v1.4.0 but pyproject.toml says 1.3.0", stale.stdout)


if __name__ == "__main__":
    unittest.main()
