# -*- coding: utf-8 -*-
"""Три новых визуальных направления каталога — по-настоящему разных.

От оригинала берутся только тексты, порядок полос и снимки. Раскладка,
ритм, обработка снимков, гарнитуры — свои у каждого направления.
Фирменные цвета сохранены во всех трёх: фиолетовый и оранжевый.

  A «Чертёж»   — светлый лист, рамка чертёжного листа с линейкой, тёмно-
                 фиолетовый текст, снимки в строгих окнах внутри рамки.
  B «Ночь»     — глубокая ночь, все снимки в фирменной дуотонии
                 (фиолетовые тени — оранжевый свет), широкий гротеск.
  C «Поля»     — плакатные поля: целая полоса оранжевая или фиолетовая,
                 огромный гротеск, рядом — снимок в натуральном цвете.
"""
from .model import Rect, Line, Image, Text, Slide, PT
from .tokens import Ground, mix
from . import vector
from .layouts import text
from .pages import Pg, _pf

V_DEEP, V_BRIGHT, ORANGE = (52, 44, 93), (82, 70, 156), (234, 135, 41)
WHITE = (247, 245, 241)

DIRECTIONS = {
    'A': dict(code='A', name='Чертёж',
              idea='Светлый лист с рамкой и линейкой чертёжного формата: язык инженерной '
                   'документации, переведённый в премиальную вёрстку. Тёмно-фиолетовый текст, '
                   'оранжевый — только метки и сигналы. Снимки — в строгих окнах.',
              display='onest-black', body='onest', strong='onest-semi', number='onest-black'),
    'B': dict(code='B', name='Ночь',
              idea='Глубокий ночной фиолетовый и снимки в фирменной дуотонии: тени — фиолетовые, '
                   'свет — оранжевый. Разномастные фото становятся одной серией, как в '
                   'архитектурной монографии. Широкий гротеск Unbounded.',
              display='wide-bold', body='onest', strong='onest-semi', number='wide'),
    'C': dict(code='C', name='Поля',
              idea='Плакатный язык: полоса целиком — сплошной оранжевый или фиолетовый, '
                   'огромный гротеск, рядом снимок в натуральном цвете. Ритм разворотов '
                   'держится на чередовании полей.',
              display='onest-black', body='onest', strong='onest-semi', number='onest-black'),
}

GROUNDS = {
    'paper':  Ground('paper', (244, 242, 237), (43, 35, 80), (104, 98, 124), (200, 195, 210), ORANGE),
    'night':  Ground('night', (24, 20, 46), WHITE, (176, 169, 196), (72, 64, 108), ORANGE),
    'deep':   Ground('deep', V_DEEP, WHITE, (196, 190, 214), (94, 85, 140), ORANGE),
    'violet': Ground('violet', V_BRIGHT, WHITE, (224, 220, 236), (124, 113, 186), ORANGE),
    'orange': Ground('orange', ORANGE, (40, 32, 74), (78, 52, 52), (196, 108, 38), V_DEEP),
}

DUO = dict(kind='duotone', contrast=1.15,
           stops=[(0.0, (16, 13, 34)), (0.42, (66, 54, 124)), (0.78, (212, 136, 80)), (1.0, (255, 228, 198))])


def T(sl, s, x, y, w, h, font, size, color, lead=1.2, track=0.0, size_min=None, align='l',
      role='body', max_lines=None):
    return text(sl, s, x, y, w, h, font, size, color, lead, track, size_min or size * 0.6, align,
                role, max_lines)


def _logo(sl, spec, x, y, w, color):
    if spec.get('_logo'):
        sh, h = vector.place(spec['_logo'], x, y, w, color)
        sl.add(sh)
        return h
    return 0


def _ground(sl, X, W, H, g):
    sl.add(Rect(X, 0, W + (0.4 if X == 0 else 0), H, g.bg, role='ground'))


# ======================================================== A «Чертёж»

