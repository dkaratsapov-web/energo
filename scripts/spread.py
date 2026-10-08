# -*- coding: utf-8 -*-
"""
Разворот как единица вёрстки.

Каталог сшивается, и читатель видит не полосу, а разворот 420×297 мм.
Поэтому разворот рисуется ОДНОЙ функцией в сквозных координатах, а потом
сохраняется тремя файлами:

    …_L.pdf       левая полоса, обрез+вылет  — в типографию
    …_R.pdf       правая полоса, обрез+вылет — в типографию
    …_spread.pdf  совмещённый разворот       — на согласование

Содержимое всех трёх — результат одного и того же кода, поэтому фон,
линейки и диаграммы, переходящие через сгиб, стыкуются ровно: расхождения
нет не потому, что его выверили, а потому, что стыка в исходнике нет.

Что разворот даёт вёрстке:
  · зеркальные поля — корешковое 22 мм, внешнее 16 мм, у каждой полосы со
    своей стороны;
  · колонцифра во внешнем нижнем углу, как в книге, а не в углу слайда;
  · связки через сгиб: линейка, плашка и диаграмма идут из полосы в полосу;
  · правило сгиба — в мёртвую зону 44 мм не заходит ничего читаемого, тон
    у сгиба с обеих сторон одинаковый, чтобы смещение на сшивке не вылезло.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reportlab.pdfgen import canvas
from render import Slide, fonts, boxes
from ds import *

L, R = 'L', 'R'


class Spread(Slide):
    """Полоса-разворот. Начало координат — левый нижний угол обреза ЛЕВОЙ
    полосы; x растёт через сгиб на правую. Компоненты набора наследуются
    от Slide: они работают от переданных координат и о сгибе не знают."""

    def __init__(self, c, side=None):
        """side — какая полоса сейчас рисуется: 'L', 'R' или None для
        совмещённого разворота. От этого зависит только вылет в корешок."""
        super().__init__(c=c)
        self.side = side

    def bleed_box(self, side):
        """(x0, x1) полосы вместе с вылетами — для кадров и плашек навылет.

        Наружу вылет есть всегда. В корешок он добавляется ТОЛЬКО в файле
        самой полосы: на совмещённом развороте он налез бы на соседнюю
        полосу, а в печати этот край всё равно обрезается.
        """
        b = BLEED
        gut = b if self.side == side else 0
        return (-b, PAGE_W + gut) if side == L else (FOLD - gut, SPREAD_W + b)

    # ── фоны ─────────────────────────────────────────────────────────────
    def fill(self, color):
        """Залить разворот целиком, с вылетом по всем четырём сторонам."""
        b = BLEED
        self.c.setFillColorRGB(*rgb(color))
        self.c.rect(-b, -b, SPREAD_W + 2*b, PAGE_H + 2*b, stroke=0, fill=1)

    def band(self, y, h, color, alpha=None):
        """Горизонтальная плашка через весь разворот.

        Горизонтальный раздел тона — единственный, который на сшивке
        безупречен: он идёт вдоль сгиба, а не через него, и смещение полос
        его не разрывает. Вертикальные разделы тона у сгиба не ставим.
        """
        b = BLEED
        self.c.saveState()
        if alpha is None:
            self.c.setFillColorRGB(*rgb(color))
        else:
            self.c.setFillColorRGB(*rgb(color), alpha=alpha)
        self.c.rect(-b, y, SPREAD_W + 2*b, h, stroke=0, fill=1)
        self.c.restoreState()

    def fold_shade(self, color, w=26*mm, alpha=0.30, steps=48, bg=None, rows=40):
        """Притенение у сгиба с обеих сторон — так разворот читается как
        согнутый лист, а не как два приставленных друг к другу листа. Тон
        симметричен относительно сгиба: смещение на сшивке незаметно.

        bg — фон под притенением. Если он задан, тень рисуется НЕПРОЗРАЧНЫМИ
        плашками уже смешанного цвета: PDF/X-1a живой прозрачности не
        допускает, а её сведение растрирует полосу вместе с набором.
        """
        from graphics import mix
        b = BLEED
        self.c.saveState()
        dw = w/steps
        H = PAGE_H + 2*b
        for i in range(steps):
            t = (i + 0.5)/steps                   # 0 у сгиба → 1 на краю зоны
            a = alpha*(1 - t)**1.8
            dx = w*t
            if bg is None:
                self.c.setFillColorRGB(*rgb(color), alpha=a)
                self.c.rect(FOLD - dx - dw, -b, dw, H, stroke=0, fill=1)
                self.c.rect(FOLD + dx,      -b, dw, H, stroke=0, fill=1)
                continue
            for j in range(rows):                 # фон меняется по вертикали
                yy = -b + H*j/rows
                self.c.setFillColorRGB(*rgb(mix(color, bg.at(yy + H/rows/2), a)))
                self.c.rect(FOLD - dx - dw, yy, dw, H/rows + 0.6, stroke=0, fill=1)
                self.c.rect(FOLD + dx,      yy, dw, H/rows + 0.6, stroke=0, fill=1)
        self.c.restoreState()

    # ── служебные элементы ───────────────────────────────────────────────
    def heads(self, section_l, section_r, dark=True, rule=True):
        """Шапка разворота: название раздела у внешнего края каждой полосы и
        одна линейка, идущая через сгиб. Линейка и есть главная связка:
        две полосы висят на общей горизонтали."""
        muted = C.MUTED_D if dark else C.MUTED_L
        line  = C.LINE_D  if dark else C.LINE_L
        y = PAGE_H - MARGIN_TOP
        for side, sec in ((L, section_l), (R, section_r)):
            if not sec:
                continue
            _, ox = edges(side)
            # к внешнему краю: на левой полосе он слева, на правой справа
            self.text(sec.upper(), ox, y, T.FONT_MED, T.MICRO, muted,
                      track=T.TRACK_CAPS, align='l' if side == L else 'r')
        if rule:
            x, w = across()
            self.rule(x, y - 7, w, line, 0.5)
        return y - 7

    def folios(self, n_left, dark=True):
        """Колонцифры во внешних нижних углах — по-книжному. На левой полосе
        чётный номер у левого обреза, на правой нечётный у правого."""
        muted = C.MUTED_D if dark else C.MUTED_L
        y = MARGIN_BOTTOM - 8*mm
        for side, num in ((L, n_left), (R, n_left + 1)):
            _, ox = edges(side)
            self.text(f'{num:02d}', ox, y, T.FONT_BLACK, T.SMALL, muted,
                      track=20, align='l' if side == L else 'r')

    def title(self, side, rows, y=None, size=None, dark=True, font=None,
              span=12, track=-6):
        """Заголовок на полосе разворота: кегль подбирается под наборную
        полосу этой полосы, а не под абстрактную ширину А4."""
        y = Y_TITLE if y is None else y
        x, w = px(side, 0, span)
        f = font or T.FONT_BLACK
        s = size or self.fit_size(rows, w, f, T.H1, track=track)
        col = C.WHITE if dark else C.INK
        self.lines(rows, x, y, f, s, col, T.LEAD_H1, track=track)
        return y - (len(rows) - 1)*s*T.LEAD_H1

    def eyebrow(self, side, s, y=None, dark=True, col=None):
        """Надзаголовок капителью — ступень между колонтитулом и заголовком."""
        y = Y_EYEBROW if y is None else y
        x, _ = px(side, 0, 12)
        self.text(s, x, y, T.FONT_MED, T.MICRO,
                  col or (C.ORANGE if dark else C.ORANGE), track=T.TRACK_CAPS)

    def label(self, s, x, y, font, size, color, track=0):
        """Подпись, центрированная по x, но не выходящая за наборную полосу
        своей полосы. У сгиба центрированная подпись заезжает в корешок —
        здесь она сама отходит внутрь, а не ставится «на глаз»."""
        from reportlab.pdfbase import pdfmetrics
        w = pdfmetrics.stringWidth(s, font, size) + track*size/1000.0*max(len(s)-1, 0)
        side = L if x < FOLD else R
        inner, outer = edges(side)
        lo, hi = (min(outer, inner), max(outer, inner))
        x0 = min(max(x - w/2, lo), hi - w)
        return self.text(s, x0, y, font, size, color, track)

    def rule_across(self, y, color, weight=0.5):
        x, w = across()
        self.rule(x, y, w, color, weight)

    def rule_page(self, side, y, color, weight=0.5, span=12):
        x, w = px(side, 0, span)
        self.rule(x, y, w, color, weight)


# ── сборка ───────────────────────────────────────────────────────────────

def _clip(c, x0, x1):
    p = c.beginPath()
    p.rect(x0, -BLEED, x1 - x0, PAGE_H + 2*BLEED)
    c.clipPath(p, stroke=0, fill=0)

def build(draw, out_dir, name, pages=True, spread=True):
    """Нарисовать разворот и сохранить нужные файлы.

    draw(s) — функция вёрстки, получает объект Spread в координатах
    разворота. Вызывается отдельно для каждого файла: канва у ReportLab
    одноразовая, а вёрстка должна остаться той же.
    """
    fonts()
    os.makedirs(out_dir, exist_ok=True)
    made = []
    B, PGS = BLEED, (PAGE_W + 2*BLEED, PAGE_H + 2*BLEED)

    if pages:
        # Левая полоса: координаты разворота совпадают с координатами полосы.
        for side in (L, R):
            path = f'{out_dir}/{name}_{side}.pdf'
            c = canvas.Canvas(path, pagesize=PGS)
            c.translate(B if side == L else B - PAGE_W, B)
            x0 = -B if side == L else PAGE_W - B
            _clip(c, x0, x0 + PAGE_W + 2*B)
            draw(Spread(c, side))
            c.showPage(); c.save(); boxes(path); made.append(path)

    if spread:
        path = f'{out_dir}/{name}_spread.pdf'
        c = canvas.Canvas(path, pagesize=(SPREAD_W + 2*B, PAGE_H + 2*B))
        c.translate(B, B)
        draw(Spread(c))
        c.showPage(); c.save(); boxes(path); made.append(path)

    return made
