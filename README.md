# Worldwide Transit

An agent skill for public transport anywhere in the world. Free, no API key, standard-library Python only.

- `transit.py` plans trips with transfers, lists departures and looks up places worldwide, using [Transitous](https://transitous.org), a free community service built on open timetable data. City buses, metro, trams, trains and intercity coaches (Amtrak, VIA Rail, FlixBus and more), across borders, with live delays where the operator publishes them.
- `gtfs.py` reads any official timetable feed in the world, found in the free [Mobility Database](https://mobilitydatabase.org) catalog (about 2,000 live feeds). It is the backup for regions Transitous lacks, such as Kelowna's city buses (missing as of 2026-11).

On first use the agent asks for your home city or region and saves it, with its time zone, to `~/.config/worldwide-transit/home.json`. Name lookups then prefer places near you, and times come out in your zone.

## Examples

All output below is real, run on 2026-11-20 and 2026-11-21, with some lines trimmed.

Cross-border trip with a transfer:

```
$ python3 transit.py plan "Pacific Central Station, Vancouver" "King Street Station, Seattle" --date 2026-11-24 --at 08:00 -n 1
From: Vancouver (Pacific Central Station) (Metro Vancouver Regional District, British Columbia, Canada)
To:   King Street Station (King County, Washington, United States)
Times in America/Vancouver

leave Tue Nov 24 8:00 AM  arrive Tue Nov 24 12:03 PM  4h03m  0 transfer(s)
    8:00 AM  coach FlixBus-us FlixBus 2114 toward Seattle Bus Station
        Vancouver (Pacific Central Station) -> Seattle Bus Station  arrive 11:50 AM
    walk 13 min to King Street Station
```

A trip away from home (`--near` steers names, `--tz` sets the zone):

```
$ python3 transit.py plan "Shibuya" "Asakusa" --near Tokyo --tz Asia/Tokyo -n 1
leave Sat Nov 21 9:49 AM  arrive Sat Nov 21 10:23 AM  34 min  0 transfer(s)
    9:49 AM  subway 東京メトロ Tokyo Metro G toward (普通 Local) 浅草 Asakusa
        渋谷 Shibuya -> 浅草 Asakusa  arrive 10:23 AM
```

When the planner has no route, it prints the backup commands:

```
$ python3 transit.py plan "Kelowna" "Vancouver"
No public transport route found in Transitous. Next, find official feeds covering each end:
    python3 gtfs.py feeds 49.88792,-119.49590
    python3 gtfs.py feeds 49.26087,-123.11395

$ python3 gtfs.py feeds 49.88792,-119.49590
 2555  BC Transit (Kelowna Regional Transit System)  (Kelowna, British Columbia, CA)
 1871  Rider Express  (British Columbia, CA)
  735  VIA Rail Canada  (CA)

$ python3 gtfs.py next kelowna "ubco exchange" --date 2026-11-23 --at 07:00 -n 3
Feed 2555  BC Transit (Kelowna Regional Transit System)  (Kelowna, British Columbia, CA)
Monday 2026-11-23, scheduled times in America/Vancouver (feed valid 20261118 to 20261219)
               7:00 AM  route 84 Academy Way  from UBCO Exchange Bay A
               7:00 AM  route 97 Westbank  from UBCO Exchange Bay C
               7:05 AM  route 8 University - To UBCO  from UBCO Exchange Bay B

$ python3 gtfs.py next 1871 "kelowna downtown"
FEED EXPIRED: it ends 20231230, so it has no times for 2026-11-20. Use the operator's own website.
```

Operators with no open timetable (Canadian intercity coaches such as Ebus and Rider Express, many private lines elsewhere) are left to the agent: `SKILL.md` tells it to find the operator's current schedule on the web, join it to the legs the scripts cover, and say where each leg came from.

## Install

Needs Python 3.9 or newer and internet access. On Windows, run `pip install tzdata` once.

```bash
git clone https://github.com/Bestdoom20/worldwide-transit.git ~/.claude/skills/worldwide-transit   # Claude Code (CLI, IDE, desktop Code tab)
git clone https://github.com/Bestdoom20/worldwide-transit.git ~/.agents/skills/worldwide-transit   # Codex, Gemini CLI and other harnesses that read ~/.agents/skills
npx skills add Bestdoom20/worldwide-transit                                                        # any harness the skills CLI supports
```

**Claude app (web, desktop, mobile chats):** download `worldwide-transit.zip` from the [latest release](https://github.com/Bestdoom20/worldwide-transit/releases/latest) and upload it under Settings > Capabilities > Skills. Code execution must be on, with network access to all domains (feeds are hosted by thousands of operators). Chats there do not keep files, so the agent asks for your region once per chat.

**Any other agent:** give it `SKILL.md` and the two scripts.

## How gtfs.py reads a feed

A GTFS feed is a zip of CSV files: `stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt`, `calendar.txt`, `calendar_dates.txt` and, for headway-based lines, `frequencies.txt`. The time zone comes from the feed's own `agency.txt`.

Things in the data that are easy to get wrong, each with a case in the selftest:

- **Times past 24:00.** A bus that leaves at 12:30 AM on Saturday is written as `24:30:00` on Friday's service. Asking for Saturday has to pull in Friday's late trips, and asking for Friday has to label them "next day".
- **Service days.** A weekday trip must not show up on a Saturday. The weekly calendar is applied first, then the dated additions and removals for holidays.
- **One bus, several trips.** A loop route ends its trip at an exchange and the same vehicle carries on as a new trip with riders still on board. The script follows the vehicle through its `block_id`, so the ride is found.
- **Headways.** Many metros publish "every 3 minutes from 5 AM to midnight" instead of each run. Departures are expanded from `frequencies.txt`.
- **Dead feeds.** A feed whose end date has passed stops with `FEED EXPIRED` rather than printing nothing.

## Check

```
$ python3 transit.py selftest
selftest ok
$ python3 gtfs.py selftest
selftest ok
```

Both run offline.

## Limits

- Coverage is whatever operators publish as open data: strong across Europe, North America, Japan, Australia and many big cities; patchy for private coaches and parts of South Asia and Africa. Planner coverage: https://transitous.org/sources/
- Transitous is a free community service. The skill makes one request per question.
- No fares or bookings.
- `gtfs.py` gives scheduled times only, one vehicle per trip (no transfers), and reads the whole `stop_times.txt` once per question. Big city feeds take a minute; the planner covers most of those anyway.

## How this was built

I designed it, decided what it had to get right (the cases above) and directed AI coding agents to write the code. I tested it against real schedules and I can walk through every part.

## Licence

MIT. Trips come from Transitous (transitous.org), whose data comes from each operator's open feeds and OpenStreetMap. The feed catalog is the Mobility Database (mobilitydatabase.org). Each timetable stays under its operator's own licence.
