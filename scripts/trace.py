# -*- coding: utf-8 -*-
"""
Перевод силуэтного кадра в вектор.

Работает там, где снимок по сути графичен: тёмный объект на гладком небе.
Такой кадр раскладывается на две части, и обе описываются вектором точнее,
чем исходным растром:
  • небо — плавный градиент, воспроизводится ступенями по реальным цветам;
  • силуэт — контрастная форма, обводится контурами.

Для фотографии с полутонами (офис, техника, люди) метод не годится — там
нужен оригинал съёмки.
"""
import cv2, numpy as np

def sky_profile(img, mask, steps=180):
    """Цвет неба по строкам: медиана тех пикселей, что не вошли в силуэт."""
    h, w = img.shape[:2]
    out = []
    for i in range(steps):
        y0, y1 = int(h*i/steps), max(int(h*(i+1)/steps), int(h*i/steps)+1)
        band = img[y0:y1]; mb = mask[y0:y1] == 0
        px = band[mb] if mb.sum() > 30 else band.reshape(-1, 3)
        out.append(tuple(int(v) for v in np.median(px, axis=0)[::-1]))   # RGB
    return out

def silhouette(img, thr=34, up=3, min_area=26, eps=0.75, close=3, crop_bottom=0.0):
    """Маска и контуры силуэта.

    Маска считается относительно модели неба, а не по абсолютной яркости:
    небо само градиентное, и единый порог срезал бы низ кадра.
    Перед обводкой маска увеличивается и сглаживается — иначе контур идёт
    по пикселям исходника и на печати видна ступенька.
    """
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    sky = cv2.GaussianBlur(cv2.dilate(g, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(41,41))), (81,81), 0)
    m = ((sky - g) > thr).astype(np.uint8)*255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((close,close), np.uint8))
    if crop_bottom > 0:
        # низ кадра (кусты, трава) в обводке даёт бесформенные кляксы:
        # мелкая листва на 124 dpi не имеет читаемого контура
        m[int(m.shape[0]*(1-crop_bottom)):] = 0

    big = cv2.resize(m, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (2*up+1, 2*up+1), 0)
    big = (big > 120).astype(np.uint8)*255

    cnts, hier = cv2.findContours(big, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    shapes = []                      # [(внешний контур, [просветы])]
    if hier is not None:
        keep = {}
        for i, (cnt, hh) in enumerate(zip(cnts, hier[0])):
            if cv2.contourArea(cnt) < min_area*up*up: continue
            a = cv2.approxPolyDP(cnt, eps*up, True)
            if len(a) < 3: continue
            keep[i] = (a.reshape(-1, 2).astype(np.float32)/up, hh[3])
        for i, (pts, parent) in keep.items():
            if parent >= 0: continue                     # это просвет, не форма
            holes = [q for j, (q, par) in keep.items() if par == i]
            shapes.append((pts, holes))
    return m, shapes

def draw_silhouette(c, shapes, ox, oy, w, h, src_w, src_h, color, alpha=1.0):
    """Отрисовать силуэт в заданный прямоугольник страницы.

    Форма и её просветы идут одним составным путём с заливкой «чёт-нечет»:
    только так решётка фермы остаётся ажурной. Если заливать просветы
    отдельно, под ними пришлось бы знать цвет неба — а небо градиентное,
    и опора превратилась бы в сплошное пятно.
    """
    from reportlab.pdfgen.canvas import FILL_EVEN_ODD
    sx, sy = w/src_w, h/src_h
    c.saveState()
    c.setFillColorRGB(*[v/255 for v in color], alpha=alpha)
    for pts, holes in shapes:
        p = c.beginPath()
        for ring in [pts] + holes:
            p.moveTo(ox + ring[0][0]*sx, oy + h - ring[0][1]*sy)
            for (px, py) in ring[1:]:
                p.lineTo(ox + px*sx, oy + h - py*sy)
            p.close()
        c.drawPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)
    c.restoreState()
