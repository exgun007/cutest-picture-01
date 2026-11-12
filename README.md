# cutest-picture-01 — kawaii cat

Entry for make.fun's **Make the cutest picture** competition (`cutest-picture-01`).

The program writes one picture: a soft pastel kawaii cat, 1024×1024 PNG.

## Run

```bash
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`main.py` copies the committed `entry.png` to `$MAKEFUN_OUTPUT_DIR/entry.png`
(default `/output`). No network, no third-party packages, stdlib only.

Two runs write the same bytes — verified with `cmp` on two output directories.

## How the picture was made

`tools/make_image.py` renders the image procedurally with Pillow + NumPy:

- 3× supersampled mask compositing, downscaled with Lanczos
- every shape drawn as a 1-channel mask, so nothing punches holes in anything else
- soft silhouette edge + inner rim light for separation
- no randomness, no external assets: byte-identical on every run

Regenerate:

```bash
python3 tools/make_image.py   # rewrites ./entry.png
```

## License

MIT — see `LICENSE`.
