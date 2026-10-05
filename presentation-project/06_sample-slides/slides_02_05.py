# -*- coding: utf-8 -*-
"""
Эталонные полосы 2–5. Весь текст и все цифры взяты из текущего каталога.

Композиции намеренно разные — каталог не должен читаться как лента
одинаковых карточек:
  02  цифры          — плакат, одна мысль крупно
  03  направления    — нумерованный перечень в две колонки, асимметрия
  04  динамика роста — инфографика, диаграмма держит полосу
  05  миссия и цели  — editorial, текст на светлой полосе
"""
import os, sys
sys.path.insert(0, 'scripts')
from render import Slide, preview
from graphics import gradient, field_lines, grid
from ds import *

OUT = 'presentation-project/06_sample-slides'

# ─────────────────────────────────────────────────────────── 02 · ЦИФРЫ ──
def slide02():
    p = Slide(f'{OUT}/slide02_numbers.pdf'); c = p.c; B = BLEED
    gradient(c, -B, -B, PAGE_W+2*B, PAGE_H+2*B, (30, 34, 78), (52, 40, 82))
    field_lines(c, -B, 150*mm, PAGE_W+2*B, PAGE_H-120*mm, rows=34, seed=4,
                alpha=(0.05, 0.20))
    x, _  = col_x(0, 12)
    right = PAGE_W - MARGIN_OUTER
    p.header('01', 'Компания в цифрах')

    y = p.title(['ЧТО ПОСТРОЕНО'], PAGE_H - 52*mm)

    # главная цифра держит полосу одна
    y -= 42*mm
    p.text('413 278', x, y, T.FONT_BLACK, 96, C.ORANGE, track=-26)
    p.text('опор ЛЭП установлено при строительстве', x, y - 17*mm,
           T.FONT_BOOK, T.H3, C.MUTED_D)

    p.rule(x, y - 30*mm, right - x, C.LINE_D, 0.5)

    # остальные — сеткой 2×2, чтобы не спорили с главной
    rows = [('25 800', ['км проводов протянуто', 'на воздушных ЛЭП']),
            ('1 224',  ['подстанций, ТП и РП', 'построено']),
            ('502 000',['объектов подключено', 'к электрическим сетям']),
            ('339',    ['км прокола', 'горизонтальным бурением'])]
    y0 = y - 48*mm
    for i, (num, cap) in enumerate(rows):
        cx, _ = col_x(6*(i % 2), 5)
        p.stat(cx, y0 - (i//2)*38*mm, num, cap, size=40)

    p.rule(x, MARGIN_BOTTOM + 20*mm, right - x, C.LINE_D, 0.5)
    p.text('16 298 м² промышленных и гражданских площадей введено в эксплуатацию',
           x, MARGIN_BOTTOM + 10*mm, T.FONT_BOOK, T.BODY, C.MUTED_D)
    return p.save()

# ────────────────────────────────────────────────────── 03 · НАПРАВЛЕНИЯ ──
def slide03():
    p = Slide(f'{OUT}/slide03_services.pdf'); c = p.c; B = BLEED
    c.setFillColorRGB(*rgb(C.PAPER)); c.rect(-B, -B, PAGE_W+2*B, PAGE_H+2*B, stroke=0, fill=1)
    grid(c, -B, -B, PAGE_W+2*B, PAGE_H+2*B, 14*mm, C.LINE_L, 0.25, 0.5)
    # плотная плашка сверху — раздел открывается цветом
    c.setFillColorRGB(*rgb(C.PURPLE_DEEP))
    c.rect(-B, PAGE_H - 92*mm, PAGE_W + 2*B, 92*mm + B, stroke=0, fill=1)

    x, _  = col_x(0, 12)
    right = PAGE_W - MARGIN_OUTER
    p.header('02', 'Направления работ')
    p.title(['ПРОЕКТИРОВАНИЕ', 'И СТРОИТЕЛЬСТВО'], PAGE_H - 52*mm)

    items = ['Внутренние электрические сети', 'Кабельные линии',
             'Воздушные линии электропередач',
             'Распределительные пункты, трансформаторные подстанции',
             'Архитектурное освещение', 'Сервисное обслуживание электроустановок',
             'Электротехническая лаборатория', 'Наружное электроосвещение',
             'Пусконаладочные работы', 'ГНБ/ГНП']
    y0 = PAGE_H - 112*mm
    step = 17*mm
    for i, t in enumerate(items):
        col = i // 5
        cx, cw = col_x(col*6, 5)        # колонка уже: между ними воздух
        yy = y0 - (i % 5)*step
        p.numbered(i+1, cx, yy, t, dark=False, size=11, num_w=11*mm,
                   width=cw, lead=1.35)
        p.rule(cx, yy - 7*mm, cw, C.LINE_L, 0.5)
    return p.save()

# ─────────────────────────────────────────────────────── 04 · ДИНАМИКА ──
def slide04():
    p = Slide(f'{OUT}/slide04_growth.pdf'); c = p.c; B = BLEED
    gradient(c, -B, -B, PAGE_W+2*B, PAGE_H+2*B, (28, 32, 74), (46, 38, 80))
    x, _  = col_x(0, 12)
    right = PAGE_W - MARGIN_OUTER
    p.header('03', 'Динамика роста')
    p.title(['ПОРТФЕЛЬ ВЫРОС', 'ВТРОЕ ЗА ШЕСТЬ ЛЕТ'], PAGE_H - 52*mm)

    p.lines(['Объём работ в контрактах, млрд рублей. Рост не прерывался',
             'ни в один год рассматриваемого периода.'],
            x, PAGE_H - 86*mm, T.FONT_BOOK, T.H3, C.MUTED_D, T.LEAD_H2)

    data = [('2019', 1500, '>1 500'), ('2020', 1700, '>1 700'),
            ('2021', 1850, '>1 850'), ('2022', 2000, '>2 000'),
            ('2023', 3500, '>3 500'), ('2024', 4200, '>4 200'),
            ('2025', 4800, '>4 800')]
    p.bars(x, MARGIN_BOTTOM + 52*mm, right - x, 88*mm, data)

    p.rule(x, MARGIN_BOTTOM + 30*mm, right - x, C.LINE_D, 0.5)
    for i, (num, cap) in enumerate([('×3,2', ['рост портфеля', 'с 2019 года']),
                                    ('317',  ['сотрудников', 'в штате']),
                                    ('141',  ['единица', 'собственной техники'])]):
        cx, _ = col_x(i*4, 4)
        p.stat(cx, MARGIN_BOTTOM + 18*mm, num, cap, size=28)
    return p.save()

# ─────────────────────────────────────────────────── 05 · МИССИЯ И ЦЕЛИ ──
def slide05():
    p = Slide(f'{OUT}/slide05_mission.pdf'); c = p.c; B = BLEED
    c.setFillColorRGB(*rgb(C.PAPER)); c.rect(-B, -B, PAGE_W+2*B, PAGE_H+2*B, stroke=0, fill=1)
    # вертикальная плашка на внешнем поле — ритм разворота
    c.setFillColorRGB(*rgb(C.PURPLE_DEEP))
    c.rect(PAGE_W - 34*mm, -B, 34*mm + B, PAGE_H + 2*B, stroke=0, fill=1)

    x, _ = col_x(0, 9)
    p.header('04', 'Миссия и цели', dark=False)
    p.title(['МИССИЯ', 'КОМПАНИИ'], PAGE_H - 52*mm, dark=False)

    y = PAGE_H - 92*mm
    _, cw = col_x(0, 8)
    for para in [
        ['Укрепление российского электроэнергетического комплекса',
         'путём участия в проектах, позволяющих сформировать максимально',
         'благоприятные условия для постоянного развития экономики РФ.'],
        ['Качественное выполнение своих задач по подготовке проектов,',
         'их реализации, поставке оборудования, его установке и наладке,',
         'а также вводу в эксплуатацию объектов энергетики, удовлетворяющим',
         'нормам экологической и промышленной безопасности.']]:
        c.setFillColorRGB(*rgb(C.ORANGE)); c.circle(x - 6*mm, y + 1.5*mm, 1.6*mm, stroke=0, fill=1)
        p.lines(para, x, y, T.FONT_BOOK, 11.5, C.INK, 1.52)
        y -= (len(para)*11.5*1.52 + 12*mm)

    y -= 6*mm
    p.rule(x, y, cw, C.LINE_L, 0.6)
    y -= 14*mm
    p.title(['ЦЕЛИ КОМПАНИИ'], y, size=22, dark=False)
    y -= 14*mm
    p.lines(['Стать надёжным партнёром для нашего заказчика и ответственным',
             'работодателем для каждого сотрудника, а также создать сеть филиалов',
             'для присутствия в каждом регионе нашей необъятной страны с целью',
             'участия в работах по строительству, реконструкции, модернизации',
             'и техническому перевооружению энергетической системы',
             'Российской Федерации.'],
            x, y, T.FONT_BOOK, 11.5, C.INK, 1.52)
    return p.save()

if __name__ == '__main__':
    for fn in (slide02, slide03, slide04, slide05):
        path = fn()
        preview(path, path.replace('.pdf', '.jpg'), 1000)
        print(os.path.basename(path))
