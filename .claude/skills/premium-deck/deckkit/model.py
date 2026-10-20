# -*- coding: utf-8 -*-
"""Модель слайда: положенные элементы в мм, y сверху вниз.

Один и тот же список элементов отдают и PDF, и PPTX — поэтому они совпадают.
Прозрачности в модели нет вовсе: всё, что «полупрозрачно» на вид, считается
заранее как непрозрачный смешанный цвет или впекается в пиксели снимка.
Иначе PDF/X-1a при печати растрирует страницу целиком.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from . import fonts

PT = 25.4 / 72          # мм в пункте


@dataclass
class Rect:
    x: float; y: float; w: float; h: float
    fill: tuple
    role: str = 'shape'


@dataclass
class Line:
    x0: float; y0: float; x1: float; y1: float
    color: tuple
    width: float = 0.75              # pt
    role: str = 'motif'


@dataclass
class Poly:
    pts: List[Tuple[float, float]]
    stroke: Optional[tuple] = None
    fill: Optional[tuple] = None
    width: float = 0.75
    closed: bool = False
    role: str = 'motif'


@dataclass
class Dot:
    cx: float; cy: float; r: float
    fill: tuple
    role: str = 'motif'


@dataclass
class Image:
    path: str
    x: float; y: float; w: float; h: float
    focus: Tuple[float, float] = (0.5, 0.5)     # куда смотрит кадрирование
    shade: Optional[dict] = None                # затемнение, впекается в пиксели
    role: str = 'image'


@dataclass
class Text:
    x: float; y: float; w: float                # y — верх строки (по ascent)
    lines: List[str]
    font: str
    size: float
    color: tuple
    leading: float = 1.2                        # доля кегля
    track: float = 0.0                          # доля кегля
    align: str = 'l'
    role: str = 'body'
    box_h: Optional[float] = None               # отведённая высота (для контроля)
    fit_ok: bool = True

    @property
    def ascent(self):
        return fonts.info(self.font)['ascent'] * self.size * PT

    @property
    def h(self):
        """Высота от верха первой строки до низа выносных последней, мм."""
        f = fonts.info(self.font)
        n = len(self.lines)
        return ((n - 1) * self.size * self.leading + (f['ascent'] + f['descent']) * self.size) * PT

    def baseline(self, i):
        return self.y + self.ascent + i * self.size * self.leading * PT

    def line_w(self, i):
        return fonts.width(self.lines[i], self.font, self.size, self.track) * PT

    def bbox(self):
        ws = [self.line_w(i) for i in range(len(self.lines))] or [0]
        wmax = max(ws)
        x0 = {'l': self.x, 'r': self.x + self.w - wmax, 'c': self.x + (self.w - wmax) / 2}[self.align]
        return x0, self.y, x0 + wmax, self.y + self.h


@dataclass
class Slide:
    n: int
    layout: str
    ground: object
    items: list = field(default_factory=list)
    notes: str = ''
    warnings: list = field(default_factory=list)

    def add(self, *els):
        self.items.extend(els)
        return els[-1] if els else None
