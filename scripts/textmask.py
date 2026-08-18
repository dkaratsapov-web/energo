# -*- coding: utf-8 -*-
"""
Надёжное стирание впечатанного текста с фона + детекция строк.

Почему прежний erase_old_text давал «двоение»: маска строилась по
абсолютному порогу белого (R>200 и т.п.). Сглаженные края глифов
(антиалиасинг) в порог не попадали и оставались на фоне серым
ореолом — он и проступает из-под нового вектора.

Здесь маска строится ОТНОСИТЕЛЬНО локального фона (morphological
black-hat / top-hat), поэтому ловит и полутоновую окантовку, и текст
на неоднородном фото. Дальше маска расширяется с запасом и заливается
inpaint-ом.
"""
import cv2, numpy as np

def text_mask(img, boxes=None, dark=False, k=31, thr=18, strict=False, only=None):
    """Маска впечатанного текста. dark=True — тёмный текст на светлом фоне.

    strict=True добавляет цветовой фильтр (белый текст = яркий + ненасыщенный).
    Нужен для ДЕТЕКЦИИ строк, где отклик от фото-фона мешает; для СТИРАНИЯ
    он не нужен — там наоборот хочется захватить всю окантовку глифа.
    """
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k))
    # top-hat: светлые детали мельче ядра; black-hat: тёмные
    hat = cv2.morphologyEx(g, cv2.MORPH_BLACKHAT if dark else cv2.MORPH_TOPHAT, ker)
    m = (hat > thr).astype(np.uint8)*255
    if strict:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        S_, V_ = hsv[...,1], hsv[...,2]
        H_ = hsv[...,0]
        if dark:
            col = (V_ < 90)
        else:
            white  = (V_ > 165) & (S_ < 70)
            # брендовый оранжевый (252,144,43) — заголовки и маркеры
            orange = (H_ > 3) & (H_ < 22) & (S_ > 110) & (V_ > 130)
            col = {'white':white, 'orange':orange}.get(only, white | orange)
        col = col.astype(np.uint8)*255
        m = cv2.bitwise_and(m, col)
    if boxes is not None:
        reg = np.zeros(m.shape, np.uint8)
        for (x0,y0,x1,y1) in boxes: reg[y0:y1, x0:x1] = 255
        m = cv2.bitwise_and(m, reg)
    return m

def erase(img, boxes, dark=False, k=31, thr=18, grow=4, radius=12):
    """Стереть текст в boxes и вернуть чистый фон."""
    m = text_mask(img, boxes, dark, k, thr)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(grow*2+1,)*2))
    out = cv2.inpaint(img, m, radius, cv2.INPAINT_TELEA)
    # второй проход сглаживает остаточную «рябь» inpaint внутри маски
    blur = cv2.medianBlur(out, 7)
    m3 = cv2.merge([m,m,m]).astype(np.float32)/255.0
    m3 = cv2.GaussianBlur(m3,(9,9),0)
    return (out*(1-m3) + blur*m3).astype(np.uint8)

def find_lines(img, box, dark=False, k=31, thr=18, min_h=8, min_w=20, gap=6,
               row_frac=0.02, only=None):
    """Найти строки текста внутри box -> [(x0,y0,x1,y1), ...] в px страницы."""
    x0,y0,x1,y1 = box
    sub = img[y0:y1, x0:x1]
    m = text_mask(sub, None, dark, k, thr, strict=True, only=only)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN,  np.ones((2,2),np.uint8))
    rows = (m>0).sum(1)
    on = rows > max(3, row_frac*m.shape[1])
    lines=[]; s=None; blank=0
    for i,v in enumerate(on):
        if v:
            if s is None: s=i
            blank=0
        else:
            if s is not None:
                blank+=1
                if blank>=gap:
                    if i-blank-s >= min_h: lines.append((s, i-blank))
                    s=None; blank=0
    if s is not None and len(on)-s>=min_h: lines.append((s,len(on)-1))
    out=[]
    for (a,b) in lines:
        strip = m[a:b+1]
        cols = (strip>0).sum(0)
        nz = np.where(cols>0)[0]
        if len(nz)==0 or nz[-1]-nz[0] < min_w: continue
        out.append((x0+int(nz[0]), y0+a, x0+int(nz[-1])+1, y0+b+1))
    return out
