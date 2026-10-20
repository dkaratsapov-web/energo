# -*- coding: utf-8 -*-
"""PDF из модели слайдов.

preview — экранный файл размером слайда, RGB.
print   — обрез из требований типографии + вылеты, всё непрозрачное;
          мелкий тёмный текст сразу в одну краску K100, чтобы после перевода
          в CMYK он не превратился в четырёхкрасочный и не «поплыл» при
          несовмещении. Дальше файл идёт в ghostscript -> PDF/X-1a.
"""
import os
import pikepdf
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import FILL_EVEN_ODD
from .model import Rect, Line, Poly, Dot, Image, Text, Shape, PT
from . import fonts, images, pdfx

MM = 72 / 25.4


def _neutral_ink(col, ground):
    """Мелкий текст, который печатается краской (темнее фона) и почти серый."""
    bg = ground.bg if ground is not None else (255, 255, 255)
    return sum(col) < sum(bg) and max(col) - min(col) <= 40


def _k_of(col):
    """Доля чёрной краски для серого той же светлоты (тёмный -> K100)."""
    from .tokens import lum
    if max(col) <= 64:
        return 1.0
    return round(min(1.0, max(0.0, 1 - lum(col) ** (1 / 2.2))), 3)


class Frame:
    """Окно полотна, которое ложится на одну страницу PDF.

    Полотно — слайд, полоса или разворот (sl.w × sl.h, мм). Окно (ox, oy,
    vw, vh) — его часть, попадающая на страницу: весь слайд, или левая /
    правая полоса разворота. k — масштаб макета к обрезу, b — вылет, мм.
    Элемент, касающийся края ПОЛОТНА, уходит в вылет; у корешка вылет
    заполняется продолжением соседней полосы — так и должно быть.
    """

    def __init__(self, cw, ch, ox=0.0, oy=0.0, vw=None, vh=None, trim=None, bleed=0.0):
        self.W, self.H = cw, ch
        self.ox, self.oy = ox, oy
        self.vw, self.vh = vw or cw, vh or ch
        tw, th = trim or (self.vw, self.vh)
        self.k = tw / self.vw
        self.b = bleed
        self.pw, self.ph = tw + 2 * bleed, th + 2 * bleed
        self.ext = bleed / self.k                 # вылет в единицах макета

    def p(self, x, y):
        return ((self.b + (x - self.ox) * self.k) * MM,
                (self.ph - self.b - (y - self.oy) * self.k) * MM)

    def box(self, grow=True):
        e = self.ext if grow else 0.0
        return (self.ox - e, self.oy - e, self.ox + self.vw + e, self.oy + self.vh + e)


def _grow(fr, x, y, w, h):
    """Элемент у края полотна уходит в вылет."""
    e, eps = fr.ext, 0.05
    x0, y0, x1, y1 = x, y, x + w, y + h
    if x0 <= eps: x0 -= e
    if y0 <= eps: y0 -= e
    if x1 >= fr.W - eps: x1 += e
    if y1 >= fr.H - eps: y1 += e
    return x0, y0, x1 - x0, y1 - y0


def _clip_seg(x0, y0, x1, y1, bx0, by0, bx1, by1):
    """Лиана–Барски: отрезок внутри прямоугольника или None."""
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - bx0), (dx, bx1 - x0), (-dy, y0 - by0), (dy, by1 - y0)):
        if p == 0:
            if q < 0:
                return None
        else:
            r = q / p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                return None
    return x0 + t0 * dx, y0 + t0 * dy, x0 + t1 * dx, y0 + t1 * dy


class Ink:
    """Цвет на холст: RGB для экрана, CMYK по профилю — для печати."""

    def __init__(self, c, mode, tac):
        self.c, self.print, self.tac = c, mode == 'print', tac

    def fill(self, col):
        if self.print:
            self.c.setFillColorCMYK(*pdfx.cmyk(col, self.tac))
        else:
            self.c.setFillColorRGB(*(v / 255 for v in col))

    def stroke(self, col):
        if self.print:
            self.c.setStrokeColorCMYK(*pdfx.cmyk(col, self.tac))
        else:
            self.c.setStrokeColorRGB(*(v / 255 for v in col))


