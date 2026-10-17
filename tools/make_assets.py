import sys, os, json, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "icona-assets") + "/"
PHOTOS = os.path.join(ROOT, "photos") + "/"   # put the original photos here (not committed)
MUSIC = None                                   # --music FILE (one 7 s clip) or DIR (pool of 7 s clips, one per item: pool[n % len])
FD = "/usr/share/fonts/truetype/freefont/"
# Brand palette B (locked 2026-10-17): bottle green, ivory, dusty pink, brass, oxblood.
BG = (31, 74, 55)        # #1F4A37 bottle green: backgrounds, bands
CREAM = (244, 234, 213)  # #F4EAD5 ivory: titles, pills
GOLD = (184, 137, 59)    # #B8893B brass: frame lines, price badge fill
PINK = (232, 167, 176)   # #E8A7B0 dusty pink: sub-lines and CTAs on green (4.8:1)
OXBLOOD = (122, 34, 48)  # #7A2230 text on ivory/brass (pill text, badge text and ring)

FONTS = {
    "SERIF": FD + "FreeSerif.ttf",
    "SERIFB": FD + "FreeSerifBold.ttf",
    "SANS": FD + "FreeSans.ttf",
    "SANSB": FD + "FreeSansBold.ttf",
}
_fc = {}


def font(name, size):
    k = (name, int(size))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONTS[name], int(size))
    return _fc[k]


def _load_items():
    d = json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))
    return {i["n"]: dict(img=i.get("photo", i["slug"]), brand=i["brand_upper"], desc=i["desc"],
                         price=str(i["price"]), slug=i["slug"], n=i["n"]) for i in d}


ITEMS = _load_items()


def load(it):
    im = Image.open(PHOTOS + it["img"] + ".jpg")
    return ImageOps.exif_transpose(im).convert("RGB")


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def spaced(d, text, f, tracking, cx, cy, fill):
    width = sum(f.getlength(c) for c in text) + tracking * (len(text) - 1)
    x = cx - width / 2
    for c in text:
        d.text((x, cy), c, font=f, fill=fill, anchor="lm")
        x += f.getlength(c) + tracking
    return width


def fit_font(name, text, maxw, start, minsize=20):
    s = start
    f = font(name, s)
    while f.getlength(text) > maxw and s > minsize:
        s -= 2
        f = font(name, s)
    return f


