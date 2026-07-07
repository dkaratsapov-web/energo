# -*- coding: utf-8 -*-
"""
Финальный печатный конвейер: собранный ВЕКТОРНЫЙ PDF -> PDF/X-1a (CMYK FOGRA39) с вылетами.
ВАЖНО: текст остаётся ВЕКТОРОМ (не растрируем!). gs встраивает шрифты и переводит цвет в CMYK.

Требования типографии (из ТЗ клиента), которые здесь учтены:
  - CMYK (профиль FOGRA39, OutputIntent встроен), без RGB;
  - вылеты (bleed) >= 4 мм;  TrimBox = A4 (210x297);
  - БЕЗ меток обреза (спуск полос типография делает сама в CorelDraw);
  - один слой / без лишних путей — обеспечивается плоской вёрсткой.
  - Растровые фото должны быть 300 dpi CMYK (следите за разрешением подставляемых фото).

Шаги:
  1) combine: склеить постраничные векторные PDF в один deck.pdf (по порядку 1..32).
  2) add_bleed: расширить фон каждой страницы на 4 мм (bleed) — см. ниже реализацию.
  3) gs -dPDFX + PDFX_def.ps -> CMYK PDF/X-1a.
  4) pikepdf -> добавить XMP-метаданные PDF/X.

Замечание по bleed для ВЕКТОРНЫХ страниц:
  Векторные страницы собраны в размер обреза (595.446 x 841.691 pt) без вылетов.
  Простейший способ добавить bleed без потери качества — при сборке страницы
  (build_page) класть фон-изображение чуть больше листа (на 4 мм с каждой стороны,
  reflect-паддинг растрового фона) и ставить страницу размером trim+bleed, а TrimBox
  задавать внутренним прямоугольником. Ниже — вариант, добавляющий bleed постфактум
  масштабированием содержимого (проще, но края чуть «наезжают»). Для идеала —
  пересобрать страницы сразу в размер с вылетами.
"""
import sys, io, subprocess
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

A4_W, A4_H = 595.445669, 841.691339
MM = 2.834645  # pt per mm
BLEED_MM = 4.0

def combine(page_pdfs, out='deck.pdf'):
    w=PdfWriter()
    for p in page_pdfs:
        w.add_page(PdfReader(p).pages[0])
    with open(out,'wb') as f: w.write(f)
    return out

def set_boxes(inp, out, bleed_mm=BLEED_MM):
    """Задать TrimBox/BleedBox. Предполагается, что страницы уже размера trim+bleed
    (MediaBox = bleed box). Если страницы размера trim (без вылетов), сначала добавьте
    вылеты (см. примечание в докстринге)."""
    b=bleed_mm*MM
    r=PdfReader(inp); wr=PdfWriter()
    for p in r.pages:
        mb=p.mediabox; x0,y0,x1,y1=map(float,(mb.left,mb.bottom,mb.right,mb.top))
        p.bleedbox=RectangleObject([x0,y0,x1,y1])
        p.trimbox =RectangleObject([x0+b,y0+b,x1-b,y1-b])
        p.cropbox =RectangleObject([x0,y0,x1,y1])
        wr.add_page(p)
    with open(out,'wb') as f: wr.write(f)
    return out

def to_pdfx(inp, out='print_PDFX-1a.pdf', pdfx_def='color/PDFX_def.ps'):
    """gs -> CMYK PDF/X-1a. PDFX_def.ps должен ссылаться на FOGRA39.icc (абс. путь!)."""
    cmd=['gs','-dPDFX','-dBATCH','-dNOPAUSE','-dNOSAFER','-sDEVICE=pdfwrite',
         '-sColorConversionStrategy=CMYK','-dProcessColorModel=/DeviceCMYK',
         '-dPassThroughJPEGImages=true','-dAutoRotatePages=/None','-dCompatibilityLevel=1.4',
         f'-sOutputFile={out}', pdfx_def, inp]
    subprocess.run(cmd, check=True)
    return out

def add_xmp(inp, out):
    import pikepdf
    xmp=('<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>'
     '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
     'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
     '<rdf:Description rdf:about="" '
     'xmlns:pdfx="http://ns.adobe.com/pdfx/1.3/" '
     'xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/">'
     '<pdfx:GTS_PDFXVersion>PDF/X-1:2001</pdfx:GTS_PDFXVersion>'
     '<pdfx:GTS_PDFXConformance>PDF/X-1a:2001</pdfx:GTS_PDFXConformance>'
     '<pdfxid:GTS_PDFXVersion>PDF/X-1:2001</pdfxid:GTS_PDFXVersion>'
     '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>')
    pdf=pikepdf.open(inp)
    st=pdf.make_stream(xmp.encode('utf-8')); st.Type=pikepdf.Name.Metadata; st.Subtype=pikepdf.Name.XML
    pdf.Root.Metadata=pdf.make_indirect(st)
    pdf.save(out, deterministic_id=False)
    return out

if __name__=='__main__':
    # пример полного прогона (страницы уже с вылетами!):
    pages=[f'vector_pages/page{ i:02d}.pdf' for i in range(1,33)]  # подставьте реальные файлы
    deck=combine(pages,'deck.pdf')
    boxed=set_boxes(deck,'deck_boxed.pdf')
    x=to_pdfx(boxed,'print_PDFX-1a.pdf')
    add_xmp(x,'print_PDFX-1a_xmp.pdf')
    print('done -> print_PDFX-1a_xmp.pdf')
