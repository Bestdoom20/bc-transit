---
name: worldwide-transit
description: Travel planner for anywhere in the world, free, no API key, no setup. Live flight prices and the cheapest days to fly, trains, intercity coaches, ferries, local buses and metro with transfers and live delays, driving distance, time and fuel cost, and multi-city trips priced leg by leg. Use when the user asks "how do I get from X to Y", "when is the next bus", "cheapest flight to Japan in January", "plan a 30-day trip", "is it cheaper to drive to Vancouver and fly from there", "how long is the drive", "what will gas cost", "Kelowna to Calgary", "route 97", or anything about getting somewhere.
license: MIT
compatibility: Python 3.9+ (standard library only). Needs internet access to api.transitous.org, www.google.com, valhalla1.openstreetmap.de, router.project-osrm.org, share.mobilitydata.org, storage.googleapis.com and operators' feed hosts. Linux, macOS, Windows (on Windows run `pip install tzdata` once).
---

# Worldwide Transit: travel planner

Four scripts sit in the same folder as this file. Answer from them, never from memory: fares and timetables change daily.

| Script | Answers |
|---|---|
| `flights.py` | live flight prices, cheapest days to leave for a stay of N days, multi-city legs (Google Flights' public data) |
| `transit.py` | trains, coaches, ferries, city buses and metro with transfers and live delays, departures, place lookup (Transitous) |
| `drive.py` | driving distance, time and fuel for any road trip (OpenStreetMap routers) |
| `gtfs.py` | exact times from any official timetable feed in the world, for places `transit.py` lacks |

```bash
D="<this skill's folder>"
```

## First use: the home region (do this before anything else)

Run `python3 "$D/transit.py" home`. If nothing is saved, ask ONE short question: what city or region they are usually in. Save it with its time zone and currency:

```bash
python3 "$D/transit.py" home "Kelowna, BC" --tz America/Vancouver --currency CAD
```

It steers place lookups, sets the time zone, and sets the currency for flight prices. If the harness keeps no files between chats, ask once per chat and pass `--tz` / `--currency` on each command.

## Flights

Use IATA airport codes. Join several airports with commas to search them together (`NRT,HND` for Tokyo, `YVR,YLW`).

```bash
python3 "$D/flights.py" search YLW NRT,HND 2027-01-12 --return 2027-02-11          # live fares, round trip
python3 "$D/flights.py" dates YLW NRT,HND --from 2027-01-05 --to 2027-01-25 --stay 30   # cheapest day to leave for 30 days
python3 "$D/flights.py" multi YLW-NRT:2027-01-12 NRT-BKK:2027-01-26 BKK-YVR:2027-02-09  # a multi-city trip, leg by leg
```

Options: `--adults N`, `--cabin economy|premium|business|first`, `--stops any|0|1|2`, `--currency XXX`, `-n`.

- Round-trip prices are the total for the round trip; the outbound flights are listed.
- `dates` makes one request per day (31 days at most, about 2 seconds each). Tell the user it takes a minute.
- "refusing requests right now (rate limit)" is NOT "no flights". Wait a few minutes, then retry once.
- Prices move hour to hour and between searches. Always give the "Check and book" link, and say prices are what Google Flights showed at that moment.

## Ground: trains, coaches, ferries, buses

```bash
python3 "$D/transit.py" plan "Pacific Central Station, Vancouver" "King Street Station, Seattle" --date 2026-11-24 --at 08:00
python3 "$D/transit.py" plan "Tsawwassen" "Swartz Bay" --date 2026-11-24                    # ferries are in the planner
python3 "$D/transit.py" plan "Narita Airport" "Shinjuku" --near Tokyo --tz Asia/Tokyo -n 2  # away from home: --near and --tz
python3 "$D/transit.py" next "UBCO Exchange" -n 10                                         # departures from a stop
```

- `--date`, `--at HH:MM` or `--arrive-by HH:MM`. Times use the home zone unless `--tz` is given; for trips elsewhere pass the local zone and say which zone the times are in.
- Check the `From:` / `To:` / `Stop:` lines. Wrong town? Retry with `--near <city>`, a fuller name, or lat,lon.
- `[live]` is realtime; `(+3 min late)` is a delay. Output is already 12-hour time.

**When `plan` finds no route**, it prints `gtfs.py feeds <lat,lon>` for both ends. Run it, pick the local operator's id, then `gtfs.py stops <id> "<words>"`, `gtfs.py next <id> "<stop>"` or `gtfs.py trip <id> "<from>" "<to>" --arrive-by HH:MM` (one vehicle, no transfers). `FEED EXPIRED` means do not use it. Operators with no open data at all (Canadian intercity coaches such as Ebus and Rider Express, many private lines): find the schedule on the operator's own site and say so.

## Driving

```bash
python3 "$D/drive.py" "Kelowna" "Vancouver International Airport" --consumption 8.5 --fuel-price 1.62
python3 "$D/drive.py" "Kelowna" "Calgary" --via "Revelstoke" --consumption 8.5
python3 "$D/drive.py" "Seattle" "Portland" --imperial --consumption 30 --fuel-price 4.10 --currency USD
```

- Time is at typical road speeds before traffic, meal stops and border waits. For drives over about 5 hours, say so and suggest breaks.
- `--consumption` is what their car uses (L/100 km, or mpg with `--imperial`). Ask what they drive once, then reuse it.
- `--fuel-price` must be a real current price: ask the user, or look up today's average for that region on the web and name the source and date. Without it the script prints litres only. Never guess a fuel price.
- Places separated by sea return "No driving route": add a ferry (`transit.py`) or a flight.

## Planning a whole trip

1. **Pin down the brief in one message:** from where, to where (or "somewhere warm"), leave date or window, how many days, who is going (adults, children), and any must-haves (nonstop, cabin, budget, places to see). Default anything they skip and say what you assumed.
2. **Flights first.** `dates` over their window with `--stay` for the cheapest day, then `search` that day for the actual flights.
3. **Compare airports.** If a bigger airport nearby is cheaper (YVR instead of YLW, SEA from Vancouver), price getting there: `drive.py` with fuel, or `transit.py` / a coach. Add parking only from the airport's published rate. Show both options side by side: total time and total priced cost.
4. **Multi-city trips:** choose an order that avoids backtracking, give each place its days, price it with `multi`, and check whether a train, coach or ferry beats a flight on short legs (`transit.py plan` between the cities).
5. **Door to door time:** drive or transit to the airport + time at the airport before departure (state it as airline guidance, typically 2 h international, 1.5 h domestic) + flight time from `flights.py` + airport to the first night's stay with `transit.py`.
6. **Entry rules:** for international trips, check the destination government's official entry requirements for the traveller's citizenship (visa, passport validity, onward ticket) and link the source.

## Money rules (never break)

- Every price shown comes from a script output or a page you fetched, with its source. No estimates, no "about", no typical prices from memory.
- Anything you could not price (hotels, parking, transit fares, ferries, visas) is listed as "not priced", with a link to where to price it. You may look up real listings on the web and cite them.
- Totals add up only priced items, and say what is left out.

## Booking

This skill never books or pays. It finds and compares; the user books through the links (Google Flights, the airline, the operator). Do not enter payment details or passenger data anywhere on their behalf.

## Limits (say them when they matter)

- Flight prices come from Google Flights' public web data, which has no official API: Google may throttle or change it. Treat results as a strong lead, then confirm on the link.
- Ground coverage is whatever operators publish as open data: strong across Europe, North America, Japan and Australia, patchy for private coaches and parts of South Asia and Africa.
- The routing and transit servers are free community services: one request per question, no loops beyond `dates`.

## Check

`python3 "$D/transit.py" selftest`, `python3 "$D/gtfs.py" selftest`, `python3 "$D/flights.py" selftest` and `python3 "$D/drive.py" selftest` must all print `selftest ok`.
