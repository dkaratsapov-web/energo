# -*- coding: utf-8 -*-
"""
Сборка каталога из полос разворотов в один файл для типографии.

Разворот существует тремя файлами: две полосы с вылетом и совмещённый
разворот. В типографию идут ПОЛОСЫ: спуск делает типография, и подавать ей
развороты нельзя — она сама расставит их по печатному листу.

Порядок страниц задан нумерацией файлов, а не порядком сборки: полоса 09
лежит в spread_08_09_R.pdf, и собирать её по имени разворота — верный способ
однажды перепутать местами.
"""
import os, sys, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pikepdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = f'{ROOT}/presentation-project/06_sample-slides'
OUT  = f'{ROOT}/build/v3'

def pages():
    """{номер полосы: файл} по всем собранным разворотам и одиночным полосам."""
    m = {1: f'{SRC}/slide01_cover.pdf', 32: f'{SRC}/page32_back.pdf'}
    for f in glob.glob(f'{SRC}/spread_*_[LR].pdf'):
        a, b, side = re.search(r'spread_(\d+)_(\d+)_([LR])\.pdf$', f).groups()
        m[int(a) if side == 'L' else int(b)] = f
    return m

def assemble(out=None):
    m = pages()
    miss = [n for n in range(1, 33) if n not in m]
    if miss:
        raise SystemExit(f'нет полос: {miss}')
    os.makedirs(OUT, exist_ok=True)
    out = out or f'{OUT}/ЭнергоГрупп_2025_вёрстка.pdf'
    pdf = pikepdf.Pdf.new()
    for n in range(1, 33):
        with pikepdf.open(m[n]) as p:
            pdf.pages.extend(p.pages)
    pdf.save(out)
    return out

if __name__ == '__main__':
    m = pages()
    print('собрано полос:', len(m))
    print(assemble())
