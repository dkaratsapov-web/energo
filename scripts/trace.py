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

def _chaikin(pts, iters=2):
    """Сглаживание полилинии срезанием углов. Контур, снятый с пиксельной
    маски, идёт ступеньками; approxPolyDP их не убирает, а лишь прореживает.
    Срезание углов даёт плавную кривую, не смещая форму."""
    p = pts
    for _ in range(iters):
        if len(p) < 4: break
        q = np.empty((len(p)*2, 2), np.float32)
        a = p
        b = np.roll(p, -1, axis=0)
        q[0::2] = a*0.75 + b*0.25
        q[1::2] = a*0.25 + b*0.75
        p = q
    return p

def silhouette(img, thr=34, up=6, min_area=4, eps=0.12, close=0, crop_bottom=0.0,
               smooth=2):
    """Маска и контуры силуэта.

    Маска считается относительно модели неба, а не по абсолютной яркости:
    небо само градиентное, и единый порог срезал бы низ кадра.
    Перед обводкой маска увеличивается и сглаживается — иначе контур идёт
    по пикселям исходника и на печати видна ступенька.
    """
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    sky = cv2.GaussianBlur(cv2.dilate(g, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(41,41))), (81,81), 0)
    m = ((sky - g) > thr).astype(np.uint8)*255
    if close:
        # морфология слепляет тонкие раскосы и провода, по умолчанию выключена
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    if crop_bottom > 0:
        # низ кадра (кусты, трава) в обводке даёт бесформенные кляксы:
        # мелкая листва на 124 dpi не имеет читаемого контура
        m[int(m.shape[0]*(1-crop_bottom)):] = 0

    # увеличиваем по градации серого: кубическая интерполяция восстанавливает
    # промежуточные значения на краю, и граница ложится между пикселями
    # исходника, а не по их сетке
    big = cv2.resize((sky - g), None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    big = (big > thr).astype(np.uint8)*255
    if crop_bottom > 0:
        big[int(big.shape[0]*(1-crop_bottom)):] = 0

    cnts, hier = cv2.findContours(big, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    shapes = []                      # [(внешний контур, [просветы])]
    if hier is not None:
        keep = {}
        for i, (cnt, hh) in enumerate(zip(cnts, hier[0])):
            if cv2.contourArea(cnt) < min_area*up*up: continue
            a = cv2.approxPolyDP(cnt, eps*up, True)
            if len(a) < 3: continue
            pts = a.reshape(-1, 2).astype(np.float32)
            if smooth: pts = _chaikin(pts, smooth)
            keep[i] = (pts/up, hh[3])
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


def silhouette_levels(img, levels=(0.22, 0.42, 0.66, 0.88), up=6, min_area=3,
                      eps=0.12, crop_bottom=0.0, smooth=2):
    """Многоуровневая обводка: силуэт как набор слоёв по плотности.

    Бинарный порог на тонких элементах выбирает «всё или ничего»: раскос
    шириной в полтора пикселя либо пропадает, либо раздувается. Разложение
    на несколько уровней сохраняет полутона — дальние раскосы ложатся
    светлее, ближние плотнее, и форма читается как на снимке.

    Возвращает [(доля_плотности, shapes), ...] от светлого к плотному.
    """
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    sky = cv2.GaussianBlur(cv2.dilate(g, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(41,41))), (81,81), 0)
    d = np.clip((sky - g)/max(np.percentile(sky - g, 99.5), 1e-3), 0, 1)
    big = cv2.resize(d, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    if crop_bottom > 0:
        big[int(big.shape[0]*(1-crop_bottom)):] = 0

    out = []
    for li, lv in enumerate(levels):
        m = (big > lv).astype(np.uint8)*255
        # на светлых уровнях в маску попадает шум неба — отсеиваем мелочь
        area = min_area * (5.0 if li == 0 else 2.2 if li == 1 else 1.0)
        cnts, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        keep = {}
        if hier is not None:
            for i, (cnt, hh) in enumerate(zip(cnts, hier[0])):
                if cv2.contourArea(cnt) < area*up*up: continue
                a = cv2.approxPolyDP(cnt, eps*up, True)
                if len(a) < 3: continue
                pts = a.reshape(-1, 2).astype(np.float32)
                if smooth: pts = _chaikin(pts, smooth)
                keep[i] = (pts/up, hh[3])
        shapes = []
        for i, (pts, parent) in keep.items():
            if parent >= 0: continue
            shapes.append((pts, [q for j, (q, par) in keep.items() if par == i]))
        out.append((lv, shapes))
    return out

def draw_levels(c, levels, ox, oy, w, h, src_w, src_h, color):
    """Слои силуэта поверх друг друга: каждый добавляет плотности."""
    n = len(levels)
    for i, (lv, shapes) in enumerate(levels):
        a = 0.42 if i == 0 else 0.42 + 0.58*(i/(n-1))**0.8
        draw_silhouette(c, shapes, ox, oy, w, h, src_w, src_h, color, alpha=a)
