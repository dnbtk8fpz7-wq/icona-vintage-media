#!/usr/bin/env python3
"""Preflight + queue diff for the Icona Vintage content pipeline.

  python3 tools/check.py                    # validate data, media files and captions (exit 1 on any ERROR)
  python3 tools/check.py --diff queue.json  # compare Metricool's scheduled posts with what we planned

queue.json = the getScheduledPosts result for brand 7281190 saved to a file (raw {"data":[...]} or a plain list).
Diff rules (same philosophy as the other project: THE USER'S MANUAL CHANGES WIN):
  MISSING  planned post not in the queue  -> user probably deleted it. Do NOT re-add; record in data/manual_changes.json.
  EDITED   text/date differs from plan    -> user edited it. Do NOT overwrite; record it.
  EXTRA    queued post we don't know      -> user added it by hand. Leave it.
Run from anywhere; needs ffprobe/ffmpeg for the media checks.
"""
import datetime, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import payloads  # noqa: E402

ASSETS = os.path.join(ROOT, "icona-assets")
HOLIDAYS_2026 = {"2026-10-09": "Dia de la Comunitat Valenciana", "2026-10-12": "Fiesta Nacional",
                 "2026-11-01": "Todos los Santos", "2026-12-06": "Constitución", "2026-12-08": "Inmaculada",
                 "2026-12-25": "Navidad"}
errors, warns = [], []


def err(m): errors.append(m)
def warn(m): warns.append(m)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,duration",
                          "-of", "json", path], capture_output=True, text=True)
    return json.loads(out.stdout or "{}").get("streams", [])


def mean_volume(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vn", "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def validate():
    items, sched = payloads.load()
    seen_days, seen_items = set(), set()
    today = datetime.date.today().isoformat()
    if sched.get("brand_id") != "7281190":
        err("schedule.json brand_id must be 7281190 (Icona Vintage Valencia)")
    for e in sched["posts"]:
        d, n = e["date"], e["item"]
        if d in seen_days: err(f"{d}: two items on the same day")
        if n in seen_items: err(f"item {n}: scheduled twice")
        seen_days.add(d); seen_items.add(n)
        if n not in items: err(f"{d}: unknown item {n}"); continue
        it = items[n]
        if it["status"] == "sold" and d >= today:
            err(f"{d}: item {n} ({it['brand']}) is SOLD but still has a future post — delete it in Metricool")
        if d in HOLIDAYS_2026 and "festivo" not in (it.get("extra") or ""):
            warn(f"{d}: bank holiday ({HOLIDAYS_2026[d]}) — add 'extra' note that the shop is open")
        day = payloads.build_day(e, items)
        for k in ("ig_tiktok", "facebook", "pinterest"):
            t = day[k]["text"]
            if "adults" in t.lower(): err(f"{d} {k}: wrong wording")
            if k != "facebook" and "vinted.es/items" in t: err(f"{d} {k}: raw Vinted URL belongs only in Facebook text")
            if k == "facebook" and it["vinted_url"] not in t: err(f"{d}: Facebook text lacks the Vinted link")
        if len(day["ig_tiktok"]["text"]) > 2200: err(f"{d}: IG caption too long")
        if len(day["ig_tiktok"]["tiktokData"]["title"]) > 150: err(f"{d}: TikTok title > 150")
        if len(it["pin_title"]) > 100: err(f"{d}: pin title > 100")
        if len(day["pinterest"]["text"]) > 500: err(f"{d}: pin description > 500")
        if len(set(re.findall(r"#\w+", day["ig_tiktok"]["text"]))) > 12: warn(f"{d}: more than 12 hashtags")
        # media files
        base = os.path.join(ASSETS, it["file"])
        for suf, wh, kind in (("_reel-9x16-music.mp4", (1080, 1920), "video"), ("_pin-2x3.jpg", (1000, 1500), "image"),
                              ("_post-4x5.jpg", (1080, 1350), "image")):
            p = base + suf
            if not os.path.exists(p): err(f"missing file {os.path.basename(p)}"); continue
            st = probe(p)
            v = next((s for s in st if s.get("codec_type") == "video"), None)
            if not v or (v["width"], v["height"]) != wh: err(f"{os.path.basename(p)}: size should be {wh}"); continue
            if kind == "video":
                if not any(s.get("codec_type") == "audio" for s in st): err(f"{os.path.basename(p)}: no audio track")
                elif (mv := mean_volume(p)) is None or mv < -35: err(f"{os.path.basename(p)}: audio silent ({mv} dB)")
                dur = float(v.get("duration") or 0)
                if not 5 <= dur <= 15: err(f"{os.path.basename(p)}: duration {dur}s outside 5–15 s")
                if os.path.getsize(p) > 25_000_000: err(f"{os.path.basename(p)}: > 25 MB")
    # items file sanity
    for n, it in items.items():
        if it["status"] not in ("available", "scheduled", "sold"): err(f"item {n}: bad status {it['status']}")
        if not it["vinted_url"].startswith("https://www.vinted.es/items/"): err(f"item {n}: vinted_url looks wrong")


def diff(queue_path):
    items, sched = payloads.load()
    q = json.load(open(queue_path, encoding="utf-8"))
    q = q["data"] if isinstance(q, dict) else q
    by_uuid = {str(p["uuid"]): p for p in q}
    known = set()
    for e in sched["posts"]:
        day = payloads.build_day(e, items)
        for k in ("ig_tiktok", "facebook", "pinterest"):
            uid = e["uuids"].get(k)
            known.add(uid)
            exp = day[k]
            p = by_uuid.get(uid)
            if p is None:
                if exp["publicationDate"]["dateTime"] >= datetime.datetime.now().isoformat(timespec="seconds"):
                    print(f"MISSING  {e['date']} {k} (item {e['item']}) — probably deleted by the user; do NOT re-add, record it")
                continue
            pd = p["publicationDate"]["dateTime"]
            if pd != exp["publicationDate"]["dateTime"]:
                print(f"EDITED   {e['date']} {k}: time {pd} (planned {exp['publicationDate']['dateTime']}) — keep the user's change")
            if p["text"].strip() != exp["text"].strip():
                print(f"EDITED   {e['date']} {k}: caption changed by hand — keep it")
            nets = sorted(x["network"] for x in p["providers"])
            if nets != sorted(x["network"] for x in exp["providers"]):
                print(f"EDITED   {e['date']} {k}: networks now {nets}")
    for uid, p in by_uuid.items():
        if uid not in known:
            print(f"EXTRA    {p['publicationDate']['dateTime']} {[x['network'] for x in p['providers']]} — added by hand (or a new batch not yet in schedule.json); leave it")
    print("diff done")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--diff":
        diff(sys.argv[2])
    else:
        validate()
        for w in warns: print("WARN ", w)
        for e in errors: print("ERROR", e)
        print(f"{len(errors)} errors, {len(warns)} warnings")
        sys.exit(1 if errors else 0)
