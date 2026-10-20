# -*- coding: utf-8 -*-
"""
Просмотрщик собранного каталога — чтобы видеть итог, а не воображать его.

Превью в масштабе 25 % скрывает ровно те дефекты, которые на полосе видны
первыми: завал горизонта, съехавшую на полмиллиметра линейку, набор, уехавший
под кадр. Поэтому здесь два режима:

  страница/разворот целиком — общее впечатление;
  вырезка с увеличением    — проверка конкретного места.

И в обоих при желании кладётся ОПОРНАЯ СЕТКА: горизонтали через заданный шаг.
Без неё «криво или не криво» решается на глаз и решается неверно — глаз
подстраивается под наклонённую сцену и перестаёт его замечать.

    python3 scripts/look.py build/v3/...pdf 15            # полоса 15
    python3 scripts/look.py ...pdf 15 --grid              # с сеткой
    python3 scripts/look.py ...pdf 15 --crop 0,0.3,1,0.8 --dpi 300
    python3 scripts/look.py ...pdf --sheet                # контактный лист
"""
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2, numpy as np, pymupdf

OUT = os.environ.get('LOOK_DIR', '/tmp/claude-0/look')


def render(pdf, page=1, dpi=150, crop=None, trim=True):
    """Полоса (или её часть) в массив BGR. crop — доли (x0,y0,x1,y1)."""
    d = pymupdf.open(pdf)
    p = d[page - 1]
    box = p.trimbox if trim else p.mediabox
    if crop:
        x0, y0, x1, y1 = crop
        box = pymupdf.Rect(box.x0 + box.width*x0, box.y0 + box.height*y0,
                           box.x0 + box.width*x1, box.y0 + box.height*y1)
    z = dpi/72
    px = p.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=box)
    a = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width, px.n)
    return a[:, :, :3][:, :, ::-1].copy()


def grid(img, step_mm=10, dpi=150, color=(0, 220, 255)):
    """Опорная сетка поверх вырезки: горизонтали, каждая пятая ярче.

    Это не украшение, а измерительный прибор: наклон кадра виден только
    рядом с заведомо горизонтальной линией.
    """
    out = img.copy()
    step = step_mm/25.4*dpi
    h, w = img.shape[:2]
    i = 0
    y = 0.0
    while y < h:
        th = 1
        c = color if i % 5 else (0, 160, 255)
        cv2.line(out, (0, int(y)), (w, int(y)), c, th, cv2.LINE_AA)
        y += step; i += 1
    return cv2.addWeighted(img, 0.72, out, 0.28, 0)


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    path = f'{OUT}/{name}.jpg'
    cv2.imwrite(path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 94])
    return path


def sheet(pdf, cols=4, w=430):
    """Контактный лист всего файла одной картинкой."""
    d = pymupdf.open(pdf)
    tiles = []
    for i in range(len(d)):
        a = render(pdf, i + 1, dpi=w/(d[i].trimbox.width/72)*1.0)
        hh = int(a.shape[0]*w/a.shape[1])
        a = cv2.resize(a, (w, hh), interpolation=cv2.INTER_AREA)
        pad = np.full((int(w*1.46), w, 3), 248, np.uint8)
        pad[:min(hh, pad.shape[0])] = a[:min(hh, pad.shape[0])]
        cv2.putText(pad, str(i + 1), (6, pad.shape[0] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1, cv2.LINE_AA)
        tiles.append(pad)
    rows = []
    for i in range(0, len(tiles), cols):
        r = tiles[i:i+cols]
        r += [np.full_like(tiles[0], 248)]*(cols - len(r))
        rows.append(np.hstack(r))
    return np.vstack(rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('page', nargs='?', type=int, default=1)
    ap.add_argument('--dpi', type=int, default=150)
    ap.add_argument('--crop', help='x0,y0,x1,y1 в долях полосы')
    ap.add_argument('--grid', action='store_true')
    ap.add_argument('--step', type=float, default=10.0, help='шаг сетки, мм')
    ap.add_argument('--sheet', action='store_true')
    ap.add_argument('--name')
    a = ap.parse_args()
    if a.sheet:
        print(save(sheet(a.pdf), a.name or 'sheet'))
        sys.exit()
    crop = tuple(float(v) for v in a.crop.split(',')) if a.crop else None
    img = render(a.pdf, a.page, a.dpi, crop)
    if a.grid:
        img = grid(img, a.step, a.dpi)
    print(save(img, a.name or f'p{a.page:02d}'))
