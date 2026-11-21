---
name: worldwide-transit
description: Public transport trips and departures anywhere in the world, free, no API key. Plans trips with transfers across cities, countries and borders (buses, metro, trams, trains, Amtrak, VIA Rail, FlixBus and more) with live delays where published, and reads any official timetable feed in the world when the planner lacks a region. Use when the user asks "how do I get from X to Y by bus/train/transit", "when is the next bus", "last bus home", "can I get to X by 8:30", "Kelowna to Vancouver", "Seattle to Portland by train", "route 97", or needs a commute check for a job, school or appointment.
license: MIT
compatibility: Python 3.9+ (standard library only). Needs internet access to api.transitous.org, share.mobilitydata.org, storage.googleapis.com and the operators' own feed hosts. Linux, macOS, Windows (on Windows run `pip install tzdata` once).
---

# Worldwide Transit

Two scripts sit in the same folder as this file. Answer from them, never from memory: timetables change several times a year.

- `transit.py`: worldwide trip planner with transfers, departures and place lookup (Transitous, a free community service).
- `gtfs.py`: reads any official timetable (GTFS) feed in the world, found in the free Mobility Database catalog. The backup for places the planner lacks (Kelowna's city buses, as of 2026-11).

```bash
T="<this skill's folder>/transit.py"
G="<this skill's folder>/gtfs.py"
```

## First use: get the home region (do this before anything else)

Run `python3 "$T" home`. If no home region is saved, ask the user one short question: what city or region they are usually in. Save it with its IANA time zone:

```bash
python3 "$T" home "Kelowna, BC" --tz America/Vancouver
```

The home region steers place lookups (so "Queensway" means the nearby one) and sets the time zone. Ask once. If the harness does not keep files between chats (Claude app sandbox), ask once per chat, or pass `--tz` on every command.

## Plan a trip (try this first)

```bash
python3 "$T" plan "Pacific Central Station, Vancouver" "King Street Station, Seattle" --date 2026-11-24 --at 08:00
python3 "$T" plan "Vernon" "UBCO Exchange" --arrive-by 10:00           # latest trips that arrive by 10:00
python3 "$T" plan 49.888,-119.496 "Calgary Tower" -n 3                 # lat,lon works for either end
python3 "$T" next "Shinjuku" --near Tokyo --tz Asia/Tokyo -n 10       # departures; --near steers names away from home
python3 "$T" find "Berlin Hbf" --stops                                # check what a name resolves to
```

- `--date YYYY-MM-DD`, `--at HH:MM` (leave at or after) or `--arrive-by HH:MM`. Default is now.
- Times use the home zone unless `--tz` is given. For a trip in another zone, pass the zone where it starts and tell the user which zone the times are in.
- Check the `From:`, `To:` and `Stop:` lines. If a name resolved to the wrong town or country, retry with `--near <city>`, a fuller name, or lat,lon. For any trip away from home, pass `--near <city>` from the start.
- `[live]` means realtime data; `(+3 min late)` is a delay against the timetable.
- Output is already in 12-hour time. Show it that way, leg by leg.

## When there is no route

"No public transport route found in Transitous" means the planner lacks that timetable, not that no service exists. It prints `gtfs.py feeds <lat,lon>` commands for both ends. In order:

1. **Official feed for the local part.** Run the printed `feeds` command. It lists live feeds covering that point, smallest area first, with catalog ids. Pick the local operator, then:
   ```bash
   python3 "$G" stops 2555 "queensway"                                   # find stops (id, or a unique name like kelowna)
   python3 "$G" next 2555 "ubco exchange" --date 2026-11-23 --at 07:00   # departures, feed's own time zone
   python3 "$G" trip 2555 "ubco exchange" "queensway" --arrive-by 08:30  # rides on ONE vehicle, no transfers
   ```
   `FEED EXPIRED` means the operator stopped publishing that feed: do not use it, go to step 2.
2. **No open timetable at all** (Canadian intercity coaches such as Ebus and Rider Express, many private operators in Asia, Africa and Latin America): search the web for the operator's current schedule. Tell the user those times came from the operator's site.
3. **Stitch long trips together.** Example: Kelowna to Calgary is the Kelowna city bus to the coach stop (step 1), the coach (step 2), then Calgary Transit with `plan`. Leave at least 15 minutes between legs, and name each leg's source.

## Limits (say them when they matter)

- Coverage is whatever operators publish as open data: strong across Europe, North America, Japan, Australia and many big cities; patchy for private coaches and parts of South Asia and Africa. Planner coverage: https://transitous.org/sources/
- Transitous is a free community service. One request per question, no retry loops.
- Fares and bookings are not included. Link the operator for tickets.
- `gtfs.py` gives scheduled times only, one vehicle per trip. Big city feeds (100+ MB) take a minute to download and scan: prefer `plan` for those.

## Check

`python3 "$T" selftest` and `python3 "$G" selftest` must both print `selftest ok`.
