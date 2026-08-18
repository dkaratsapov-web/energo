# -*- coding: utf-8 -*-
"""
Починка имён в статических начертаниях Onest.

Все пять файлов fonts/Onest-*.ttf несут одно и то же внутреннее имя
(family «Onest», subfamily «Regular», PostScript-имя «Onest-Regular») —
след генерации из вариативного Onest-VF.ttf без правки таблицы name.

Для ReportLab это означает, что регистрация пяти TTFont под разными
псевдонимами даёт один и тот же встроенный шрифт: в PDF попадает
единственный «Onest-Regular», и весь набор печатается светлым
начертанием независимо от того, что указано в вёрстке.

Скрипт переписывает записи name (1,2,4,6) и OS/2, создавая корректно
именованные файлы в fonts/static/.
"""
from fontTools.ttLib import TTFont
import os

WEIGHTS = {'Regular':(400,'Regular'), 'Medium':(500,'Medium'),
           'SemiBold':(600,'SemiBold'), 'Bold':(700,'Bold'),
           'ExtraBold':(800,'ExtraBold')}
SRC, DST = 'fonts', 'fonts/static'

def main():
    os.makedirs(DST, exist_ok=True)
    for w,(usw,sub) in WEIGHTS.items():
        f = TTFont(f'{SRC}/Onest-{w}.ttf')
        family, ps, full = 'Onest', f'Onest-{w}', f'Onest {sub}'
        # RIBBI-совместимость: только Regular/Bold допустимы как subfamily,
        # остальные веса объявляем через typographic-имена (16/17)
        ribbi = 'Bold' if w=='Bold' else 'Regular'
        pref_family = family if w in ('Regular','Bold') else f'{family} {sub}'
        for rec in list(f['name'].names):
            if rec.nameID == 1: rec.string = pref_family.encode(rec.getEncoding())
            elif rec.nameID == 2: rec.string = ribbi.encode(rec.getEncoding())
            elif rec.nameID == 4: rec.string = full.encode(rec.getEncoding())
            elif rec.nameID == 6: rec.string = ps.encode(rec.getEncoding())
            elif rec.nameID == 16: rec.string = family.encode(rec.getEncoding())
            elif rec.nameID == 17: rec.string = sub.encode(rec.getEncoding())
        f['OS/2'].usWeightClass = usw
        # снять бит Bold в fsSelection у всех, кроме Bold
        # бит 5 = Bold, бит 6 = Regular; они взаимоисключающие
        fs = f['OS/2'].fsSelection & ~(0x20 | 0x40)
        f['OS/2'].fsSelection = fs | (0x20 if w=='Bold' else 0x40)
        f['head'].macStyle = 1 if w=='Bold' else 0
        f.save(f'{DST}/Onest-{w}.ttf')
        print(f'  Onest-{w}: psName={ps}, usWeightClass={usw}')

if __name__=='__main__':
    main()
