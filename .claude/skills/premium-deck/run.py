# -*- coding: utf-8 -*-
"""premium-deck: премиальная презентация из брифа одной командой.

  python3 run.py check                         зависимости и скиллы
  python3 run.py concepts BRIEF.yaml [--out D] три концепции на слайдах брифа
  python3 run.py build    BRIEF.yaml [--out D] [--concept A|B|C] [--no-print]

build выпускает в папку D:
  presentation.pptx          редактируемая колода (живой текст, фигуры, снимки)
  presentation_preview.pdf   экранный PDF, RGB, размер слайда
  presentation_print.pdf     печатный PDF/X-1a, CMYK FOGRA39, обрез + вылеты
  design_system.md           дизайн-система колоды
  preflight_report.md        все проверки и неподтверждённые требования типографии
  previews/                  PNG каждого слайда, листы-контакты: PDF, PPTX, печать
"""
import argparse, glob, importlib, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PY = [('reportlab', 'reportlab'), ('pptx', 'python-pptx'), ('pikepdf', 'pikepdf'),
      ('pymupdf', 'pymupdf'), ('PIL', 'pillow'), ('numpy', 'numpy'), ('yaml', 'pyyaml'),
      ('fontTools', 'fonttools'), ('lxml', 'lxml')]
BIN = [('gs', 'apt-get install -y ghostscript', 'PDF/X-1a и перевод снимков'),
       ('soffice', 'apt-get install -y --no-install-recommends libreoffice-impress',
        'независимый рендер PPTX для проверки'),
       ('fc-cache', 'apt-get install -y fontconfig', 'шрифты для LibreOffice')]
SKILLS = ['presentation-design', 'presentation-craft', 'slides', 'pptx', 'canvas-design',
          'typography-system', 'brand-guidelines', 'moodboard-builder', 'print-layout', 'pdf',
          'slop-check', 'design-critique']
SKILL_SRC = {
    'presentation-design': 'npx skills add blisse-code/presentation-design-skill',
    'slides': 'claude plugin marketplace add jameshemson/slides',
    'pptx': 'claude plugin install document-skills@anthropic-agent-skills',
    'pdf': 'claude plugin install document-skills@anthropic-agent-skills',
    'canvas-design': 'claude plugin install example-skills@anthropic-agent-skills',
    'brand-guidelines': 'claude plugin install example-skills@anthropic-agent-skills',
}


def _skill_index():
    roots = [os.path.expanduser('~/.claude'), os.path.join(HERE, '..', '..', '..'),
             os.path.expanduser('~/.agents')]
    names = set()
    for r in roots:
        for f in glob.glob(os.path.join(r, '**', 'SKILL.md'), recursive=True):
            try:
                head = open(f, encoding='utf-8', errors='ignore').read(600)
            except OSError:
                continue
            m = re.search(r'^name:\s*["\']?([\w:.-]+)', head, re.M)
            names.add((m.group(1) if m else os.path.basename(os.path.dirname(f))).split(':')[-1])
            names.add(os.path.basename(os.path.dirname(f)))
    return names


def check(verbose=True):
    ok = True
    out = []
    for mod, pip in PY:
        try:
            m = importlib.import_module(mod)
            out.append(('OK', mod, getattr(m, '__version__', getattr(m, 'VERSION', ''))))
        except Exception:
            ok = False
            out.append(('НЕТ', mod, f'pip install {pip}'))
    for b, cmd, why in BIN:
        p = shutil.which(b) or (shutil.which('libreoffice') if b == 'soffice' else None)
        if p and b == 'soffice':
            # LibreOffice без модуля Impress не открывает PPTX
            if not glob.glob('/usr/lib/libreoffice/share/.registry/impress.xcd') and \
                    not glob.glob('/Applications/LibreOffice.app/Contents/Resources/registry/impress.xcd'):
                p = None
        out.append(('OK' if p else 'НЕТ', b, why if p else f'{cmd}  — {why}'))
        if not p and b == 'gs':
            ok = False
    fdir = os.path.join(HERE, 'fonts')
    need = ['Onest-Regular.ttf', 'Onest-SemiBold.ttf', 'Onest-ExtraBold.ttf', 'PTSerif-Regular.ttf',
            'PTSerif-Italic.ttf', 'Unbounded-Bold.ttf']
    miss = [f for f in need if not os.path.exists(os.path.join(fdir, f))]
    out.append(('OK' if not miss else 'НЕТ', 'шрифты', 'Onest, PT Serif, Unbounded (OFL)' if not miss else f'нет {miss}'))
    icc = os.path.exists(os.path.join(HERE, 'color', 'FOGRA39.icc'))
    out.append(('OK' if icc else 'НЕТ', 'FOGRA39.icc', 'профиль печати' if icc else 'положите профиль в color/'))
    ok = ok and not miss and icc
    idx = _skill_index()
    for s in SKILLS:
        have = s in idx
        out.append(('OK' if have else 'нет', f'скилл {s}', '' if have else SKILL_SRC.get(s, 'не обязателен')))
    if verbose:
        for st, name, note in out:
            print(f'  [{st:>3}] {name:<26} {note}')
        print('\n  Конвейер ' + ('готов к запуску.' if ok else 'НЕ готов: поставьте отмеченное «НЕТ».'))
    return ok, out


