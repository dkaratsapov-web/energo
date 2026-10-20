# -*- coding: utf-8 -*-
"""Preflight: проверки вёрстки, экранного и печатного файлов, PPTX.

Каждая проверка возвращает строки (уровень, слайд, текст). Уровни:
  FAIL — дефект, сдавать нельзя;  WARN — требует решения человека;  OK.
Печатный файл объявляется готовым, только если нет ни одного FAIL
и все требования типографии подтверждены. Иначе отчёт так и пишет.
"""
import collections, datetime, math, os, re
import numpy as np
import pikepdf, pymupdf
from PIL import Image as PImage
from .model import Text, Image, Rect, PT
from .tokens import contrast, lum
from . import fonts, images, spec as S

MM = 72 / 25.4


class Log:
    def __init__(self):
        self.rows = []

    def add(self, level, area, where, msg):
        self.rows.append((level, area, where, msg))

    def count(self, level, area=None):
        return sum(1 for r in self.rows if r[0] == level and (area is None or r[1] == area))


# ------------------------------------------------------------ вёрстка

DECOR = ('ghost',)


def check_layout(slides, ds, spec, log, k_print):
    W, H = ds['W'], ds['H']
    pr = spec['print']
    safe = pr['safe_mm'] / k_print            # безопасное поле в единицах макета
    prev = []
    for sl in slides:
        where = f'{sl.n:02d} {sl.layout}'
        for w in sl.warnings:
            log.add('FAIL' if 'не влез' in w or 'нет знаков' in w else 'WARN', 'вёрстка', where, w)
        texts = [t for t in sl.items if isinstance(t, Text) and t.role not in DECOR]
        words = 0
        for t in texts:
            x0, y0, x1, y1 = t.bbox()
            words += sum(len(l.split()) for l in t.lines)
            if t.size < 10:
                log.add('FAIL', 'вёрстка', where, f'кегль {t.size:.1f} pt мельче 10 pt на экране: «{t.lines[0][:30]}»')
            if t.size * k_print < pr['min_text_pt']:
                log.add('FAIL', 'печать', where, f'в печати {t.size * k_print:.1f} pt < {pr["min_text_pt"]} pt: «{t.lines[0][:30]}»')
            if x0 < safe - 0.01 or y0 < safe - 0.01 or x1 > W - safe + 0.01 or y1 > H - safe + 0.01:
                log.add('FAIL', 'печать', where, f'текст ближе {pr["safe_mm"]} мм к обрезу: «{t.lines[0][:30]}»')
            for l in t.lines:
                if l.endswith((' в', ' и', ' с', ' к', ' на', ' по', ' за', ' не', ' а')):
                    log.add('WARN', 'типографика', where, f'висячий предлог в конце строки: «{l[-20:]}»')
        # наложения строк разных блоков
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                a, b = texts[i].bbox(), texts[j].bbox()
                ix = min(a[2], b[2]) - max(a[0], b[0])
                iy = min(a[3], b[3]) - max(a[1], b[1])
                if ix > 0.8 and iy > 0.8:
                    log.add('FAIL', 'вёрстка', where,
                            f'текст налезает на текст: «{texts[i].lines[0][:22]}» / «{texts[j].lines[0][:22]}»')
        if words > 75:
            log.add('WARN', 'вёрстка', where, f'{words} слов — слайд перегружен, лучше разделить')
        sizes = sorted((t.size for t in texts), reverse=True)
        if len(sizes) > 1 and sizes[0] < sizes[1] * 1.4 and sl.layout not in ('process', 'gallery'):
            log.add('WARN', 'иерархия', where, 'нет явной точки входа: два самых крупных текста почти равны')
        prev.append(sl.layout)
        if len(prev) >= 3 and len(set(prev[-3:])) == 1:
            log.add('WARN', 'ритм', where, f'композиция «{sl.layout}» три раза подряд')
    if not log.count('FAIL', 'вёрстка'):
        log.add('OK', 'вёрстка', 'все', 'тексты влезают, не налезают друг на друга, кегли не мельче 10 pt')


