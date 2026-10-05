# -*- coding: utf-8 -*-
"""
Отрисовка полос нового каталога. Печатная ветка: сразу в PDF, вектор.

Полоса собирается размером обрез+вылет, содержимое сдвинуто внутрь, TrimBox
по обрезу. Так вылет получается без масштабирования вёрстки — тем же способом,
каким собран прежний печатный файл.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
import pikepdf
from ds import *

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_reg = False

def fonts():
    global _reg
    if _reg: return
    base = f'{ROOT}/fonts/static' if os.path.isdir(f'{ROOT}/fonts/static') else f'{ROOT}/fonts'
    for w in ['Regular','Medium','SemiBold','Bold','ExtraBold']:
        pdfmetrics.registerFont(TTFont('Onest-'+w, f'{base}/Onest-{w}.ttf'))
    _reg = True

class Page:
    """Полоса с вылетом. Начало координат — левый нижний угол ОБРЕЗА."""
    def __init__(self, path, left_page=False):
        fonts()
        self.path, self.left = path, left_page
        self.c = canvas.Canvas(path, pagesize=(PAGE_W+2*BLEED, PAGE_H+2*BLEED))
        self.c.translate(BLEED, BLEED)

    # — фон —
    def fill(self, color, bleed=True):
        b = BLEED if bleed else 0
        self.c.setFillColorRGB(*rgb(color))
        self.c.rect(-b, -b, PAGE_W+2*b, PAGE_H+2*b, stroke=0, fill=1)

    def image(self, path, x, y, w, h, bleed_sides=()):
        """Фото. bleed_sides: 'l','r','t','b' — стороны, уходящие под обрез."""
        x -= BLEED if 'l' in bleed_sides else 0
        y -= BLEED if 'b' in bleed_sides else 0
        w += (BLEED if 'l' in bleed_sides else 0) + (BLEED if 'r' in bleed_sides else 0)
        h += (BLEED if 'b' in bleed_sides else 0) + (BLEED if 't' in bleed_sides else 0)
        self.c.drawImage(path, x, y, width=w, height=h, mask=None)

    def veil(self, color, alpha, x=None, y=None, w=None, h=None):
        """Полупрозрачная вуаль поверх фото, чтобы текст читался."""
        self.c.saveState(); self.c.setFillColorRGB(*rgb(color), alpha=alpha)
        self.c.rect(x if x is not None else -BLEED, y if y is not None else -BLEED,
                    w if w is not None else PAGE_W+2*BLEED,
                    h if h is not None else PAGE_H+2*BLEED, stroke=0, fill=1)
        self.c.restoreState()

    # — текст —
    def text(self, s, x, y, font, size, color, track=0, align='l'):
        """Строка с трекингом. ReportLab задаёт межбуквенный интервал только
        через текстовый объект, у канвы такого метода нет."""
        sp = track*size/1000.0
        w = pdfmetrics.stringWidth(s, font, size) + sp*max(len(s)-1, 0)
        if   align == 'r': x -= w
        elif align == 'c': x -= w/2
        self.c.setFillColorRGB(*rgb(color))
        t = self.c.beginText(x, y)
        t.setFont(font, size)
        if sp: t.setCharSpace(sp)
        t.textOut(s)
        self.c.drawText(t)
        return w

    def fit_size(self, rows, width, font, size_max, track=0):
        """Наибольший кегль, при котором самая длинная строка влезает в width.

        Без этого крупная типографика разъезжается: кегль, подобранный на
        глаз под одну строку, другую выносит за поле.
        """
        size = size_max
        while size > 6:
            w = max(pdfmetrics.stringWidth(r, font, size) + track*size/1000.0*max(len(r)-1,0)
                    for r in rows)
            if w <= width: break
            size -= 0.5
        return size

    def lines(self, rows, x, y, font, size, color, lead, track=0, align='l'):
        """Несколько строк вниз от y с заданным интерлиньяжем."""
        for i, s in enumerate(rows):
            self.text(s, x, y - i*size*lead, font, size, color, track, align)
        return y - (len(rows)-1)*size*lead

    def rule(self, x, y, w, color, weight=0.6):
        self.c.setStrokeColorRGB(*rgb(color)); self.c.setLineWidth(weight)
        self.c.line(x, y, x+w, y)

    def save(self):
        self.c.showPage(); self.c.save()
        with pikepdf.open(self.path, allow_overwriting_input=True) as pdf:
            for p in pdf.pages:
                mb = [float(v) for v in p.MediaBox]
                p.BleedBox = pikepdf.Array(mb); p.CropBox = pikepdf.Array(mb)
                p.TrimBox = pikepdf.Array([mb[0]+BLEED, mb[1]+BLEED,
                                           mb[2]-BLEED, mb[3]-BLEED])
            pdf.save(self.path)
        return self.path

def preview(pdf, png, width=1400):
    import pymupdf, numpy as np, cv2
    p = pymupdf.open(pdf)[0]
    z = width/p.trimbox.width
    px = p.get_pixmap(matrix=pymupdf.Matrix(z,z), clip=p.trimbox)
    a = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width, px.n)
    cv2.imwrite(png, a[:,:,:3][:,:,::-1], [int(cv2.IMWRITE_JPEG_QUALITY), 93])
    return png


# ── Компоненты полосы ────────────────────────────────────────────────────

class Slide(Page):
    """Полоса каталога с общими элементами: колонтитул, шапка раздела, цифры."""

    def header(self, num, section, dark=True):
        """Колонтитул: номер раздела слева, название справа, линейка под ними."""
        from ds import C, T, S, MARGIN_TOP, MARGIN_OUTER, PAGE_W, PAGE_H, col_x
        muted = C.MUTED_D if dark else C.MUTED_L
        line  = C.LINE_D  if dark else C.LINE_L
        x, _  = col_x(0, 12)
        right = PAGE_W - MARGIN_OUTER
        y = PAGE_H - MARGIN_TOP
        self.text(num, x, y, T.FONT_BLACK, 13, C.ORANGE, track=20)
        self.text(section.upper(), right, y, T.FONT_MED, T.MICRO, muted,
                  track=T.TRACK_CAPS, align='r')
        self.rule(x, y - 7, right - x, line, 0.5)
        return y - 7

    def title(self, rows, y, size=None, dark=True, font=None):
        """Заголовок полосы: кегль подбирается под ширину наборной полосы."""
        from ds import C, T, MARGIN_OUTER, PAGE_W, col_x
        x, _  = col_x(0, 12)
        right = PAGE_W - MARGIN_OUTER
        f = font or T.FONT_BLACK
        s = size or self.fit_size(rows, right - x, f, T.H1, track=-6)
        col = C.WHITE if dark else C.INK
        self.lines(rows, x, y, f, s, col, T.LEAD_H1, track=-6)
        return y - (len(rows)-1)*s*T.LEAD_H1

    def stat(self, x, y, num, cap, size=34, dark=True, cap_w=None):
        """Цифра с подписью. Подпись сидит на фиксированном расстоянии от
        базовой линии числа, иначе колонки цифр разной высоты разъезжаются."""
        from ds import C, T, mm
        muted = C.MUTED_D if dark else C.MUTED_L
        self.text(num, x, y, T.FONT_BLACK, size, C.ORANGE, track=-12)
        self.lines(cap if isinstance(cap, list) else [cap],
                   x, y - 7.5*mm, T.FONT_BOOK, T.SMALL, muted, T.LEAD_SMALL)
        return y - 7.5*mm

    def wrap(self, text, width, font, size):
        """Разбить строку по ширине колонки. Без этого длинный пункт
        вылезает за поле и наезжает на соседнюю колонку."""
        words = text.split()
        rows, cur = [], ''
        for w in words:
            t = (cur + ' ' + w).strip()
            if pdfmetrics.stringWidth(t, font, size) <= width or not cur:
                cur = t
            else:
                rows.append(cur); cur = w
        if cur: rows.append(cur)
        return rows

    def numbered(self, i, x, y, text, dark=True, size=None, num_w=None,
                 width=None, lead=None):
        """Строка нумерованного перечня: номер оранжевым, текст рядом."""
        from ds import C, T, mm
        col = C.WHITE if dark else C.INK
        n = f'{i:02d}'
        sz = size or T.H3
        nw = num_w or 13*mm
        self.text(n, x, y, T.FONT_BLACK, T.H3, C.ORANGE, track=10)
        rows = self.wrap(text, width - nw, T.FONT_BOOK, sz) if width else [text]
        self.lines(rows, x + nw, y, T.FONT_BOOK, sz, col, lead or T.LEAD_SMALL)
        return y - (len(rows)-1)*sz*(lead or T.LEAD_SMALL)

    def bars(self, x, y, w, h, data, dark=True, label_every=1):
        """Столбчатая диаграмма: подписи значений над столбцами, годы снизу."""
        from ds import C, T, mm
        muted = C.MUTED_D if dark else C.MUTED_L
        n = len(data)
        gap = w*0.030
        bw  = (w - gap*(n-1))/n
        vmax = max(v for _, v, _ in data)
        for i, (year, val, label) in enumerate(data):
            bx = x + i*(bw + gap)
            bh = h*(val/vmax)
            self.c.setFillColorRGB(*[v/255 for v in C.ORANGE])
            self.c.rect(bx, y, bw*0.76, bh, stroke=0, fill=1)
            self.c.setFillColorRGB(*[min(v*1.0 + 46, 255)/255 for v in C.ORANGE])
            self.c.rect(bx + bw*0.76, y, bw*0.24, bh, stroke=0, fill=1)
            self.text(label, bx, y + bh + 4*mm, T.FONT_SEMI, T.SMALL, muted)
            self.text(year,  bx, y - 6*mm, T.FONT_MED, T.SMALL, muted, track=20)
