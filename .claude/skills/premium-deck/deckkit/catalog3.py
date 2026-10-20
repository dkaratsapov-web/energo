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
from .model import Rect, Line, Dot, Image, Text, Slide, Shape, Poly, PT
from .tokens import mix
from . import vector, fonts
from .catalog2 import (GROUNDS, ORANGE, V_DEEP, V_BRIGHT, WHITE, T, _logo, _ground, _a_frame,
                       b_cover, b_stats, b_list)
from .pages import Pg, _pf

H = 297.0
MARK = (14.0, 1.6)                         # оранжевая метка над заголовком
CROP = 0.15                                # больше — кадр уже теряет смысл
LOGO_W, LOGO_TOP, LOGO_OUT = 28.0, 17.0, 16.0   # логотип: всегда здесь
LOGO_FLOOR = LOGO_TOP + LOGO_W * 0.675 + 6      # ниже — свободно для снимков


def ar(it):
    """Пропорция снимка w/h по исходнику (после снятия кромок)."""
    from . import images
    p, _ = _pf(it)
    sw, sh = images.src_size(p)
    return sw / sh


def mc(it):
    """Допуск подрезки кадра: по умолчанию CROP, у снимка с небом/фасадом по краям — свой."""
    return it.get('max_crop', CROP) if isinstance(it, dict) else CROP


def crop_of(it, w, h):
    """Какую долю кадра срежет окно w×h (по одной стороне)."""
    a, b = ar(it), w / h
    return 1 - (a / b if b > a else b / a)


def column(items, w, avail, gap):
    """Снимки столбцом во всю ширину: высоты — по пропорциям; если места
    мало — сначала подрезка до CROP, потом сужение столбца."""
    nat = [w / ar(it) for it in items]
    total = sum(nat) + gap * (len(items) - 1)
    k = (avail - gap * (len(items) - 1)) / sum(nat)
    if k >= 1:
        return w, nat
    kc = max(k, 1 - CROP)
    hs = [n * kc for n in nat]
    if k >= 1 - CROP:
        return w, [n * k for n in nat]
    s = k / kc                                # не влезает и с подрезкой — сужаем
    return w * s, [n * kc * s for n in nat]


def row(items, w, avail, gap):
    """Снимки в ряд на одной высоте: ширина каждого — по пропорции."""
    a = [ar(it) for it in items]
    h = (w - gap * (len(items) - 1)) / sum(a)
    if h <= avail:
        return h, [h * x for x in a]
    if h * (1 - CROP) <= avail:              # чуть подрезаем по высоте
        return avail, [(w - gap * (len(items) - 1)) * x / sum(a) for x in a]
    return avail, [avail * x for x in a]      # уже не влезает — ряд уже


def bottom_photo(it, x, w, text_end, min_gap=14):
    """Снимок во всю ширину снизу полосы: высота по пропорции, подрезка
    не больше CROP; если текста слишком много — окно сужается."""
    nat = w / ar(it)
    avail = H - (text_end + min_gap)
    if nat <= avail:
        return x, H - nat, w, nat
    if nat * (1 - CROP) <= avail:
        return x, H - avail, w, avail
    ww = avail * ar(it) / (1 - CROP)
    return x, H - avail, ww, avail


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


FOLIO = (10.0, 12.0, 7.0)                  # отступ от обреза, окно ширина × высота


def folio(sl, pg, n, g, light):
    """Номер полосы — одно окно 12×7 мм внизу снаружи на всех полосах.
    В «Чертеже» окно — часть рамки (_a_frame); здесь то же окно на фоне полосы,
    поверх снимка — залитое цветом фона."""
    if light:
        return
    m, bw, bh = FOLIO
    bx = pg.X + pg.W - m - bw if pg.side != 'L' else pg.X + m
    by = H - m - bh
    sl.add(Rect(bx, by, bw, bh, g.bg, role='plate'))
    for a, b, c_, d in ((bx, by, bx + bw, by), (bx + bw, by, bx + bw, by + bh),
                        (bx + bw, by + bh, bx, by + bh), (bx, by + bh, bx, by)):
        sl.add(Line(a, b, c_, d, g.line, 0.5, role='tab'))
    T(sl, f'{n:02d}', bx, H - m - 5.2, bw, 6, 'onest-semi', 7, g.muted, 1.0, 0.08, align='c',
      role='folio', max_lines=1)


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
                                    y + (sh - 0.377 * 58) / 2, 58, g.ink, role='wordmark')
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


