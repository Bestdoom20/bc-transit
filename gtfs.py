#!/usr/bin/env python3
"""Exact scheduled times from any official GTFS feed in the world, found in the free Mobility Database catalog (stdlib only).

Backup for places Transitous (transit.py) does not cover yet: it reads the operator's own published timetable."""
import argparse, csv, io, os, re, sys, time, unicodedata, urllib.request, zipfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

CATALOG = 'https://share.mobilitydata.org/catalogs-csv'  # ~2,000 live GTFS feeds with coverage boxes, no key
CACHE = os.path.expanduser('~/.cache/worldwide-transit')
UA = 'worldwide-transit-skill/2.1'
DAY = 86400
LATLON = re.compile(r'^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$')


def fetch(url, path, max_age):
    if not os.path.exists(path) or time.time() - os.path.getmtime(path) > max_age:  # feeds change with each service change
        os.makedirs(CACHE, exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=30) as r, open(path + '.part', 'wb') as f:
            f.write(r.read())
        os.replace(path + '.part', path)
    return path


def catalog():
    """Live static GTFS feeds from the catalog (retired and deprecated ones dropped)."""
    with open(fetch(CATALOG, os.path.join(CACHE, 'catalog.csv'), 7 * DAY), encoding='utf-8-sig') as f:
        return [r for r in csv.DictReader(f) if r['data_type'] == 'gtfs' and r['status'] not in ('deprecated', 'inactive')]


def area(r):
    try:
        return (float(r['location.bounding_box.maximum_latitude']) - float(r['location.bounding_box.minimum_latitude'])) * \
               (float(r['location.bounding_box.maximum_longitude']) - float(r['location.bounding_box.minimum_longitude']))
    except ValueError:
        return float('inf')


def covers(r, lat, lon):
    try:
        return float(r['location.bounding_box.minimum_latitude']) <= lat <= float(r['location.bounding_box.maximum_latitude']) and \
               float(r['location.bounding_box.minimum_longitude']) <= lon <= float(r['location.bounding_box.maximum_longitude'])
    except ValueError:
        return False


def find_feeds(feeds, q):
    """A catalog id, a lat,lon (feeds whose area covers it, smallest first), or words from the operator or place name."""
    if q.isdigit():
        return [r for r in feeds if r['mdb_source_id'] == q]
    m = LATLON.match(q)
    if m:
        return sorted((r for r in feeds if covers(r, float(m[1]), float(m[2]))), key=area)
    words = q.lower().split()
    text = lambda r: ' '.join(r[k] for k in ('provider', 'name', 'location.municipality', 'location.subdivision_name', 'location.country_code')).lower()
    return sorted((r for r in feeds if all(w in text(r) for w in words)), key=area)


def label(r):
    where = ', '.join(x for x in (r['location.municipality'], r['location.subdivision_name'], r['location.country_code']) if x)
    return f"{r['mdb_source_id']:>5}  {r['provider'][:70]}{' - ' + r['name'] if r['name'] else ''}  ({where or 'area not listed'})"


def feed(q):
    hits = find_feeds(catalog(), q)
    if not hits:
        sys.exit(f'No live feed matches "{q}". Try a lat,lon, or: gtfs.py feeds "<operator or city>"')
    if len(hits) > 1 and not LATLON.match(q):
        sys.exit(f'"{q}" matches {len(hits)} feeds; pass the id:\n' + '\n'.join(label(r) for r in hits[:15]))
    r, path = hits[0], os.path.join(CACHE, f"{hits[0]['mdb_source_id']}.zip")
    urls = [r['urls.direct_download']] if r['urls.authentication_type'] in ('', '0') and r['urls.direct_download'] else []
    for i, url in enumerate(urls + [r['urls.latest']]):  # the operator's own link first, the catalog's mirror if that fails
        try:
            z = zipfile.ZipFile(fetch(url, path, DAY))
            break
        except Exception as e:
            print(f'download failed ({url}): {e}', file=sys.stderr)
            if os.path.exists(path) and i == 0:
                os.remove(path)
    else:
        sys.exit(f'Could not download feed {r["mdb_source_id"]}.')
    print(f'Feed {label(r).strip()}')
    return z


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
    return (datetime(2000, 1, 1) + timedelta(seconds=t)).strftime('%I:%M %p').lstrip('0') + (' (next day)' if t >= DAY else '')


