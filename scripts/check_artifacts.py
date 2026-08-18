# -*- coding: utf-8 -*-
"""
Поиск замыленных пятен на пересобранных страницах.

Инпейнт, которым стирается впечатанный текст, при неудачных настройках
съедает детали самой фотографии. На глаз это «размазанные пятна», и
искать их постранично вручную — гиблое дело. Здесь сравнение с
оригиналом: там, где локальная детализация просела, а текста рядом нет,
и есть артефакт.
"""
import cv2, numpy as np, sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pageio import load_page, BASE_W, BASE_H

def detail(img, win=9):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mu = cv2.blur(g,(win,win))
    return np.sqrt(np.maximum(cv2.blur(g*g,(win,win))-mu*mu, 0))

def render(pdf_path):
    d = pymupdf.open(pdf_path); p = d[0]
    clip = p.trimbox if abs(p.trimbox.width-p.mediabox.width) > 1 else None
    z = BASE_W/(clip.width if clip else p.mediabox.width)
    px = p.get_pixmap(matrix=pymupdf.Matrix(z,z), clip=clip)
    a = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width, px.n)
    a = a[:,:,:3][:,:,::-1].copy()
    return cv2.resize(a,(BASE_W,BASE_H),interpolation=cv2.INTER_AREA) if a.shape[:2]!=(BASE_H,BASE_W) else a

def scan(page, pdf_path, drop=0.45, min_area=900, near=10):
    old = load_page(page)
    new = render(pdf_path)
    d_old, d_new = detail(old), detail(new)
    # где деталь просела заметно, а в оригинале она была
    lost = ((d_new < d_old*drop) & (d_old > 9)).astype(np.uint8)*255
    # под самим набором детализация падает законно: пиксельный текст
    # заменён гладким вектором. Эти зоны из проверки исключаем.
    mp = f'build/masks/pg{page:02d}.png'
    if os.path.exists(mp):
        keep = cv2.imread(mp, cv2.IMREAD_GRAYSCALE)
        band = cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                                          (near*2+1,)*2))
        lost = cv2.bitwise_and(lost, cv2.bitwise_not(band))
    lost = cv2.morphologyEx(lost, cv2.MORPH_OPEN, np.ones((5,5),np.uint8))
    lost = cv2.morphologyEx(lost, cv2.MORPH_CLOSE, np.ones((9,9),np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(lost, 8)
    spots=[]
    for i in range(1,n):
        x,y,w,h,a = st[i]
        if a < min_area: continue
        spots.append((int(x),int(y),int(w),int(h),int(a)))
    return sorted(spots, key=lambda s:-s[4]), lost

if __name__=='__main__':
    src = sys.argv[1] if len(sys.argv)>1 else 'build/pages'
    total=0
    for f in sorted(glob.glob(f'{src}/page*.pdf')):
        pg = int(os.path.basename(f)[4:6])
        spots,_ = scan(pg, f)
        if spots:
            total += len(spots)
            big = ', '.join(f'{s[2]}x{s[3]}px в ({s[0]},{s[1]})' for s in spots[:3])
            print(f'  стр {pg:02d}: подозрительных зон {len(spots)} — {big}')
    print(f'\nвсего зон с потерей детализации: {total}')