def _a_frame(sl, pg, n):
    """Рамка чертёжного листа: волосяная линия, линейка сверху, номер в окне."""
    g = GROUNDS['paper']
    m = 10.0
    x0, x1 = pg.X + m, pg.X + pg.W - m
    y0, y1 = m, pg.H - m
    for a, b, c, d in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        sl.add(Line(a, b, c, d, g.line, 0.5, role='frame'))
    x = x0
    k = 0
    while x <= x1 + 0.01:                      # линейка: деления 5 и 10 мм
        sl.add(Line(x, y0, x, y0 + (2.2 if k % 2 == 0 else 1.2), g.line, 0.4, role='tick'))
        x += 5.0
        k += 1
    if n:
        bw = 12
        bx = x1 - bw if pg.side != 'L' else x0
        sl.add(Line(bx, y1 - 7, bx + bw, y1 - 7, g.line, 0.5, role='frame'))
        sl.add(Line(bx + (0 if pg.side != 'L' else bw), y1 - 7, bx + (0 if pg.side != 'L' else bw), y1,
                    g.line, 0.5, role='frame'))
        T(sl, f'{n:02d}', bx, y1 - 5.2, bw, 6, 'onest-semi', 7, g.muted, 1.0, 0.08, align='c',
          role='folio', max_lines=1)
    return x0, y0, x1, y1


def a_cover(sl, c, pg, spec):
    g = GROUNDS['paper']
    _ground(sl, pg.X, pg.W, pg.H, g)
    x0, y0, x1, y1 = _a_frame(sl, pg, None)
    _logo(sl, spec, x0 + 8, y0 + 10, 40, V_DEEP)
    p, f = c['image'], tuple(c.get('focus', (0.5, 0.5)))
    sl.add(Image(p, x0 + 8, 62, x1 - x0 - 16, 140, f))
    t = T(sl, c['title'], x0 + 8, 216, x1 - x0 - 16, 50, 'onest-black', 46, g.ink, 0.98, -0.03,
          role='hero')
    sl.add(Rect(x0 + 8, t.y + t.h + 7, 22, 1.6, ORANGE, role='marker'))
    T(sl, c.get('tag', ''), x1 - 8 - 40, y1 - 14, 40, 8, 'onest-semi', 11, g.ink,
      1.0, 0.04, align='r', role='tag', max_lines=1)


