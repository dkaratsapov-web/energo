# -*- coding: utf-8 -*-
"""
Завал горизонта: измерение и правка.

Съёмка велась с рук, и часть кадров завалена на один-три градуса. На экране
в масштабе 25 % это не видно, а на полосе каталога видно сразу — особенно
там, где в кадре есть длинная горизонталь: ограждение подстанции, кромка
дороги, парапет здания. Глазами тридцать два разворота так не проверишь,
поэтому угол меряется.

Как меряется. Канни + вероятностное преобразование Хафа дают отрезки; угол
каждого сворачивается по модулю 90°, потому что заваленному кадру
одинаково «не на месте» и горизонталь, и вертикаль. Отрезки взвешиваются
длиной: длинная кромка ограждения весит больше, чем сетка рабицы. Берётся
не среднее, а пик взвешенной гистограммы — среднее уводят диагонали
(раскосы опор, откосы траншей), которых в этих кадрах много.

Как правится. Поворот на найденный угол с последующей обрезкой до
наибольшего вписанного прямоугольника той же пропорции. Обрезка стоит
разрешения: поворот на 2° съедает около 3,5 % ширины. При исходных 1240 px
это 43 px, то есть 147 dpi превращаются в 142. Поэтому правятся только
кадры с заметным завалом — ниже порога дешевле оставить как есть.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2, numpy as np

MIN_DEG = 0.45          # ниже — не правим: обрезка дороже пользы
MAX_DEG = 7.0           # выше — это не завал, а ракурс; трогать нельзя


def tilt(img, bins=180):
    """Угол завала в градусах: >0 — кадр наклонён против часовой стрелки."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    edges = cv2.Canny(g, 60, 170, apertureSize=3)
    h, w = g.shape
    lines = cv2.HoughLinesP(edges, 1, np.pi/720, threshold=60,
                            minLineLength=int(min(h, w)*0.22), maxLineGap=6)
    if lines is None:
        return 0.0, 0
    hist = np.zeros(bins, np.float64)
    n = 0
    for seg in lines.reshape(-1, 4):
        x1, y1, x2, y2 = (int(v) for v in seg)
        L = math.hypot(x2 - x1, y2 - y1)
        a = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 90.0
        if a > 45:
            a -= 90.0                       # сворачиваем в [-45, 45]
        if abs(a) > 12:
            continue                        # диагонали раскосов и откосов
        hist[int((a + 45)/90*bins) % bins] += L
        n += 1
    if n < 4 or hist.max() <= 0:
        return 0.0, n
    # пик сглаженной гистограммы, уточнённый по соседям
    sm = cv2.GaussianBlur(hist.reshape(-1, 1), (1, 5), 0).ravel()
    k = int(sm.argmax())
    lo, hi = max(k-2, 0), min(k+3, bins)
    wsum = sm[lo:hi].sum()
    centre = (sm[lo:hi]*np.arange(lo, hi)).sum()/wsum if wsum else k
    return (centre/bins*90 - 45), n


def rotate(img, deg):
    """Повернуть и обрезать до вписанного прямоугольника НАИБОЛЬШЕЙ ШИРИНЫ.

    Обрезка с сохранением пропорции на широком кадре стоит дорого: при 3° и
    пропорции 1,9 она съедает 9 % ширины. А ширина и есть разрешение на
    полосе — высоту вёрстка всё равно пересчитывает из пропорции кадра.
    Поэтому сохраняем ширину и отдаём высоту: из условий вписанности
        W·cos a + H·sin a ≤ w,   W·sin a + H·cos a ≤ h
    получается H = (h·cos a − w·sin a)/cos 2a и W = (w − H·sin a)/cos a.
    Те же 3° на том же кадре стоят 2,3 % ширины вместо 9.
    """
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w/2, h/2), deg, 1.0)
    out = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LANCZOS4,
                         borderMode=cv2.BORDER_REPLICATE)
    a = math.radians(abs(deg))
    if w >= h:
        nh = (h*math.cos(a) - w*math.sin(a))/math.cos(2*a)
        nw = (w - nh*math.sin(a))/math.cos(a)
    else:
        nw = (w*math.cos(a) - h*math.sin(a))/math.cos(2*a)
        nh = (h - nw*math.sin(a))/math.cos(a)
    nw, nh = int(nw) - 2, int(nh) - 2          # запас от краёв поворота
    x, y = (w - nw)//2, (h - nh)//2
    return out[y:y+nh, x:x+nw]


def fix(path, out=None, verbose=True):
    """Выровнять кадр, если он завален. Возвращает (путь, угол, поправлен)."""
    img = cv2.imread(path)
    deg, n = tilt(img)
    name = os.path.basename(path)
    if not (MIN_DEG <= abs(deg) <= MAX_DEG):
        if verbose:
            print(f'{name:22s} {deg:+5.2f}°  ({n} отрезков)  — оставлен')
        return path, deg, False
    fixed = rotate(img, deg)
    out = out or path
    cv2.imwrite(out, fixed)
    if verbose:
        h0, h1 = img.shape[1], fixed.shape[1]
        print(f'{name:22s} {deg:+5.2f}°  ({n} отрезков)  — выровнен, '
              f'ширина {h0}→{h1} px ({(1-h1/h0)*100:.1f} %)')
    return out, deg, True


if __name__ == '__main__':
    import glob
    PH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
         '/presentation-project/05_assets/photos'
    files = sys.argv[1:] or sorted(glob.glob(f'{PH}/*.png'))
    for f in files:
        img = cv2.imread(f)
        deg, n = tilt(img)
        mark = '  ЗАВАЛ' if MIN_DEG <= abs(deg) <= MAX_DEG else ''
        print(f'{os.path.basename(f):22s} {deg:+6.2f}°  отрезков {n:3d}{mark}')
