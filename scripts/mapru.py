# -*- coding: utf-8 -*-
"""
Карта России для разворота «География проектов» — в вектор.

В утверждённом каталоге карта лежит в той же сведённой полосе 150 dpi, что
и всё остальное: на печати это мыльный силуэт с рваной кромкой. Здесь она
снимается с полосы как маска и обводится potrace, то есть превращается в
кривые Безье и печатается резко при любом увеличении.

Карта на полосе разложена на два тона: сама страна чуть светлее фона, а
регионы присутствия — ещё светлее. Это разделение и используется: страна
рисуется приглушённо, семнадцать регионов — фирменным оранжевым.

Обводка идёт долго, поэтому результат кладётся в кэш и переснимается только
при удалении файла кэша.
"""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2, numpy as np
from photos import page_raster
from potrace_vec import trace_layer

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = f'{ROOT}/presentation-project/05_assets/map_ru.pkl'
UP    = 4

def _masks():
    """Две маски с полосы 28: страна целиком и регионы присутствия.

    Фон полосы — вертикальный градиент, поэтому порог берётся не от яркости,
    а от превышения над фоном СТРОКИ: за фон строки принят её 12-й
    перцентиль. Высокочастотная модель фона (размытие) здесь не годится —
    страна занимает почти всю ширину полосы, и размытие уезжает вместе с ней,
    выедая середину материка.

    Замеренные уровни превышения: тело страны 9–12, регионы присутствия
    20–22, белый набор заголовка от 39. Заголовок отсекается верхней
    границей, иначе буквы ушли бы в карту.
    """
    g = cv2.cvtColor(page_raster(28), cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Фон полосы — чисто вертикальный градиент: в любой строке он постоянен
    # по x (проверено, разброс 0). Значит фоном строки можно взять её
    # минимум — карта нигде не закрывает строку целиком. Перцентиль здесь не
    # годится: в самых широких строках карта занимает 96 % ширины, и даже
    # третий перцентиль попадает в материк, отчего карта рвётся поперёк.
    bg = cv2.medianBlur(g.min(1).reshape(1, -1).astype(np.uint8), 41)
    d  = g - bg.ravel().astype(np.float32)[:, None]

    # Замеренные уровни превышения над фоном: тело страны 11–13, регионы
    # присутствия 16–23, белый набор заголовка от 39. Вокруг заголовка идёт
    # горизонтальный ореол сжатия амплитудой до 11 — порог страны взят выше
    # него, иначе ореол обводится полосами во всю ширину полосы.
    country = ((d > 10.5) & (d < 35)).astype(np.uint8)

    # Ореол заголовка поднимает тон материка на строках заголовка с 12 до 18
    # и попадает в диапазон регионов — на карте появляются оранжевые полосы
    # во всю ширину. Уровень материка выравнивается построчно: из каждой
    # строки вычитается её отклонение от общего уровня тела страны.
    lvl = np.full(d.shape[0], np.nan, np.float32)
    for y in range(d.shape[0]):
        v = d[y][country[y] > 0]
        if v.size > 80:
            lvl[y] = np.median(v)
    base = np.nanmedian(lvl)
    lvl = np.nan_to_num(lvl, nan=base)
    lvl = cv2.blur(lvl.reshape(1, -1), (9, 1)).ravel()
    dn = d - (lvl - base)[:, None]

    regions = ((dn > 15.5) & (dn < 35)).astype(np.uint8)
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    k9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    # закрытие вытянуто по вертикали: оценка фона по минимуму строки
    # изредка промахивается на одну строку, и материк рвётся тонкой щелью
    country = cv2.morphologyEx(cv2.morphologyEx(country, cv2.MORPH_OPEN, k3),
                               cv2.MORPH_CLOSE,
                               cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 19)))
    regions = cv2.morphologyEx(cv2.morphologyEx(regions, cv2.MORPH_CLOSE, k9),
                               cv2.MORPH_OPEN, k3)

    # Буквы заголовка вырезаются, дыры заращиваются ПО МАСКЕ, а не по
    # полутону: вокруг буквы маска сплошная, и дыра заполняется однозначно.
    # Расширение 17 px, а не вплотную по букве: сглаженная кромка набора
    # падает до уровня регионов и иначе остаётся на карте оранжевой крошкой.
    text = cv2.dilate((d > 30).astype(np.uint8),
                      cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    out = []
    for m in (country, regions):
        m = m.copy(); m[text > 0] = 0
        out.append((cv2.inpaint(m*255, text, 12, cv2.INPAINT_TELEA) > 127
                    ).astype(np.uint8))
    country, regions = out
    country = np.maximum(country, regions)
    return country, regions

def layers(force=False):
    """[(пути страны, w, h), (пути регионов, w, h)] — из кэша или заново."""
    if os.path.exists(CACHE) and not force:
        return pickle.load(open(CACHE, 'rb'))
    out = []
    for m, turd in zip(_masks(), (28, 10)):
        big = cv2.resize(m, None, fx=UP, fy=UP, interpolation=cv2.INTER_NEAREST)
        big = cv2.medianBlur(big*255, 5)//255       # сгладить ступеньку апскейла
        out.append((trace_layer(big, turdsize=turd, alphamax=1.0,
                                opttolerance=0.12), big.shape[1], big.shape[0]))
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    pickle.dump(out, open(CACHE, 'wb'))
    return out

def ink_box():
    """Габарит самой карты в координатах трассировки (y вверх от низа).

    Полоса каталога вертикальная, а страна на ней занимает узкую полосу по
    середине. Без этого габарита карта вписывалась бы в прямоугольник вместе
    с пустыми полями полосы и выходила бы втрое мельче нужного.
    """
    country, _ = _masks()
    ys, xs = np.nonzero(country)
    h = country.shape[0]
    return (xs.min()*UP, (h - ys.max())*UP, xs.max()*UP, (h - ys.min())*UP)

def draw(c, x, y, w, h, color_country, color_regions, a_country=1.0, fit='both'):
    """Вписать карту в прямоугольник по её собственному габариту.

    fit='width' масштабирует только по ширине и позволяет карте выходить за
    прямоугольник сверху и снизу — так она уходит под обрез, а не повисает
    в поле. Восточный край карты в исходнике срезан краем полосы; если не
    выпустить его за обрез, срез читается как брак вёрстки.
    """
    from potrace_vec import draw as pdraw
    (pc, sw, sh), (pr, _, _) = layers()
    bx0, by0, bx1, by1 = ink_box()
    k = w/(bx1 - bx0) if fit == 'width' else min(w/(bx1 - bx0), h/(by1 - by0))
    ox = x + (w - (bx1 - bx0)*k)/2 - bx0*k
    oy = y + (h - (by1 - by0)*k)/2 - by0*k
    pdraw(c, [(1.0, pc, sw, sh)], ox, oy, sw*k, sh*k, color_country,
          a0=a_country, a1=a_country)
    pdraw(c, [(1.0, pr, sw, sh)], ox, oy, sw*k, sh*k, color_regions, a0=1.0, a1=1.0)

if __name__ == '__main__':
    (pc, w, h), (pr, _, _) = layers(force='--force' in sys.argv)
    print(f'страна: {len(pc)} контуров, регионы: {len(pr)} контуров, растр {w}×{h}')
