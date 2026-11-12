#!/usr/bin/env python3
"""Deterministic generator for a kawaii cat entry image.

Everything is drawn as 1-channel masks and composited, so shapes can never
punch holes in each other. Supersampled 3x then downscaled with Lanczos.
No randomness, no network, no external assets: two runs write the same bytes.
"""
from __future__ import annotations

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W = 1024
SS = 3
C = W * SS


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def mask_new() -> Image.Image:
    return Image.new("L", (C, C), 0)


def paint(base: Image.Image, colour: tuple[int, int, int], mask: Image.Image, alpha: float = 1.0) -> Image.Image:
    """Composite a flat colour onto base through an L mask."""
    a = mask if alpha >= 1.0 else mask.point(lambda v: int(v * alpha))
    layer = Image.new("RGB", (C, C), colour)
    base.paste(layer, (0, 0), a)
    return base


def round_poly(draw: ImageDraw.ImageDraw, pts, r: float, fill=255) -> None:
    """Polygon with rounded corners: polygon + a disc at every vertex."""
    draw.polygon(pts, fill=fill)
    for x, y in pts:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def radial_small(cx: float, cy: float, power: float = 2.0, res: int = 256) -> Image.Image:
    """Soft radial falloff (1 at centre -> 0 at the frame edge), low res."""
    ys = np.linspace(0.0, 1.0, res, dtype=np.float32)[:, None]
    xs = np.linspace(0.0, 1.0, res, dtype=np.float32)[None, :]
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / 0.72
    v = np.clip(1.0 - d, 0.0, 1.0) ** power
    return Image.fromarray((v * 255).astype(np.uint8), "L").resize((C, C), Image.BICUBIC)


def linear_small(top: float, bottom: float) -> Image.Image:
    """Vertical ramp, low res, upscaled."""
    res = 256
    v = np.linspace(top, bottom, res, dtype=np.float32)[:, None] * np.ones((1, res), dtype=np.float32)
    return Image.fromarray(np.clip(v, 0, 255).astype(np.uint8), "L").resize((C, C), Image.BICUBIC)


def heart(draw, cx, cy, size, fill) -> None:
    r = size * 0.27
    top = cy - size * 0.34
    draw.ellipse([cx - size * 0.48, top - r * 0.15, cx - size * 0.48 + 2 * r * 1.28, top + 2 * r * 1.13], fill=fill)
    draw.ellipse([cx + size * 0.48 - 2 * r * 1.28, top - r * 0.15, cx + size * 0.48, top + 2 * r * 1.13], fill=fill)
    draw.polygon(
        [
            (cx - size * 0.47, top + r * 1.15),
            (cx + size * 0.47, top + r * 1.15),
            (cx, cy + size * 0.52),
        ],
        fill=fill,
    )


def sparkle(draw, cx, cy, r, fill) -> None:
    pts = []
    for i in range(8):
        ang = -math.pi / 2 + math.pi / 4 * i
        rad = r if i % 2 == 0 else r * 0.24
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=fill)


# --------------------------------------------------------------------------
# palette + geometry
# --------------------------------------------------------------------------
CREAM = rgb("#FFFBF2")
CREAM_SHADE = rgb("#E8DCD2")
CREAM_DEEP = rgb("#D8C8BE")
PINK = rgb("#FFB6C8")
PINK_DEEP = rgb("#FF93AD")
BLUSH = rgb("#FF9DB4")
INK = rgb("#3A2E3F")
IRIS = rgb("#7A5480")

# geometry, all in supersampled pixels
CX = C // 2
HEAD_CY = int(C * 0.470)
RX = int(C * 0.300)
RY = int(C * 0.278)

