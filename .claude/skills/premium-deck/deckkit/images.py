# -*- coding: utf-8 -*-
"""Кадрирование и затемнение снимков — заранее, в пикселях.

Затемнение под текстом впекается в сам снимок, а не кладётся полупрозрачной
плашкой: прозрачность в PDF/X-1a приводит к растрированию всей полосы.
Увеличения нет: если исходника мало, файл остаётся маленьким, а preflight
честно показывает эффективное разрешение.
"""
import os, hashlib
import numpy as np
from PIL import Image as PImage, ImageCms

MM_IN = 25.4
VERSION = 2          # меняется вместе с обработкой — сбрасывает кэш


_sizes = {}


def src_size(path):
    """Размер исходника после снятия кромок — по нему и считаем dpi."""
    if path not in _sizes:
        im, cut = clean(path)
        _sizes[path] = (im.size, cut)
    return _sizes[path][0]


def src_cut(path):
    src_size(path)
    return _sizes[path][1]


def crop_box(sw, sh, w, h, focus=(0.5, 0.5)):
    """Наибольший прямоугольник с пропорцией w:h внутри исходника."""
    ar = w / h
    if sw / sh > ar:
        ch, cw = sh, sh * ar
    else:
        cw, ch = sw, sw / ar
    fx, fy = focus
    x0 = min(max(fx * sw - cw / 2, 0), sw - cw)
    y0 = min(max(fy * sh - ch / 2, 0), sh - ch)
    return x0, y0, x0 + cw, y0 + ch


def effective_dpi(path, w_mm, h_mm, focus=(0.5, 0.5)):
    sw, sh = src_size(path)
    x0, y0, x1, y1 = crop_box(sw, sh, w_mm, h_mm, focus)
    return (x1 - x0) / (w_mm / MM_IN)


def slivers(arr, band=0.03, jump=24.0):
    """Полоски чужого кадра по краям вырезки (остатки соседнего снимка).

    Ищем у каждого края резкий скачок среднего цвета между соседними
    строками/столбцами в пределах 3% размера. Возвращает срез (t, b, l, r) в px.
    """
    a = arr.astype(np.float32)
    h, w = a.shape[:2]
    cut = {}
    for side in 'tblr':
        if side in 'tb':
            n = max(int(h * band), 3)
            prof = a.mean(axis=1) if side == 't' else a[::-1].mean(axis=1)
        else:
            n = max(int(w * band), 3)
            prof = a.mean(axis=0) if side == 'l' else a[:, ::-1].mean(axis=0)
        d = np.linalg.norm(np.diff(prof[:n + 1], axis=0), axis=1)
        i = int(d.argmax())
        base = float(np.median(d)) + 1e-3
        cut[side] = i + 1 if d[i] > jump and d[i] > 6 * base else 0
    return cut['t'], cut['b'], cut['l'], cut['r']


def clean(path):
    """Исходник без кромок-обрезков и сколько пикселей снято с каждого края."""
    im = PImage.open(path).convert('RGB')
    t, b, l, r = slivers(np.asarray(im))
    if t or b or l or r:
        im = im.crop((l, t, im.width - r, im.height - b))
    return im, (t, b, l, r)


def _shade(arr, shade, frame=None):
    """frame — доля (x0,y0,x1,y1) области обреза внутри кадра с вылетом,
    чтобы градиент лёг одинаково в превью и в печати."""
    h, w = arr.shape[:2]
    fx0, fy0, fx1, fy1 = frame or (0, 0, 1, 1)
    side, ext, amt = shade.get('side', 'bottom'), shade.get('extent', 0.5), shade.get('amount', 0.8)
    to = np.array(shade['to'], dtype=np.float32)
    if side in ('bottom', 'top'):
        u = (np.arange(h) / max(h - 1, 1) - fy0) / (fy1 - fy0)
        d = (1 - u) if side == 'bottom' else u
        a = np.clip(1 - d / ext, 0, 1)
        a = (a * a * (3 - 2 * a)) * amt
        a = a[:, None, None]
    else:
        u = (np.arange(w) / max(w - 1, 1) - fx0) / (fx1 - fx0)
        d = u if side == 'left' else (1 - u)
        a = np.clip(1 - d / ext, 0, 1)
        a = (a * a * (3 - 2 * a)) * amt
        a = a[None, :, None]
    return arr * (1 - a) + to * a


def to_cmyk(im, tac_max):
    """RGB -> CMYK FOGRA39 с ограничением суммы красок в каждой точке."""
    from .pdfx import _transform
    c = np.asarray(ImageCms.applyTransform(im, _transform()), dtype=np.float32)
    lim = (tac_max - 8) / 100 * 255
    k = c[..., 3]
    cmy = c[..., :3].sum(-1)
    over = c.sum(-1) > lim
    f = np.where(over, np.clip((lim - k) / np.maximum(cmy, 1e-3), 0, 1), 1.0)
    c[..., :3] *= f[..., None]
    return PImage.fromarray(np.clip(c + 0.5, 0, 255).astype(np.uint8), 'CMYK')


def prepare(path, w_mm, h_mm, focus=(0.5, 0.5), shade=None, dpi=300, cache='/tmp',
            frame=None, cmyk_tac=None):
    """Файл, готовый к размещению w×h мм: кадрирован, затемнён, не больше dpi.
    cmyk_tac — для печати: сразу CMYK FOGRA39 с ограничением покрытия."""
    key = hashlib.md5(repr((VERSION, os.path.abspath(path), os.path.getmtime(path), round(w_mm, 2),
                            round(h_mm, 2), tuple(focus), repr(shade), dpi, frame,
                            cmyk_tac)).encode()).hexdigest()[:16]
    out = os.path.join(cache, f'{key}.{"tif" if cmyk_tac else "jpg"}')
    if os.path.exists(out):
        return out
    im, _ = clean(path)
    box = crop_box(*im.size, w_mm, h_mm, focus)
    im = im.crop(tuple(round(v) for v in box))
    need = round(w_mm / MM_IN * dpi)
    if im.width > need:
        im = im.resize((need, round(need * h_mm / w_mm)), PImage.LANCZOS)
    if shade:
        arr = np.asarray(im, dtype=np.float32)
        for sh in (shade if isinstance(shade, (list, tuple)) else [shade]):
            arr = _shade(arr, sh, frame)
        im = PImage.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    os.makedirs(cache, exist_ok=True)
    if cmyk_tac:
        to_cmyk(im, cmyk_tac).save(out, 'TIFF', compression='tiff_lzw', dpi=(dpi, dpi))
    else:
        im.save(out, 'JPEG', quality=92, subsampling=0, dpi=(dpi, dpi))
    return out
