# -*- coding: utf-8 -*-
"""
Автоподбор начертания Onest по «плотности краски» строки.

Для каждого начертания рендерим ту же строку с кеглем, дающим ту же
ширину, и сравниваем долю закрашенных пикселей с оригиналом. Совпадение
по плотности = совпадение по толщине штриха.
"""
import cv2, numpy as np, os
from PIL import Image, ImageDraw, ImageFont
from textmask import text_mask

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS = ['Regular','Medium','SemiBold','Bold','ExtraBold']

def ink_ratio_src(img, line, dark=False, k=31, thr=18):
    x0,y0,x1,y1 = line
    sub = img[max(0,y0-3):y1+3, max(0,x0-3):x1+3]
    m = text_mask(sub, None, dark, k, thr, strict=True)
    return float((m>0).sum())/ (m.shape[0]*m.shape[1])

def _dbg(img, line, text, dark=False):
    src = ink_ratio_src(img, line, dark)
    x0,y0,x1,y1 = line
    return src, {w: round(ink_ratio_font(text,w,x1-x0,y1-y0),4) for w in WEIGHTS}

SS = 4   # сверхсэмплинг: рендерим крупно и уменьшаем, чтобы получить
         # такой же антиалиасинг, как у исходного растра 150 dpi.
         # Иначе чистый рендер «худее» пережатого JPEG и вес завышается.

def ink_ratio_font(text, weight, w_px, h_px):
    path=f'{ROOT}/fonts/Onest-{weight}.ttf'
    lo,hi=4,400*SS
    tw = w_px*SS
    for _ in range(30):                       # подбор кегля под ширину
        mid=(lo+hi)/2
        f=ImageFont.truetype(path, max(int(round(mid)),4))
        if f.getlength(text) < tw: lo=mid
        else: hi=mid
    f=ImageFont.truetype(path, max(int(round(lo)),4))
    W=int(w_px)+6; H=int(h_px)+6
    im=Image.new('L',(W*SS,H*SS),0); d=ImageDraw.Draw(im)
    bb=d.textbbox((0,0),text,font=f)
    d.text((3*SS-bb[0], 3*SS-bb[1]), text, 255, font=f)
    a=cv2.resize(np.array(im),(W,H),interpolation=cv2.INTER_AREA)
    # тот же критерий, что и у детектора текста на странице
    return float((a>60).sum())/(W*H)

def guess_weight(img, line, text, dark=False, k=31, thr=18):
    x0,y0,x1,y1 = line
    src = ink_ratio_src(img, line, dark, k, thr)
    best=None
    for w in WEIGHTS:
        r = ink_ratio_font(text, w, (x1-x0), (y1-y0))
        d = abs(r-src)
        if best is None or d<best[1]: best=(w,d,r)
    return best[0], src, best[2]
