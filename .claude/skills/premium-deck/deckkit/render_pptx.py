# -*- coding: utf-8 -*-
"""Редактируемый PPTX из той же модели, что и PDF.

Всё — живые объекты PowerPoint: текстовые поля с настоящим текстом,
прямоугольники, линии, кривые, снимки. Строки уже перенесены движком,
перенос в полях выключен, интерлиньяж точный (spcPts), трекинг — spc.
Поэтому PowerPoint показывает ту же вёрстку, что и PDF, а клиент может
править текст.
"""
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.oxml.ns import qn
from .model import Rect, Line, Poly, Dot, Image, Text, PT
from .render_pdf import _clip_seg
from .layouts import clip_runs
from . import fonts, images

EMU_MM = 36000

# При точном интерлиньяже первая базовая линия стоит на (интерлиньяж − 0,2)
# кегля ниже верха поля — независимо от гарнитуры. Измерено на калибровочной
# колоде через LibreOffice Impress (импорт PPTX эмулирует PowerPoint);
# preflight каждый раз сверяет позиции строк PDF↔PPTX заново.
FIRST_BASELINE = -0.2


def E(mm):
    return Emu(int(round(mm * EMU_MM)))


def _rgb(col):
    return RGBColor(*col)


def _no_line(shape):
    shape.line.fill.background()


def _shadowless(shape):
    """Снимаем стиль темы: иначе PowerPoint/LibreOffice добавят тень и
    обводку по умолчанию. Заливку и линию мы задаём явно."""
    el = shape._element
    st = el.find(qn('p:style'))
    if st is not None:
        el.remove(st)
    sp = el.spPr
    if sp.find(qn('a:effectLst')) is None:
        sp.append(sp.makeelement(qn('a:effectLst'), {}))


def _text(slide, el):
    f = fonts.info(el.font)
    n = len(el.lines)
    lead = el.size * el.leading
    wmax = max(el.line_w(i) for i in range(n)) if n else el.w
    w = max(el.w, wmax + 1.0)
    x = el.x if el.align == 'l' else (el.x + el.w - w if el.align == 'r' else el.x + (el.w - w) / 2)
    top = el.baseline(0) - (el.leading + FIRST_BASELINE) * el.size * PT
    h = n * lead * PT + 0.3 * el.size * PT
    tb = slide.shapes.add_textbox(E(x), E(top), E(w), E(h))
    tf = tb.text_frame
    tf.word_wrap = False
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, ln in enumerate(el.lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {'l': PP_ALIGN.LEFT, 'r': PP_ALIGN.RIGHT, 'c': PP_ALIGN.CENTER}[el.align]
        p.line_spacing = Pt(lead)
        p.space_before = Pt(0)
        p.space_after = Pt(0)
        r = p.add_run()
        r.text = ln
        fn = r.font
        fn.name = f['family']
        fn.size = Pt(el.size)
        fn.bold = f['bold']
        fn.italic = f['italic']
        fn.color.rgb = _rgb(el.color)
        rpr = r._r.get_or_add_rPr()
        rpr.set('spc', str(int(round(el.track * el.size * 100))))
        for tag in ('a:ea', 'a:cs'):
            sub = rpr.find(qn(tag))
            if sub is None:
                sub = rpr.makeelement(qn(tag), {})
                rpr.append(sub)
            sub.set('typeface', f['family'])
    tb.name = f'{el.role}: {el.lines[0][:30] if el.lines else ""}'
    return tb


def render(slides, path, W, H, cache='/tmp/deckkit-img', meta=None):
    fonts.register()
    prs = Presentation()
    prs.slide_width, prs.slide_height = E(W), E(H)
    blank = prs.slide_layouts[6]
    meta = meta or {}
    cp = prs.core_properties
    cp.title = meta.get('title', '')
    cp.author = meta.get('author', '')
    cp.subject = meta.get('subject', '')
    box = (0, 0, W, H)
    for sl in slides:
        s = prs.slides.add_slide(blank)
        for el in sl.items:
            if isinstance(el, Rect):
                x0, y0 = max(el.x, 0), max(el.y, 0)
                x1, y1 = min(el.x + el.w, W), min(el.y + el.h, H)
                if x1 <= x0 or y1 <= y0:
                    continue
                sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, E(x0), E(y0), E(x1 - x0), E(y1 - y0))
                sh.fill.solid(); sh.fill.fore_color.rgb = _rgb(el.fill)
                _no_line(sh); _shadowless(sh)
                sh.name = el.role
            elif isinstance(el, Line):
                seg = _clip_seg(el.x0, el.y0, el.x1, el.y1, *box)
                if not seg:
                    continue
                ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(seg[0]), E(seg[1]),
                                            E(seg[2]), E(seg[3]))
                ln.line.color.rgb = _rgb(el.color)
                ln.line.width = Pt(el.width)
                _shadowless(ln)
                ln.name = el.role
            elif isinstance(el, Poly):
                runs = [el.pts] if el.closed else clip_runs(el.pts, 0, 0, W, H)
                for pts in runs:
                    fb = s.shapes.build_freeform(E(pts[0][0]), E(pts[0][1]), scale=1.0)
                    fb.add_line_segments([(E(x), E(y)) for x, y in pts[1:]], close=el.closed)
                    sh = fb.convert_to_shape()
                    if el.fill:
                        sh.fill.solid(); sh.fill.fore_color.rgb = _rgb(el.fill)
                    else:
                        sh.fill.background()
                    if el.stroke:
                        sh.line.color.rgb = _rgb(el.stroke); sh.line.width = Pt(el.width)
                    else:
                        _no_line(sh)
                    _shadowless(sh)
                    sh.name = el.role
            elif isinstance(el, Dot):
                sh = s.shapes.add_shape(MSO_SHAPE.OVAL, E(el.cx - el.r), E(el.cy - el.r),
                                        E(2 * el.r), E(2 * el.r))
                sh.fill.solid(); sh.fill.fore_color.rgb = _rgb(el.fill)
                _no_line(sh); _shadowless(sh)
                sh.name = el.role
            elif isinstance(el, Image):
                f = images.prepare(el.path, el.w, el.h, el.focus, el.shade, 200, cache)
                pic = s.shapes.add_picture(f, E(el.x), E(el.y), E(el.w), E(el.h))
                pic.name = 'image'
            elif isinstance(el, Text):
                _text(s, el)
        if sl.notes:
            s.notes_slide.notes_text_frame.text = sl.notes
    prs.save(path)
    return path
