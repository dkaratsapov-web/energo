# -*- coding: utf-8 -*-
"""Проверка готового файла по требованиям типографии."""
import sys, subprocess, pikepdf, pymupdf

def check(path):
    ok = True
    def line(good, text):
        nonlocal ok
        ok = ok and good
        print(('  [ок]   ' if good else '  [!!]   ') + text)

    d = pymupdf.open(path)
    print(f'\nФАЙЛ: {path}\nстраниц: {len(d)}')
    line(len(d)==32, f'32 страницы (сейчас {len(d)})')

    mm = lambda v: v/72*25.4
    bad_trim = bad_bleed = 0
    for p in d:
        t, m = p.trimbox, p.mediabox
        if abs(mm(t.width)-210)>0.3 or abs(mm(t.height)-297)>0.3: bad_trim += 1
        if min(mm(t.x0-m.x0), mm(m.x1-t.x1), mm(t.y0-m.y0), mm(m.y1-t.y1)) < 3.9: bad_bleed += 1
    p0 = d[0]
    line(bad_trim==0, f'TrimBox = 210x297 мм на всех страницах '
                      f'(сейчас {mm(p0.trimbox.width):.2f}x{mm(p0.trimbox.height):.2f}, '
                      f'нарушений {bad_trim})')
    line(bad_bleed==0, f'вылет >= 4 мм со всех сторон (нарушений {bad_bleed})')

    # шрифты
    fonts=set(); notemb=set()
    for p in d:
        for f in p.get_fonts(full=True):
            fonts.add(f[3])
            if not f[3].count('+'): notemb.add(f[3])
    line(len(notemb)==0, f'шрифты встроены: {sorted(fonts)}'
                         + (f' | НЕ встроены: {sorted(notemb)}' if notemb else ''))

    # текст остался вектором
    chars = sum(len(p.get_text().strip()) for p in d)
    line(chars > 3000, f'текст живой, не растр: {chars} знаков')

    # цвет изображений
    with pikepdf.open(path) as pdf:
        cs={}
        for page in pdf.pages:
            for _,im in getattr(page,'images',{}).items():
                c=str(im.get('/ColorSpace','?'))
                cs[c]=cs.get(c,0)+1
        rgb=sum(v for k,v in cs.items() if 'RGB' in k)
        line(rgb==0, f'изображения в CMYK: {cs}')
        root=pdf.Root
        oi = '/OutputIntents' in root
        line(oi, 'OutputIntent присутствует' +
                 (f" ({str(root.OutputIntents[0].get('/OutputConditionIdentifier'))})" if oi else ''))
        line('/Metadata' in root, 'XMP-метаданные PDF/X есть')

    # dpi подложки
    worst=None
    for p in d:
        for im in p.get_images(full=True):
            r=p.get_image_rects(im[0])
            if not r: continue
            dpi = im[2]/(r[0].width/72)
            if worst is None or dpi<worst[0]: worst=(dpi,p.number+1)
    line(worst and worst[0]>=295, f'разрешение растра >= 300 dpi '
                                  f'(минимум {worst[0]:.0f} dpi на стр. {worst[1]})')
    print(f'\nИТОГ: {"файл соответствует проверенным требованиям" if ok else "есть замечания (см. [!!])"}\n')
    return ok

if __name__=='__main__':
    check(sys.argv[1] if len(sys.argv)>1 else 'build/ЭнергоГрупп_2025_печать_PDFX-1a.pdf')
