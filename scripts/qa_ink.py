# -*- coding: utf-8 -*-
"""
Красочные проверки печатного файла — два пункта, которых не было.

1. Суммарное покрытие (TAC). Сумма C+M+Y+K в точке на мелованной бумаге при
   офсете обычно ограничена 300–330 %. Выше краска не успевает лечь и
   высохнуть: отмарывает на соседний лист, пачкает оборот. Тёмные грунты
   после перевода в CMYK набирают покрытие легко — фиолетовая ночь из RGB
   превращается в четыре плотные краски.

2. Чёрный мелкого набора. Текст мельче ~12 pt и тонкие линейки должны идти
   ОДНОЙ краской K: составной чёрный из четырёх красок на мелком кегле при
   малейшем несовмещении печатных форм даёт цветную бахрому по буквам.

Проверяется ГОТОВЫЙ файл PDF/X — то, что уйдёт в типографию, — а не вёрстка.
"""
import os, sys
import numpy as np, pymupdf

def tac(pdf, dpi=40, limit=300.0):
    """Наибольшее суммарное покрытие по каждой полосе, в процентах."""
    d = pymupdf.open(pdf)
    out = []
    for i, p in enumerate(d, 1):
        px = p.get_pixmap(matrix=pymupdf.Matrix(dpi/72, dpi/72),
                          colorspace=pymupdf.csCMYK, clip=p.trimbox)
        a = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width, px.n)[:, :, :4]
        s = a.astype(np.float32).sum(2)/255*100
        p999 = float(np.percentile(s, 99.9))        # без единичных точек
        frac = float((s > limit).mean()*100)
        out.append((i, p999, frac))
    return out

def small_text_k(pdf, max_pt=12.0):
    """Каким цветом заливки идёт мелкий набор — по операторам потока.

    Отрисовка в CMYK для этой проверки не годится: MuPDF рендерит через
    RGB и переразделяет цвет по профилю, так что чистый K100 на снимке
    выглядит составным. Поэтому проверка читает сам поток содержимого, как
    это делает препресс: какой оператор цвета заливки действует в момент
    вывода каждой строки и каков её фактический кегль (Tf × масштаб Tm).

    Возвращает счётчик: K100, составной тёмный, цветной, светлый.
    """
    import pikepdf
    pdf_ = pikepdf.open(pdf)
    stat = {'k100': 0, 'rich': 0, 'color': 0, 'light': 0}
    rich_pages = set()
    for pno, pg in enumerate(pdf_.pages, 1):
        stack = []
        fill = ('g', (0.0,))
        tf, tm = 1.0, (1, 0, 0, 1, 0, 0)
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
                size = abs(tf)*(abs(tm[0]*tm[3] - tm[1]*tm[2]))**0.5
                if size > max_pt:
                    continue
                kind, v = fill
                if kind == 'k':
                    c, m, y, k = v
                    if k > 0.95 and max(c, m, y) < 0.02:
                        stat['k100'] += 1
                    elif k > 0.5 or (c + m + y) > 2.0:
                        stat['rich'] += 1; rich_pages.add(pno)
                    elif max(c, m, y, k) < 0.15:
                        stat['light'] += 1
                    else:
                        stat['color'] += 1
                else:
                    lum = sum(v)/len(v)
                    if lum < 0.3:
                        stat['rich'] += 1; rich_pages.add(pno)
                    elif lum > 0.85:
                        stat['light'] += 1
                    else:
                        stat['color'] += 1
    return stat, sorted(rich_pages)

if __name__ == '__main__':
    f = sys.argv[1]
    lim = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
    rows = tac(f, limit=lim)
    worst = max(rows, key=lambda r: r[1])
    over = [r for r in rows if r[1] > lim]
    print(f'Суммарное покрытие (предел {lim:.0f} %):')
    print(f'  наибольшее — {worst[1]:.0f} % на стр. {worst[0]}')
    for i, v, frac in over:
        print(f'  [!!] стр. {i}: {v:.0f} %, выше предела {frac:.1f} % площади')
    if not over:
        print('  [ок] все полосы в пределе')
    stat, pages = small_text_k(f)
    print(f'\nМелкий набор до 12 pt — цвет заливки по операторам потока:')
    print(f'  чистый K100:       {stat["k100"]}')
    print(f'  составной тёмный:  {stat["rich"]}' +
          (f'  [!!] стр. {pages}' if stat['rich'] else '  [ок]'))
    print(f'  цветной набор:     {stat["color"]}  (фирменный цвет, не чёрный)')
    print(f'  светлый / белый:   {stat["light"]}')
