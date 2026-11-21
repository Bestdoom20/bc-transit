---
name: transit
description: Public transport trips and departures anywhere in the world, free, from open timetable data (Transitous), with live delays where the operator publishes them. City buses, metro, trams, regional and long-distance trains, intercity coaches (Amtrak, FlixBus and more), across borders. Exact BC Transit schedules from the official feeds as a backup. Use when the user asks "how do I get from X to Y by bus/train/transit", "when is the next bus", "last bus home", "can I get to X by 8:30", "Kelowna to Vancouver", "Seattle to Portland by train", "route 97", or needs a commute check for a job, school or appointment.
license: MIT
compatibility: Python 3.9+ (standard library only). Needs internet access to api.transitous.org (and bct.tmix.se for the BC Transit backup). Linux, macOS, Windows (on Windows run `pip install tzdata` once for time zones).
---

# Transit

Two scripts sit in the same folder as this file. Answer from them, never from memory: timetables change several times a year.

- `transit.py`: worldwide trip planning with transfers, departures, place lookup (Transitous, free, no key).
- `bctransit.py`: exact BC Transit schedules straight from BC Transit's own feeds. Backup for BC towns that are missing from Transitous (Kelowna's city buses are missing as of 2026-11).

```bash
T="<this skill's folder>/transit.py"
B="<this skill's folder>/bctransit.py"
```

## First use: get the home region (do this before anything else)

Run `python3 "$T" home`. If it says no home region is saved, ask the user one short question: what city or region they are usually in. Then save it with its IANA time zone:

```bash
python3 "$T" home "Kelowna, BC" --tz America/Vancouver
```

The home region steers place lookups (so "Queensway" means the nearby one) and sets the time zone for input and output. Ask once. If the harness does not keep files between chats (Claude app sandbox), ask once per chat, or skip saving and pass `--tz` on every command.

## Commands

```bash
python3 "$T" plan "Pacific Central Station, Vancouver" "King Street Station, Seattle" --date 2026-11-24 --at 08:00
python3 "$T" plan "Vernon" "UBCO Exchange" --arrive-by 10:00            # latest trips that arrive by 10:00
python3 "$T" plan 49.888,-119.496 "Kelowna Airport" -n 3               # lat,lon works for either end
python3 "$T" next "UBCO Exchange" -n 10                                # departures from a stop, from now
python3 "$T" find "Berlin Hbf" --stops                                 # check what a name resolves to
python3 "$T" plan "Berlin Hbf" "Potsdamer Platz" --tz Europe/Berlin    # a trip away from home: pass that place's zone
```

- `--date YYYY-MM-DD`, `--at HH:MM` (leave at or after) or `--arrive-by HH:MM`. Default is now.
- Times are read and printed in the home zone unless `--tz` is given. For a trip in another zone, pass the zone where the trip starts, and say which zone the times are in.
- `From:` and `To:` lines show what each name resolved to. If one is wrong (wrong town, wrong country), retry with a fuller name or lat,lon.
- `[live]` means the time includes realtime data; `(+3 min late)` shows a delay against the timetable.
- Output is already in 12-hour time. Show it that way, leg by leg.

## When there is no route

"No public transport route found in open data" means the timetable is not in Transitous, not that no bus exists. In order:

1. **BC town?** Use the official-feed backup for the local part:
   `python3 "$B" systems`, then `python3 "$B" stops kelowna "queensway"`, `python3 "$B" next kelowna "ubco exchange"`, `python3 "$B" trip kelowna "ubco exchange" "queensway" --arrive-by 08:30` (one bus only, no transfers).
2. **Intercity in Canada** (for example Kelowna to Vancouver or Calgary): private coach lines such as Ebus and Rider Express do not publish open timetables. Search the web for the operator's current schedule, and say the times came from the operator's site, not from this skill.
3. **Stitch the trip together:** local leg from step 1, intercity leg from step 2, the far end with `plan` (Vancouver, Calgary, Seattle and most large cities are covered). Leave at least 15 minutes between legs and say each leg's source.

## Limits (say them when they matter)

- Coverage is whatever operators publish as open data: strong in Europe, US and Canadian cities, Amtrak, VIA Rail, FlixBus; weak for private coach lines and some small towns. Coverage list: https://transitous.org/sources/
- Transitous is a free community service. Make one request per question, not loops of retries.
- Fares and bookings are not included. Link the operator for tickets.
- `bctransit.py` reads scheduled times only, one bus per trip.

## Check

`python3 "$T" selftest` and `python3 "$B" selftest` must both print `selftest ok`.
