# -*- coding: utf-8 -*-
"""Линейные иконки фактов — вектор, один стиль: контур 0,9 pt, квадрат 12 мм.

Рисуются примитивами модели (линии, ломаные, точки), поэтому в PDF это
кривые, а в PPTX — редактируемые фигуры. Новых слов иконки не добавляют.
"""
import math
from .model import Line, Poly, Dot

W_ = 0.9   # pt


def _arc(cx, cy, r, a0, a1, n=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _sag(x0, y0, x1, y1, s, n=20):
    return [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + 4 * s * t * (1 - t)) for t in (i / n for i in range(n + 1))]


def wires(x, y, s, c):
    """Пролёт ВЛ: две опоры и провисающие провода."""
    k = s / 12
    out = [Line(x + 1.5 * k, y + 2 * k, x + 1.5 * k, y + 11 * k, c, W_),
           Line(x + 10.5 * k, y + 2 * k, x + 10.5 * k, y + 11 * k, c, W_),
           Line(x + 0.5 * k, y + 3 * k, x + 2.5 * k, y + 3 * k, c, W_),
           Line(x + 9.5 * k, y + 3 * k, x + 11.5 * k, y + 3 * k, c, W_)]
    for dy, sg in ((3, 2.2), (5.2, 2.0)):
        out.append(Poly(_sag(x + 1.5 * k, y + dy * k, x + 10.5 * k, y + dy * k, sg * k), stroke=c, width=W_))
    return out


def tower(x, y, s, c):
    """Решётчатая опора ЛЭП."""
    k = s / 12
    P = lambda a, b: (x + a * k, y + b * k)
    out = [Poly([P(3, 12), P(6, 0.5), P(9, 12)], stroke=c, width=W_),
           Line(*P(1, 3.2), *P(11, 3.2), c, W_), Line(*P(2, 6), *P(10, 6), c, W_),
           Poly([P(4.3, 6), P(7.6, 9.2), P(3.6, 9.2), P(8.3, 12)], stroke=c, width=W_),
           Poly([P(5.2, 3.2), P(6.9, 6), P(5.0, 6)], stroke=c, width=W_)]
    return out


def substation(x, y, s, c):
    """Трансформатор: корпус, изоляторы, молния."""
    k = s / 12
    P = lambda a, b: (x + a * k, y + b * k)
    out = [Poly([P(1, 4), P(11, 4), P(11, 11.5), P(1, 11.5), P(1, 4)], stroke=c, width=W_),
           Line(*P(3.5, 4), *P(3.5, 1), c, W_), Line(*P(8.5, 4), *P(8.5, 1), c, W_),
           Line(*P(2.5, 1.6), *P(4.5, 1.6), c, W_), Line(*P(7.5, 1.6), *P(9.5, 1.6), c, W_),
           Poly([P(6.6, 5.5), P(4.8, 8.2), P(6.6, 8.2), P(5.4, 10.6)], stroke=c, width=W_)]
    return out


def plug(x, y, s, c):
    """Вилка с кабелем — подключение к сети."""
    k = s / 12
    P = lambda a, b: (x + a * k, y + b * k)
    out = [Line(*P(4.5, 0.8), *P(4.5, 3.6), c, W_), Line(*P(7.5, 0.8), *P(7.5, 3.6), c, W_),
           Poly([P(2.5, 3.6), P(9.5, 3.6), P(9.5, 6.2)] + _arc(x + 6 * k, y + 6.2 * k, 3.5 * k, 0, 180, 12)[1:] +
                [P(2.5, 3.6)], stroke=c, width=W_),
           Poly([P(6, 9.7), P(6, 11.2), P(10.5, 11.2)], stroke=c, width=W_)]
    return out


def drilling(x, y, s, c):
    """ГНБ: линия земли и дуга скважины под ней."""
    k = s / 12
    P = lambda a, b: (x + a * k, y + b * k)
    arc = _arc(x + 6 * k, y + 2.6 * k, 5 * k, 175, 5, 24)
    arc = [(px, y + 2.6 * k + (py - (y + 2.6 * k)) * -1.4) for px, py in arc]
    out = [Line(*P(0.3, 4), *P(11.7, 4), c, W_), Poly(arc, stroke=c, width=W_),
           Dot(arc[-1][0], arc[-1][1], 0.9 * k, c), Dot(arc[0][0], arc[0][1], 0.9 * k, c)]
    return out


def area(x, y, s, c):
    """Здание и отметка площади."""
    k = s / 12
    P = lambda a, b: (x + a * k, y + b * k)
    out = [Poly([P(1.5, 11.5), P(1.5, 4.5), P(6, 1), P(10.5, 4.5), P(10.5, 11.5), P(1.5, 11.5)], stroke=c, width=W_),
           Poly([P(4, 11.5), P(4, 7), P(8, 7), P(8, 11.5)], stroke=c, width=W_),
           Line(*P(0, 12.6), *P(12, 12.6), c, 0.5)]
    return out


ICONS = dict(wires=wires, tower=tower, substation=substation, plug=plug, drilling=drilling, area=area)


def _bbox(els):
    xs, ys = [], []
    for e in els:
        if isinstance(e, Line):
            xs += [e.x0, e.x1]; ys += [e.y0, e.y1]
        elif isinstance(e, Poly):
            xs += [p[0] for p in e.pts]; ys += [p[1] for p in e.pts]
        elif isinstance(e, Dot):
            xs += [e.cx - e.r, e.cx + e.r]; ys += [e.cy - e.r, e.cy + e.r]
    return min(xs), min(ys), max(xs), max(ys)


def draw(name, x, y, s, color):
    return ICONS[name](x, y, s, color)


def centered(name, cx, cy, s, color):
    """Иконка, у которой центр нарисованного (а не квадрата) — в (cx, cy)."""
    els = ICONS[name](0, 0, s, color)
    x0, y0, x1, y1 = _bbox(els)
    dx, dy = cx - (x0 + x1) / 2, cy - (y0 + y1) / 2
    for e in els:
        if isinstance(e, Line):
            e.x0 += dx; e.x1 += dx; e.y0 += dy; e.y1 += dy
        elif isinstance(e, Poly):
            e.pts = [(px + dx, py + dy) for px, py in e.pts]
        elif isinstance(e, Dot):
            e.cx += dx; e.cy += dy
    return els
