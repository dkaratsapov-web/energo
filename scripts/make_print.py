# -*- coding: utf-8 -*-
"""
Печатный конвейер: спеки -> 32 страницы с вылетами -> PDF/X-1a CMYK.

Что делает:
  1. собирает каждую страницу размером обрез+вылет (подложка 300 dpi,
     вылет 4 мм отражением края, TrimBox = 210x297 мм);
  2. склеивает в один документ;
  3. переводит в CMYK FOGRA39 и ставит OutputIntent (ghostscript -dPDFX);
  4. дописывает XMP-метки PDF/X (pikepdf).

Текст на всех этапах остаётся вектором: -dNoOutputFonts не используем,
шрифты встраиваются, растрируется только подложка.
"""
import os, sys, subprocess, glob
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))   # specs.py лежит в корне проекта
import pikepdf
from rebuild import build, MM
from specs import SPECS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLEED_MM = 4.0

def render_pages(out_dir='build/print', dpi=300, denoise=True, pages=None):
    os.makedirs(out_dir, exist_ok=True)
    done=[]
    for n in sorted(SPECS):
        if pages and n not in pages: continue
        build(SPECS[n], out_dir=out_dir, bleed_mm=BLEED_MM, dpi=dpi,
              denoise=denoise, verbose=False)
        done.append(n)
        print(f'  стр {n:02d} готова', flush=True)
    return done

def combine(out='build/deck.pdf', src='build/print'):
    pdf = pikepdf.Pdf.new()
    for i in range(1,33):
        p = f'{src}/page{i:02d}.pdf'
        if not os.path.exists(p):
            raise SystemExit(f'нет страницы {p}')
        with pikepdf.open(p) as s:
            pdf.pages.extend(s.pages)
    pdf.save(out)
    return out

def to_pdfx(inp, out='build/ЭнергоГрупп_2025_печать_PDFX-1a.pdf'):
    """CMYK FOGRA39 + OutputIntent. Профиль подставляем абсолютным путём."""
    src = open(f'{ROOT}/color/PDFX_def.ps', encoding='utf-8').read()
    src = src.replace('/ICCProfile (FOGRA39.icc) def',
                      f'/ICCProfile ({ROOT}/color/FOGRA39.icc) def')
    defps = 'build/PDFX_def_abs.ps'
    open(defps,'w',encoding='utf-8').write(src)
    cmd = ['gs','-dPDFX','-dBATCH','-dNOPAUSE','-dNOSAFER','-sDEVICE=pdfwrite',
           '-sColorConversionStrategy=CMYK','-dProcessColorModel=/DeviceCMYK',
           '-dAutoRotatePages=/None','-dCompatibilityLevel=1.3',
           '-dSubsetFonts=true','-dEmbedAllFonts=true',
           '-dDownsampleColorImages=false','-dDownsampleGrayImages=false',
           '-dColorImageFilter=/DCTEncode','-dJPEGQ=92',
           f'-sOutputFile={out}', defps, inp]
    subprocess.run(cmd, check=True, capture_output=True)
    return out

XMP = ('<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
 '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
 'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
 '<rdf:Description rdf:about="" xmlns:pdfx="http://ns.adobe.com/pdfx/1.3/">'
 '<pdfx:GTS_PDFXVersion>PDF/X-1:2001</pdfx:GTS_PDFXVersion>'
 '<pdfx:GTS_PDFXConformance>PDF/X-1a:2001</pdfx:GTS_PDFXConformance>'
 '</rdf:Description>'
 '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">'
 '<dc:title><rdf:Alt><rdf:li xml:lang="x-default">'
 'ЭнергоГрупп. Комплексное строительство 2025</rdf:li></rdf:Alt></dc:title>'
 '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>')

def add_xmp(path):
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        st = pdf.make_stream(XMP.encode('utf-8'))
        st.Type = pikepdf.Name.Metadata; st.Subtype = pikepdf.Name.XML
        pdf.Root.Metadata = pdf.make_indirect(st)
        pdf.save(path)
    return path

if __name__ == '__main__':
    only = [int(a) for a in sys.argv[1:] if a.isdigit()] or None
    if '--skip-render' not in sys.argv:
        print('1) страницы с вылетами, подложка 300 dpi')
        render_pages(pages=only)
    print('2) склейка')
    deck = combine()
    print('3) CMYK FOGRA39 / PDF/X-1a')
    out = to_pdfx(deck)
    print('4) XMP')
    add_xmp(out)
    print('готово ->', out)
