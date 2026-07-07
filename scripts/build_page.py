# -*- coding: utf-8 -*-
"""
Сборщик векторной страницы: фон (фото/плашка) + вектор-текст Onest.

Ключевые принципы (проверено):
- Геометрия страницы = A4: 595.445669 x 841.691339 pt.
- Постраничный фон = 1240x1754 px @150dpi. Перевод px->pt:
      sx = 595.445669/1240 = 0.480199 ;  sy = 841.691339/1754 = 0.479870
      X(px) = px*sx ;  Y(px) = PH - py*sy   (в PDF начало координат снизу-слева)
- Шрифт: Onest (подтверждён совпадением ширины). Заголовки = Onest-ExtraBold,
  текст/буллеты = Onest-Regular.
- РАЗМЕР шрифта подбирается ТОЧНО под измеренную ширину через метрики шрифта:
      size = (target_width_px * sx) / stringWidth(text, font, 1.0)
  (никаких ручных подгонок — ширина совпадает 1-в-1).
- ГЛАВНОЕ против «двоения»: перед наложением вектора СТИРАЕМ старый впечатанный
  текст с фона (inpaint по маске белого текста), иначе старый пиксельный текст
  проступает из-под нового.

Цвета (примеры, уточнять пипеткой по странице):
  заголовок ~ (240,240,246) белый;  маркеры оранжевые (252,144,43);
  плашка-градиент фиолет (67,70,103)->(87,88,144).
"""
import cv2, numpy as np
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PW, PH = 595.445669, 841.691339
SX, SY = PW/1240.0, PH/1754.0
X = lambda px: px*SX
Y = lambda py: PH - py*SY

FONTS_DIR = 'fonts'  # поправьте путь при необходимости
def register_fonts(fonts_dir=FONTS_DIR):
    for w in ['Regular','Medium','SemiBold','Bold','ExtraBold']:
        pdfmetrics.registerFont(TTFont('Onest-'+w, f'{fonts_dir}/Onest-{w}.ttf'))

def size_for(text, font, width_px):
    """Кегль (pt), при котором строка text шрифтом font имеет ширину width_px."""
    return (width_px*SX)/pdfmetrics.stringWidth(text, font, 1.0)

def erase_old_text(img_path, out_path, boxes, white_thr=(200,195,205), dilate=2, radius=7):
    """Стереть старый впечатанный СВЕТЛЫЙ текст: inpaint по маске белого в заданных
    прямоугольниках boxes=[(x0,y0,x1,y1),...] (px). Возвращает out_path (чистый фон)."""
    img=cv2.imread(img_path)
    a=cv2.cvtColor(img,cv2.COLOR_BGR2RGB).astype(int)
    R,G,B=a[...,0],a[...,1],a[...,2]
    white=(R>white_thr[0])&(G>white_thr[1])&(B>white_thr[2])
    region=np.zeros(white.shape,bool)
    for (x0,y0,x1,y1) in boxes: region[y0:y1, x0:x1]=True
    mask=np.zeros(img.shape[:2],np.uint8); mask[white&region]=255
    mask=cv2.dilate(mask,np.ones((5,5),np.uint8),iterations=dilate)
    clean=cv2.inpaint(img,mask,radius,cv2.INPAINT_TELEA)
    cv2.imwrite(out_path,clean)
    return out_path

def build_page(out_pdf, bg_image, title_lines=None, bullets=None,
               title_font='Onest-ExtraBold', body_font='Onest-Regular',
               title_rgb=(240/255,240/255,246/255), body_rgb=(240/255,240/255,246/255),
               dot_rgb=(252/255,144/255,43/255), dot_r_px=11):
    """
    title_lines = [(text, baseline_px, left_x_px, measured_width_px), ...]
                  (все строки заголовка получают ОДИН кегль — по самой широкой строке)
    bullets = [(dot_cx_px, [ (text, baseline_px, left_x_px, measured_width_px), ...] ), ...]
                  (несколько строк в одном буллете допускается; кегль буллетов —
                   по самой широкой строке буллетов)
    """
    c=canvas.Canvas(out_pdf, pagesize=(PW,PH))
    c.drawImage(bg_image, 0,0, width=PW, height=PH)
    if title_lines:
        ts=max(size_for(t,title_font,w) for (t,b,x,w) in title_lines)
        c.setFillColorRGB(*title_rgb); c.setFont(title_font, ts)
        for (t,base,x,w) in title_lines: c.drawString(X(x), Y(base), t)
    if bullets:
        allw=[(t,w) for (cx,lines) in bullets for (t,b,x,w) in lines]
        bs=max(size_for(t,body_font,w) for (t,w) in allw)
        for (cx,lines) in bullets:
            # маркер по центру блока строк
            cys=[b for (t,b,x,w) in lines]; cy=(min(cys)+max(cys))//2 - 8
            c.setFillColorRGB(*dot_rgb); c.circle(X(cx), Y(cy), dot_r_px*SX, stroke=0, fill=1)
            c.setFillColorRGB(*body_rgb); c.setFont(body_font, bs)
            for (t,base,x,w) in lines: c.drawString(X(x), Y(base), t)
    c.showPage(); c.save()
    return out_pdf

# ---- ПРИМЕР (страница 7) ----
if __name__=='__main__':
    register_fonts()
    # 1) стереть старый текст с фона:
    erase_old_text('page_images_150dpi/pg07.jpg','pg07_clean.jpg',
                   boxes=[(90,260,1050,520),(110,600,700,1330)])
    # 2) собрать вектор поверх чистого фона:
    build_page('page07.pdf','pg07_clean.jpg',
        title_lines=[('ПРОЕКТИРОВАНИЕ',336,111,777),('И СТРОИТЕЛЬСТВО',416,111,786),
                     ('В СФЕРЕ ЭНЕРГЕТИКИ',495,111,907)],
        bullets=[(134,[('Внутренние электрические сети',632,183,455)]),
                 (134,[('Кабельные линии',707,183,242)]),
                 (134,[('Воздушные линии электропередач',782,183,489)]),
                 (134,[('Распределительные пункты,',846,183,394),
                       ('трансформаторные подстанции',878,183,448)]),
                 (134,[('Архитектурное освещение',943,183,379)]),
                 (134,[('Сервисное обслуживание электроустановок',1018,183,636)]),
                 (134,[('Электротехническая лаборатория',1093,183,480)]),
                 (134,[('Наружное электроосвещение',1168,183,421)]),
                 (134,[('Пусконаладочные работы',1243,183,361)]),
                 (134,[('ГНБ/ГНП',1318,183,125)])])
    print('page07.pdf built')
