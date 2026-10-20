# -*- coding: utf-8 -*-
"""Каталог в смешанной системе «Ночь / Чертёж / Поле».

Выбор клиента по листу направлений: обложка — «Ночь»; цифры и список —
«Ночь» и «Чертёж»; направления работ — «Чертёж» и «Поле». Из этого
собрана одна система с тремя режимами разворота, которые чередуются:

  night — глубокий ночной фиолетовый, широкий Unbounded для крупных
          моментов (обложки, цифры, карта), строки на волосяных линейках;
  light — светлый лист с рамкой и линейкой чертёжного формата, тёмно-
          фиолетовый текст, снимки в окнах внутри рамки;
  field — фиолетовое поле с крупным заголовком, рядом — снимки в
          натуральном цвете, между ними оранжевая черта.

Общее для всех режимов (это и держит гармонию): оранжевая метка над каждым
заголовком, Onest ExtraBold в заголовках полос, Onest в тексте, логотип
вверху снаружи правой полосы, номер полосы внизу снаружи. Тексты, порядок
полос и снимки — из оригинала без изменений.
"""
import math
from .model import Rect, Line, Image, Text, Slide, Shape, PT
from .tokens import mix
from . import vector, fonts
from .catalog2 import (GROUNDS, ORANGE, V_DEEP, V_BRIGHT, WHITE, T, _logo, _ground, _a_frame,
                       b_cover, b_stats, b_list)
from .pages import Pg, _pf

H = 297.0
MARK = (14.0, 1.6)                         # оранжевая метка над заголовком


def mark(sl, x, y):
    sl.add(Rect(x, y, MARK[0], MARK[1], ORANGE, role='marker'))


def head(sl, s, x, y, w, size, color, font='onest-black', h=70, lead=1.0, track=-0.025):
    mark(sl, x, y)
    return T(sl, s, x - 0.8, y + 7, w + 2, h, font, size, color, lead, track, size_min=size * 0.55,
             role='title')


def rows(sl, items, x, y, w, g, size=10.5, mk=True, gap=3.8, font='onest', lead=1.32):
    """Пункты на волосяных линейках; маркер — оранжевый квадрат."""
    for it in items:
        sl.add(Line(x, y, x + w, y, g.line, 0.5))
        if mk:
            sl.add(Rect(x, y + gap + size * PT * 0.32, 1.8, 1.8, ORANGE, role='marker'))
        t = T(sl, it, x + (5.5 if mk else 0), y + gap, w - (5.5 if mk else 0), 40, font, size, g.ink,
              lead, role='item')
        y = t.y + t.h + gap
    sl.add(Line(x, y, x + w, y, g.line, 0.5))
    return y


def folio(sl, pg, n, g, light):
    """Номер полосы внизу снаружи; если там снимок — на вкладке цвета фона."""
    if light:
        return                              # в «Чертеже» номер стоит в окне рамки
    x = pg.x1 - 20 if pg.side != 'L' else pg.x0
    al = 'r' if pg.side != 'L' else 'l'
    t = T(sl, f'{n:02d}', x, H - 12, 20, 6, 'onest-semi', 7.5, g.muted, 1.0, 0.06,
          align=al, role='folio', max_lines=1)
    x0, y0, x1, y1 = t.bbox()
    if any(isinstance(e, Image) and e.x <= x0 and e.x + e.w >= x1 and e.y <= y0 and e.y + e.h >= y1
           for e in sl.items):
        t.color = g.ink
        sl.items.insert(sl.items.index(t), Rect(x0 - 3, y0 - 2.4, x1 - x0 + 6, H - y0 + 2.4, g.bg,
                                                role='plate'))


def logo_r(sl, spec, pg, color, w=28, y=17):
    if pg.side != 'L':
        _logo(sl, spec, pg.x1 - w, y, w, color)


