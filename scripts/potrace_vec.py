# -*- coding: utf-8 -*-
"""
Векторизация через potrace — промышленный трассировщик битмапов.

Самодельная обводка через контуры OpenCV даёт ломаную: углы срезаются,
кривая приближается отрезками, и на печати это видно как огранку.
potrace строит кривые Безье и оптимизирует их, поэтому силуэт выходит
гладким при любом увеличении.

Многоуровневая схема: кадр режется на несколько слоёв плотности, каждый
трассируется отдельно и рисуется со своей прозрачностью. Так сохраняются
полутона — тонкие раскосы не пропадают и не раздуваются.
"""
import os, re, subprocess, tempfile
import cv2, numpy as np

def _pbm(mask, path):
    """Записать бинарную маску в PBM (potrace принимает её напрямую)."""
    h, w = mask.shape
    with open(path, 'wb') as f:
        f.write(b'P4\n%d %d\n' % (w, h))
        f.write(np.packbits(mask > 0, axis=1).tobytes())

_NUM = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')

def _parse_svg_paths(svg):
    """Вернуть [(команда, [числа]), ...] для каждого path из SVG potrace."""
    out = []
    for d in re.findall(r'<path[^>]*\sd="([^"]+)"', svg):
        toks = re.findall(r'([MmLlHhVvCcSsZz])|([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', d)
        cmds, cur, nums = [], None, []
        for c, n in toks:
            if c:
                if cur: cmds.append((cur, nums)); nums = []
                cur = c
            else:
                nums.append(float(n))
        if cur: cmds.append((cur, nums))
        out.append(cmds)
    return out

def trace_layer(mask, turdsize=2, alphamax=1.0, opttolerance=0.2):
    """Один слой: маска -> список путей в координатах маски (y вниз)."""
    with tempfile.TemporaryDirectory() as td:
        pbm, svg = os.path.join(td, 'm.pbm'), os.path.join(td, 'm.svg')
        _pbm(mask, pbm)
        subprocess.run(['potrace', pbm, '-s', '-o', svg,
                        '-t', str(turdsize), '-a', str(alphamax),
                        '-O', str(opttolerance), '-u', '1'],
                       check=True, capture_output=True)
        return _parse_svg_paths(open(svg, encoding='utf-8', errors='ignore').read())

def levels(img, lv=(0.18, 0.36, 0.58, 0.80), up=4, crop_bottom=0.0,
           turdsize=2, alphamax=1.0, opttolerance=0.2, denoise=True,
           sharpen=0.0):
    """Разложить кадр на слои плотности и трассировать каждый.

    denoise — сгладить небо, сохранив кромку конструкции. Без этого шум
    матрицы попадает в маску и трассируется как рваная бахрома по краю.
    sharpen — поднять контраст кромки перед разложением: на 124 dpi край
    размазан на два-три пикселя, и уровни «плывут».
    """
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if denoise:
        # двусторонний фильтр: усредняет небо, но не трогает границу силуэта
        g = cv2.bilateralFilter(g, 9, 28, 9)
    sky = cv2.GaussianBlur(
        cv2.dilate(g, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41))), (81, 81), 0)
    d = np.clip((sky - g)/max(np.percentile(sky - g, 99.5), 1e-3), 0, 1)
    if sharpen:
        # нерезкая маска по карте плотности — кромка становится круче,
        # и слои ложатся по самому краю, а не по его размытию
        blur = cv2.GaussianBlur(d, (0, 0), 1.1)
        d = np.clip(d + (d - blur)*sharpen, 0, 1)
    big = cv2.resize(d, None, fx=up, fy=up, interpolation=cv2.INTER_LANCZOS4)
    if crop_bottom > 0:
        big[int(big.shape[0]*(1-crop_bottom)):] = 0
    out = []
    for i, t in enumerate(lv):
        m = (big > t).astype(np.uint8)
        # на светлых уровнях в маску лезет шум неба — там отсекаем крупнее,
        # иначе вокруг фермы появляются рыхлые «облака»
        ts = turdsize * max(1, int(round(10 * (1 - i/max(len(lv)-1, 1))**2.2)))
        out.append((t, trace_layer(m, ts, alphamax, opttolerance),
                    big.shape[1], big.shape[0]))
    return out

def draw(c, layers, ox, oy, w, h, color, a0=0.38, a1=1.0, ramp=None):
    """Отрисовать слои на canvas. Координаты potrace: y вверх от низа.

    ramp=(светлый, тёмный) рисует слои НЕПРОЗРАЧНЫМИ цветами по градации от
    светлого к тёмному вместо наложения прозрачностей. Так и задумано для
    печати: PDF/X-1a живой прозрачности не допускает, а её сведение в
    ghostscript растрирует полосу целиком — вместе с набором.
    """
    from reportlab.pdfgen.canvas import FILL_EVEN_ODD
    n = len(layers)
    for i, (t, paths, sw, sh) in enumerate(layers):
        k = (i/(n-1))**0.75 if n > 1 else 1.0
        alpha = a0 + (a1 - a0)*k
        col = color
        if ramp is not None:
            col = tuple(ramp[0][j] + (ramp[1][j] - ramp[0][j])*k for j in range(3))
            alpha = None
        sx, sy = w/sw, h/sh
        X = lambda v: ox + v*sx
        Y = lambda v: oy + v*sy          # potrace уже отдаёт y снизу вверх
        c.saveState()
        if alpha is None:
            c.setFillColorRGB(*[v/255 for v in col])
        else:
            c.setFillColorRGB(*[v/255 for v in col], alpha=alpha)
        for cmds in paths:
            p = c.beginPath(); cx = cy = 0.0; sx0 = sy0 = 0.0; started = False
            for cmd, nums in cmds:
                rel = cmd.islower(); k = cmd.upper()
                if k == 'M':
                    for j in range(0, len(nums)-1, 2):
                        x, y = nums[j], nums[j+1]
                        cx, cy = (cx+x, cy+y) if rel else (x, y)
                        if j == 0:
                            p.moveTo(X(cx), Y(cy)); sx0, sy0 = cx, cy; started = True
                        else:
                            p.lineTo(X(cx), Y(cy))
                elif k == 'L':
                    for j in range(0, len(nums)-1, 2):
                        x, y = nums[j], nums[j+1]
                        cx, cy = (cx+x, cy+y) if rel else (x, y)
                        p.lineTo(X(cx), Y(cy))
                elif k == 'H':
                    for x in nums:
                        cx = cx+x if rel else x
                        p.lineTo(X(cx), Y(cy))
                elif k == 'V':
                    for y in nums:
                        cy = cy+y if rel else y
                        p.lineTo(X(cx), Y(cy))
                elif k == 'C':
                    for j in range(0, len(nums)-5, 6):
                        a = nums[j:j+6]
                        if rel:
                            pts = [(cx+a[0], cy+a[1]), (cx+a[2], cy+a[3]), (cx+a[4], cy+a[5])]
                        else:
                            pts = [(a[0], a[1]), (a[2], a[3]), (a[4], a[5])]
                        p.curveTo(X(pts[0][0]), Y(pts[0][1]),
                                  X(pts[1][0]), Y(pts[1][1]),
                                  X(pts[2][0]), Y(pts[2][1]))
                        cx, cy = pts[2]
                elif k == 'Z':
                    if started: p.close(); cx, cy = sx0, sy0
            c.drawPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)
        c.restoreState()
