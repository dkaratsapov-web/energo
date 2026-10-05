# -*- coding: utf-8 -*-
"""
Контроль качества РАЗВОРОТА — то, чего проверка отдельной полосы не видит.

Проверка полосы (qa_slide.py) ловит наложения, мелкий кегль и вылет за
наборную полосу. На развороте к этому добавляются ошибки, которые на
одиночной полосе выглядят безупречно:

  · набор заехал в мёртвую зону сгиба — в сшитом каталоге он уйдёт в корешок;
  · поля не зеркальные: обе полосы набраны от одного края, и разворот
    визуально «валится» в одну сторону;
  · мера набора у соседних полос разная — разворот рассыпается;
  · заголовки соседних полос не стоят на общей базовой линии;
  · файл полосы не склеивается с развернутым файлом (рассинхрон вёрстки).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from ds import (PAGE_W, PAGE_H, MARGIN_OUTER, MARGIN_INNER, MARGIN_TOP,
                MARGIN_BOTTOM, mm)

PT = lambda v: v*72/25.4
MM = lambda v: v/72*25.4

def _spans(page):
    """Строки с координатами в системе «от левого-нижнего угла обреза»."""
    t = page.trimbox
    out = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                x0, y0, x1, y1 = s['bbox']           # y вниз от верха страницы
                out.append(dict(t=s['text'], size=s['size'],
                                x0=x0 - t.x0, x1=x1 - t.x0,
                                yb=t.y1 - y1, yt=t.y1 - y0))
    return out

def check(path, left_folio, min_pt=6.0, edge_mm=8.0, fold_keep_mm=None):
    """path — файл РАЗВОРОТА (420×297 + вылет)."""
    d = pymupdf.open(path); p = d[0]
    assert abs(p.trimbox.width - PT(420)) < 1, 'это не разворот'
    sp = _spans(p)
    iss = []
    fold = PT(PAGE_W/mm)
    inner_l, inner_r = PT(PAGE_W/mm - MARGIN_INNER/mm), PT(PAGE_W/mm + MARGIN_INNER/mm)
    outer_l, outer_r = PT(MARGIN_OUTER/mm), PT(420 - MARGIN_OUTER/mm)
    top, bot = PT(PAGE_H/mm - MARGIN_TOP/mm), PT(MARGIN_BOTTOM/mm)

    # мёртвая зона сгиба совпадает с двумя корешковыми полями
    dead = PT(fold_keep_mm if fold_keep_mm is not None else MARGIN_INNER/mm)
    for s in sp:
        lab = repr(s['t'][:30])
        if s['size'] < min_pt:
            iss.append(f"кегль {s['size']:.1f} pt: {lab}")
        # мёртвая зона сгиба
        if s['x1'] > fold - dead + 0.5 and s['x0'] < fold + dead - 0.5:
            iss.append(f"в мёртвой зоне сгиба: {lab}")
        # зеркальные поля: набор не выходит ни за внешние, ни за корешковые
        if s['x0'] < outer_l - 1:
            iss.append(f"за внешнее поле слева ({MM(outer_l - s['x0']):.1f} мм): {lab}")
        if s['x1'] > outer_r + 1:
            iss.append(f"за внешнее поле справа ({MM(s['x1'] - outer_r):.1f} мм): {lab}")
        if s['x1'] <= fold and s['x1'] > inner_l + 1:
            iss.append(f"за корешковое поле левой полосы ({MM(s['x1']-inner_l):.1f} мм): {lab}")
        if s['x0'] >= fold and s['x0'] < inner_r - 1:
            iss.append(f"за корешковое поле правой полосы ({MM(inner_r-s['x0']):.1f} мм): {lab}")
        # верх и низ: колонцифра стоит ниже наборной полосы — она исключение
        if s['yt'] > top + 1 and s['size'] > 8.5:
            iss.append(f"выше верхнего поля: {lab}")

    # Общая базовая линия заголовков соседних полос. Смотрим только верх
    # полосы и только крупный кегль: ниже стоят цифры и диаграммы, которым
    # выравниваться друг с другом не нужно.
    def biggest(lo, hi):
        z = [s for s in sp if lo <= (s['x0'] + s['x1'])/2 < hi
             and s['size'] >= 20 and s['yb'] > PT(PAGE_H/mm)*0.62]
        return max(z, key=lambda s: s['size']) if z else None
    a, b = biggest(0, fold), biggest(fold, PT(420))
    if a and b and abs(a['size'] - b['size']) < 3 and abs(a['yb'] - b['yb']) > 1.5:
        iss.append(f"заголовки полос на разных базовых линиях: "
                   f"{MM(abs(a['yb']-b['yb'])):.1f} мм — {a['t'][:18]!r} / {b['t'][:18]!r}")

    # колонцифры: обе на месте, у внешних краёв
    want = {f'{left_folio:02d}', f'{left_folio+1:02d}'}
    got = {s['t'].strip() for s in sp if s['t'].strip() in want and s['yb'] < bot}
    for n in sorted(want - got):
        iss.append(f"нет колонцифры {n} во внешнем нижнем углу")

    # вёрстка полосы и вёрстка разворота должны совпадать
    for side, off in (('L', 0.0), ('R', PT(PAGE_W/mm))):
        f = path.replace('_spread.pdf', f'_{side}.pdf')
        if not os.path.exists(f):
            iss.append(f"нет файла полосы {side}"); continue
        q = pymupdf.open(f)[0]
        a = sorted((round(s['x0'] - off, 1), round(s['yb'], 1), s['t'])
                   for s in sp if (s['x0'] < PT(PAGE_W/mm)) == (side == 'L'))
        bb = sorted((round(s['x0'], 1), round(s['yb'], 1), s['t']) for s in _spans(q))
        if a != bb:
            iss.append(f"полоса {side} расходится с разворотом: "
                       f"{len(a)} строк против {len(bb)}")
    return iss

if __name__ == '__main__':
    bad = 0
    args = sys.argv[1:]
    for i in range(0, len(args), 2):
        f, folio = args[i], int(args[i+1])
        it = check(f, folio)
        print(f'— {os.path.basename(f)}: ' + ('чисто' if not it else f'{len(it)} замечаний'))
        for x in it[:14]: print('   ·', x)
        bad += len(it)
    print('\nвсего замечаний:', bad)
