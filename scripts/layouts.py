# -*- coding: utf-8 -*-
"""
Повторяющиеся схемы разворотов каталога.

Тридцать две полосы собираются полутора десятком схем. Схемы лежат здесь,
а не в файлах разворотов: иначе одинаковые по замыслу развороты расходятся
по мелочам — где-то отбивка 18 мм, где-то 20, где-то кадр шире на пять.

Все схемы работают в координатах разворота и ничего не знают о том, в какой
из трёх файлов (левая полоса, правая полоса, совмещённый разворот) они
рисуются.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2
from spread import Spread, L, R
from graphics import gradient, field_lines, grid, Bg
from ds import *

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PH   = f'{ROOT}/presentation-project/05_assets/photos'

# Ширина кадра: предел, при котором исходные 1240 px дают ровно 300 dpi.
PW = 105*mm


class Tone:
    """Тон разворота: цвета линеек, подписей и «водяного» номера."""
    def __init__(self, dark):
        self.dark  = dark
        self.line  = C.LINE_D  if dark else C.LINE_L
        self.muted = C.MUTED_D if dark else C.MUTED_L
        self.ink   = C.WHITE   if dark else C.INK
        self.ghost = (56, 58, 104) if dark else (227, 225, 220)


def base(s, n, section_l, section_r, dark=True, seed=3, top_lines=True,
         chrome=True):
    """Фон, шапка и колонцифры разворота. Возвращает тон.

    chrome=False рисует только фон: шапку и колонцифры вызывают сами,
    когда между фоном и ними должна лечь графика во всю полосу.
    """
    c, B = s.c, BLEED
    if dark:
        bg = Bg((28, 32, 74), (48, 39, 82), -B, PAGE_H + 2*B)
        gradient(c, -B, -B, SPREAD_W + 2*B, PAGE_H + 2*B, (28, 32, 74), (48, 39, 82))
        if top_lines:
            field_lines(c, -B, PAGE_H - 96*mm, SPREAD_W + 2*B, 96*mm + B, rows=16,
                        seed=seed, alpha=(0.03, 0.13), bg=bg)
        s.fold_shade((10, 11, 26), w=30*mm, alpha=0.26, bg=bg)
    else:
        bg = Bg(C.PAPER)
        s.fill(C.PAPER)
        grid(c, -B, -B, SPREAD_W + 2*B, PAGE_H + 2*B, 14*mm, C.LINE_L, 0.25, 0.5, bg=bg)
        s.fold_shade((120, 118, 112), w=26*mm, alpha=0.13, bg=bg)
    if chrome:
        s.heads(section_l, section_r, dark=dark)
        s.folios(n, dark=dark)
    return Tone(dark)


def outer_x(side, w):
    """x блока шириной w, прижатого к ВНЕШНЕМУ обрезу полосы."""
    _, ox = edges(side)
    return ox if side == L else ox - w


def ghost_num(s, side, num, t, size=200):
    """«Водяной» номер у нижнего поля: закрывает низ полосы под коротким
    перечнем. Текста не добавляет — то же число стоит в надзаголовке.
    Базовая линия поднята: метрический габарит строки такого кегля уходит
    на 17 мм ниже базовой и перекрыл бы колонцифру."""
    x, _ = px(side, 0, 12)
    s.text(num, x, MARGIN_BOTTOM + 24*mm, T.FONT_BLACK, size, t.ghost, track=-30)


def bullets(s, side, items, y, t, size=12, step=20*mm, lead=1.40,
            numbered=True, rules=True, num_w=13*mm):
    """Перечень по общей сетке отбивок. Возвращает низ блока."""
    x, w = px(side, 0, 12)
    for i, it in enumerate(items, 1):
        if rules:
            s.rule(x, y + 11*mm, w, t.line, 0.5)
        if numbered:
            s.numbered(i, x, y, it, dark=t.dark, size=size, num_w=num_w,
                       width=w, lead=lead)
        else:
            s.c.setFillColorRGB(*rgb(C.ORANGE))
            s.c.circle(x - 6*mm, y + 1.4*mm, 1.5*mm, stroke=0, fill=1)
            s.lines(s.wrap(it, w, T.FONT_BOOK, size), x, y, T.FONT_BOOK, size,
                    t.ink, lead)
        y -= step
    if rules:
        s.rule(x, y + 11*mm, w, t.line, 0.5)
    return y


def body(s, side, text, y, t, size=11, lead=1.52, span=12, col=None):
    """Абзац по мере полосы. Возвращает базовую линию последней строки."""
    x, w = px(side, 0, span)
    rows = s.wrap(text, w, T.FONT_BOOK, size)
    s.lines(rows, x, y, T.FONT_BOOK, size, col or t.ink, lead)
    return y - (len(rows) - 1)*size*lead


def photo_h(path, w=PW, dpi=300):
    """Предельная высота кадра: считается из его пикселей, не назначается."""
    a = cv2.imread(f'{PH}/{path}.png')
    return min(a.shape[0]/dpi*25.4*mm, w*a.shape[0]/a.shape[1])


def stack(s, side, photos, top, bottom, w=PW, gap_max=14*mm, caps=None, t=None):
    """Кадры столбцом у внешнего обреза. Высота каждого — предел его
    разрешения, остаток уходит в равные промежутки, поэтому столбец всегда
    стоит от верхней границы до нижнего поля.

    Запись (None, высота) резервирует слот под кадр, который рисуется
    отдельно. Возвращает список (y, высота) по слотам.
    """
    x = outer_x(side, w)
    hs = [p[1] if p[0] is None else photo_h(p[0], w) for p in photos]
    gap = min(gap_max, (top - bottom - sum(hs))/max(len(hs) - 1, 1))
    y, out = top, []
    for (path, anchor), h in zip(photos, hs):
        y -= h
        if path is not None:
            s.photo(f'{PH}/{path}.png', x, y, w, h, anchor=anchor or 'c')
        out.append((y, h))
        y -= gap
    if caps:
        for (yy, hh), cap in zip(out, caps):
            if cap:
                s.text(cap, x, yy - 5*mm, T.FONT_BOOK, T.SMALL, t.muted)
    return out


def pair(s, side, a, b, y, h, w=PW, gap=4*mm):
    """Два узких кадра в одном слоте столбца."""
    x  = outer_x(side, w)
    ww = (w - gap)/2
    s.photo(f'{PH}/{a}.png', x,           y, ww, h)
    s.photo(f'{PH}/{b}.png', x + ww + gap, y, ww, h)


def topic(s, side, eyebrow, title, t, size=None):
    """Шапка темы на полосе: надзаголовок и название. Возвращает низ."""
    s.eyebrow(side, eyebrow)
    return s.title(side, title, dark=t.dark, size=size)
