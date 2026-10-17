"""Retrofit already-built pins and reels to the current brand palette (see make_assets.py) WITHOUT
touching the item photo. Used once on 2026-10-17 when palette B replaced the old burgundy/gold look,
because the original photos are not stored in this repo.

  python3 tools/rebrand.py 5,6,1 [--src icona-assets] [--out DIR]

Pin:  repaints only the bottom band (y >= 1333) and the "ICONA VINTAGE · VALENCIA" pill.
Reel: rebuilds the background (title, sub-lines, CTAs, frame line) and overlays the ORIGINAL photo window
      (crop 886x1184 at 97,218) with its zoom, price badge and pill, plus the original audio (copied).
New batches should use make_assets.py directly (it already has the new palette).
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_assets as M  # noqa: E402

WX, WY, BW, BH = 94, 215, 892, 1190  # photo window used by make_assets.build_reel


def rebrand_pin(it, src, dst):
    im = Image.open(src).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1333, W, H), fill=M.BG)
    line1 = it["brand"] + "  ·  " + M.price_txt(it)
    d.text((W / 2, 1333 + 52), line1, font=M.fit_font("SERIFB", line1, 940, 56), fill=M.CREAM, anchor="mm")
    line2 = "Ver en Vinted  ·  Icona Vintage, Ruzafa (Valencia)"
    d.text((W / 2, 1333 + 118), line2, font=M.fit_font("SANS", line2, 940, 30), fill=M.PINK, anchor="mm")
    M.paste_sprite(im, M.sprite_pill("ICONA VINTAGE · VALENCIA", 24, 3), (270, 62))
    im.save(dst, quality=92, optimize=True)


def rebrand_reel(it, src, dst):
    bgA, bgB = M.reel_backgrounds(it)
    for bg in (bgA, bgB):
        ImageDraw.Draw(bg).rectangle((WX, WY, WX + BW - 1, WY + BH - 1), outline=M.GOLD, width=3)
    with tempfile.TemporaryDirectory() as tmp:
        pa, pb = os.path.join(tmp, "a.png"), os.path.join(tmp, "b.png")
        bgA.save(pa)
        bgB.save(pb)
        fc = (
            "[2:v]format=rgba,fade=t=in:st=3.4:d=0.35:alpha=1[b2];"
            "[1:v][b2]overlay=format=auto[bg];"
            "[0:v]crop=886:1184:97:218[w];"
            "[bg][w]overlay=97:218:format=auto,format=yuv420p[v]"
        )
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-loop", "1", "-i", pa, "-loop", "1", "-i", pb,
               "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-t", "7", "-r", "30",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
               "-c:a", "copy", "-movflags", "+faststart", dst]
        subprocess.run(cmd, check=True)


def main():
    args = sys.argv[1:]
    src_dir, out_dir = os.path.join(M.ROOT, "icona-assets"), None
    if "--src" in args:
        k = args.index("--src"); src_dir = args[k + 1]; del args[k:k + 2]
    if "--out" in args:
        k = args.index("--out"); out_dir = args[k + 1]; del args[k:k + 2]
    out_dir = out_dir or src_dir
    os.makedirs(out_dir, exist_ok=True)
    for n in [int(x) for x in args[0].split(",")]:
        it = M.ITEMS[n]
        stem = f"item{n:02d}-{it['slug']}"
        rebrand_pin(it, f"{src_dir}/{stem}_pin-2x3.jpg", f"{out_dir}/{stem}_pin-2x3.jpg")
        rebrand_reel(it, f"{src_dir}/{stem}_reel-9x16-music.mp4", f"{out_dir}/{stem}_reel-9x16-music.mp4")
        print("rebranded", n, flush=True)


if __name__ == "__main__":
    main()