def n_stats(sl, c, pg, spec, n):
    """Цифры: иконка по смыслу, цифра, подпись; строки на волосяных линейках."""
    from . import icons
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, H, g)
    items = c['items']
    y = 30
    rh = (H - 30 - 26) / len(items)
    ic = 12.0
    for i, it in enumerate(items):
        yy = y + i * rh
        sl.add(Line(pg.x0, yy, pg.x1, yy, g.line, 0.5))
        size = 30 if i else 44
        vy = yy + 6
        if it.get('icon'):                   # центр иконки = центр высоты цифр
            f = fonts.info('wide')
            base = vy + f['ascent'] * size * PT
            cy = base - f['cap'] * size * PT / 2
            sl.items.extend(icons.centered(it['icon'], pg.x0 + ic / 2, cy, ic, ORANGE))
        x = pg.x0 + (ic + 7 if it.get('icon') else 0)
        T(sl, it['value'], x, vy, pg.w * 0.62 - (x - pg.x0), 30, 'wide', size, ORANGE if i == 0 else g.ink,
          1.0, -0.02, role='hero' if i == 0 else 'stat', max_lines=1)
        T(sl, it.get('label', ''), pg.x0 + pg.w * 0.66, yy + 7.5, pg.w * 0.34, 20, 'onest', 9, g.muted, 1.35)
    folio(sl, pg, n, g, False)


def n_list(sl, c, pg, spec, n):
    """Список направлений: оранжевая точка у каждого пункта."""
    g = GROUNDS['deep']
    _ground(sl, pg.X, pg.W, H, g)
    mark(sl, pg.x0, 48)
    t = T(sl, c['title'], pg.x0, 55, pg.w, 60, 'wide-bold', 22, g.ink, 1.22, -0.01, role='title')
    y = max(t.y + t.h + 30, 130)
    for it in c['items']:
        sl.add(Line(pg.x0, y, pg.x1, y, g.line, 0.5))
        tt = T(sl, it, pg.x0 + 6, y + 3.8, pg.w - 6, 14, 'onest', 11.5, g.ink, 1.3, role='item')
        sl.add(Dot(pg.x0 + 1.3, tt.baseline(0) - 11.5 * PT * 0.34, 1.1, ORANGE, role='marker'))
        y = tt.y + tt.h + 4
    sl.add(Line(pg.x0, y, pg.x1, y, g.line, 0.5))
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
        x, top, w, hh = bottom_photo(ims[0], pg.X, pg.W, y)
        if w < pg.W and pg.side == 'L':
            x = pg.X                              # узкое окно — к внешнему обрезу
        elif w < pg.W:
            x = pg.X + pg.W - w
        img = Image(p, x, top, w, hh, f)
        sl.add(img)
        if c.get('caption'):
            caption_on(sl, g, pg, c['caption'], img)
    folio(sl, pg, n, g, False)


def n_map(sl, c, pg, spec, n):
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, H, g)
    mark(sl, pg.x0, 26)
    T(sl, c['title'], pg.x0, 33, pg.w * 0.6, 40, 'wide-bold', 24, g.ink, 1.12, -0.02, role='hero')
    folio(sl, pg, n, g, False)


def n_regions(sl, c, pg, spec, n):
    """Области — одним списком поверх карты, на всю высоту полосы."""
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, H, g)
    items = c['items']
    top, bot = LOGO_FLOOR + 14, H - 26
    step = (bot - top) / len(items)
    w = pg.w * 0.78
    for j, it in enumerate(items):
        y = top + j * step
        sl.add(Line(pg.x0, y, pg.x0 + w, y, mix(g.line, WHITE, 0.15), 0.5))
        t = T(sl, it, pg.x0 + 6, y + (step - 10.5 * PT) / 2 - 0.4, w - 6, 8, 'onest', 10.5, g.ink, 1.2,
              role='item', max_lines=1)
        sl.add(Dot(pg.x0 + 1.4, t.baseline(0) - 10.5 * PT * 0.34, 1.1, ORANGE, role='marker'))
    sl.add(Line(pg.x0, bot, pg.x0 + w, bot, mix(g.line, WHITE, 0.15), 0.5))
    folio(sl, pg, n, g, False)


def _under(sl, els):
    """Элементы на весь разворот — сразу над фонами обеих полос, под всем остальным."""
    gr = [e for e in sl.items if isinstance(e, Rect) and e.role == 'ground']
    sl.items[:] = gr + els + [e for e in sl.items if not (isinstance(e, Rect) and e.role == 'ground')]


