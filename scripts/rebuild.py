# -*- coding: utf-8 -*-
"""
Пересборка страницы: чистый фон + живой вектор-текст Onest.

Спека блока задаёт ПРЯМОУГОЛЬНИК ПОИСКА и список строк, которые в нём
лежат — по порядку сверху вниз. Всё остальное (координаты, ширина,
базовая линия, цвет, кегль) снимается с оригинала автоматически, поэтому
спека не разъезжается при подстройке детектора.

Кегль подбирается по метрикам шрифта под измеренную ширину строки:
    size = width_pt / stringWidth(text, font, 1.0)
Ручных подгонок нет — ширина строки совпадает с оригиналом.
"""
import cv2, numpy as np, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from textmask import find_lines, erase
from metrics import line_metrics, dot_circles
from weight import guess_weight, WEIGHTS

PW, PH = 595.445669, 841.691339
BASE_W, BASE_H = 1240, 1754
SX, SY = PW/BASE_W, PH/BASE_H
X = lambda px: px*SX
Y = lambda py: PH - py*SY

# маска шире глифа примерно на 1 px с каждой стороны (антиалиасинг)
W_BIAS = 3.0
R_BIAS = 1.2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_reg = False
def register_fonts():
    global _reg
    if _reg: return
    for w in ['Regular','Medium','SemiBold','Bold','ExtraBold']:
        pdfmetrics.registerFont(TTFont('Onest-'+w, f'{ROOT}/fonts/Onest-{w}.ttf'))
    _reg = True

def size_for(text, font, width_px):
    sw = pdfmetrics.stringWidth(text, font, 1.0)
    return (max(width_px-W_BIAS,1)*SX)/sw if sw else 10.0

def measure(img, block):
    """Снять метрики строк блока и сопоставить с текстами спеки."""
    d = dict(dark=block.get('dark',False), thr=block.get('thr',18),
             k=block.get('k',31), gap=block.get('gap',3),
             row_frac=block.get('row_frac',0.02), only=block.get('only'))
    lines = find_lines(img, block['box'], **d)
    lines.sort(key=lambda l:(l[1],l[0]))
    if 'skip' in block:
        lines = [l for i,l in enumerate(lines) if i not in block['skip']]
    if 'pick' in block:
        lines = [lines[i] for i in block['pick']]
    texts = block['texts']
    if len(lines) != len(texts):
        raise SystemExit(f"  !! блок {block['box']}: найдено строк {len(lines)}, "
                         f"в спеке {len(texts)}\n     {[ (l[0],l[1],l[2]-l[0]) for l in lines]}")
    out=[]
    for l,t in zip(lines,texts):
        m = line_metrics(img, l, dark=d['dark'], k=d['k'], thr=d['thr'], only=d['only'])
        if m is None: continue
        m['text']=t; m['line']=l
        out.append(m)
    return out

def build(spec, src_dir='page_images_150dpi', out_dir='vector_pages',
          bg_override=None, scale=1, verbose=True):
    """Собрать одну страницу. scale>1 — фон подставляется увеличенным."""
    register_fonts()
    pg = spec['page']
    img = cv2.imread(bg_override or f'{src_dir}/pg{pg:02d}.jpg')
    if img.shape[1] != BASE_W:
        img = cv2.resize(img,(BASE_W,BASE_H),interpolation=cv2.INTER_AREA)

    blocks=[]
    for b in spec.get('blocks',[]):
        blocks.append((b, measure(img, b)))
    dots=[]
    for db in spec.get('dots',[]):
        dots += dot_circles(img, db)

    # ---- стереть старый впечатанный текст ----
    light_boxes, dark_boxes = [], []
    for b,ms in blocks:
        pad = b.get('pad',10)
        for m in ms:
            x0,y0,x1,y1 = m['line']
            (dark_boxes if b.get('dark') else light_boxes).append(
                (max(0,x0-pad), max(0,y0-pad), min(BASE_W,x1+pad), min(BASE_H,y1+pad)))
    for eb in spec.get('erase',[]):    light_boxes.append(tuple(eb))
    for eb in spec.get('erase_dark',[]): dark_boxes.append(tuple(eb))
    for (cx,cy,r) in dots:
        rr=int(r+4); light_boxes.append((int(cx-rr),int(cy-rr),int(cx+rr),int(cy+rr)))

    clean = img
    if light_boxes: clean = erase(clean, light_boxes, dark=False, **spec.get('erase_opt',{}))
    if dark_boxes:  clean = erase(clean, dark_boxes,  dark=True,  **spec.get('erase_opt_dark',{}))

    os.makedirs('build/backgrounds', exist_ok=True)
    bgp = f'build/backgrounds/pg{pg:02d}_clean.jpg'
    if scale != 1:
        clean = cv2.resize(clean,(BASE_W*scale,BASE_H*scale),interpolation=cv2.INTER_LANCZOS4)
    cv2.imwrite(bgp, clean, [int(cv2.IMWRITE_JPEG_QUALITY), 96])

    # ---- вектор поверх ----
    os.makedirs(out_dir, exist_ok=True)
    outp = f'{out_dir}/page{pg:02d}.pdf'
    c = canvas.Canvas(outp, pagesize=(PW,PH))
    c.drawImage(bgp, 0, 0, width=PW, height=PH)

    for (cx,cy,r) in dots:
        col = spec.get('dot_rgb',(252,144,43))
        c.setFillColorRGB(*[v/255 for v in col])
        c.circle(X(cx), Y(cy), max(r-R_BIAS,1)*SX, stroke=0, fill=1)

    for b,ms in blocks:
        # если начертание не задано — подбираем по плотности штриха
        if 'font' not in b:
            gs=[guess_weight(img, m['line'], m['text'], dark=b.get('dark',False))[0] for m in ms]
            font='Onest-'+max(set(gs), key=gs.count)
            print(f"    [подбор] блок {b['box']}: {font}  (по строкам: {gs})")
        else:
            font = b['font']
        if b.get('size','group')=='group':
            sizes=[size_for(m['text'],font,m['w']) for m in ms]
            sz = float(np.median(sizes)) if b.get('robust') else max(sizes)
            per=[sz]*len(ms)
        else:
            per=[size_for(m['text'],font,m['w']) for m in ms]
        rgb = b.get('rgb')
        if rgb is None:
            arr=np.array([m['rgb'] for m in ms]); rgb=tuple(arr.mean(0).astype(int))
        c.setFillColorRGB(*[v/255 for v in rgb])
        sk = b.get('skew', 0.0)       # наклон в градусах (эмуляция курсива)
        for m,s in zip(ms,per):
            c.setFont(font, s)
            if sk:
                # наклон вокруг базовой линии: сдвигаем верх глифа вправо
                t = np.tan(np.radians(sk))
                c.saveState()
                c.transform(1, 0, t, 1, -t*Y(m['base']), 0)
                c.drawString(X(m['x']), Y(m['base']) , m['text'])
                c.restoreState()
            else:
                c.drawString(X(m['x']), Y(m['base']), m['text'])
        if verbose:
            print(f"  стр{pg:02d} блок {b['box']} шрифт={font} кегль={per[0]:.1f}pt "
                  f"строк={len(ms)} цвет={tuple(int(v) for v in rgb)}")
    c.showPage(); c.save()
    return outp
