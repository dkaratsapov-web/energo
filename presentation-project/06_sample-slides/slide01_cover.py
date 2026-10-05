# -*- coding: utf-8 -*-
"""
Полоса 1 — обложка. Целиком вектор, растровых изображений нет.

Кадр заказчика «Силуэт ЛЭП в сумеречном небе» разложен на две векторные
части: небо — градиент по реальным цветам снимка, опора с проводами —
обведённые контуры. Исходник 1066×1476 px дал бы на полосе 124 dpi и
печатался бы мыльным; в векторе кадр резок при любом увеличении.

Текст и цифры — из текущего каталога без изменений.
"""
import os, sys
sys.path.insert(0, 'scripts')
import cv2
from render import Page, preview
from trace import silhouette, sky_profile
from potrace_vec import levels as pt_levels, draw as pt_draw
from graphics import gradient, nodes
from ds import *

OUT = 'presentation-project/06_sample-slides'
SRC = 'incoming/Силуэт ЛЭП в сумеречном небе.png'

def build():
    img = cv2.imread(SRC)
    # трассировка potrace: кривые Безье вместо ломаной, четыре слоя
    # плотности сохраняют полутона тонких раскосов
    mask, _ = silhouette(img, thr=30, crop_bottom=0.30)
    levels  = pt_levels(img, lv=(0.30, 0.47, 0.64, 0.82), up=4,
                        crop_bottom=0.30, turdsize=4, alphamax=1.15,
                        opttolerance=0.18)
    sky = sky_profile(img, mask, steps=200)
    sh, sw = img.shape[:2]

    p = Page(f'{OUT}/slide01_cover.pdf'); c = p.c; B = BLEED
    x, _  = col_x(0, 12)
    right = PAGE_W - MARGIN_OUTER

    # — небо: ступени по реальным цветам кадра, снизу уходит в фирменный тон —
    H = PAGE_H + 2*B
    n = len(sky)
    for i, col in enumerate(sky):
        t  = i/(n-1)
        mix = min(max((t - 0.55)/0.45, 0), 1)**1.3          # к низу — к фирменному
        rgbv = [col[k]*(1-mix) + C.PURPLE_DEEP[k]*mix for k in range(3)]
        c.setFillColorRGB(*[v/255 for v in rgbv])
        c.rect(-B, -B + H*(1 - (i+1)/n), PAGE_W + 2*B, H/n + 0.7, stroke=0, fill=1)

    # — силуэт: кадр кадрируется по высоте полосы, низ уходит под текст —
    pt_draw(c, levels, -B, PAGE_H - H*0.86, PAGE_W + 2*B, H*0.86,
            (12, 13, 28), a0=0.42, a1=1.0)

    # — низ притемнён под набор, вектором —
    for i in range(170):
        t = i/169
        c.setFillColorRGB(*rgb(C.PURPLE_DEEP), alpha=0.97*(t**1.5))
        c.rect(-B, 150*mm*(1 - (i+1)/170) - B, PAGE_W + 2*B, 150*mm/170 + 0.7, stroke=0, fill=1)

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

    # — цифры —
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
