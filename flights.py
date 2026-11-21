#!/usr/bin/env python3
"""Live flight prices worldwide from Google Flights' public web data (no key), stdlib only.

Searches one-way and round-trip fares, finds the cheapest days to leave for a stay of N days, and prices a multi-leg
trip leg by leg. It never books: every result carries a Google Flights link where the traveller checks and buys.
Request format ported from fli (https://github.com/punitarani/fli, MIT); see NOTICE."""
import argparse, json, os, sys, time, urllib.parse, urllib.request
from datetime import date, timedelta

URL = 'https://www.google.com/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/GetShoppingResults'
HOME = os.path.join(os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'), 'worldwide-transit', 'home.json')
CABIN = {'economy': 1, 'premium': 2, 'business': 3, 'first': 4}
STOPS = {'any': 0, '0': 1, '1': 2, '2': 3}  # Google's codes: nonstop, at most 1 stop, at most 2 stops
PAUSE = 2.0  # seconds between requests in loops; ponytail: fixed pause, enough for one person's searches


def home_currency():
    try:
        with open(HOME) as f:
            return json.load(f).get('currency') or 'USD'
    except FileNotFoundError:
        return 'USD'


def airports(s):
    """'NRT,HND' -> Google's airport list. Several airports per end are searched together."""
    codes = [c.strip().upper() for c in s.split(',') if c.strip()]
    if not codes or any(len(c) != 3 or not c.isalpha() for c in codes):
        sys.exit(f'"{s}" is not a list of 3-letter airport codes, e.g. YLW or NRT,HND')
    return [[[c, 0] for c in codes]]


def payload(legs, trip, adults, cabin, stops):
    """legs: [(from, to, 'YYYY-MM-DD')]. trip: 1 round trip, 2 one-way."""
    segs = [[airports(a), airports(b), None, stops, None, None, d, None, None, None, None, None, None, None,
             1 if trip == 1 and i else 3] for i, (a, b, d) in enumerate(legs)]
    body = [[], [None, None, trip, None, [], cabin, [adults, 0, 0, 0], None, None, None, None, None, None, segs]
            + [None] * 3 + [1] + [None] * 10 + [0], 2, 1, 0, 1]  # sort cheapest first, all results
    return 'f.req=' + urllib.parse.quote(json.dumps([None, json.dumps(body, separators=(',', ':'))], separators=(',', ':')))


def inner(text):
    """The JSON payload inside Google's ')]}\\'' wrapped 'wrb.fr' envelope."""
    raw = text.lstrip()[4:].lstrip() if text.lstrip().startswith(")]}'") else text
    if raw[:1].isdigit():  # length-prefixed chunk
        raw = raw.split('\n', 1)[1]
    for row in json.loads(raw.split('\n')[0] if raw.startswith('[[') else raw):
        if isinstance(row, list) and len(row) > 2 and row[0] == 'wrb.fr' and isinstance(row[2], str):
            return json.loads(row[2])
    return None


def parse(data):
    out = []
    for i in (2, 3):
        block = data[i] if len(data) > i and isinstance(data[i], list) else None
        for row in (block[0] if block else []) or []:
            try:
                head, d = row[1][0], row[0]
                if not head:
                    continue  # no shopping price shown for this row
                legs = [{'airline': (l[22] or [None])[0], 'flight': f"{(l[22] or [''])[0]}{(l[22] or ['', ''])[1]}",
                         'from': l[3], 'to': l[6], 'dep': (l[20], l[8]), 'arr': (l[21], l[10])} for l in d[2]]
                out.append({'price': float(head[-1]), 'minutes': d[9], 'legs': legs})
            except (IndexError, TypeError, ValueError):
                continue  # adverts and half-filled rows
    return sorted(out, key=lambda r: r['price'])


def fetch(legs, trip, a):
    req = urllib.request.Request(f'{URL}?curr={a.currency}&hl=en', data=payload(legs, trip, a.adults, CABIN[a.cabin], STOPS[a.stops]).encode(),
                                 headers={'content-type': 'application/x-www-form-urlencoded;charset=UTF-8', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        sys.exit(f'Google Flights returned HTTP {e.code}. Wait a minute and try again; if it persists the format changed.')
    except urllib.error.URLError as e:
        sys.exit(f'Cannot reach google.com ({e.reason}).')
    if 'ErrorResponse' in text[:3000]:
        return None  # throttled, not "no flights"
    data = inner(text)
    return parse(data) if data else []


def search(legs, trip, a, tries=4):
    """Google throttles bursts with an error page (code 13); back off 2, 4, 8 s and ask again.
    Returns [] for a real "no flights" answer, None if Google kept refusing."""
    for i in range(tries):
        rows = fetch(legs, trip, a)
        if rows is not None or i == tries - 1:
            return rows
        time.sleep(2 ** (i + 1))


def stamp(dt):
    (y, mo, d), (h, mi) = dt[0], (dt[1] + [0, 0])[:2]
    return f"{date(y, mo, d):%a %b %d} {(h or 0) % 12 or 12}:{mi or 0:02d} {'AM' if (h or 0) < 12 else 'PM'}"


def link(legs, ret=None):
    q = f'Flights from {legs[0][0]} to {legs[0][1]} on {legs[0][2]}' + (f' through {ret}' if ret else '')
    return 'https://www.google.com/travel/flights?q=' + urllib.parse.quote(q)


def show(rows, n, cur, adults):
    for r in rows[:n]:
        stops = len(r['legs']) - 1
        print(f"\n{cur} {r['price']:,.0f}{' total for ' + str(adults) if adults > 1 else ''}  {r['minutes'] // 60}h{r['minutes'] % 60:02d}m  "
              f"{'nonstop' if not stops else str(stops) + ' stop' + ('s' if stops > 1 else '')}")
        for l in r['legs']:
            print(f"    {l['flight']:8} {l['from']} {stamp(l['dep'])} -> {l['to']} {stamp(l['arr'])}")
    if rows is None:
        print('Google Flights is refusing requests right now (rate limit). Wait a few minutes and ask again; this is not "no flights".')
    elif not rows:
        print('No priced flights found. Try nearby airports (e.g. YVR,YLW), another date, or --stops any.')


def days(a, b):
    d0, d1 = date.fromisoformat(a), date.fromisoformat(b)
    if d1 < d0 or (d1 - d0).days > 30:
        sys.exit('--from and --to must be in order and at most 31 days apart (one request per day).')
    return [d0 + timedelta(i) for i in range((d1 - d0).days + 1)]


def cmd_search(a):
    legs = [(a.origin, a.dest, a.date)] + ([(a.dest, a.origin, a.ret)] if a.ret else [])
    print(f"{'Round trip' if a.ret else 'One way'} {a.origin} -> {a.dest}, {a.date}{' to ' + a.ret if a.ret else ''}, "
          f"{a.adults} adult(s), {a.cabin}, prices in {a.currency}" + (' (outbound shown; price is the round-trip total)' if a.ret else ''))
    show(search(legs, 1 if a.ret else 2, a), a.n, a.currency, a.adults)
    print(f'\nCheck and book: {link(legs, a.ret)}')


def cmd_dates(a):
    print(f"Cheapest {'round trips of ' + str(a.stay) + ' days' if a.stay else 'one-way fares'} {a.origin} -> {a.dest}, "
          f"leaving {a.start} to {a.end}, prices in {a.currency}")
    found = []
    for i, d in enumerate(days(a.start, a.end)):
        if i:
            time.sleep(PAUSE)
        back = str(d + timedelta(a.stay)) if a.stay else None
        legs = [(a.origin, a.dest, str(d))] + ([(a.dest, a.origin, back)] if back else [])
        rows = search(legs, 1 if back else 2, a)
        if rows:
            found.append((rows[0]['price'], d, back, rows[0]))
        print(f"  {d:%a %b %d}{' -> ' + date.fromisoformat(back).strftime('%a %b %d') if back else ''}  "
              f"{a.currency + ' ' + format(rows[0]['price'], ',.0f') if rows else 'no price shown' if rows == [] else 'not checked (rate limit)'}", flush=True)
    for price, d, back, r in sorted(found, key=lambda x: x[0])[:3]:
        print(f"\nBest: leave {d:%a %b %d}{', back ' + date.fromisoformat(back).strftime('%a %b %d') if back else ''}  "
              f"{a.currency} {price:,.0f}  {link([(a.origin, a.dest, str(d))], back)}")


def cmd_multi(a):
    legs = []
    for spec in a.legs:
        try:
            route, d = spec.split(':')
            src, dst = route.split('-')
            date.fromisoformat(d)
        except ValueError:
            sys.exit(f'"{spec}" should look like YLW-NRT:2027-01-12')
        legs.append((src, dst, d))
    total, missing = 0.0, []
    for i, (src, dst, d) in enumerate(legs):
        if i:
            time.sleep(PAUSE)
        rows = search([(src, dst, d)], 2, a)
        print(f"\nLeg {i + 1}: {src} -> {dst} on {d}")
        show(rows, 1, a.currency, a.adults)
        print(f'    book: {link([(src, dst, d)])}')
        if rows:
            total += rows[0]['price']
        else:
            missing.append(f'{src}-{dst}')
    print(f"\nFlights total: {a.currency} {total:,.0f} for {len(legs) - len(missing)} of {len(legs)} legs, cheapest fare on each, booked separately."
          + (f" No fare found for {', '.join(missing)}." if missing else ''))


def selftest():
    p = urllib.parse.unquote(payload([('YLW', 'NRT,HND', '2027-01-12'), ('NRT,HND', 'YLW', '2027-02-11')], 1, 2, 1, 0)[6:])
    body = json.loads(json.loads(p)[1])
    seg = body[1][13]
    assert body[1][2] == 1 and body[1][6] == [2, 0, 0, 0] and body[2] == 2
    assert seg[0][0] == [[['YLW', 0]]] and seg[0][1] == [[['NRT', 0], ['HND', 0]]] and seg[0][6] == '2027-01-12'
    assert seg[0][14] == 3 and seg[1][14] == 1, 'outbound 3, return 1'
    row = [[None, None, [[None, None, None, 'YLW', None, None, 'YYC', None, [10, 45], None, [12, 0], 75, None, None, None, None, None, None,
                          None, None, [2027, 1, 12], [2027, 1, 12], ['WS', '123']]], None, None, None, None, None, None, 825], [[None, 648], 'tok']]
    wire = ")]}'\n\n" + json.dumps([['wrb.fr', None, json.dumps([None, None, [[row]], None])]])
    r = parse(inner(wire))
    assert r[0]['price'] == 648.0 and r[0]['legs'][0]['flight'] == 'WS123' and r[0]['minutes'] == 825
    assert stamp(([2027, 1, 12], [14, 5])) == 'Tue Jan 12 2:05 PM' and stamp(([2027, 1, 12], [0])) == 'Tue Jan 12 12:00 AM'
    assert len(days('2027-01-01', '2027-01-31')) == 31
    class A: currency, adults, cabin, stops = 'CAD', 1, 'economy', 'any'
    throttled = ")]}'\n\n" + json.dumps([['wrb.fr', None, None, None, None, [13, None, [['type.googleapis.com/travel.frontend.flights.ErrorResponse']]]]])
    real_urlopen = urllib.request.urlopen
    class Resp:
        def __init__(self, t): self.t = t
        def __enter__(self): return self
        def __exit__(self, *e): pass
        def read(self): return self.t.encode()
    try:
        urllib.request.urlopen = lambda *x, **k: Resp(throttled)
        assert fetch([('YLW', 'NRT', '2027-01-12')], 2, A) is None, 'throttle page is not "no flights"'
        urllib.request.urlopen = lambda *x, **k: Resp(wire)
        assert fetch([('YLW', 'NRT', '2027-01-12')], 2, A)[0]['price'] == 648.0
    finally:
        urllib.request.urlopen = real_urlopen
    print('selftest ok')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('search', help='live fares for one date (and a return date)')
    p.add_argument('origin'); p.add_argument('dest'); p.add_argument('date'); p.add_argument('--return', dest='ret')
    p = sp.add_parser('dates', help='cheapest day to leave in a window, for a stay of N days')
    p.add_argument('origin'); p.add_argument('dest')
    p.add_argument('--from', dest='start', required=True); p.add_argument('--to', dest='end', required=True)
    p.add_argument('--stay', type=int, help='days away (round trip); omit for one-way')
    p = sp.add_parser('multi', help='price a multi-leg trip, leg by leg')
    p.add_argument('legs', nargs='+', help='YLW-NRT:2027-01-12 NRT-BKK:2027-01-26 ...')
    for q in sp.choices.values():
        q.add_argument('--adults', type=int, default=1); q.add_argument('--cabin', choices=CABIN, default='economy')
        q.add_argument('--stops', choices=STOPS, default='any', help='max stops: any, 0, 1, 2')
        q.add_argument('--currency', default=None, help='ISO code, default from the home region (else USD)')
        q.add_argument('-n', type=int, default=5)
    sp.add_parser('selftest')
    a = ap.parse_args()
    if a.cmd == 'selftest':
        return selftest()
    a.currency = (a.currency or home_currency()).upper()
    {'search': cmd_search, 'dates': cmd_dates, 'multi': cmd_multi}[a.cmd](a)


if __name__ == '__main__':
    main()