def caption_on(sl, g, pg, s, img):
    """Подпись по снимку — на вкладке цвета фона, от нижнего края кадра."""
    al = 'r' if pg.side == 'L' else 'l'
    t = T(sl, s, pg.x0, 0, pg.w, 6, 'onest-semi', 7.5, g.ink, 1.2, 0.02, align=al, role='caption',
          max_lines=1)
    bottom = img.y + img.h
    pb = 6.0 if bottom >= H - 0.01 else 2.4
    t.y = min(bottom, H) - pb - t.h
    x0, y0, x1, y1 = t.bbox()
    sl.items.insert(sl.items.index(t), Rect(x0 - 3, y0 - 2.4, x1 - x0 + 6, min(bottom, H) - y0 + 2.4,
                                            g.bg, role='plate'))


# ======================================================== night

def n_numbered(sl, c, pg, spec, n):
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, H, g)
    y = 26
    e = c.get('emblem')
    if e:
        sh = 24
        sl.add(Image(e['image_night'] if e.get('image_night') else e['image'], pg.x0, y,
                     sh * e.get('ar', 0.88), sh, role='emblem'))
        if e.get('wordmark'):
            shape, _ = vector.place(e['wordmark'], pg.x0 + sh * e.get('ar', 0.88) + 6,
                                    y + (sh - 0.377 * 58) / 2, 58, g.ink)
            sl.add(shape)
        y += sh + 22
    mark(sl, pg.x0, y)
    t = T(sl, c['lead'], pg.x0, y + 7, pg.w * 0.95, 60, 'onest-black', 19, g.ink, 1.12, -0.02,
          role='lead')
    y = t.y + t.h + 18
    T(sl, c.get('items_label', ''), pg.x0, y, pg.w, 8, 'onest-semi', 8, ORANGE, 1.2, 0.08, role='label',
      max_lines=1)
    y += 9
    lw = 34
    for it in c['items']:
        sl.add(Line(pg.x0, y, pg.x1, y, g.line, 0.5))
        T(sl, it['label'], pg.x0, y + 4.2, lw, 8, 'wide', 8.5, ORANGE, 1.2, 0.0, role='label', max_lines=1)
        b = T(sl, it['text'], pg.x0 + lw, y + 3.6, pg.w - lw, 40, 'onest', 9.5, g.ink, 1.38)
        y = b.y + b.h + 6
    sl.add(Line(pg.x0, y, pg.x1, y, g.line, 0.5))
    if c.get('url'):
        T(sl, c['url'], pg.x0, H - 24, pg.w, 8, 'onest-semi', 10, ORANGE, 1.0, 0.0, role='url', max_lines=1)
    folio(sl, pg, n, g, False)


def n_directions(sl, c, pg, spec, n):
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, H, g)
    logo_r(sl, spec, pg, ORANGE)
    mark(sl, pg.x0, 50)
    T(sl, c['title'], pg.x0, 57, pg.w, 60, 'wide-bold', 24, g.ink, 1.15, -0.015, role='title')
    items = c['items']
    y0 = 130
    step = (H - 30 - y0) / len(items)
    for i, it in enumerate(items):
        y = y0 + i * step
        sl.add(Line(pg.x0, y, pg.x1, y, g.line, 0.5))
        T(sl, it['num'], pg.x0 - 1, y + 7, 60, 40, 'wide', 44, ORANGE, 1.0, -0.03, role='num', max_lines=1)
        T(sl, it['text'], pg.x0 + pg.w * 0.42, y + 10, pg.w * 0.58, 30, 'onest-black', 15, g.ink, 1.2,
          -0.01, role='item')
    folio(sl, pg, n, g, False)


def n_service(sl, c, pg, spec, n):
    """Ночная полоса направления: заголовок на ночном фоне, снимок в вылет снизу."""
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, H, g)
    logo_r(sl, spec, pg, ORANGE)
    t = head(sl, c['title'], pg.x0, 44, pg.w, 27, g.ink)
    y = rows(sl, c.get('items', []), pg.x0, t.y + t.h + 14, pg.w * 0.8, g, size=10)
    ims = c.get('photos', [])
    if ims:
        p, f = _pf(ims[0])
        top = max(y + 16, H * c.get('photo_top', 0.48))
        img = Image(p, pg.X, top, pg.W, H - top, f)
        sl.add(img)
        if c.get('caption'):
            caption_on(sl, g, pg, c['caption'], img)
    folio(sl, pg, n, g, False)


