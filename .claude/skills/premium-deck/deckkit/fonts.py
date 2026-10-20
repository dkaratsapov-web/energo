# -*- coding: utf-8 -*-
"""Шрифты колоды: регистрация в ReportLab, метрики, перенос строк.

Строки переносятся ЗДЕСЬ, один раз, и уже готовыми уходят и в PDF, и в PPTX.
Так PowerPoint не переверстает абзац по-своему: в PPTX каждая строка стоит
отдельной строкой, перенос в текстовом поле выключен.
"""
import os, re
from fontTools.ttLib import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as RLFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(os.path.dirname(HERE), 'fonts')

# ключ -> файл. Ключи используют токены концепций.
FILES = {
    'onest':       'Onest-Regular.ttf',
    'onest-med':   'Onest-Medium.ttf',
    'onest-semi':  'Onest-SemiBold.ttf',
    'onest-bold':  'Onest-Bold.ttf',
    'onest-black': 'Onest-ExtraBold.ttf',
    'serif':       'PTSerif-Regular.ttf',
    'serif-bold':  'PTSerif-Bold.ttf',
    'serif-it':    'PTSerif-Italic.ttf',
    'wide':        'Unbounded-Regular.ttf',
    'wide-bold':   'Unbounded-Bold.ttf',
}

_info = {}


def register():
    for key, fn in FILES.items():
        if key in _info:
            continue
        path = os.path.join(FONT_DIR, fn)
        pdfmetrics.registerFont(RLFont('dk-' + key, path))
        t = TTFont(path)
        n = t['name']
        sel = t['OS/2'].fsSelection
        hh = t['hhea']
        upm = t['head'].unitsPerEm
        _info[key] = dict(
            path=path, rl='dk-' + key,
            family=n.getDebugName(1),          # имя семейства для PowerPoint
            bold=bool(sel & 0b100000), italic=bool(sel & 0b1),
            ascent=hh.ascent / upm, descent=-hh.descent / upm,
            cap=getattr(t['OS/2'], 'sCapHeight', 0.7 * upm) / upm,
            cmap=set(t.getBestCmap()))
    return _info


def info(key):
    register()
    return _info[key]


def width(s, key, size, track=0.0):
    """Ширина строки в pt; track — трекинг в долях кегля (-0.03 = -30 ед.)."""
    w = pdfmetrics.stringWidth(s, info(key)['rl'], size)
    return w + track * size * max(len(s) - 1, 0)


# Висячие предлоги и союзы привязываем к следующему слову — признак набора,
# который делал человек. Неразрывный пробел переживает и PDF, и PPTX.
_SHORT = r'(?<![\wА-Яа-яЁё])(в|во|и|с|со|к|ко|о|об|у|а|но|на|по|за|из|от|до|не|ни|для|при|без|что|как|или|под|над|про|же|ли)\s+'


def typograph(s):
    s = re.sub(r'\s+', ' ', s.strip())
    s = s.replace(' — ', '\u00a0— ').replace(' – ', '\u00a0– ')
    s = re.sub(_SHORT, lambda m: m.group(1) + '\u00a0', s, flags=re.I)
    s = re.sub(r'(\d)\s(?=\d{3}\b)', '\\1\u00a0', s)     # 71 560
    s = re.sub(r'(\d)\s(?=(%|км|м|м²|млн|млрд|руб|₽|ед|кВ|МВт)\b)', '\\1\u00a0', s)
    s = re.sub(r'(\d)\s(?=[A-Za-zА-Яа-яЁё])', '\\1\u00a0', s)        # 144 монтажника
    s = s.replace(' -- ', '\u00a0— ').replace(' - ', '\u00a0— ')
    return s


def wrap(text, key, size, w, track=0.0):
    """Жадный перенос по словам. Явный \\n — принудительная строка."""
    out = []
    for para in str(text).split('\n'):
        words = typograph(para).split(' ')
        line = ''
        for wd in words:
            cand = wd if not line else line + ' ' + wd
            if width(cand, key, size, track) <= w or not line:
                line = cand
            else:
                out.append(line)
                line = wd
        out.append(line)
    return out


def balance(text, key, size, w, track=0.0):
    """Без «сирот»: если последняя строка — одно короткое слово, сужаем
    колонку, пока слово не получит соседа при том же числе строк."""
    lines = wrap(text, key, size, w, track)
    if len(lines) < 2 or ' ' in lines[-1] or len(lines[-1]) > 9:
        return lines
    for k in (0.94, 0.88, 0.82, 0.76, 0.70):
        alt = wrap(text, key, size, w * k, track)
        if len(alt) == len(lines) and (' ' in alt[-1] or len(alt[-1]) > 9):
            return alt
    return lines


def fit(text, key, w, h, size_max, size_min, leading=1.0, track=0.0, step=1.0,
        max_lines=None):
    """Крупнейший кегль, при котором текст влезает в w×h (pt).
    Возвращает (строки, кегль, влезло ли)."""
    size = size_max
    while True:
        lines = balance(text, key, size, w, track)
        widest = max(width(l, key, size, track) for l in lines)
        hgt = size * leading * (len(lines) - 1) + size * info(key)['ascent']
        ok = widest <= w + 0.5 and hgt <= h and (max_lines is None or len(lines) <= max_lines)
        if ok or size - step < size_min:
            return lines, size, ok
        size -= step


def missing_glyphs(text, key):
    cm = info(key)['cmap']
    return sorted({ch for ch in text if ch not in '\n' and ord(ch) not in cm})