def _out(brief, out):
    d = out or os.path.join(os.path.dirname(os.path.abspath(brief)),
                            os.path.splitext(os.path.basename(brief))[0] + '_deck')
    os.makedirs(d, exist_ok=True)
    return d


def concepts(brief, out=None, pick=(0, 1, 4)):
    from deckkit import spec as S, tokens, layouts, pages, render_pdf, preview, docs
    sp = S.load(brief)
    if sp['_errors']:
        sys.exit('Ошибки брифа:\n  ' + '\n  '.join(sp['_errors']))
    catalog = (sp.get('format') or {}).get('kind') == 'catalog'
    if catalog:
        pick = (0, 2, 7)                  # обложка, цифры, направление со снимком
    d = _out(brief, out)
    cdir = os.path.join(d, 'concepts')
    os.makedirs(cdir, exist_ok=True)
    files, labels = [], []
    for code in 'ABC':
        ds = tokens.system(code, sp['brand'], sp.get('format') if catalog else None)
        sl = pages.build(ds, sp) if catalog else layouts.build(ds, sp)
        chosen = [sl[i] for i in pick if i < len(sl)]
        pdf = os.path.join(cdir, f'concept_{code}.pdf')
        render_pdf.render(chosen, pdf, ds['W'], ds['H'], meta=sp['meta'])
        f = preview.pngs(pdf, cdir, dpi=72, prefix=f'concept_{code}')
        files += f
        labels += [f'{code} · {ds["name"]} · ' + ('стр. ' + '–'.join(map(str, sl[i].pages)) if catalog
                                                 else f'слайд {i + 1:02d}') for i in pick if i < len(sl)]
    sheet = preview.contact(files, os.path.join(d, 'concepts.jpg'), cols=len(pick), width=2400, labels=labels)
    # общий PDF концепций
    import pymupdf
    allpdf = pymupdf.open()
    for code in 'ABC':
        allpdf.insert_pdf(pymupdf.open(os.path.join(cdir, f'concept_{code}.pdf')))
    allpdf.save(os.path.join(d, 'concepts.pdf'))
    docs.concepts_md(sp, os.path.join(d, 'concepts.md'), sp.get('concept'))
    print('Концепции:', sheet)
    return d