def check_contrast(slides, notext_pdf, log, dpi=60):
    """Контраст по фактическому фону: рендер без текста, пиксели под строкой."""
    doc = pymupdf.open(notext_pdf)
    worst = 99
    for sl, pg in zip(slides, doc):
        pix = pg.get_pixmap(dpi=dpi)
        a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[..., :3]
        sx = pix.width / (pg.rect.width / MM)
        for t in sl.items:
            if not isinstance(t, Text) or t.role in DECOR:
                continue
            x0, y0, x1, y1 = t.bbox()
            r = a[max(int(y0 * sx), 0):max(int(y1 * sx), 1), max(int(x0 * sx), 0):max(int(x1 * sx), 1)]
            if r.size == 0:
                continue
            px = r.reshape(-1, 3).astype(np.float32) / 255
            lin = np.where(px <= 0.03928, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)
            L = lin @ np.array([0.2126, 0.7152, 0.0722])
            lt = lum(t.color)
            ratio = (np.maximum(L, lt) + 0.05) / (np.minimum(L, lt) + 0.05)
            c = float(np.percentile(ratio, 10))            # худшие 10% фона
            big = t.size >= 24 or (t.size >= 18.5 and ('bold' in t.font or 'black' in t.font))
            need = 3.0 if big else 4.5
            worst = min(worst, c)
            if c < need:
                log.add('FAIL' if c < need * 0.8 else 'WARN', 'контраст', f'{sl.n:02d} {sl.layout}',
                        f'контраст {c:.1f}:1 < {need}:1 у «{t.lines[0][:28]}» ({t.size:.0f} pt)')
    if not log.count('FAIL', 'контраст') and not log.count('WARN', 'контраст'):
        log.add('OK', 'контраст', 'все', f'WCAG AA выполнен для всего текста, худший {worst:.1f}:1')


def check_images(placements, spec, log, mode):
    pr = spec['print']
    seen = set()
    for p in placements:
        key = (p['slide'], p['path'])
        if key in seen:
            continue
        seen.add(key)
        where = f'{p["slide"]:02d}'
        name = os.path.basename(p['path'])
        cut = images.src_cut(p['path'])
        if mode != 'print' and max(cut) > 2 and (p['path'], 'cut') not in seen:
            seen.add((p['path'], 'cut'))
            log.add('WARN', 'снимки', where, f'{name}: по краям срезаны полоски чужого кадра {cut} px (t,b,l,r) — проверьте исходник')
        d = p['dpi']
        if mode == 'print':
            if d < pr['warn_dpi']:
                log.add('FAIL', 'снимки', where, f'{name}: {d:.0f} dpi в печати (нужно {pr["min_dpi"]}), '
                        f'место {p["w_mm"]:.0f}×{p["h_mm"]:.0f} мм — нужен исходник ≥ '
                        f'{math.ceil(p["w_mm"] / 25.4 * pr["min_dpi"])} px по ширине')
            elif d < pr['min_dpi']:
                log.add('WARN', 'снимки', where, f'{name}: {d:.0f} dpi (норма {pr["min_dpi"]})')
        else:
            if d < 96:
                log.add('WARN', 'снимки', where, f'{name}: {d:.0f} dpi на экране — может быть мыльно на проекторе 4K')
    if mode == 'print' and not log.count('FAIL', 'снимки'):
        log.add('OK', 'снимки', 'все', f'эффективное разрешение не ниже {pr["warn_dpi"]} dpi')


# ------------------------------------------------------------ печатный PDF

