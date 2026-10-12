# -*- coding: utf-8 -*-
"""
Полоса 1 — обложка. Целиком вектор, ни одного растрового пикселя.

Почему не обведённая фотография. Кадр заказчика 1066×1476 px даёт на полосе
124 dpi и печатается мыльным, поэтому его обводили potrace. Обводка честно
показала, чем она является: небо ступенями, провода — царапинами, в небе
висят обрывки изоляторов, вырванные из контекста. Автотрейс фотографии не
становится иллюстрацией.

Поэтому обложка СТРОИТСЯ, а не обводится. Линия электропередачи рисуется
формулами по реальной схеме анкерно-угловой опоры ВЛ 110 кВ: сужающийся
решётчатый ствол, раскосы крест-накрест, траверсы с гирляндами изоляторов,
провода цепной линией. Тот же язык, что на задней обложке и на проводе в
шапке каждого разворота, — каталог собирается в одно целое.

Сумерки набраны тремя остановками: холодный зенит, тёплое зарево у
горизонта, тёмная земля. Переход считается по ступеням плотнее растровой
точки, поэтому полос на печати не даёт.
"""
import os, sys
sys.path.insert(0, 'scripts')
from render import Page, preview
from graphics import tower, wire, nodes, mix, _rgb
from ds import *

OUT = 'presentation-project/06_sample-slides'

HORIZON = 112*mm            # линия горизонта
STOPS = [(0.00, (10, 12, 34)),     # зенит
         (0.42, (28, 28, 64)),
         (0.56, (58, 48, 90)),     # зарево
         (0.635, (104, 74, 92)),   # самая тёплая полоса над горизонтом
         (0.672, (52, 40, 70)),    # земля начинается мягче, без ребра
         (1.00, (16, 15, 40))]


class Sky:
    """Небо как функция высоты: нужно и для заливки, и для того, чтобы
    считать цвет графики, которая на него ложится. Прозрачности в печатном
    файле нет — полупрозрачный штрих заменён смешанным цветом."""
    def __init__(self, y0, h):
        self.y0, self.h = y0, h

    def at(self, y):
        t = min(max((self.y0 + self.h - y)/self.h, 0.0), 1.0)
        for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
            if t <= t1:
                k = (t - t0)/max(t1 - t0, 1e-6)
                return tuple(c0[i] + (c1[i] - c0[i])*k for i in range(3))
        return STOPS[-1][1]