def n_map(sl, c, pg, spec, n):
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, H, g)
    m = spec.get('_map')
    if m:
        country, regions = m
        dy = spec.get('map_offset_mm', 0.0)
        tr = lambda cs: [[(pg.X + x * pg.W, y * pg.W + dy) for x, y in cc] for cc in cs]
        sl.add(Shape(tr(country), (48, 41, 86), 'map'))
        sl.add(Shape(tr(regions), mix(g.bg, ORANGE, 0.85), 'map'))
    mark(sl, pg.x0, 30)
    T(sl, c['title'], pg.x0, 37, pg.w, 60, 'wide-bold', 30, g.ink, 1.12, -0.02, role='hero')
    folio(sl, pg, n, g, False)


def n_regions(sl, c, pg, spec, n):
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, H, g)
    logo_r(sl, spec, pg, ORANGE)
    items = c['items']
    half = math.ceil(len(items) / 2)
    cw = (pg.w - 8) / 2
    y0 = 66
    for ci, chunk in enumerate((items[:half], items[half:])):
        x = pg.x0 + ci * (cw + 8)
        rows(sl, chunk, x, y0, cw, g, size=10, gap=3.4)
    folio(sl, pg, n, g, False)


def n_back(sl, c, pg, spec):
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, H, g)
    sl.add(Image(c['image'], pg.X, 0, pg.W, H, tuple(c.get('focus', (0.5, 0.5)))))
    _logo(sl, spec, pg.x0, H - 18 - 0.67 * 34, 34, ORANGE)


# ======================================================== light «Чертёж»

def _light(sl, pg, n):
    g = GROUNDS['paper']
    _ground(sl, pg.X, pg.W, H, g)
    x0, y0, x1, y1 = _a_frame(sl, pg, n)
    return g, x0 + 10, x1 - 10, y0, y1, x0, x1


def l_service(sl, c, pg, spec, n):
    g, L, R, y0, y1, fx0, fx1 = _light(sl, pg, n)
    if pg.side != 'L':
        _logo(sl, spec, R - 26, y0 + 8, 26, V_DEEP)
    ims = c.get('photos', [])
    t = head(sl, c['title'], L, 34 if ims else 70, R - L, 30 if ims else 36, g.ink)
    y = t.y + t.h + 14
    if c.get('items'):
        y = rows(sl, c['items'], L, y, R - L, g, size=10.5) + 8
    for ptxt in c.get('paras', []):
        b = T(sl, ptxt, L, y, (R - L) * 0.9, 80, 'onest', 10, g.ink, 1.42)
        y = b.y + b.h + 5
    if ims:
        top = max(y + 12, H * c.get('photo_top', 0.45))
        bot = y1 - (14 if c.get('caption') else 6)
        n_im = len(ims)
        vertical = c.get('vertical', False)
        if vertical:
            hh = (bot - top - 4 * (n_im - 1)) / n_im
            for i, it in enumerate(ims):
                p, f = _pf(it)
                sl.add(Image(p, fx0 + 6, top + i * (hh + 4), fx1 - fx0 - 12, hh, f))
        else:
            ww = (fx1 - fx0 - 12 - 4 * (n_im - 1)) / n_im
            for i, it in enumerate(ims):
                p, f = _pf(it)
                sl.add(Image(p, fx0 + 6 + i * (ww + 4), top, ww, bot - top, f))
        if c.get('caption'):
            T(sl, c['caption'], fx0 + 6, bot + 3.2, fx1 - fx0 - 12, 6, 'onest-semi', 7.5, g.muted, 1.2, 0.02,
              align='r' if pg.side == 'L' else 'l', role='caption', max_lines=1)


def l_photos(sl, c, pg, spec, n):
    g, L, R, y0, y1, fx0, fx1 = _light(sl, pg, n)
    ims = c['photos']
    top, bot = y0 + 6, y1 - 12
    split = top + (bot - top) * c.get('split', 0.5)
    for i, it in enumerate(ims[:2]):
        p, f = _pf(it)
        ya, yb = (top, split - 2) if i == 0 else (split + 2, bot)
        sl.add(Image(p, fx0 + 6, ya, fx1 - fx0 - 12, yb - ya, f))
    if pg.side != 'L':
        _logo(sl, spec, fx1 - 18 - 22, bot + 1.6, 22, V_DEEP)    # левее окна с номером