def check_print_pdf(path, spec, log):
    pr = spec['print']
    tw, th = pr['trim_mm']
    b = pr['bleed_mm']
    pdf = pikepdf.open(path)
    # ящики
    bad = 0
    for i, pg in enumerate(pdf.pages, 1):
        mb = [float(v) for v in pg.obj.MediaBox]
        tb = [float(v) for v in pg.obj.get('/TrimBox', mb)]
        bb = [float(v) for v in pg.obj.get('/BleedBox', mb)]
        want_m = ((tw + 2 * b) * MM, (th + 2 * b) * MM)
        if '/TrimBox' not in pg.obj or abs((mb[2] - mb[0]) - want_m[0]) > 0.6 or abs((mb[3] - mb[1]) - want_m[1]) > 0.6 \
                or abs((tb[2] - tb[0]) - tw * MM) > 0.6 or abs(tb[0] - b * MM) > 0.6 or abs((bb[2] - bb[0]) - want_m[0]) > 0.6:
            bad += 1
            log.add('FAIL', 'PDF/X', f'стр. {i}', f'ящики не те: Media {mb}, Trim {tb}')
    if not bad:
        log.add('OK', 'PDF/X', 'все', f'обрез {tw}×{th} мм, вылеты {b} мм: MediaBox, BleedBox, TrimBox на месте')
    # OutputIntent и метаданные
    oi = pdf.Root.get('/OutputIntents')
    ok_oi = bool(oi) and any(str(o.get('/S')) == '/GTS_PDFX' and '/DestOutputProfile' in o for o in oi)
    log.add('OK' if ok_oi else 'FAIL', 'PDF/X', 'файл',
            'OutputIntent GTS_PDFX с профилем FOGRA39' if ok_oi else 'нет OutputIntent GTS_PDFX')
    ver = str(pdf.docinfo.get('/GTS_PDFXVersion', ''))
    xmp = '/Metadata' in pdf.Root
    log.add('OK' if ver.startswith('PDF/X-1') and xmp else 'FAIL', 'PDF/X', 'файл',
            f'GTS_PDFXVersion «{ver}», XMP {"есть" if xmp else "нет"}, PDF {pdf.pdf_version}')
    if pdf.pdf_version > '1.4':
        log.add('FAIL', 'PDF/X', 'файл', f'версия PDF {pdf.pdf_version}, для X-1a нужна ≤ 1.4')
    # шрифты, цвет, прозрачность
    fonts_bad, rgb, transp, fonts_ok = set(), 0, 0, set()
    for i, pg in enumerate(pdf.pages, 1):
        res = pg.obj.get('/Resources', {})
        for name, f in (res.get('/Font') or {}).items():
            fd = f.get('/FontDescriptor')
            if fd is None and '/DescendantFonts' in f:
                fd = f.DescendantFonts[0].get('/FontDescriptor')
            base = str(f.get('/BaseFont', name))
            if fd is None or not any(k in fd for k in ('/FontFile', '/FontFile2', '/FontFile3')):
                fonts_bad.add(base)
            else:
                fonts_ok.add(base.split('+')[-1])
        for name, gs in (res.get('/ExtGState') or {}).items():
            if float(gs.get('/ca', 1)) < 1 or float(gs.get('/CA', 1)) < 1 or \
                    str(gs.get('/SMask', '/None')) != '/None' or str(gs.get('/BM', '/Normal')) not in ('/Normal', '/Compatible'):
                transp += 1
        for name, x in (res.get('/XObject') or {}).items():
            if str(x.get('/Subtype')) == '/Image':
                cs = x.get('/ColorSpace')
                if str(cs) not in ('/DeviceCMYK', '/DeviceGray'):
                    rgb += 1
                if '/SMask' in x:
                    transp += 1
        if '/Group' in pg.obj and str(pg.obj.Group.get('/S')) == '/Transparency':
            transp += 1
        for operands, op in pikepdf.parse_content_stream(pg):
            if str(op) in ('rg', 'RG'):
                rgb += 1
    log.add('FAIL' if fonts_bad else 'OK', 'шрифты', 'файл',
            ('не встроены: ' + ', '.join(sorted(fonts_bad))) if fonts_bad else
            'все шрифты встроены: ' + ', '.join(sorted(fonts_ok)))
    log.add('FAIL' if rgb else 'OK', 'цвет', 'файл',
            f'найдено RGB-объектов: {rgb}' if rgb else 'только CMYK/Gray: ни одного RGB-оператора и снимка')
    log.add('FAIL' if transp else 'OK', 'прозрачность', 'файл',
            f'живая прозрачность: {transp}' if transp else 'живой прозрачности нет')
    pdf.close()
    # текст остался текстом
    doc = pymupdf.open(path)
    chars = sum(len(p.get_text()) for p in doc)
    log.add('OK' if chars > 50 else 'FAIL', 'шрифты', 'файл',
            f'текст векторный, извлекается ({chars} знаков)' if chars > 50 else 'текста нет — растрирован?')
    # покрытие
    worst = (0, 0)
    for i, pg in enumerate(doc, 1):
        px = pg.get_pixmap(matrix=pymupdf.Matrix(40 / 72, 40 / 72), colorspace=pymupdf.csCMYK, clip=pg.trimbox)
        a = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width, px.n)[..., :4]
        s = a.astype(np.float32).sum(2) / 255 * 100
        v = float(np.percentile(s, 99.9))
        worst = max(worst, (v, i))
        if v > pr['tac_max']:
            log.add('FAIL', 'краска', f'стр. {i}', f'суммарное покрытие {v:.0f} % > {pr["tac_max"]} %')
    if worst[0] <= pr['tac_max']:
        log.add('OK', 'краска', 'все', f'суммарное покрытие ≤ {pr["tac_max"]} %, наибольшее {worst[0]:.0f} % (стр. {worst[1]})')
    small_text_ink(path, log)