def spread_map(sl, spec, regions_page, W2):
    """Карта страны на весь разворот: субъекты с тонкими границами,
    области присутствия — фирменным оранжевым по настоящим границам."""
    from . import geo
    path = spec.get('_geo')
    if not path:
        return
    d = geo.load(path)
    present = set(regions_page['items'])
    g = GROUNDS['night']
    mw = W2 - 40                                 # 20 мм поля с каждой стороны
    mh = mw * d['aspect']
    x0 = 20
    y0 = spec.get('map_top_mm', 62)
    base = (50, 42, 92)
    k_ = mw
    shapes, lines = [], []
    for name, rings in d['regions'].items():
        pts = [[(x0 + x * k_, y0 + y * k_) for x, y in r] for r in rings]
        col = ORANGE if name in present else base
        shapes.append(Shape(pts, col, 'map'))
        for r in pts:
            lines.append(Poly(r + [r[0]], stroke=g.bg, width=0.3, role='map-line'))
    missing = present - set(d['regions'])
    if missing:
        sl.warnings.append('на карте не найдены: ' + ', '.join(sorted(missing)))
    _under(sl, shapes + lines)


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
        top = y + 12
        bot = y1 - (14 if c.get('caption') else 12)   # выше окна с номером (7 мм) + воздух
        fw = fx1 - fx0 - 12
        if c.get('fill') and len(ims) == 1:   # один кадр на всё свободное место
            it = ims[0]
            a_ = ar(it)
            hh = min(bot - top, fw / (a_ * (1 - mc(it))))
            p, f = _pf(it)
            sl.add(Image(p, fx0 + 6, bot - hh, fw, hh, f, allow_crop=mc(it) if mc(it) > CROP else 0.0))
        elif c.get('vertical', False):
            cw, hs = column(ims, fw, bot - top, 4)
            yy = bot - sum(hs) - 4 * (len(hs) - 1)
            for it, hh in zip(ims, hs):
                p, f = _pf(it)
                sl.add(Image(p, fx0 + 6, yy, cw, hh, f))
                yy += hh + 4
        else:
            hh, ws = row(ims, fw, bot - top, 4)
            xx = fx0 + 6
            for it, ww in zip(ims, ws):
                p, f = _pf(it)
                sl.add(Image(p, xx, bot - hh, ww, hh, f))
                xx += ww + 4
        if c.get('caption'):
            T(sl, c['caption'], fx0 + 6, bot + 3.2, fx1 - fx0 - 12, 6, 'onest-semi', 7.5, g.muted, 1.2, 0.02,
              align='r' if pg.side == 'L' else 'l', role='caption', max_lines=1)


def l_photos(sl, c, pg, spec, n):
    g, L, R, y0, y1, fx0, fx1 = _light(sl, pg, n)
    ims = c['photos'][:2]
    top = LOGO_FLOOR if pg.side != 'L' else y0 + 6
    bot = y1 - 12
    cw, hs = column(ims, fx1 - fx0 - 12, bot - top, 4)
    yy = top + (bot - top - sum(hs) - 4 * (len(hs) - 1)) / 2
    for it, hh in zip(ims, hs):
        p, f = _pf(it)
        sl.add(Image(p, fx0 + 6, yy, cw, hh, f))
        yy += hh + 4


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
    RH = 12.5                                  # одна сетка строк для обеих колонок
    from . import icons
    for ci, rws in enumerate(cols):
        x = L + ci * (cw + 8)
        for j, r in enumerate(rws):
            y = y_tab + j * RH
            sl.add(Line(x, y, x + cw, y, g.line, 0.5))
            if r.get('num'):
                T(sl, r['num'], x, y + 3.6, 20, 10, 'onest-black', 16, g.ink, 1.0, -0.02, role='num',
                  max_lines=1)
            else:                              # строка без числа — иконка на месте числа
                sl.items.extend(icons.draw(r.get('icon', 'area'), x + 0.5, y + 2.6, 7.5, ORANGE))
            # подпись на одной базовой линии с числом; две строки — по центру строки таблицы
            nb = y + 3.6 + fonts.info('onest-black')['ascent'] * 16 * PT
            fa = fonts.info('onest')['ascent'] * 9 * PT
            lines = len(fonts.wrap(r['label'], 'onest', 9, (cw - 17) / PT))
            if lines == 1:
                ty = nb - fa
            else:
                ty = y + RH / 2 - ((lines - 1) * 9 * 1.3 * PT) / 2 - fa + 9 * PT * 0.36
            T(sl, r['label'], x + 17, ty, cw - 17, 20, 'onest', 9, g.muted, 1.3)
        sl.add(Line(x, y_tab + len(rws) * RH, x + cw, y_tab + len(rws) * RH, g.line, 0.5))


