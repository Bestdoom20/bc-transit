#!/usr/bin/env python3
"""Exact scheduled bus times for any BC Transit system, read from its official GTFS feed (stdlib only)."""
import argparse, csv, io, os, sys, time, urllib.request, zipfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Feed numbers and names from https://www.bctransit.com/open-data/ (2026-11-19). One feed often carries several
# neighbouring systems under a single name (Vernon's routes are inside "Shuswap"), so towns are listed in ALIASES.
SYSTEMS = {'Cowichan Valley': 10, 'Port Alberni': 11, 'Campbell River': 12, 'Agassiz-Harrison': 13, 'Shuswap': 14,
           'South Okanagan-Similkameen': 15, 'Creston Valley': 16, 'Mount Waddington': 17, 'Sunshine Coast': 18,
           'West Kootenay': 20, 'Columbia Valley': 21, 'Bulkley-Nechako': 22, 'Port Edward': 23, 'Hazeltons': 26,
           'Dawson Creek': 27, 'Fort St. John': 28, 'Powell River': 29, 'Smithers': 31, 'Quesnel': 32, 'Williams Lake': 33,
           '100 Mile House': 34, 'Clearwater': 35, 'Revelstoke': 36, 'Merritt': 37, 'Ashcroft-Cache-Creek-Clinton': 38,
           'Salt Spring Island': 39, 'Nanaimo': 41, 'Squamish': 43, 'Whistler': 44, 'Comox Valley': 45, 'Kamloops': 46,
           'Kelowna': 47, 'Victoria': 48, 'Pemberton Valley': 50, 'West Coast': 51}
# Towns found in each feed's route list on 2026-11-19, for the feeds whose name hides them.
ALIASES = {'Vernon': 14, 'Salmon Arm': 14, 'Enderby': 14, 'Lumby': 14, 'Abbotsford': 13, 'Mission': 13, 'Chilliwack': 13,
           'Penticton': 15, 'Summerland': 15, 'Osoyoos': 15, 'Princeton': 15, 'Nelson': 20, 'Castlegar': 20, 'Trail': 20,
           'Rossland': 20, 'Nakusp': 20, 'Kaslo': 20, 'Cranbrook': 21, 'Kimberley': 21, 'Fernie': 21, 'Invermere': 21,
           'Prince George': 22, 'Burns Lake': 22, 'Prince Rupert': 23, 'Kitimat': 26, 'Terrace': 26, 'Lake Country': 47,
           'West Kelowna': 47, 'Peachland': 47, 'Duncan': 10, 'Ladysmith': 10, 'Parksville': 41, 'Qualicum': 41,
           'Courtenay': 45, 'Cumberland': 45, 'Sechelt': 18, 'Gibsons': 18, 'Tofino': 51, 'Ucluelet': 51,
           'Port Hardy': 17, 'Port McNeill': 17}
PLACES = {**SYSTEMS, **ALIASES}
FEED = 'https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=%d'
CACHE = os.path.expanduser('~/.cache/bctransit')
TZ = ZoneInfo('America/Vancouver')
DAY = 86400


def feed(system):
    hits = sorted({PLACES[n] for n in PLACES if system.lower() in n.lower()})
    if len(hits) != 1:
        sys.exit(f'"{system}" matches {len(hits)} feeds. Run: bctransit.py systems')
    path = os.path.join(CACHE, f'{hits[0]}.zip')
    if not os.path.exists(path) or time.time() - os.path.getmtime(path) > DAY:  # feeds change with each service change
        os.makedirs(CACHE, exist_ok=True)
        urllib.request.urlretrieve(FEED % hits[0], path)
    return zipfile.ZipFile(path)


def rows(z, name):
    return csv.DictReader(io.TextIOWrapper(z.open(name), 'utf-8-sig')) if name in z.namelist() else []


def services(z, d):
    """Service ids running on date d: the weekly calendar, then the dated additions (1) and removals (2)."""
    ymd, on = d.strftime('%Y%m%d'), set()
    for r in rows(z, 'calendar.txt'):
        if r['start_date'] <= ymd <= r['end_date'] and r[d.strftime('%A').lower()] == '1':
            on.add(r['service_id'])
    for r in rows(z, 'calendar_dates.txt'):
        if r['date'] == ymd:
            (on.add if r['exception_type'] == '1' else on.discard)(r['service_id'])
    return on


def secs(hms):
    h, m, s = hms.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def clock(t):
    """Seconds after midnight as 1:07 PM; schedule times past 24:00 belong to the next morning."""
    return (datetime(2000, 1, 1) + timedelta(seconds=t)).strftime('%-I:%M %p') + (' (next day)' if t >= DAY else '')


def stops(z, q):
    """A stop number or id matches exactly; otherwise every word of q must appear in the stop name."""
    allstops = list(rows(z, 'stops.txt'))
    exact = [s for s in allstops if q in (s.get('stop_code'), s['stop_id'])]
    return exact or [s for s in allstops if all(w in s['stop_name'].lower() for w in q.lower().split())]


def trip_info(z):
    names = {r['route_id']: r['route_short_name'] or r['route_long_name'] for r in rows(z, 'routes.txt')}
    return {t['trip_id']: (names[t['route_id']], t['service_id'], t.get('trip_headsign', ''), t.get('block_id', ''))
            for t in rows(z, 'trips.txt')}