def build():
    p = Page(f'{OUT}/slide01_cover.pdf'); c = p.c; B = BLEED
    H = PAGE_H + 2*B
    sky = Sky(-B, H)

    # — небо: 420 ступеней, шаг мельче растровой точки —
    N = 420
    for i in range(N):
        yy = -B + H*(1 - (i + 1)/N)
        c.setFillColorRGB(*_rgb(sky.at(yy + H/N/2)))
        c.rect(-B, yy, PAGE_W + 2*B, H/N + 0.7, stroke=0, fill=1)

    # — линия электропередачи уходит вдаль: ближняя опора справа, дальние
    #   мельче и выше по кадру, провода провисают между ними —
    # (ось, пята, высота, вес штриха, плотность) — дальние опоры бледнее:
    # воздушная перспектива, без неё линия не уходит вдаль, а лепится в одну
    # плоскость
    towers = [(176*mm, HORIZON - 2*mm, 132*mm, 1.05, 0.95),
              ( 96*mm, HORIZON + 1*mm,  84*mm, 0.72, 0.68),
              ( 44*mm, HORIZON + 3*mm,  54*mm, 0.55, 0.46),
              ( 12*mm, HORIZON + 4*mm,  36*mm, 0.44, 0.34)]

    # Точки подвеса берутся из геометрии самой опоры: нижняя траверса на
    # 0,62 высоты с вылетом 0,46, верхняя на 0,86 с вылетом 0,33, гирлянда
    # изоляторов опускает провод ещё на 0,075. Иначе провода «плавают»
    # мимо траверс — именно это и выдаёт нарисованную от руки схему.
    ARMS = ((0.62, 0.46), (0.86, 0.33))

    def hang(x, b, h, lvl, d):
        y_rel, arm = ARMS[lvl]
        return x + d*h*arm, b + h*(y_rel - 0.075)

    # провода рисуются ПОД опорами: в натуре они заходят за ствол
    for (x0, b0, h0, _, a0), (x1, b1, h1, _, a1) in zip(towers, towers[1:]):
        for lvl in (0, 1):
            for d in (-1, 1):
                ax, ay = hang(x0, b0, h0, lvl, d)
                bx, by = hang(x1, b1, h1, lvl, d)
                wire(c, ax, ay, bx, by, (ax - bx)*0.085, (158, 158, 200),
                     0.5, (a0 + a1)/2*0.62, bg=sky)
    # провода уходят за правый обрез
    x0, b0, h0, _, a0 = towers[0]
    for lvl in (0, 1):
        for d in (-1, 1):
            ax, ay = hang(x0, b0, h0, lvl, d)
            # к правому обрезу провод идёт почти горизонтально: если дать
            # ему подъём, линия читается карабкающейся в гору
            wire(c, ax, ay, PAGE_W + B, ay - 4*mm, 5*mm, (158, 158, 200),
                 0.5, a0*0.62, bg=sky)

    for cx, by, h, w, a in towers:
        tower(c, cx, by, h, (222, 224, 246), weight=w, alpha=a, bg=sky)
    # сигнальный огонь на вершине ближней опоры — единственная точка цвета
    # выше набора
    nodes(c, [(towers[0][0], towers[0][1] + towers[0][2]*1.055, 1.0)],
          C.ORANGE_HOT, r=1.5, bg=sky)

    # — земля: плотная полоса под горизонтом, набор ложится на неё —
    for i in range(240):
        t = i/239
        yy = HORIZON*(1 - (i + 1)/240) - B
        c.setFillColorRGB(*_rgb(mix((12, 13, 32), sky.at(yy), 0.92*t**1.1)))
        c.rect(-B, yy, PAGE_W + 2*B, HORIZON/240 + 0.7, stroke=0, fill=1)

    # — шапка —
    x, _  = col_x(0, 12)
    right = PAGE_W - MARGIN_OUTER
    p.text('ГРУППА КОМПАНИЙ', x, PAGE_H - MARGIN_TOP - 4,
           T.FONT_MED, T.MICRO, C.MUTED_D, track=T.TRACK_CAPS)
    p.text('ЭНЕРГО ГРУПП', x, PAGE_H - MARGIN_TOP - 21,
           T.FONT_BLACK, 18, C.ORANGE, track=10)
    p.text('КАТАЛОГ 2025', right, PAGE_H - MARGIN_TOP - 4,
           T.FONT_MED, T.MICRO, C.MUTED_D, track=T.TRACK_CAPS, align='r')

    # — заголовок —
    base = 96*mm
    head = ['КОМПЛЕКСНОЕ', 'СТРОИТЕЛЬСТВО']
    size = p.fit_size(head, right - x, T.FONT_BLACK, T.DISPLAY, track=-14)
    y = p.lines(head, x, base, T.FONT_BLACK, size, C.WHITE, 1.0, track=-14)
    y = p.lines(['Проектирование, строительство и ввод в эксплуатацию',
                 'объектов энергетики по всей России'],
                x, y - 15*mm, T.FONT_BOOK, T.H3, C.MUTED_D, T.LEAD_H2)

    # — цифры —
    p.rule(x, y - 12*mm, right - x, C.LINE_D, 0.5)
    for i, (num, cap) in enumerate([('25 800', 'км проводов'),
                                    ('1 224', 'подстанции'),
                                    ('17', 'регионов')]):
        cx, _ = col_x(i*4, 4)
        p.text(num, cx, y - 26*mm, T.FONT_BLACK, 30, C.ORANGE, track=-10)
        p.text(cap, cx, y - 33*mm, T.FONT_BOOK, T.SMALL, C.MUTED_D)
    p.text('#2025', x, MARGIN_BOTTOM - 7*mm, T.FONT_MED, T.BODY, C.MUTED_D,
           track=30)

    path = p.save()
    preview(path, f'{OUT}/slide01_cover.jpg', 1100)
    return path


if __name__ == '__main__':
    print(build())