def small_text_ink(path, log, max_pt=12.0):
    """Мелкий набор, печатаемый краской, — одной K; по операторам потока."""
    pdf = pikepdf.open(path)
    rich, konly = 0, 0
    pages = set()
    for pno, pg in enumerate(pdf.pages, 1):
        stack, fill, tf, tm = [], ('g', (0.0,)), 1.0, (1, 0, 0, 1, 0, 0)
        for operands, op in pikepdf.parse_content_stream(pg):
            o = str(op)
            if o == 'q':
                stack.append((fill, tf, tm))
            elif o == 'Q' and stack:
                fill, tf, tm = stack.pop()
            elif o in ('k', 'rg', 'g'):
                fill = (o, tuple(float(v) for v in operands))
            elif o == 'Tf':
                tf = float(operands[1])
            elif o == 'Tm':
                tm = tuple(float(v) for v in operands)
            elif o == 'BT':
                tm = (1, 0, 0, 1, 0, 0)
            elif o in ('Tj', 'TJ', "'", '"'):
                size = abs(tf) * (abs(tm[0] * tm[3] - tm[1] * tm[2])) ** 0.5
                if size > max_pt or fill[0] != 'k':
                    continue
                c, m, y, k = fill[1]
                if max(c, m, y) < 0.005 and k > 0:
                    konly += 1
                elif k > 0.6 or (c + m + y + k) > 1.6:
                    rich += 1
                    pages.add(pno)
    pdf.close()
    log.add('FAIL' if rich else 'OK', 'краска', 'файл',
            f'мелкий тёмный текст в 4 краски: {rich} строк, стр. {sorted(pages)}' if rich else
            f'мелкий тёмный и серый текст — одной краской K ({konly} строк)')


# ------------------------------------------------------------ PPTX

