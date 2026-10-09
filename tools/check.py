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
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import payloads  # noqa: E402

ASSETS = os.path.join(ROOT, "icona-assets")
HOLIDAYS_2026 = {"2026-10-09": "Dia de la Comunitat Valenciana", "2026-10-12": "Fiesta Nacional",
                 "2026-11-01": "Todos los Santos", "2026-12-06": "Constitución", "2026-12-08": "Inmaculada",
                 "2026-12-25": "Navidad"}
errors, warns = [], []
MADRID = ZoneInfo("Europe/Madrid")


def now_madrid():
    return datetime.datetime.now(MADRID)


def git(*a):
    r = subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


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
    raw = json.load(open(os.path.join(ROOT, "data/items.json"), encoding="utf-8"))
    for key in ("n", "file", "vinted_url", "slug"):
        vals = [i.get(key) for i in raw]
        if len(vals) != len(set(vals)): err(f"duplicate '{key}' in items.json")
    for i in raw:
        for key in ("n", "file", "brand", "price", "vinted_url", "board", "hook", "tags", "pin_title", "pin_desc", "status"):
            if i.get(key) in (None, ""): err(f"item {i.get('n')}: missing '{key}'")
        if "cost" in i: err(f"item {i.get('n')}: 'cost' must not be stored in this PUBLIC repo")
        if i.get("tags") and not all(t.startswith("#") for t in i["tags"].split()): err(f"item {i.get('n')}: tags must start with #")
        for amount in re.findall(r"(\d+(?:[.,]\d+)?)\s*€", i.get("hook") or ""):
            if float(amount.replace(",", ".")) != float(i["price"]): err(f"item {i['n']}: hook price {amount} € != price {i['price']}")
        if i.get("board") not in payloads.BOARDS: warn(f"item {i['n']}: board '{i['board']}' has no numeric id in data/boards.json")
    seen_days, seen_items, seen_uuids = set(), set(), set()
    now = now_madrid(); today = now.date().isoformat()
    if sched.get("brand_id") != "7281190":
        err("schedule.json brand_id must be 7281190 (Icona Vintage Valencia)")
    for e in sched["posts"]:
        d, n = e["date"], e["item"]
        try: datetime.date.fromisoformat(d)
        except ValueError: err(f"{d}: bad date format"); continue
        if d in seen_days: err(f"{d}: two items on the same day")
        if n in seen_items: err(f"item {n}: scheduled twice")
        seen_days.add(d); seen_items.add(n)
        for k, u in (e.get("uuids") or {}).items():
            if u in seen_uuids: err(f"{d}: uuid {u} used twice")
            seen_uuids.add(u)
        if not e.get("uuids"):   # new day, not scheduled yet
            if d < today or (d == today and now.hour >= 10): err(f"{d}: new day is in the past / too late for the 10:00 post")
        if n not in items: err(f"{d}: unknown item {n}"); continue
        it = items[n]
        if it["status"] == "sold" and d >= today:
            err(f"{d}: item {n} ({it['brand']}) is SOLD but still has a future post — set it to draft/delete it (ask the user to delete in the Metricool planner)")
        if it["status"] == "available": warn(f"{d}: item {n} is scheduled but status is 'available' (set 'scheduled')")
        lc = it.get("last_confirmed")
        if not lc or (datetime.date.fromisoformat(d) - datetime.date.fromisoformat(lc)).days > 10:
            warn(f"{d}: item {n} availability last confirmed {lc} — ask the user before this post goes out")
        if d in HOLIDAYS_2026 and "festivo" not in (it.get("extra") or ""):
            warn(f"{d}: bank holiday ({HOLIDAYS_2026[d]}) — add 'extra' note that the shop is open")
        if "festivo" in (it.get("extra") or "") and d not in HOLIDAYS_2026:
            err(f"{d}: item {n} carries a 'festivo' note but {d} is not a holiday — fix 'extra'")
        day = payloads.build_day(e, items)
        for k in ("ig_tiktok", "facebook", "pinterest"):
            t = day[k]["text"]
            if re.search(r"\bNone\b|\{|\}|nan", t): err(f"{d} {k}: placeholder text in caption")
            if k != "facebook" and "vinted.es/items" in t: err(f"{d} {k}: raw Vinted URL belongs only in Facebook text")
            if k == "facebook" and it["vinted_url"] not in t: err(f"{d}: Facebook text lacks the Vinted link")
        if len(day["ig_tiktok"]["text"]) > 2200: err(f"{d}: IG caption too long")
        if len(day["ig_tiktok"]["tiktokData"]["title"]) > 150: err(f"{d}: TikTok title > 150")
        if len(it["pin_title"]) > 100: err(f"{d}: pin title > 100")
        if len(day["pinterest"]["text"]) > 500: err(f"{d}: pin description > 500")
        if len(set(re.findall(r"#\w+", day["ig_tiktok"]["text"]))) > 12: warn(f"{d}: more than 12 hashtags")
        if len(set(re.findall(r"#\w+", day["ig_tiktok"]["text"]))) > 30: err(f"{d}: more than 30 hashtags")
        # media files
        base = os.path.join(ASSETS, it["file"])
        for suf, wh, kind in (("_reel-9x16-music.mp4", (1080, 1920), "video"), ("_pin-2x3.jpg", (1000, 1500), "image"),
                              ("_post-4x5.jpg", (1080, 1350), "image")):
            p = base + suf
            if not os.path.exists(p): err(f"missing file {os.path.basename(p)}"); continue
            if git("ls-files", "--error-unmatch", p)[0] != 0: err(f"{os.path.basename(p)} is not committed — Metricool cannot fetch it")
            st = probe(p)
            v = next((s for s in st if s.get("codec_type") == "video"), None)
            if not v or (v["width"], v["height"]) != wh: err(f"{os.path.basename(p)}: size should be {wh}"); continue
            if kind == "video":
                if not any(s.get("codec_type") == "audio" for s in st): err(f"{os.path.basename(p)}: no audio track")
                elif (mv := mean_volume(p)) is None or mv < -35: err(f"{os.path.basename(p)}: audio silent ({mv} dB)")
                dur = float(v.get("duration") or 0)
                if not 5 <= dur <= 15: err(f"{os.path.basename(p)}: duration {dur}s outside 5–15 s")
                if os.path.getsize(p) > 25_000_000: err(f"{os.path.basename(p)}: > 25 MB")
    for n, it in items.items():
        if it["status"] not in ("available", "scheduled", "sold"): err(f"item {n}: bad status {it['status']}")
        if not str(it["vinted_url"]).startswith("https://www.vinted.es/items/"): err(f"item {n}: vinted_url looks wrong")
    rc, head = git("rev-parse", "HEAD"); rc2, remote = git("rev-parse", "origin/icona-assets")
    if rc == 0 and rc2 == 0 and head != remote: warn("local HEAD is not pushed to origin/icona-assets — raw URLs may 404 until you push")
    rc3, dirty = git("status", "--porcelain", "icona-assets")
    if dirty: warn("uncommitted changes in icona-assets/")


