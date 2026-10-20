# -*- coding: utf-8 -*-
"""Полосы печатного каталога (A4, развороты).

Содержание каждой полосы приходит из брифа ДОСЛОВНО: движок ничего не
добавляет от себя, кроме номера полосы и логотипа. Слова, порядок полос и
снимки — как в утверждённом оригинале; меняется только оформление.

Полотно — разворот 420 × 297 мм (или одиночная полоса: обложки). Каждая
функция рисует свою полосу со смещением X (0 — левая, 210 — правая).
Текст не подходит к корешку ближе внутреннего поля: в печати он уйдёт
в переплёт.
"""
import math
from .model import Rect, Line, Dot, Image, Text, Slide, PT
from .tokens import mix
from . import fonts, vector
from .layouts import text, label, place_arc, MM

GAP = 3.0             # между снимками — полоса фона


# ------------------------------------------------------------ сетка полосы

class Pg:
    """Поля одной полосы: внешнее поле снаружи, внутреннее — у корешка."""

    def __init__(self, ds, X, side):
        gr = ds['grid']
        self.X, self.side = X, side          # side: 'L', 'R' или 'S' (одиночная)
        self.W, self.H = ds['W'], ds['H']
        out, inn = gr['margin'], gr['inner']
        if side == 'L':
            self.x0, self.x1 = X + out, X + self.W - inn
        elif side == 'R':
            self.x0, self.x1 = X + inn, X + self.W - out
        else:
            self.x0, self.x1 = X + out, X + self.W - out
        self.top, self.bottom = gr['top'], self.H - gr['bottom']
        self.w = self.x1 - self.x0

    @property
    def outer_x(self):
        return self.x0 if self.side == 'L' else self.x1

    def col(self, i, span, cols=6, gutter=5.0):
        cw = (self.w - (cols - 1) * gutter) / cols
        return self.x0 + i * (cw + gutter), span * cw + (span - 1) * gutter


def _caps_track(ds, s, track):
    """Прописные антиквой — с разрядкой, иначе буквы слипаются."""
    if s.upper() == s and any(ch.isalpha() for ch in s):
        return 0.045 if ds['display'].startswith('serif') else 0.01
    return track


def title(sl, ds, g, s, x, y, w, h, size=None, size_min=18, color=None, role='title', lead=1.08):
    size = size or ds['scale']['h1']
    return text(sl, s, x, y, w, h, ds['display'], size, color or g.ink, lead,
                _caps_track(ds, s, ds['display_track']), size_min, 'l', role)


def para(sl, ds, g, s, x, y, w, h=200, size=None, color=None, font=None, role='body', lead=None):
    size = size or ds['scale']['body']
    return text(sl, s, x, y, w, h, font or ds['body'], size, color or g.ink,
                lead or ds['lead_k']['body'], 0.0, size, 'l', role)


def small(sl, ds, g, s, x, y, w=120, color=None, align='l', role='label', size=None):
    size = size or ds['scale']['label']
    return text(sl, s, x, y, w, 30, ds['label'], size, color or g.muted, 1.25, 0.08,
                size, align, role)


def ground(sl, ds, g, X, x0=0, w=None):
    sl.add(Rect(X + x0, 0, (w or ds['W']) + (0.4 if X == 0 else 0), ds['H'], g.bg, role='ground'))


def folio(sl, ds, g, pg, n):
    """Номер полосы — снаружи внизу. Единственное, что движок добавляет сам.
    На снимке — на вкладке, как подписи."""
    al = 'r' if pg.side != 'L' else 'l'
    tab(sl, ds, g, pg, f'{n:02d}', al, pg.bottom + 3.2, 'folio', size=7, color=g.muted)


def logo(sl, ds, pg, spec, w=30, y=None, color=None, x=None):
    path = spec.get('_logo')
    if not path:
        return 0
    x = x if x is not None else pg.x1 - w
    shape, h = vector.place(path, x, y if y is not None else pg.top, w, color or ds['ground']['dark'].accent)
    sl.add(shape)
    return h


