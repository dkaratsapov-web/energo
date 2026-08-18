# -*- coding: utf-8 -*-
"""
Векторизация «силуэтных» страниц: градиентное небо + тёмный контур.

Работает там, где кадр по сути графичен — опора ЛЭП и провода на фоне
неба. Такой сюжет раскладывается на гладкую заливку и контрастный
силуэт, и обе части описываются вектором точнее, чем растром 150 dpi:
на печати силуэт получается идеально резким при любом увеличении.

Для предметной съёмки (офис, техника, люди, фасады) метод не годится и
не применяется — там нужен оригинал фотографии.

Разложение:
  1. модель фона — сильное размытие по «светлым» пикселям, то есть небу;
  2. alpha = насколько пиксель темнее модели;
  3. alpha режется на несколько уровней, каждый становится слоем
     полигонов со своей прозрачностью — так сохраняются полутона
     проводов и дальних веток.
"""
import cv2, numpy as np

def sky_model(img, mask_dark, ksize=151):
    """Гладкая модель фона: тёмные пиксели заменяются окружающим небом."""
    src = img.astype(np.float32)
    m = (mask_dark > 0).astype(np.uint8)
    filled = cv2.inpaint(img, cv2.dilate(m, np.ones((7,7),np.uint8)), 9, cv2.INPAINT_TELEA)
    f = filled.astype(np.float32)
    for k in (61, 101, ksize):
        f = cv2.GaussianBlur(f, (k|1, k|1), 0)
    return f

def split_layers(img, levels=(0.10, 0.22, 0.38, 0.58), min_area=6, eps=0.6):
    """Разложить кадр на слои силуэта. Возвращает (модель_фона, слои).

    Слой = (alpha, [контуры]); контуры — списки точек в пикселях страницы.
    """
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    # первичная оценка: что темнее локального фона
    bg0 = cv2.GaussianBlur(g, (151,151), 0)
    rough = ((bg0 - g) > 6).astype(np.uint8)*255
    model = sky_model(img, rough)
    mg = cv2.cvtColor(model.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    alpha = np.clip((mg - g) / np.maximum(mg, 1e-3), 0, 1)
    alpha = cv2.GaussianBlur(alpha, (3,3), 0)

    layers=[]
    for lv in levels:
        m = (alpha >= lv).astype(np.uint8)*255
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))
        cnts,_ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        polys=[]
        for c in cnts:
            if cv2.contourArea(c) < min_area: continue
            a = cv2.approxPolyDP(c, eps, True)
            if len(a) < 3: continue
            polys.append(a.reshape(-1,2))
        layers.append((lv, polys))
    return model, alpha, layers

def draw(c, layers, X, Y, SX, SY, ink=(12,12,20), step=None):
    """Нарисовать слои силуэта на canvas ReportLab."""
    n = len(layers)
    for i,(lv, polys) in enumerate(layers):
        # каждый следующий слой добавляет плотности поверх предыдущего
        a = (step or (1.0/n))
        c.saveState()
        c.setFillColorRGB(*[v/255 for v in ink], alpha=a)
        for p in polys:
            path = c.beginPath()
            path.moveTo(X(float(p[0][0])), Y(float(p[0][1])))
            for (x,y) in p[1:]:
                path.lineTo(X(float(x)), Y(float(y)))
            path.close()
            c.drawPath(path, stroke=0, fill=1)
        c.restoreState()
