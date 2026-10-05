# -*- coding: utf-8 -*-
"""
Полоса 1 — обложка. Направление B: крупная типографика на тёмном.

Текст взят из текущего каталога без изменений:
    КОМПЛЕКСНОЕ СТРОИТЕЛЬСТВО · #2025
Добавлены только те данные, что уже есть внутри каталога (полоса 6), —
они вынесены на обложку как доказательство масштаба.
"""
import os, sys
sys.path.insert(0, 'scripts')
from render import Page, preview
from ds import *

OUT = 'presentation-project/06_sample-slides'

def build():
    p = Page(f'{OUT}/slide01_cover.pdf')
    c = p.c

    # Фото ЛЭП на вылет, уходящее в фирменный фиолетовый к низу полосы
    p.image(f'presentation-project/05_assets/cover_bg.jpg',
            0, 0, PAGE_W, PAGE_H, bleed_sides=('l','r','t','b'))

    x, _ = col_x(0, 12)                    # левое поле наборной полосы
    right = PAGE_W - MARGIN_OUTER

    # — верх: знак компании и год —
    p.text('ГРУППА КОМПАНИЙ', x, PAGE_H - MARGIN_TOP - 4,
           T.FONT_MED, T.MICRO, C.MUTED_D, track=T.TRACK_CAPS)
    p.text('ЭНЕРГО ГРУПП', x, PAGE_H - MARGIN_TOP - 20,
           T.FONT_BLACK, 17, C.ORANGE, track=10)
    # год — под знаком компании, иначе наезжает на логотип в углу подложки
    p.text('КАТАЛОГ 2025', x, PAGE_H - MARGIN_TOP - 38,
           T.FONT_MED, T.MICRO, C.MUTED_D, track=T.TRACK_CAPS)
    p.rule(x, PAGE_H - MARGIN_TOP - 48, right - x, C.LINE_D, 0.5)

    # — заголовок: две строки во всю ширину полосы —
    base = 132*mm
    head = ['КОМПЛЕКСНОЕ', 'СТРОИТЕЛЬСТВО']
    size = p.fit_size(head, right - x, T.FONT_BLACK, T.DISPLAY, track=-12)
    p.lines(head, x, base, T.FONT_BLACK, size, C.WHITE, T.LEAD_DISPLAY, track=-12)

    # — подзаголовок: кто мы, одной строкой —
    p.lines(['Проектирование, строительство и ввод в эксплуатацию',
             'объектов энергетики по всей России'],
            x, base - size*T.LEAD_DISPLAY - 16*mm,
            T.FONT_BOOK, T.H3, C.MUTED_D, T.LEAD_H2)

    # — доказательство масштаба: три цифры из каталога —
    y = MARGIN_BOTTOM + 30*mm
    p.rule(x, y + 20*mm, right - x, C.LINE_D, 0.5)
    facts = [('25 800', 'км проводов'), ('1 224', 'подстанции'), ('17', 'регионов')]
    for i, (num, cap) in enumerate(facts):
        cx, cw = col_x(i*4, 4)
        p.text(num, cx, y, T.FONT_BLACK, 30, C.ORANGE, track=-10)
        p.text(cap, cx, y - 7*mm, T.FONT_BOOK, T.SMALL, C.MUTED_D)

    # — низ: год выпуска как в оригинале —
    p.text('#2025', x, MARGIN_BOTTOM, T.FONT_MED, T.BODY, C.MUTED_D, track=30)

    path = p.save()
    preview(path, f'{OUT}/slide01_cover.jpg')
    return path

if __name__ == '__main__':
    print(build())
