# -*- coding: utf-8 -*-
"""Три визуальные концепции и сборка дизайн-системы из концепции + бренда.

Концепция — это не «тема оформления», а набор решений: какая поверхность
главная, какая гарнитура несёт характер, чем занят акцент, какой мотив
повторяется. Бренд клиента подставляет свои цвета в эти роли, но роли не
меняет: акцент всегда делает одну работу.
"""
import copy

SLIDE_W, SLIDE_H = 338.667, 190.5          # 16:9, мм (13,333 × 7,5 дюйма)


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


CONCEPTS = {
    'A': dict(
        code='A', name='Редакционная сетка',
        idea='Светлый лист, жёсткая модульная сетка, крупный гротеск с плотным '
             'трекингом. Порядок и точность — язык инженерной компании.',
        references=[
            'Йозеф Мюллер-Брокман, «Grid Systems in Graphic Design» — модульная сетка, асимметрия',
            'Годовые отчёты Experimental Jetset и Pentagram — гротеск, тонкие линейки, индексы',
            'Журнал «Проект Россия» (2000-е) — архитектурная вёрстка, много воздуха',
        ],
        mood=['точность', 'воздух', 'инженерия', 'спокойная уверенность'],
        display='onest-black', display_track=-0.035, display_case='upper',
        body='onest', strong='onest-semi', label='onest-semi', number='onest-black',
        quote='onest-bold',
        scale=dict(hero=168, h1=58, h2=34, lead=24, body=17, label=11.5, caption=12),
        lead_k=dict(display=1.0, body=1.4),
        motif='rule',
        grounds=dict(base='paper', alt='paper2', field='dark', image='dark'),
    ),
    'B': dict(
        code='B', name='Ночная антиква',
        idea='Глубокий тёмный фон, крупная антиква в светлом начертании, курсив '
             'для смысловых акцентов. Вечерний свет: премиально, сдержанно, '
             'немного кинематографично.',
        references=[
            'Обложки и развороты Kinfolk / Cereal — антиква крупным кеглем, тишина',
            'Презентации аукционных домов (Sotheby’s, Phillips) — тёмный фон, курсив, минимум элементов',
            'Айдентика ночных архитектурных съёмок (Hufton+Crow) — свет на тёмном',
        ],
        mood=['глубина', 'вечер', 'вес', 'доверие'],
        display='serif', display_track=-0.02, display_case='none',
        body='onest', strong='onest-semi', label='onest-semi', number='serif',
        quote='serif-it',
        scale=dict(hero=176, h1=62, h2=36, lead=25, body=17, label=11.5, caption=12),
        lead_k=dict(display=1.0, body=1.42),
        motif='arc',
        grounds=dict(base='dark', alt='dark2', field='paper', image='dark'),
    ),
    'C': dict(
        code='C', name='Цветовое поле',
        idea='Насыщенные плоские поля фирменного цвета, широкий гротеск, '
             'блоки, уходящие за обрез. Энергия и масштаб — для смелого клиента.',
        references=[
            'Плакаты Wim Crouwel и цветовые поля Карла Герстнера',
            'Айдентика Sagmeister & Walsh для Casa da Música — цвет как структура',
            'Кампании Spotify Wrapped — плоский цвет, крупный широкий шрифт',
        ],
        mood=['энергия', 'масштаб', 'смелость', 'движение'],
        display='wide-bold', display_track=-0.025, display_case='upper',
        body='onest', strong='onest-semi', label='onest-semi', number='wide-bold',
        quote='onest-bold',
        scale=dict(hero=150, h1=50, h2=30, lead=24, body=17, label=11.5, caption=12),
        lead_k=dict(display=1.06, body=1.4),
        motif='block',
        grounds=dict(base='paper', alt='accent', field='dark', image='dark'),
    ),
}

DEFAULT_BRAND = dict(accent='#E0872F', dark='#2E3154', ink='#1A1B26', paper='#F2F1EE')


