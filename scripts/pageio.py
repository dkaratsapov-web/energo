# -*- coding: utf-8 -*-
"""Единая загрузка страницы-подложки.

Исходники выгружены шириной 1241 px, а вся геометрия построена на сетке
1240x1754. Разница в один пиксель смещает детекцию на границе порогов,
поэтому нормализация должна быть одна и та же во всех инструментах.
"""
import cv2
BASE_W, BASE_H = 1240, 1754

def fit(img):
    """Привести подложку к сетке 1240x1754.

    Расхождение в 1-2 px (артефакт экспорта) снимаем обрезкой: интерполяция
    здесь размывает и без того слабый текст на фото, и он перестаёт
    детектироваться. Существенную разницу масштабируем.
    """
    h, w = img.shape[:2]
    if (w, h) == (BASE_W, BASE_H):
        return img
    if abs(w-BASE_W) <= 2 and abs(h-BASE_H) <= 2:
        if w > BASE_W: img = img[:, :BASE_W]
        if h > BASE_H: img = img[:BASE_H, :]
        h, w = img.shape[:2]
        if w < BASE_W or h < BASE_H:
            img = cv2.copyMakeBorder(img, 0, max(0,BASE_H-h), 0, max(0,BASE_W-w),
                                     cv2.BORDER_REPLICATE)
        return img
    return cv2.resize(img, (BASE_W, BASE_H), interpolation=cv2.INTER_AREA)

def load_page(page, src_dir='page_images_150dpi'):
    return fit(cv2.imread(f'{src_dir}/pg{page:02d}.jpg'))
