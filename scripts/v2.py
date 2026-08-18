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
from rebuild import build, PW, PH
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
    elif cmd == 'approve':
        print('утверждены:', approve(int(sys.argv[2])))
    elif cmd == 'assemble':
        f,p = assemble(); print(f'{f} — слайдов {len(p)}: {p}')
