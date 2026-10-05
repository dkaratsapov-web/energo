# -*- coding: utf-8 -*-
"""
Векторная графика каталога: опоры ЛЭП, провода, градиенты, сетка.

Зачем вектор вместо фотографии. Каталог пересобирается ровно потому, что
растр 150 dpi пикселит на печати, а оригиналов съёмки нет. Класть тот же
растр в новый макет бессмысленно: апскейл не создаёт детали. Поэтому там,
где кадр не несёт доказательной нагрузки (обложка, разделители, фоны),
изображение строится геометрией — оно резкое при любом увеличении и весит
килобайты.

Опора рисуется по реальной схеме анкерно-угловой опоры ВЛ 110 кВ:
сужающийся кверху ствол, раскосы крест-накрест, траверсы с изоляторами.
"""
import math
from reportlab.lib.units import mm


# ── Фон под графикой ─────────────────────────────────────────────────────
# PDF/X-1a не допускает живой прозрачности, а её сведение в ghostscript
# растрирует полосу ЦЕЛИКОМ — вместе с набором. Это ровно та болезнь, из-за
# которой каталог и переделывают, поэтому в вёрстке прозрачности нет вообще:
# полупрозрачный штрих заменяется НЕПРОЗРАЧНЫМ цветом, уже смешанным с фоном.
# Для этого графике нужно знать, на что она ложится.

class Bg:
    """Фон полосы: плоский цвет или вертикальный градиент.

    Bg(color)                       — плоская заливка;
    Bg(top, bottom, y0, h)          — градиент от top сверху до bottom снизу.
    """
    def __init__(self, top, bottom=None, y0=0.0, h=1.0):
        self.top, self.bottom = top, bottom if bottom is not None else top
        self.y0, self.h = y0, max(h, 1e-6)

    def at(self, y):
        t = min(max((self.y0 + self.h - y)/self.h, 0.0), 1.0)
        return tuple(self.top[k] + (self.bottom[k] - self.top[k])*t for k in range(3))


def mix(fg, bg, a):
    """Цвет штриха прозрачностью a поверх фона bg — но непрозрачный."""
    a = min(max(a, 0.0), 1.0)
    return tuple(fg[k]*a + bg[k]*(1 - a) for k in range(3))


def _rgb(col):
    return [v/255 for v in col]

def gradient(c, x, y, w, h, top, bottom, steps=256):
    """Вертикальный градиент заливкой. Полос на печати не даёт: шаг
    перекрывается на полпикселя, а 256 ступеней мельче растровой точки."""
    for i in range(steps):
        t = i/(steps-1)
        col = [ (top[k] + (bottom[k]-top[k])*t)/255 for k in range(3) ]
        c.setFillColorRGB(*col)
        yy = y + h*(1 - (i+1)/steps)
        c.rect(x, yy, w, h/steps + 0.6, stroke=0, fill=1)

def _lat(c, x0, y0, x1, y1, w0, w1, bays, weight):
    """Секция решётчатого ствола: пояса и раскосы крест-накрест."""
    for i in range(bays):
        t0, t1 = i/bays, (i+1)/bays
        xa0, xa1 = x0 + (x1-x0)*t0, x0 + (x1-x0)*t1
        ya0, ya1 = y0 + (y1-y0)*t0, y0 + (y1-y0)*t1
        ha0, ha1 = (w0 + (w1-w0)*t0)/2, (w0 + (w1-w0)*t1)/2
        c.setLineWidth(weight*0.62)
        c.line(xa0-ha0, ya0, xa1+ha1, ya1)      # раскос вправо
        c.line(xa0+ha0, ya0, xa1-ha1, ya1)      # раскос влево
        c.setLineWidth(weight)
        c.line(xa0-ha0, ya0, xa1-ha1, ya1)      # пояса
        c.line(xa0+ha0, ya0, xa1+ha1, ya1)
        c.setLineWidth(weight*0.62)
        c.line(xa1-ha1, ya1, xa1+ha1, ya1)      # распорка

