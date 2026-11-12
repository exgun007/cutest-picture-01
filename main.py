#!/usr/bin/env python3
"""Entry program for make.fun "Make the cutest picture" (cutest-picture-01).

Writes one whole PNG, 1024x1024, to $MAKEFUN_OUTPUT_DIR/entry.png.

The picture is a kawaii cat generated deterministically by tools/make_image.py
and committed in this repository. This program copies those exact bytes, so it
needs no network access and no third-party packages, and two runs always write
the same bytes.

Run locally:
    MAKEFUN_OUTPUT_DIR=out python3 main.py
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "entry.png"
OUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / "entry.png"
    shutil.copyfile(SOURCE, target)
    print(f"wrote {target} {target.stat().st_size} bytes")


if __name__ == "__main__":
    main()