def bullets(sl, ds, g, items, x, y, w, size=None, gap=3.2, rule=True, font=None):
    """Пункты: маркер-квадрат акцентом, волосяная линейка между пунктами.
    Номера не добавляем — в оригинале их нет."""
    size = size or ds['scale']['body'] + 1
    yy = y
    for i, it in enumerate(items):
        if rule:
            sl.add(Line(x, yy, x + w, yy, g.line, 0.4))
        yy += gap
        sl.add(Rect(x, yy + size * PT * 0.32, 1.6, 1.6, g.accent, role='marker'))
        t = text(sl, it, x + 6, yy, w - 6, 40, font or ds['body'], size, g.ink, 1.3, 0.0,
                 size, 'l', 'item')
        yy = t.y + t.h + gap
    if rule and items:
        sl.add(Line(x, yy, x + w, yy, g.line, 0.4))
    return yy


def photos_block(sl, items, x, y, w, h, vertical=None):
    """1–3 снимка в прямоугольнике: ряд или столбец, между ними — фон."""
    n = len(items)
    if not n:
        return
    vertical = (h > w * 0.9) if vertical is None else vertical
    if vertical:
        hh = (h - GAP * (n - 1)) / n
        for i, it in enumerate(items):
            p, f = _pf(it)
            sl.add(Image(p, x, y + i * (hh + GAP), w, hh, f))
    else:
        ww = (w - GAP * (n - 1)) / n
        for i, it in enumerate(items):
            p, f = _pf(it)
            sl.add(Image(p, x + i * (ww + GAP), y, ww, h, f))


def _shade_under(sl, box, amount=0.62, depth=32.0):
    """Снимки под мелким светлым текстом затемняются снизу — в пикселях."""
    x0, y0, x1, y1 = box
    for e in sl.items:
        if isinstance(e, Image) and e.x < x1 and e.x + e.w > x0 and e.y < y1 and e.y + e.h > y0:
            ext = min(0.6, (e.y + e.h - y0 + depth * 0.4) / e.h)
            add = dict(side='bottom', to=(20, 18, 36), amount=amount, extent=ext)
            cur = [e.shade] if isinstance(e.shade, dict) else list(e.shade or [])
            if add not in cur:
                e.shade = cur + [add]


def tab(sl, ds, g, pg, s, align, y_hint, role, size=7.5, color=None):
    """Мелкий текст на снимке — на «вкладке» цвета фона полосы, растущей от
    нижнего края кадра. Непрозрачно, читается на любом снимке."""
    px, pt_, pb = 3.0, 2.4, 2.4
    probe_x = pg.x1 - 4 if align == 'r' else pg.x0 + 4
    img = [e for e in sl.items if isinstance(e, Image) and e.x <= probe_x <= e.x + e.w
           and e.y <= y_hint <= e.y + e.h]
    if not img:
        return small(sl, ds, g, s, pg.x0, y_hint, pg.w, color=color or g.muted, align=align,
                     size=size, role=role)
    bottom = min(max(e.y + e.h for e in img), pg.H)
    if bottom >= pg.H - 0.01:
        pb = 6.0                              # у обреза текст остаётся в безопасном поле (5 мм)
    t = small(sl, ds, g, s, pg.x0, 0, pg.w, color=color or g.ink, align=align, size=size, role=role)
    t.y = bottom - pb - t.h
    x0, y0, x1, y1 = t.bbox()
    plate = Rect(x0 - px, y0 - pt_, x1 - x0 + 2 * px, bottom - (y0 - pt_), g.bg, role='plate')
    sl.items.insert(sl.items.index(t), plate)
    return t


def caption(sl, ds, g, pg, s, y_bottom, on_photo=True):
    """Подпись к снимку — со стороны корешка (снаружи стоит номер полосы)."""
    al = 'r' if pg.side == 'L' else 'l'
    return tab(sl, ds, g, pg, s, al, y_bottom - 4, 'caption')


def _pf(it):
    if isinstance(it, dict):
        return it['path'], tuple(it.get('focus', (0.5, 0.5)))
    return it, (0.5, 0.5)


def _bleed_x(pg):
    """Края полосы для снимков в вылет: снаружи — за обрез, у корешка — до корешка."""
    return pg.X, pg.X + pg.W


# ------------------------------------------------------------ полосы