def tower(c, cx, base_y, height, color, weight=1.0, alpha=1.0, bg=None):
    """Анкерно-угловая опора ВЛ. cx — ось, base_y — пята, height — высота.

    bg — фон, на который ложится опора: цвет штриха считается смешанным,
    без прозрачности (см. Bg).
    """
    c.saveState()
    if bg is not None:
        color, alpha = mix(color, bg.at(base_y + height*0.5), alpha), 1.0
    c.setStrokeColorRGB(*_rgb(color), alpha=alpha)
    c.setLineCap(1)

    w_base, w_waist, w_top = height*0.30, height*0.105, height*0.075
    y_waist = base_y + height*0.46
    y_top   = base_y + height

    _lat(c, cx, base_y, cx, y_waist, w_base, w_waist, 5, weight)
    _lat(c, cx, y_waist, cx, y_top,  w_waist, w_top,  4, weight)

    # траверсы: нижняя длиннее верхней
    for y_rel, arm_rel in ((0.62, 0.46), (0.86, 0.33)):
        y   = base_y + height*y_rel
        arm = height*arm_rel
        hw  = (w_waist + (w_top-w_waist)*((y_rel-0.46)/0.54))/2
        for s in (-1, 1):
            xe = cx + s*arm
            c.setLineWidth(weight)
            c.line(cx + s*hw, y, xe, y)                       # пояс траверсы
            c.setLineWidth(weight*0.62)
            c.line(cx + s*hw, y + height*0.052, xe, y)        # подкос сверху
            c.line(cx + s*hw, y - height*0.030, xe, y)        # подкос снизу
            for k in (0.42, 0.72):                            # стойки решётки
                xk = cx + s*(hw + (arm-hw)*k)
                c.line(xk, y, cx + s*hw, y + height*0.052*(1-k))
            # гирлянда изоляторов и провод
            c.setLineWidth(weight*0.9)
            c.line(xe, y, xe, y - height*0.075)
            c.setLineWidth(weight*0.55)
            for j in range(4):
                yy = y - height*0.018 - j*height*0.0165
                c.line(xe - height*0.011, yy, xe + height*0.011, yy)
    # молниезащитный трос
    c.setLineWidth(weight*0.8)
    c.line(cx, y_top, cx, y_top + height*0.055)
    c.restoreState()

def wire(c, x0, y0, x1, y1, sag, color, weight=0.7, alpha=1.0, bg=None):
    """Провод между точками. Форма — цепная линия, как в натуре."""
    c.saveState()
    if bg is not None:
        color, alpha = mix(color, bg.at((y0 + y1)/2 - sag*0.6), alpha), 1.0
    c.setStrokeColorRGB(*_rgb(color), alpha=alpha)
    c.setLineWidth(weight); c.setLineCap(1)
    p = c.beginPath(); p.moveTo(x0, y0)
    for i in range(1, 49):
        t = i/48
        x = x0 + (x1-x0)*t
        y = y0 + (y1-y0)*t - sag*math.sin(math.pi*t)
        p.lineTo(x, y)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()

def grid(c, x, y, w, h, step, color, weight=0.2, alpha=0.5, bg=None):
    """Технический модуль-сетка для фоновых планов."""
    c.saveState()
    if bg is not None:
        color, alpha = mix(color, bg.at(y + h/2), alpha), 1.0
    c.setStrokeColorRGB(*_rgb(color), alpha=alpha)
    c.setLineWidth(weight)
    n = int(w/step)+1
    for i in range(n): c.line(x+i*step, y, x+i*step, y+h)
    for j in range(int(h/step)+1): c.line(x, y+j*step, x+w, y+j*step)
    c.restoreState()


# ── Генеративная графика ─────────────────────────────────────────────────

def _noise2(x, y, seed=0):
    """Гладкое псевдослучайное поле: сумма синусов с несоизмеримыми частотами.
    Даёт органичное течение без периодических повторов, видимых глазу."""
    s = seed*0.37
    return (math.sin(x*1.00 + s) * math.cos(y*0.73 - s*1.3) +
            math.sin(x*2.17 - y*1.31 + s*0.7) * 0.55 +
            math.sin(y*3.07 + x*0.41 - s*2.1) * 0.28 +
            math.sin((x+y)*4.73 + s*3.3) * 0.14)

def flow_field(c, x, y, w, h, n=520, seed=7, base=(150,160,210), accent=(224,135,47),
               accent_ratio=0.07, scale=0.9, steps=120, step_len=None,
               weight=(0.22, 0.75), alpha=(0.05, 0.42)):
    """Поток линий вдоль векторного поля.

    Линии стартуют от нижней кромки и текут вверх, подчиняясь полю; часть
    подсвечена фирменным оранжевым. Плотность и прозрачность растут к низу —
    так графика уплотняется там, где лежит заголовок, и уходит в фон вверху.
    """
    import random
    rnd = random.Random(seed)
    step_len = step_len or h/steps*1.15
    c.saveState(); c.setLineCap(1)
    for i in range(n):
        # больше линий у нижней кромки: распределение смещено вниз
        px = x - w*0.12 + rnd.random()*w*1.24
        py = y - h*0.05 + (rnd.random()**2.2)*h*1.05
        t = (py - y)/h                      # 0 — низ, 1 — верх
        is_acc = rnd.random() < accent_ratio
        col = accent if is_acc else base
        a = alpha[0] + (alpha[1]-alpha[0])*(1-t)**1.7
        if is_acc: a = min(a*1.9, 0.72)
        lw = weight[0] + (weight[1]-weight[0])*rnd.random()
        if is_acc: lw *= 1.25
        c.setStrokeColorRGB(*[v/255 for v in col], alpha=a)
        c.setLineWidth(lw)
        p = c.beginPath(); p.moveTo(px, py)
        cx, cy = px, py
        for _ in range(int(steps*(0.35 + 0.65*rnd.random()))):
            ang = _noise2(cx/w*scale*6.0, cy/h*scale*6.0, seed) * 0.9 + 1.18
            cx += math.cos(ang)*step_len
            cy += math.sin(ang)*step_len
            if not (x-w*0.2 < cx < x+w*1.2 and y-h*0.2 < cy < y+h*1.2): break
            p.lineTo(cx, cy)
        c.drawPath(p, stroke=1, fill=0)
    c.restoreState()

