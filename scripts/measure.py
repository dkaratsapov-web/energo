# -*- coding: utf-8 -*-
"""
Измеритель раскладки: находит горизонтальные полосы текста и оранжевые маркеры
на постраничном изображении (1240x1754 px @150dpi).
Используется, чтобы снять координаты/ширину текста для точной пересборки вектором.
"""
import numpy as np
from PIL import Image

def text_bands(path, thr=(205,205,213), ymin=0, ymax=None, xmax=1240, minrun=12):
    """Возвращает список (y0,y1,x0,x1) полос светлого (белого) текста."""
    a=np.array(Image.open(path).convert('RGB')).astype(int)
    H,W,_=a.shape; ymax=ymax or H
    R,G,B=a[...,0],a[...,1],a[...,2]
    m=(R>thr[0])&(G>thr[1])&(B>thr[2])
    m[:ymin]=False; m[ymax:]=False; m[:,xmax:]=False
    rows=m.sum(axis=1); res=[]; inl=False; s=0
    for y in range(len(rows)):
        if rows[y]>minrun and not inl: s=y; inl=True
        elif rows[y]<=minrun and inl: res.append((s,y)); inl=False
    out=[]
    for s,e in res:
        xs=np.where(m[s:e].any(axis=0))[0]
        out.append((s,e,int(xs.min()),int(xs.max())))
    return out

def orange_dots(path, ymin=0, xmax=300):
    """Возвращает список (cy,cx,r) оранжевых маркеров (буллетов)."""
    a=np.array(Image.open(path).convert('RGB')).astype(int)
    R,G,B=a[...,0],a[...,1],a[...,2]
    o=(R>200)&(G>90)&(G<185)&(B<85)
    o[:ymin]=False; o[:,xmax:]=False
    col=o.sum(axis=1); res=[]; inl=False; s=0
    for y in range(len(col)):
        if col[y]>4 and not inl: s=y; inl=True
        elif col[y]<=4 and inl:
            xs=np.where(o[s:y].any(axis=0))[0]
            res.append(((s+y)//2,int((xs.min()+xs.max())/2),int((xs.max()-xs.min())/2)))
            inl=False
    return res

if __name__=='__main__':
    import sys
    p=sys.argv[1]
    print('TEXT BANDS (y0,y1,x0,x1):')
    for b in text_bands(p): print('  ',b)
    print('ORANGE DOTS (cy,cx,r):', orange_dots(p))