def a_stats(sl, c, pg, spec, n):
    g = GROUNDS['paper']
    _ground(sl, pg.X, pg.W, pg.H, g)
    x0, y0, x1, y1 = _a_frame(sl, pg, n)
    L, R = x0 + 10, x1 - 10
    items = c['items']
    y = 34
    h0 = items[0]
    sl.add(Rect(L, y, 14, 1.6, ORANGE, role='marker'))
    v = T(sl, h0['value'], L - 1.5, y + 8, R - L, 60, 'onest-black', 92, g.ink, 0.95, -0.045, role='hero')
    T(sl, h0['label'], L, v.y + v.h + 2, 90, 12, 'onest', 10, g.muted, 1.3)
    rows = items[1:]
    top = 150
    rh = (y1 - 18 - top) / 3
    cw = (R - L - 8) / 2
    for i, it in enumerate(rows):
        cx = L + (i % 2) * (cw + 8)
        cy = top + (i // 2) * rh
        sl.add(Line(cx, cy, cx + cw, cy, g.line, 0.5))
        sl.add(Rect(cx, cy - 0.8, 6, 1.6, ORANGE, role='marker'))
        vv = T(sl, it['value'], cx, cy + 6, cw, 24, 'onest-black', 38, g.ink, 1.0, -0.03, role='stat',
               max_lines=1)
        T(sl, it.get('label', ''), cx, vv.y + vv.h + 2.5, cw, 14, 'onest', 8.5, g.muted, 1.3)


def a_list(sl, c, pg, spec, n):
    g = GROUNDS['paper']
    _ground(sl, pg.X, pg.W, pg.H, g)
    x0, y0, x1, y1 = _a_frame(sl, pg, n)
    L, R = x0 + 10, x1 - 10
    _logo(sl, spec, R - 28, y0 + 9, 28, V_DEEP)
    sl.add(Rect(L, 34, 14, 1.6, ORANGE, role='marker'))
    t = T(sl, c['title'], L, 41, R - L, 60, 'onest-black', 31, g.ink, 1.02, -0.02, role='title')
    y = max(t.y + t.h + 24, 120)
    items = c['items']
    half = (len(items) + 1) // 2
    cw = (R - L - 8) / 2
    for ci, chunk in enumerate((items[:half], items[half:])):
        cx = L + ci * (cw + 8)
        yy = y
        for it in chunk:
            sl.add(Line(cx, yy, cx + cw, yy, g.line, 0.5))
            sl.add(Rect(cx, yy + 4.6, 1.8, 1.8, ORANGE, role='marker'))
            tt = T(sl, it, cx + 5, yy + 3.8, cw - 5, 16, 'onest', 11, g.ink, 1.3, role='item')
            yy = max(yy + 15, tt.y + tt.h + 4.5)
        sl.add(Line(cx, yy, cx + cw, yy, g.line, 0.5))


def a_service(sl, c, pg, spec, n):
    g = GROUNDS['paper']
    _ground(sl, pg.X, pg.W, pg.H, g)
    x0, y0, x1, y1 = _a_frame(sl, pg, n)
    L, R = x0 + 10, x1 - 10
    sl.add(Rect(L, 34, 14, 1.6, ORANGE, role='marker'))
    t = T(sl, c['title'], L, 41, R - L, 60, 'onest-black', 31, g.ink, 1.02, -0.02, role='title')
    y = t.y + t.h + 14
    for it in c.get('items', []):
        sl.add(Line(L, y, R, y, g.line, 0.5))
        sl.add(Rect(L, y + 4.4, 1.8, 1.8, ORANGE, role='marker'))
        tt = T(sl, it, L + 5, y + 3.6, R - L - 5, 20, 'onest', 10.5, g.ink, 1.35, role='item')
        y = tt.y + tt.h + 4
    sl.add(Line(L, y, R, y, g.line, 0.5))
    ims = c.get('photos', [])
    if ims:
        p, f = _pf(ims[0])
        top = max(y + 14, 132)
        sl.add(Image(p, x0 + 6, top, x1 - x0 - 12, y1 - 6 - top, f))


def a_photos(sl, c, pg, spec, n):
    g = GROUNDS['paper']
    _ground(sl, pg.X, pg.W, pg.H, g)
    x0, y0, x1, y1 = _a_frame(sl, pg, n)
    ims = c['photos']
    top, bot = y0 + 6, y1 - 12
    split = top + (bot - top) * c.get('split', 0.5)
    for i, it in enumerate(ims[:2]):
        p, f = _pf(it)
        ya, yb = (top, split - 2) if i == 0 else (split + 2, bot)
        sl.add(Image(p, x0 + 6, ya, x1 - x0 - 12, yb - ya, f))
    _logo(sl, spec, x1 - 6 - 28, bot + 1.5, 22, V_DEEP)


# ======================================================== B «Ночь»

def b_cover(sl, c, pg, spec):
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, pg.H, g)
    p, f = c['image'], tuple(c.get('focus', (0.5, 0.5)))
    sl.add(Image(p, pg.X, 0, pg.W, pg.H, f,
                 shade=[DUO, dict(side='bottom', to=g.bg, amount=0.9, extent=0.45)]))
    _logo(sl, spec, pg.x0, 18, 36, ORANGE)
    t = T(sl, c['title'], pg.x0, 0, pg.w + 6, 70, 'wide-bold', 40, g.ink, 1.1, -0.02, role='hero')
    t.y = 297 - 46 - t.h
    sl.add(Rect(pg.x0, t.y - 10, 30, 1.2, ORANGE, role='marker'))
    T(sl, c.get('tag', ''), pg.x0, t.y + t.h + 7, 60, 8, 'wide', 11, ORANGE, 1.0, 0.02, role='tag',
      max_lines=1)


def _b_folio(sl, pg, n, g):
    x = pg.x1 - 20 if pg.side != 'L' else pg.x0
    T(sl, f'{n:02d}', x, 297 - 12, 20, 6, 'wide', 7, g.muted, 1.0, 0.02,
      align='r' if pg.side != 'L' else 'l', role='folio', max_lines=1)


