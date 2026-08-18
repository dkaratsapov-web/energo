# -*- coding: utf-8 -*-
"""
Боковые отступы глифов Onest.

ReportLab ставит строку по origin первого глифа, а с растра снимается
край чернил. Разница — левый боковой отступ (lsb) — даёт сдвиг набора
вправо на несколько пикселей: старый текст выглядывает из-под нового
слева и читается как призрак.

По той же причине нельзя подбирать кегль по stringWidth: это ширина
пера (advance), а измеряется ширина чернил. Разница — lsb первого глифа
плюс rsb последнего.
"""
import os
from functools import lru_cache
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@lru_cache(maxsize=8)
def _font(name):
    w = name.split('-',1)[1]
    p = f'{ROOT}/fonts/static/Onest-{w}.ttf'
    if not os.path.exists(p): p = f'{ROOT}/fonts/Onest-{w}.ttf'
    f = TTFont(p)
    return f, f.getBestCmap(), f['hmtx'].metrics, f['glyf'], f['head'].unitsPerEm

def _glyph(name, ch):
    f, cmap, hmtx, glyf, upem = _font(name)
    gn = cmap.get(ord(ch))
    if gn is None: return None
    adv, lsb = hmtx[gn]
    g = glyf[gn]
    if g.numberOfContours == 0:      # пробел и прочие пустые
        return adv, lsb, 0, upem
    g.recalcBounds(glyf)
    return adv, lsb, (g.xMax - g.xMin), upem

def bearings(name, text):
    """(lsb первого глифа, rsb последнего) в долях кегля."""
    if not text: return 0.0, 0.0
    a = _glyph(name, text[0]); b = _glyph(name, text[-1])
    if a is None or b is None: return 0.0, 0.0
    upem = a[3]
    lsb = a[1]/upem
    adv, lsb_b, w_b, _ = b
    rsb = (adv - lsb_b - w_b)/upem
    return lsb, rsb
