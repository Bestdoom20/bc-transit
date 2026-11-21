# bc-transit

Exact scheduled bus times for 35 BC Transit feeds, read from the official GTFS schedule data. One Python file, standard library only.

Schedules change often: the Kelowna feed used below is valid for about a month (2026-11-17 to 2026-12-19). A remembered answer goes stale, so the script reads the published feed every time.

## What it does

- `systems`: lists the 35 feeds, and the towns inside each one.
- `stops`: finds a stop by words from its name or by the stop number printed on the pole.
- `next`: the next departures from a stop, from now or from a date and time you give.
- `trip`: rides on one bus from stop A to stop B, either leaving after a time or arriving by a time.
- `selftest`: checks the schedule logic against a small built-in feed.

Times are Pacific and printed in 12-hour form. The first line of every answer shows the dates the feed is valid for.

## Install

Needs Python 3.9 or newer on Linux or macOS. Nothing to install.

```bash
git clone https://github.com/Bestdoom20/bc-transit.git
cd bc-transit
python3 bctransit.py selftest
```

### As an agent skill

The repo is an [Agent Skill](https://agentskills.io): `SKILL.md` at the root tells the agent when and how to run the script. Clone it into your harness's skills folder:

```bash
git clone https://github.com/Bestdoom20/bc-transit.git ~/.claude/skills/bc-transit   # Claude Code
git clone https://github.com/Bestdoom20/bc-transit.git ~/.agents/skills/bc-transit   # Codex and other harnesses that read ~/.agents/skills
npx skills add Bestdoom20/bc-transit                                                 # any harness the skills CLI supports
```

Any other agent can use it by reading `SKILL.md` and running the script.

The first query for a system downloads its feed (about 1 MB for Kelowna) into `~/.cache/bctransit/` and reuses it for a day.

## Examples

All output below is real, run on 2026-11-19.

1. List the feeds (first 8 of 35 lines). Towns after the first name live inside that feed.

```
$ python3 bctransit.py systems
100 Mile House
Agassiz-Harrison, Abbotsford, Chilliwack, Mission
Ashcroft-Cache-Creek-Clinton
Bulkley-Nechako, Burns Lake, Prince George
Campbell River
Clearwater
Columbia Valley, Cranbrook, Fernie, Invermere, Kimberley
Comox Valley, Courtenay, Cumberland
```

2. Find a stop. An exchange has several bays, and all of them match.

```
$ python3 bctransit.py stops victoria "legislature"
 100002  Legislature Exch  (48.41974,-123.36901)
 100003  Legislature Exch Bay D  (48.41915,-123.36896)
 100004  Legislature Exch Bay F  (48.4183,-123.36936)
 100006  Legislature Exch Bay E  (48.41827,-123.36807)
 100029  Legislature Exch Bay C  (48.41897,-123.36896)
 100355  Legislature Exch Bay B  (48.41882,-123.36897)
 102211  Legislature Exch Bay A  (48.41865,-123.36896)
 102467  Legislature Exch (Belleville St) Bay G  (48.4206,-123.3681)
```

3. Next departures from a stop at a given date and time.

```
$ python3 bctransit.py next kelowna "ubco exchange" --date 2026-11-23 --at 07:00 -n 5
Monday 2026-11-23, scheduled times (feed valid 20261117 to 20261219)
Stops matched: 140103 UBCO Exchange Bay D; 140101 UBCO Exchange Bay B; 140098 UBCO Exchange; 140102 UBCO Exchange Bay C; 140099 UBCO Exchange Bay A; 140104 UBCO Exchange Bay E
               7:00 AM  route 84 Academy Way  from UBCO Exchange Bay A
               7:00 AM  route 97 Westbank  from UBCO Exchange Bay C
               7:05 AM  route 8 University - To UBCO  from UBCO Exchange Bay B
               7:06 AM  route 13 Quail Ridge  from UBCO Exchange Bay E
               7:07 AM  route 97 UBCO  from UBCO Exchange Bay C
```

4. Late at night. Buses that leave after midnight still belong to the evening's service, and are marked.

```
$ python3 bctransit.py next kelowna "queensway" --date 2026-11-20 --at 23:50 -n 6
Friday 2026-11-20, scheduled times (feed valid 20261117 to 20261219)
Stops matched: 102859 Queensway Exchange Bay E; 102861 Queensway Exchange Bay C; 102855 Queensway Exchange Bay I; 102856 Queensway Exchange Bay H; 102860 Queensway Exchange Bay D; 102854 Queensway Exchange Bay J
              11:50 PM  route 1 Downtown  from Queensway Exchange Bay C
              11:51 PM  route 11 Downtown  from Queensway Exchange Bay I
   12:00 AM (next day)  route 1 Lakeshore - Mission Rec Exch  from Queensway Exchange Bay C
   12:00 AM (next day)  route 10 To Rutland Exch  from Queensway Exchange Bay J
   12:00 AM (next day)  route 11 To Orchard Park  from Queensway Exchange Bay I
   12:00 AM (next day)  route 5 Downtown  from Queensway Exchange Bay D
```

5. "Which bus gets me downtown for 8:30?" The latest rides that arrive in time.

```
$ python3 bctransit.py trip kelowna "ubco exchange" "queensway" --date 2026-11-23 --arrive-by 08:30 -n 4
Monday 2026-11-23, scheduled times (feed valid 20261117 to 20261219)
6 boarding stop(s), 10 arrival stop(s) matched. Direct trips only.
  leave   7:45 AM  arrive   8:08 AM   23 min  route 97 Westbank
  leave   7:51 AM  arrive   8:24 AM   33 min  route 98 Downtown Via Rutland
  leave   8:00 AM  arrive   8:23 AM   23 min  route 97 Westbank
  leave   8:00 AM  arrive   8:27 AM   27 min  route 6 Downtown
```

6. A town that has no feed of its own. Vernon's routes are published inside the feed BC Transit calls "Shuswap". The script knows the town by name.

```
$ python3 bctransit.py trip vernon "ubco" "downtown exchange" --date 2026-11-23
Monday 2026-11-23, scheduled times (feed valid 20261117 to 20271231)
1 boarding stop(s), 7 arrival stop(s) matched. Direct trips only.
  leave   8:00 AM  arrive   8:51 AM   51 min  route 90 UBCO - To Vernon
  leave   9:00 AM  arrive   9:51 AM   51 min  route 90 UBCO - To Vernon
  leave  10:00 AM  arrive  10:51 AM   51 min  route 90 UBCO - To Vernon
  leave  12:00 PM  arrive  12:51 PM   51 min  route 90 UBCO - To Vernon
  leave   1:00 PM  arrive   1:51 PM   51 min  route 90 UBCO - To Vernon
  leave   2:00 PM  arrive   2:51 PM   51 min  route 90 UBCO - To Vernon
  leave   4:00 PM  arrive   4:51 PM   51 min  route 90 UBCO - To Vernon
  leave   5:00 PM  arrive   5:51 PM   51 min  route 90 UBCO - To Vernon
```

## How it works

A GTFS feed is a zip of CSV files. The script reads five of them:

| File | Used for |
|---|---|
| `stops.txt` | stop names and numbers |
| `routes.txt`, `trips.txt` | which route and direction each trip is |
| `stop_times.txt` | the time each trip reaches each stop |
| `calendar.txt`, `calendar_dates.txt` | which services run on a given date |

Three things in the data are easy to get wrong, and each has a case in the selftest:

- **Times past 24:00.** A bus that leaves at 12:30 AM on Saturday is written as `24:30:00` on Friday's service. Asking for Saturday has to pull in Friday's late trips, and asking for Friday has to label them "next day".
- **Service days.** A weekday trip must not show up on a Saturday. The weekly calendar is applied first, then the dated additions and removals for holidays.
- **One bus, several trips.** A loop route ends its trip at an exchange and the same vehicle carries on as a new trip with riders still on board. Kelowna's route 23 does this. Looking at single trips, a ride across that point does not exist. The script follows the vehicle through its `block_id`, so the ride is found.

## Check

```
$ python3 bctransit.py selftest
selftest ok
```

The selftest builds a four-trip feed in memory and asserts the three cases above. It needs no network.

## Limits

- **Scheduled times only.** It does not read live delays. For "is my bus late", use the BC Transit site or app.
- **One bus only.** `trip` does not plan transfers. For a trip with a change, run each leg and leave a few minutes between them.
- **One feed per query.** A trip that crosses from one feed into another needs one query for each.
- **A date outside the feed's valid range has no answer.** The first line of output shows the range.
- Each question reads the whole `stop_times.txt` once. That is fast enough for one person asking one question. A database would be the next step if it had to serve many.
- The feed numbers were taken from bctransit.com/open-data on 2026-11-19. If BC Transit renumbers a feed, the table at the top of the script needs the new number.

## How this was built

I designed it, decided what it had to get right (the three cases above) and directed AI coding agents to write the code. I tested it against real schedules and I can walk through every part.

## Licence

MIT. The schedule data comes from BC Transit's open data page (bctransit.com/open-data).
