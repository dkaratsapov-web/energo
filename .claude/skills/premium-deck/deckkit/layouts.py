# -*- coding: utf-8 -*-
"""Композиции слайдов.

Каждая функция получает содержание слайда из брифа и раскладывает его по
сетке концепции. Правила, которые держат все композиции:
  * одна точка входа: самый крупный элемент — один;
  * асимметрия по умолчанию, центр — никогда «просто так»;
  * текст не мельче подписи концепции, тело — не длиннее 5 строк;
  * мотив присутствует на каждом слайде, но в разной роли и масштабе;
  * никакой прозрачности — только смешанные цвета и впечённое затемнение.
"""
import math, random
from .model import Rect, Line, Poly, Dot, Image, Text, Slide, PT
from .tokens import col_x, mix, contrast
from . import fonts

MM = 1 / PT          # pt в мм


# ---------------------------------------------------------------- текст

def _case(ds, s):
    return s.upper() if ds['display_case'] == 'upper' else s


def text(sl, s, x, y, w, h, font, size, color, leading=1.38, track=0.0,
         size_min=None, align='l', role='body', max_lines=None, case=None):
    s = case(s) if case else s
    lines, size, ok = fonts.fit(s, font, w * MM, h * MM, size, size_min or size,
                                leading, track, step=1.0, max_lines=max_lines)
    t = Text(x, y, w, lines, font, size, color, leading, track, align, role,
             box_h=h, fit_ok=ok)
    if not ok:
        sl.warnings.append(f'текст не влез в отведённый блок: «{s[:40]}…»')
    sl.add(t)
    return t


def headline(sl, ds, g, s, x, y, w, h, size=None, size_min=None, color=None,
             role='title', align='l', max_lines=None):
    size = size or ds['scale']['h1']
    return text(sl, s, x, y, w, h, ds['display'], size, color or g.ink,
                ds['lead_k']['display'], ds['display_track'],
                size_min or max(26, size * 0.55), align, role, max_lines,
                case=lambda v: _case(ds, v))


def body(sl, ds, g, s, x, y, w, h, size=None, color=None, font=None, role='body',
         size_min=None, max_lines=None):
    size = size or ds['scale']['body']
    return text(sl, s, x, y, w, h, font or ds['body'], size, color or g.ink,
                ds['lead_k']['body'], 0.0, size_min or max(14, size - 3), 'l', role,
                max_lines)


def label(sl, ds, g, s, x, y, w=120, color=None, align='l', role='label'):
    return text(sl, s.upper(), x, y, w, 8, ds['label'], ds['scale']['label'],
                color or g.muted, 1.2, 0.12, align=align, role=role, max_lines=1)


def eyebrow(sl, ds, g, s, x, y, w=150):
    """Надзаголовок. В концепции A перед ним — короткая линейка акцентом."""
    if not s:
        return y
    if ds['motif'] == 'rule':
        sl.add(Line(x, y + 1.6, x + 9, y + 1.6, g.accent, 2.0))
        label(sl, ds, g, s, x + 13, y, w - 13)
    else:
        label(sl, ds, g, s, x, y, w, color=g.accent_text(ds['scale']['label'])
              if ds['motif'] == 'block' else g.muted)
    return y + 9


# ---------------------------------------------------------------- мотив

def arc_pts(cx, cy, r, a0, a1, n=240):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def clip_runs(pts, x0, y0, x1, y1):
    """Части ломаной внутри прямоугольника (точки снаружи отбрасываем)."""
    runs, cur = [], []
    for p in pts:
        if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
            cur.append(p)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) > 1]


