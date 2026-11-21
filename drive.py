#!/usr/bin/env python3
"""Driving distance, time and fuel anywhere roads connect, from the free public Valhalla router (FOSSGIS, OpenStreetMap), stdlib only.

Fuel cost is printed only when a real fuel price is given (--fuel-price): ask the traveller or look up today's local
price and say where it came from. Never guess a price."""
import argparse, json, os, sys, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transit  # noqa: E402  same folder: shared place lookup (Transitous geocoder, biased to the home region)

ROUTER = 'https://valhalla1.openstreetmap.de/route?json='  # closer to real drive times than the OSRM demo
LONG_ROUTER = 'https://router.project-osrm.org/route/v1/driving/'  # no distance cap, but its times run 10-25% long
KM_PER_MILE = 1.609344


def route(points):
    """points: ['lat,lon', ...] -> (metres, seconds, [(metres, seconds) per leg])."""
    locs = [{'lat': float(p.split(',')[0]), 'lon': float(p.split(',')[1])} for p in points]
    q = urllib.parse.quote(json.dumps({'locations': locs, 'costing': 'auto', 'directions_type': 'none'}))
    req = urllib.request.Request(ROUTER + q, headers={'User-Agent': transit.UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        d = json.loads(e.read() or b'{}')  # the router explains failures (no route) in the body
    except urllib.error.URLError as e:
        sys.exit(f'Cannot reach the routing server ({e.reason}).')
    if 'trip' in d:
        legs = [(l['summary']['length'] * 1000, l['summary']['time']) for l in d['trip']['legs']]
        return sum(m for m, _ in legs), sum(s for _, s in legs), legs, ''
    if 'max distance' not in str(d.get('error')):
        sys.exit(f"No driving route: {d.get('error', d)}. Places separated by sea need a ferry or flight leg.")
    coords = ';'.join(f"{p.split(',')[1]},{p.split(',')[0]}" for p in points)  # OSRM wants lon,lat
    try:
        with urllib.request.urlopen(urllib.request.Request(LONG_ROUTER + coords + '?overview=false', headers={'User-Agent': transit.UA}), timeout=60) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        d = json.loads(e.read() or b'{}')
    if d.get('code') != 'Ok':
        sys.exit(f"No driving route: {d.get('message', d.get('code'))}. Places separated by sea need a ferry or flight leg.")
    r = d['routes'][0]
    return r['distance'], r['duration'], [(l['distance'], l['duration']) for l in r['legs']], ' (long-distance router: times run 10-25% long)'


def hm(sec):
    m = round(sec / 60)
    return f'{m // 60}h{m % 60:02d}m'


def fuel(km, a):
    """(amount, unit, cost or None). Consumption is L/100 km, or mpg with --imperial."""
    if a.imperial:
        amount, unit = km / KM_PER_MILE / a.consumption, 'US gal'
    else:
        amount, unit = km * a.consumption / 100, 'L'
    return amount, unit, amount * a.fuel_price if a.fuel_price is not None else None


def selftest():
    class A: imperial, consumption, fuel_price = False, 8.5, 1.5
    assert fuel(400, A) == (34.0, 'L', 51.0)
    A.imperial, A.consumption, A.fuel_price = True, 30, None
    amount, unit, cost = fuel(KM_PER_MILE * 300, A)
    assert round(amount, 6) == 10 and unit == 'US gal' and cost is None, 'no price, no cost'
    assert hm(3720) == '1h02m'
    print('selftest ok')


def main():
    if sys.argv[1:] == ['selftest']:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('origin'); ap.add_argument('dest')
    ap.add_argument('--via', action='append', default=[], help='stop on the way (repeatable)')
    ap.add_argument('--consumption', type=float, help='L/100 km (or mpg with --imperial); ask the traveller what they drive')
    ap.add_argument('--fuel-price', type=float, help='price per litre (per US gallon with --imperial), from the traveller or a cited source')
    ap.add_argument('--currency', help='label for the fuel price, default from the home region')
    ap.add_argument('--imperial', action='store_true', help='miles, mpg and US gallons')
    ap.add_argument('--near', help='bias name lookups toward this place')
    a = ap.parse_args()
    if a.near:
        transit.NEAR = transit.place(a.near)[2]
    stops = [a.origin] + a.via + [a.dest]
    found = [transit.place(s) for s in stops]
    for s, (_, name, ll) in zip(stops, found):
        print(f'{name}  [{ll}]')
    metres, secs, legs, note = route([ll for _, _, ll in found])
    km = metres / 1000
    dist = lambda k: f'{k / KM_PER_MILE:,.0f} mi' if a.imperial else f'{k:,.0f} km'
    if len(legs) > 1:
        for i, (m, s) in enumerate(legs):
            print(f'  leg {i + 1}: {dist(m / 1000)}, {hm(s)}')
    print(f'Drive: {dist(km)}, {hm(secs)} at typical road speeds, before traffic, stops and border waits{note}')
    if a.consumption:
        amount, unit, cost = fuel(km, a)
        cur = (a.currency or (transit.home() or {}).get('currency') or '').upper()
        print(f'Fuel: {amount:,.1f} {unit}' + (f' = {cur} {cost:,.2f}'.replace('  ', ' ') if cost is not None else
                                               '  (add --fuel-price for the cost)'))


if __name__ == '__main__':
    main()