def b_stats(sl, c, pg, spec, n):
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, pg.H, g)
    items = c['items']
    y = 30
    rh = (297 - 30 - 26) / len(items)
    for i, it in enumerate(items):
        yy = y + i * rh
        sl.add(Line(pg.x0, yy, pg.x1, yy, g.line, 0.5))
        size = 30 if i else 44
        v = T(sl, it['value'], pg.x0, yy + 6, pg.w * 0.64, 30, 'wide', size, ORANGE if i == 0 else g.ink,
              1.0, -0.02, role='hero' if i == 0 else 'stat', max_lines=1)
        T(sl, it.get('label', ''), pg.x0 + pg.w * 0.66, yy + 7.5, pg.w * 0.34, 20, 'onest', 9, g.muted, 1.35)
    _b_folio(sl, pg, n, g)


def b_list(sl, c, pg, spec, n):
    g = GROUNDS['deep']
    _ground(sl, pg.X, pg.W, pg.H, g)
    _logo(sl, spec, pg.x1 - 28, 18, 28, ORANGE)
    t = T(sl, c['title'], pg.x0, 48, pg.w, 60, 'wide-bold', 22, g.ink, 1.22, -0.01, role='title')
    y = max(t.y + t.h + 30, 130)
    for it in c['items']:
        sl.add(Line(pg.x0, y, pg.x1, y, g.line, 0.5))
        tt = T(sl, it, pg.x0, y + 3.8, pg.w, 14, 'onest', 11.5, g.ink, 1.3, role='item')
        y = tt.y + tt.h + 4
    sl.add(Line(pg.x0, y, pg.x1, y, g.line, 0.5))
    _b_folio(sl, pg, n, g)


def b_service(sl, c, pg, spec, n):
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, pg.H, g)
    ims = c.get('photos', [])
    if ims:
        p, f = _pf(ims[0])
        sl.add(Image(p, pg.X, 0, pg.W, 297, f,
                     shade=[DUO, dict(side='top', to=g.bg, amount=0.95, extent=0.62)]))
    t = T(sl, c['title'], pg.x0, 40, pg.w, 60, 'wide-bold', 26, g.ink, 1.16, -0.015, role='title')
    y = t.y + t.h + 16
    for it in c.get('items', []):
        sl.add(Rect(pg.x0, y + 1.9, 6, 1.0, ORANGE, role='marker'))
        tt = T(sl, it, pg.x0 + 10, y, pg.w * 0.78, 20, 'onest', 10.5, g.ink, 1.38, role='item')
        y = tt.y + tt.h + 5
    _b_folio(sl, pg, n, g)


def b_photos(sl, c, pg, spec, n):
    g = GROUNDS['night']
    _ground(sl, pg.X, pg.W, pg.H, g)
    ims = c['photos']
    split = 297 * c.get('split', 0.5)
    for i, it in enumerate(ims[:2]):
        p, f = _pf(it)
        ya, yb = (0, split - 1) if i == 0 else (split + 1, 297)
        sl.add(Image(p, pg.X, ya, pg.W, yb - ya, f, shade=DUO))
    _logo(sl, spec, pg.x1 - 28, 18, 28, ORANGE)


# ======================================================== C «Поля»

def c_cover(sl, c, pg, spec):
    g = GROUNDS['orange']
    _ground(sl, pg.X, pg.W, pg.H, g)
    p, f = c['image'], tuple(c.get('focus', (0.5, 0.5)))
    sl.add(Image(p, pg.X, 168, pg.W, 297 - 168, f))
    _logo(sl, spec, pg.x0, 18, 42, V_DEEP)
    t = T(sl, c['title'], pg.x0 - 1.5, 0, pg.w + 8, 90, 'onest-black', 54, g.ink, 0.95, -0.04, role='hero')
    t.y = 168 - 14 - t.h
    T(sl, c.get('tag', ''), pg.x1 - 40, 20, 40, 8, 'onest-black', 14, g.ink, 1.0, 0.0, align='r',
      role='tag', max_lines=1)


def _c_folio(sl, pg, n, g):
    x = pg.x1 - 20 if pg.side != 'L' else pg.x0
    T(sl, f'{n:02d}', x, 297 - 12, 20, 6, 'onest-black', 8, g.ink, 1.0, 0.0,
      align='r' if pg.side != 'L' else 'l', role='folio', max_lines=1)


