# -*- coding: utf-8 -*-
"""Проба качества: пересборка обложки (pg01) и услуг (pg07) начисто."""
import sys, cv2, numpy as np
from PIL import Image
sys.path.insert(0, 'scripts')
from rebuild import (register_fonts, size_for, erase_text_lum, build_page,
                     PW, PH, SX, SY, X, Y)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

register_fonts()
ORANGE = (252/255, 144/255, 43/255)
WHITE  = (240/255, 240/255, 246/255)

def inpaint_boxes(img_path, out_path, boxes, radius=12):
    """Заполнить прямоугольники целиком (для стирания логотипа с гладкого неба)."""
    img = cv2.imread(img_path)
    mask = np.zeros(img.shape[:2], np.uint8)
    for (x0, y0, x1, y1) in boxes:
        mask[y0:y1, x0:x1] = 255
    clean = cv2.inpaint(img, mask, radius, cv2.INPAINT_NS)
    cv2.imwrite(out_path, clean)
    return out_path

def place_logo(c, logo_png, x0_px, top_px, w_px):
    im = Image.open(logo_png)
    ar = im.size[1] / im.size[0]
    h_px = w_px * ar
    c.drawImage(logo_png, X(x0_px), Y(top_px + h_px), width=w_px*SX, height=h_px*SY,
                mask='auto')

# ---------------- PG01 (обложка) ----------------
# стереть старый логотип (весь прямоугольник), затем старый заголовок и #2025
inpaint_boxes('page_images_150dpi/pg01.jpg', 'proof/pg01_a.jpg',
              boxes=[(915, 55, 1170, 235)], radius=14)
erase_text_lum('proof/pg01_a.jpg', 'proof/pg01_clean.jpg',
               boxes=[(70, 1430, 800, 1690)], dark_bg=True, contrast=40, dilate=5, radius=10)

c = canvas.Canvas('proof/page01.pdf', pagesize=(PW, PH))
c.drawImage('proof/pg01_clean.jpg', 0, 0, width=PW, height=PH)
# логотип (оранжевый) в правом верхнем углу
place_logo(c, 'assets/logo_orange.png', x0_px=918, top_px=60, w_px=250)
# заголовок: одна кегль по двум строкам
lines = [('КОМПЛЕКСНОЕ', 1506, 80, 629), ('СТРОИТЕЛЬСТВО', 1589, 77, 710)]
ts = max(size_for(t, 'Onest-ExtraBold', w) for (t, b, x, w) in lines)
c.setFillColorRGB(*WHITE); c.setFont('Onest-ExtraBold', ts)
for (t, b, x, w) in lines:
    c.drawString(X(x), Y(b), t)
# #2025
c.setFont('Onest-Regular', size_for('#2025', 'Onest-Regular', 115))
c.drawString(X(80), Y(1676), '#2025')
c.showPage(); c.save()
print('proof/page01.pdf built, title size=%.1f' % ts)

# ---------------- PG07 (услуги) ----------------
erase_text_lum('page_images_150dpi/pg07.jpg', 'proof/pg07_clean.jpg',
               boxes=[(100, 260, 1050, 520), (150, 590, 900, 1340)],
               dark_bg=True, contrast=38, dilate=5, radius=9)
# стереть старый логотип
inpaint_boxes('proof/pg07_clean.jpg', 'proof/pg07_clean.jpg',
              boxes=[(915, 55, 1170, 235)], radius=14)

c = canvas.Canvas('proof/page07.pdf', pagesize=(PW, PH))
c.drawImage('proof/pg07_clean.jpg', 0, 0, width=PW, height=PH)
place_logo(c, 'assets/logo_orange.png', x0_px=918, top_px=60, w_px=250)
title = [('ПРОЕКТИРОВАНИЕ', 336, 111, 777), ('И СТРОИТЕЛЬСТВО', 415, 111, 786),
         ('В СФЕРЕ ЭНЕРГЕТИКИ', 494, 111, 907)]
ts = max(size_for(t, 'Onest-ExtraBold', w) for (t, b, x, w) in title)
c.setFillColorRGB(*WHITE); c.setFont('Onest-ExtraBold', ts)
for (t, b, x, w) in title:
    c.drawString(X(x), Y(b), t)
bullets = [(134, [('Внутренние электрические сети', 631, 183, 456)]),
           (134, [('Кабельные линии', 706, 183, 242)]),
           (134, [('Воздушные линии электропередач', 785, 183, 490)]),
           (134, [('Распределительные пункты,', 845, 183, 395),
                  ('трансформаторные подстанции', 879, 183, 448)]),
           (134, [('Архитектурное освещение', 942, 183, 379)]),
           (134, [('Сервисное обслуживание электроустановок', 1017, 183, 637)]),
           (134, [('Электротехническая лаборатория', 1092, 183, 481)]),
           (134, [('Наружное электроосвещение', 1168, 183, 422)]),
           (134, [('Пусконаладочные работы', 1243, 183, 362)]),
           (134, [('ГНБ/ГНП', 1317, 183, 125)])]
allw = [(t, w) for (cx, ls) in bullets for (t, b, x, w) in ls]
bs = max(size_for(t, 'Onest-Regular', w) for (t, w) in allw)
for (cx, ls) in bullets:
    cys = [b for (t, b, x, w) in ls]; cy = (min(cys)+max(cys))//2 - 8
    c.setFillColorRGB(*ORANGE); c.circle(X(cx), Y(cy), 11*SX, stroke=0, fill=1)
    c.setFillColorRGB(*WHITE); c.setFont('Onest-Regular', bs)
    for (t, b, x, w) in ls:
        c.drawString(X(x), Y(b), t)
c.showPage(); c.save()
print('proof/page07.pdf built, title=%.1f body=%.1f' % (ts, bs))