def l_mission_chart(sl, c, pg, spec, n):
    g, L, R, y0, y1, fx0, fx1 = _light(sl, pg, n)
    y = 34
    for blk in c['blocks']:
        t = head(sl, blk['title'], L, y, R - L, 15, g.ink, h=20)
        y = t.y + t.h + 6
        for ptxt in blk['paras']:
            b = T(sl, ptxt, L + 30, y, R - L - 30, 60, 'onest', 9.5, g.ink, 1.42)
            y = b.y + b.h + 3.5
        y += 9
    ch = c['chart']
    t = head(sl, ch['title'], L, y + 2, R - L, 15, g.ink, h=24)
    top = t.y + t.h + 18
    base = y1 - 14
    data = ch['data']
    k = len(data)
    gap = 3.0
    bw = (R - L - gap * (k - 1)) / k
    vmax = max(d['value'] for d in data)
    rest = (214, 209, 224)
    for i, d in enumerate(data):
        hi = i == k - 1
        bh = (base - top - 14) * d['value'] / vmax
        bx = L + i * (bw + gap)
        sl.add(Rect(bx, base - bh, bw, bh, ORANGE if hi else rest, role='bar'))
        T(sl, d['display'], bx - 2, base - bh - 10.5, bw + 4, 8, 'onest-black', 10 if hi else 8.5, g.ink,
          1.0, -0.01, align='c', role='bar-value', max_lines=1)
        T(sl, d['unit'], bx - 2, base - bh - 4.8, bw + 4, 6, 'onest', 7, g.muted, 1.0, 0, align='c',
          role='bar-unit', max_lines=1)
        T(sl, d['label'], bx - 2, base + 3, bw + 4, 6, 'onest', 7.5, g.muted, 1.0, 0, align='c',
          role='axis', max_lines=1)
    sl.add(Line(L, base, R, base, g.line, 0.5))


def l_figures(sl, c, pg, spec, n):
    g, L, R, y0, y1, fx0, fx1 = _light(sl, pg, n)
    if pg.side != 'L':
        _logo(sl, spec, R - 26, y0 + 8, 26, V_DEEP)
    tot = c['totals']
    mark(sl, L, 40)
    v = T(sl, tot[0]['value'], L - 2, 46, (R - L) * 0.6, 60, 'onest-black', 96, g.ink, 0.95, -0.05,
          role='hero', max_lines=1)
    cap = T(sl, tot[0]['label'], L, v.y + v.h + 1, 60, 10, 'onest-semi', 10, g.ink, 1.2)
    rx = L + (R - L) * 0.56
    yy = 52
    for t_ in tot[1:]:
        vv = T(sl, t_['value'], rx, yy, R - rx, 20, 'onest-black', 34, g.ink, 1.0, -0.03, role='stat',
               max_lines=1)
        cc = T(sl, t_['label'], rx, vv.y + vv.h + 1.5, R - rx, 12, 'onest', 9, g.muted, 1.3)
        yy = cc.y + cc.h + 10
    y_tab = max(cap.y + cap.h, yy) + 18
    cols = c['columns']
    cw = (R - L - 8) / len(cols)
    for ci, rws in enumerate(cols):
        x = L + ci * (cw + 8)
        y = y_tab
        for r in rws:
            sl.add(Line(x, y, x + cw, y, g.line, 0.5))
            if r.get('num'):
                T(sl, r['num'], x, y + 3.6, 20, 10, 'onest-black', 16, g.ink, 1.0, -0.02, role='num',
                  max_lines=1)
            b = T(sl, r['label'], x + (17 if r.get('num') else 0), y + 4.9,
                  cw - (17 if r.get('num') else 0), 20, 'onest', 9, g.muted, 1.3)
            y = max(y + 12.5, b.y + b.h + 4)
        sl.add(Line(x, y, x + cw, y, g.line, 0.5))


