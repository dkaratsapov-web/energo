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

def tower(c, cx, base_y, height, color, weight=1.0, alpha=1.0):
    """Анкерно-угловая опора ВЛ. cx — ось, base_y — пята, height — высота."""
    c.saveState()
    c.setStrokeColorRGB(*[v/255 for v in color], alpha=alpha)
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

def wire(c, x0, y0, x1, y1, sag, color, weight=0.7, alpha=1.0):
    """Провод между точками. Форма — цепная линия, как в натуре."""
    c.saveState()
    c.setStrokeColorRGB(*[v/255 for v in color], alpha=alpha)
    c.setLineWidth(weight); c.setLineCap(1)
    p = c.beginPath(); p.moveTo(x0, y0)
    for i in range(1, 49):
        t = i/48
        x = x0 + (x1-x0)*t
        y = y0 + (y1-y0)*t - sag*math.sin(math.pi*t)
        p.lineTo(x, y)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()

def grid(c, x, y, w, h, step, color, weight=0.2, alpha=0.5):
    """Технический модуль-сетка для фоновых планов."""
    c.saveState()
    c.setStrokeColorRGB(*[v/255 for v in color], alpha=alpha)
    c.setLineWidth(weight)
    n = int(w/step)+1
    for i in range(n): c.line(x+i*step, y, x+i*step, y+h)
    for j in range(int(h/step)+1): c.line(x, y+j*step, x+w, y+j*step)
    c.restoreState()
