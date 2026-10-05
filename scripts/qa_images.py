# -*- coding: utf-8 -*-
"""
Проверка фактического разрешения кадров в готовом PDF.

Именно по этому признаку типография завернула прежний файл: полосы были
сведены в растр 150 dpi. Проверка считает разрешение так же, как считает его
препресс, — делит число пикселей кадра на его размер на полосе, — и смотрит
на то, что лежит в файле, а не на то, что задумано в вёрстке.

Нормы: 300 dpi — норма для печати 175 lpi; ниже 250 dpi кадр на мелованной
бумаге уже заметно мягкий; ниже 200 dpi виден пиксель.
"""
import os, sys
import pymupdf

def check(path, want=300.0, warn=250.0):
    d = pymupdf.open(path)
    rows = []
    for i, pg in enumerate(d, 1):
        for im in pg.get_image_info():
            x0, y0, x1, y1 = im['bbox']
            w_mm = (x1 - x0)/72*25.4
            h_mm = (y1 - y0)/72*25.4
            if w_mm < 1 or h_mm < 1:
                continue
            dpi = min(im['width']/((x1 - x0)/72), im['height']/((y1 - y0)/72))
            rows.append((i, im['width'], im['height'], w_mm, h_mm, dpi))
    return rows

if __name__ == '__main__':
    bad = 0
    for f in sys.argv[1:]:
        rows = check(f)
        print(f'— {os.path.basename(f)}: кадров {len(rows)}')
        for i, pw, ph, w, h, dpi in rows:
            mark = 'норма' if dpi >= 299.5 else ('мягко' if dpi >= 250 else 'БРАК')
            if dpi < 299.5: bad += 1
            print(f'   стр {i}: {pw}×{ph} px на {w:.0f}×{h:.0f} мм = {dpi:5.0f} dpi  {mark}')
    print('\nкадров ниже 300 dpi:', bad)
