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

def italic(c, t, x_pt, y_pt, size, font, rgb):
    c.setFillColorRGB(*rgb); c.setFont(font, size)
    c.saveState(); c.translate(x_pt, y_pt); c.transform(1, 0, 0.18, 1, 0, 0)
    c.drawString(0, 0, t); c.restoreState()

# ---------------- Стр. 3 — разделитель / оглавление ----------------
def divider(out='build/page03.pdf'):
    c = canvas.Canvas(out, pagesize=(PW, PH))
    bg_gradient(c, [(0.0, G_TOP), (0.6, G_MID), (1.0, (0.30,0.22,0.48))])
    # субтильная опора справа
    tower(c, PW*0.86, PH*0.12, PH*0.5, 60, rgb=(0.62,0.64,0.82), lw=1.2)
    # логотип
    place_svg(c, 'assets/logo_vector_orange.svg', PW-190, PH-96, 150)
    # заголовок
    c.setFillColorRGB(*WHITE)
    ts = max(size_for(t,'Onest-ExtraBold',w) for (t,w) in [('КОМПЛЕКСНОЕ',629),('СТРОИТЕЛЬСТВО',710)])
    c.setFont('Onest-ExtraBold', ts)
    c.drawString(X(107), Y(384), 'КОМПЛЕКСНОЕ'); c.drawString(X(104), Y(468), 'СТРОИТЕЛЬСТВО')
    # оглавление 01/02/03
    items = [('01','Объекты энергетики'), ('02','Промышленные объекты'), ('03','Объекты гражданского назначения')]
    ys = [PH*0.52, PH*0.36, PH*0.20]
    for (num, lab), yb in zip(items, ys):
        italic(c, num, X(107), yb, 66, 'Onest-ExtraBold', ORANGE)
        c.setStrokeColorRGB(*ORANGE); c.setLineWidth(2); c.line(X(112), yb-14, X(240), yb-14)
        c.setFillColorRGB(*WHITE); c.setFont('Onest-Medium', 20); c.drawString(X(112), yb-40, lab)
    c.showPage(); c.save(); print('divider ok')

# ---------------- Стр. 6 — достижения на «чертёжном» векторном фоне ----------------
def blueprint_bg(c):
    from reportlab.lib.colors import Color
    c.linearGradient(0, PH, 0, 0, [Color(0.07,0.06,0.17), Color(0.16,0.12,0.32), Color(0.10,0.09,0.24)], [0,0.5,1], extend=True)
    # сетка
    c.setStrokeColorRGB(1,1,1); c.setLineWidth(0.4); c.setStrokeAlpha(0.06)
    step = 26
    x = 0
    while x < PW: c.line(x,0,x,PH); x += step
    y = 0
    while y < PH: c.line(0,y,PW,y); y += step
    # схематические окружности/линии (намёк на чертёж)
    c.setStrokeAlpha(0.10); c.setLineWidth(1.0)
    for (cx,cy,r) in [(PW*0.2,PH*0.72,60),(PW*0.8,PH*0.3,80),(PW*0.7,PH*0.8,45)]:
        c.circle(cx,cy,r,stroke=1,fill=0); c.circle(cx,cy,r*0.5,stroke=1,fill=0)
    c.setStrokeAlpha(1)

def achievements(out='build/page06.pdf'):
    c = canvas.Canvas(out, pagesize=(PW, PH))
    blueprint_bg(c)
    rows = [
        ('25 800 км', 'протянуто проводов на воздушных ЛЭП'),
        ('413 278', 'опор ЛЭП использовано при строительстве'),
        ('1224', 'ПС, ТП, РП построено объектов'),
        ('502 000', 'объектов подключено к электрическим сетям'),
        ('ГНБ прокол 339 км', None),
        ('16 298 м²', 'построено и введено в эксплуатацию промышленных и гражданских площадей'),
    ]
    n = len(rows); top = PH*0.86; gap = (top - PH*0.12)/(n-1)
    for i,(num,cap) in enumerate(rows):
        yb = top - i*gap
        nw = pdfmetrics.stringWidth(num, 'Onest-ExtraBold', 26)
        italic(c, num, PW/2 - nw/2, yb, 26, 'Onest-ExtraBold', ORANGE)
        if cap:
            c.setFillColorRGB(*WHITE); c.setFont('Onest-Regular', 12.5)
            cw = pdfmetrics.stringWidth(cap, 'Onest-Regular', 12.5)
            if cw > PW*0.8:  # перенос длинной подписи
                words = cap.split(); mid = len(words)//2+1
                l1=' '.join(words[:mid]); l2=' '.join(words[mid:])
                for k,l in enumerate([l1,l2]):
                    w=pdfmetrics.stringWidth(l,'Onest-Regular',12.5); c.drawString(PW/2-w/2, yb-20-k*16, l)
            else:
                c.drawString(PW/2-cw/2, yb-20, cap)
    c.showPage(); c.save(); print('achievements ok')

