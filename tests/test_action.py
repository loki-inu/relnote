"""Run the shell step of action.yml the way GitHub Actions does (bash + env).

Covers: notes + has-changes=true, the clean no-op when there are no new
commits (has-changes=false, empty notes and next-version), fail-on-empty,
and that real errors (unknown ref) still fail the step.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_monorepo import _commit
from tests.test_output import _git, _init_repo

ROOT = Path(__file__).resolve().parent.parent
ACTION = ROOT / "action.yml"


def _run_script() -> str:
    """The `run: |` block of the composite step, de-indented."""
    lines = ACTION.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "run: |") + 1
    indent = len(lines[start]) - len(lines[start].lstrip())
    body = []
    for line in lines[start:]:
        if line.strip() and len(line) - len(line.lstrip()) < indent:
            break
        body.append(line[indent:])
    script = "\n".join(body) + "\n"
    assert "${{" not in script, "run block must read inputs from env only"
    return script


def _parse_outputs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    lines = iter(text.splitlines())
    for line in lines:
        if "<<" in line:
            key, delim = line.split("<<", 1)
            value = []
            for inner in lines:
                if inner == delim:
                    break
                value.append(inner)
            out[key] = "\n".join(value)
        elif "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out


class ActionMetadataTests(unittest.TestCase):
    def test_plain_values_have_no_colon_space(self) -> None:
        # "key: text (default: x)" is invalid YAML; quote such values.
        for number, line in enumerate(ACTION.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"^\s*[\w-]+: (.*)$", line)
            if not match:
                continue
            value = match.group(1)
            if value.startswith(("'", '"', "|", "${{")):
                continue
            self.assertNotIn(": ", value, f"action.yml line {number}: quote this value")

    def test_documented_inputs_and_outputs(self) -> None:
        text = ACTION.read_text(encoding="utf-8")
        for name in ("include-release-commits:", "fail-on-empty:", "has-changes:"):
            self.assertIn(name, text)


@unittest.skipIf(
    shutil.which("bash") is None or sys.platform == "win32",
    "composite step runs in bash on Linux/macOS runners",
)
class ActionStepTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        _init_repo(self.repo)
        _git(["tag", "v1.0.0"], self.repo)
        self.script = _run_script()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def step(self, **inputs: str) -> tuple[int, dict[str, str], str]:
        output_file = Path(self._tmp.name) / "github_output"
        output_file.write_text("", encoding="utf-8")
        env = {
            **os.environ,
            "GITHUB_OUTPUT": str(output_file),
            "RELNOTE_MAIN": str(ROOT / "relnote" / "__main__.py"),
            "INPUT_FORMAT": "github",
            "INPUT_NO_BOTS": "true",
            "INPUT_REPO": str(self.repo),
            "INPUT_INCLUDE_RELEASE_COMMITS": "false",
            "INPUT_FAIL_ON_EMPTY": "false",
        }
        for key, value in inputs.items():
            env["INPUT_" + key.upper()] = value
        # GitHub runs: bash --noprofile --norc -eo pipefail {0}
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", self.script],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return (
            result.returncode,
            _parse_outputs(output_file.read_text(encoding="utf-8")),
            result.stdout + result.stderr,
        )

    def test_new_commits_give_notes_and_next_version(self) -> None:
        _commit(self.repo, "a.txt", "feat: add a")
        code, out, log = self.step()
        self.assertEqual(code, 0, log)
        self.assertEqual(out["has-changes"], "true")
        self.assertEqual(out["next-version"], "v1.1.0")
        self.assertIn("add a", out["notes"])

    def test_tag_push_names_the_new_tag(self) -> None:
        # on: push: tags -> HEAD is the new tag; notes cover the previous tag..new tag
        _git(["remote", "add", "origin", "https://github.com/acme/app.git"], self.repo)
        _commit(self.repo, "a.txt", "fix: patch it")
        _git(["tag", "v1.0.1"], self.repo)
        code, out, log = self.step()
        self.assertEqual(code, 0, log)
        self.assertEqual(out["has-changes"], "true")
        self.assertIn("patch it", out["notes"])
        self.assertIn("compare/v1.0.0...v1.0.1", out["notes"])
        self.assertEqual(out["next-version"], "v1.0.1")

    def test_no_new_commits_is_a_clean_no_op(self) -> None:
        code, out, log = self.step(since="v1.0.0")
        self.assertEqual(code, 0, log)
        self.assertEqual(out, {"has-changes": "false", "next-version": "", "notes": ""})
        self.assertIn("nothing to release", log)

    def test_only_release_commit_is_a_no_op(self) -> None:
        _commit(self.repo, "CHANGELOG.md", "chore(release): v1.0.1")
        code, out, log = self.step()
        self.assertEqual((code, out["has-changes"]), (0, "false"), log)
        code, out, log = self.step(include_release_commits="true")
        self.assertEqual((code, out["has-changes"]), (0, "true"), log)
        self.assertIn("v1.0.1", out["notes"])

    def test_unchanged_package_in_monorepo_is_a_no_op(self) -> None:
        _commit(self.repo, "packages/web/w.txt", "feat(web): page")
        code, out, log = self.step(path="packages/api\n", tag_prefix="v")
        self.assertEqual((code, out["has-changes"], out["notes"]), (0, "false", ""), log)
        code, out, log = self.step(path="packages/web\n")
        self.assertEqual((code, out["has-changes"]), (0, "true"), log)

    def test_no_changelog_written_when_empty(self) -> None:
        code, out, log = self.step(since="v1.0.0", changelog="CHANGELOG.md")
        self.assertEqual((code, out["has-changes"]), (0, "false"), log)
        self.assertFalse((self.repo / "CHANGELOG.md").exists())

    def test_fail_on_empty(self) -> None:
        code, out, log = self.step(since="v1.0.0", fail_on_empty="true")
        self.assertEqual(code, 1, log)
        self.assertNotIn("has-changes", out)
        self.assertIn("no commits in range", log)

    def test_unknown_ref_still_fails(self) -> None:
        code, out, log = self.step(since="no-such-ref")
        self.assertEqual(code, 1, log)
        self.assertIn("unknown ref", log)
        self.assertNotIn("has-changes", out)


if __name__ == "__main__":
    unittest.main()
