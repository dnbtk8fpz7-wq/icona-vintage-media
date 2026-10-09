#!/usr/bin/env python3
"""Build the Metricool `info` payloads for Icona Vintage posts from data/items.json + data/schedule.json.

Usage:
  python3 tools/payloads.py            # writes payloads/<date>.json for every scheduled day
  python3 tools/payloads.py 2026-10-11 # print one day

Each day has 3 posts: ig_tiktok (10:00 Reel), facebook (10:00 Reel), pinterest (18:00 pin).
Posts are always created with blogId 7281190 (Icona Vintage Valencia) and Europe/Madrid.
Never hand-write captions: generate them here so every post follows the same rules.
"""
import datetime, json, os, re, sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://raw.githubusercontent.com/dnbtk8fpz7-wq/icona-vintage-media/icona-assets/icona-assets/"
BLOG_ID = "7281190"
TZ = "Europe/Madrid"
ADDR = "Carrer del Músic Padilla, 2 (Ruzafa), Valencia"
HOURS = "Abrimos todos los días de 10:00 a 20:00"
BASE_TAGS = "#iconavintage #vintagevalencia #ruzafa #segundamanovalencia"


def fmt_price(p):
    """65 -> '65 €', 65.5 -> '65,5 €' (Spanish decimal comma)."""
    s = str(int(p)) if float(p).is_integer() else str(p).replace(".", ",")
    return f"{s} €"


def offset_iso(date, hhmm):
    """'2026-10-11','10:00' -> '2026-10-11T10:00:00+02:00' (correct across the 2026-10-25 DST change)."""
    dt = datetime.datetime.fromisoformat(f"{date}T{hhmm}:00").replace(tzinfo=ZoneInfo(TZ))
    return dt.isoformat()


def load():
    items = {i["n"]: i for i in json.load(open(os.path.join(ROOT, "data/items.json"), encoding="utf-8"))}
    sched = json.load(open(os.path.join(ROOT, "data/schedule.json"), encoding="utf-8"))
    return items, sched


def captions(it):
    p = fmt_price(it["price"])
    extra = ("\n" + it["extra"]) if it.get("extra") else ""
    ig = (f"{it['hook']}\nPieza única · {p}\n📍 {ADDR}\n🕙 {HOURS}.{extra}\n"
          f"Reserva por DM o cómpralo en Vinted (link en nuestra bio).\n\n{it['tags']} {BASE_TAGS}")
    fb = (f"{it['hook']}\nPieza única · {p}\n📍 {ADDR}\n🕙 {HOURS}.{extra}\n"
          f"Cómpralo en Vinted: {it['vinted_url']}\nO escríbenos por mensaje para reservarlo.")
    pin = (f"{it['pin_desc']} {p}. Disponible en Vinted y en nuestra tienda de Ruzafa (Valencia), "
           f"abierta todos los días de 10 a 20 h. {it['tags']}")
    tt_title = it["hook"] if re.search(r"\bsolo\b", it["hook"].lower()) else f"{it['hook']} Solo {p}"
    return dict(ig=ig, fb=fb, pin=pin, tt_title=tt_title)


def media(it, kind):
    suffix = {"reel": "_reel-9x16-music.mp4", "pin": "_pin-2x3.jpg", "post": "_post-4x5.jpg"}[kind]
    return BASE + it["file"] + suffix


BOARDS = json.load(open(os.path.join(ROOT, "data/boards.json"), encoding="utf-8"))


def build_day(entry, items):
    it = items[entry["item"]]
    c = captions(it)
    d = entry["date"]
    common = dict(autoPublish=True, descendants=[], draft=False, hasNotReadNotes=False, shortener=False,
                  smartLinkData={"ids": []})
    return {
        "date": d, "item": it["n"], "uuids": entry.get("uuids", {}),   # NOT part of info; see create_args()
        "ig_tiktok": dict(common, media=[media(it, "reel")], mediaAltText=[],
                          providers=[{"network": "instagram"}, {"network": "tiktok"}],
                          publicationDate={"dateTime": d + "T10:00:00", "timezone": TZ}, text=c["ig"],
                          instagramData={"type": "REEL", "showReelOnFeed": True},
                          tiktokData={"privacyOption": "PUBLIC_TO_EVERYONE", "disableComment": False,
                                      "disableDuet": False, "disableStitch": False, "title": c["tt_title"]}),
        "facebook": dict(common, media=[media(it, "reel")], mediaAltText=[], providers=[{"network": "facebook"}],
                         publicationDate={"dateTime": d + "T10:00:00", "timezone": TZ}, text=c["fb"],
                         facebookData={"type": "REEL", "title": f"{it['brand']} · {fmt_price(it['price'])}"}),
        "pinterest": dict(common, media=[media(it, "pin")], mediaAltText=[f"{it['pin_title']}, {fmt_price(it['price'])}"],
                          providers=[{"network": "pinterest"}],
                          publicationDate={"dateTime": d + "T18:00:00", "timezone": TZ}, text=c["pin"],
                          pinterestData={"boardId": BOARDS.get(it["board"], it["board"]), "pinTitle": it["pin_title"],
                                         "pinLink": it["vinted_url"], "pinNewFormat": True}),
    }


def create_args(day):
    """The three createScheduledPost calls for a day: {blogId, date, info}. Send ONLY these keys."""
    out = {}
    for k, hhmm in (("ig_tiktok", "10:00"), ("facebook", "10:00"), ("pinterest", "18:00")):
        out[k] = {"blogId": BLOG_ID, "date": offset_iso(day["date"], hhmm), "info": day[k]}
    return out


def build_all():
    items, sched = load()
    return [build_day(e, items) for e in sched["posts"]]


if __name__ == "__main__":
    days = build_all()
    if len(sys.argv) > 1:
        for d in days:
            if d["date"] == sys.argv[1]:
                print(json.dumps(d, ensure_ascii=False, indent=1))
    else:
        os.makedirs(os.path.join(ROOT, "payloads"), exist_ok=True)
        for d in days:
            out = dict(d, create_args=create_args(d))
            json.dump(out, open(os.path.join(ROOT, "payloads", d["date"] + ".json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        print("wrote", len(days), "days to payloads/")
