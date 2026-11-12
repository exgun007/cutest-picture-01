#!/usr/bin/env python3
"""Copy the committed 1024x1024 entry.png into the grader's output directory.

The picture is the PNG sitting next to this file. It is copied byte-for-byte
(no decoding, no re-encoding), so runs are deterministic and always produce an
identical file. Stdlib only, no network, no randomness.

Output directory: $MAKEFUN_OUTPUT_DIR, or /output when unset. The copied file is
always named entry.png and the directory is created recursively if needed.

Local run:

    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py

Any failure (missing/unreadable source, unwritable output) prints one clear
message on stderr and exits 1.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "entry.png"
OUTPUT_NAME = "entry.png"
FALLBACK_OUTPUT_DIR = "/output"


def resolve_output_dir() -> Path:
    """Return the target directory: $MAKEFUN_OUTPUT_DIR, else /output."""
    return Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or FALLBACK_OUTPUT_DIR)


def fail(message: str) -> int:
    """Print one clear stderr message and return the failure exit code."""
    print(f"error: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if not SOURCE.is_file():
        return fail(f"source image not found at {SOURCE} (it must sit next to main.py)")
    if not os.access(SOURCE, os.R_OK):
        return fail(f"source image is not readable: {SOURCE}")

    out_dir = resolve_output_dir()
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return fail(f"cannot create output directory {out_dir}: {exc}")

    target = out_dir / OUTPUT_NAME
    try:
        # Verbatim byte copy: no decoding, no re-encoding, no metadata rewriting.
        shutil.copyfile(SOURCE, target)
    except OSError as exc:
        return fail(f"cannot copy {SOURCE} to {target}: {exc}")

    print(f"wrote {target} {target.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
