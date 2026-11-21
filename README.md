<div align="center">

<img src="assets/logo/worldwide-transit-512.png" alt="Worldwide Transit logo" width="180" />

# Worldwide Transit

### Any trip, any city, any border. Hand it to your agent and ask for the next bus.

[![selftest](https://img.shields.io/github/actions/workflow/status/Bestdoom20/worldwide-transit/selftest.yml?branch=main&label=selftest&style=for-the-badge&labelColor=0d1117&color=e8442e)](.github/workflows/selftest.yml)
[![License](https://img.shields.io/badge/license-MIT-e8442e?style=for-the-badge&labelColor=0d1117)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B%20stdlib-8f8a81?style=for-the-badge&labelColor=0d1117)](#installation)
[![Agent](https://img.shields.io/badge/agent-any%20skills%20harness-8f8a81?style=for-the-badge&labelColor=0d1117)](SKILL.md)
[![Cost](https://img.shields.io/badge/API%20keys-none-8f8a81?style=for-the-badge&labelColor=0d1117)](#where-the-data-comes-from)

<img src="docs/assets/hero.png" alt="Worldwide Transit" width="94%" />

</div>

## Overview

Worldwide Transit is an agent skill for public transport anywhere in the world. Hand this link to your agent, tell it
your city, and ask it anything you would ask a transit app: the next bus, the last train home, how to get across town by
9, or Vancouver to Seattle on Saturday. It answers from the operators' own timetables, never from memory.

## What it does

- Plans trips with transfers across cities, countries and borders: buses, metro, trams, trains and intercity coaches.
- Lists the next departures from any stop, with live delays where the operator publishes them.
- Reads any of 1,809 official timetable feeds in 80 countries when the planner lacks a region.
- Asks for your home region once, then understands "Queensway" as the stop near you and answers in your time zone.
- Says plainly when no open timetable exists, and tells your agent where to look instead.
- Works with Claude Code, Codex, Gemini CLI and any harness that reads skills. Free, no API key, no dependencies.

## How it works

```mermaid
flowchart LR
    Q([You ask<br/>your agent]) --> P[PLAN<br/>Transitous]
    P -->|route found| A([Answer<br/>leg by leg])
    P -->|no route| F[FEEDS<br/>official GTFS<br/>near each end]
    F -->|feed is live| A
    F -->|no open data| W[OPERATOR SITE<br/>agent looks it up]
    W --> A
    classDef you fill:#0e0e0d,stroke:#e8442e,color:#e8442e
    classDef step fill:#131312,stroke:#2a2927,color:#efebe4
    class Q,A you
    class P,F,W step
```

1. **Plan.** `transit.py` asks [Transitous](https://transitous.org), a free community trip planner built on open
   timetable data, for routes with transfers.
2. **Backup.** If it has no route, it prints the next command: `gtfs.py` finds the official feeds covering each end in
   the [Mobility Database](https://mobilitydatabase.org) catalog and reads the operator's own timetable.
3. **No data at all.** Some operators publish nothing (Canadian intercity coaches such as Ebus and Rider Express, many
   private lines elsewhere). The skill tells your agent to find the schedule on the operator's site and say so.

## Installation

**Give this to your agent:**

```text
Install https://github.com/Bestdoom20/worldwide-transit and set it up for me.
```

It follows [AGENTS.md](AGENTS.md): installs the skill, asks what city you are in, plans one trip near you to prove it
works, and tells you what to ask. Any agent with a shell can do it.

**Or from the command line:**

```bash
curl -fsSL https://raw.githubusercontent.com/Bestdoom20/worldwide-transit/main/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/Bestdoom20/worldwide-transit/main/install.ps1 | iex
```

The installer needs `git` and Python 3.9+. It puts the skill in `~/.claude/skills` (Claude Code) and
`~/.agents/skills` (Codex, Gemini CLI and others), runs the selftests and prints `INSTALL OK`. Run it again to update.
Another folder: `sh install.sh /path/to/skills`.

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

## Where the data comes from

| Source | What | Coverage | Key |
|---|---|---|---|
| [Transitous](https://transitous.org/sources/) | trip planning with transfers, departures, live delays, place search | Europe, North America, Japan, Australia and many big cities worldwide | no |
| [Mobility Database](https://mobilitydatabase.org) | catalog of 1,809 live official GTFS feeds in 80 countries | backup for regions Transitous lacks | no |
| Operators' own sites | schedules for lines with no open data | found by your agent on the web | no |

Coverage is whatever operators publish as open data. Strong across Europe, North America, Japan and Australia;
patchy for private coaches and parts of South Asia and Africa. Fares and bookings are not included.

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

Both run offline, and CI runs them on Python 3.9 and 3.13 on every push.

## What it will not do

- **Answer from memory.** Every time comes from a timetable read at the moment you ask.
- **Pass off a dead feed.** An expired timetable stops with `FEED EXPIRED` instead of printing old times.
- **Hammer free services.** One request per question, cached feeds, no retry loops.
- **Sell you a ticket.** It links the operator; booking stays with you.

## Links

- **Agent skill:** [SKILL.md](SKILL.md) · agent install steps: [AGENTS.md](AGENTS.md)
- **Data:** [Transitous](https://transitous.org) (operators' open feeds and OpenStreetMap) · [Mobility Database](https://mobilitydatabase.org)

## How this was built

I designed it, decided what it had to get right (the cases above) and directed AI coding agents to write the code. I
tested it against real schedules and I can walk through every part.

<div align="center"><sub>MIT licensed. Timetables stay under their operators' own licences. Your home region stays in one file on your machine.</sub></div>
