# -*- coding: utf-8 -*-
"""Просмотр: PNG каждого слайда, лист-контакт, рендер PPTX через LibreOffice."""
import os, subprocess, shutil, tempfile
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont
from .fonts import FONT_DIR


def pngs(pdf, out_dir, dpi=110, prefix='slide', clip_trim=False):
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf)
    out = []
    for i, pg in enumerate(doc, 1):
        clip = pg.trimbox if clip_trim else None
        pix = pg.get_pixmap(dpi=dpi, clip=clip)
        f = os.path.join(out_dir, f'{prefix}_{i:02d}.png')
        pix.save(f)
        out.append(f)
    return out


def contact(files, out, cols=3, width=2400, labels=None, bg=(236, 235, 231)):
    ims = [Image.open(f).convert('RGB') for f in files]
    gap = 28
    cw = (width - gap * (cols + 1)) // cols
    ch = round(cw * ims[0].height / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    lab = 34
    sheet = Image.new('RGB', (width, gap + rows * (ch + lab + gap)), bg)
    d = ImageDraw.Draw(sheet)
    try:
        fnt = ImageFont.truetype(os.path.join(FONT_DIR, 'Onest-Medium.ttf'), 20)
    except OSError:
        fnt = None
    for i, im in enumerate(ims):
        x = gap + (i % cols) * (cw + gap)
        y = gap + (i // cols) * (ch + lab + gap)
        sheet.paste(im.resize((cw, ch), Image.LANCZOS), (x, y + lab))
        d.text((x, y + 4), (labels[i] if labels else f'{i + 1:02d}'), fill=(60, 60, 70), font=fnt)
    sheet.save(out, quality=90)
    return out


def install_fonts():
    """Шрифты колоды в ~/.fonts — иначе LibreOffice подставит чужие."""
    dst = os.path.expanduser('~/.fonts/premium-deck')
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(FONT_DIR):
        if f.endswith('.ttf'):
            shutil.copy2(os.path.join(FONT_DIR, f), dst)
    subprocess.run(['fc-cache', '-f', dst], capture_output=True)
    return dst


def pptx_to_pdf(pptx, out_dir):
    """PPTX глазами другой программы: LibreOffice, без участия нашего рендера."""
    install_fonts()
    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    if not soffice:
        return None
    prof = tempfile.mkdtemp(prefix='lo-')
    subprocess.run([soffice, f'-env:UserInstallation=file://{prof}', '--headless',
                    '--convert-to', 'pdf', '--outdir', out_dir, pptx],
                   capture_output=True, timeout=300)
    shutil.rmtree(prof, ignore_errors=True)
    f = os.path.join(out_dir, os.path.splitext(os.path.basename(pptx))[0] + '.pdf')
    return f if os.path.exists(f) else None