def c_stats(sl, c, pg, spec, n):
    g = GROUNDS['orange']
    _ground(sl, pg.X, pg.W, pg.H, g)
    items = c['items']
    y = 26
    h0 = items[0]
    v = T(sl, h0['value'], pg.x0 - 2.5, y, pg.w + 8, 60, 'onest-black', 88, g.ink, 0.92, -0.05, role='hero',
          max_lines=1)
    T(sl, h0['label'], pg.x0, v.y + v.h + 2, 100, 12, 'onest-semi', 10, g.ink, 1.3)
    rows = items[1:]
    top = 122
    rh = (297 - 24 - top) / len(rows)
    for i, it in enumerate(rows):
        yy = top + i * rh
        sl.add(Line(pg.x0, yy, pg.x1, yy, g.ink, 0.7))
        vv = T(sl, it['value'], pg.x0, yy + 5, pg.w * 0.6, 28, 'onest-black', 36, g.ink, 1.0, -0.04,
               role='stat', max_lines=1)
        T(sl, it.get('label', ''), pg.x0 + pg.w * 0.6, yy + 6.5, pg.w * 0.4, 20, 'onest-semi', 8.5, g.ink, 1.3)
    _c_folio(sl, pg, n, g)


def c_list(sl, c, pg, spec, n):
    g = GROUNDS['violet']
    _ground(sl, pg.X, pg.W, pg.H, g)
    _logo(sl, spec, pg.x1 - 30, 18, 30, ORANGE)
    t = T(sl, c['title'], pg.x0 - 1, 40, pg.w + 4, 80, 'onest-black', 36, g.ink, 0.97, -0.035, role='title')
    y = max(t.y + t.h + 26, 128)
    for it in c['items']:
        tt = T(sl, it, pg.x0, y, pg.w, 16, 'onest-semi', 14, g.ink, 1.2, -0.01, role='item')
        y = tt.y + tt.h + 5.5
    _c_folio(sl, pg, n, g)


def c_service(sl, c, pg, spec, n):
    g = GROUNDS['deep']
    _ground(sl, pg.X, pg.W, pg.H, g)
    t = T(sl, c['title'], pg.x0 - 1.5, 30, pg.w + 6, 100, 'onest-black', 46, g.ink, 0.95, -0.04, role='title')
    y = max(t.y + t.h + 20, 150)
    for it in c.get('items', []):
        sl.add(Rect(pg.x0, y + 2.0, 8, 1.6, ORANGE, role='marker'))
        tt = T(sl, it, pg.x0 + 12, y, pg.w - 12, 30, 'onest', 10.5, g.ink, 1.35, role='item')
        y = tt.y + tt.h + 7
    _c_folio(sl, pg, n, g)


def c_photos(sl, c, pg, spec, n):
    g = GROUNDS['deep']
    _ground(sl, pg.X, pg.W, pg.H, g)
    ims = c['photos']
    split = 297 * c.get('split', 0.5)
    for i, it in enumerate(ims[:2]):
        p, f = _pf(it)
        ya, yb = (0, split) if i == 0 else (split, 297)
        sl.add(Image(p, pg.X, ya, pg.W, yb - ya, f))
    sl.add(Rect(pg.X, split - 1.5, pg.W, 3, ORANGE, role='band'))


RENDER = {
    'A': dict(cover=a_cover, stats=a_stats, list=a_list, service=a_service, photos=a_photos),
    'B': dict(cover=b_cover, stats=b_stats, list=b_list, service=b_service, photos=b_photos),
    'C': dict(cover=c_cover, stats=c_stats, list=c_list, service=c_service, photos=c_photos),
}


def sample(ds, spec, code, groups=((1,), (6, 7), (12, 13))):
    """Полотна-образцы направления: обложка и два разворота."""
    pages = {p['n']: p for p in spec['pages']}
    R = RENDER[code]
    W, H = ds['W'], ds['H']
    out = []
    for k, grp in enumerate(groups, 1):
        sl = Slide(k, code, GROUNDS['paper'])
        sl.w, sl.h, sl.pages = W * len(grp), H, grp
        for i, pn in enumerate(grp):
            c = pages[pn]
            side = 'S' if len(grp) == 1 else ('L' if i == 0 else 'R')
            pg = Pg(ds, i * W, side)
            if c['layout'] == 'cover':
                R['cover'](sl, c, pg, spec)
            else:
                R[c['layout']](sl, c, pg, spec, pn)
        out.append(sl)
    return out
