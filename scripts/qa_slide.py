# -*- coding: utf-8 -*-
"""
Контроль качества полосы: ищет то, что глаз пропускает на превью.

Проверяет наложения строк, вылет за наборную полосу, близость к обрезу,
мелкий кегль. Любая из этих ошибок на печати неисправима, а на экране
в масштабе 25 % почти не видна.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from reportlab.lib.units import mm

MM = lambda v: v/72*25.4

def check(path, margin_outer=16, margin_inner=22, min_pt=6.0, edge_mm=8.0):
    d = pymupdf.open(path); p = d[0]; t = p.trimbox
    spans = [(s, l) for b in p.get_text('dict')['blocks']
             for l in b.get('lines', []) for s in l['spans']]
    issues = []

    for s, _ in spans:
        if s['size'] < min_pt:
            issues.append(f"кегль {s['size']:.1f} pt < {min_pt}: {s['text'][:34]!r}")
        r = s['bbox']
        d_edge = min(r[0]-t.x0, t.x1-r[2], r[1]-t.y0, t.y1-r[3])
        if MM(d_edge) < edge_mm:
            issues.append(f"{MM(d_edge):.1f} мм до обреза: {s['text'][:34]!r}")
        if MM(r[2] - t.x0) > MM(t.x1 - t.x0) - margin_outer + 1.0:
            issues.append(f"выходит за наборную полосу: {s['text'][:34]!r}")

    # Наложение строк. Прямоугольник строки у ReportLab включает запас на
    # выносные элементы, поэтому соседние строки абзаца всегда чуть заходят
    # друг на друга — это норма. Ошибкой считаем перекрытие больше трети
    # высоты меньшей строки.
    boxes = sorted(((s['bbox'], s['text']) for s, _ in spans), key=lambda b: b[0][1])
    for i, (a, ta) in enumerate(boxes):
        for b, tb in boxes[i+1:]:
            if b[1] >= a[3] - 0.5: break
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            hmin = min(a[3]-a[1], b[3]-b[1])
            if ox > 2 and oy > hmin*0.34:
                issues.append(f"наложение {oy/hmin*100:.0f}%: {ta[:22]!r} / {tb[:22]!r}")
    return issues

if __name__ == '__main__':
    bad = 0
    for f in sys.argv[1:]:
        iss = check(f)
        print(f'— {os.path.basename(f)}: ' + ('чисто' if not iss else f'{len(iss)} замечаний'))
        for i in iss[:8]: print('   ·', i)
        bad += len(iss)
    print('\nвсего замечаний:', bad)
