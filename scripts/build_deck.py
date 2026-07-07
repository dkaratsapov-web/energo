# -*- coding: utf-8 -*-
"""Сборка страниц каталога в вектор по спецификациям SPECS.
Каждая страница: чистим фон (erase/inpaint) -> кладём фон -> логотип -> заголовок -> буллеты.
"""
import sys, os, cv2, numpy as np
from PIL import Image
sys.path.insert(0, 'scripts')
from rebuild import register_fonts, size_for, erase_text_lum, PW, PH, SX, SY, X, Y
from reportlab.pdfgen import canvas

register_fonts()
ORANGE = (252/255, 144/255, 43/255)
WHITE  = (240/255, 240/255, 246/255)
OUT = 'build'
os.makedirs(OUT, exist_ok=True)

def inpaint_boxes(img, boxes, radius=12):
    mask = np.zeros(img.shape[:2], np.uint8)
    for (x0, y0, x1, y1) in boxes:
        mask[y0:y1, x0:x1] = 255
    return cv2.inpaint(img, mask, radius, cv2.INPAINT_NS)

def clean_bg_patch(img, box, sample_x):
    """Закрасить box чистым фоном: берём вертикальный профиль цвета из колонки sample_x
    (гладко сглаженный) и им заливаем каждую строку box. Убирает след инпейнта под логотипом."""
    x0, y0, x1, y1 = box
    sx = max(0, min(sample_x, img.shape[1] - 1))
    col = img[:, sx].astype(np.float32)
    col = cv2.GaussianBlur(col.reshape(-1, 1, 3), (1, 31), 0).reshape(-1, 3)
    for y in range(y0, y1):
        img[y, x0:x1] = col[y]
    return img

def place_logo(c, logo_png, x0_px, top_px, w_px):
    im = Image.open(logo_png); ar = im.size[1] / im.size[0]; h_px = w_px * ar
    c.drawImage(logo_png, X(x0_px), Y(top_px + h_px), width=w_px*SX, height=h_px*SY, mask='auto')

def build(spec):
    n = spec['n']
    img = cv2.imread(f"page_images_150dpi/pg{n:02d}.jpg")
    # 1) стереть светлый текст в заданных зонах
    if spec.get('erase'):
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        L = lab[..., 0].astype(np.int16)
        Lbg = cv2.medianBlur(lab[..., 0], 41).astype(np.int16)
        diff = L - Lbg
        text = diff > spec.get('contrast', 38)
        region = np.zeros(text.shape, bool)
        for (x0, y0, x1, y1) in spec['erase']:
            region[y0:y1, x0:x1] = True
        mask = np.zeros(img.shape[:2], np.uint8); mask[text & region] = 255
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=5)
        img = cv2.inpaint(img, mask, 9, cv2.INPAINT_NS)
    # 2) убрать старый логотип: заливка чистым фоном (профиль цвета слева от логотипа),
    #    чтобы не было следа инпейнта под прозрачными участками нового логотипа
    if spec.get('logo_erase'):
        le = spec['logo_erase']
        sx = spec.get('logo_bg_sample_x', le[0] - 35)
        img = clean_bg_patch(img, le, sx)
    # 2b) полностью закрасить произвольные области (напр. старые растровые точки/иконки)
    if spec.get('fill'):
        img = inpaint_boxes(img, spec['fill'], radius=12)
    # 2b') чистая заливка фона (для больших заголовков на почти-сплошном фоне)
    for (box, sample_x) in spec.get('bg_fill', []):
        img = clean_bg_patch(img, box, sample_x)
    # 2c) стереть СТАРЫЕ растровые точки буллетов (их не берёт яркостный фильтр —
    #     они оранжевые), чтобы под новыми вектор-точками не было ореола
    if spec.get('bullets') and not spec.get('no_dot_erase'):
        r = spec.get('dot_r', 11)
        dot_boxes = []
        for (cx, ls) in spec['bullets']:
            cys = [b for (t, b, x, w) in ls]
            cy = (min(cys) + max(cys)) // 2 - 8
            dot_boxes.append((cx - r - 12, cy - r - 20, cx + r + 12, cy + r + 14))
        img = inpaint_boxes(img, dot_boxes, radius=10)
    clean = f"{OUT}/pg{n:02d}_clean.jpg"; cv2.imwrite(clean, img)

    c = canvas.Canvas(f"{OUT}/page{n:02d}.pdf", pagesize=(PW, PH))
    c.drawImage(clean, 0, 0, width=PW, height=PH)
    if spec.get('logo'):
        place_logo(c, 'assets/logo_orange.png', *spec['logo'])
    # заголовок
    if spec.get('title'):
        tf = spec.get('title_font', 'Onest-ExtraBold')
        ts = spec.get('title_size') or max(size_for(t, tf, w) for (t, b, x, w) in spec['title'])
        c.setFillColorRGB(*spec.get('title_rgb', WHITE)); c.setFont(tf, ts)
        for (t, b, x, w) in spec['title']:
            c.drawString(X(x), Y(b), t)
    # буллеты
    if spec.get('bullets'):
        bf = spec.get('body_font', 'Onest-Regular')
        allw = [(t, w) for (cx, ls) in spec['bullets'] for (t, b, x, w) in ls]
        bs = spec.get('body_size') or max(size_for(t, bf, w) for (t, w) in allw)
        r = spec.get('dot_r', 11)
        for (cx, ls) in spec['bullets']:
            cys = [b for (t, b, x, w) in ls]; cy = (min(cys)+max(cys))//2 - 8
            c.setFillColorRGB(*ORANGE); c.circle(X(cx), Y(cy), r*SX, stroke=0, fill=1)
            c.setFillColorRGB(*WHITE); c.setFont(bf, bs)
            for (t, b, x, w) in ls:
                c.drawString(X(x), Y(b), t)
    # свободный текст [(text,base,x,size,font,rgb)]; суффикс '/i' у шрифта = наклон (курсив)
    for (t, b, x, sz, f, rgb) in spec.get('body', []):
        italic = f.endswith('/i'); fname = f[:-2] if italic else f
        c.setFillColorRGB(*rgb); c.setFont(fname, sz)
        if italic:
            c.saveState(); c.translate(X(x), Y(b)); c.transform(1, 0, 0.18, 1, 0, 0)
            c.drawString(0, 0, t); c.restoreState()
        else:
            c.drawString(X(x), Y(b), t)
    c.showPage(); c.save()
    return f"{OUT}/page{n:02d}.pdf"

# импорт спецификаций
from specs import SPECS

if __name__ == '__main__':
    which = sys.argv[1:] or [str(s['n']) for s in SPECS]
    want = set(int(x) for x in which)
    for spec in SPECS:
        if spec['n'] in want:
            build(spec); print(f"built page{spec['n']:02d}.pdf")
