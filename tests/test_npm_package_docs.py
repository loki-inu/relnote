"""The npm package walkthrough on docs/npm-package.html, run for real.

Builds the page's package.json and history in a scratch repository, runs
examples/release.sh --bump-file package.json --exec "npm install
--package-lock-only --ignore-scripts --silent" with real npm, and compares
the script output, release commit files, CHANGELOG.md section, and Release
body with the page. Checks that package-lock.json matches package.json
afterwards and stays stale without --exec. Runs the workflow's tag check
step against matching and stale tags.
"""

from __future__ import annotations

import html
import json
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
PAGE = ROOT / "docs" / "npm-package.html"
SCRIPT = ROOT / "examples" / "release.sh"
HASH = re.compile(r"\(`[0-9a-f]{7,}`\)")
DATE = re.compile(r"\] - \d{4}-\d{2}-\d{2}")
EXEC = "npm install --package-lock-only --ignore-scripts --silent"


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
    tail = workflow.split("- name: Tag matches package.json", 1)[1]
    script = tail.split("        run: |\n", 1)[1].split("      - run:", 1)[0]
    return textwrap.dedent(script)


def _lock_version(repo: Path) -> str:
    lock = json.loads((repo / "package-lock.json").read_text(encoding="utf-8"))
    return lock["packages"][""]["version"]


class NpmPackagePageStaticTests(unittest.TestCase):
    def test_page_runs_the_pinned_script_with_lock_sync(self) -> None:
        block = _block("curl -fsSLO")
        self.assertIn(f'bash release.sh --bump-file package.json --exec "{EXEC}"', block)
        version = re.search(r"/relnote/(v[\d.]+)/examples/release.sh", block).group(1)
        self.assertIn(f"uses: loki-inu/relnote@{version}", _block("name: Release"))

    def test_workflow_publishes_with_trusted_publishing(self) -> None:
        workflow = _block("name: Release")
        self.assertIn("id-token: write", workflow)
        self.assertIn("actions/setup-node@v4", workflow)
        self.assertIn("npm publish --access public", workflow)
        self.assertIn("npm ci", workflow)
        self.assertLess(workflow.index("npm publish"), workflow.index("gh release create"))


@unittest.skipIf(shutil.which("bash") is None or shutil.which("npm") is None,
                 "bash and npm needed")
class NpmPackagePageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        _git(["init", "--initial-branch=main"], self.repo)
        _git(["remote", "add", "origin", "https://github.com/you/demo.git"], self.repo)
        (self.repo / "package.json").write_text(
            _block("{\n  \"name\": \"demo\"") + "\n", encoding="utf-8", newline="\n")
        (self.repo / "index.js").write_text(
            "module.exports = { version: require('./package.json').version };\n",
            encoding="utf-8")
        (self.repo / "index.test.js").write_text(
            "const { test } = require('node:test');\n"
            "const assert = require('node:assert/strict');\n"
            "const { version } = require('./index.js');\n"
            "test('exports package version', () => {\n"
            "  assert.equal(typeof version, 'string');\n"
            "});\n",
            encoding="utf-8")
        subprocess.run(
            ["npm", "install", "--package-lock-only", "--ignore-scripts", "--silent"],
            cwd=self.repo, check=True, capture_output=True, text=True)
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
            "GIT_AUTHOR_NAME": "Ada Lovelace",
            "GIT_AUTHOR_EMAIL": "ada@example.com",
            "GIT_COMMITTER_NAME": "Ada Lovelace",
            "GIT_COMMITTER_EMAIL": "ada@example.com",
            "GIT_CONFIG_NOSYSTEM": "1",
            **extra,
        }

    def _release(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT), "--bump-file", "package.json", *args],
            cwd=self.repo, env=self._env(), capture_output=True, text=True, check=False)

    def test_release_output_files_and_changelog_match_page(self) -> None:
        result = self._release("--exec", EXEC)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stdout.strip(), _block("next: v1.3.0").strip())
        files = subprocess.run(
            ["git", "show", "--name-only", "--format=", "v1.3.0^{commit}"],
            cwd=self.repo, capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(files, _block("git show --name-only").splitlines()[1:])
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=self.repo,
            capture_output=True, text=True, check=True).stdout
        self.assertEqual(status, "")
        pkg = json.loads((self.repo / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["version"], "1.3.0")
        self.assertEqual(_lock_version(self.repo), "1.3.0")
        text = (self.repo / "CHANGELOG.md").read_text(encoding="utf-8")
        section = text[text.index("## [v1.3.0]"):]
        self.assertEqual(_mask(section), _mask(_block("## [v1.3.0]")))

    def test_without_exec_the_lock_file_is_stale(self) -> None:
        result = self._release()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        pkg = json.loads((self.repo / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["version"], "1.3.0")
        self.assertEqual(_lock_version(self.repo), "1.2.0")
        files = subprocess.run(
            ["git", "show", "--name-only", "--format=", "v1.3.0^{commit}"],
            cwd=self.repo, capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(files, ["CHANGELOG.md", "package.json"])

    def test_release_body_on_tag_push_matches_page(self) -> None:
        self.assertEqual(self._release("--exec", EXEC).returncode, 0)
        code, out, err = _run(["--repo", str(self.repo)])
        self.assertEqual(code, 0, err)
        self.assertEqual(_mask(out), _mask(_block("## What's changed")))
        self.assertNotIn("chore(release)", out)

    @unittest.skipIf(os.name == "nt", "POSIX only")
    def test_tag_check_step(self) -> None:
        self.assertEqual(self._release("--exec", EXEC).returncode, 0)

        def check(ref: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["bash", "-e", "-c", _tag_check_script()], cwd=self.repo,
                env=self._env(GITHUB_REF_NAME=ref),
                capture_output=True, text=True, check=False)

        ok = check("v1.3.0")
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        stale = check("v1.4.0")
        self.assertEqual(stale.returncode, 1)
        self.assertIn("::error::tag v1.4.0 but package.json says 1.3.0", stale.stdout)


if __name__ == "__main__":
    unittest.main()