def day_offsets(z, d):
    """service id -> seconds to add so a schedule time lands on date d (yesterday's service runs past midnight)."""
    off = {s: -DAY for s in services(z, d - timedelta(days=1))}
    off.update({s: 0 for s in services(z, d)})  # ponytail: a service on both days keeps only today's trips
    return off


def departures(z, d, t0, stop_q, route=None):
    ids = {s['stop_id']: s for s in stops(z, stop_q)}
    info, off, out = trip_info(z), day_offsets(z, d), []
    # ponytail: one full pass over stop_times per question (1 to 8 s); cache in sqlite if that gets slow
    for r in rows(z, 'stop_times.txt'):
        if r['stop_id'] in ids and r['departure_time']:
            rt, svc, head, _ = info[r['trip_id']]
            t = secs(r['departure_time']) + off.get(svc, -10 * DAY)
            if t >= t0 and (not route or rt == route):
                out.append((t, rt, head or r.get('stop_headsign', ''), ids[r['stop_id']]['stop_name']))
    return sorted(out), list(ids.values())


def direct_trips(z, d, a_q, b_q):
    """Rides on ONE bus from a stop matching a_q to a later stop matching b_q. No transfers.

    One bus can be several linked trips (same block_id): a loop route ends a trip at its exchange and the same
    vehicle carries on as the next trip with riders still aboard, so the ride is followed along the block."""
    a, b = {s['stop_id'] for s in stops(z, a_q)}, {s['stop_id'] for s in stops(z, b_q)}
    info, off, start, seen, out = trip_info(z), day_offsets(z, d), {}, {}, []
    for r in rows(z, 'stop_times.txt'):
        trip = r['trip_id']
        if r['departure_time'] and trip not in start:
            start[trip] = secs(r['departure_time'])  # rows come in stop order, so the first one is the trip's start
        if r['stop_id'] in a or r['stop_id'] in b:
            rt, svc, head, block = info[trip]
            if svc in off:
                seen.setdefault((block, svc) if block else trip, []).append(
                    (start.get(trip, 0), int(r['stop_sequence']), r['stop_id'], r['departure_time'], r['arrival_time'], rt, head, svc))
    for visits in seen.values():
        board = None
        for _, _, sid, dep, arr, rt, head, svc in sorted(visits):
            if sid in b and board and arr:  # the latest boarding before each arrival is the ride
                t_dep, t_arr = board[0] + off[svc], secs(arr) + off[svc]
                # under two hours: a bus parked between runs is not a ride. From midnight on: yesterday's
                # service only counts for its trips past midnight.
                if t_dep >= 0 and t_arr - t_dep < 7200:
                    out.append((t_dep, t_arr, board[1], board[2]))
                board = None
            if sid in a and dep:
                board = (secs(dep), rt, head)
    return sorted(out), len(a), len(b)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('systems')
    s = sub.add_parser('stops'); s.add_argument('system'); s.add_argument('query')
    for name in ('next', 'trip'):
        c = sub.add_parser(name); c.add_argument('system'); c.add_argument('stop')
        if name == 'trip':
            c.add_argument('to'); c.add_argument('--arrive-by', metavar='HH:MM')
        else:
            c.add_argument('--route')
        c.add_argument('--at', metavar='HH:MM'); c.add_argument('--date', metavar='YYYY-MM-DD'); c.add_argument('-n', type=int, default=8)
    a = p.parse_args()
    if a.cmd == 'systems':
        return print('\n'.join(n + ''.join(f', {t}' for t, i in sorted(ALIASES.items()) if i == SYSTEMS[n]) for n in sorted(SYSTEMS)))
    z = feed(a.system)
    if a.cmd == 'stops':
        return print('\n'.join(f"{s.get('stop_code') or s['stop_id']:>7}  {s['stop_name']}  ({s['stop_lat']},{s['stop_lon']})" for s in stops(z, a.query)) or 'no stop matches')
    now = datetime.now(TZ)
    d = datetime.strptime(a.date, '%Y-%m-%d').date() if a.date else now.date()
    t0 = secs(a.at + ':00') if a.at else (0 if a.date else now.hour * 3600 + now.minute * 60)
    info = next(iter(rows(z, 'feed_info.txt')), {})
    print(f"{d:%A %Y-%m-%d}, scheduled times (feed valid {info.get('feed_start_date', '?')} to {info.get('feed_end_date', '?')})")
    if a.cmd == 'next':
        deps, matched = departures(z, d, t0, a.stop, a.route)
        print('Stops matched: ' + '; '.join(f"{s.get('stop_code')} {s['stop_name']}" for s in matched[:6]) if matched else 'no stop matches')
        for t, rt, head, stop in deps[:a.n]:
            print(f'  {clock(t):>20}  route {rt} {head}  from {stop}')
    else:
        found, na, nb = direct_trips(z, d, a.stop, a.to)
        if a.arrive_by:
            found = [x for x in found if x[1] <= secs(a.arrive_by + ':00')][-a.n:]
        else:
            found = [x for x in found if x[0] >= t0][:a.n]
        print(f'{na} boarding stop(s), {nb} arrival stop(s) matched. Direct trips only.')
        for dep, arr, rt, head in found:
            print(f'  leave {clock(dep):>9}  arrive {clock(arr):>9}  {(arr - dep) // 60:>3} min  route {rt} {head}')
        if not found:
            print('  none: no single bus serves both stops in that order at that time (try each leg separately)')


if __name__ == '__main__':
    main()
