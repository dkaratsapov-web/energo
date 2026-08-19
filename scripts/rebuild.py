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
from PIL import Image, ImageDraw, ImageFont
from textmask import find_lines, erase
from pageio import load_page, fit
from upscale import upscale, add_bleed
from shapes import rects as shape_rects
from metrics import line_metrics, dot_circles
from weight import guess_weight, WEIGHTS
from bearings import bearings

# Точный A4 = 210x297 мм. В исходнике страница была 595.4457x841.6913 pt
# (210.06x296.93 мм) — расхождение в десятые доли миллиметра; типография
# требует размер строго по продукции, поэтому приводим к точному A4.
MM = 72.0/25.4
PW, PH = 210*MM, 297*MM
BASE_W, BASE_H = 1240, 1754
SX, SY = PW/BASE_W, PH/BASE_H
X = lambda px: px*SX
Y = lambda py: PH - py*SY

# маска шире глифа примерно на 1 px с каждой стороны (антиалиасинг)
W_BIAS = 2.0
R_BIAS = 1.2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_reg = False
def register_fonts():
    global _reg
    if _reg: return
    # fonts/static — начертания с исправленными именами (см. fix_fonts.py):
    # в исходных файлах у всех весов одно PostScript-имя, и ReportLab
    # встраивал в PDF единственный светлый шрифт вместо пяти.
    base = f'{ROOT}/fonts/static' if os.path.isdir(f'{ROOT}/fonts/static') else f'{ROOT}/fonts'
    for w in ['Regular','Medium','SemiBold','Bold','ExtraBold']:
        pdfmetrics.registerFont(TTFont('Onest-'+w, f'{base}/Onest-{w}.ttf'))
    _reg = True

DIGIT_H = 0.724   # высота цифры в долях кегля (Onest)

def size_by_height(cap_px):
    """Кегль по измеренной высоте цифр.

    Для коротких наклонных чисел ширина — плохая опора: прямоугольник
    строки растянут наклоном, а на паре глифов ошибка трекинга даёт
    заметный сдвиг. Высота от наклона не зависит.
    """
    return (cap_px*SY)/DIGIT_H

def size_for(text, font, width_px, skew=0.0, cap_px=0.0):
    """Кегль, при котором строка имеет измеренную ширину.

    У наклонного начертания прямоугольник строки шире самого набора:
    верх глифа уезжает вправо на tan(угол)*высоту. Если это не вычесть,
    кегль завышается — на 12 градусах и крупных цифрах до 15 %.
    """
    # ширина ЧЕРНИЛ, а не пера: stringWidth — это advance, в него входят
    # боковые отступы первого и последнего глифа, которых на растре нет
    lsb, rsb = bearings(font, text)
    sw = pdfmetrics.stringWidth(text, font, 1.0) - lsb - rsb
    w = max(width_px - W_BIAS - (np.tan(np.radians(skew))*cap_px if skew else 0.0), 1)
    return (w*SX)/sw if sw > 0 else 10.0

