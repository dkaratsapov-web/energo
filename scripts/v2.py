# -*- coding: utf-8 -*-
"""
Пересборка v2: слайд за слайдом, каждый утверждается отдельно.

Референс — текущая версия каталога. Слайд собирается, отправляется на
согласование картинкой, и только утверждённый попадает в итоговый файл.
Список утверждённых лежит в build/v2/approved.txt, порядок в документе
задаётся номером страницы, а не порядком утверждения.
"""
import os, sys, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE); sys.path.insert(0, os.path.dirname(_HERE))
import cv2, numpy as np, pymupdf, pikepdf
from rebuild import build, PW, PH, ROOT
from specs import SPECS

OUT   = 'build/v2/slides'
PREV  = 'build/v2/preview'
APPR  = 'build/v2/approved.txt'
FINAL = 'build/v2/ЭнергоГрупп_2025_v2.pdf'

def make(page, dpi=300, bleed=4.0):
    """Собрать один слайд в печатном виде."""
    return build(SPECS[page], out_dir=OUT, bleed_mm=bleed, dpi=dpi, verbose=False)

def preview(page, width=1400, with_ref=False):
    """Картинка слайда для согласования; with_ref — рядом с референсом."""
    p = pymupdf.open(f'{OUT}/page{page:02d}.pdf')[0]
    z = width/(p.trimbox.width/72*25.4/25.4*72/72*p.trimbox.width/p.trimbox.width)
    z = width/p.trimbox.width
    px = p.get_pixmap(matrix=pymupdf.Matrix(z,z), clip=p.trimbox)
    a = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width, px.n)[:,:,:3][:,:,::-1]
    out = f'{PREV}/slide{page:02d}.jpg'
    if with_ref:
        from pageio import load_page
        ref = load_page(page)
        ref = cv2.resize(ref, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
        lab = np.full((34, a.shape[1]*2+8, 3), 24, np.uint8)
        cv2.putText(lab, 'REFERENS (kak bylo)', (12,24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120,200,120), 2)
        cv2.putText(lab, 'NOVAYA SBORKA', (a.shape[1]+20,24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120,160,255), 2)
        img = np.vstack([lab, np.hstack([ref, np.full((a.shape[0],8,3),(0,0,255),np.uint8), a])])
    else:
        img = a
    cv2.imwrite(out, img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    return out

def _label(w, text, sub=''):
    """Подпись кириллицей — OpenCV её не рисует, берём шрифт проекта."""
    from PIL import Image as PImage, ImageDraw as PDraw, ImageFont as PFont
    im = PImage.new('RGB', (w, 54), (22,22,26))
    d = PDraw.Draw(im)
    f  = PFont.truetype(f'{ROOT}/fonts/static/Onest-Bold.ttf', 30)
    f2 = PFont.truetype(f'{ROOT}/fonts/static/Onest-Regular.ttf', 22)
    d.text((16, 12), text, (255,255,255), font=f)
    if sub:
        d.text((16 + d.textlength(text, font=f) + 18, 18), sub, (150,150,160), font=f2)
    return np.array(im)[:,:,::-1].copy()

def render_spread(pages, width, source):
    """Склеить две страницы в разворот. source: 'new' | 'ref'."""
    from pageio import load_page
    parts=[]
    for n in pages:
        if n is None:
            parts.append(None); continue
        if source == 'ref':
            a = load_page(n)
        else:
            p = pymupdf.open(f'{OUT}/page{n:02d}.pdf')[0]
            z = (width/2)/p.trimbox.width
            px = p.get_pixmap(matrix=pymupdf.Matrix(z,z), clip=p.trimbox)
            a = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width, px.n)[:,:,:3][:,:,::-1]
        parts.append(a)
    h = max(p.shape[0] for p in parts if p is not None)
    out=[]
    for p in parts:
        if p is None:
            p = np.full((h, width//2, 3), 245, np.uint8)
        else:
            p = cv2.resize(p, (int(p.shape[1]*h/p.shape[0]), h), interpolation=cv2.INTER_AREA)
        out.append(p)
    return np.hstack([out[0], np.full((h,3,3),(210,210,210),np.uint8), out[1]])

def compare(left, right, width=2000):
    """Разворот в формате до/после — референс сверху, новая сборка снизу."""
    ref = render_spread([left,right], width, 'ref')
    new = render_spread([left,right], width, 'new')
    if new.shape[1] != ref.shape[1]:
        new = cv2.resize(new, (ref.shape[1], int(new.shape[0]*ref.shape[1]/new.shape[1])),
                         interpolation=cv2.INTER_AREA)
    tag = f'{left}-{right}' if right else f'{left}'
    w = ref.shape[1]
    img = np.vstack([
        _label(w, f'БЫЛО — развороты {tag}', 'исходный каталог, растр 150 dpi'), ref,
        np.full((10,w,3),(22,22,26),np.uint8),
        _label(w, f'СТАЛО — развороты {tag}', 'текст в векторе, подложка 300 dpi'), new])
    out = f'{PREV}/sravnenie_{tag}.jpg'
    cv2.imwrite(out, img, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    return out

def spread(left, right, width=2200):
    """Разворот: две страницы рядом, как в готовом каталоге."""
    imgs=[]
    for n in (left, right):
        if n is None:
            imgs.append(None); continue
        p = pymupdf.open(f'{OUT}/page{n:02d}.pdf')[0]
        z = (width/2)/p.trimbox.width
        px = p.get_pixmap(matrix=pymupdf.Matrix(z,z), clip=p.trimbox)
        a = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width, px.n)
        imgs.append(a[:,:,:3][:,:,::-1].copy())
    h = max(i.shape[0] for i in imgs if i is not None)
    parts=[]
    for i in imgs:
        if i is None:
            i = np.full((h, width//2, 3), 245, np.uint8)
        elif i.shape[0] != h:
            i = cv2.resize(i,(int(i.shape[1]*h/i.shape[0]), h),interpolation=cv2.INTER_AREA)
        parts.append(i)
    img = np.hstack([parts[0], np.full((h,3,3),(200,200,200),np.uint8), parts[1]])
    tag = f'{left:02d}-{right:02d}' if right else f'{left:02d}'
    out = f'{PREV}/razvorot_{tag}.jpg'
    cv2.imwrite(out, img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    return out

def approve(page):
    done = set(read_approved()); done.add(page)
    open(APPR,'w').write('\n'.join(str(x) for x in sorted(done)))
    return sorted(done)

def read_approved():
    if not os.path.exists(APPR): return []
    return [int(x) for x in open(APPR).read().split() if x.strip().isdigit()]

def assemble():
    """Собрать итоговый файл из утверждённых слайдов."""
    pages = read_approved()
    if not pages: raise SystemExit('нет утверждённых слайдов')
    pdf = pikepdf.Pdf.new()
    for n in pages:
        with pikepdf.open(f'{OUT}/page{n:02d}.pdf') as s:
            pdf.pages.extend(s.pages)
    tmp = 'build/v2/_deck.pdf'; pdf.save(tmp)
    from make_print import to_pdfx, add_xmp
    to_pdfx(tmp, FINAL); add_xmp(FINAL)
    return FINAL, pages

if __name__=='__main__':
    cmd = sys.argv[1]
    if cmd == 'make':
        for n in [int(x) for x in sys.argv[2:]]:
            make(n); print(preview(n, with_ref=True))
    elif cmd == 'compare':
        a = int(sys.argv[2]); b = int(sys.argv[3]) if len(sys.argv)>3 else None
        for n in ([a,b] if b else [a]):
            if not os.path.exists(f'{OUT}/page{n:02d}.pdf'): make(n)
        print(compare(a,b))
    elif cmd == 'spread':
        a = int(sys.argv[2]); b = int(sys.argv[3]) if len(sys.argv)>3 else None
        for n in ([a,b] if b else [a]):
            if not os.path.exists(f'{OUT}/page{n:02d}.pdf'): make(n)
        print(spread(a,b))
    elif cmd == 'approve':
        print('утверждены:', approve(int(sys.argv[2])))
    elif cmd == 'assemble':
        f,p = assemble(); print(f'{f} — слайдов {len(p)}: {p}')