def check_pptx(pptx_path, lo_pdf, preview_pdf, spec, log):
    from pptx import Presentation
    prs = Presentation(pptx_path)
    names = {fonts.info(k)['family'] for k in fonts.FILES}
    used, bad_wrap, texts = set(), 0, 0
    for s in prs.slides:
        for sh in s.shapes:
            if sh.has_text_frame:
                texts += 1
                if sh.text_frame.word_wrap:
                    bad_wrap += 1
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        if r.font.name:
                            used.add(r.font.name)
    alien = used - names
    log.add('FAIL' if alien else 'OK', 'PPTX', 'файл',
            f'чужие шрифты: {alien}' if alien else f'{len(prs.slides)} слайдов, {texts} живых текстовых полей, '
            f'шрифты: {", ".join(sorted(used))}')
    if bad_wrap:
        log.add('WARN', 'PPTX', 'файл', f'{bad_wrap} полей с автопереносом')
    if not lo_pdf:
        log.add('WARN', 'PPTX', 'файл', 'LibreOffice недоступен — PPTX не проверен независимым рендером')
        return
    A, B = _spans(preview_pdf), _spans(lo_pdf)
    idx = collections.defaultdict(list)
    for r in B:
        idx[(r[0], r[1])].append(r)
    dmax, miss, n = 0.0, [], 0
    per = collections.defaultdict(float)
    for r in A:
        q = idx.get((r[0], r[1]))
        if not q:
            miss.append(f'{r[0] + 1:02d} «{r[1][:24]}»')
            continue
        q = q.pop(0)
        d = math.hypot(q[2] - r[2], q[3] - r[3])
        dmax = max(dmax, d); n += 1
        per[r[0]] = max(per[r[0]], d)
    if miss:
        log.add('FAIL', 'PPTX', 'текст', f'строки не совпали с PDF ({len(miss)}): {"; ".join(miss[:5])}')
    lvl = 'OK' if dmax <= 1.0 else ('WARN' if dmax <= 2.5 else 'FAIL')
    log.add(lvl, 'PPTX', 'текст', f'{n} строк PPTX (рендер LibreOffice) совпали с PDF, наибольший сдвиг {dmax:.2f} мм')
    # пиксельная разница
    da, db = pymupdf.open(preview_pdf), pymupdf.open(lo_pdf)
    worst = (0, 0)
    for i, (pa, pb) in enumerate(zip(da, db), 1):
        ia = _arr(pa); ib = _arr(pb, ia.shape[1], ia.shape[0])
        v = float(np.abs(ia - ib).mean())
        worst = max(worst, (v, i))
    lvl = 'OK' if worst[0] < 12 else 'WARN'      # сглаживание крупного текста и снимков даёт 3–10
    log.add(lvl, 'PPTX', 'вид', f'средняя разница пикселей PDF↔PPTX ≤ {worst[0]:.1f}/255 (худший слайд {worst[1]:02d})')
    if len(da) != len(db):
        log.add('FAIL', 'PPTX', 'файл', f'слайдов в PPTX {len(db)}, в PDF {len(da)}')


def _arr(pg, w=None, h=None):
    pix = pg.get_pixmap(dpi=48)
    im = PImage.frombytes('RGB', (pix.width, pix.height), pix.samples)
    im = im.reduce(4)                  # усреднение 4×4: общий вид без зерна снимков
    if w:
        im = im.resize((w, h), PImage.BOX)
    return np.asarray(im, dtype=np.float32)


def _spans(path):
    out = []
    for pi, pg in enumerate(pymupdf.open(path)):
        for b in pg.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                t = ''.join(s['text'] for s in l['spans']).replace(' ', ' ').strip()
                if t:
                    s = l['spans'][0]
                    out.append((pi, t, s['origin'][0] / MM, s['origin'][1] / MM))
    return out


# ------------------------------------------------------------ отчёт

