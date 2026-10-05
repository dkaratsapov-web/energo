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