def l_civil(sl, c, pg, spec, n):
    g, L, R, y0, y1, fx0, fx1 = _light(sl, pg, n)
    t = head(sl, c['title'], L, 34, R - L, 30, g.ink)
    y = t.y + t.h + 14
    for ptxt in c.get('paras', []):
        y = rows(sl, [ptxt], L, y, R - L, g, size=10.5) + 6
    top = max(y + 10, 118)
    bot = y1 - 6
    rws = c['rows']
    caps = sum(1 for r in rws if r.get('caption'))
    hgt = (bot - top - 4 * (len(rws) - 1) - 9 * caps) / len(rws)
    yy = top
    for r in rws:
        ims = r['photos']
        ww = (fx1 - fx0 - 12 - 4 * (len(ims) - 1)) / len(ims)
        for i, it in enumerate(ims):
            p, f = _pf(it)
            sl.add(Image(p, fx0 + 6 + i * (ww + 4), yy, ww, hgt, f))
        yy += hgt
        if r.get('caption'):
            T(sl, r['caption'], fx0 + 6, yy + 2.6, fx1 - fx0 - 12, 6, 'onest-semi', 7.5, g.muted, 1.2,
              0.02, align='r' if pg.side == 'L' else 'l', role='caption', max_lines=1)
            yy += 9
        yy += 4


