# -*- coding: utf-8 -*-
"""Печатная подготовка: CMYK для вектора и PDF/X-1a через ghostscript.

Векторные цвета переводим в CMYK САМИ, по профилю (littleCMS), и сразу
ограничиваем суммарное покрытие: тёмные грунты из RGB после профиля легко
набирают 320–340 %, а офсет на мелованной бумаге держит около 300 %.
Ghostscript затем переводит в CMYK только снимки и пишет PDF/X-1a
(OutputIntent, без прозрачности, все шрифты встроены, текст — вектор).

Сохранение PowerPoint «в PDF» этого не делает: там RGB, нет вылетов,
TrimBox и OutputIntent. Поэтому печатный файл строится только здесь.
"""
import os, subprocess, tempfile
import numpy as np
import pikepdf
from PIL import Image, ImageCms

HERE = os.path.dirname(os.path.abspath(__file__))
ICC = os.path.join(os.path.dirname(HERE), 'color', 'FOGRA39.icc')

_xf = None
_cache = {}


def _transform():
    global _xf
    if _xf is None:
        _xf = ImageCms.buildTransform(ImageCms.createProfile('sRGB'),
                                      ImageCms.getOpenProfile(ICC), 'RGB', 'CMYK',
                                      renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
                                      flags=ImageCms.Flags.BLACKPOINTCOMPENSATION)
    return _xf


def cmyk(rgb, tac_max=300.0):
    """RGB 0–255 -> CMYK 0–1 по FOGRA39 с ограничением суммы красок."""
    key = (tuple(rgb), tac_max)
    if key in _cache:
        return _cache[key]
    im = Image.new('RGB', (1, 1), tuple(int(v) for v in rgb))
    c, m, y, k = (v / 255 for v in ImageCms.applyTransform(im, _transform()).getpixel((0, 0)))
    lim = (tac_max - 8) / 100           # запас под растискивание и округления
    s = c + m + y + k
    if s > lim:                         # снимаем цветные краски, чёрную держим
        f = max((lim - k) / max(c + m + y, 1e-6), 0)
        c, m, y = c * f, m * f, y * f
    if min(rgb) >= 252:
        c = m = y = k = 0.0             # чистый белый — без следов краски
    out = tuple(round(v, 4) for v in (c, m, y, k))
    _cache[key] = out
    return out


XMP = ('<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
       '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
       'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
       '<rdf:Description rdf:about="" xmlns:pdfx="http://ns.adobe.com/pdfx/1.3/" '
       'xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/" '
       'xmlns:dc="http://purl.org/dc/elements/1.1/">'
       '<pdfx:GTS_PDFXVersion>PDF/X-1:2001</pdfx:GTS_PDFXVersion>'
       '<pdfx:GTS_PDFXConformance>PDF/X-1a:2001</pdfx:GTS_PDFXConformance>'
       '<pdfxid:GTS_PDFXVersion>PDF/X-1:2001</pdfxid:GTS_PDFXVersion>'
       '<dc:title><rdf:Alt><rdf:li xml:lang="x-default">@TITLE@</rdf:li></rdf:Alt></dc:title>'
       '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>')

DEF = """%!
[ /GTS_PDFXVersion (PDF/X-1:2001)
  /GTS_PDFXConformance (PDF/X-1a:2001)
  /Title (@TITLE@)
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


def _ascii(s):
    tr = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                  ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o',
                   'p', 'r', 's', 't', 'u', 'f', 'h', 'ts', 'ch', 'sh', 'sch', '', 'y', '', 'e',
                   'yu', 'ya']))
    out = ''.join(tr.get(ch.lower(), ch) if ord(ch) > 127 else ch for ch in s)
    return ''.join(ch for ch in out if 32 <= ord(ch) < 127 and ch not in '()\\')


def to_pdfx(src, out, title='Presentation'):
    """Вёрстка с вылетами -> PDF/X-1a:2001, CMYK FOGRA39. Ящики не трогаем."""
    src, out = os.path.abspath(src), os.path.abspath(out)
    tmp = out + '.gs.pdf'
    with tempfile.NamedTemporaryFile('w', suffix='.ps', delete=False) as f:
        f.write(DEF.replace('@ICC@', ICC).replace('@TITLE@', _ascii(title)))
        defs = f.name
    try:
        r = subprocess.run(
            ['gs', '-dPDFX', '-dBATCH', '-dNOPAUSE', '-dNOSAFER', '-sDEVICE=pdfwrite',
             '-sColorConversionStrategy=CMYK', '-dProcessColorModel=/DeviceCMYK',
             '-dAutoRotatePages=/None', '-dCompatibilityLevel=1.4',
             '-dSubsetFonts=true', '-dEmbedAllFonts=true',
             '-dDownsampleColorImages=false', '-dAutoFilterColorImages=false',
             '-dColorImageFilter=/DCTEncode', '-dJPEGQ=92',
             f'-sOutputFile={tmp}', defs, src], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError('ghostscript: ' + (r.stderr or r.stdout)[-800:])
    finally:
        os.unlink(defs)
    pdf = pikepdf.open(tmp)
    st = pdf.make_stream(XMP.replace('@TITLE@', title).encode('utf-8'))
    st.Type, st.Subtype = pikepdf.Name.Metadata, pikepdf.Name.XML
    pdf.Root.Metadata = pdf.make_indirect(st)
    pdf.docinfo['/Title'] = title
    pdf.docinfo['/GTS_PDFXVersion'] = 'PDF/X-1:2001'
    pdf.docinfo['/GTS_PDFXConformance'] = 'PDF/X-1a:2001'
    pdf.docinfo['/Trapped'] = pikepdf.Name.False_
    pdf.save(out)
    pdf.close()
    os.remove(tmp)
    return out
