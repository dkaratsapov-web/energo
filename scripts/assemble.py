# -*- coding: utf-8 -*-
"""Финальная сборка: склеить 32 страницы в один deck.pdf по порядку,
затем (опционально) прогнать печатный конвейер PDF/X-1a.
Страницы, для которых нет собранного вектора, берём из исходного растра.
"""
import sys, os
sys.path.insert(0, 'scripts')
from rebuild import PW, PH
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

BUILD = 'build'
os.makedirs(BUILD, exist_ok=True)

# страницы, которые оставляем растровыми как есть (нет текста / нет вектор-исходников)
KEEP_ORIGINAL = [9, 11, 13, 15, 21, 23, 25, 30, 32]

def ensure_original(n):
    """Собрать одностраничный PDF из исходного растра pgNN.jpg."""
    out = f"{BUILD}/page{n:02d}.pdf"
    c = canvas.Canvas(out, pagesize=(PW, PH))
    c.drawImage(f"page_images_150dpi/pg{n:02d}.jpg", 0, 0, width=PW, height=PH)
    c.showPage(); c.save()
    return out

def combine(out='deck.pdf'):
    w = PdfWriter()
    missing = []
    for n in range(1, 33):
        p = f"{BUILD}/page{n:02d}.pdf"
        if not os.path.exists(p):
            if n in KEEP_ORIGINAL:
                p = ensure_original(n)
            else:
                missing.append(n)
                p = ensure_original(n)  # временно, чтобы дек был полным
        w.add_page(PdfReader(p).pages[0])
    with open(out, 'wb') as f:
        w.write(f)
    return out, missing

if __name__ == '__main__':
    out, missing = combine('deck.pdf')
    print(f"deck.pdf: 32 страницы собраны -> {out}")
    if missing:
        print("ВНИМАНИЕ, ещё не пересобраны (взяты из растра):", missing)
    else:
        print("Все страницы на месте.")