class Ground:
    """Поверхность и всё, что на ней пишется."""

    def __init__(self, name, bg, ink, muted, line, accent):
        self.name, self.bg, self.ink, self.muted, self.line = name, bg, ink, muted, line
        self.accent = accent
        self.dark = lum(bg) < 0.2

    def accent_text(self, size_pt):
        """Акцент для текста — только если читается; иначе основной цвет."""
        need = 3.0 if size_pt >= 24 else 4.5
        return self.accent if contrast(self.accent, self.bg) >= need else self.ink


def readable(col, bg, need=4.6):
    """Сдвигаем вторичный цвет к основному, пока он не читается на фоне."""
    ink = max(((0, 0, 0), (255, 255, 255)), key=lambda v: contrast(v, bg))
    t = 0.0
    c = col
    while contrast(c, bg) < need and t < 1:
        t += 0.04
        c = mix(col, ink, t)
    return c


# Печатный каталог A4: кегли под чтение с руки, поля под переплёт.
PRINT_SCALE = dict(hero=104, h1=34, h2=20, lead=13, body=9.5, label=7.0, caption=7.5)


def system(concept='A', brand=None, fmt=None):
    """fmt — None (слайды 16:9) или {'page_mm': [210, 297], 'spreads': True}."""
    c = copy.deepcopy(CONCEPTS[concept])
    b = dict(DEFAULT_BRAND, **(brand or {}))
    acc, dark = hexrgb(b['accent']), hexrgb(b['dark'])
    ink, paper = hexrgb(b['ink']), hexrgb(b['paper'])
    # фирменный тёмный по умолчанию в B углубляется; brand.keep_dark — не трогать
    deep = dark if b.get('keep_dark') else mix(dark, (8, 9, 20), 0.35)
    g = {
        'paper':  Ground('paper', paper, ink, mix(ink, paper, 0.42), mix(ink, paper, 0.78), acc),
        'paper2': Ground('paper2', mix(paper, ink, 0.06), ink, mix(ink, paper, 0.40),
                         mix(ink, paper, 0.72), acc),
        'dark':   Ground('dark', deep if concept == 'B' else dark, paper,
                         mix(paper, dark, 0.42), mix(paper, dark, 0.72), acc),
        'dark2':  Ground('dark2', hexrgb(b['dark2']) if b.get('dark2') else mix(deep, paper, 0.07),
                         paper, mix(paper, deep, 0.40), mix(paper, deep, 0.70), acc),
    }
    # насыщенное поле: текст тёмный или светлый — что контрастнее
    on_acc = max((ink, paper), key=lambda v: contrast(v, acc))
    if contrast(on_acc, acc) < 4.6:        # фирменные не читаются — чистые чёрный/белый
        on_acc = max(((0, 0, 0), (255, 255, 255)), key=lambda v: contrast(v, acc))
    g['accent'] = Ground('accent', acc, on_acc, mix(on_acc, acc, 0.30),
                         mix(on_acc, acc, 0.55), on_acc)
    for gr in g.values():                  # вторичный текст — не ниже AA
        gr.muted = readable(gr.muted, gr.bg)
    c['ground'] = g
    c['brand'] = b
    if fmt:
        pw, ph = fmt.get('page_mm', (210, 297))
        c['scale'] = dict(PRINT_SCALE, **fmt.get('scale', {}))
        c['grid'] = dict(margin=16.0, inner=18.0, top=15.0, bottom=13.0, cols=6, gutter=5.0)
        c['W'], c['H'] = pw, ph
        c['spreads'] = fmt.get('spreads', True)
        c['print_doc'] = True
    else:
        c['grid'] = dict(margin=18.0, top=16.0, bottom=14.0, cols=12, gutter=5.0)
        c['W'], c['H'] = SLIDE_W, SLIDE_H
        c['print_doc'] = False
    return c


def col_x(ds, i, span=1):
    """Левый край колонки i (0..11) и ширина span колонок, мм."""
    gr = ds['grid']
    cw = (ds['W'] - 2 * gr['margin'] - (gr['cols'] - 1) * gr['gutter']) / gr['cols']
    x = gr['margin'] + i * (cw + gr['gutter'])
    return x, span * cw + (span - 1) * gr['gutter']