BODY_TOP = int(C * 0.640)
BODY_W = int(C * 0.215)
BODY_BOT = int(C * 0.930)


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------
def render() -> Image.Image:
    # ---- background ----------------------------------------------------
    bg = Image.new("RGB", (C, C))
    bg.paste(Image.new("RGB", (C, C), rgb("#FFEAF3")), (0, 0))
    paint(bg, rgb("#F0E8FF"), linear_small(0, 255), 1.0)
    paint(bg, rgb("#D6F7EC"), linear_small(0, 0), 1.0)
    # blend the three bands so nothing looks striped
    grad = Image.new("RGB", (256, 256))
    gd = ImageDraw.Draw(grad)
    for y in range(256):
        t = y / 255.0
        if t < 0.55:
            k = t / 0.55
            a, b = rgb("#FFEAF3"), rgb("#EFE7FF")
        else:
            k = (t - 0.55) / 0.45
            a, b = rgb("#EFE7FF"), rgb("#D6F7EC")
        gd.line(
            [(0, y), (256, y)],
            fill=tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)),
        )
    bg = grad.resize((C, C), Image.BICUBIC)

    # warm glow behind the character
    paint(bg, (255, 255, 255), radial_small(0.5, 0.40, power=2.4), 0.50)
    # corner vignette
    paint(bg, rgb("#B9A7C4"), radial_small(0.5, 0.5, power=3.0), 0.10)

    # ---- body ----------------------------------------------------------
    body = mask_new()
    bd = ImageDraw.Draw(body)
    bd.ellipse([CX - BODY_W, BODY_TOP, CX + BODY_W, BODY_BOT], fill=255)
    paint(bg, CREAM, body)
    paint(bg, CREAM_SHADE, Image.composite(radial_small(0.5, 0.30, 2.2), mask_new(), body), 0.55)

    # ---- head + ears as one silhouette ---------------------------------
    fur = mask_new()
    fd = ImageDraw.Draw(fur)
    fd.ellipse([CX - RX, HEAD_CY - RY, CX + RX, HEAD_CY + RY], fill=255)

    ear_masks = []
    for sx in (-1, 1):
        base_in = (CX + sx * RX * 0.24, HEAD_CY - RY * 0.86)
        base_out = (CX + sx * RX * 1.00, HEAD_CY - RY * 0.24)
        apex = (CX + sx * RX * 0.74, HEAD_CY - RY * 1.62)
        em = mask_new()
        round_poly(ImageDraw.Draw(em), [base_in, base_out, apex], C * 0.020)
        ear_masks.append(em)
        fur = Image.fromarray(np.maximum(np.array(fur), np.array(em)), "L")

    # soft contact shadow so the cream fur separates from the pale bg
    halo = fur.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(C * 0.012))
    paint(bg, rgb("#B49BB0"), halo.filter(ImageFilter.GaussianBlur(C * 0.010)), 0.30)
    paint(bg, CREAM, fur)

    # ---- inner ears (clipped to their own ear so no stray discs) --------
    for sx, em in zip((-1, 1), ear_masks):
        inner = mask_new()
        base_in = (CX + sx * RX * 0.36, HEAD_CY - RY * 0.86)
        base_out = (CX + sx * RX * 0.92, HEAD_CY - RY * 0.40)
        apex = (CX + sx * RX * 0.74, HEAD_CY - RY * 1.38)
        round_poly(ImageDraw.Draw(inner), [base_in, base_out, apex], C * 0.0035)
        inner = Image.fromarray(np.minimum(np.array(inner), np.array(em)), "L")
        inner = inner.filter(ImageFilter.GaussianBlur(C * 0.0018))
        paint(bg, PINK, inner, 0.95)

    # ---- crisp silhouette edge ------------------------------------------
    fur_np = np.array(fur, dtype=np.int16)
    spread = np.array(fur.filter(ImageFilter.GaussianBlur(C * 0.0055)), dtype=np.int16)
    edge_np = np.clip((spread - fur_np) * 2.2, 0, 255).astype(np.uint8)
    edge = Image.fromarray(edge_np, "L").filter(ImageFilter.GaussianBlur(C * 0.0016))
    paint(bg, rgb("#8B7186"), edge, 0.55)
    # inner rim light so the fur does not look flat
    rim_np = np.clip((fur_np - np.array(fur.filter(ImageFilter.GaussianBlur(C * 0.0045)), dtype=np.int16)) * 1.5, 0, 255)
    rim = Image.fromarray(rim_np.astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(C * 0.0018))
    paint(bg, (255, 255, 255), rim, 0.45)

    # ---- shading on the fur --------------------------------------------
    shade = mask_new()
    sd = ImageDraw.Draw(shade)
    sd.ellipse(
        [CX - RX * 1.02, HEAD_CY + RY * 0.22, CX + RX * 1.02, HEAD_CY + RY * 1.30],
        fill=210,
    )
    shade = shade.filter(ImageFilter.GaussianBlur(C * 0.030))
    shade = Image.composite(shade, mask_new(), fur)
    paint(bg, CREAM_SHADE, shade, 0.85)
    deep = Image.composite(radial_small(0.5, 0.60, 1.6), mask_new(), fur)
    paint(bg, CREAM_DEEP, deep, 0.18)

    # ---- blush ---------------------------------------------------------
    eye_dx = int(RX * 0.455)
    eye_cy = HEAD_CY + int(RY * 0.115)
    blush = mask_new()
    bl = ImageDraw.Draw(blush)
    for sx in (-1, 1):
        bl.ellipse(
            [
                CX + sx * eye_dx - int(RX * 0.235),
                eye_cy + int(RY * 0.255),
                CX + sx * eye_dx + int(RX * 0.235),
                eye_cy + int(RY * 0.470),
            ],
            fill=235,
        )
    blush = blush.filter(ImageFilter.GaussianBlur(C * 0.018))
    blush = Image.composite(blush, mask_new(), fur)
    paint(bg, BLUSH, blush, 0.62)

    # ---- eyes ----------------------------------------------------------
    ew = int(RX * 0.300)
    eh = int(RY * 0.375)
    eye_mask = mask_new()
    ed = ImageDraw.Draw(eye_mask)
    for sx in (-1, 1):
        ex = CX + sx * eye_dx
        ed.ellipse([ex - ew, eye_cy - eh, ex + ew, eye_cy + eh], fill=255)
    eye_mask = eye_mask.filter(ImageFilter.GaussianBlur(C * 0.0016))
    paint(bg, INK, eye_mask)

    iris = mask_new()
    ir = ImageDraw.Draw(iris)
    for sx in (-1, 1):
        ex = CX + sx * eye_dx
        ir.ellipse(
            [ex - ew * 0.60, eye_cy + eh * 0.10, ex + ew * 0.60, eye_cy + eh * 0.92],
            fill=255,
        )
    iris = iris.filter(ImageFilter.GaussianBlur(C * 0.009))
    iris = Image.fromarray(np.minimum(np.array(iris), np.array(eye_mask)), "L")
    paint(bg, IRIS, iris, 0.85)

    glint = mask_new()
    gl = ImageDraw.Draw(glint)
    for sx in (-1, 1):
        ex = CX + sx * eye_dx
        # big soft glint, upper-left
        gl.ellipse(
            [ex - ew * 0.70, eye_cy - eh * 0.72, ex - ew * 0.70 + ew * 0.66, eye_cy - eh * 0.72 + ew * 0.66],
            fill=255,
        )
        # small sharp sparkle, lower-right
        gl.ellipse(
            [ex + ew * 0.20, eye_cy + eh * 0.30, ex + ew * 0.20 + ew * 0.30, eye_cy + eh * 0.30 + ew * 0.30],
            fill=255,
        )
    paint(bg, (255, 255, 255), glint)

    # ---- nose + mouth --------------------------------------------------
    nose = mask_new()
    nd = ImageDraw.Draw(nose)
    nose_y = eye_cy + int(RY * 0.300)
    nw = int(RX * 0.052)
    round_poly(
        ImageDraw.Draw(nose),
        [(CX - nw, nose_y), (CX + nw, nose_y), (CX, nose_y + int(nw * 1.25))],
        C * 0.004,
    )
    paint(bg, PINK_DEEP, nose)

    mouth = Image.new("RGB", (C, C), INK)
    mm = mask_new()
    md = ImageDraw.Draw(mm)
    lw = max(2, int(C * 0.0040))
    m_top = nose_y + int(nw * 1.05)
    m_half = int(RX * 0.105)
    m_drop = int(RY * 0.055)
    for sx in (-1, 1):
        box = [
            min(CX, CX + sx * m_half * 2),
            m_top - m_drop,
            max(CX, CX + sx * m_half * 2),
            m_top + m_drop,
        ]
        if sx < 0:
            md.arc(box, start=0, end=80, fill=255, width=lw)
        else:
            md.arc(box, start=100, end=180, fill=255, width=lw)
    mm = mm.filter(ImageFilter.GaussianBlur(C * 0.0007))
    bg.paste(mouth, (0, 0), mm)

    # ---- whiskers -------------------------------------------------------
    whisk = mask_new()
    wd = ImageDraw.Draw(whisk)
    wy = nose_y + int(RY * 0.010)
    for sx in (-1, 1):
        for dy, ln in ((-0.075, 0.30), (0.0, 0.335), (0.072, 0.295)):
            x0 = CX + sx * int(RX * 0.60)
            x1 = CX + sx * int(RX * (0.60 + ln))
            wd.line(
                [(x0, wy + int(RY * dy)), (x1, wy + int(RY * (dy - 0.030)))],
                fill=200,
                width=max(2, int(C * 0.0026)),
            )
    whisk = whisk.filter(ImageFilter.GaussianBlur(C * 0.0012))
    paint(bg, rgb("#A9959F"), whisk, 0.75)

    # ---- paws -----------------------------------------------------------
    paws = mask_new()
    pd = ImageDraw.Draw(paws)
    for sx in (-1, 1):
        px = CX + sx * int(C * 0.098)
        py = int(C * 0.885)
        pd.ellipse(
            [px - int(C * 0.046), py - int(C * 0.034), px + int(C * 0.046), py + int(C * 0.034)],
            fill=255,
        )
    paint(bg, CREAM, paws)
    pd2 = mask_new()
    d2 = ImageDraw.Draw(pd2)
    for sx in (-1, 1):
        px = CX + sx * int(C * 0.098)
        py = int(C * 0.885)
        d2.ellipse(
            [px - int(C * 0.046), py + int(C * 0.004), px + int(C * 0.046), py + int(C * 0.034)],
            fill=180,
        )
    pd2 = pd2.filter(ImageFilter.GaussianBlur(C * 0.006))
    pd2 = Image.fromarray(np.minimum(np.array(pd2), np.array(paws)), "L")
    paint(bg, CREAM_SHADE, pd2, 0.9)

    # ---- ground shadow --------------------------------------------------
    shadow = mask_new()
    ImageDraw.Draw(shadow).ellipse(
        [CX - int(C * 0.275), int(C * 0.905), CX + int(C * 0.275), int(C * 0.960)], fill=150
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(C * 0.020))
    paint(bg, rgb("#B49BB0"), shadow, 0.35)

    # ---- decorations ----------------------------------------------------
    deco = mask_new()
    dd = ImageDraw.Draw(deco)
    for fx, fy, fs, al in (
        (0.135, 0.215, 0.105, 255),
        (0.855, 0.265, 0.072, 230),
        (0.800, 0.620, 0.046, 200),
        (0.185, 0.640, 0.038, 190),
    ):
        heart(dd, int(C * fx), int(C * fy), int(C * fs), al)
    soft = deco.filter(ImageFilter.GaussianBlur(C * 0.0012))
    paint(bg, PINK, soft)

    spk = mask_new()
    sp = ImageDraw.Draw(spk)
    for fx, fy, fs, al in (
        (0.290, 0.130, 0.042, 255),
        (0.700, 0.110, 0.030, 240),
        (0.895, 0.445, 0.026, 225),
        (0.100, 0.385, 0.024, 210),
        (0.640, 0.775, 0.020, 190),
        (0.335, 0.815, 0.017, 180),
    ):
        sparkle(sp, int(C * fx), int(C * fy), int(C * fs), al)
    paint(bg, (255, 255, 255), spk)

    return bg.resize((W, W), Image.LANCZOS)


def main() -> None:
    img = render()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.abspath(os.path.join(here, "..", "entry.png"))
    img.save(out, format="PNG", optimize=True)
    print(f"wrote {out} {os.path.getsize(out)} bytes {img.size}")
    print("sha256 head:", __import__("hashlib").sha256(open(out, "rb").read()).hexdigest()[:16])


if __name__ == "__main__":
    main()
