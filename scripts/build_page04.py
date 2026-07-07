# -*- coding: utf-8 -*-
"""Custom rebuild of page 04: mission/goals text + vector bar chart."""
import sys, os, cv2, numpy as np
sys.path.insert(0, 'scripts')
from rebuild import register_fonts, size_for, PW, PH, SX, SY, X, Y
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

register_fonts()
WHITE  = (240/255, 240/255, 246/255)
ORANGE = (252/255, 144/255, 43/255)
PEACH  = (255/255, 197/255, 140/255)
OUT = 'build'; os.makedirs(OUT, exist_ok=True)

# ---- 1. erase old WHITE text via local luminance, keep gradient bg ----
img = cv2.imread('page_images_150dpi/pg04.jpg')
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
L = lab[..., 0].astype(np.int16)
Lbg = cv2.medianBlur(lab[..., 0], 41).astype(np.int16)
diff = L - Lbg                      # text lighter than bg
text = diff > 34
ERASE = [
    (90, 215, 700, 275),            # МИССИЯ КОМПАНИИ
    (180, 300, 1080, 395),          # bullet 1
    (180, 408, 1120, 500),          # bullet 2
    (90, 565, 575, 628),            # ЦЕЛИ КОМПАНИИ
    (100, 658, 1100, 780),          # goals paragraph
    (95, 865, 610, 995),            # ДИНАМИКА / РОСТА КОМПАНИИ (left block)
    # per-bar value labels (above bar tops, avoid bar bodies)
    (20, 1398, 245, 1480), (240, 1322, 375, 1408), (385, 1250, 520, 1336),
    (530, 1142, 665, 1227), (675, 996, 815, 1083), (818, 916, 962, 1002),
    (910, 846, 1145, 932),
    (110, 1525, 1075, 1580),        # year row
]
region = np.zeros(text.shape, bool)
for (x0, y0, x1, y1) in ERASE:
    region[y0:y1, x0:x1] = True
mask = np.zeros(img.shape[:2], np.uint8); mask[text & region] = 255
mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=5)
img = cv2.inpaint(img, mask, 9, cv2.INPAINT_NS)

# полностью убрать СТАРЫЕ растровые столбцы (закрасить их область чистым градиентом),
# чтобы под новыми вектор-столбцами не было мутных краёв
BARS_XT = [(127,181,1484),(272,326,1411),(417,471,1339),(562,616,1230),
           (707,761,1086),(853,907,1006),(998,1051,936)]
bmask = np.zeros(img.shape[:2], np.uint8)
for (x0, x1, top) in BARS_XT:
    bmask[top-12:1530, x0-14:x1+40] = 255
img = cv2.inpaint(img, bmask, 12, cv2.INPAINT_NS)
clean = f"{OUT}/pg04_clean.jpg"; cv2.imwrite(clean, img)

# ---- 2. draw ----
c = canvas.Canvas(f"{OUT}/page04.pdf", pagesize=(PW, PH))
c.drawImage(clean, 0, 0, width=PW, height=PH)

def text_line(t, base, x, size, font, rgb=WHITE):
    c.setFillColorRGB(*rgb); c.setFont(font, size); c.drawString(X(x), Y(base), t)

def centered(t, base, cx, size, font, rgb=WHITE):
    w = pdfmetrics.stringWidth(t, font, size)
    c.setFillColorRGB(*rgb); c.setFont(font, size)
    c.drawString(X(cx) - w/2, Y(base), t)

# headings (ExtraBold, ~24.6pt)
HS = 24.6
text_line('МИССИЯ КОМПАНИИ', 263, 106, HS, 'Onest-ExtraBold')
text_line('ЦЕЛИ КОМПАНИИ',   619, 106, HS, 'Onest-ExtraBold')
text_line('ДИНАМИКА',        920, 106, HS, 'Onest-ExtraBold')
text_line('РОСТА КОМПАНИИ',  984, 108, HS, 'Onest-ExtraBold')

# bullets (Regular ~9.77pt) + orange dots
BS = 9.77
bullet1 = [
    ('Укрепление российского электроэнергетического комплекса путём участия в проектах,', 320, 185),
    ('позволяющих сформировать максимально благоприятные условия для постоянного', 352, 185),
    ('развития экономики РФ.', 383, 185),
]
bullet2 = [
    ('Качественное выполнение своих задач по подготовке проектов, их реализации, поставке', 428, 186),
    ('оборудования, его установке и наладке, а также вводу в эксплуатацию объектов энергетики,', 462, 186),
    ('удовлетворяющим нормам экологической и промышленной безопасности.', 490, 185),
]
for (cy, lines) in [(345, bullet1), (453, bullet2)]:
    c.setFillColorRGB(*ORANGE); c.circle(X(129), Y(cy), 12*SX, stroke=0, fill=1)
    for (t, base, x) in lines:
        text_line(t, base, x, BS, 'Onest-Regular')

# goals paragraph (Regular, no bullet)
for (t, base) in [
    ('Стать надежным партнером для нашего заказчика и ответственным работодателем для каждого', 678),
    ('сотрудника, а также создать сеть филиалов для присутствия в каждом регионе нашей необъятной', 712),
    ('страны с целью участия в работах по строительству, реконструкции, модернизации и технического', 742),
    ('перевооружения энергетической системы Российской Федерации.', 772),
]:
    text_line(t, base, 107, BS, 'Onest-Regular')

# ---- bar chart ----
BASELINE = 1520
bars = [  # (x0, x1, top, value_str, year)
    (127, 181, 1484, '>1 500', '2019'),
    (272, 326, 1411, '>1 700', '2020'),
    (417, 471, 1339, '>1 850', '2021'),
    (562, 616, 1230, '>2 000', '2022'),
    (707, 761, 1086, '>3 500', '2023'),
    (853, 907, 1006, '>4 200', '2024'),
    (998, 1051, 936, '>4 800', '2025'),
]
for (x0, x1, top, val, year) in bars:
    cx = (x0 + x1) / 2
    px = X(x0 - 1); py = Y(BASELINE)
    w = (x1 - x0 + 1) * SX; h = (BASELINE - top) * SY
    # main bar
    c.setFillColorRGB(*ORANGE); c.rect(px, py, w, h, stroke=0, fill=1)
    # right highlight strip
    c.setFillColorRGB(*PEACH); c.rect(X(x1 - 1), py, 6 * SX, h, stroke=0, fill=1)
    # value label (two lines, centered)
    centered(val, top - 52, cx, 10.5, 'Onest-SemiBold')
    centered('млрд руб', top - 22, cx, 10.5, 'Onest-Regular')
    # year label below
    centered(year, 1554, cx, 10.7, 'Onest-SemiBold')

c.showPage(); c.save()
print('built build/page04.pdf')