def motif(sl, ds, g, n, total, strength='quiet', seed=None, edge='right', col=None):
    """Подпись колоды: линейка-прогресс (A), дуга (B), поле (C)."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    rnd = random.Random(seed if seed is not None else n * 7919)
    m = ds['motif']
    if m == 'rule':
        # линейка внизу; точка показывает место слайда в колоде
        y = H - gr['bottom'] - 6
        sl.add(Line(gr['margin'], y, W - gr['margin'], y, g.line, 0.5))
        px = gr['margin'] + (W - 2 * gr['margin']) * (n - 1) / max(total - 1, 1)
        sl.add(Dot(px, y, 1.4, g.accent))
    elif m == 'arc':
        # дугу ставим в последнюю очередь, когда известен весь текст слайда
        sl.arc_req = dict(strength=strength, edge=edge, col=col, seed=seed)
    elif m == 'block':
        acc = g.accent if g.name != 'accent' else mix(g.bg, g.ink, 0.18)
        if strength == 'loud':
            return
        k = n % 3
        if k == 0:
            sl.add(Rect(W - 34, 0, 34, 7, acc))
        elif k == 1:
            sl.add(Rect(0, H - 7, 46, 7, acc))
        else:
            sl.add(Rect(W - 7, H * 0.38, 7, H * 0.62, acc))


def _arc_try(ds, g, n, strength, edge, col, rnd, k):
    W, H = ds['W'], ds['H']
    col = col or mix(g.bg, g.ink, 0.22 if strength == 'quiet' else 0.34)
    if strength == 'loud':
        r = H * rnd.uniform(0.9, 1.3)
        cx = W * rnd.uniform(0.62, 1.05); cy = H * rnd.uniform(0.55, 1.25)
    else:
        r = H * rnd.uniform(0.18 if k > 30 else 0.28, 0.44)
        e = edge if k < 20 else ('left' if edge == 'right' else 'right')
        cx = W + r * rnd.uniform(0.2, 0.5) if e == 'right' else -r * rnd.uniform(0.2, 0.5)
        cy = -r * rnd.uniform(0.2, 0.5) if (n + k) % 2 else H + r * rnd.uniform(0.2, 0.5)
    b = 6.0
    els = [Poly(run, stroke=col, width=0.9 if strength == 'quiet' else 1.2, role='arc')
           for run in clip_runs(arc_pts(cx, cy, r, 0, 360, 720), -b, -b, W + b, H + b)]
    if strength == 'loud':
        for _ in range(12):
            a = math.radians(rnd.uniform(180, 270))
            px, py = cx + r * math.cos(a), cy + r * math.sin(a)
            if 8 < px < W - 8 and 8 < py < H - 8:
                els.append(Dot(px, py, 1.8, g.accent, role='arc'))
                break
    return els


def place_arc(sl, ds):
    """Дуга, которая не задевает ни одной строки и ни одного столбца данных."""
    req = getattr(sl, 'arc_req', None)
    if not req:
        return
    g = sl.ground
    pad = 3.0
    obst = []
    for el in sl.items:
        if isinstance(el, Text) and el.role != 'ghost':
            x0, y0, x1, y1 = el.bbox()
            obst.append((x0 - pad, y0 - pad, x1 + pad, y1 + pad))
        elif isinstance(el, Rect) and el.role == 'bar':
            obst.append((el.x - pad, el.y - pad, el.x + el.w + pad, el.y + el.h + pad))
    def hits(els):
        for e in els:
            pts = e.pts if isinstance(e, Poly) else [(e.cx, e.cy)]
            for x, y in pts:
                for a, b, c, d in obst:
                    if a <= x <= c and b <= y <= d:
                        return True
        return False
    rnd = random.Random(req['seed'] if req['seed'] is not None else sl.n * 7919)
    chosen = None
    for k in range(60):
        els = _arc_try(ds, g, sl.n, req['strength'], req['edge'], req['col'], rnd, k)
        if els and not hits(els):
            chosen = els
            break
    if not chosen:
        sl.warnings.append('мотив-дуга не нашла места без пересечения с текстом — пропущена')
        return
    # под текст: сразу после фона и снимков
    idx = 0
    for i, el in enumerate(sl.items):
        if isinstance(el, Image) or (isinstance(el, Rect) and el.role == 'ground'):
            idx = i + 1
    sl.items[idx:idx] = chosen


def chrome(sl, ds, g, n, total, deck, section=''):
    """Фолио: раздел слева, номер справа. Мелко, приглушённо, на одной линии."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    y = H - gr['bottom'] - 3.2
    label(sl, ds, g, section or deck, gr['margin'], y, 160, role='folio')
    label(sl, ds, g, f'{n:02d} / {total:02d}', W - gr['margin'] - 40, y, 40,
          align='r', role='folio')


def ground_rect(sl, ds, g):
    sl.add(Rect(0, 0, ds['W'], ds['H'], g.bg, role='ground'))


def img(sl, path, x, y, w, h, focus=(0.5, 0.5), shade=None):
    return sl.add(Image(path, x, y, w, h, tuple(focus), shade))


# ---------------------------------------------------------------- композиции