def build(brief, out=None, concept=None, do_print=True):
    from deckkit import spec as S, tokens, layouts, pages, render_pdf, render_pptx, preview, preflight, pdfx, docs
    t0 = time.time()
    sp = S.load(brief)
    if sp['_errors']:
        sys.exit('Ошибки брифа:\n  ' + '\n  '.join(sp['_errors']))
    if concept:
        sp['concept'] = concept
    d = _out(brief, out)
    pv = os.path.join(d, 'previews')
    shutil.rmtree(pv, ignore_errors=True)
    os.makedirs(pv)
    cache = os.path.join(d, '.cache')
    os.makedirs(cache, exist_ok=True)
    catalog = (sp.get('format') or {}).get('kind') == 'catalog'
    ds = tokens.system(sp['concept'], sp['brand'], sp.get('format') if catalog else None)
    slides = pages.build(ds, sp) if catalog else layouts.build(ds, sp)
    W, H = ds['W'], ds['H']
    pr = sp['print']
    trim = pr['trim_mm']
    if catalog and (abs(trim[0] - W) > 0.01 or abs(trim[1] - H) > 0.01):
        sys.exit(f'Обрез {trim} не совпадает с форматом полосы {W}×{H} мм.')
    if abs(trim[0] / trim[1] - W / H) > 0.005:
        sys.exit(f'Формат печати {trim} не 16:9 — слайды нельзя масштабировать без искажения. '
                 f'Возьмите {trim[0]}×{trim[0] * H / W:.2f} мм или задайте другой формат слайда.')
    k = trim[0] / W
    log = preflight.Log()
    files = {}
    # 1. экранный PDF
    files['Экранный PDF'] = f_prev = os.path.join(d, 'presentation_preview.pdf')
    _, pl_prev, _ = render_pdf.render(slides, f_prev, W, H, meta=sp['meta'], cache=cache)
    notext = os.path.join(cache, 'notext.pdf')
    render_pdf.render(slides, notext, W, H, notext=True, cache=cache)
    f_pages = f_prev
    if catalog:                       # те же полосы по одной — для сверки с PPTX
        f_pages = os.path.join(cache, 'pages_preview.pdf')
        render_pdf.render(slides, f_pages, W, H, mode='pages', meta=sp['meta'], cache=cache)
    # 2. PPTX
    files['PPTX'] = f_pptx = os.path.join(d, 'presentation.pptx')
    render_pptx.render(slides, f_pptx, W, H, cache=cache, meta=sp['meta'], split=catalog)
    lo = preview.pptx_to_pdf(f_pptx, cache)
    # 3. печать
    f_print = None
    if do_print:
        lay = os.path.join(cache, 'print_layout.pdf')
        _, pl_print, _ = render_pdf.render(slides, lay, W, H, mode='print', trim=trim, bleed=pr['bleed_mm'],
                                           meta=sp['meta'], cache=cache, tac=pr['tac_max'])
        files['Печатный PDF/X-1a'] = f_print = os.path.join(d, 'presentation_print.pdf')
        pdfx.to_pdfx(lay, f_print, sp['meta']['title'])
    # 4. просмотр каждого слайда
    a = preview.pngs(f_prev, pv, dpi=60 if catalog else 110, prefix='spread' if catalog else 'slide')
    preview.contact(a, os.path.join(pv, 'sheet_preview.jpg'), cols=2 if catalog else 3,
                    labels=[s_.layout if not catalog else 'стр. ' + '–'.join(map(str, s_.pages))
                            for s_ in slides])
    if catalog:
        a = preview.pngs(f_pages, pv, dpi=60, prefix='page')
    if lo:
        b = preview.pngs(lo, pv, dpi=60 if catalog else 110, prefix='pptx')
        pair, lab = [], []
        for i, (x, y) in enumerate(zip(a, b), 1):
            pair += [x, y]; lab += [f'{i:02d} · PDF', f'{i:02d} · PPTX (LibreOffice)']
        preview.contact(pair, os.path.join(pv, 'sheet_pptx_vs_pdf.jpg'), cols=4 if catalog else 2, labels=lab)
    if f_print:
        c = preview.pngs(f_print, pv, dpi=50 if catalog else 80, prefix='print')
        preview.contact(c, os.path.join(pv, 'sheet_print_bleed.jpg'), cols=8 if catalog else 3,
                        labels=[f'{i:02d} · печать, с вылетами' for i in range(1, len(c) + 1)])
    # 5. проверки
    if catalog:
        preflight.check_layout_catalog(slides, ds, sp, log)
        preflight.check_source_text(slides, ds, sp, log)
    else:
        preflight.check_layout(slides, ds, sp, log, k)
    preflight.check_contrast(slides, notext, log)
    preflight.check_images(pl_prev, sp, log, 'screen')
    preflight.check_pptx(f_pptx, lo, f_pages, sp, log)
    if f_print:
        preflight.check_images(pl_print, sp, log, 'print')
        preflight.check_print_pdf(f_print, sp, log)
    files['Дизайн-система'] = docs.design_system(ds, sp, os.path.join(d, 'design_system.md'))
    rep, fails, warns, un = preflight.report(log, sp, files, os.path.join(d, 'preflight_report.md'))
    print(f'Готово за {time.time() - t0:.0f} с → {d}')
    print(f'  FAIL {fails} · WARN {warns} · неподтверждённых требований типографии: {len(un)}')
    for r in log.rows:
        if r[0] == 'FAIL':
            print(f'  [FAIL] {r[1]} · {r[2]} · {r[3]}')
    if f_print:
        print('  Печать: ' + ('НЕ готово — есть дефекты.' if fails else
                              'проверки пройдены, но требования типографии не подтверждены.' if un else
                              'готово к печати.'))
    return d, fails


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['check', 'concepts', 'build'])
    ap.add_argument('brief', nargs='?')
    ap.add_argument('--out')
    ap.add_argument('--concept', choices=['A', 'B', 'C'])
    ap.add_argument('--no-print', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'check':
        sys.exit(0 if check()[0] else 1)
    if not a.brief:
        ap.error('нужен путь к брифу YAML')
    if a.cmd == 'concepts':
        concepts(a.brief, a.out)
    else:
        build(a.brief, a.out, a.concept, not a.no_print)


if __name__ == '__main__':
    main()
