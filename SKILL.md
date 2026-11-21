---
name: bc-transit
description: Exact scheduled bus times for BC Transit systems (Victoria, Kelowna, Kamloops, Nanaimo, Whistler, Vernon, Prince George and 30 more) from the official GTFS schedule feeds. Use when the user asks "when is the next bus", "bus times", "last bus home", "first bus", "can I get to X by bus for 8:30", "route 23", "BC Transit", or needs a commute check by bus anywhere in British Columbia outside Metro Vancouver.
license: MIT
compatibility: Python 3.9+ (standard library only), internet access to bct.tmix.se. Linux or macOS.
---

# BC Transit bus times

Run `bctransit.py`, which sits in the same folder as this file. Do not answer bus times from memory or a web search: schedules change several times a year and the feed is the source.

```bash
S="<this skill's folder>/bctransit.py"
python3 "$S" systems                                    # the 35 feeds and the towns inside each
python3 "$S" stops victoria "legislature"               # find a stop: words from its name, or its stop number
python3 "$S" next kelowna 140098                        # next departures from a stop, from now
python3 "$S" next kelowna "ubco exchange" --date 2026-11-23 --at 07:00 --route 97 -n 10
python3 "$S" trip kelowna "ubco exchange" "queensway" --arrive-by 08:30   # one-bus rides, latest that make it
python3 "$S" trip kelowna "queensway" "ubco exchange" --date 2026-11-21 --at 21:00
```

- A stop is its stop number (printed on the pole) or words from its name. Several stops can match (an exchange has bays); all are used.
- `--date` defaults to today, `--at` to now (to the start of the day when a date is given). Times are Pacific.
- Output is already in 12-hour time. Show it that way.
- The first output line names the dates the feed is valid for. A date outside that range has no answer yet: say so.

## Limits (say them when they matter)

- **Scheduled times only.** No live delays. For "is my bus late", point to the BC Transit site or the Umo app.
- **One bus only.** `trip` follows a single vehicle (including a loop route that continues under a new trip). No transfer planning: run each leg and leave a few minutes between them.
- **Feeds hold several systems under one name.** Vernon is inside "Shuswap", Prince George inside "Bulkley-Nechako", Abbotsford and Chilliwack inside "Agassiz-Harrison". The script knows these towns (`systems` lists them). A town not listed may sit in a neighbour's feed.
- A trip crossing two feeds needs one query per feed.
- Metro Vancouver (TransLink) is not BC Transit and is not covered.
- Feeds are cached for a day in `~/.cache/bctransit/`. Delete the file to force a fresh download.

## Check

`python3 "$S" selftest` must print `selftest ok`.
