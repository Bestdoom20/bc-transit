#!/usr/bin/env python3
"""Worldwide public transport trips and departures from Transitous (https://transitous.org), free, no key. Stdlib only."""
import argparse, json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API = 'https://api.transitous.org/api'
UA = 'transit-agent-skill/1.0'  # Transitous asks clients to send a User-Agent
HOME = os.path.join(os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'), 'transit', 'home.json')
LATLON = re.compile(r'^\s*(-?\d+(\.\d+)?)\s*,\s*(-?\d+(\.\d+)?)\s*$')


def get(path, **params):
    url = f'{API}{path}?' + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f'Transitous returned HTTP {e.code} for {url}: {e.read()[:300].decode(errors="replace")}')
    except urllib.error.URLError as e:
        sys.exit(f'Cannot reach {API} ({e.reason}). This needs internet access to api.transitous.org.')


def home():
    try:
        with open(HOME) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def zone(tz):
    h = home()
    return ZoneInfo(tz or (h and h['tz']) or 'UTC')


def geocode(text, stops_only=False):
    h = home()
    return get('/v1/geocode', text=text, type='STOP' if stops_only else None,
               place=f"{h['lat']},{h['lon']}" if h else None)  # bias results toward the saved home region


def area(p):
    return ', '.join(a['name'] for a in reversed(p.get('areas', [])[:3]) if a.get('name') != p['name'])


def place(text):
    """'lat,lon' passes through; anything else is geocoded and the best match is used (and printed)."""
    if LATLON.match(text):
        return text.replace(' ', ''), text
    hits = geocode(text)
    if not hits:
        sys.exit(f'No place found for "{text}". Try a fuller name, e.g. "Pacific Central Station, Vancouver", or lat,lon.')
    p = hits[0]
    return p['id'] if p['type'] == 'STOP' else f"{p['lat']},{p['lon']}", f"{p['name']} ({area(p)})"


def when(date, hm, tz):
    """--date/--at in the given zone, as the UTC instant Transitous expects. None = now."""
    if not date and not hm:
        return None
    d = datetime.strptime(date, '%Y-%m-%d').date() if date else datetime.now(tz).date()
    t = datetime.strptime(hm or '00:00', '%H:%M').time()
    return datetime.combine(d, t, tz).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def clock(iso, tz, day=False):
    t = datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(tz)
    s = t.strftime('%I:%M %p').lstrip('0')
    return (t.strftime('%a %b %d ') + s) if day else s


def mins(sec):
    m = round(sec / 60)
    return f'{m // 60}h{m % 60:02d}m' if m >= 60 else f'{m} min'


def late(stop, key):
    """' (+N min late)' when the realtime time differs from the timetable."""
    a, b = stop.get(key), stop.get('scheduled' + key[0].upper() + key[1:])
    if not a or not b or a == b:
        return ''
    d = round((datetime.fromisoformat(a.replace('Z', '+00:00')) - datetime.fromisoformat(b.replace('Z', '+00:00'))).total_seconds() / 60)
    return f' ({"+" if d > 0 else ""}{d} min {"late" if d > 0 else "early"})' if d else ''


def show_plan(d, tz, n):
    its = d.get('itineraries', [])[:n]
    if not its:
        print('No public transport route found in open data. See SKILL.md "When there is no route".')
    for it in its:
        print(f"\nleave {clock(it['startTime'], tz, True)}  arrive {clock(it['endTime'], tz, True)}  "
              f"{mins(it['duration'])}  {it['transfers']} transfer(s)")
        for l in it['legs']:
            if l['mode'] == 'WALK':
                if l['duration'] >= 60:
                    print(f"    walk {mins(l['duration'])} to {l['to']['name']}")
                continue
            who = ' '.join(dict.fromkeys(x for x in (l.get('agencyName'), l.get('routeShortName')) if x))
            head = f" toward {l['headsign']}" if l.get('headsign') else ''
            live = ' [live]' if l.get('realTime') else ''
            print(f"    {clock(l['startTime'], tz)}{late(l['from'], 'departure')}  {l['mode'].lower()} {who}{head}{live}\n"
                  f"        {l['from']['name']} -> {l['to']['name']}  arrive {clock(l['endTime'], tz)}{late(l['to'], 'arrival')}")