# ---------------- Стр. 2 — фонд «Энергия Русского духа» ----------------
def charity(out='build/page02.pdf'):
    sys.path.insert(0, 'scripts')
    import build_page02 as bp
    c = canvas.Canvas(out, pagesize=(PW, PH))
    bg_gradient(c, [(0.0, G_TOP), (0.5, (0.22,0.16,0.40)), (1.0, (0.34,0.24,0.46))])
    tower(c, PW*0.9, PH*0.1, PH*0.42, 52, rgb=(0.58,0.6,0.8), lw=1.0)
    # герб фонда (временная вырезка на прозрачном — нужен ВЕКТОР от самого фонда)
    fw = (722-100)  # px ширины лок-апа в исходнике
    ar = 0.277
    c.drawImage('assets/fund_logo_keyed.png', X(100), Y(66) - fw*ar*SX,
                width=fw*SX, height=fw*ar*SX, mask='auto')
    # текст/иконки — как в build_page02, но поверх вектор-фона
    for cx, cy, fn in bp.ICONS:
        c.setFillColorRGB(*ORANGE); c.circle(X(cx), Y(cy), 26*SX, stroke=0, fill=1)
        fn(c, cx, cy, 26)
    for (t, b, x, sz, f, rgb) in bp.__dict__.get('BODY', []) or []:
        pass
    # тексты (совпадают с build_page02.body)
    body = [
        ('Входим в попечительский совет', 340, 116, 18.57, 'Onest-ExtraBold', WHITE),
        ('благотворительного фонда', 380, 115, 18.57, 'Onest-ExtraBold', WHITE),
        ('«Энергия Русского духа»', 419, 115, 18.57, 'Onest-ExtraBold', WHITE),
        ('Миссии фонда', 513, 116, 18.24, 'Onest-ExtraBold', ORANGE),
        ('Миссия 1', 606, 195, 13.79, 'Onest-ExtraBold', ORANGE),
        ('Миссия 2', 828, 195, 13.79, 'Onest-ExtraBold', ORANGE),
        ('Миссия 3', 1081, 195, 13.79, 'Onest-ExtraBold', ORANGE),
        ('Содействие в восстановлении благополучия', 668, 116, 11.92, 'Onest-Regular', WHITE),
        ('работников энергетической отрасли и их семей,', 695, 116, 11.92, 'Onest-Regular', WHITE),
        ('пострадавших в результате событий, связанных', 722, 116, 11.92, 'Onest-Regular', WHITE),
        ('с проведением специальной военной операции', 749, 116, 11.92, 'Onest-Regular', WHITE),
        ('Обеспечение необходимой медицинской,', 892, 116, 11.92, 'Onest-Regular', WHITE),
        ('социальной и материальной помощи работникам', 918, 116, 11.92, 'Onest-Regular', WHITE),
        ('отрасли для преодоления травм, полученных в результате', 948, 116, 11.92, 'Onest-Regular', WHITE),
        ('событий, связанных с проведением специальной военной', 972, 116, 11.92, 'Onest-Regular', WHITE),
        ('операции, и возвращения к полноценной жизни', 1000, 116, 11.92, 'Onest-Regular', WHITE),
        ('Восстановление психологического здоровья', 1142, 118, 11.92, 'Onest-Regular', WHITE),
        ('и душевного равновесия работников энергетической', 1169, 118, 11.92, 'Onest-Regular', WHITE),
        ('отрасли, пострадавших в результате событий, связанных', 1196, 117, 11.92, 'Onest-Regular', WHITE),
        ('с проведением специальной военной операции', 1224, 117, 11.92, 'Onest-Regular', WHITE),
        ('https://эрдфонд.рф/', 1315, 116, 11.61, 'Onest-Regular', ORANGE),
    ]
    for (t, b, x, sz, f, rgb) in body:
        c.setFillColorRGB(*rgb); c.setFont(f, sz); c.drawString(X(x), Y(b), t)
    c.showPage(); c.save(); print('charity ok')

if __name__ == '__main__':
    import sys
    which = sys.argv[1:] or ['1','2','3','6']
    if '1' in which: cover()
    if '2' in which: charity()
    if '3' in which: divider()
    if '6' in which: achievements()
