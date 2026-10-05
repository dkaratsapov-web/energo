# -*- coding: utf-8 -*-
"""
Развороты 28–29, 30–31 и задняя обложка 32.

28–29  география: карта России вектором, семнадцать регионов присутствия
       оранжевым, список регионов на правой полосе;
30–31  заказчики и допуски: стена логотипов слева, разрешительные
       документы и контакты справа;
32     задняя обложка — целиком вектор, как и передняя.

Карта снята с полосы 28 утверждённого каталога и обведена potrace: в
прежней вёрстке она лежала в сведённом растре 150 dpi и печаталась мыльной.

Логотипы заказчиков взяты из того же растра и поставлены в размере, при
котором их пиксели дают 300 dpi, — это 27,5 мм по ширине плашки. Чтобы дать
их крупнее, нужны векторные оригиналы; восемнадцать знаков перечислены в
assets_needed/README.md.
"""
import os, sys
sys.path.insert(0, 'scripts')
import cv2
from spread import Spread, build, L, R
from render import Page, preview
from layouts import base, topic, bullets, body, outer_x, PH
from graphics import gradient, field_lines, tower, wire, nodes, Bg
import mapru
from ds import *

OUT = 'presentation-project/06_sample-slides'
REGIONS = ['Брянская область', 'Владимирская область', 'Волгоградская область',
           'Вологодская область', 'Воронежская область', 'Ленинградская область',
           'Липецкая область', 'Московская область', 'Мурманская область',
           'Нижегородская область', 'Орловская область', 'Рязанская область',
           'Смоленская область', 'Тамбовская область', 'Тверская область',
           'Тульская область', 'Ярославская область']