def diff(queue_path):
    items, sched = payloads.load()
    q = json.load(open(queue_path, encoding="utf-8"))
    q = q["data"] if isinstance(q, dict) else q
    by_uuid = {str(p["uuid"]): p for p in q}
    now = now_madrid()
    known, planned = set(), []
    for e in sched["posts"]:
        day = payloads.build_day(e, items)
        for k in ("ig_tiktok", "facebook", "pinterest"):
            exp = day[k]
            planned.append((exp["publicationDate"]["dateTime"], exp["text"].strip(), e["date"], k))
            uid = (e.get("uuids") or {}).get(k)
            if not uid:
                print(f"NEW      {e['date']} {k} (item {e['item']}) — planned, not scheduled yet (no uuid)")
                continue
            known.add(uid)
            p = by_uuid.get(uid)
            if p is None:
                when = datetime.datetime.fromisoformat(exp["publicationDate"]["dateTime"]).replace(tzinfo=MADRID)
                if when > now:
                    print(f"MISSING  {e['date']} {k} (item {e['item']}) — probably deleted by the user; do NOT re-add, record it")
                else:
                    print(f"GONE     {e['date']} {k} — time has passed (published or failed): check getScheduledPosts status for the past days")
                continue
            pd = p["publicationDate"]["dateTime"]
            if pd[:19] != exp["publicationDate"]["dateTime"][:19]:
                print(f"EDITED   {e['date']} {k}: time {pd} (planned {exp['publicationDate']['dateTime']}) — keep the user's change")
            if p["text"].strip() != exp["text"].strip():
                print(f"EDITED   {e['date']} {k}: caption changed by hand — keep it")
            nets = sorted(x["network"] for x in p["providers"])
            if nets != sorted(x["network"] for x in exp["providers"]):
                print(f"EDITED   {e['date']} {k}: networks now {nets}")
    dup_keys = {}
    for uid, p in by_uuid.items():
        key = (p["publicationDate"]["dateTime"][:19], p["text"].strip(), tuple(sorted(x["network"] for x in p["providers"])))
        dup_keys.setdefault(key, []).append(uid)
    for key, uids in dup_keys.items():
        if len(uids) > 1:
            print(f"DUPLICATE {key[0]} {list(key[2])}: {len(uids)} identical posts in the queue (uuids {uids}) — delete the extras")
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
