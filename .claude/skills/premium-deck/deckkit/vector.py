# -*- coding: utf-8 -*-
"""Векторные знаки (логотипы) из SVG, который пишет potrace.

Растровый логотип клиента сначала переводится в вектор (potrace по альфа-
каналу или по маске цвета), дальше он — обычная фигура: в PDF это кривые
без разрешения, в PPTX — редактируемая фигура, цвет задаёт дизайн-система.
"""
import re
from functools import lru_cache

_num = re.compile(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?')


def _bez(p0, p1, p2, p3, n=10):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def _parse_path(d):
    toks = re.findall(r'[MmLlCcZz]|' + _num.pattern, d)
    contours, cur, pos, start, cmd, i = [], [], (0.0, 0.0), (0.0, 0.0), None, 0
    while i < len(toks):
        t = toks[i]
        if t in 'MmLlCcZz':
            cmd = t
            i += 1
            if cmd in 'Zz':
                if cur:
                    contours.append(cur)
                cur, pos = [], start
            continue
        if cmd in 'Mm':
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
            pos = (pos[0] + x, pos[1] + y) if cmd == 'm' else (x, y)
            if cur:
                contours.append(cur)
            cur, start = [pos], pos
            cmd = 'l' if cmd == 'm' else 'L'
        elif cmd in 'Ll':
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
            pos = (pos[0] + x, pos[1] + y) if cmd == 'l' else (x, y)
            cur.append(pos)
        elif cmd in 'Cc':
            v = [float(toks[i + k]) for k in range(6)]; i += 6
            if cmd == 'c':
                p1 = (pos[0] + v[0], pos[1] + v[1]); p2 = (pos[0] + v[2], pos[1] + v[3])
                p3 = (pos[0] + v[4], pos[1] + v[5])
            else:
                p1, p2, p3 = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
            cur.extend(_bez(pos, p1, p2, p3))
            pos = p3
        else:
            i += 1
    if cur:
        contours.append(cur)
    return contours


def simplify(pts, tol):
    """Рамер–Дуглас–Пекер: убираем точки, отклонение которых меньше tol."""
    import numpy as np
    a = np.asarray(pts, dtype=float)
    if len(a) < 4:
        return [tuple(p) for p in a]
    keep = np.zeros(len(a), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(a) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        p, q = a[i], a[j]
        d = q - p
        n = np.hypot(*d)
        seg = a[i + 1:j]
        if n < 1e-12:
            dist = np.hypot(*(seg - p).T)
        else:
            dist = np.abs(d[0] * (seg[:, 1] - p[1]) - d[1] * (seg[:, 0] - p[0])) / n
        k = int(dist.argmax())
        if dist[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack += [(i, m), (m, j)]
    return [tuple(p) for p in a[keep]]


@lru_cache(maxsize=16)
def load(path):
    """Контуры знака в долях ширины: x 0..1, y вниз; и пропорция h/w."""
    s = open(path, encoding='utf-8').read()
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', s).group(1).split()]
    W, H = vb[2], vb[3]
    tr = re.search(r'translate\(([-\d.]+),([-\d.]+)\)\s*scale\(([-\d.]+),([-\d.]+)\)', s)
    tx, ty, sx, sy = (float(v) for v in tr.groups()) if tr else (0, 0, 1, 1)
    out = []
    for d in re.findall(r'<path[^>]*\sd="([^"]+)"', s, re.S):
        for c in _parse_path(d):
            pts = simplify([((tx + sx * x) / W, (ty + sy * y) / W) for x, y in c], 2.5e-4)
            if len(pts) > 2:
                out.append(tuple(pts))
    return tuple(out), H / W


def place(path, x, y, w, color, role='logo'):
    """Знак шириной w мм с левым верхним углом в (x, y)."""
    from .model import Shape
    cs, ar = load(path)
    return Shape([[(x + px * w, y + py * w) for px, py in c] for c in cs], color, role), w * ar


def from_cmds(paths, w, h):
    """Пути potrace в виде [(cmd, [числа…]), …] (y вверх, пиксели растра)
    -> контуры в долях ширины, y вниз. Так хранится, например, карта."""
    out = []
    for path in paths:
        cur, pos, start = [], (0.0, 0.0), (0.0, 0.0)
        for cmd, args in path:
            if cmd in 'Mm':
                if cur:
                    out.append(cur)
                pos = (args[0], args[1]) if cmd == 'M' else (pos[0] + args[0], pos[1] + args[1])
                cur, start = [pos], pos
            elif cmd in 'Ll':
                for i in range(0, len(args), 2):
                    pos = (args[i], args[i + 1]) if cmd == 'L' else (pos[0] + args[i], pos[1] + args[i + 1])
                    cur.append(pos)
            elif cmd in 'Cc':
                for i in range(0, len(args), 6):
                    v = args[i:i + 6]
                    if cmd == 'c':
                        p1 = (pos[0] + v[0], pos[1] + v[1]); p2 = (pos[0] + v[2], pos[1] + v[3])
                        p3 = (pos[0] + v[4], pos[1] + v[5])
                    else:
                        p1, p2, p3 = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
                    cur.extend(_bez(pos, p1, p2, p3, 6))
                    pos = p3
            elif cmd in 'Zz':
                if cur:
                    out.append(cur)
                cur, pos = [], start
        if cur:
            out.append(cur)
    return [simplify([(x / w, (h - y) / w) for x, y in c], 2.5e-4) for c in out if len(c) > 2]


def fit(contours, x, y, w, h, color, role='map', mode='contain', ref=None):
    """Вписать контуры в прямоугольник по их собственному габариту (или ref)."""
    from .model import Shape
    xs = [p[0] for c in (ref or contours) for p in c]
    ys = [p[1] for c in (ref or contours) for p in c]
    bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
    k = w / (bx1 - bx0) if mode == 'width' else min(w / (bx1 - bx0), h / (by1 - by0))
    ox = x + (w - (bx1 - bx0) * k) / 2 - bx0 * k
    oy = y + (h - (by1 - by0) * k) / 2 - by0 * k
    return Shape([[(ox + px * k, oy + py * k) for px, py in c] for c in contours], color, role)