def stops(z, q):
    """A stop number or id matches exactly; otherwise every word of q must appear in the stop name."""
    allstops = list(rows(z, 'stops.txt'))
    exact = [s for s in allstops if q in (s.get('stop_code'), s['stop_id'])]
    return exact or [s for s in allstops if all(w in fold(s['stop_name']) for w in fold(q).split())]


def fold(text):
    """Lower case without accents, so "zocalo" finds "Zócalo"."""
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


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
    info, off, out, start = trip_info(z), day_offsets(z, d), [], {}
    freq = {}  # headway-based trips (many metros): the trip's times repeat every headway_secs within each window
    for f in rows(z, 'frequencies.txt'):
        freq.setdefault(f['trip_id'], []).append((secs(f['start_time']), secs(f['end_time']), int(f['headway_secs'])))
    # ponytail: one full pass over stop_times per question (1 to 8 s); cache in sqlite if that gets slow
    for r in rows(z, 'stop_times.txt'):
        if r['departure_time']:
            start.setdefault(r['trip_id'], secs(r['departure_time']))  # rows come in stop order
        if r['stop_id'] in ids and r['departure_time']:
            rt, svc, head, _ = info[r['trip_id']]
            base = secs(r['departure_time'])
            starts = [w + k for a, b, h in freq[r['trip_id']] for w in [a] for k in range(0, b - a, h)] if r['trip_id'] in freq else [start[r['trip_id']]]
            for s0 in starts:
                t = s0 + base - start[r['trip_id']] + off.get(svc, -10 * DAY)
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