def l_civil(sl, c, pg, spec, n):
    g, L, R, y0, y1, fx0, fx1 = _light(sl, pg, n)
    t = head(sl, c['title'], L, 34, R - L, 30, g.ink)
    y = t.y + t.h + 14
    for ptxt in c.get('paras', []):
        y = rows(sl, [ptxt], L, y, R - L, g, size=10.5) + 6
    for ln in c.get('note_lines', []):
        T(sl, ln, L + 5.5, y - 2, R - L, 6, 'onest-semi', 8.5, g.muted, 1.2, 0.02, role='note', max_lines=1)
        y += 5.2
    top = y + 10
    bot = y1 - 12                              # выше окна с номером (7 мм) + воздух
    rws = c['rows']
    fw = fx1 - fx0 - 12
    caps = 9 * sum(1 for r in rws if r.get('caption'))
    nat = [(fw - 4 * (len(r['photos']) - 1)) / sum(ar(it) for it in r['photos']) for r in rws]
    avail = bot - top - caps - 4 * (len(rws) - 1)
    k = min(1.0, avail / sum(nat))
    if c.get('fill'):                         # ряды растут на свободное место, кадры
        m = min(mc(it) for r in rws for it in r['photos'])     # подрезаются с боков не больше допуска
        k = min(avail / sum(nat), 1 / (1 - m))
    kc = max(k, 1 - CROP) if k < 1 else k     # подрезка рядов по высоте не больше CROP
    shrink = k / kc                           # остальное — сужением рядов
    yy = bot - (sum(nat) * k + caps + 4 * (len(rws) - 1))
    for r, hn in zip(rws, nat):
        ims = r['photos']
        hh = hn * k
        a = [ar(it) for it in ims]
        rw = fw * shrink
        ws = [(rw - 4 * (len(ims) - 1)) * x / sum(a) for x in a]
        xx = fx0 + 6
        for it, ww in zip(ims, ws):
            p, f = _pf(it)
            sl.add(Image(p, xx, yy, ww, hh, f, allow_crop=mc(it) if mc(it) > CROP else 0.0))
            xx += ww + 4
        yy += hh
        if r.get('caption'):
            T(sl, r['caption'], fx0 + 6, yy + 2.6, rw, 6, 'onest-semi', 7.5, g.muted, 1.2,
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

def f_full(sl, c, pg, spec, n):
    """Снимок на всю полосу, заголовок — по небу; сверху мягкий переход в фиолетовый."""
    g = GROUNDS['deep']
    _ground(sl, pg.X, pg.W, H, g)
    p, f = _pf(c['photos'][0])
    sh = [dict(side='top', to=g.bg, amount=c.get('shade', 0.8), extent=c.get('shade_extent', 0.5))]
    if c.get('shade_left'):                     # под колонкой текста — ещё и слева
        sh.append(dict(side='left', to=g.bg, amount=c['shade_left'], extent=0.6))
    sl.add(Image(p, pg.X, 0, pg.W, H, f, allow_crop=mc(c['photos'][0]), shade=sh))
    logo_r(sl, spec, pg, ORANGE)
    t = head(sl, c['title'], pg.x0, 40, pg.w * 0.86, c.get('title_size', 40), g.ink, h=100, lead=1.04,
             track=-0.02)
    y = t.y + t.h + 12
    for it in c.get('items', []):
        sl.add(Rect(pg.x0, y + 2.0, 8, 1.6, ORANGE, role='marker'))
        tt = T(sl, it, pg.x0 + 12, y, pg.w * c.get('items_w', 0.7), 40, 'onest', 10.5, g.ink, 1.38, role='item')
        y = tt.y + tt.h + 6
    folio(sl, pg, n, g, False)


def f_service(sl, c, pg, spec, n):
    if c.get('full_photo'):
        return f_full(sl, c, pg, spec, n)
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
        x, top, w, hh = bottom_photo(ims[0], pg.X, pg.W, y)
        # черта на высоте соседней полосы, если кадр это выдерживает без лишней подрезки
        want = getattr(sl, 'band_y', None)
        if want and want >= y + 14 and crop_of(ims[0], pg.W, H - want) <= CROP:
            x, top, w, hh = pg.X, want, pg.W, H - want
        if w < pg.W:
            x = pg.X if pg.side == 'L' else pg.X + pg.W - w
        img = Image(p, x, top, w, hh, f)
        sl.add(img)
        sl.add(Rect(pg.X, top - 1.5, pg.W, 3, ORANGE, role='band'))
        if c.get('caption'):
            caption_on(sl, g, pg, c['caption'], img)
    folio(sl, pg, n, g, False)


def _split(ims, W=210.0):
    """Где разрезать полосу на два кадра, чтобы оба потеряли поровну и мало."""
    if len(ims) < 2:
        return H
    n1, n2 = W / ar(ims[0]), W / ar(ims[1])
    return H * n1 / (n1 + n2)


def f_photos(sl, c, pg, spec, n):
    g = GROUNDS['deep']
    _ground(sl, pg.X, pg.W, H, g)
    ims = c['photos']
    split = getattr(sl, 'band_y', None) or _split(ims)
    for i, it in enumerate(ims[:2]):
        p, f = _pf(it)
        ya, yb = (0, split) if i == 0 else (split, H)
        sl.add(Image(p, pg.X, ya, pg.W, yb - ya, f))
    sl.add(Rect(pg.X, split - 1.5, pg.W, 3, ORANGE, role='band'))
    logo_r(sl, spec, pg, ORANGE)
    folio(sl, pg, n, g, False)


# ======================================================== сборка

ROUTE = {
    ('night', 'cover'): 'cover', ('night', 'back'): 'back',
    ('night', 'numbered'): n_numbered, ('night', 'directions'): n_directions,
    ('night', 'stats'): n_stats, ('night', 'list'): n_list, ('night', 'service'): n_service,
    ('night', 'map'): n_map, ('night', 'regions'): n_regions,
    ('light', 'service'): l_service, ('light', 'photos'): l_photos,
    ('light', 'mission_chart'): l_mission_chart, ('light', 'figures'): l_figures,
    ('light', 'civil'): l_civil, ('light', 'logos'): l_logos, ('light', 'credentials'): l_credentials,
    ('field', 'service'): f_service, ('field', 'photos'): f_photos,
}


def spread_backdrop(sl, pages, grp):
    """Подложка на весь разворот (под всем, кроме фона): поле страницы
    с ключом backdrop. darken — доля затемнения к ночному тону, чтобы текст читался."""
    bd = next((pages[p]['backdrop'] for p in grp if pages[p].get('backdrop')), None)
    if not bd:
        return
    p, f = _pf(bd)
    sh = dict(side='all', to=GROUNDS['night'].bg, amount=bd.get('darken', 0.0)) if bd.get('darken') else None
    _under(sl, [Image(p, 0, 0, sl.w, H, f, shade=sh, role='backdrop')])
    for t in sl.items:                          # на рисунке серый текст теряется — белым
        if isinstance(t, Text) and t.color in (GROUNDS['night'].muted, GROUNDS['deep'].muted):
            t.color = WHITE


def place_logo(sl, spec, grp, styles, W):
    """Логотип всегда в одном месте: вверху снаружи, 16 мм от обреза, ширина 28 мм.
    На правой полосе и лицевой обложке — справа; на задней обложке — слева."""
    sl.items[:] = [e for e in sl.items if not (isinstance(e, Shape) and e.role == 'logo')]
    if not spec.get('_logo'):
        return
    for i, pn in enumerate(grp):
        single = len(grp) == 1
        right = (i == 1) or (single and pn == 1)
        left_back = single and pn != 1
        if not (right or left_back):
            continue
        X = i * W
        x = X + W - LOGO_OUT - LOGO_W if right else X + LOGO_OUT
        color = V_DEEP if styles[i] == 'light' else ORANGE
        _logo(sl, spec, x, LOGO_TOP, LOGO_W, color)


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
        if len(grp) == 2 and styles[1] == 'field' and pages[grp[1]]['layout'] == 'photos':
            sl.band_y = _split(pages[grp[1]]['photos'])     # общая черта поля на развороте
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
        lays = [pages[p]['layout'] for p in grp]
        if 'map' in lays and 'regions' in lays:
            spread_map(sl, spec, pages[grp[lays.index('regions')]], sl.w)
        spread_backdrop(sl, pages, grp)
        place_logo(sl, spec, grp, styles, W)
        sl.ground = GROUNDS['paper' if styles[0] == 'light' else 'night']
        for t in sl.items:
            if isinstance(t, Text):
                miss = fonts.missing_glyphs(''.join(t.lines), t.font)
                if miss:
                    sl.warnings.append(f'в шрифте {t.font} нет знаков: {"".join(miss)}')
        out.append(sl)
    return out
