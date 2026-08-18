# -*- coding: utf-8 -*-
"""
Подготовка подложки к печати: 150 -> 300 dpi.

Честно о пределах метода: новой детали здесь взяться неоткуда. Задача
скромнее — не дать растру выглядеть грязнее, чем он есть: снять
JPEG-артефакты (они на печати заметнее, чем на экране), увеличить
ресемплингом Lanczos и вернуть краям ту резкость, которую съедает
интерполяция.

Нейросетевой апскейл здесь недоступен (нет весов и GPU) и для каталога
он рискован: на кирпиче, окнах и логотипах партнёров такие модели
дорисовывают несуществующие детали, а это уже искажение объекта.
"""
import cv2, numpy as np

def deblock(img, strength=2):
    """Снять JPEG-блочность, сохранив края.

    Слабая настройка намеренно: сильный шумодав вместе с артефактами
    съедает и настоящую мелкую фактуру — зерно бетона, снег, листву.
    Лучше оставить немного шума, чем сгладить поверхность в пластик.
    """
    return cv2.fastNlMeansDenoisingColored(img, None, strength, strength, 7, 21)

def unsharp(img, sigma=1.0, amount=0.62, threshold=3):
    """Мягкая нерезкая маска: возвращает край, съеденный интерполяцией."""
    blur = cv2.GaussianBlur(img, (0,0), sigma)
    sharp = cv2.addWeighted(img, 1+amount, blur, -amount, 0)
    if threshold > 0:
        low = np.abs(img.astype(np.int16)-blur.astype(np.int16)).max(2) < threshold
        sharp[low] = img[low]
    return sharp

def upscale(img, factor=2, denoise=True):
    if denoise:
        img = deblock(img)
    h, w = img.shape[:2]
    out = cv2.resize(img, (w*factor, h*factor), interpolation=cv2.INTER_LANCZOS4)
    return unsharp(out)

def add_bleed(img, bleed_px):
    """Вылет отражением края — рисунок продолжается естественно."""
    return cv2.copyMakeBorder(img, bleed_px, bleed_px, bleed_px, bleed_px,
                              cv2.BORDER_REFLECT_101)