def l_logos(sl, c, pg, spec, n):
    g, L, R, y0, y1, fx0, fx1 = _light(sl, pg, n)
    ims = c['logos']
    cols = 3
    rws = math.ceil(len(ims) / cols)
    gap = 4.0
    cw = (R - L - gap * (cols - 1)) / cols
    chh = cw * 208 / 327
    total = rws * chh + (rws - 1) * gap
    y = (H - total) / 2
    for i, p in enumerate(ims):
        x = L + (i % cols) * (cw + gap)
        yy = y + (i // cols) * (chh + gap)
        sl.add(Image(p, x, yy, cw, chh, (0.5, 0.5), role='card'))
        for a, b, cc, d in ((x, yy, x + cw, yy), (x + cw, yy, x + cw, yy + chh), (x, yy + chh, x + cw, yy + chh),
                            (x, yy, x, yy + chh)):
            sl.add(Line(a, b, cc, d, g.line, 0.4, role='card-frame'))


def l_credentials(sl, c, pg, spec, n):
    g, L, R, y0, y1, fx0, fx1 = _light(sl, pg, n)
    if pg.side != 'L':
        _logo(sl, spec, R - 26, y0 + 8, 26, V_DEEP)
    y = rows(sl, c['items'], L, 92, R - L, g, size=10.5, gap=4.0)
    yy = y1 - 16 - 7 * len(c['contacts'])
    mark(sl, L, yy - 8)
    for i, ct in enumerate(c['contacts']):
        T(sl, ct['label'], L, yy + i * 7 + 1, 20, 6, 'onest-semi', 7.5, g.muted, 1.0, 0.06, role='label',
          max_lines=1)
        T(sl, ct['value'], L + 18, yy + i * 7, R - L - 18, 6, 'onest-black', 11, g.ink, 1.0, 0.0,
          role='contact', max_lines=1)


# ======================================================== field «Поле»

def f_service(sl, c, pg, spec, n):
    g = GROUNDS['deep']
    _ground(sl, pg.X, pg.W, H, g)
    logo_r(sl, spec, pg, ORANGE)
    ims = c.get('photos', [])
    t = head(sl, c['title'], pg.x0, 40, pg.w, c.get('title_size', 40), g.ink, h=100, lead=0.98,
             track=-0.035)
    y = max(t.y + t.h + 22, 120 if ims else 104)
    for it in c.get('items', []):
        sl.add(Rect(pg.x0, y + 2.0, 8, 1.6, ORANGE, role='marker'))
        tt = T(sl, it, pg.x0 + 12, y, pg.w - 12, 40, 'onest', 10.5, g.ink, 1.38, role='item')
        y = tt.y + tt.h + 6
    for ptxt in c.get('paras', []):
        b = T(sl, ptxt, pg.x0 + 12, y, pg.w - 12, 80, 'onest', 10, g.ink, 1.42)
        y = b.y + b.h + 5
    if c.get('note'):
        T(sl, c['note'][0], pg.x0 + 12, y + 6, pg.w, 6, 'onest', 8.5, g.muted, 1.2, role='note', max_lines=1)
        T(sl, c['note'][1], pg.x0 + 12, y + 11, pg.w, 6, 'onest-semi', 9.5, g.ink, 1.2, role='note',
          max_lines=1)
        y += 16
    if ims:
        p, f = _pf(ims[0])
        top = max(y + 14, H * c.get('photo_top', 0.56))
        # снимок во всю полосу: оранжевая черта над ним продолжает черту соседней полосы
        xa, xb = pg.X, pg.X + pg.W
        img = Image(p, xa, top, xb - xa, H - top, f)
        sl.add(img)
        sl.add(Rect(xa, top - 1.5, xb - xa, 3, ORANGE, role='band'))
        sl.band_y = top                      # соседняя полоса режет снимки на этой же высоте
        if c.get('caption'):
            caption_on(sl, g, pg, c['caption'], img)
    folio(sl, pg, n, g, False)


def f_photos(sl, c, pg, spec, n):
    g = GROUNDS['deep']
    _ground(sl, pg.X, pg.W, H, g)
    ims = c['photos']
    split = getattr(sl, 'band_y', None) or H * c.get('split', 0.5)
    for i, it in enumerate(ims[:2]):
        p, f = _pf(it)
        ya, yb = (0, split) if i == 0 else (split, H)
        sl.add(Image(p, pg.X, ya, pg.W, yb - ya, f))
    sl.add(Rect(pg.X, split - 1.5, pg.W, 3, ORANGE, role='band'))
    logo_r(sl, spec, pg, ORANGE)


# ======================================================== сборка

ROUTE = {
    ('night', 'cover'): 'cover', ('night', 'back'): 'back',
    ('night', 'numbered'): n_numbered, ('night', 'directions'): n_directions,
    ('night', 'stats'): b_stats, ('night', 'list'): b_list, ('night', 'service'): n_service,
    ('night', 'map'): n_map, ('night', 'regions'): n_regions,
    ('light', 'service'): l_service, ('light', 'photos'): l_photos,
    ('light', 'mission_chart'): l_mission_chart, ('light', 'figures'): l_figures,
    ('light', 'civil'): l_civil, ('light', 'logos'): l_logos, ('light', 'credentials'): l_credentials,
    ('field', 'service'): f_service, ('field', 'photos'): f_photos,
}


def _spreads(n_pages):
    out, p = [(1,)], 2
    while p < n_pages:
        out.append((p, p + 1) if p + 1 < n_pages else (p,))
        p += 2
    out.append((n_pages,))
    return out


def build(ds, spec):
    pages = {p['n']: p for p in spec['pages']}
    W = ds['W']
    out = []
    for k, grp in enumerate(_spreads(max(pages)), 1):
        styles = [pages[p].get('style', 'night') for p in grp]
        sl = Slide(k, '+'.join(f'{s}:{pages[p]["layout"]}' for s, p in zip(styles, grp)), None)
        sl.w, sl.h, sl.pages = W * len(grp), H, grp
        for i, pn in enumerate(grp):
            c = pages[pn]
            side = 'S' if len(grp) == 1 else ('L' if i == 0 else 'R')
            pg = Pg(ds, i * W, side)
            fn = ROUTE.get((styles[i], c['layout']))
            if fn is None:
                raise ValueError(f'полоса {pn}: нет композиции «{c["layout"]}» в режиме «{styles[i]}»')
            if fn == 'cover':
                b_cover(sl, c, pg, spec)
            elif fn == 'back':
                n_back(sl, c, pg, spec)
            else:
                fn(sl, c, pg, spec, pn)
            if c.get('notes'):
                sl.notes += c['notes'] + '\n'
        sl.ground = GROUNDS['paper' if styles[0] == 'light' else 'night']
        for t in sl.items:
            if isinstance(t, Text):
                miss = fonts.missing_glyphs(''.join(t.lines), t.font)
                if miss:
                    sl.warnings.append(f'в шрифте {t.font} нет знаков: {"".join(miss)}')
        out.append(sl)
    return out
