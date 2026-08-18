# -*- coding: utf-8 -*-
"""
Плоские заливки (столбцы диаграммы, плашки) — в вектор.

Такие элементы в исходнике растровые, и на печати их края идут
«лесенкой». Геометрия у них простая: прямоугольник сплошного цвета,
поэтому его можно снять с растра и перерисовать заливкой.

Детектируем по цвету, а не по краям: столбец диаграммы лежит на
градиенте, и градиентный фон даёт ложные контуры.
"""
import cv2, numpy as np

def color_mask(img, spec):
    """spec: (Rmin,Rmax, Gmin,Gmax, Bmin,Bmax) в RGB."""
    rgb = img[:,:,::-1].astype(int)
    R,G,B = rgb[...,0], rgb[...,1], rgb[...,2]
    r0,r1,g0,g1,b0,b1 = spec
    return (((R>=r0)&(R<=r1)&(G>=g0)&(G<=g1)&(B>=b0)&(B<=b1)).astype(np.uint8))*255

def rects(img, box, spec, min_area=800, min_w=6, min_h=6, fill=0.75):
    """Прямоугольные заливки заданного цвета внутри box.

    fill — минимальная заполненность bbox, отсекает нерпямоугольные пятна.
    Возвращает [(x,y,w,h,(r,g,b)), ...] в координатах страницы.
    """
    x0,y0,x1,y1 = box
    sub = img[y0:y1, x0:x1]
    m = color_mask(sub, spec)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    out=[]
    for i in range(1,n):
        x,y,w,h,a = st[i]
        if a < min_area or w < min_w or h < min_h: continue
        if a < fill*w*h: continue
        core = (lab[y:y+h, x:x+w] == i)
        core = cv2.erode(core.astype(np.uint8), np.ones((3,3),np.uint8)).astype(bool)
        px = sub[y:y+h, x:x+w][core if core.any() else (lab[y:y+h,x:x+w]==i)]
        rgb = tuple(int(v) for v in px.mean(0)[::-1])
        out.append((x0+int(x), y0+int(y), int(w), int(h), rgb))
    return sorted(out, key=lambda r:(r[0], r[1]))