def sprite_badge(text, r):
    S = 4
    size = (2 * r + 16) * S
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size // 2
    d.ellipse((c - r * S, c - r * S, c + r * S, c + r * S), fill=GOLD + (255,))
    d.ellipse((c - (r - 9) * S, c - (r - 9) * S, c + (r - 9) * S, c + (r - 9) * S), outline=OXBLOOD + (255,), width=3 * S)
    f = fit_font("SERIFB", text, 1.35 * r * S, int(r * S * 0.75))
    d.text((c, c), text, font=f, fill=OXBLOOD + (255,), anchor="mm")
    return im.resize((size // S, size // S), Image.LANCZOS)


def sprite_pill(text, size_px=30, tracking=3, pad=(26, 14)):
    S = 4
    f = font("SANSB", size_px * S)
    tw = sum(f.getlength(c) for c in text) + tracking * S * (len(text) - 1)
    w = int(tw + 2 * pad[0] * S)
    h = int(size_px * S + 2 * pad[1] * S)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=CREAM + (255,))
    spaced(d, text, f, tracking * S, w / 2, h / 2, OXBLOOD)
    return im.resize((w // S, h // S), Image.LANCZOS)


def paste_sprite(img, sp, center, alpha=1.0):
    x = int(center[0] - sp.width / 2)
    y = int(center[1] - sp.height / 2)
    a = sp.getchannel("A")
    if alpha < 1.0:
        a = a.point(lambda v: int(v * alpha))
    img.paste(sp.convert("RGB"), (x, y), a)


def price_txt(it):
    return it["price"] + " €"


# ---------------------------------------------------------------- post 4:5
def build_post(it):
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), BG)
    p = load(it).resize((900, 1200), Image.LANCZOS)
    img.paste(p, (90, 40))
    d = ImageDraw.Draw(img)
    d.rectangle((90, 40, 989, 1239), outline=GOLD, width=3)
    paste_sprite(img, sprite_pill("NOVEDAD · PIEZA ÚNICA", 26, 3), (330, 95))
    paste_sprite(img, sprite_badge(price_txt(it), 92), (952, 150))
    f1 = fit_font("SERIFB", it["brand"], 940, 50)
    spaced(d, it["brand"], f1, 4, W / 2, 1272, CREAM)
    f2 = fit_font("SANS", it["desc"], 960, 27)
    d.text((W / 2, 1316), it["desc"] + "  ·  Ruzafa, València", font=fit_font("SANS", it["desc"] + "  ·  Ruzafa, València", 980, 26), fill=PINK, anchor="mm")
    return img


# ---------------------------------------------------------------- pin 2:3
def build_pin(it):
    W, H = 1000, 1500
    img = Image.new("RGB", (W, H), BG)
    p = load(it).resize((1000, 1333), Image.LANCZOS)
    img.paste(p, (0, 0))
    d = ImageDraw.Draw(img)
    paste_sprite(img, sprite_pill("ICONA VINTAGE · VALENCIA", 24, 3), (270, 62))
    line1 = it["brand"] + "  ·  " + price_txt(it)
    d.text((W / 2, 1333 + 52), line1, font=fit_font("SERIFB", line1, 940, 56), fill=CREAM, anchor="mm")
    line2 = "Ver en Vinted  ·  Icona Vintage, Ruzafa (Valencia)"
    d.text((W / 2, 1333 + 118), line2, font=fit_font("SANS", line2, 940, 30), fill=PINK, anchor="mm")
    return img


# ---------------------------------------------------------------- reel 9:16
def reel_backgrounds(it):
    W, H = 1080, 1920
    ctas = ["Abierto todos los días · 10:00–20:00 · Ruzafa", "Reserva por DM  ·  Compra en Vinted (link en bio)"]
    outs = []
    for cta in ctas:
        bg = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(bg)
        spaced(d, "ICONA", font("SERIF", 70), 12, W / 2, 80, CREAM)
        ry = 132
        d.line((W / 2 - 150, ry, W / 2 - 14, ry), fill=GOLD, width=2)
        d.line((W / 2 + 14, ry, W / 2 + 150, ry), fill=GOLD, width=2)
        d.polygon([(W / 2, ry - 7), (W / 2 + 7, ry), (W / 2, ry + 7), (W / 2 - 7, ry)], fill=GOLD)
        spaced(d, "VINTAGE · VALENCIA", font("SERIF", 28), 9, W / 2, 175, PINK)
        f1 = fit_font("SERIFB", it["brand"], 980, 66)
        spaced(d, it["brand"], f1, 5, W / 2, 1462, CREAM)
        fd = font("SANS", 34)
        lines = wrap(it["desc"], fd, 960)
        y = 1522
        for ln in lines:
            d.text((W / 2, y), ln, font=fd, fill=CREAM, anchor="mm")
            y += 38
        d.text((W / 2, 1602), cta, font=fit_font("SANSB", cta, 980, 30), fill=PINK, anchor="mm")
        outs.append(bg)
    return outs


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def build_reel(it, path, seconds=7.0, fps=30):
    W, H = 1080, 1920
    src = load(it)
    bgA, bgB = reel_backgrounds(it)
    badge = sprite_badge(price_txt(it), 100)
    pill = sprite_pill("NOVEDAD · PIEZA ÚNICA", 26, 3)
    n = int(seconds * fps)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        *(["-i", music_for(it)] if MUSIC else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]),
        "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k" if MUSIC else "64k", "-shortest", "-movflags", "+faststart", path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    base_w, base_h = 892, 1190
    wx, wy = 94, 215
    for i in range(n):
        t = i / fps
        # background with cross-fade of the bottom CTA line at 3.4s
        a = max(0.0, min(1.0, (t - 3.4) / 0.35))
        frame = Image.blend(bgA, bgB, a) if 0 < a < 1 else (bgB if a >= 1 else bgA)
        frame = frame.copy()
        s = 1.0 + 0.08 * (t / seconds)
        zw, zh = int(base_w * s), int(base_h * s)
        z = src.resize((zw, zh), Image.BICUBIC)
        l, tp = (zw - base_w) // 2, (zh - base_h) // 2
        frame.paste(z.crop((l, tp, l + base_w, tp + base_h)), (wx, wy))
        d = ImageDraw.Draw(frame)
        d.rectangle((wx, wy, wx + base_w - 1, wy + base_h - 1), outline=GOLD, width=3)
        pa = ease_out((t - 0.2) / 0.4)
        if pa > 0:
            paste_sprite(frame, pill, (wx + 22 + pill.width / 2, wy + 52), alpha=pa)
        # badge pop with slight overshoot
        bt = (t - 0.5) / 0.45
        if bt > 0:
            k = ease_out(bt)
            sc = k * (1.0 + 0.12 * (1 - k) * 2) if bt < 1 else 1.0
            sc = min(sc, 1.12)
            if sc > 0.02:
                sp = badge.resize((max(2, int(badge.width * sc)), max(2, int(badge.height * sc))), Image.LANCZOS)
                paste_sprite(frame, sp, (wx + base_w - 6 - badge.width / 2, wy + 30 + badge.height / 2))
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()


def music_for(it):
    """Single file, or a directory pool: clip chosen by item number so the choice is stable."""
    if os.path.isdir(MUSIC):
        pool = sorted(f for f in os.listdir(MUSIC) if f.lower().endswith((".wav", ".mp3", ".m4a")))
        if not pool:
            sys.exit(f"no audio clips in {MUSIC}")
        return os.path.join(MUSIC, pool[(int(it["n"]) - 1) % len(pool)])
    return MUSIC


def main():
    global MUSIC
    args = sys.argv[1:]
    global OUT
    if "--out" in args:
        k = args.index("--out"); OUT = args[k + 1].rstrip("/") + "/"; del args[k:k + 2]
    if "--photos" in args:
        k = args.index("--photos"); globals()["PHOTOS"] = args[k + 1].rstrip("/") + "/"; del args[k:k + 2]
    if "--music" in args:
        k = args.index("--music"); MUSIC = args[k + 1]; del args[k:k + 2]
    nums = [int(x) for x in args[0].split(",")]
    what = args[1] if len(args) > 1 else "all"
    os.makedirs(OUT, exist_ok=True)
    for n in nums:
        it = ITEMS[n]
        stem = f"{OUT}item{n:02d}-{it['slug']}"
        if what in ("all", "images"):
            build_post(it).save(stem + "_post-4x5.jpg", quality=92, optimize=True)
            build_pin(it).save(stem + "_pin-2x3.jpg", quality=92, optimize=True)
        if what in ("all", "reel"):
            build_reel(it, stem + ("_reel-9x16-music.mp4" if MUSIC else "_reel-9x16.mp4"))
        print("done", n, flush=True)


if __name__ == "__main__":
    main()
