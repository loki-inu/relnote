#!/usr/bin/env python3
"""Build relnote as a single executable file.

Writes three files to dist/ (or --dist DIR):

  relnote        Python zipapp with a "#!/usr/bin/env python3" shebang, executable
  relnote.pyz    the same bytes, for "python3 relnote.pyz" on Windows
  SHA256SUMS     sha256sum-compatible checksums of the two files

The archive contains only the relnote package and LICENSE, so it has no
dependencies beyond Python 3.11+ and git on PATH. Running it never needs
the source tree: "relnote --repo /any/project" works from anywhere.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTERPRETER = "/usr/bin/env python3"
# Fixed mtime for archive members so rebuilding the same tree gives the same bytes.
# zipfile rejects timestamps before 1980, so use 2000-01-01 (UTC) unless
# SOURCE_DATE_EPOCH asks for something else.
DEFAULT_EPOCH = 946684800
MAIN_PY = "from relnote.__main__ import main\n\nraise SystemExit(main())\n"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(dist: Path) -> list[Path]:
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", DEFAULT_EPOCH))
    dist.mkdir(parents=True, exist_ok=True)
    pyz = dist / "relnote.pyz"
    exe = dist / "relnote"
    sums = dist / "SHA256SUMS"

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "app"
        shutil.copytree(
            ROOT / "relnote",
            stage / "relnote",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copyfile(ROOT / "LICENSE", stage / "LICENSE")
        (stage / "__main__.py").write_text(MAIN_PY, encoding="utf-8")
        for path in stage.rglob("*"):
            os.utime(path, (epoch, epoch))
        zipapp.create_archive(stage, pyz, interpreter=INTERPRETER, compressed=True)

    shutil.copyfile(pyz, exe)
    for path in (exe, pyz):
        path.chmod(0o755)
    sums.write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in (exe, pyz)),
        encoding="utf-8",
    )
    return [exe, pyz, sums]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dist",
        type=Path,
        default=ROOT / "dist",
        help="output directory (default: dist/ next to pyproject.toml)",
    )
    args = parser.parse_args(argv)
    for path in build(args.dist):
        print(f"{path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