def cover(sl, ds, c, ctx):
    W, H, gr = ds['W'], ds['H'], ds['grid']
    m = gr['margin']
    if c.get('image') and ds['motif'] != 'block':
        g = ds['ground']['dark']
        ground_rect(sl, ds, g)
        # кадр на 62% ширины справа, текст на тёмном поле слева
        ix = W * 0.40
        img(sl, c['image'], ix, 0, W - ix, H, c.get('focus', (0.5, 0.5)),
            shade=dict(side='left', to=g.bg, amount=1.0, extent=0.35))
        if ds['motif'] == 'arc':      # тонкая светлая дуга по кадру
            motif(sl, ds, g, ctx['n'], ctx['total'], 'quiet', edge='right',
                  col=mix(g.ink, g.bg, 0.15))
        tw = ix - 4
    else:
        g = ds['ground']['accent' if ds['motif'] == 'block' else 'dark']
        ground_rect(sl, ds, g)
        if c.get('image'):
            img(sl, c['image'], W * 0.58, 0, W * 0.42, H, c.get('focus', (0.5, 0.5)))
            tw = W * 0.50
        else:
            tw = W * 0.78
        motif(sl, ds, g, ctx['n'], ctx['total'], 'loud')
    sl.ground = g
    label(sl, ds, g, c.get('client', ''), m, gr['top'], 150, color=g.ink)
    y_lab = H - gr['bottom'] - 3.2
    label(sl, ds, g, c.get('date', ''), m, y_lab, 120)
    # заголовок — монумент над подзаголовком; сверху ему оставлено место
    # под имя клиента и надзаголовок, чтобы они не слиплись
    sub = None
    sub_h = 0
    if c.get('subtitle'):
        sub = body(sl, ds, g, c['subtitle'], m, 0, min(tw - m, 165), 34,
                   size=ds['scale']['lead'], color=g.muted, role='lead', max_lines=3, size_min=18)
        sub_h = sub.h + 7
    ceiling = gr['top'] + 10 + (13 if c.get('eyebrow') else 0) + 6
    room = y_lab - 10 - sub_h - ceiling
    t = headline(sl, ds, g, c['title'], m, 0, tw - m, min(room, H * 0.50),
                 size=ds['scale']['h1'] * 1.45, size_min=36, role='hero')
    top = y_lab - 10 - sub_h - t.h
    t.y = top
    if sub:
        sub.y = top + t.h + 7
    if c.get('eyebrow'):
        eyebrow(sl, ds, g, c['eyebrow'], m, top - 13)


def section(sl, ds, c, ctx):
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground'][ds['grounds']['field'] if ds['motif'] != 'block' else 'accent']
    sl.ground = g
    ground_rect(sl, ds, g)
    m = gr['margin']
    num = str(c.get('number', ''))
    if num:
        size = ds['scale']['hero'] * 1.35
        f = ds['number']
        col = mix(g.bg, g.ink, 0.16)
        nw = fonts.width(num, f, size, -0.04) * PT
        sl.add(Text(W - m - nw + 2, H - gr['bottom'] - 12 - fonts.info(f)['ascent'] * size * PT * 0.98,
                    nw + 4, [num], f, size, col, 1.0, -0.04, 'l', 'ghost'))
    motif(sl, ds, g, ctx['n'], ctx['total'], 'loud')
    t = headline(sl, ds, g, c['title'], m, 0, W * 0.55, H * 0.42, size=ds['scale']['h1'] * 1.15)
    t.y = H * 0.56 - t.h
    eyebrow(sl, ds, g, c.get('eyebrow', ''), m, t.y - 13)
    chrome(sl, ds, g, ctx['n'], ctx['total'], ctx['deck'], c.get('folio', ''))