def nodes(c, pts, color, r=1.5, glow=True, alpha=0.9, bg=None):
    """Узлы сети: точка с мягким ореолом из концентрических кругов.

    Без фона круги накладываются прозрачностью. С фоном каждый круг рисуется
    непрозрачно, но своим НАКОПЛЕННЫМ цветом: круг j перекрыт всеми кругами
    меньшего радиуса, значит его видимая прозрачность 1-(1-a)^(8-j).
    """
    c.saveState()
    for (px, py, k) in pts:
        if glow:
            for j in range(7, 0, -1):
                a = alpha*0.045*k
                if bg is None:
                    c.setFillColorRGB(*_rgb(color), alpha=a)
                else:
                    c.setFillColorRGB(*_rgb(mix(color, bg.at(py),
                                                1 - (1 - a)**(8 - j))))
                c.circle(px, py, r*k*(1 + j*0.85), stroke=0, fill=1)
        a = min(alpha*k, 1)
        if bg is None:
            c.setFillColorRGB(*_rgb(color), alpha=a)
        else:
            c.setFillColorRGB(*_rgb(mix(color, bg.at(py), a)))
        c.circle(px, py, r*k, stroke=0, fill=1)
    c.restoreState()


def field_lines(c, x, y, w, h, rows=46, seed=3, base=(132,146,205), accent=(224,135,47),
                accent_rows=(7, 19, 33), amp=(4, 26), alpha=(0.08, 0.34), weight=0.5,
                bg=None):
    """Силовые линии: горизонтальные волны разной амплитуды и фазы.

    В отличие от свободного потока линии не сбиваются в жгуты и не спорят
    с набором — поле читается как ровная ритмическая структура.
    """
    import random
    rnd = random.Random(seed)
    c.saveState(); c.setLineCap(1)
    for i in range(rows):
        t  = i/(rows-1)
        yy = y + h*t
        a  = amp[0] + (amp[1]-amp[0])*abs(math.sin(t*math.pi*1.3 + 0.4))
        ph = rnd.random()*math.tau
        fr = 1.1 + rnd.random()*1.5
        acc = i in accent_rows
        col = accent if acc else base
        al  = (alpha[0] + (alpha[1]-alpha[0])*(1-abs(t-0.5)*1.4))
        a = min(al*(2.1 if acc else 1), 0.8)
        if bg is None:
            c.setStrokeColorRGB(*_rgb(col), alpha=a)
        else:
            c.setStrokeColorRGB(*_rgb(mix(col, bg.at(yy), a)))
        c.setLineWidth(weight*(1.5 if acc else 1) * (0.6 + rnd.random()*0.8))
        p = c.beginPath(); p.moveTo(x, yy)
        for k in range(1, 97):
            tx = k/96
            px = x + w*tx
            py = yy + math.sin(tx*math.pi*fr + ph)*a + math.sin(tx*math.pi*fr*2.7 + ph*1.7)*a*0.22
            p.lineTo(px, py)
        c.drawPath(p, stroke=1, fill=0)
    c.restoreState()

def network(c, x, y, w, h, n=34, seed=5, base=(132,146,205), accent=(224,135,47),
            link_dist=0.30, alpha_link=0.30, alpha_node=0.85):
    """Граф энергосистемы: узлы и связи между близкими. Узлы покрупнее —
    оранжевые, как опорные подстанции."""
    import random
    rnd = random.Random(seed)
    pts = []
    for i in range(n):
        pts.append((x + rnd.random()*w, y + rnd.random()*h,
                    0.35 + rnd.random()**2.2 * 1.5))
    d_max = link_dist*math.hypot(w, h)
    c.saveState(); c.setLineCap(1)
    for i, (x1, y1, k1) in enumerate(pts):
        for (x2, y2, k2) in pts[i+1:]:
            d = math.hypot(x2-x1, y2-y1)
            if d > d_max: continue
            f = 1 - d/d_max
            big = (k1 > 1.1 and k2 > 1.1)
            c.setStrokeColorRGB(*[v/255 for v in (accent if big else base)],
                                alpha=alpha_link*f*(1.5 if big else 1))
            c.setLineWidth(0.25 + f*0.55)
            c.line(x1, y1, x2, y2)
    c.restoreState()
    nodes(c, pts, accent, r=1.1, alpha=alpha_node)
