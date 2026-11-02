"""The Rust crate walkthrough on docs/rust-crate.html, run for real.

Builds the page's Cargo.toml and history in a scratch repository, runs
examples/release.sh --bump-file Cargo.toml --exec "cargo update --workspace"
with real cargo (offline), and compares the script output, release commit
files, CHANGELOG.md section, and Release body with the page. Checks that
Cargo.lock is in sync afterwards (cargo metadata --locked) and runs the
workflow's tag check step against matching and stale tags.
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
PAGE = ROOT / "docs" / "rust-crate.html"
SCRIPT = ROOT / "examples" / "release.sh"
HASH = re.compile(r"\(`[0-9a-f]{7,}`\)")
DATE = re.compile(r"\] - \d{4}-\d{2}-\d{2}")
EXEC = "cargo update --workspace"


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
    tail = workflow.split("- name: Tag matches Cargo.toml", 1)[1]
    script = tail.split("        run: |\n", 1)[1].split("      - run:", 1)[0]
    return textwrap.dedent(script)


class RustCratePageStaticTests(unittest.TestCase):
    def test_page_runs_the_pinned_script_with_cargo_lock_sync(self) -> None:
        block = _block("curl -fsSLO")
        self.assertIn(f'bash release.sh --bump-file Cargo.toml --exec "{EXEC}"', block)
        version = re.search(r"/relnote/(v[\d.]+)/examples/release.sh", block).group(1)
        self.assertIn(f"uses: loki-inu/relnote@{version}", _block("name: Release"))

    def test_workflow_publishes_locked_with_trusted_publishing(self) -> None:
        workflow = _block("name: Release")
        self.assertIn("id-token: write", workflow)
        self.assertIn("rust-lang/crates-io-auth-action@v1", workflow)
        self.assertIn("cargo publish --locked", workflow)
        self.assertLess(workflow.index("cargo publish"), workflow.index("gh release create"))


@unittest.skipIf(shutil.which("bash") is None or shutil.which("cargo") is None,
                 "bash and cargo needed")
class RustCratePageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.repo = base / "repo"
        self.cargo_home = base / "cargo-home"
        (self.repo / "src").mkdir(parents=True)
        _git(["init", "--initial-branch=main"], self.repo)
        _git(["remote", "add", "origin", "https://github.com/you/demo.git"], self.repo)
        (self.repo / "Cargo.toml").write_text(
            _block("[package]") + "\n", encoding="utf-8", newline="\n")
        (self.repo / "src" / "lib.rs").write_text("", encoding="utf-8")
        (self.repo / ".gitignore").write_text("/target\n", encoding="utf-8")
        self._cargo("generate-lockfile")
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
            "CARGO_HOME": str(self.cargo_home),
            "CARGO_NET_OFFLINE": "true",
            "GIT_AUTHOR_NAME": "Ada Lovelace",
            "GIT_AUTHOR_EMAIL": "ada@example.com",
            "GIT_COMMITTER_NAME": "Ada Lovelace",
            "GIT_COMMITTER_EMAIL": "ada@example.com",
            "GIT_CONFIG_NOSYSTEM": "1",
            **extra,
        }

    def _cargo(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["cargo", *args], cwd=self.repo, env=self._env(),
                              capture_output=True, text=True, check=False)

    def _release(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["bash", str(SCRIPT), "--bump-file", "Cargo.toml", *args],
                              cwd=self.repo, env=self._env(), capture_output=True, text=True,
                              check=False)

    def test_release_output_files_and_changelog_match_page(self) -> None:
        result = self._release("--exec", EXEC)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), _block("next: v1.3.0").strip())
        files = subprocess.run(["git", "show", "--name-only", "--format=", "v1.3.0^{commit}"],
                               cwd=self.repo, capture_output=True, text=True,
                               check=True).stdout.split()
        self.assertEqual(files, _block("git show --name-only").splitlines()[1:])
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.repo,
                                capture_output=True, text=True, check=True).stdout
        self.assertEqual(status, "")
        locked = self._cargo("metadata", "--locked", "--format-version", "1")
        self.assertEqual(locked.returncode, 0, locked.stderr)
        text = (self.repo / "CHANGELOG.md").read_text(encoding="utf-8")
        section = text[text.index("## [v1.3.0]"):]
        self.assertEqual(_mask(section), _mask(_block("## [v1.3.0]")))

    def test_without_exec_the_lock_file_is_stale(self) -> None:
        result = self._release()
        self.assertEqual(result.returncode, 0, result.stderr)
        locked = self._cargo("metadata", "--locked", "--format-version", "1")
        self.assertNotEqual(locked.returncode, 0)
        self.assertIn("needs to be updated but --locked was passed", locked.stderr)

    def test_release_body_on_tag_push_matches_page(self) -> None:
        self.assertEqual(self._release("--exec", EXEC).returncode, 0)
        code, out, err = _run(["--repo", str(self.repo)])
        self.assertEqual(code, 0, err)
        self.assertEqual(_mask(out), _mask(_block("## What's changed")))
        self.assertNotIn("chore(release)", out)

    @unittest.skipIf(os.name == "nt" or shutil.which("jq") is None, "POSIX with jq only")
    def test_tag_check_step(self) -> None:
        self.assertEqual(self._release("--exec", EXEC).returncode, 0)

        def check(ref: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(["bash", "-e", "-c", _tag_check_script()], cwd=self.repo,
                                  env=self._env(GITHUB_REF_NAME=ref),
                                  capture_output=True, text=True, check=False)

        ok = check("v1.3.0")
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        stale = check("v1.4.0")
        self.assertEqual(stale.returncode, 1)
        self.assertIn("::error::tag v1.4.0 but Cargo.toml says 1.3.0", stale.stdout)


if __name__ == "__main__":
    unittest.main()