def draw_slide(c, sl, fr, mode, cache, placements, notext=False, tac=300.0, page=None):
    ink = Ink(c, mode, tac)
    box = fr.box(mode == 'print')
    c.saveState()
    cp = c.beginPath()
    bx, by = fr.p(box[0], box[3])
    cp.rect(bx, by, (box[2] - box[0]) * fr.k * MM, (box[3] - box[1]) * fr.k * MM)
    c.clipPath(cp, stroke=0, fill=0)
    for el in sl.items:
        if _outside(el, box):
            continue
        if isinstance(el, Rect):
            x, y, w, h = _grow(fr, el.x, el.y, el.w, el.h) if mode == 'print' else (el.x, el.y, el.w, el.h)
            ink.fill(el.fill)
            px, py = fr.p(x, y + h)
            c.rect(px, py, w * fr.k * MM, h * fr.k * MM, stroke=0, fill=1)
        elif isinstance(el, Line):
            s = _clip_seg(el.x0, el.y0, el.x1, el.y1, *box)
            if not s:
                continue
            ink.stroke(el.color)
            c.setLineWidth(el.width * fr.k)
            c.setLineCap(0)
            c.line(*fr.p(s[0], s[1]), *fr.p(s[2], s[3]))
        elif isinstance(el, Poly):
            pts = [p for p in el.pts]
            if not pts:
                continue
            path = c.beginPath()
            path.moveTo(*fr.p(*pts[0]))
            for q in pts[1:]:
                path.lineTo(*fr.p(*q))
            if el.closed:
                path.close()
            if el.fill:
                ink.fill(el.fill)
            if el.stroke:
                ink.stroke(el.stroke)
                c.setLineWidth(el.width * fr.k)
            c.drawPath(path, stroke=1 if el.stroke else 0, fill=1 if el.fill else 0)
        elif isinstance(el, Shape):
            path = c.beginPath()
            for cont in el.contours:
                path.moveTo(*fr.p(*cont[0]))
                for q in cont[1:]:
                    path.lineTo(*fr.p(*q))
                path.close()
            ink.fill(el.fill)
            c.drawPath(path, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)
        elif isinstance(el, Dot):
            ink.fill(el.fill)
            c.circle(*fr.p(el.cx, el.cy), el.r * fr.k * MM, stroke=0, fill=1)
        elif isinstance(el, Image):
            x, y, w, h = _grow(fr, el.x, el.y, el.w, el.h) if mode == 'print' else (el.x, el.y, el.w, el.h)
            frame = ((el.x - x) / w, (el.y - y) / h, (el.x + el.w - x) / w, (el.y + el.h - y) / h)
            dpi = 300 if mode == 'print' else 200
            f = images.prepare(el.path, w * fr.k, h * fr.k, el.focus, el.shade, dpi, cache, frame,
                               cmyk_tac=tac if mode == 'print' else None)
            px, py = fr.p(x, y + h)
            c.drawImage(f, px, py, w * fr.k * MM, h * fr.k * MM)
            cx = el.x + el.w / 2                  # снимок числится за полосой, где лежит его центр
            if not (fr.ox <= cx <= fr.ox + fr.vw):
                continue
            placements.append(dict(slide=page or sl.n, path=el.path, w_mm=w * fr.k, h_mm=h * fr.k,
                                   dpi=images.effective_dpi(el.path, w, h, el.focus)
                                   * (w / (w * fr.k))))
        elif isinstance(el, Text) and not notext:
            size = el.size * fr.k
            for i, ln in enumerate(el.lines):
                lw = el.line_w(i)
                x = {'l': el.x, 'r': el.x + el.w - lw, 'c': el.x + (el.w - lw) / 2}[el.align]
                tx, ty = fr.p(x, el.baseline(i))
                t = c.beginText(tx, ty)
                t.setFont(fonts.info(el.font)['rl'], size)
                t.setCharSpace(el.track * size)
                if mode == 'print' and size <= 12 and _neutral_ink(el.color, sl.ground):
                    # мелкий тёмный и серый набор — одной чёрной краской
                    t.setFillColorCMYK(0, 0, 0, _k_of(el.color))
                elif mode == 'print':
                    t.setFillColorCMYK(*pdfx.cmyk(el.color, tac))
                else:
                    t.setFillColorRGB(*(v / 255 for v in el.color))
                t.textLine(ln)
                c.drawText(t)
    c.restoreState()


