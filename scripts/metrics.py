# -*- coding: utf-8 -*-
"""
Точные метрики впечатанной строки: левый край, ширина, БАЗОВАЯ ЛИНИЯ, цвет.

Базовая линия — не низ bbox: буквы с нижними выносами (у, р, д, ц, щ)
опускают bbox ниже строки. Поэтому baseline = медиана нижних краёв
отдельных букв: выносных букв в строке меньшинство, медиана их отсекает.

Цвет берём из «ядра» глифа (маска, съеденная эрозией), иначе в среднее
попадают полупрозрачные края и цвет уходит в фон.
"""
import cv2, numpy as np
from textmask import text_mask

def line_metrics(img, line, dark=False, k=31, thr=18, only=None):
    x0,y0,x1,y1 = line
    pad=4
    sy0,sy1 = max(0,y0-pad), min(img.shape[0],y1+pad)
    sx0,sx1 = max(0,x0-pad), min(img.shape[1],x1+pad)
    sub = img[sy0:sy1, sx0:sx1]
    m = text_mask(sub, None, dark, k, thr, strict=True, only=only)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    comps=[stats[i] for i in range(1,n) if stats[i][4] >= 12]
    if not comps: return None
    H = np.median([c[3] for c in comps])
    # для baseline берём только «полноростовые» буквы, без точек/запятых
    bots = sorted(c[1]+c[3] for c in comps if c[3] >= H*0.6)
    if not bots: bots = sorted(c[1]+c[3] for c in comps)
    baseline = sy0 + int(np.median(bots))
    left  = sx0 + min(c[0] for c in comps)
    right = sx0 + max(c[0]+c[2] for c in comps)
    core = cv2.erode(m, np.ones((3,3),np.uint8))
    if core.sum()==0: core = m
    px = sub[core>0]
    if len(px)==0:
        rgb = (240,240,246)
    else:
        # у мелкого кегля даже «ядро» глифа наполовину состоит из полутонов,
        # и среднее уезжает к фону. Берём четверть пикселей, наиболее
        # удалённых от фона по яркости — это чистый цвет краски.
        lum = px.astype(np.float32) @ np.array([0.114,0.587,0.299])
        n = max(len(px)//4, 1)
        idx = np.argsort(lum)[:n] if dark else np.argsort(lum)[-n:]
        rgb = tuple(int(v) for v in px[idx].mean(0)[::-1])
    return dict(x=left, base=baseline, w=right-left, rgb=rgb,
                cap=int(np.percentile([c[3] for c in comps],75)))

def dot_circles(img, box, min_r=5, max_r=20):
    """Оранжевые маркеры-буллеты внутри box -> [(cx,cy,r), ...]."""
    x0,y0,x1,y1 = box
    sub = img[y0:y1, x0:x1]
    hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
    H,S,V = hsv[...,0],hsv[...,1],hsv[...,2]
    m = (((H>3)&(H<22)&(S>90)&(V>120)).astype(np.uint8))*255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))
    n,lab,stats,cent = cv2.connectedComponentsWithStats(m,8)
    out=[]
    for i in range(1,n):
        x,y,w,h,a = stats[i]
        if not (min_r*2*0.7 <= w <= max_r*2*1.3): continue
        if abs(w-h) > max(3, 0.35*w): continue          # круг, а не текст
        if a < 0.55*np.pi*(w/2)**2: continue            # заполненность круга
        out.append((x0+cent[i][0], y0+cent[i][1], (w+h)/4.0))
    return sorted(out, key=lambda c:(c[1],c[0]))


def skew_angle(img, line, dark=False, k=31, thr=18, only=None):
    """Угол наклона набора в строке, градусы.

    Оценивается по смещению центра масс чернил от строки к строке: у
    наклонного шрифта верх глифа уходит вправо. Угол, взятый на глаз,
    даёт расхождение по ширине в пару процентов — этого хватает, чтобы
    из-под нового набора выглянул старый.
    """
    x0,y0,x1,y1 = line
    sub = img[y0:y1, x0:x1]
    m = text_mask(sub, None, dark, k, thr, strict=True, only=only)
    ys, xs = np.nonzero(m)
    if len(xs) < 50: return 0.0
    rows = np.unique(ys)
    if len(rows) < 6: return 0.0
    cx = np.array([xs[ys==r].mean() for r in rows])
    # верх изображения = меньший y; наклон вправо -> cx убывает с ростом y
    a = np.polyfit(rows.astype(float), cx, 1)[0]
    return float(np.degrees(np.arctan(-a)))