# ══════════════════════════════ 28–29 · ГЕОГРАФИЯ ═══════════════════════
def spread_28_29(s):
    c, B = s.c, BLEED
    t = base(s, 28, 'География проектов', 'Регионы присутствия',
             dark=True, seed=28, top_lines=False, chrome=False)

    # Карта отдана правой полосе целиком и уходит за верхний, нижний и
    # внешний обрез: в исходнике её восточный край срезан краем полосы, и
    # без выпуска под обрез этот срез читается как брак вёрстки. Через сгиб
    # карту не ведём — европейская часть с подсвеченными регионами
    # пришлась бы ровно в корешок.
    c.saveState()
    cp = c.beginPath(); cp.rect(FOLD, -B, PAGE_W + 2*B, PAGE_H + 2*B)
    c.clipPath(cp, stroke=0, fill=0)
    # Ширина 232 мм при отношении сторон 1,2 даёт высоту 193 мм: страна
    # целиком помещается по высоте полосы, а восточный срез уходит за обрез.
    mapru.draw(c, FOLD + 6*mm, 50*mm, 232*mm, 193.4*mm,
               (62, 66, 118), C.ORANGE, fit='width')
    c.restoreState()
    # шапка и колонцифры — поверх карты
    s.heads('География проектов', 'Регионы присутствия')
    s.folios(28)

    yb = topic(s, L, 'ГДЕ МЫ РАБОТАЕМ', ['ГЕОГРАФИЯ', 'ПРОЕКТОВ'], t)
    x, w = px(L, 0, 12)
    s.text('17', x, 186*mm, T.FONT_BLACK, 110, C.ORANGE, track=-30)
    s.lines(['регионов', 'присутствия'], x + 46*mm, 196*mm, T.FONT_BOOK, T.H3,
            t.muted, T.LEAD_H2)
    s.rule(x, 172*mm, w, t.line, 0.5)

    y0, step = 158*mm, 15*mm
    for i, r in enumerate(REGIONS):
        cx, cw = px(L, (i // 9)*6, 5)
        yy = y0 - (i % 9)*step
        s.text(f'{i+1:02d}', cx, yy, T.FONT_BLACK, T.SMALL, C.ORANGE, track=20)
        s.text(r, cx + 12*mm, yy, T.FONT_BOOK, T.BODY, C.WHITE)
        s.rule(cx, yy - 5*mm, cw, t.line, 0.4)

    s.text('РЕГИОНЫ ПРИСУТСТВИЯ', *px(R, 0, 12)[:1], Y_EYEBROW, T.FONT_MED,
           T.MICRO, C.ORANGE, track=T.TRACK_CAPS)


# ══════════════════════ 30–31 · ЗАКАЗЧИКИ | ДОПУСКИ ═════════════════════
LOGO_W, LOGO_H = 27.5*mm, 17.5*mm

def spread_30_31(s):
    t = base(s, 30, 'Заказчики и партнёры', 'Допуски и лицензии', dark=False)

    topic(s, L, 'С КЕМ МЫ РАБОТАЕМ', ['НАМ', 'ДОВЕРЯЮТ'], t)
    x, w = px(L, 0, 12)
    # Сетка 3×6 строится от наборной полосы: промежутки считаются из
    # остатка, а не назначаются, иначе нижний ряд уходит за нижнее поле.
    top, bot, rows, cols = 200*mm, MARGIN_BOTTOM + 10*mm, 6, 3
    gx = (w - cols*LOGO_W)/(cols - 1)
    gy = (top - bot - rows*LOGO_H)/(rows - 1)
    for i in range(18):
        r, k = divmod(i, cols)
        bx = x + k*(LOGO_W + gx)
        by = top - LOGO_H - r*(LOGO_H + gy)
        s.c.setStrokeColorRGB(*rgb(C.LINE_L)); s.c.setLineWidth(0.4)
        s.c.rect(bx - 3.5*mm, by - 3.5*mm, LOGO_W + 7*mm, LOGO_H + 7*mm,
                 stroke=1, fill=0)
        s.photo(f'{PH}/partners/logo{i+1:02d}.png', bx, by, LOGO_W, LOGO_H)

    yb = topic(s, R, 'РАЗРЕШИТЕЛЬНЫЕ ДОКУМЕНТЫ', ['ДОПУСКИ', 'И ЛИЦЕНЗИИ'], t)
    y = bullets(s, R, [
        'СРО в области инженерных изысканий и в области '
        'архитектурно-строительного проектирования. '
        'Уровень ответственности 25 млн. руб.',
        'СРО в области строительства, реконструкции, капитального ремонта, '
        'сноса объектов капитального строительства. '
        'Уровень ответственности 3 млрд. рублей',
        'Лицензия Министерства Культуры', 'Лицензия МЧС',
        'Свидетельство Ростехнадзора о регистрации электролаборатории'],
        yb - 26*mm, t, size=11, step=26*mm, lead=1.42)

    xr, wr = px(R, 0, 12)
    s.rule(xr, MARGIN_BOTTOM + 26*mm, wr, t.line, 0.5)
    for i, (lab, val) in enumerate((('E-MAIL', 'info@egroupp.ru'),
                                    ('САЙТ', 'https://egroupp.ru/'))):
        cx, _ = px(R, i*6, 5)
        s.text(lab, cx, MARGIN_BOTTOM + 14*mm, T.FONT_SEMI, T.MICRO, C.ORANGE,
               track=T.TRACK_CAPS)
        s.text(val, cx, MARGIN_BOTTOM + 4*mm, T.FONT_MED, T.H3, C.INK)


# ═══════════════════════════ 32 · ЗАДНЯЯ ОБЛОЖКА ════════════════════════
def back_cover():
    """Задняя обложка: целиком вектор, как и передняя."""
    p = Page(f'{OUT}/page32_back.pdf'); c = p.c; B = BLEED
    bg = Bg((30, 34, 78), (52, 40, 82), -B, PAGE_H + 2*B)
    gradient(c, -B, -B, PAGE_W + 2*B, PAGE_H + 2*B, (30, 34, 78), (52, 40, 82))
    field_lines(c, -B, 120*mm, PAGE_W + 2*B, PAGE_H - 100*mm, rows=26, seed=32,
                alpha=(0.04, 0.16), bg=bg)

    # Линия электропередачи: три опоры и провисающие провода. Рисуется
    # формулами, а не снимается с растра, поэтому резка при любом увеличении.
    base_y = 44*mm
    xs = [26*mm, 105*mm, 190*mm]
    hs = [70*mm, 96*mm, 62*mm]
    for x, h in zip(xs, hs):
        tower(c, x, base_y, h, (96, 102, 150), weight=0.9, alpha=0.85, bg=bg)
    for (x0, h0), (x1, h1) in zip(zip(xs, hs), zip(xs[1:], hs[1:])):
        for d in (0.80, 0.92):
            wire(c, x0, base_y + h0*d, x1, base_y + h1*d, 9*mm,
                 (120, 126, 176), 0.6, 0.8, bg=bg)
    nodes(c, [(x, base_y + h, 1.0) for x, h in zip(xs, hs)], C.ORANGE, 1.4, bg=bg)

    x, _  = col_x(0, 12)
    right = PAGE_W - MARGIN_OUTER
    p.text('ГРУППА КОМПАНИЙ', x, PAGE_H - MARGIN_TOP - 4, T.FONT_MED, T.MICRO,
           C.MUTED_D, track=T.TRACK_CAPS)
    p.text('ЭНЕРГО ГРУПП', x, PAGE_H - MARGIN_TOP - 20, T.FONT_BLACK, 17,
           C.ORANGE, track=10)
    p.rule(x, PAGE_H - MARGIN_TOP - 32, right - x, C.LINE_D, 0.5)

    head = ['КОМПЛЕКСНОЕ', 'СТРОИТЕЛЬСТВО', 'ОБЪЕКТОВ ЭНЕРГЕТИКИ']
    size = p.fit_size(head, right - x, T.FONT_BLACK, 34, track=-8)
    p.lines(head, x, PAGE_H - 92*mm, T.FONT_BLACK, size, C.WHITE, T.LEAD_H1,
            track=-8)

    p.rule(x, 30*mm, right - x, C.LINE_D, 0.5)
    for i, (lab, val) in enumerate((('E-MAIL', 'info@egroupp.ru'),
                                    ('САЙТ', 'https://egroupp.ru/'))):
        cx, _ = col_x(i*6, 5)
        p.text(lab, cx, 22*mm, T.FONT_SEMI, T.MICRO, C.ORANGE, track=T.TRACK_CAPS)
        p.text(val, cx, 13*mm, T.FONT_MED, T.H3, C.WHITE)
    return p.save()


SPREADS = [('spread_28_29', spread_28_29, 28), ('spread_30_31', spread_30_31, 30)]

if __name__ == '__main__':
    for name, fn, n in SPREADS:
        made = build(fn, OUT, name)
        for m in made:
            if m.endswith('_spread.pdf'):
                preview(m, m.replace('.pdf', '.jpg'), 2200)
        print(name, 'ok')
    path = back_cover()
    preview(path, path.replace('.pdf', '.jpg'), 1100)
    print('page32_back ok')