def p_cover(sl, ds, c, pg, spec):
    g = ds['ground']['dark']
    ground(sl, ds, g, pg.X)
    sl.add(Image(c['image'], pg.X, 0, pg.W, pg.H, tuple(c.get('focus', (0.5, 0.5))),
                 shade=dict(side='bottom', to=g.bg, amount=0.85, extent=0.42)))
    logo(sl, ds, pg, spec, w=46, y=pg.top + 2)
    t = title(sl, ds, g, c['title'], pg.x0, 0, pg.w, 90, size=50, size_min=30, role='hero', lead=1.05)
    tag = c.get('tag')
    yb = pg.bottom - (12 if tag else 0)
    t.y = yb - t.h
    sl.add(Line(pg.x0, t.y - 9, pg.x0 + 22, t.y - 9, g.accent, 1.6))
    if tag:
        text(sl, tag, pg.x0, yb + 3.5, 60, 10, ds['strong'], 12, g.accent, 1.0, 0.04,
             role='tag', max_lines=1)
    return g


def p_back(sl, ds, c, pg, spec):
    g = ds['ground']['dark']
    ground(sl, ds, g, pg.X)
    sl.add(Image(c['image'], pg.X, 0, pg.W, pg.H, tuple(c.get('focus', (0.5, 0.5)))))
    return g


def p_numbered(sl, ds, c, pg, spec):
    """Фонд: знак, вводная фраза, миссии, адрес."""
    g = ds['ground'][c.get('ground', 'dark')]
    ground(sl, ds, g, pg.X)
    y = pg.top + 4
    if c.get('emblem'):
        e = c['emblem']
        sh = 26
        sl.add(Image(e['image'], pg.x0, y, sh * e.get('ar', 0.88), sh, role='emblem'))
        if e.get('wordmark'):
            shape, hh = vector.place(e['wordmark'], pg.x0 + sh * e.get('ar', 0.88) + 6,
                                     y + (sh - 0.377 * 62) / 2, 62, g.ink)
            sl.add(shape)
        y += sh + 16
    t = title(sl, ds, g, c['lead'], pg.x0, y, pg.w * 0.92, 60, size=19, size_min=14,
              role='lead', lead=1.22)
    y = t.y + t.h + 16
    if c.get('items_label'):
        small(sl, ds, g, c['items_label'], pg.x0, y, color=g.accent_text(9), size=8)
        y += 9
    lx, lw = pg.col(0, 2)
    tx, tw = pg.col(2, 4)
    for it in c['items']:
        sl.add(Line(pg.x0, y, pg.x1, y, g.line, 0.4))
        small(sl, ds, g, it['label'], lx, y + 4, lw, color=g.accent_text(9), size=8)
        b = para(sl, ds, g, it['text'], tx, y + 3.4, tw, size=ds['scale']['body'] + 0.5)
        y = b.y + b.h + 6
    sl.add(Line(pg.x0, y, pg.x1, y, g.line, 0.4))
    if c.get('url'):
        text(sl, c['url'], pg.x0, pg.bottom - 6, pg.w, 8, ds['strong'], 10, g.accent_text(10),
             1.0, 0.0, role='url', max_lines=1)
    return g


def p_directions(sl, ds, c, pg, spec):
    """Три направления: крупные номера антиквой акцентом."""
    g = ds['ground'][c.get('ground', 'dark')]
    ground(sl, ds, g, pg.X)
    logo(sl, ds, pg, spec)
    t = title(sl, ds, g, c['title'], pg.x0, pg.top + 34, pg.w, 40, size=30)
    n = len(c['items'])
    y0 = max(t.y + t.h + 26, pg.H * 0.36)
    step = (pg.bottom - 10 - y0) / n
    for i, it in enumerate(c['items']):
        y = y0 + i * step
        sl.add(Line(pg.x0, y, pg.x1, y, g.line, 0.4))
        text(sl, it['num'], pg.x0 - 1, y + 6, 60, 40, ds['number'], 54, g.accent_text(54), 1.0,
             -0.02, role='num', max_lines=1)
        title(sl, ds, g, it['text'], pg.col(2, 4)[0], y + 9, pg.col(2, 4)[1], 30, size=17,
              size_min=12, role='item', lead=1.2)
    return g


