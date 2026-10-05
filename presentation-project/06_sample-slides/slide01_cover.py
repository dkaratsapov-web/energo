# -*- coding: utf-8 -*-
"""
Полоса 1 — обложка. Полностью вектор, ни одного растрового пикселя.

Текст и цифры взяты из текущего каталога без изменений:
    КОМПЛЕКСНОЕ СТРОИТЕЛЬСТВО · #2025
    25 800 км · 1 224 подстанции · 17 регионов (полоса 6 исходника)

Фотография на обложке не используется сознательно: исходников съёмки нет,
а растр 150 dpi — та самая причина, по которой каталог пересобирается.
Опора и провода построены геометрией и резки при любом увеличении.
"""
import os, sys
sys.path.insert(0, 'scripts')
from render import Page, preview
from graphics import gradient, tower, wire, grid, flow_field, nodes
from ds import *

OUT = 'presentation-project/06_sample-slides'

def build():
    p = Page(f'{OUT}/slide01_cover.pdf')
    c = p.c
    B = BLEED
    x, _  = col_x(0, 12)
    right = PAGE_W - MARGIN_OUTER

    # — фон: градиент ночного неба, вектор —
    gradient(c, -B, -B, PAGE_W+2*B, PAGE_H+2*B, (26, 32, 74), (58, 42, 86))

    # — поток энергии: генеративное поле линий, вектор —
    flow_field(c, -B, -B, PAGE_W+2*B, PAGE_H+2*B,
               n=560, seed=11, base=(132, 146, 205), accent=C.ORANGE,
               accent_ratio=0.075, scale=0.85,
               weight=(0.20, 0.70), alpha=(0.05, 0.40))

    # — узлы сети: точки с ореолом, как подстанции на схеме —
    nodes(c, [(PAGE_W*0.72, 232*mm, 1.6), (PAGE_W*0.26, 205*mm, 1.0),
              (PAGE_W*0.52, 251*mm, 0.8), (PAGE_W*0.88, 192*mm, 1.2),
              (PAGE_W*0.14, 246*mm, 0.7)], C.ORANGE, r=1.4)

    # — низ полосы притемнён под текст: вектор, не растр —
    c.saveState()
    for i in range(140):
        t = i/139
        c.setFillColorRGB(*rgb(C.PURPLE_DEEP), alpha=0.92*(t**1.5))
        yy = 150*mm*(1 - (i+1)/140) - B
        c.rect(-B, yy, PAGE_W+2*B, 150*mm/140 + 0.6, stroke=0, fill=1)
    c.restoreState()

    # — шапка —
    p.text('ГРУППА КОМПАНИЙ', x, PAGE_H - MARGIN_TOP - 4,
           T.FONT_MED, T.MICRO, C.MUTED_D, track=T.TRACK_CAPS)
    p.text('ЭНЕРГО ГРУПП', x, PAGE_H - MARGIN_TOP - 20,
           T.FONT_BLACK, 17, C.ORANGE, track=10)
    p.text('КАТАЛОГ 2025', x, PAGE_H - MARGIN_TOP - 38,
           T.FONT_MED, T.MICRO, C.MUTED_D, track=T.TRACK_CAPS)
    p.rule(x, PAGE_H - MARGIN_TOP - 48, right - x, C.LINE_D, 0.5)

    # — заголовок —
    base = 118*mm
    head = ['КОМПЛЕКСНОЕ', 'СТРОИТЕЛЬСТВО']
    size = p.fit_size(head, right - x, T.FONT_BLACK, T.DISPLAY, track=-12)
    p.lines(head, x, base, T.FONT_BLACK, size, C.WHITE, T.LEAD_DISPLAY, track=-12)

    p.lines(['Проектирование, строительство и ввод в эксплуатацию',
             'объектов энергетики по всей России'],
            x, base - size*T.LEAD_DISPLAY - 14*mm,
            T.FONT_BOOK, T.H3, C.MUTED_D, T.LEAD_H2)

    # — цифры: доказательство масштаба —
    y = MARGIN_BOTTOM + 28*mm
    p.rule(x, y + 19*mm, right - x, C.LINE_D, 0.5)
    for i, (num, cap) in enumerate([('25 800', 'км проводов'),
                                    ('1 224', 'подстанции'),
                                    ('17', 'регионов')]):
        cx, _ = col_x(i*4, 4)
        p.text(num, cx, y, T.FONT_BLACK, 30, C.ORANGE, track=-10)
        p.text(cap, cx, y - 7*mm, T.FONT_BOOK, T.SMALL, C.MUTED_D)

    p.text('#2025', x, MARGIN_BOTTOM, T.FONT_MED, T.BODY, C.MUTED_D, track=30)

    path = p.save()
    preview(path, f'{OUT}/slide01_cover.jpg')
    return path

if __name__ == '__main__':
    print(build())