def measure(img, block):
    """Снять метрики строк блока и сопоставить с текстами спеки."""
    d = dict(dark=block.get('dark',False), thr=block.get('thr',18),
             k=block.get('k',31), gap=block.get('gap',3),
             row_frac=block.get('row_frac',0.02), only=block.get('only'))
    boxes = block.get('boxes') or [block['box']]
    lines = []
    for bx in boxes:
        lines += find_lines(img, tuple(bx), **d)
    # порядок чтения: сверху вниз, а внутри одной строки — слева направо.
    # Верхние края фрагментов одной строки различаются на пару пикселей
    # (выносные элементы), поэтому y огрубляем.
    band = block.get('band', 14)
    if block.get('order') == 'columns':
        # подписи стоят лесенкой над столбцами: читаем по колонкам —
        # слева направо, внутри колонки сверху вниз
        cb = block.get('col_band', 145)
        lines.sort(key=lambda l:(l[0]//cb, l[1]))
    else:
        lines.sort(key=lambda l:(l[1]//band, l[0]))
    if 'skip' in block:
        lines = [l for i,l in enumerate(lines) if i not in block['skip']]
    if 'pick' in block:
        lines = [lines[i] for i in block['pick']]
    texts = block['texts']
    if len(lines) != len(texts):
        raise SystemExit(f"  !! блок {block.get('box') or block['boxes']}: найдено строк {len(lines)}, "
                         f"в спеке {len(texts)}\n     {[ (l[0],l[1],l[2]-l[0]) for l in lines]}")
    out=[]
    for l,t in zip(lines,texts):
        m = line_metrics(img, l, dark=d['dark'], k=d['k'], thr=d['thr'], only=d['only'])
        if m is None: continue
        m['text']=t; m['line']=l
        out.append(m)
    return out

def _font_and_sizes(img, b, ms):
    """Начертание и кегль каждой строки блока."""
    if 'font' not in b:
        gs=[guess_weight(img, m['line'], m['text'], dark=b.get('dark',False))[0] for m in ms]
        font='Onest-'+max(set(gs), key=gs.count)
    else:
        font = b['font']
    sk = b.get('skew', 0.0)
    if b.get('fit') == 'height':
        per=[size_by_height(m['cap']) for m in ms]
    elif 'size_ref' in b:
        r = ms[b['size_ref']]
        per=[size_for(r['text'],font,r['w'],sk,r['cap'])]*len(ms)
    elif isinstance(b.get('size'), (int,float)):
        per=[float(b['size'])]*len(ms)
    elif b.get('size','group')=='group':
        sizes=[size_for(m['text'],font,m['w'],sk,m['cap']) for m in ms]
        if b.get('robust'):
            sz = float(np.median(sizes))
        else:
            # опора на самую длинную строку: у неё наименьшая
            # относительная погрешность измерения ширины
            sz = sizes[int(np.argmax([m['w'] for m in ms]))]
        per=[sz]*len(ms)
    else:
        per=[size_for(m['text'],font,m['w'],sk,m['cap']) for m in ms]
    return font, per

def build(spec, src_dir='page_images_150dpi', out_dir='vector_pages',
          bg_override=None, scale=1, verbose=True, bleed_mm=0.0, dpi=150,
          denoise=True):
    """Собрать одну страницу.

    bleed_mm > 0 — страница делается размером обрез+вылет: подложка
    расширяется отражением края, содержимое сдвигается внутрь, TrimBox
    ставится по обрезу. Так вылет получается без масштабирования вёрстки.
    dpi=300 — подложка увеличивается вдвое с обработкой (scripts/upscale).
    """
    register_fonts()
    pg = spec['page']
    img = fit(cv2.imread(bg_override)) if bg_override else load_page(pg, src_dir)

    register_fonts()
    blocks=[]
    for b in spec.get('blocks',[]):
        ms = measure(img, b)
        blocks.append((b, ms, *_font_and_sizes(img, b, ms)))
    dots=[]
    for db in spec.get('dots',[]):
        dots += dot_circles(img, db)
    # плоские заливки (столбцы диаграммы, плашки) — перерисовываем вектором
    shapes=[]
    for sh in spec.get('shapes',[]):
        found = shape_rects(img, tuple(sh['box']), tuple(sh['color']),
                            min_area=sh.get('min_area',800),
                            min_w=sh.get('min_w',6), min_h=sh.get('min_h',6),
                            fill=sh.get('fill',0.75))
        if sh.get('expect') and len(found) != sh['expect']:
            raise SystemExit(f"  !! заливки {sh['box']}: найдено {len(found)}, "
                             f"ожидалось {sh['expect']}")
        for (x,y,w,h,rgb) in found:
            shapes.append((x,y,w,h,rgb,sh.get('grow',1),sh.get('radius',0)))

    # ---- стереть старый впечатанный текст ----
    light_boxes, dark_boxes = [], []
    for b,ms,_font,_per in blocks:
        pad = b.get('pad',10)
        for m in ms:
            x0,y0,x1,y1 = m['line']
            (dark_boxes if b.get('dark') else light_boxes).append(
                (max(0,x0-pad), max(0,y0-pad), min(BASE_W,x1+pad), min(BASE_H,y1+pad)))
    for eb in spec.get('erase',[]):    light_boxes.append(tuple(eb))
    for eb in spec.get('erase_dark',[]): dark_boxes.append(tuple(eb))
    for (cx,cy,r) in dots:
        rr=int(r+4); light_boxes.append((int(cx-rr),int(cy-rr),int(cx+rr),int(cy+rr)))

    # Всё, что перекроет новый набор, стирать не нужно: inpaint по большой
    # площади мылит фото (на детализированном кадре это видно как пятна).
    # Оставляем под стирание только кайму старых глифов, торчащую из-под
    # новых, — новый текст стоит на тех же координатах и того же кегля.
    keep = _new_ink_mask(blocks, dots, shapes, spec.get('dot_rgb',(252,144,43)))
    # зоны блоков, где старый набор стирается целиком
    full = np.zeros((BASE_H, BASE_W), np.uint8)
    for b, ms, _f, _p in blocks:
        if not b.get('full_erase'): continue
        pad = b.get('pad',10)
        for m in ms:
            x0,y0,x1,y1 = m['line']
            full[max(0,y0-pad):min(BASE_H,y1+pad), max(0,x0-pad):min(BASE_W,x1+pad)] = 255
    os.makedirs('build/masks', exist_ok=True)
    cv2.imwrite(f'build/masks/pg{pg:02d}.png', keep)   # нужна для проверки артефактов
    clean = img
    if light_boxes:
        clean = erase(clean, light_boxes, dark=False, keep=keep, full=full,
                      **spec.get('erase_opt',{}))
    if dark_boxes:
        clean = erase(clean, dark_boxes, dark=True, keep=keep, full=full,
                      **spec.get('erase_opt_dark',{}))

    # ---- подложка: разрешение и вылет ----
    factor = max(1, int(round(dpi/150.0)))
    if factor > 1:
        clean = upscale(clean, factor, denoise=denoise)
    bleed_pt = bleed_mm*MM
    if bleed_mm > 0:
        clean = add_bleed(clean, int(round(bleed_mm/25.4*dpi)))

    os.makedirs('build/backgrounds', exist_ok=True)
    bgp = f'build/backgrounds/pg{pg:02d}_clean.jpg'
    cv2.imwrite(bgp, clean, [int(cv2.IMWRITE_JPEG_QUALITY), 88])

    # ---- вектор поверх ----
    os.makedirs(out_dir, exist_ok=True)
    outp = f'{out_dir}/page{pg:02d}.pdf'
    MW, MH = PW+2*bleed_pt, PH+2*bleed_pt
    c = canvas.Canvas(outp, pagesize=(MW,MH))
    c.drawImage(bgp, 0, 0, width=MW, height=MH)
    if bleed_mm > 0:
        # дальше рисуем в координатах обрезного формата
        c.translate(bleed_pt, bleed_pt)

    for (x,y,w,h,rgb,grow,radius) in shapes:
        # рисуем поверх старой заливки с запасом в grow px, чтобы накрыть
        # сглаженную кромку растра
        c.setFillColorRGB(*[v/255 for v in rgb])
        X0, Y0 = X(x-grow), Y(y+h+grow)
        W, H = (w+2*grow)*SX, (h+2*grow)*SY
        if radius:
            c.roundRect(X0, Y0, W, H, radius*SX, stroke=0, fill=1)
        else:
            c.rect(X0, Y0, W, H, stroke=0, fill=1)

    for (cx,cy,r) in dots:
        col = spec.get('dot_rgb',(252,144,43))
        c.setFillColorRGB(*[v/255 for v in col])
        c.circle(X(cx), Y(cy), max(r-R_BIAS,1)*SX, stroke=0, fill=1)

    for b,ms,font,per in blocks:
        sk = b.get('skew', 0.0)
        rgb = b.get('rgb')
        if rgb is None:
            arr=np.array([m['rgb'] for m in ms]); rgb=tuple(arr.mean(0).astype(int))
        c.setFillColorRGB(*[v/255 for v in rgb])
        for m,s in zip(ms,per):
            c.setFont(font, s)
            lsb, _ = bearings(font, m['text'])
            x0 = X(m['x']) - lsb*s
            # кегль в блоке общий, но ширина строки должна совпасть с
            # оригиналом до пикселя: иначе старый набор выглядывает
            # из-под нового призраком. Остаток добираем горизонтальным
            # масштабом — на 1-2 % он неразличим.
            k = _hscale(m, font, s, sk)
            c.saveState()
            if sk:
                t = np.tan(np.radians(sk))
                c.transform(1, 0, t, 1, -t*Y(m['base']), 0)
            if abs(k-1.0) > 1e-4:
                c.transform(k, 0, 0, 1, x0*(1-k), 0)
            c.drawString(x0, Y(m['base']), m['text'])
            c.restoreState()
        if verbose:
            print(f"  стр{pg:02d} блок {b.get('box') or b['boxes']} шрифт={font} кегль={per[0]:.1f}pt "
                  f"строк={len(ms)} цвет={tuple(int(v) for v in rgb)}")
    c.showPage(); c.save()
    if bleed_mm > 0:
        _set_trimbox(outp, bleed_pt)
    return outp

def _hscale(m, font, size, skew=0.0):
    """Во сколько раз сжать/растянуть строку, чтобы ширина совпала с оригиналом."""
    lsb, rsb = bearings(font, m['text'])
    ink_pt = (pdfmetrics.stringWidth(m['text'], font, 1.0) - lsb - rsb)*size
    if ink_pt <= 0: return 1.0
    target_px = m['w'] - W_BIAS - (np.tan(np.radians(skew))*m['cap'] if skew else 0.0)
    k = (max(target_px,1)*SX)/ink_pt
    return float(np.clip(k, 0.90, 1.10))

def _new_ink_mask(blocks, dots, shapes, dot_rgb=(252,144,43)):
    """Куда ляжет новый вектор — в пикселях подложки.

    Маску снимаем с фактического рендера того же ReportLab-набора, а не
    перерисовываем шрифтом через PIL: у двух движков чуть разный трекинг,
    и к концу строки маска расходится с реальными глифами на несколько
    пикселей. Тогда из-под нового текста торчит полоска старого, её
    стирает inpaint — и вокруг букв появляются грязные пятна.
    """
    import io, pymupdf
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    c.setFillColorRGB(0,0,0); c.rect(0,0,PW,PH, stroke=0, fill=1)
    c.setFillColorRGB(1,1,1)
    for (x,y,w,h,rgb,grow,radius) in shapes:
        c.rect(X(x-grow), Y(y+h+grow), (w+2*grow)*SX, (h+2*grow)*SY, stroke=0, fill=1)
    for (cx,cy,r) in dots:
        c.circle(X(cx), Y(cy), max(r-R_BIAS,1)*SX, stroke=0, fill=1)
    for (b, ms, font, per) in blocks:
        # блок с full_erase в маску не попадает: старый набор под ним
        # стирается целиком, а не только по кайме. Нужно там, где строка
        # тусклая и её ширину с растра точно не снять
        if b.get('full_erase'): continue
        sk = b.get('skew', 0.0)
        for m, size in zip(ms, per):
            c.setFont(font, size)
            x0 = X(m['x']) - bearings(font, m['text'])[0]*size
            k = _hscale(m, font, size, sk)
            c.saveState()
            if sk:
                t = np.tan(np.radians(sk))
                c.transform(1, 0, t, 1, -t*Y(m['base']), 0)
            if abs(k-1.0) > 1e-4:
                c.transform(k, 0, 0, 1, x0*(1-k), 0)
            c.drawString(x0, Y(m['base']), m['text'])
            c.restoreState()
    c.showPage(); c.save()
    doc = pymupdf.open(stream=buf.getvalue(), filetype='pdf')
    px = doc[0].get_pixmap(matrix=pymupdf.Matrix(BASE_W/PW, BASE_H/PH), colorspace='gray')
    a = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width)
    if a.shape != (BASE_H, BASE_W):
        a = cv2.resize(a, (BASE_W, BASE_H), interpolation=cv2.INTER_AREA)
    # порог низкий: сглаженный край глифа тоже кроет фон
    return (a > 32).astype(np.uint8)*255

def _font_path(name):
    w = name.split('-',1)[1]
    p = f'{ROOT}/fonts/static/Onest-{w}.ttf'
    return p if os.path.exists(p) else f'{ROOT}/fonts/Onest-{w}.ttf'

def _set_trimbox(path, bleed_pt):
    """TrimBox = обрезной формат, BleedBox/CropBox = вся страница с вылетом."""
    import pikepdf
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        for page in pdf.pages:
            mb = [float(v) for v in page.MediaBox]
            page.BleedBox = pikepdf.Array(mb)
            page.CropBox  = pikepdf.Array(mb)
            page.TrimBox  = pikepdf.Array([mb[0]+bleed_pt, mb[1]+bleed_pt,
                                           mb[2]-bleed_pt, mb[3]-bleed_pt])
        pdf.save(path)
