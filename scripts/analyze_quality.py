# -*- coding: utf-8 -*-
"""
Анализ реального (эффективного) разрешения растра постранично.

МЕТОД. Страница = 1240x1754 @150dpi. Для печати нужно 300dpi (2480x3508),
т.е. любое фото придётся брать заново в HD. Но фото делятся на два класса:

  A. «Резкое на 150dpi» — оригинал у клиента хороший, деталь есть вплоть
     до Найквиста. HD-оригинал точно существует -> просим его.
  B. «Уже мыльное на 150dpi» — фото было апскейлено/пережато ДО вёрстки
     (скрин из мессенджера, кроп с телефона). HD-оригинал может и не
     существовать -> просим отдельно и предупреждаем клиента.

Тест на апскейл: уменьшаем в k раз и возвращаем обратно. Если картинка
почти не изменилась — деталей выше 1/k Найквиста в ней нет, т.е. она
была растянута примерно в k раз. residual = ср.модуль(img-up)/контраст.
Метрика считается ТОЛЬКО по текстурным зонам (гладкое небо/плашки
исключаются), иначе результат смазывается.
"""
import numpy as np, cv2, json

PAGE_W, PAGE_H = 1240, 1754

def load(p):
    im = cv2.imread(p)
    if im.shape[1] != PAGE_W:
        im = cv2.resize(im, (PAGE_W, PAGE_H), interpolation=cv2.INTER_AREA)
    return im

def texture_mask(g, win=9, thr=8.0):
    """Зоны с реальной текстурой: локальное СКО выше порога."""
    f = g.astype(np.float32)
    mu = cv2.blur(f,(win,win))
    sd = np.sqrt(np.maximum(cv2.blur(f*f,(win,win))-mu*mu, 0))
    return sd > thr

def upscale_factor(img):
    """Во сколько раз картинка была растянута (1 = родное разрешение)."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = texture_mask(g)
    if m.sum() < 2000: return None, 0.0
    base = float(g[m].std())
    if base < 3: return None, 0.0
    h,w = g.shape
    res={}
    for k in (2,3,4):
        small = cv2.resize(g,(max(w//k,1),max(h//k,1)),interpolation=cv2.INTER_AREA)
        up    = cv2.resize(small,(w,h),interpolation=cv2.INTER_CUBIC)
        d = np.abs(g.astype(np.float32)-up.astype(np.float32))
        res[k] = float(d[m].mean())/base
    # если потеря при k=2 ничтожна -> деталей выше 1/2 Найквиста нет
    if   res[2] < 0.030: f = 4.0 if res[4] < 0.045 else (3.0 if res[3] < 0.040 else 2.0)
    elif res[2] < 0.055: f = 2.0
    elif res[2] < 0.085: f = 1.5
    else:                f = 1.0
    return f, res[2]

def flat_mask(img, win=16, thr=6.0):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mu = cv2.blur(g,(win,win))
    sd = np.sqrt(np.maximum(cv2.blur(g*g,(win,win))-mu*mu,0))
    return sd < thr

def photo_boxes(img, min_area=40000):
    m = (~flat_mask(img)).astype(np.uint8)*255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25,25),np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN,  np.ones((9,9),np.uint8))
    n,lab,stats,_ = cv2.connectedComponentsWithStats(m,8)
    out=[]
    for i in range(1,n):
        x,y,w,h,a = stats[i]
        if a<min_area or w<150 or h<150: continue
        out.append((int(x),int(y),int(w),int(h),int(a)))
    return sorted(out,key=lambda b:-b[4])

def analyze(path):
    img = load(path); out=[]
    for (x,y,w,h,a) in photo_boxes(img):
        f,r = upscale_factor(img[y:y+h, x:x+w])
        if f is None: continue
        out.append(dict(box=[x,y,w,h], up=f, resid=round(r,4),
                        eff_dpi=round(150.0/f),
                        need_px=[round(w*2), round(h*2)]))
    return out

if __name__=='__main__':
    res={}
    print(f"{'стр':>4} {'блок (x,y,w,h)':<24} {'растянуто':>9} {'эфф.dpi':>8}  вердикт")
    for i in range(1,33):
        res[i]=analyze(f'page_images_150dpi/pg{i:02d}.jpg')
        for r in res[i]:
            v = ('РОДНОЕ 150dpi — оригинал у клиента хороший' if r['up']<=1.0 else
                 f"мягкое (~{r['up']}x) — проверить оригинал"  if r['up']<=1.5 else
                 f"АПСКЕЙЛ ~{r['up']:.0f}x — фото было плохим ДО вёрстки")
            print(f"{i:>4} {str(r['box']):<24} {r['up']:>8.1f}x {r['eff_dpi']:>8}  {v}")
    json.dump(res, open('analysis/quality.json','w'), ensure_ascii=False, indent=1)