def p_mission_chart(sl, ds, c, pg, spec):
    g = ds['ground'][c.get('ground', 'paper')]
    ground(sl, ds, g, pg.X)
    y = pg.top + 6
    for blk in c['blocks']:
        h = title(sl, ds, g, blk['title'], pg.x0, y, pg.w, 20, size=15, size_min=12, role='h2')
        y = h.y + h.h + 5
        for ptxt in blk['paras']:
            b = para(sl, ds, g, ptxt, pg.col(1, 5)[0], y, pg.col(1, 5)[1])
            y = b.y + b.h + 3.5
        y += 7
    ch = c['chart']
    h = title(sl, ds, g, ch['title'], pg.x0, y + 4, pg.w, 24, size=15, size_min=12, role='h2')
    top = h.y + h.h + 16
    base = pg.bottom - 12
    data = ch['data']
    n = len(data)
    gap = 3.0
    bw = (pg.w - gap * (n - 1)) / n
    vmax = max(d['value'] for d in data)
    rest = mix(g.bg, g.ink, 0.16)
    for i, d in enumerate(data):
        hi = i == n - 1
        bh = (base - top - 14) * d['value'] / vmax
        bx = pg.x0 + i * (bw + gap)
        sl.add(Rect(bx, base - bh, bw, bh, g.accent if hi else rest, role='bar'))
        v = text(sl, d['display'], bx - 2, base - bh - 10.5, bw + 4, 8, ds['strong'] if not hi else ds['number'],
                 8.5 if not hi else 11, g.ink, 1.0, -0.01, 7, 'c', 'bar-value', 1)
        text(sl, d['unit'], bx - 2, base - bh - 4.8, bw + 4, 6, ds['body'], 7, g.muted, 1.0, 0,
             7, 'c', 'bar-unit', 1)
        text(sl, d['label'], bx - 2, base + 3, bw + 4, 6, ds['body'], 7.5, g.muted, 1.0, 0, 7,
             'c', 'axis', 1)
    sl.add(Line(pg.x0, base, pg.x1, base, g.line, 0.5))
    return g


def p_figures(sl, ds, c, pg, spec):
    """Кадры и техника: итоги сверху крупно (точка входа), ниже — две
    колонки строк «число — что»."""
    g = ds['ground'][c.get('ground', 'paper')]
    ground(sl, ds, g, pg.X)
    logo(sl, ds, pg, spec)
    tot = c['totals']
    y = pg.top + 34
    v = text(sl, tot[0]['value'], pg.x0 - 1.5, y, pg.w * 0.6, 50, ds['number'], 96, g.accent_text(96),
             1.0, -0.035, 40, 'l', 'hero', 1)
    cap = para(sl, ds, g, tot[0]['label'], pg.x0, v.y + v.h + 1, 60, size=10, color=g.ink)
    rx = pg.x0 + pg.w * 0.52
    yy = y + 6
    for t in tot[1:]:
        vv = text(sl, t['value'], rx, yy, pg.x1 - rx, 20, ds['number'], 34, g.ink, 1.0, -0.02, 20,
                  'l', 'stat', 1)
        cc = para(sl, ds, g, t['label'], rx, vv.y + vv.h + 1, pg.x1 - rx, size=9, color=g.muted)
        yy = cc.y + cc.h + 9
    y0 = max(cap.y + cap.h, yy) + 16
    cols = c['columns']
    cw = (pg.w - 8) / len(cols)
    for ci, rows in enumerate(cols):
        x = pg.x0 + ci * (cw + 8)
        y = y0
        for r in rows:
            sl.add(Line(x, y, x + cw, y, g.line, 0.4))
            if r.get('num'):
                text(sl, r['num'], x, y + 3.4, 20, 10, ds['number'], 17, g.ink, 1.0, -0.01,
                     role='num', max_lines=1)
            b = para(sl, ds, g, r['label'], x + (18 if r.get('num') else 0), y + 4.8,
                     cw - (18 if r.get('num') else 0), size=9, color=g.muted, lead=1.3)
            y = max(y + 12.5, b.y + b.h + 4)
        sl.add(Line(x, y, x + cw, y, g.line, 0.4))
    return g


