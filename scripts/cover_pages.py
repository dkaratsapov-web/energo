# -*- coding: utf-8 -*-
"""Пересборка страниц 1, 2, 3 ПОЛНОСТЬЮ вектором (без фото) — печатное качество.
Фирменный градиент + мотив ЛЭП + карта РФ (из логотипа) + вектор-логотип + текст Onest."""
import sys, math
sys.path.insert(0, 'scripts')
from rebuild import register_fonts, size_for, PW, PH, SX, SY, X, Y
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

register_fonts()
ORANGE = (252/255, 144/255, 43/255)
WHITE  = (240/255, 240/255, 246/255)
# фирменные тона градиента
G_TOP = (0.086, 0.075, 0.20)     # глубокий индиго
G_MID = (0.24, 0.17, 0.42)       # фиолет
G_BOT = (0.42, 0.30, 0.60)       # тёплый фиолет

def bg_gradient(c, stops=None):
    stops = stops or [(0.0, G_TOP), (0.55, G_MID), (1.0, G_BOT)]
    cols = [(r, g, b) for (_, (r, g, b)) in stops]
    pos = [p for (p, _) in stops]
    from reportlab.lib.colors import Color
    c.linearGradient(0, PH, 0, 0, [Color(*rgb) for rgb in cols], pos, extend=True)

def place_svg(c, path, x, y, w):
    d = svg2rlg(path)
    sc = w / d.width
    c.saveState(); c.translate(x, y); c.scale(sc, sc); renderPDF.draw(d, c, 0, 0); c.restoreState()
    return d.height * sc

def map_watermark(c, x, y, w, alpha=0.10):
    """Карта РФ из белого лого как крупный водяной знак."""
    c.saveState(); c.setFillAlpha(alpha); c.setStrokeAlpha(alpha)
    place_svg(c, 'assets/logo_vector_white.svg', x, y, w)
    c.restoreState()

def tower(c, bx, by, h, base_w, rgb=WHITE, lw=1.4, arms=True):
    """Стилизованная решётчатая опора ЛЭП. bx,by — центр основания (pt)."""
    c.setStrokeColorRGB(*rgb); c.setLineWidth(lw); c.setLineCap(1); c.setLineJoin(1)
    top_w = base_w * 0.22
    def leg_x(side, t):  # t=0 низ, 1 верх
        w = base_w + (top_w - base_w) * t
        return bx + side * w / 2
    # ноги
    steps = 10
    for side in (-1, 1):
        pts = [(leg_x(side, i/steps), by + h*i/steps) for i in range(steps+1)]
        c.lines([(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]) for i in range(steps)])
    # горизонтальные пояса + X-раскосы
    for i in range(steps):
        t0, t1 = i/steps, (i+1)/steps
        xL0, xR0 = leg_x(-1, t0), leg_x(1, t0)
        xL1, xR1 = leg_x(-1, t1), leg_x(1, t1)
        y0, y1 = by + h*t0, by + h*t1
        c.line(xL0, y0, xR0, y0)                       # пояс
        c.line(xL0, y0, xR1, y1); c.line(xR0, y0, xL1, y1)  # X
    # верхний пояс
    c.line(leg_x(-1, 1), by+h, leg_x(1, 1), by+h)
    # траверсы (крестовины) с изоляторами
    tips = []
    if arms:
        for k, ay in enumerate([by + h*0.78, by + h*0.9, by + h*1.0]):
            aw = base_w * (1.4 - 0.15*k)
            c.line(bx - aw/2, ay, bx + aw/2, ay)
            c.line(bx - aw/2, ay, bx, ay - h*0.05); c.line(bx + aw/2, ay, bx, ay - h*0.05)
            tips += [(bx - aw/2, ay), (bx + aw/2, ay)]
        # вершина
        c.line(bx, by+h, bx, by+h+h*0.06)
    return tips

def catenary(c, x0, y0, x1, y1, sag, rgb=ORANGE, lw=1.2, alpha=1.0):
    c.saveState(); c.setStrokeColorRGB(*rgb); c.setLineWidth(lw); c.setStrokeAlpha(alpha)
    p = c.beginPath(); p.moveTo(x0, y0)
    n = 24
    for i in range(1, n+1):
        t = i/n; x = x0 + (x1-x0)*t
        y = y0 + (y1-y0)*t - sag*4*t*(1-t)
        p.lineTo(x, y)
    c.drawPath(p, stroke=1, fill=0); c.restoreState()

# ---------------- Стр. 1 — обложка ----------------
def cover(out='build/page01.pdf'):
    c = canvas.Canvas(out, pagesize=(PW, PH))
    bg_gradient(c)
    # мотив ЛЭП по нижней трети
    base = PH*0.30
    t1 = tower(c, PW*0.30, base, PH*0.34, 60, rgb=(0.80,0.82,0.92), lw=1.5)
    t2 = tower(c, PW*0.62, base+20, PH*0.40, 66, rgb=(0.86,0.88,0.96), lw=1.6)
    t3 = tower(c, PW*0.90, base-6, PH*0.30, 54, rgb=(0.72,0.74,0.88), lw=1.4)
    # провода между траверсами (оранжевые, разной прозрачности)
    for (a, b) in [(t1[1], t2[0]), (t2[1], t3[0])]:
        for i in range(min(len(a) if isinstance(a,tuple) else 0,0)): pass
    # берём крайние траверсы
    if t1 and t2 and t3:
        for k in range(3):
            catenary(c, t1[2*k+1][0], t1[2*k+1][1], t2[2*k][0], t2[2*k][1], 26, alpha=0.85)
            catenary(c, t2[2*k+1][0], t2[2*k+1][1], t3[2*k][0], t3[2*k][1], 22, alpha=0.7)
    # логотип-вектор в правом верхнем углу
    place_svg(c, 'assets/logo_vector_orange.svg', PW-190, PH-96, 150)
    # заголовок
    lines = [('КОМПЛЕКСНОЕ', 1506, 80, 629), ('СТРОИТЕЛЬСТВО', 1589, 77, 710)]
    ts = max(size_for(t, 'Onest-ExtraBold', w) for (t,b,x,w) in lines)
    c.setFillColorRGB(*WHITE); c.setFont('Onest-ExtraBold', ts)
    for (t,b,x,w) in lines: c.drawString(X(x), Y(b), t)
    # оранжевый акцент-линия + #2025
    c.setStrokeColorRGB(*ORANGE); c.setLineWidth(3); c.line(X(80), Y(1636), X(300), Y(1636))
    c.setFillColorRGB(*ORANGE); c.setFont('Onest-ExtraBold', 18); c.drawString(X(80), Y(1690), '#2025')
    c.showPage(); c.save(); print('cover ok')

if __name__ == '__main__':
    cover()