def statement(sl, ds, c, ctx):
    """Одна мысль крупно. Тело — короткое, в узкой колонке справа внизу."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground'][c.get('ground', ds['grounds']['base'])]
    sl.ground = g
    ground_rect(sl, ds, g)
    motif(sl, ds, g, ctx['n'], ctx['total'], 'quiet')
    m = gr['margin']
    y = eyebrow(sl, ds, g, c.get('eyebrow', ''), m, gr['top'])
    x, w = col_x(ds, 0, 10)
    t = headline(sl, ds, g, c['title'], x, y + 6, w, H * 0.48,
                 size=ds['scale']['h1'] * 1.1, role='title')
    if c.get('text'):
        bx, bw = col_x(ds, 7, 5)
        by = max(t.y + t.h + 12, H * 0.60)
        body(sl, ds, g, c['text'], bx, by, bw, H - gr['bottom'] - 14 - by,
             size=ds['scale']['body'] + 1, color=g.muted, max_lines=5)
    chrome(sl, ds, g, ctx['n'], ctx['total'], ctx['deck'], c.get('folio', ''))


def number(sl, ds, c, ctx):
    """Герой-цифра слева во всю высоту, справа — что она значит."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground'][c.get('ground', ds['grounds']['base'])]
    sl.ground = g
    ground_rect(sl, ds, g)
    motif(sl, ds, g, ctx['n'], ctx['total'], 'quiet')
    m = gr['margin']
    y = eyebrow(sl, ds, g, c.get('eyebrow', ''), m, gr['top'])
    hx, hw = col_x(ds, 0, 7)
    val = str(c['value'])
    t = text(sl, val, hx - 1.5, 0, hw, H * 0.6, ds['number'], ds['scale']['hero'],
             g.accent_text(ds['scale']['hero']), 0.9, -0.045, size_min=60,
             role='hero', max_lines=1)
    t.y = H * 0.52 - t.h * 0.5
    if c.get('unit'):
        u = text(sl, c['unit'], hx, t.y + t.h + 2, hw, 14, ds['strong'],
                 ds['scale']['h2'] * 0.75, g.ink, 1.1, -0.01, role='unit', max_lines=1)
    rx, rw = col_x(ds, 8, 4)
    hl = headline(sl, ds, g, c['title'], rx, t.y + 2, rw, H * 0.30,
                  size=ds['scale']['h2'], size_min=20)
    if c.get('text'):
        body(sl, ds, g, c['text'], rx, hl.y + hl.h + 8, rw,
             H - gr['bottom'] - 14 - (hl.y + hl.h + 8), color=g.muted, max_lines=5)
    chrome(sl, ds, g, ctx['n'], ctx['total'], ctx['deck'], c.get('folio', ''))


def split_image(sl, ds, c, ctx):
    """Кадр 58% в вылет, текст в узкой колонке. Сторона чередуется."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground'][c.get('ground', ds['grounds']['base'])]
    sl.ground = g
    ground_rect(sl, ds, g)
    side = c.get('side') or ('right' if ctx['n'] % 2 == 0 else 'left')
    iw = W * 0.58
    if side == 'right':
        img(sl, c['image'], W - iw, 0, iw, H, c.get('focus', (0.5, 0.5)))
        x0, x1 = gr['margin'], W - iw - 12
    else:
        img(sl, c['image'], 0, 0, iw, H, c.get('focus', (0.5, 0.5)))
        x0, x1 = iw + 12, W - gr['margin']
    w = x1 - x0
    if ds['motif'] == 'block':
        sl.add(Rect(W - iw if side == 'right' else iw - 7, H - 34, 7, 34, g.accent))
    elif ds['motif'] == 'arc':
        motif(sl, ds, g, ctx['n'], ctx['total'], 'quiet',
              edge=side, col=mix(g.ink, g.bg, 0.15))     # тонкая светлая дуга по кадру
    y = eyebrow(sl, ds, g, c.get('eyebrow', ''), x0, gr['top'], w)
    t = headline(sl, ds, g, c['title'], x0, y + 6, w, H * 0.30, size=ds['scale']['h1'] * 0.72,
                 size_min=24, max_lines=3)
    yb = t.y + t.h + 10
    if c.get('text'):
        b = body(sl, ds, g, c['text'], x0, yb, w, H * 0.36, max_lines=6)
        yb = b.y + b.h + 8
    floor = H - gr['bottom'] - 12
    for i, p in enumerate(c.get('points', [])[:3]):
        if yb + 13 > floor:
            sl.warnings.append(f'пункт «{p[:30]}» не поместился под текстом — снят')
            break
        sl.add(Line(x0, yb, x0 + w, yb, g.line, 0.5))
        body(sl, ds, g, p, x0, yb + 3.2, w, 12, size=ds['scale']['body'] - 1,
             font=ds['strong'], max_lines=2, role='point')
        yb += 14
    _folio_side(sl, ds, g, ctx, x0, x1, c)


def _folio_side(sl, ds, g, ctx, x0, x1, c):
    H, gr = ds['H'], ds['grid']
    y = H - gr['bottom'] - 3.2
    label(sl, ds, g, c.get('folio', '') or ctx['deck'], x0, y, (x1 - x0) * 0.7, role='folio')
    label(sl, ds, g, f'{ctx["n"]:02d} / {ctx["total"]:02d}', x1 - 30, y, 30, align='r',
          role='folio')
    if ds['motif'] == 'rule':
        yy = y - 2.8
        sl.add(Line(x0, yy, x1, yy, g.line, 0.5))
        px = x0 + (x1 - x0) * (ctx['n'] - 1) / max(ctx['total'] - 1, 1)
        sl.add(Dot(px, yy, 1.4, g.accent))


def full_image(sl, ds, c, ctx):
    """Кадр на весь слайд, заголовок на впечённом затемнении снизу."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground']['dark']
    sl.ground = g
    img(sl, c['image'], 0, 0, W, H, c.get('focus', (0.5, 0.5)),
        shade=dict(side='bottom', to=g.bg, amount=0.96, extent=0.78))
    m = gr['margin']
    x, w = col_x(ds, 0, 8)
    t = headline(sl, ds, g, c['title'], x, 0, w, H * 0.30, size=ds['scale']['h1'] * 0.85)
    yb = H - gr['bottom'] - 14
    if c.get('text'):
        bx, bw = col_x(ds, 8, 4)
        b = body(sl, ds, g, c['text'], bx, 0, bw, 40, color=g.ink, max_lines=4)
        b.y = yb - b.h
    t.y = yb - t.h
    if c.get('eyebrow'):          # по снимку — только светлым, приглушённое теряется
        label(sl, ds, g, c['eyebrow'], m, t.y - 12, color=g.ink)
    if ds['motif'] == 'block':
        sl.add(Rect(0, 0, 7, H * 0.42, g.accent))
    chrome(sl, ds, g, ctx['n'], ctx['total'], ctx['deck'], c.get('folio', ''))


