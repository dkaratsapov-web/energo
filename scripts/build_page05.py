# -*- coding: utf-8 -*-
"""Custom rebuild of page 05: keep raster bg (white cards + orange line icons +
faint pylon watermark + logo); erase old text and re-typeset it crisply.
- card rows: dark text on pure-white cards (inpaint of dark text -> perfect white)
- bottom callouts: orange italic numbers + underline + white labels on dark bg."""
import sys, os, cv2, numpy as np
sys.path.insert(0, 'scripts')
from rebuild import register_fonts, PW, PH, SX, SY, X, Y
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

register_fonts()
WHITE  = (240/255, 240/255, 246/255)
ORANGE = (252/255, 144/255, 43/255)
DARK   = (45/255, 45/255, 55/255)
SKEW   = 0.20
OUT = 'build'; os.makedirs(OUT, exist_ok=True)

CARD_TOPS = [276, 373, 470, 567, 664, 761, 858, 955, 1052, 1149, 1246]

# ---------- 1. erase old text ----------
img = cv2.imread('page_images_150dpi/pg05.jpg')
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
L = lab[..., 0].astype(np.int16)
Lbg = cv2.medianBlur(lab[..., 0], 41).astype(np.int16)

# (a) dark text on white cards: text DARKER than local bg
dark_text = (Lbg - L) > 30
region = np.zeros(dark_text.shape, bool)
for t in CARD_TOPS:
    region[t+4:t+77, 372:978] = True     # card text zone, right of icon square
mask = np.zeros(img.shape[:2], np.uint8); mask[dark_text & region] = 255

# (b) light callouts (labels + underline) on dark bg via luminance
light_text = (L - Lbg) > 28
region2 = np.zeros(light_text.shape, bool)
region2[1550:1615, 70:1100] = True       # underline + labels only
mask[light_text & region2] = 255
# big bold orange numbers: thick strokes defeat luminance -> erase full boxes
for (x0, y0, x1, y1) in [(92, 1455, 262, 1548), (328, 1455, 476, 1548),
                          (626, 1450, 1048, 1550)]:
    mask[y0:y1, x0:x1] = 255

mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=4)
img = cv2.inpaint(img, mask, 9, cv2.INPAINT_NS)
clean = f"{OUT}/pg05_clean.jpg"; cv2.imwrite(clean, img)

# ---------- 2. draw ----------
c = canvas.Canvas(f"{OUT}/page05.pdf", pagesize=(PW, PH))
c.drawImage(clean, 0, 0, width=PW, height=PH)

def oblique(text, xpt, ypt, font, size, rgb, skew=SKEW):
    c.setFillColorRGB(*rgb)
    to = c.beginText(); to.setFont(font, size)
    to.setTextTransform(1, 0, skew, 1, xpt, ypt); to.textOut(text)
    c.drawText(to)

def plain(text, xpt, ypt, font, size, rgb):
    c.setFillColorRGB(*rgb); c.setFont(font, size); c.drawString(xpt, ypt, text)

# ----- card rows -----
NUM_S, WORD_S = 14.2, 13.85
rows = [
    ("24",  "руководителя"),
    ("32",  "инженера"),
    ("21",  "проектировщик"),
    ("144", "монтажника"),
    ("32",  "строителя"),
    ("64",  "сотрудника других профессий"),
    (None,  ["мастерские, складские и гаражные", "помещения, офисные комплексы"]),
    ("35",  "ед.транспорта ОВБ"),
    ("68",  "ед.спецтехники"),
    ("33",  "ед. бурильно крановых машин"),
    ("5",   "машины ГНБ"),
]
LEFT = X(393)
for top, (num, word) in zip(CARD_TOPS, rows):
    if num is None:                       # two-line row, no number
        base1, base2 = Y(top + 38), Y(top + 68)
        plain(word[0], LEFT, base1, 'Onest-Regular', WORD_S, DARK)
        plain(word[1], LEFT, base2, 'Onest-Regular', WORD_S, DARK)
        continue
    base = Y(top + 55)
    oblique(num, LEFT, base, 'Onest-ExtraBold', NUM_S, DARK)
    nw = pdfmetrics.stringWidth(num, 'Onest-ExtraBold', NUM_S)
    gap = (18 if num == '5' else 9)       # wider gap after lone "5"
    plain(word, LEFT + nw + gap, base, 'Onest-Regular', WORD_S, DARK)

# ----- bottom callouts -----
NUM_C, LBL_C = 48.0, 13.85
callouts = [
    ('317',       98,  'сотрудников',              259),
    ('141',       335, 'единица техники',          474),
    ('71 560 м²', 634, 'производственные площади', 1029),
]
for num, nx, label, ux in callouts:
    oblique(num, X(nx), Y(1539), 'Onest-ExtraBold', NUM_C, ORANGE)
    # underline
    c.setStrokeColorRGB(*WHITE); c.setLineWidth(2.2)
    c.line(X(nx), Y(1563), X(ux), Y(1563))
    # label
    plain(label, X(nx), Y(1602), 'Onest-Regular', LBL_C, WHITE)

c.showPage(); c.save()
print('built build/page05.pdf')