def p_stats(sl, ds, c, pg, spec):
    """Компания в цифрах: первая цифра — герой во всю ширину, остальные 2×2+."""
    g = ds['ground'][c.get('ground', 'dark')]
    ground(sl, ds, g, pg.X)
    items = c['items']
    y = pg.top + 30
    h0 = items[0]
    v = text(sl, h0['value'], pg.x0 - 1, y, pg.w, 40, ds['number'], 72, g.accent_text(72), 1.0,
             -0.03, 40, 'l', 'hero', 1)
    cap = para(sl, ds, g, h0['label'], pg.x0, v.y + v.h + 2, pg.w * 0.7, size=10.5)
    rest = items[1:]
    rows = math.ceil(len(rest) / 2)
    y0 = cap.y + cap.h + 22
    rh = (pg.bottom - 6 - y0) / rows
    cw = (pg.w - 8) / 2
    for i, it in enumerate(rest):
        x = pg.x0 + (i % 2) * (cw + 8)
        yy = y0 + (i // 2) * rh
        sl.add(Line(x, yy, x + cw, yy, g.line, 0.4))
        vv = text(sl, it['value'], x, yy + 6, cw, 20, ds['number'], 32, g.ink, 1.0, -0.02, 20,
                  'l', 'stat', 1)
        if it.get('label'):
            para(sl, ds, g, it['label'], x, vv.y + vv.h + 2.5, cw * 0.92, size=9, color=g.muted)
    return g


def p_list(sl, ds, c, pg, spec):
    g = ds['ground'][c.get('ground', 'dark')]
    ground(sl, ds, g, pg.X)
    logo(sl, ds, pg, spec)
    t = title(sl, ds, g, c['title'], pg.x0, pg.top + 34, pg.w, 50, size=26)
    y = max(t.y + t.h + 22, pg.H * 0.36)
    bullets(sl, ds, g, c['items'], pg.x0, y, pg.w, size=11.5, gap=3.6)
    return g


def p_service(sl, ds, c, pg, spec):
    """Направление работ: заголовок, пункты или текст, снимок крупно.
    mode: bottom — снимок снизу во всю ширину полосы и в вылет;
          top    — снимок сверху, текст снизу;
          full   — снимок на всю полосу, текст на впечённом затемнении."""
    g = ds['ground'][c.get('ground', 'dark')]
    mode = c.get('mode', 'bottom')
    ims = c.get('photos', [])
    bx0, bx1 = _bleed_x(pg)
    ground(sl, ds, g, pg.X)
    if mode == 'full' and ims:
        p, f = _pf(ims[0])
        sl.add(Image(p, bx0, 0, bx1 - bx0, pg.H, f,
                     shade=dict(side='top', to=g.bg, amount=0.97, extent=c.get('shade', 0.62))))
    if c.get('logo', pg.side != 'L'):
        logo(sl, ds, pg, spec)
    tw = pg.w * c.get('title_w', 0.86)
    textonly = not ims
    ty = (pg.H * 0.24 if textonly else pg.top + 30) if mode != 'top' else 0
    t = title(sl, ds, g, c['title'], pg.x0, ty, tw, 60,
              size=c.get('title_size', 34 if textonly else 27), size_min=18)
    if mode == 'top':
        ph = pg.H * c.get('photo_h', 0.50)
        photos_block(sl, ims, bx0, 0, bx1 - bx0, ph, vertical=False)
        t.y = ph + 14
    y = t.y + t.h + 12
    if c.get('items'):
        y = bullets(sl, ds, g, c['items'], pg.x0, y, pg.w * 0.82, size=10, gap=2.6)
        y += 6
    for ptxt in c.get('paras', []):
        b = para(sl, ds, g, ptxt, pg.x0, y, pg.w * 0.82, size=c.get('para_size', 10))
        y = b.y + b.h + 4
    if c.get('note'):                 # заказчик и т. п. — подписью
        for i, ln in enumerate(c['note']):
            text(sl, ln, pg.x0, y + 4 + i * 4.6, pg.w, 6, ds['strong'] if i else ds['body'], 8.5,
                 g.muted if i == 0 else g.ink, 1.2, 0, 8, 'l', 'note', 1)
        y += 4 + 4.6 * len(c['note'])
    if mode == 'bottom' and ims:
        py = max(y + 14, pg.H * c.get('photo_top', 0.46))
        photos_block(sl, ims, bx0, py, bx1 - bx0, pg.H - py, vertical=c.get('vertical', False))
    if c.get('caption'):
        caption(sl, ds, g, pg, c['caption'], pg.bottom - 3, on_photo=mode != 'top')
    return g


def p_photos(sl, ds, c, pg, spec):
    """Полоса-снимки: 1–2 кадра во всю полосу, в вылет."""
    g = ds['ground'][c.get('ground', 'dark')]
    ground(sl, ds, g, pg.X)
    bx0, bx1 = _bleed_x(pg)
    ims = c['photos']
    split = c.get('split')
    if len(ims) == 2 and split:
        h0 = pg.H * split
        p, f = _pf(ims[0]); sl.add(Image(p, bx0, 0, bx1 - bx0, h0 - GAP / 2, f))
        p, f = _pf(ims[1]); sl.add(Image(p, bx0, h0 + GAP / 2, bx1 - bx0, pg.H - h0 - GAP / 2, f))
    else:
        photos_block(sl, ims, bx0, 0, bx1 - bx0, pg.H, vertical=True)
    if c.get('captions'):
        for cap in c['captions']:
            small(sl, ds, g, cap['text'], pg.x0, cap['y'], pg.w, color=(250, 250, 248), size=7.5,
                  role='caption')
    if pg.side != 'L' and c.get('logo', True):
        logo(sl, ds, pg, spec)
    return g


def p_civil(sl, ds, c, pg, spec):
    """Гражданское: заголовок, текст, сетка домов с подписями сроков."""
    g = ds['ground'][c.get('ground', 'paper')]
    ground(sl, ds, g, pg.X)
    bx0, bx1 = _bleed_x(pg)
    t = title(sl, ds, g, c['title'], pg.x0, pg.top + 30, pg.w * 0.86, 46, size=27)
    y = t.y + t.h + 12
    for ptxt in c.get('paras', []):
        b = para(sl, ds, g, ptxt, pg.x0, y, pg.w * 0.82, size=10)
        y = b.y + b.h + 4
    top = max(y + 14, pg.H * 0.40)
    rows = c['rows']                      # [{photos:[..], caption}]
    hgt = (pg.H - top - GAP * (len(rows) - 1)) / len(rows)
    for i, r in enumerate(rows):
        yy = top + i * (hgt + GAP)
        photos_block(sl, r['photos'], bx0, yy, bx1 - bx0, hgt, vertical=False)
        if r.get('caption'):
            caption(sl, ds, g, pg, r['caption'], min(yy + hgt - 4, pg.bottom - 3))
    return g


def p_map(sl, ds, c, pg, spec):
    """Название раздела крупно; карта — общая на разворот (рисует spread)."""
    g = ds['ground'][c.get('ground', 'dark2')]
    ground(sl, ds, g, pg.X)
    title(sl, ds, g, c['title'], pg.x0, pg.top + 30, pg.w, 60, size=38, role='hero', lead=1.05)
    return g


def p_regions(sl, ds, c, pg, spec):
    g = ds['ground'][c.get('ground', 'dark2')]
    ground(sl, ds, g, pg.X)
    logo(sl, ds, pg, spec)
    items = c['items']
    half = math.ceil(len(items) / 2)
    cw = (pg.w - 8) / 2
    y0 = pg.top + 30
    for ci, chunk in enumerate((items[:half], items[half:])):
        x = pg.x0 + ci * (cw + 8)
        y = y0
        for it in chunk:
            sl.add(Rect(x, y + 1.6, 1.4, 1.4, g.accent, role='marker'))
            t = text(sl, it, x + 4.5, y, cw - 4.5, 10, ds['body'], 9, g.ink, 1.2, 0, 8, 'l', 'item', 1)
            y += 5.6
    return g


def p_logos(sl, ds, c, pg, spec):
    """Партнёры: карточки одного размера — логотипы так и сданы, на белом."""
    g = ds['ground'][c.get('ground', 'dark')]
    ground(sl, ds, g, pg.X)
    ims = c['logos']
    cols = 3
    rows = math.ceil(len(ims) / cols)
    gap = 5.0
    cw = (pg.w - gap * (cols - 1)) / cols
    ch = cw * 208 / 327
    total = rows * ch + (rows - 1) * gap
    y0 = (pg.H - total) / 2 + 4
    for i, p in enumerate(ims):
        x = pg.x0 + (i % cols) * (cw + gap)
        y = y0 + (i // cols) * (ch + gap)
        sl.add(Image(p, x, y, cw, ch, (0.5, 0.5), role='card'))
    return g


def p_credentials(sl, ds, c, pg, spec):
    g = ds['ground'][c.get('ground', 'dark')]
    ground(sl, ds, g, pg.X)
    logo(sl, ds, pg, spec)
    y = pg.H * 0.36
    y = bullets(sl, ds, g, c['items'], pg.x0, y, pg.w, size=10.5, gap=3.4)
    yy = pg.bottom - 6 - 6.5 * len(c['contacts'])
    for i, ct in enumerate(c['contacts']):
        small(sl, ds, g, ct['label'], pg.x0, yy + i * 6.5 + 0.8, 20, size=7.5)
        text(sl, ct['value'], pg.x0 + 18, yy + i * 6.5, pg.w - 18, 6, ds['strong'], 10.5,
             g.accent_text(10.5), 1.0, 0, 9, 'l', 'contact', 1)
    return g


PAGES = dict(cover=p_cover, back=p_back, numbered=p_numbered, directions=p_directions,
             mission_chart=p_mission_chart, figures=p_figures, stats=p_stats, list=p_list,
             service=p_service, photos=p_photos, civil=p_civil, map=p_map, regions=p_regions,
             logos=p_logos, credentials=p_credentials)


# ------------------------------------------------------------ развороты

def _spreads(n_pages):
    """Обложка одна, далее пары (2,3)…(30,31), задняя обложка одна."""
    out = [(1,)]
    p = 2
    while p < n_pages:
        out.append((p, p + 1) if p + 1 < n_pages else (p,))
        p += 2
    out.append((n_pages,))
    return out


def _map(sl, ds, spec, g, X, W):
    """Карта — в геометрии оригинала: она снята с полосы 28 и занимает её
    по ширине, восточный край уходит к корешку, как в утверждённой версии."""
    from .model import Shape
    m = spec.get('_map')
    if not m:
        return
    country, regions = m
    k = W
    dy = spec.get('map_offset_mm', 0.0)      # сдвиг вниз, чтобы карта не легла под заголовок
    tr = lambda cs: [[(X + x * k, y * k + dy) for x, y in c] for c in cs]
    sl.add(Shape(tr(country), mix(g.bg, g.ink, 0.10), 'map'))
    sl.add(Shape(tr(regions), mix(g.bg, g.accent, 0.80), 'map'))


def build(ds, spec):
    pages = {p['n']: p for p in spec['pages']}
    n_pages = max(pages)
    out = []
    W, H = ds['W'], ds['H']
    for k, grp in enumerate(_spreads(n_pages), 1):
        sl = Slide(k, '+'.join(pages[p]['layout'] for p in grp), None)
        sl.w, sl.h, sl.pages = W * len(grp), H, grp
        grounds = []
        for i, pn in enumerate(grp):
            c = pages[pn]
            side = 'S' if len(grp) == 1 else ('L' if i == 0 else 'R')
            pg = Pg(ds, i * W, side)
            g = PAGES[c['layout']](sl, ds, c, pg, spec)
            grounds.append(g)
            if c['layout'] not in ('cover', 'back'):
                folio(sl, ds, g, pg, pn)
            if c.get('notes'):
                sl.notes += c['notes'] + '\n'
        for i, pn in enumerate(grp):
            if pages[pn]['layout'] == 'map':
                _map(sl, ds, spec, grounds[i], i * W, W)
                _behind_text(sl, i * W)
        sl.ground = grounds[0]
        loud = any(pages[p]['layout'] in ('cover', 'directions', 'back') for p in grp)
        sl.arc_req = dict(strength='loud' if loud else 'quiet', edge='right', col=None, seed=None,
                          avoid_images=True, optional=True)
        place_arc(sl, ds)
        for t in sl.items:
            if isinstance(t, Text):
                miss = fonts.missing_glyphs(''.join(t.lines), t.font)
                if miss:
                    sl.warnings.append(f'в шрифте {t.font} нет знаков: {"".join(miss)}')
        out.append(sl)
    return out


def _behind_text(sl, X):
    """Карта — под текстом своей полосы: сразу за её фоном."""
    from .model import Shape
    maps = [e for e in sl.items if isinstance(e, Shape) and e.role == 'map']
    rest = [e for e in sl.items if not (isinstance(e, Shape) and e.role == 'map')]
    idx = next(i for i, e in enumerate(rest)
               if isinstance(e, Rect) and e.role == 'ground' and abs(e.x - X) < 0.01) + 1
    sl.items[:] = rest[:idx] + maps + rest[idx:]