def _outside(el, box):
    """Элемент целиком вне окна — на другой полосе разворота."""
    if isinstance(el, (Rect, Image)):
        x0, y0, x1, y1 = el.x, el.y, el.x + el.w, el.y + el.h
    elif isinstance(el, Text):
        x0, y0, x1, y1 = el.bbox()
    elif isinstance(el, Dot):
        x0, y0, x1, y1 = el.cx - el.r, el.cy - el.r, el.cx + el.r, el.cy + el.r
    elif isinstance(el, Line):
        x0, x1 = sorted((el.x0, el.x1)); y0, y1 = sorted((el.y0, el.y1))
    elif isinstance(el, Shape):
        x0, y0, x1, y1 = el.bbox()
    elif isinstance(el, Poly):
        xs = [p[0] for p in el.pts]; ys = [p[1] for p in el.pts]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    else:
        return False
    return x1 < box[0] or x0 > box[2] or y1 < box[1] or y0 > box[3]


def views(sl, W, H, mode, trim, bleed):
    """Окна полотна: на экране — целиком, в печати — по полосе."""
    cw, ch = sl.w or W, sl.h or H
    if mode not in ('print', 'pages'):
        return [(Frame(cw, ch), sl.n)]
    pages = sl.pages or (sl.n,)
    n = len(pages)
    vw = cw / n
    if mode == 'pages':          # экранные полосы по одной — для сверки с PPTX
        return [(Frame(cw, ch, i * vw, 0, vw, ch), pages[i]) for i in range(n)]
    return [(Frame(cw, ch, i * vw, 0, vw, ch, trim, bleed), pages[i]) for i in range(n)]


def render(slides, path, W, H, mode='preview', trim=None, bleed=0.0, meta=None,
           cache='/tmp/deckkit-img', notext=False, tac=300.0):
    fonts.register()
    c = canvas.Canvas(path, pageCompression=1)
    meta = meta or {}
    c.setTitle(meta.get('title', ''))
    c.setAuthor(meta.get('author', ''))
    c.setSubject(meta.get('subject', ''))
    c.setCreator('premium-deck / deckkit')
    placements = []
    sizes = []
    fr = None
    for sl in slides:
        for fr, page in views(sl, W, H, mode, trim, bleed):
            c.setPageSize((fr.pw * MM, fr.ph * MM))
            draw_slide(c, sl, fr, mode, cache, placements, notext, tac, page)
            c.showPage()
            sizes.append((fr.pw, fr.ph))
    c.save()
    if mode == 'print':
        pdf = pikepdf.open(path, allow_overwriting_input=True)
        b = bleed * MM
        for pg, (pw, ph) in zip(pdf.pages, sizes):
            mw, mh = pw * MM, ph * MM
            pg.obj.MediaBox = pikepdf.Array([0, 0, mw, mh])
            pg.obj.BleedBox = pikepdf.Array([0, 0, mw, mh])
            pg.obj.TrimBox = pikepdf.Array([b, b, mw - b, mh - b])
        pdf.save(path)
    return path, placements, fr
