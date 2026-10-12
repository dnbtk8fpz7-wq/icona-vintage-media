# Icona Vintage Valencia — content pipeline (read me first)

> **PAUSED since 2026-10-12 (user request): all unpublished posts are drafts. Do not publish, un-draft or schedule anything until the user explicitly says to proceed.** See data/manual_changes.json.

Shop: second-hand / vintage clothing, Carrer del Músic Padilla, 2 (Ruzafa), 46005 València. Open every day 10:00–20:00 (Valencia time).
Online shop for now: Vinted https://www.vinted.es/member/125675678 (items are unique pieces — "pieza única").
Accounts: Instagram @iconavintagesecondhand · TikTok @iconavintage · Facebook Page · Pinterest @iconavintage.
Goal: followers, engagement and SALES at ZERO cost. Captions are in Spanish.

## Hard rules (never break)
1. Metricool: ONLY brand **7281190 "Icona Vintage Valencia"**. Never read, post or edit brand 7298177 ("Schmoe's POV") or its repos
   (schmoes-pov, schmoes-pov-media). Before any write, call getBrandSettings and confirm the blogId/name you are about to use.
2. Spend no money. **No Higgsfield** (its credits belong to the other project). No paid ads, no paid tools.
3. All times Europe/Madrid. Daily rhythm: 10:00 Reel (Instagram Reel + TikTok together, Facebook Reel as its own post because its caption carries the Vinted link), 18:00 Pinterest pin with the Vinted link.
4. **The user's manual changes win.** Never re-add a post they deleted, never overwrite a caption/time they edited. Record it in `data/manual_changes.json` and mention it.
5. Never post an item that may be sold. Items are unique; `last_confirmed` in data/items.json is the date the user last confirmed availability (check.py warns if older than 10 days before the post). If told it's sold: set `status: "sold"` (+ `sold_date`, `sold_channel`) in data/items.json, then neutralise its queued posts: updateScheduledPost with `draft: true` (keeps it from publishing; verify with getScheduledPosts) and ask the user to delete them in the Metricool planner (there is no delete tool). Never retry a failed/timed-out createScheduledPost blindly: call getScheduledPosts first — the post may exist (a retry = duplicate public post; check.py --diff reports DUPLICATE).
6. Gmail is NOT checked for Icona (its Gmail connector belongs to the other project). Do not read it.
7. Media must be reachable by Metricool: public raw GitHub URLs on branch `icona-assets` (see tools/payloads.py). The repo is public: never commit costs, prices paid, accounting, personal data or the raw music file.

## Files
- `data/items.json` — one record per piece (seed of the future inventory DB and web shop). `status`: available | scheduled | sold. NEVER put purchase cost/accounting here (public repo): that lives in a private place (Claude Project docs / private sheet), keyed by item `n`.
- `data/boards.json` — Pinterest board name → numeric id.
- `data/schedule.json` — day → item, plus the Metricool `uuid` of each of the 3 posts (uuid is stable; id changes on every edit).
- `tools/make_assets.py` — builds post 4:5, pin 2:3 and reel 9:16 (7 s) from a photo. `python3 tools/make_assets.py 11,12 all --photos DIR --music CLIP.wav`
- `tools/payloads.py` — builds the exact Metricool payloads (captions, hashtags, boards, TikTok title). NEVER hand-write captions. `payloads/<date>.json` → use ONLY `create_args.<ig_tiktok|facebook|pinterest>` = `{blogId, date, info}` as the createScheduledPost arguments (the `date`/`item`/`uuids` keys of the outer object are not part of `info`).
- `tools/check.py` — preflight (`python3 tools/check.py`, must show 0 errors) and queue diff (`--diff queue.json`).
- `data/manual_changes.json` — what the user changed by hand and how we handled it.
- `icona-assets/` — generated media. `*_reel-9x16-music.mp4` is the version to publish.

## Music
Pool of 4 Pixabay tracks, all approved by the user for ALL future Icona reels (Pixabay licence: fine in videos, never publish the raw file):
1. "Bossa Nova Cafe – Morning Breeze", Alex Morgan (573876) — used by the 30 reels queued 11–20 Oct
2. "Little Miss Nova", faespencer (204158) · 3. "Bossa Nova Jazz Piano Summer Cafe", Denis Pavlov (398166) · 4. "Lounge Elevator Background", TuneTank (347361)
Clips (7 s, afade in 0.4 s / out 1.2 s at 5.8 s, loudnorm −15 LUFS, 44.1 kHz stereo) are stored privately, NOT in this repo. `--music DIR` picks `clip[(n−1) % 4]` by item number (sorted filenames); `--music FILE` uses one clip. Recover a clip from any existing reel: `ffmpeg -i icona-assets/item07-coach-swinger_reel-9x16-music.mp4 -vn -ar 44100 -ac 2 clip.wav`; for the three new tracks ask the user to re-attach the mp3s (start offsets: Little Miss Nova 70 s, Denis Pavlov 431 s, TuneTank 97 s; first track 24 s).
Risk: a platform may flag a Pixabay track. If a copyright notice appears, drop that track from the pool, the user disputes it with the Pixabay download page, and ask for 2–3 more tracks.

## New batch workflow (about 20 min of work per 10 items)
1. User sends photos + name + price + Vinted link per item (Word table or message). Save photos in `photos/` (not committed).
2. Add records to data/items.json (hook, tags, board, pin_title, pin_desc; Spanish; pin title ≤ 100, pin description ≤ 500). Boards: Bolsos vintage, Botas vintage, Moda Y2K, Novedades Icona Vintage (also exist: Chaquetas y abrigos vintage, Looks vintage Valencia, Ruzafa Valencia). Use original photos — the user rejected edited backgrounds except where they asked for them (items 7 and 9).
3. Build media (make_assets.py with --music), look at a contact sheet of the results, fix problems.
4. Add the days to data/schedule.json (one item per day), run `python3 tools/payloads.py`, run `python3 tools/check.py` (0 errors).
5. Commit + push to branch `icona-assets` so raw URLs work (check.py warns if HEAD is not pushed), then call createScheduledPost with each `create_args` entry (3 per day). Copy the returned `uuid`s into schedule.json (a day without uuids is "NEW" in the diff, not "MISSING"), set the items' `status` to `scheduled` and `last_confirmed`, commit + push.
6. After scheduling: getScheduledPosts for the range → save to a file → `python3 tools/check.py --diff file` must be clean.
Bank holidays: the shop opens anyway; add an `extra` note ("Hoy es festivo y abrimos igualmente…").

## Periodic checks (scheduled tasks, see the user's scheduled tasks list)
- Weekly (Fri): queue has ≥ 7 days ahead? failed posts? sold items? → asks the user for the next batch when short.
- 1st and 15th: performance + health review. Suggest, never change strategy by itself.
- 8th and 22nd: competitor and inspiration scan (read-only). Metricool Instagram/Facebook "competitors" analytics for brand 7281190 (fields IGCO02, IGCO03, IGCO07–IGCO10, IGCO12; empty until competitors are added in the Metricool app), plus WebSearch for new vintage shops, local press and markets in Valencia. Suggest ideas, don't change strategy. Competitor notes live in the Project doc `claude/icona-competitors-and-ideas.md`, not in this public repo.
- Instagram/TikTok profile pages can only be fetched with the user's approval; never scrape or use paid tools.
