# -*- coding: utf-8 -*-
"""Стр. 02 — качественная пересборка: чистый вектор-текст + ВЕКТОРНЫЕ иконки миссий
(вместо мутных растровых). Лого-медведь слева не трогаем."""
import sys, cv2, numpy as np
sys.path.insert(0, 'scripts')
from rebuild import register_fonts, PW, PH, SX, SY, X, Y
from reportlab.pdfgen import canvas
register_fonts()
WHITE = (240/255, 240/255, 246/255)
ORANGE = (252/255, 144/255, 43/255)

def erase(img, boxes, contrast, dark_bg=True):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    L = lab[..., 0].astype(np.int16); Lbg = cv2.medianBlur(lab[..., 0], 41).astype(np.int16)
    diff = (L - Lbg) if dark_bg else (Lbg - L)
    text = diff > contrast
    region = np.zeros(text.shape, bool)
    for (x0, y0, x1, y1) in boxes: region[y0:y1, x0:x1] = True
    mask = np.zeros(img.shape[:2], np.uint8); mask[text & region] = 255
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=5)
    return cv2.inpaint(img, mask, 9, cv2.INPAINT_NS)

def fill_boxes(img, boxes, radius=10):
    mask = np.zeros(img.shape[:2], np.uint8)
    for (x0, y0, x1, y1) in boxes: mask[y0:y1, x0:x1] = 255
    return cv2.inpaint(img, mask, radius, cv2.INPAINT_NS)

# ---- вектор-иконки (белые пиктограммы) ----
def icon_person(c, cx, cy, s):
    c.setFillColorRGB(*WHITE); c.setStrokeColorRGB(*WHITE)
    c.circle(X(cx), Y(cy - s*0.42), s*0.22*SX, stroke=0, fill=1)          # голова
    c.setLineWidth(s*0.16*SX); c.setLineCap(1)
    p = c.beginPath(); p.moveTo(X(cx - s*0.38), Y(cy + s*0.5))
    p.curveTo(X(cx - s*0.38), Y(cy - s*0.02), X(cx + s*0.38), Y(cy - s*0.02), X(cx + s*0.38), Y(cy + s*0.5))
    c.drawPath(p, stroke=1, fill=0)                                        # плечи

def icon_cross(c, cx, cy, s):
    c.setFillColorRGB(*WHITE)
    w = s*0.7; t = s*0.24
    c.rect(X(cx) - t*SX/2, Y(cy) - w*SY/2, t*SX, w*SY, stroke=0, fill=1)
    c.rect(X(cx) - w*SX/2, Y(cy) - t*SY/2, w*SX, t*SY, stroke=0, fill=1)

def icon_heart(c, cx, cy, s):
    c.setFillColorRGB(*WHITE)
    x0, y0 = X(cx), Y(cy - s*0.32)
    p = c.beginPath(); p.moveTo(x0, Y(cy + s*0.48))
    p.curveTo(X(cx - s*0.62), Y(cy - s*0.02), X(cx - s*0.42), Y(cy - s*0.55), x0, Y(cy - s*0.2))
    p.curveTo(X(cx + s*0.42), Y(cy - s*0.55), X(cx + s*0.62), Y(cy - s*0.02), x0, Y(cy + s*0.48))
    c.drawPath(p, stroke=0, fill=1)

ICONS = [(145, 592, icon_person), (145, 815, icon_cross), (145, 1068, icon_heart)]

def build(out='build/page02.pdf'):
    img = cv2.imread('page_images_150dpi/pg02.jpg')
    # стереть старый текст миссий/заголовка
    img = erase(img, [(110,300,735,425),(110,485,400,522),(175,582,348,614),(175,804,348,838),
                      (175,1058,350,1090),(110,650,720,755),(110,872,835,1008),(110,1125,820,1230),
                      (108,1296,365,1323)], contrast=26)
    # стереть старые растровые иконки-диски целиком (перекроем вектором)
    img = fill_boxes(img, [(100, 555, 195, 640), (100, 777, 195, 862), (100, 1030, 195, 1115)], radius=14)
    cv2.imwrite('build/pg02_clean.jpg', img)

    c = canvas.Canvas(out, pagesize=(PW, PH))
    c.drawImage('build/pg02_clean.jpg', 0, 0, width=PW, height=PH)
    # вектор-иконки: оранжевый диск + белая пиктограмма
    for cx, cy, fn in ICONS:
        c.setFillColorRGB(*ORANGE); c.circle(X(cx), Y(cy), 26*SX, stroke=0, fill=1)
        fn(c, cx, cy, 26)
    # текст
    body = [
        ('Входим в попечительский совет', 340, 116, 18.57, 'Onest-Bold', WHITE),
        ('благотворительного фонда', 380, 115, 18.57, 'Onest-Bold', WHITE),
        ('«Энергия Русского духа»', 419, 115, 18.57, 'Onest-Bold', WHITE),
        ('Миссии фонда', 513, 116, 18.24, 'Onest-Bold', ORANGE),
        ('Миссия 1', 606, 195, 13.79, 'Onest-Bold', ORANGE),
        ('Миссия 2', 828, 195, 13.79, 'Onest-Bold', ORANGE),
        ('Миссия 3', 1081, 195, 13.79, 'Onest-Bold', ORANGE),
        ('Содействие в восстановлении благополучия', 668, 116, 11.92, 'Onest-Regular', WHITE),
        ('работников энергетической отрасли и их семей,', 695, 116, 11.92, 'Onest-Regular', WHITE),
        ('пострадавших в результате событий, связанных', 722, 116, 11.92, 'Onest-Regular', WHITE),
        ('с проведением специальной военной операции', 749, 116, 11.92, 'Onest-Regular', WHITE),
        ('Обеспечение необходимой медицинской,', 892, 116, 11.92, 'Onest-Regular', WHITE),
        ('социальной и материальной помощи работникам', 918, 116, 11.92, 'Onest-Regular', WHITE),
        ('отрасли для преодоления травм, полученных в результате', 948, 116, 11.92, 'Onest-Regular', WHITE),
        ('событий, связанных с проведением специальной военной', 972, 116, 11.92, 'Onest-Regular', WHITE),
        ('операции, и возвращения к полноценной жизни', 1000, 116, 11.92, 'Onest-Regular', WHITE),
        ('Восстановление психологического здоровья', 1142, 118, 11.92, 'Onest-Regular', WHITE),
        ('и душевного равновесия работников энергетической', 1169, 118, 11.92, 'Onest-Regular', WHITE),
        ('отрасли, пострадавших в результате событий, связанных', 1196, 117, 11.92, 'Onest-Regular', WHITE),
        ('с проведением специальной военной операции', 1224, 117, 11.92, 'Onest-Regular', WHITE),
        ('https://эрдфонд.рф/', 1315, 116, 11.61, 'Onest-Regular', ORANGE),
    ]
    for (t, b, x, sz, f, rgb) in body:
        c.setFillColorRGB(*rgb); c.setFont(f, sz); c.drawString(X(x), Y(b), t)
    c.showPage(); c.save()
    print('build/page02.pdf rebuilt with vector icons')

if __name__ == '__main__':
    build()