def cmd_home(a):
    if not a.place:
        h = home()
        print(json.dumps(h) if h else f'No home region saved ({HOME}). Ask the user for their city or region, then run: home "<city>" --tz <IANA zone>')
        return
    if not a.tz:
        sys.exit('Give the time zone too, e.g. home "Kelowna, BC" --tz America/Vancouver')
    ZoneInfo(a.tz)  # fails loudly on a bad zone name
    hits = get('/v1/geocode', text=a.place)
    if not hits:
        sys.exit(f'No place found for "{a.place}".')
    p = hits[0]
    h = {'name': f"{p['name']}, {area(p)}", 'lat': p['lat'], 'lon': p['lon'], 'tz': a.tz}
    os.makedirs(os.path.dirname(HOME), exist_ok=True)
    with open(HOME, 'w') as f:
        json.dump(h, f)
    print(f"Home region saved: {h['name']} ({h['lat']:.4f},{h['lon']:.4f}), times in {a.tz}. File: {HOME}")


def cmd_find(a):
    for p in geocode(a.text, a.stops)[:a.n]:
        print(f"{p['type']:7} {p['name']}  ({area(p)})  {p['lat']:.5f},{p['lon']:.5f}  id={p['id']}")


def cmd_plan(a):
    tz = zone(a.tz)
    (f, fn), (t, tn) = place(a.origin), place(a.dest)
    print(f'From: {fn}\nTo:   {tn}\nTimes in {tz.key}')
    d = get('/v5/plan', fromPlace=f, toPlace=t, time=when(a.date, a.arrive_by or a.at, tz),
            arriveBy='true' if a.arrive_by else None, numItineraries=a.n, maxTransfers=a.max_transfers)
    show_plan(d, tz, a.n)


def cmd_next(a):
    tz = zone(a.tz)
    hits = [{'id': a.stop, 'name': a.stop}] if '_' in a.stop and ' ' not in a.stop else geocode(a.stop, True)
    if not hits:
        sys.exit(f'No stop found for "{a.stop}". Try: find "{a.stop}" --stops')
    s = hits[0]
    print(f"Stop: {s['name']}  id={s['id']}\nTimes in {tz.key}")
    d = get('/v5/stoptimes', stopId=s['id'], n=a.n, time=when(a.date, a.at, tz))
    for x in d.get('stopTimes', []):
        p = x['place']
        print(f"  {clock(p.get('departure') or p['arrival'], tz, True)}{late(p, 'departure')}  {x['mode'].lower()} "
              f"{x.get('agencyName', '')} {x.get('routeShortName', '')} toward {x.get('headsign', '?')}{' [live]' if x.get('realTime') else ''}")
    if not d.get('stopTimes'):
        print('  No departures in open data for this stop and time.')


def selftest():
    tz = ZoneInfo('Europe/Berlin')
    assert when('2026-11-24', '08:00', tz) == '2026-11-24T07:00:00Z'
    assert when('2026-07-01', '08:00', tz) == '2026-07-01T06:00:00Z'  # summer time
    assert clock('2026-11-24T07:05:00Z', tz) == '8:05 AM'
    assert mins(3720) == '1h02m' and mins(600) == '10 min'
    assert late({'departure': '2026-11-24T16:07:00Z', 'scheduledDeparture': '2026-11-24T16:05:00Z'}, 'departure') == ' (+2 min late)'
    assert place('49.88, -119.49')[0] == '49.88,-119.49'
    print('selftest ok')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('home', help='show or save the home region')
    p.add_argument('place', nargs='?'); p.add_argument('--tz', help='IANA zone, e.g. America/Vancouver')
    p = sp.add_parser('find', help='look up a place or stop')
    p.add_argument('text'); p.add_argument('--stops', action='store_true'); p.add_argument('-n', type=int, default=8)
    p = sp.add_parser('plan', help='trip from A to B, with transfers')
    p.add_argument('origin'); p.add_argument('dest')
    p.add_argument('--max-transfers', type=int)
    p = sp.add_parser('next', help='next departures from a stop')
    p.add_argument('stop')
    for name in ('plan', 'next'):
        q = sp.choices[name]
        q.add_argument('--date', help='YYYY-MM-DD'); q.add_argument('--at', help='HH:MM, leave at or after')
        q.add_argument('--tz', help='zone for input and output times (default: home zone)')
        q.add_argument('-n', type=int, default=5 if name == 'plan' else 10)
    sp.choices['plan'].add_argument('--arrive-by', help='HH:MM, arrive by')
    sp.add_parser('selftest')
    a = ap.parse_args()
    {'home': cmd_home, 'find': cmd_find, 'plan': cmd_plan, 'next': cmd_next, 'selftest': lambda a: selftest()}[a.cmd](a)


if __name__ == '__main__':
    main()