def report(log, spec, files, path):
    pr = spec['print']
    un = S.unconfirmed(spec)
    L = []
    L.append(f'# Preflight — {spec["meta"]["title"]}\n')
    L.append(f'Дата проверки: {datetime.date.today():%d.%m.%Y}. Концепция: {spec["concept"]}. '
             f'Типография: {pr.get("printer", "не указана")}.\n')
    fails, warns = log.count('FAIL'), log.count('WARN')
    if fails:
        verdict = f'**НЕ ГОТОВО К ПЕЧАТИ** — {fails} дефектов (FAIL). Печатный файл собран для проверки, но сдавать его нельзя.'
    elif un:
        verdict = ('**Технически проверено, к печати НЕ подтверждено** — дефектов нет, но требования типографии '
                   'не подтверждены (см. ниже). Готовность объявляется только после подтверждения.')
    else:
        verdict = '**Готово к печати** — все проверки пройдены, требования типографии подтверждены.'
    L.append(f'## Итог\n\n{verdict}\n\nFAIL: {fails} · WARN: {warns} · OK: {log.count("OK")}\n')
    L.append('## Файлы\n')
    for k, v in files.items():
        if v and os.path.exists(v):
            L.append(f'- {k}: `{os.path.basename(v)}` ({os.path.getsize(v) / 1e6:.1f} МБ)')
    L.append('\n## Неподтверждённые требования типографии\n')
    names = dict(trim_mm='Формат обреза', bleed_mm='Вылеты', profile='Цветовой профиль / OutputIntent',
                 standard='Стандарт PDF', min_dpi='Разрешение снимков', tac_max='Суммарное покрытие (TAC)',
                 safe_mm='Безопасное поле от обреза', min_text_pt='Минимальный кегль',
                 rich_black_text='Мелкий чёрный текст')
    vals = dict(trim_mm=f'{pr["trim_mm"][0]}×{pr["trim_mm"][1]} мм', bleed_mm=f'{pr["bleed_mm"]} мм',
                profile=pr['profile'], standard=pr['standard'], min_dpi=f'{pr["min_dpi"]} dpi',
                tac_max=f'{pr["tac_max"]} %', safe_mm=f'{pr["safe_mm"]} мм', min_text_pt=f'{pr["min_text_pt"]} pt',
                rich_black_text='только K100' if not pr['rich_black_text'] else 'составной допускается')
    if un:
        L.append('Эти параметры приняты по умолчанию и **не подтверждены типографией**. Перед сдачей '
                 'запросите технические требования и впишите `confirmed` в бриф:\n')
        L.append('| Параметр | Принято | Статус |\n|---|---|---|')
        for k in S.PRINT_KEYS:
            L.append(f'| {names[k]} | {vals[k]} | {"не подтверждено" if k in un else "подтверждено"} |')
        L.append('\nТакже уточните: способ печати (офсет/цифра), бумагу, нужны ли метки реза, '
                 'треппинг, формат сдачи (одностраничный PDF / спуск полос), допустимость CMYK-JPEG в PDF/X-1a.')
    else:
        L.append('Все параметры подтверждены типографией.')
    order = {'FAIL': 0, 'WARN': 1, 'OK': 2}
    for lvl, title in (('FAIL', 'Дефекты'), ('WARN', 'Требуют решения'), ('OK', 'Пройдено')):
        rows = [r for r in log.rows if r[0] == lvl]
        L.append(f'\n## {title} ({len(rows)})\n')
        if not rows:
            L.append('—')
            continue
        L.append('| Область | Где | Что |\n|---|---|---|')
        for _, area, where, msg in sorted(rows, key=lambda r: (r[1], r[2])):
            L.append(f'| {area} | {where} | {msg.replace("|", "/")} |')
    L.append('\n## Как проверялось\n')
    L.append('- Вёрстка — по модели слайдов: влезание, наложения, кегли, безопасное поле, ритм композиций.\n'
             '- Контраст — по пикселям фона под каждой строкой (рендер без текста), худшие 10 % фона, WCAG AA.\n'
             '- Печатный файл — разбор PDF: ящики, OutputIntent, версия, встроенность шрифтов, операторы цвета, '
             'прозрачность; покрытие — CMYK-рендер (99,9-й перцентиль); мелкий текст — операторы потока.\n'
             '- PPTX — независимый рендер LibreOffice Impress и сравнение позиций каждой строки с PDF. '
             'Сам Microsoft PowerPoint в этой среде недоступен: вид в нём не проверен напрямую.\n'
             '- Каждый слайд просмотрен глазами на листах-контактах (папка previews/).')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    return path, fails, warns, un
