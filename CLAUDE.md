# Icona Vintage Valencia — content pipeline (read me first)

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
5. Never post an item that may be sold. Items are unique; before a post goes out the user must have confirmed the item is still available (weekly check asks). If told it's sold: set `status: "sold"` in data/items.json and delete its queued posts in Metricool (use getScheduledPosts to find them by uuid).
6. Gmail is NOT checked for Icona (its Gmail connector belongs to the other project). Do not read it.
7. Media must be reachable by Metricool: public raw GitHub URLs on branch `icona-assets` (see tools/payloads.py). The repo is public: never commit costs, prices paid, accounting, personal data or the raw music file.

## Files
- `data/items.json` — one record per piece (the future inventory DB: add `cost`, `sold_date`, `sold_channel`; later this feeds accounting and the web shop). `status`: available | scheduled | sold.
- `data/schedule.json` — day → item, plus the Metricool `uuid` of each of the 3 posts (uuid is stable; id changes on every edit).
- `tools/make_assets.py` — builds post 4:5, pin 2:3 and reel 9:16 (7 s) from a photo. `python3 tools/make_assets.py 11,12 all --photos DIR --music CLIP.wav`
- `tools/payloads.py` — builds the exact Metricool payloads (captions, hashtags, boards, TikTok title). NEVER hand-write captions.
- `tools/check.py` — preflight (`python3 tools/check.py`, must show 0 errors) and queue diff (`--diff queue.json`).
- `data/manual_changes.json` — what the user changed by hand and how we handled it.
- `icona-assets/` — generated media. `*_reel-9x16-music.mp4` is the version to publish.

## Music
Track: Pixabay "Bossa Nova Cafe – Morning Breeze" by Alex Morgan (id 573876), approved by the user for ALL future Icona reels. Pixabay licence: fine in videos, never publish the raw file.
7 s clip = source from 0:24 with 0.4 s fade-in, 1.2 s fade-out, loudnorm −15 LUFS. Recover the clip from any existing reel: `ffmpeg -i icona-assets/item07-coach-swinger_reel-9x16-music.mp4 -vn -ar 44100 -ac 2 clip.wav`. For a different length ask the user to re-attach the mp3 (the file is not stored anywhere public).
Risk: a platform may flag a Pixabay track. If a copyright notice appears, the user disputes it with the Pixabay download page; ask the user for 2–3 more tracks to rotate (a pool).

## New batch workflow (about 20 min of work per 10 items)
1. User sends photos + name + price + Vinted link per item (Word table or message). Save photos in `photos/` (not committed).
2. Add records to data/items.json (hook, tags, board, pin_title, pin_desc; Spanish; pin title ≤ 100, pin description ≤ 500). Boards: Bolsos vintage, Botas vintage, Moda Y2K, Novedades Icona Vintage (also exist: Chaquetas y abrigos vintage, Looks vintage Valencia, Ruzafa Valencia). Use original photos — the user rejected edited backgrounds except where they asked for them (items 7 and 9).
3. Build media (make_assets.py with --music), look at a contact sheet of the results, fix problems.
4. Add the days to data/schedule.json (one item per day), run `python3 tools/payloads.py`, run `python3 tools/check.py` (0 errors).
5. Commit + push to branch `icona-assets` so raw URLs work, then call createScheduledPost with each payload (3 per day), blogId 7281190. Copy the returned `uuid`s into schedule.json, commit.
6. After scheduling: getScheduledPosts for the range → save to a file → `python3 tools/check.py --diff file` must be clean.
Bank holidays: the shop opens anyway; add an `extra` note ("Hoy es festivo y abrimos igualmente…").

## Periodic checks (scheduled tasks, see the user's scheduled tasks list)
- Weekly (Fri): queue has ≥ 7 days ahead? failed posts? sold items? → asks the user for the next batch when short.
- 1st and 15th: performance + health review. Suggest, never change strategy by itself.
