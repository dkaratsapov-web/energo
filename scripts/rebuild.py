# -*- coding: utf-8 -*-
"""
Улучшенный конвейер пересборки страницы в вектор.

Отличия от build_page.py:
- erase_text_lum(): маска старого текста строится по ЯРКОСТИ относительно локального
  фона (а не по хрупкому RGB-порогу белого). Это надёжно убирает «двоение» — старый
  впечатанный текст (белый/светло-серый на тёмном градиенте) стирается полностью.
- работает и со СВЕТЛЫМ текстом на тёмном фоне (dark_bg=True, по умолчанию),
  и с ТЁМНЫМ текстом на светлом фоне (dark_bg=False).
"""
import cv2, numpy as np
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PW, PH = 595.445669, 841.691339
SX, SY = PW/1240.0, PH/1754.0
X = lambda px: px*SX
Y = lambda py: PH - py*SY

FONTS_DIR = 'fonts'
def register_fonts(fonts_dir=FONTS_DIR):
    for w in ['Regular','Medium','SemiBold','Bold','ExtraBold']:
        pdfmetrics.registerFont(TTFont('Onest-'+w, f'{fonts_dir}/Onest-{w}.ttf'))

def size_for(text, font, width_px):
    return (width_px*SX)/pdfmetrics.stringWidth(text, font, 1.0)

def erase_text_lum(img_path, out_path, boxes, dark_bg=True, contrast=45,
                   dilate=4, radius=9, blur_bg=41):
    """Стереть старый текст по локальному контрасту яркости.
    boxes = [(x0,y0,x1,y1),...] (px). Внутри каждого бокса пиксель считается «текстом»,
    если его яркость сильно отличается от локального фона (медианно-размытого):
      dark_bg=True  -> текст СВЕТЛЕЕ фона (L - Lbg > contrast)
      dark_bg=False -> текст ТЕМНЕЕ фона (Lbg - L > contrast)
    """
    img = cv2.imread(img_path)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    L = lab[..., 0].astype(np.int16)
    Lbg = cv2.medianBlur(lab[..., 0], blur_bg | 1).astype(np.int16)
    diff = (L - Lbg) if dark_bg else (Lbg - L)
    text = diff > contrast
    region = np.zeros(text.shape, bool)
    for (x0, y0, x1, y1) in boxes:
        region[y0:y1, x0:x1] = True
    mask = np.zeros(img.shape[:2], np.uint8)
    mask[text & region] = 255
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=dilate)
    clean = cv2.inpaint(img, mask, radius, cv2.INPAINT_NS)
    cv2.imwrite(out_path, clean)
    return out_path

def draw_paragraph(c, lines, font, size, rgb, leading=None):
    c.setFillColorRGB(*rgb); c.setFont(font, size)
    for (t, base, x) in lines:
        c.drawString(X(x), Y(base), t)

def build_page(out_pdf, bg_image, title_lines=None, bullets=None, body=None,
               title_font='Onest-ExtraBold', body_font='Onest-Regular',
               title_rgb=(240/255, 240/255, 246/255), body_rgb=(240/255, 240/255, 246/255),
               dot_rgb=(252/255, 144/255, 43/255), dot_r_px=11, title_size=None):
    """
    title_lines = [(text, baseline_px, left_x_px, measured_width_px), ...]
    bullets     = [(dot_cx_px, [(text, baseline_px, left_x_px, measured_width_px), ...]), ...]
    body        = [(text, baseline_px, left_x_px, size_pt, font, (r,g,b)), ...]  (свободный текст)
    """
    c = canvas.Canvas(out_pdf, pagesize=(PW, PH))
    c.drawImage(bg_image, 0, 0, width=PW, height=PH)
    if title_lines:
        ts = title_size or max(size_for(t, title_font, w) for (t, b, x, w) in title_lines)
        c.setFillColorRGB(*title_rgb); c.setFont(title_font, ts)
        for (t, base, x, w) in title_lines:
            c.drawString(X(x), Y(base), t)
    if bullets:
        allw = [(t, w) for (cx, lines) in bullets for (t, b, x, w) in lines]
        bs = max(size_for(t, body_font, w) for (t, w) in allw)
        for (cx, lines) in bullets:
            cys = [b for (t, b, x, w) in lines]; cy = (min(cys)+max(cys))//2 - 8
            c.setFillColorRGB(*dot_rgb); c.circle(X(cx), Y(cy), dot_r_px*SX, stroke=0, fill=1)
            c.setFillColorRGB(*body_rgb); c.setFont(body_font, bs)
            for (t, base, x, w) in lines:
                c.drawString(X(x), Y(base), t)
    if body:
        for (t, base, x, size, font, rgb) in body:
            c.setFillColorRGB(*rgb); c.setFont(font, size)
            c.drawString(X(x), Y(base), t)
    c.showPage(); c.save()
    return out_pdf
