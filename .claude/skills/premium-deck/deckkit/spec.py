# -*- coding: utf-8 -*-
"""Бриф колоды (YAML): чтение, значения по умолчанию, проверка."""
import os
import yaml

PRINT_DEFAULTS = dict(
    printer='не указана',
    trim_mm=[297.0, 167.06],        # A4 по ширине, пропорция слайда 16:9
    bleed_mm=3.0,
    profile='Coated FOGRA39 (ISO 12647-2:2004)',
    standard='PDF/X-1a:2001',
    min_dpi=300, warn_dpi=200,
    tac_max=300,
    safe_mm=5.0,
    min_text_pt=7.0,
    rich_black_text=False,          # мелкий тёмный текст — только K100
    confirmed={},                   # какие пункты типография подтвердила
)

REQUIRED = {
    'cover': ['title'], 'section': ['title'], 'statement': ['title'],
    'number': ['value', 'title'], 'split_image': ['title', 'image'],
    'full_image': ['title', 'image'], 'points': ['title', 'items'],
    'stats': ['title', 'items'], 'chart': ['title', 'data'], 'quote': ['text'],
    'process': ['title', 'steps'], 'gallery': ['title', 'images'], 'closing': ['title'],
}

PRINT_KEYS = ['trim_mm', 'bleed_mm', 'profile', 'standard', 'min_dpi', 'tac_max',
              'safe_mm', 'min_text_pt', 'rich_black_text']


def _abs(base, p):
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


PAGE_REQUIRED = {
    'cover': ['title', 'image'], 'back': ['image'], 'numbered': ['lead', 'items'],
    'directions': ['title', 'items'], 'mission_chart': ['blocks', 'chart'],
    'figures': ['columns', 'totals'], 'stats': ['items'], 'list': ['title', 'items'],
    'service': ['title'], 'photos': ['photos'], 'civil': ['title', 'rows'], 'map': ['title'],
    'regions': ['items'], 'logos': ['logos'], 'credentials': ['items'],
}
ASSET_KEYS = ('image', 'photos', 'logos', 'path', 'wordmark')


def _resolve(node, root, errors, where):
    """Пути к файлам в любом месте страницы — от assets_dir; проверка наличия."""
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if k in ASSET_KEYS and isinstance(v, str):
                node[k] = _abs(root, v)
                if not os.path.exists(node[k]):
                    errors.append(f'{where}: нет файла {node[k]}')
            elif k in ASSET_KEYS and isinstance(v, list):
                out = []
                for it in v:
                    if isinstance(it, str):
                        it = _abs(root, it)
                        if not os.path.exists(it):
                            errors.append(f'{where}: нет файла {it}')
                    else:
                        _resolve(it, root, errors, where)
                    out.append(it)
                node[k] = out
            else:
                _resolve(v, root, errors, where)
    elif isinstance(node, list):
        for it in node:
            _resolve(it, root, errors, where)


def _load_catalog(spec, base, root, errors):
    fmt = spec['format']
    spec['print'].setdefault('trim_mm', fmt.get('page_mm', [210, 297]))
    if spec['print'].get('trim_mm') == PRINT_DEFAULTS['trim_mm']:
        spec['print']['trim_mm'] = fmt.get('page_mm', [210, 297])
    seen = set()
    for pg in spec.get('pages', []):
        n, lay = pg.get('n'), pg.get('layout')
        where = f'полоса {n}'
        if n in seen:
            errors.append(f'{where}: номер повторяется')
        seen.add(n)
        if lay not in PAGE_REQUIRED:
            errors.append(f'{where}: неизвестная композиция «{lay}»')
            continue
        for k in PAGE_REQUIRED[lay]:
            if not pg.get(k):
                errors.append(f'{where} ({lay}): нет поля «{k}»')
        _resolve(pg, root, errors, where)
    ns = sorted(seen)
    if ns and ns != list(range(1, ns[-1] + 1)):
        errors.append(f'полосы идут не подряд: {ns}')
    if spec.get('logo'):
        spec['_logo'] = _abs(root, spec['logo'])
    if spec.get('map'):
        import pickle
        from . import vector
        (pc, w, h), (pr, _, _) = pickle.load(open(_abs(root, spec['map']), 'rb'))
        spec['_map'] = (vector.from_cmds(pc, w, h), vector.from_cmds(pr, w, h))
    src = spec.get('source') or {}
    for k in ('pdf', 'texts'):
        if src.get(k):
            src[k] = _abs(base, src[k])


def load(path):
    with open(path, encoding='utf-8') as f:
        spec = yaml.safe_load(f)
    base = os.path.dirname(os.path.abspath(path))
    root = _abs(base, spec.get('assets_dir', '.'))
    spec.setdefault('meta', {})
    spec['meta'].setdefault('title', 'Презентация')
    spec.setdefault('concept', 'A')
    pr = dict(PRINT_DEFAULTS)
    pr.update(spec.get('print') or {})
    spec['print'] = pr
    errors = []
    if (spec.get('format') or {}).get('kind') == 'catalog':
        _load_catalog(spec, base, root, errors)
        spec['_errors'] = errors
        spec['_path'] = os.path.abspath(path)
        return spec
    for i, s in enumerate(spec.get('slides', []), 1):
        lay = s.get('layout')
        if lay not in REQUIRED:
            errors.append(f'слайд {i}: неизвестная композиция «{lay}»')
            continue
        for k in REQUIRED[lay]:
            if not s.get(k):
                errors.append(f'слайд {i} ({lay}): нет поля «{k}»')
        if s.get('image'):
            s['image'] = _abs(root, s['image'])
        if s.get('images'):
            s['images'] = [dict(im, path=_abs(root, im['path'])) if isinstance(im, dict)
                           else _abs(root, im) for im in s['images']]
        for p in [s.get('image')] + [im['path'] if isinstance(im, dict) else im
                                     for im in s.get('images', [])]:
            if p and not os.path.exists(p):
                errors.append(f'слайд {i}: нет файла {p}')
    if not spec.get('slides'):
        errors.append('в брифе нет слайдов')
    if spec['concept'] not in ('A', 'B', 'C'):
        errors.append('concept должен быть A, B или C')
    spec['_errors'] = errors
    spec['_path'] = os.path.abspath(path)
    return spec


def unconfirmed(spec):
    """Требования типографии, которые мы приняли сами, без подтверждения."""
    pr = spec['print']
    conf = pr.get('confirmed') or {}
    if conf is True:
        return []
    return [k for k in PRINT_KEYS if not conf.get(k)]
