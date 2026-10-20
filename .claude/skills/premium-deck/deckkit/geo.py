# -*- coding: utf-8 -*-
"""Карта страны по субъектам — из открытых данных Natural Earth (public domain).

Проекция — равновеликая коническая Альберса (для России: центральный
меридиан 100° в. д., стандартные параллели 52° и 64°), как в атласах.
Долготы западнее 0° (Чукотка за 180-м меридианом) переносятся на +360°,
чтобы страна не разрывалась. Результат — контуры каждого субъекта
в долях ширины карты, y вниз; кэшируется в pickle рядом с материалами.
"""
import json, math, os, pickle
from .vector import simplify


def albers(lon, lat, lon0=100.0, lat1=52.0, lat2=64.0, lat0=60.0):
    r = math.radians
    n = (math.sin(r(lat1)) + math.sin(r(lat2))) / 2
    C = math.cos(r(lat1)) ** 2 + 2 * n * math.sin(r(lat1))
    rho = lambda ph: math.sqrt(max(C - 2 * n * math.sin(r(ph)), 0)) / n
    if lon < 0:
        lon += 360
    th = n * r(lon - lon0)
    p = rho(lat)
    return p * math.sin(th), rho(lat0) - p * math.cos(th)


def build(geojson, out, adm0='RUS', tol=0.0006):
    d = json.load(open(geojson, encoding='utf-8'))
    regions = {}
    for f in d['features']:
        pr = f['properties']
        if pr.get('adm0_a3') != adm0 or not pr.get('name_ru'):
            continue
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        rings = []
        for poly in polys:
            for ring in poly:                     # внешний контур и дыры
                rings.append([albers(lon, lat) for lon, lat in ring])
        regions.setdefault(pr['name_ru'], []).extend(rings)
    xs = [p[0] for rs in regions.values() for r in rs for p in r]
    ys = [p[1] for rs in regions.values() for r in rs for p in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w = x1 - x0
    norm = {}
    for name, rs in regions.items():
        out_r = []
        for r in rs:
            pts = simplify([((x - x0) / w, (y1 - y) / w) for x, y in r], tol)
            if len(pts) >= 3:
                out_r.append(pts)
        norm[name] = out_r
    data = dict(regions=norm, aspect=(y1 - y0) / w, source='Natural Earth 10m admin-1 (public domain)')
    pickle.dump(data, open(out, 'wb'))
    return data


def load(path):
    return pickle.load(open(path, 'rb'))
