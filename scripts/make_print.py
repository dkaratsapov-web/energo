# -*- coding: utf-8 -*-
"""
Печатный файл каталога: собранная вёрстка -> PDF/X-1a:2001, CMYK FOGRA39.

Текст и графика остаются ВЕКТОРОМ: ghostscript встраивает шрифты и переводит
цвет в CMYK, но ничего не растрирует. Растрируем — и возвращаемся ровно к той
болезни, из-за которой типография завернула прежний файл.

Вылеты и TrimBox заданы ещё при отрисовке полос (scripts/render.py): полоса
собирается размером обрез+вылет, TrimBox ставится внутренним прямоугольником.
Поэтому здесь ящики не трогаем — только цвет и метаданные.
"""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pikepdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XMP = ('<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
       '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
       'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
       '<rdf:Description rdf:about="" xmlns:pdfx="http://ns.adobe.com/pdfx/1.3/" '
       'xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/">'
       '<pdfx:GTS_PDFXVersion>PDF/X-1:2001</pdfx:GTS_PDFXVersion>'
       '<pdfx:GTS_PDFXConformance>PDF/X-1a:2001</pdfx:GTS_PDFXConformance>'
       '<pdfxid:GTS_PDFXVersion>PDF/X-1:2001</pdfxid:GTS_PDFXVersion>'
       '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>')

DEF = """%!
[ /GTS_PDFXVersion (PDF/X-1:2001)
  /GTS_PDFXConformance (PDF/X-1a:2001)
  /Title (EnergoGrupp Kompleksnoe stroitelstvo 2025)
  /Trapped /False
/DOCINFO pdfmark
/ICCProfile (@ICC@) def
/pdfmark where {pop} {userdict /pdfmark /cleartomark load put} ifelse
[ /_objdef {icc_PDFX} /type /stream /OBJ pdfmark
[ {icc_PDFX} <</N 4>> /PUT pdfmark
[ {icc_PDFX} ICCProfile (r) file /PUT pdfmark
[ /_objdef {OutputIntent_PDFX} /type /dict /OBJ pdfmark
[ {OutputIntent_PDFX} <<
    /Type /OutputIntent
    /S /GTS_PDFX
    /OutputCondition (Coated FOGRA39 \\(ISO 12647-2:2004\\))
    /OutputConditionIdentifier (FOGRA39)
    /RegistryName (http://www.color.org)
    /DestOutputProfile {icc_PDFX}
  >> /PUT pdfmark
[ {Catalog} <</OutputIntents [ {OutputIntent_PDFX} ]>> /PUT pdfmark
"""

def to_pdfx(src, out):
    """CMYK PDF/X-1a.

    Описание OutputIntent пишется во временный файл с АБСОЛЮТНЫМ путём к
    профилю и передаётся gs тоже абсолютным путём: по короткому имени
    ghostscript подхватывает собственный PDFX_def.ps из своей библиотеки,
    а тот ссылается на профиль, которого в системе нет.
    """
    import tempfile
    src, out = os.path.abspath(src), os.path.abspath(out)
    icc = f'{ROOT}/color/FOGRA39.icc'
    with tempfile.NamedTemporaryFile('w', suffix='.ps', delete=False) as f:
        f.write(DEF.replace('@ICC@', icc))
        defs = f.name
    try:
        subprocess.run(
            ['gs', '-dPDFX', '-dBATCH', '-dNOPAUSE', '-dNOSAFER', '-sDEVICE=pdfwrite',
             '-sColorConversionStrategy=CMYK', '-dProcessColorModel=/DeviceCMYK',
             '-dPassThroughJPEGImages=true', '-dAutoRotatePages=/None',
             '-dCompatibilityLevel=1.4', '-dSubsetFonts=true', '-dEmbedAllFonts=true',
             f'-sOutputFile={out}', defs, src], check=True, capture_output=True)
    finally:
        os.unlink(defs)
    return out

def add_xmp(src, out):
    pdf = pikepdf.open(src)
    st = pdf.make_stream(XMP.encode('utf-8'))
    st.Type, st.Subtype = pikepdf.Name.Metadata, pikepdf.Name.XML
    pdf.Root.Metadata = pdf.make_indirect(st)
    pdf.save(out, deterministic_id=False)
    return out

def build(src, out):
    tmp = out + '.tmp.pdf'
    to_pdfx(src, tmp)
    add_xmp(tmp, out)
    os.remove(tmp)
    return out

if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else f'{ROOT}/build/v3/ЭнергоГрупп_2025_вёрстка.pdf'
    out = sys.argv[2] if len(sys.argv) > 2 else f'{ROOT}/build/v3/ЭнергоГрупп_2025_печать_PDFX-1a.pdf'
    f = build(src, out)
    print(f, round(os.path.getsize(f)/1e6, 2), 'МБ')