def selftest():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('routes.txt', 'route_id,route_short_name,route_long_name\nR,23,Loop\n')
        z.writestr('trips.txt', 'route_id,service_id,trip_id,trip_headsign,block_id\nR,WK,T1,North,X\nR,WK,T2,North,\n'
                   'R,SAT,T3,North,\nR,WK,T4,South,X\n')
        z.writestr('stops.txt', 'stop_id,stop_name,stop_code\nA,Main at First,100\nB,Lake Exchange,200\nC,College,300\n')
        z.writestr('stop_times.txt', 'trip_id,arrival_time,departure_time,stop_id,stop_sequence\n'
                   'T1,08:00:00,08:00:00,A,1\nT1,08:20:00,08:20:00,B,2\nT2,24:30:00,24:30:00,A,1\nT2,24:50:00,24:50:00,B,2\n'
                   'T3,09:00:00,09:00:00,B,1\nT3,09:15:00,09:15:00,A,2\nT4,08:22:00,08:22:00,B,1\nT4,08:40:00,08:40:00,C,2\n')
        z.writestr('frequencies.txt', 'trip_id,start_time,end_time,headway_secs\nT3,09:00:00,10:00:00,1800\n')
        z.writestr('calendar_dates.txt', 'service_id,date,exception_type\nWK,20261120,1\nSAT,20261121,1\n')
    z = zipfile.ZipFile(buf)
    fri, sat = datetime(2026, 11, 20).date(), datetime(2026, 11, 21).date()
    assert [clock(t) for t, *_ in departures(z, fri, 0, '100')[0]] == ['8:00 AM', '12:30 AM (next day)']
    assert fold('Zócalo') == 'zocalo'
    assert [clock(t) for t, *_ in departures(z, sat, 0, 'main first')[0]] == ['12:30 AM', '9:15 AM', '9:45 AM'], 'Friday late trip shows on Saturday; T3 repeats every 30 min'
    assert [(clock(d), clock(a)) for d, a, *_ in direct_trips(z, fri, '100', 'lake')[0]] == [('8:00 AM', '8:20 AM'), ('12:30 AM (next day)', '12:50 AM (next day)')]
    assert direct_trips(z, sat, '100', 'lake')[0][1:] == [], 'Saturday trip runs the other way, so only the late Friday trip counts'
    assert [(clock(d), clock(a)) for d, a, *_ in direct_trips(z, fri, '100', 'college')[0]] == [('8:00 AM', '8:40 AM')], 'same bus, two linked trips'
    box = lambda i, name, a, b, c, d: {'mdb_source_id': i, 'provider': name, 'name': '', 'location.municipality': '', 'location.subdivision_name': '',
                                       'location.country_code': 'CA', 'location.bounding_box.minimum_latitude': a, 'location.bounding_box.maximum_latitude': b,
                                       'location.bounding_box.minimum_longitude': c, 'location.bounding_box.maximum_longitude': d}
    cat = [box('1', 'Big Coach Lines', '40', '60', '-130', '-100'), box('2', 'Kelowna Regional Transit', '49.7', '50.1', '-119.8', '-119.3'), box('3', 'No Box', '', '', '', '')]
    assert [r['mdb_source_id'] for r in find_feeds(cat, '49.9,-119.5')] == ['2', '1'], 'smallest covering area first'
    assert [r['mdb_source_id'] for r in find_feeds(cat, 'kelowna transit')] == ['2'] and find_feeds(cat, '3')[0]['provider'] == 'No Box'
    print('selftest ok')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('selftest')
    f = sub.add_parser('feeds'); f.add_argument('query')
    s = sub.add_parser('stops'); s.add_argument('feed'); s.add_argument('query')
    for name in ('next', 'trip'):
        c = sub.add_parser(name); c.add_argument('feed'); c.add_argument('stop')
        if name == 'trip':
            c.add_argument('to'); c.add_argument('--arrive-by', metavar='HH:MM')
        else:
            c.add_argument('--route')
        c.add_argument('--at', metavar='HH:MM'); c.add_argument('--date', metavar='YYYY-MM-DD'); c.add_argument('-n', type=int, default=8)
    a = p.parse_args()
    if a.cmd == 'feeds':
        return print('\n'.join(label(r) for r in find_feeds(catalog(), a.query)[:30]) or 'no live feed matches')
    if a.cmd == 'selftest':
        return selftest()
    z = feed(a.feed)
    if a.cmd == 'stops':
        return print('\n'.join(f"{s.get('stop_code') or s['stop_id']:>7}  {s['stop_name']}  ({s['stop_lat']},{s['stop_lon']})" for s in stops(z, a.query)) or 'no stop matches')
    now = datetime.now(ZoneInfo(next(iter(rows(z, 'agency.txt')))['agency_timezone']))  # the feed's own zone
    d = datetime.strptime(a.date, '%Y-%m-%d').date() if a.date else now.date()
    t0 = secs(a.at + ':00') if a.at else (0 if a.date else now.hour * 3600 + now.minute * 60)
    info = next(iter(rows(z, 'feed_info.txt')), {})
    if not info.get('feed_end_date'):  # no feed_info: the feed lasts as long as its last calendar
        info['feed_end_date'] = max((r['end_date'] for r in rows(z, 'calendar.txt')), default='99999999')
    print(f"{d:%A %Y-%m-%d}, scheduled times in {now.tzinfo.key} (feed valid {info.get('feed_start_date', '?')} to {info.get('feed_end_date', '?')})")
    if info.get('feed_end_date', '99999999') < f'{d:%Y%m%d}':
        sys.exit(f"FEED EXPIRED: it ends {info['feed_end_date']}, so it has no times for {d}. Use the operator's own website.")
    if a.cmd == 'next':
        deps, matched = departures(z, d, t0, a.stop, a.route)
        print('Stops matched: ' + '; '.join(f"{s.get('stop_code') or s['stop_id']} {s['stop_name']}" for s in matched[:6]) if matched else 'no stop matches')
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