def points(sl, ds, c, ctx):
    """2–4 мысли. Первая — главная и крупнее, остальные — колонкой рядом.
    Не карточки одного размера и не маркированный список."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground'][c.get('ground', ds['grounds']['alt'] if ds['motif'] != 'block' else 'paper')]
    sl.ground = g
    ground_rect(sl, ds, g)
    motif(sl, ds, g, ctx['n'], ctx['total'], 'quiet')
    m = gr['margin']
    y = eyebrow(sl, ds, g, c.get('eyebrow', ''), m, gr['top'])
    tx, tw = col_x(ds, 0, 6)
    t = headline(sl, ds, g, c['title'], tx, y + 6, tw, H * 0.34, size=ds['scale']['h1'] * 0.82)
    items = c['items'][:4]
    top = max(t.y + t.h + 16, H * 0.50)
    bottom = H - gr['bottom'] - 14
    first, rest = items[0], items[1:]
    fx, fw = col_x(ds, 0, 5)
    _item(sl, ds, g, 1, first, fx, top, fw, bottom - top, big=True)
    if rest:
        rx, rw = col_x(ds, 7, 5)
        yy = y + 8
        for i, it in enumerate(rest):
            yy = _item(sl, ds, g, i + 2, it, rx, yy, rw, bottom - yy, big=False) + 6
        if yy - 6 > bottom:
            sl.warnings.append('пункты не уместились по высоте')
    chrome(sl, ds, g, ctx['n'], ctx['total'], ctx['deck'], c.get('folio', ''))


def _item(sl, ds, g, k, it, x, y, w, h, big):
    if isinstance(it, str):
        it = {'title': it}
    sl.add(Line(x, y, x + w, y, g.accent if big else g.line, 1.5 if big else 0.5))
    num = f'{k:02d}'
    nf = ds['strong']
    text(sl, num, x, y + 3.5, 14, 8, nf, ds['scale']['label'] + 1,
         g.accent_text(12) if big else g.muted, 1.2, 0.04, role='index', max_lines=1)
    ix = x + 16
    iw = w - 16
    size = ds['scale']['h2'] * (0.82 if big else 0.62)
    ti = text(sl, it['title'], ix, y + 3, iw, h * 0.5, ds['strong'] if ds['display'] != 'serif'
              else 'serif', size, g.ink, 1.12, -0.01, size_min=17, role='item', max_lines=3)
    if it.get('text'):
        b = body(sl, ds, g, it['text'], ix, ti.y + ti.h + 3, iw, h - (ti.h + 6),
                 size=ds['scale']['body'] - (0 if big else 1), color=g.muted,
                 max_lines=4 if big else 3, size_min=14)
        return b.y + b.h
    return ti.y + ti.h


def stats(sl, ds, c, ctx):
    """Набор цифр: первая — главная (крупнее вдвое), остальные — рядом."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground'][c.get('ground', ds['grounds']['field'] if ds['motif'] != 'block' else 'accent')]
    sl.ground = g
    ground_rect(sl, ds, g)
    motif(sl, ds, g, ctx['n'], ctx['total'], 'quiet')
    m = gr['margin']
    y = eyebrow(sl, ds, g, c.get('eyebrow', ''), m, gr['top'])
    tx, tw = col_x(ds, 0, 7)
    t = headline(sl, ds, g, c['title'], tx, y + 6, tw, H * 0.26, size=ds['scale']['h2'] * 1.15)
    items = c['items'][:5]
    bottom = H - gr['bottom'] - 16
    # главная цифра
    hx, hw = col_x(ds, 0, 6)
    v0 = items[0]
    big = text(sl, str(v0['value']), hx - 1, 0, hw, 60, ds['number'], ds['scale']['hero'] * 0.72,
               g.accent_text(60), 0.9, -0.04, size_min=48, role='hero', max_lines=1)
    cap0 = body(sl, ds, g, v0['label'], hx, 0, hw * 0.8, 16, size=ds['scale']['body'],
                color=g.muted, max_lines=2)
    cap0.y = bottom - cap0.h
    big.y = cap0.y - 4 - big.h
    rest = items[1:]
    if rest:
        rx, rw = col_x(ds, 6, 6)
        cols = 2 if len(rest) > 2 else len(rest)
        cw = (rw - 6 * (cols - 1)) / cols
        rows = math.ceil(len(rest) / cols)
        rh = min(36, (bottom - (t.y + t.h + 14)) / rows)
        for i, it in enumerate(rest):
            cx = rx + (i % cols) * (cw + 6)
            cy = bottom - (rows - i // cols) * rh
            sl.add(Line(cx, cy, cx + cw, cy, g.line, 0.5))
            v = text(sl, str(it['value']), cx, cy + 3, cw, 18, ds['number'],
                     ds['scale']['h2'] * 1.05, g.ink, 1.0, -0.03, size_min=22,
                     role='stat', max_lines=1)
            body(sl, ds, g, it['label'], cx, v.y + v.h + 1.5, cw, rh - v.h - 6,
                 size=ds['scale']['caption'] + 1, color=g.muted, max_lines=2, size_min=12)
    chrome(sl, ds, g, ctx['n'], ctx['total'], ctx['deck'], c.get('folio', ''))


def chart(sl, ds, c, ctx):
    """Столбцы без сетки и легенды: подписи прямо на данных,
    акцент — только у столбца, о котором говорит заголовок."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground'][c.get('ground', ds['grounds']['base'])]
    sl.ground = g
    ground_rect(sl, ds, g)
    motif(sl, ds, g, ctx['n'], ctx['total'], 'quiet', edge='left')
    m = gr['margin']
    y = eyebrow(sl, ds, g, c.get('eyebrow', ''), m, gr['top'])
    tx, tw = col_x(ds, 0, 4)
    t = headline(sl, ds, g, c['title'], tx, y + 6, tw, H * 0.40, size=ds['scale']['h2'] * 1.2,
                 size_min=22)
    if c.get('text'):
        body(sl, ds, g, c['text'], tx, t.y + t.h + 8, tw, H * 0.30, color=g.muted, max_lines=5)
    data = c['data']
    hi = c.get('highlight', len(data) - 1)
    cx, cw = col_x(ds, 5, 7)
    base_y = H - gr['bottom'] - 18
    top_y = gr['top'] + 26
    vmax = max(d['value'] for d in data)
    n = len(data)
    gap = 4.0
    bw = (cw - gap * (n - 1)) / n
    rest_col = mix(g.bg, g.ink, 0.16)
    for i, d in enumerate(data):
        bh = (base_y - top_y) * d['value'] / vmax
        bx = cx + i * (bw + gap)
        col = g.accent if i == hi else rest_col
        sl.add(Rect(bx, base_y - bh, bw, bh, col, role='bar'))
        lab = str(d.get('display', d['value']))
        size = ds['scale']['caption'] + (6 if i == hi else 0)
        text(sl, lab, bx - 3, base_y - bh - (size * PT) - 3.5, bw + 6, 12,
             ds['strong'] if i != hi else ds['number'], size,
             g.ink if i == hi else g.muted, 1.0, -0.01, size_min=10, align='c',
             role='bar-value', max_lines=1)
        text(sl, str(d['label']), bx - 2, base_y + 3, bw + 4, 8, ds['body'],
             ds['scale']['caption'], g.muted, 1.0, 0.0, size_min=10, align='c',
             role='axis', max_lines=1)
    sl.add(Line(cx, base_y, cx + cw, base_y, g.line, 0.5))
    if c.get('unit'):
        label(sl, ds, g, c['unit'], cx, gr['top'], cw, align='r')
    chrome(sl, ds, g, ctx['n'], ctx['total'], ctx['deck'], c.get('folio', ''))


def quote(sl, ds, c, ctx):
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground'][c.get('ground', ds['grounds']['field'])]
    sl.ground = g
    ground_rect(sl, ds, g)
    m = gr['margin']
    motif(sl, ds, g, ctx['n'], ctx['total'], 'quiet')
    x, w = col_x(ds, 2, 9)
    qf = ds['quote']
    # огромная кавычка — вариант мотива, полутоном
    q = Text(m - 2, gr['top'] - 4, 40, ['«'], ds['display'], 190, mix(g.bg, g.accent, 0.55),
             1.0, 0, 'l', 'ghost')
    sl.add(q)
    t = text(sl, c['text'], x, 0, w, H * 0.55, qf, ds['scale']['h2'] * 1.15, g.ink,
             1.22, -0.01, size_min=22, role='quote', max_lines=6)
    t.y = H * 0.47 - t.h / 2
    yb = t.y + t.h + 10
    sl.add(Line(x, yb, x + 16, yb, g.accent, 2.0))
    if c.get('author'):
        text(sl, c['author'], x, yb + 5, w, 8, ds['strong'], ds['scale']['body'], g.ink,
             1.2, 0, role='author', max_lines=1)
    if c.get('role'):
        label(sl, ds, g, c['role'], x, yb + 13, w)
    chrome(sl, ds, g, ctx['n'], ctx['total'], ctx['deck'], c.get('folio', ''))


def process(sl, ds, c, ctx):
    """Горизонтальная трасса с узлами; шаг, о котором речь, — акцентом."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground'][c.get('ground', ds['grounds']['base'])]
    sl.ground = g
    ground_rect(sl, ds, g)
    m = gr['margin']
    y = eyebrow(sl, ds, g, c.get('eyebrow', ''), m, gr['top'])
    tx, tw = col_x(ds, 0, 8)
    t = headline(sl, ds, g, c['title'], tx, y + 6, tw, H * 0.28, size=ds['scale']['h1'] * 0.78)
    steps = c['steps'][:5]
    hi = c.get('highlight', 0)
    n = len(steps)
    ty = max(t.y + t.h + 24, H * 0.56)
    x0, x1 = m, W - m
    sl.add(Line(-6 if ds['motif'] != 'rule' else x0, ty, W + 6, ty, g.line, 0.75))
    cw = (x1 - x0 - 6 * (n - 1)) / n
    for i, st in enumerate(steps):
        if isinstance(st, str):
            st = {'title': st}
        sx = x0 + i * (cw + 6)
        on = i == hi
        sl.add(Dot(sx + 2.4, ty, 2.4 if on else 1.5, g.accent if on else g.ink))
        text(sl, f'{i + 1:02d}', sx, ty - 11, cw, 8, ds['strong'], ds['scale']['label'] + 1,
             g.accent_text(12) if on else g.muted, 1.2, 0.04, role='index', max_lines=1)
        tt = text(sl, st['title'], sx, ty + 7, cw - 2, 20, ds['strong'],
                  ds['scale']['body'] + 3, g.ink, 1.15, -0.005, size_min=15,
                  role='step', max_lines=2)
        if st.get('text'):
            body(sl, ds, g, st['text'], sx, tt.y + tt.h + 3, cw - 2,
                 H - gr['bottom'] - 14 - (tt.y + tt.h + 3), size=ds['scale']['caption'] + 2,
                 color=g.muted, max_lines=4, size_min=12)
    chrome(sl, ds, g, ctx['n'], ctx['total'], ctx['deck'], c.get('folio', ''))


def gallery(sl, ds, c, ctx):
    """Три кадра разного масштаба: главный — в вылет, два — опорные."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground'][c.get('ground', ds['grounds']['base'])]
    sl.ground = g
    ground_rect(sl, ds, g)
    m = gr['margin']
    ims = c['images'][:3]
    big_w = W * 0.50
    img(sl, ims[0]['path'] if isinstance(ims[0], dict) else ims[0], 0, 0, big_w, H,
        (ims[0].get('focus', (0.5, 0.5)) if isinstance(ims[0], dict) else (0.5, 0.5)))
    rx = big_w + 6
    rw = W - rx
    sm_h = H * 0.44
    for i, im in enumerate(ims[1:]):
        p = im['path'] if isinstance(im, dict) else im
        f = im.get('focus', (0.5, 0.5)) if isinstance(im, dict) else (0.5, 0.5)
        w = rw * (0.56 if i == 0 else 0.44) - (3 if i == 0 else 3)
        x = rx if i == 0 else rx + rw * 0.56 + 3
        img(sl, p, x, H - sm_h, w if i == 0 else W - x, sm_h, f)
    tx = rx + 6
    y = eyebrow(sl, ds, g, c.get('eyebrow', ''), tx, gr['top'], W - tx - m)
    t = headline(sl, ds, g, c['title'], tx, y + 6, W - tx - m, (H - sm_h - y) * 0.55,
                 size=ds['scale']['h2'] * 1.1, size_min=22)
    if c.get('text'):
        body(sl, ds, g, c['text'], tx, t.y + t.h + 6, W - tx - m,
             H - sm_h - 8 - (t.y + t.h + 6), color=g.muted, max_lines=3, size_min=13)
    if ds['motif'] == 'block':
        sl.add(Rect(big_w - 7, 0, 7, 40, g.accent))
    elif ds['motif'] == 'rule':
        sl.add(Line(tx, H - sm_h - 6, W - m, H - sm_h - 6, g.line, 0.5))
        px = tx + (W - m - tx) * (ctx['n'] - 1) / max(ctx['total'] - 1, 1)
        sl.add(Dot(px, H - sm_h - 6, 1.4, g.accent))


def closing(sl, ds, c, ctx):
    """Не «Спасибо»: следующий шаг и контакты, эхом обложки."""
    W, H, gr = ds['W'], ds['H'], ds['grid']
    g = ds['ground']['accent' if ds['motif'] == 'block' else 'dark']
    sl.ground = g
    ground_rect(sl, ds, g)
    motif(sl, ds, g, ctx['n'], ctx['total'], 'loud', seed=1)
    m = gr['margin']
    y = eyebrow(sl, ds, g, c.get('eyebrow', 'Следующий шаг'), m, gr['top'])
    x, w = col_x(ds, 0, 8)
    t = headline(sl, ds, g, c['title'], x, y + 8, w, H * 0.40, size=ds['scale']['h1'] * 1.05)
    if c.get('text'):
        body(sl, ds, g, c['text'], x, t.y + t.h + 10, col_x(ds, 0, 6)[1], 30,
             size=ds['scale']['lead'], color=g.muted, max_lines=3, role='lead')
    cx, cw = col_x(ds, 8, 4)
    cy = H - gr['bottom'] - 6 - 9.5 * len(c.get('contacts', []))
    for i, line in enumerate(c.get('contacts', [])):
        text(sl, line, cx, cy + i * 9.5, cw, 8, ds['strong'] if i == 0 else ds['body'],
             ds['scale']['body'], g.ink, 1.2, 0, role='contact', max_lines=1, size_min=12)
    label(sl, ds, g, c.get('client', ctx['deck']), m, H - gr['bottom'] - 3.2, 150)


LAYOUTS = dict(cover=cover, section=section, statement=statement, number=number,
               split_image=split_image, full_image=full_image, points=points,
               stats=stats, chart=chart, quote=quote, process=process,
               gallery=gallery, closing=closing)


def build(ds, spec):
    total = len(spec['slides'])
    out = []
    for i, c in enumerate(spec['slides'], 1):
        lay = c['layout']
        sl = Slide(i, lay, None, notes=c.get('notes', ''))
        ctx = dict(n=i, total=total, deck=spec['meta'].get('short', spec['meta']['title']))
        LAYOUTS[lay](sl, ds, c, ctx)
        place_arc(sl, ds)
        for t in sl.items:
            if isinstance(t, Text):
                miss = fonts.missing_glyphs(''.join(t.lines), t.font)
                if miss:
                    sl.warnings.append(f'в шрифте {t.font} нет знаков: {"".join(miss)}')
        out.append(sl)
    return out
