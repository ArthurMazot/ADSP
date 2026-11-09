"""
Decodificador de display de 7 segmentos por algoritmo (sem modelo, sem treinamento).

Funciona com qualquer quantidade de dígitos e ignora unidades e ícones (mV, AC, AUTO...),
em qualquer posição. Todas as medidas são relativas à altura do dígito, e não ao recorte.

Pipeline:
  1. pré-processamento: canal verde, correção de iluminação, deconvolução
  2. binarização (Otsu) -> pixels de "tinta"
  3. remoção da moldura (linhas retas longas) e correção da inclinação (itálico)
  4. linha de dígitos = maior grupo de objetos com a mesma altura e o topo alinhado
     (unidades e ícones são menores e ficam de fora; a moldura é maior)
  5. reescala a imagem para os dígitos terem ~120 px de altura e repete 1-4
  6. sinal de menos (largo, baixo, à meia altura, à esquerda) e ponto decimal (pequeno,
     na base, entre dois dígitos)
  7. em cada dígito, fração de tinta nas 7 regiões dos segmentos -> dígito mais próximo
     da tabela (distância de Hamming)

        aaa
       f   b
       f   b
        ggg
       e   c
       e   c
        ddd

Uso:
  python seven_segment_decoder.py --image captures/*_raw.png          (decodifica arquivos)
  python seven_segment_decoder.py --image x.png --debug                (salva imagem de depuração)
  python seven_segment_decoder.py                                      (webcam, sem internet)
"""
import argparse
import glob
import time
from pathlib import Path

import cv2
import numpy as np

CAPTURE_DIR = Path(__file__).resolve().parent / "captures"

# Estado da seleção do retângulo na janela da webcam
start_point = None
current_point = None
selected_roi = None  # (x, y, largura, altura)
dragging = False

# Padrão de segmentos (a, b, c, d, e, f, g) de cada dígito
DIGITS = {
    "0": (1, 1, 1, 1, 1, 1, 0),
    "1": (0, 1, 1, 0, 0, 0, 0),
    "2": (1, 1, 0, 1, 1, 0, 1),
    "3": (1, 1, 1, 1, 0, 0, 1),
    "4": (0, 1, 1, 0, 0, 1, 1),
    "5": (1, 0, 1, 1, 0, 1, 1),
    "6": (1, 0, 1, 1, 1, 1, 1),
    "7": (1, 1, 1, 0, 0, 0, 0),
    "8": (1, 1, 1, 1, 1, 1, 1),
    "9": (1, 1, 1, 1, 0, 1, 1),
}
# Alguns displays desenham o 6 sem o 'a', o 7 com o 'f' e o 9 sem o 'd'
ALTERNATES = {
    "6": [(0, 0, 1, 1, 1, 1, 1)],
    "7": [(1, 1, 1, 0, 0, 1, 0)],
    "9": [(1, 1, 1, 0, 0, 1, 1)],
}

# Região de cada segmento dentro da caixa do dígito: (x0, x1, y0, y1) em fração da largura/altura
SEGMENT_REGIONS = {
    "a": (0.25, 0.75, 0.00, 0.18),
    "b": (0.70, 1.00, 0.12, 0.42),
    "c": (0.70, 1.00, 0.58, 0.88),
    "d": (0.25, 0.75, 0.82, 1.00),
    "e": (0.00, 0.30, 0.58, 0.88),
    "f": (0.00, 0.30, 0.12, 0.42),
    "g": (0.25, 0.75, 0.40, 0.60),
}
SEGMENT_ON = 0.35        # fração mínima de tinta para considerar o segmento aceso
DIGIT_H_TARGET = 120     # altura do dígito (px) depois da reescala automática
ONE_WIDTH = 0.65         # dígito com largura < isso x largura típica é um "1"


# --------------------------------------------------------------------------
# Pré-processamento (iluminação e desfoque)
# --------------------------------------------------------------------------
def flatten_background(gray, k):
    """Corrige iluminação desigual: estima o fundo do LCD e divide a imagem por ele.

    O fechamento morfológico com um kernel maior que a espessura de um segmento apaga os
    dígitos escuros e deixa só o fundo iluminado. Dividir por ele deixa o fundo uniforme.
    """
    k = max(9, int(k)) | 1
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.GaussianBlur(bg, (0, 0), k / 6)
    flat = np.clip(gray.astype(np.float32) / np.maximum(bg.astype(np.float32), 1), 0, 1)
    return cv2.normalize((flat * 255).astype(np.uint8), None, 0, 255, cv2.NORM_MINMAX)


def deblur(gray, sigma=2.5, iterations=10):
    """Deconvolução de Richardson-Lucy com PSF gaussiana: desfaz parte do desfoque."""
    img = gray.astype(np.float32) / 255 + 1e-3
    est = img.copy()
    for _ in range(iterations):
        conv = cv2.GaussianBlur(est, (0, 0), sigma) + 1e-6
        est *= cv2.GaussianBlur(img / conv, (0, 0), sigma)
    return np.clip(est * 255, 0, 255).astype(np.uint8)


def preprocess(img, scale, digit_h=None):
    """Canal verde reescalado, com iluminação corrigida e menos desfoque."""
    g = img[:, :, 1]   # verde: menos ruído e ignora reflexos vermelhos
    interp = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=interp)
    # Sem remoção de ruído (non-local means): a mediana de frames, o blur antes do Otsu e a
    # leitura por fração de tinta já lidam com o ruído, e ela custava ~75% do tempo.
    # Kernel do fundo: maior que um segmento. Sem saber o dígito, usa 20% da altura
    k = 0.35 * digit_h if digit_h else 0.2 * g.shape[0]
    g = flatten_background(g, k)
    return deblur(g, sigma=2.0 * (digit_h / DIGIT_H_TARGET) if digit_h else 2.5)


def to_ink(g):
    """Imagem pré-processada -> binária com segmentos = 255."""
    if np.median(g) < 127:          # display com backlight (dígito claro): inverte
        g = 255 - g
    g = cv2.GaussianBlur(g, (5, 5), 0)
    _, ink = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return ink


# --------------------------------------------------------------------------
# Limpeza
# --------------------------------------------------------------------------
def boxes_of(img):
    n, _, stats, _ = cv2.connectedComponentsWithStats(img, connectivity=8)
    return [tuple(int(v) for v in stats[i][:5]) for i in range(1, n)]


def remove_long_lines(ink):
    """Apaga linhas retas longas (bordas da janela do LCD), sem tocar nos segmentos.

    Abertura com um kernel de 1 pixel de espessura e comprimento L só preserva trechos
    retos com pelo menos L pixels naquela direção. Os segmentos e o sinal de menos são mais
    curtos que L, mas as bordas da moldura não. Subtrair essas linhas descola
    o sinal de menos (e dígitos) da moldura.
    """
    h = ink.shape[0]
    # Horizontal: segmentos e menos têm < 0.45h. Vertical: o lado b+c de um 3/7/9 chega a ~0.75h
    horiz = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (int(0.6 * h), 1)))
    vert = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(0.82 * h))))
    lines = cv2.dilate(cv2.bitwise_or(horiz, vert), cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    out = cv2.subtract(ink, lines)
    # A subtração pode deixar fiapos; uma abertura leve limpa
    return cv2.morphologyEx(out, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))


def remove_frame(ink):
    """Remove a moldura do display e reflexos.

    Dígitos e o ponto ficam no meio do recorte; a moldura encosta na borda ou é muito larga.
    """
    ink = remove_long_lines(ink)
    h, w = ink.shape
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    keep = np.ones(n, bool)
    keep[0] = False
    for i in range(1, n):
        x, y, ww, hh, area = stats[i]
        touches = x <= 1 or y <= 1 or x + ww >= w - 1 or y + hh >= h - 1
        big = hh > 0.45 * h or ww > 0.3 * w
        line = max(ww, hh) > 5 * max(1, min(ww, hh))
        tiny = area < (h * h) / 2000
        very_wide = ww > 0.45 * w                    # nenhum objeto legítimo é tão largo
        # Fragmento baixo encostado em cima/embaixo: pedaço da borda da janela do LCD
        edge_bit = ((y <= 1 or y + hh >= h - 1) and hh < 0.4 * h) \
            or y > 0.85 * h or y + hh < 0.15 * h        # inteiramente na faixa da borda
        if (touches and (big or line)) or tiny or very_wide or edge_bit:
            keep[i] = False
    # Uma única indexação em vez de uma máscara por componente (bem mais rápido com muita sujeira)
    return np.where(keep[labels], ink, 0).astype(np.uint8)


def shear(img, s):
    """Cisalhamento horizontal: x' = x + s * (y - h/2). s > 0 endireita dígito inclinado p/ direita."""
    h, w = img.shape
    m = np.float32([[1, s, -s * h / 2], [0, 1, 0]])
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_NEAREST)


def deskew(ink):
    """Escolhe o cisalhamento que maximiza a variância da projeção vertical (colunas nítidas)."""
    best_s, best_score = 0.0, -1.0
    for s in np.linspace(-0.35, 0.35, 29):
        score = np.var(shear(ink, s).sum(axis=0).astype(np.float64))
        if score > best_score:
            best_s, best_score = s, score
    return shear(ink, best_s), best_s


# --------------------------------------------------------------------------
# Linha de dígitos
# --------------------------------------------------------------------------
def merge_vertical(ink, kv, kw=None):
    """Fechamento vertical: junta os segmentos de um dígito (há pequenas falhas entre eles)."""
    kv = max(3, int(kv)) | 1
    kw = (max(3, int(kv / 3)) if kw is None else kw) | 1
    # Padding: sem ele, o fechamento "gruda" objetos na borda da imagem (o OpenCV trata o
    # lado de fora como tinta na erosão)
    p = kv
    padded = cv2.copyMakeBorder(ink, p, p, p, p, cv2.BORDER_CONSTANT, value=0)
    closed = cv2.morphologyEx(padded, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kv)))
    return closed[p:-p, p:-p]


def without_small_blobs(ink, dh):
    """Cópia sem objetos pequenos e compactos (ponto decimal, sujeira), para agrupar dígitos.

    O ponto pode encostar nos dois dígitos vizinhos e uni-los num objeto só.
    """
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    small = (stats[:, cv2.CC_STAT_WIDTH] < 0.22 * dh) & (stats[:, cv2.CC_STAT_HEIGHT] < 0.22 * dh)
    small[0] = True                              # fundo continua fundo
    return np.where(small[labels], 0, ink).astype(np.uint8)


def split_wide(img, box, max_ratio=0.85, depth=0):
    """Divide um objeto largo demais para ser um dígito (dois dígitos colados, p.ex. pelo ponto)
    no vale do perfil de colunas, onde há menos tinta."""
    x, y, w, h = box[:4]
    if w <= max_ratio * h or w < 8 or depth > 5:
        return [(x, y, w, h)]
    cols = (img[y:y + h, x:x + w] > 0).sum(axis=0)
    lo, hi = int(0.2 * w), int(0.8 * w)
    i = lo + int(np.argmin(cols[lo:hi]))
    if cols[i] > 0.35 * h:                      # sem vale claro: não é junção de dígitos
        return [(x, y, w, h)]
    parts = []
    for a, b in ((x, x + i), (x + i + 1, x + w)):
        sub = img[y:y + h, a:b]
        ys, xs = np.nonzero(sub)
        if ys.size == 0:
            continue
        nb = (a + int(xs.min()), y + int(ys.min()), int(xs.max() - xs.min()) + 1,
              int(ys.max() - ys.min()) + 1)
        parts += split_wide(img, nb, max_ratio, depth + 1)
    return parts


def split_all(img, boxes, max_ratio=0.85):
    out = []
    for b in boxes:
        out += split_wide(img, b, max_ratio)
    return out


def find_digit_row(ink, kv_list, kw=3):
    """Acha a linha de dígitos: o grupo de objetos com altura parecida e topo alinhado que cobre
    mais altura no total (nº de membros x altura).

    Unidades/ícones são mais baixos e a moldura é mais alta, então ficam fora do grupo.
    Pontuar por altura total evita escolher "metades" de dígitos quando os segmentos de cima
    e de baixo não se juntaram. Testa vários tamanhos de fechamento e fica com o melhor.
    Devolve (topo, altura, membros) ou None.
    """
    best, best_key = None, (0, 0)
    for kv in kv_list:
        merged = merge_vertical(ink, kv, kw=kw)
        boxes = [bx for bx in split_all(merged, boxes_of(merged))
                 if bx[3] >= 8 and 0.08 <= bx[2] / bx[3] <= 1.2]
        for _, ty, _, th in boxes:
            members = [bx for bx in boxes
                       if 0.75 * th <= bx[3] <= 1.33 * th and abs(bx[1] - ty) < 0.2 * th]
            key = (len(members) * th, th)
            if key > best_key:
                best, best_key = members, key
    if not best:
        return None
    top = float(np.median([bx[1] for bx in best]))
    height = float(np.median([bx[3] for bx in best]))
    return top, height, best


def refine_top(ink, members, top, dh):
    """Sobe o topo se houver tinta logo acima da faixa nas colunas dos dígitos.

    Em alguns displays o segmento 'a' não encosta no 'b' e fica fora do grupo encontrado.
    """
    max_gap = max(2, int(0.1 * dh))
    tops = []
    for x, _, w, _ in members:
        y = int(top)
        gap = 0
        cur = y
        while y > 0 and y > top - 0.3 * dh:
            y -= 1
            if ink[y, x:x + w].any():
                cur, gap = y, 0
            else:
                gap += 1
                if gap > max_gap:
                    break
        tops.append(cur)
    return float(np.median(tops)) if tops else top


def refine_height(ink, members, top, dh):
    """Altura real do dígito: desce pela coluna de cada dígito a partir do topo e para no
    primeiro vão grande. Fragmentos da moldura logo abaixo dos dígitos ficam de fora."""
    max_gap = max(2, int(0.1 * dh))
    heights = []
    for x, _, w, _ in members:
        prof = ink[int(top):int(top + 1.5 * dh), x:x + w].any(axis=1)
        last, gap = 0, 0
        for i, v in enumerate(prof):
            if v:
                last, gap = i, 0
            else:
                gap += 1
                if gap > max_gap and last > 0.5 * dh:
                    break
        heights.append(last + 1)
    return float(np.median(heights)) if heights else dh


def collect_digits(ink, top, dh):
    """Caixas dos dígitos na faixa [top, top + dh].

    - fechamento vertical (e levemente horizontal) junta os segmentos de cada dígito;
    - a extensão horizontal vem do perfil de colunas: só conta coluna com tinta de verdade,
      então fiapos da moldura encostados no dígito não alargam a caixa;
    - todos recebem a mesma altura (a da faixa), mesmo que a base de um suma num canto escuro.
    """
    y0, y1 = int(max(0, top)), int(min(ink.shape[0], top + dh))
    band = np.zeros_like(ink)
    band[y0:y1] = ink[y0:y1]
    merged = merge_vertical(band, 0.3 * dh, kw=max(3, int(0.06 * dh)))
    cand = [b for b in split_all(merged, boxes_of(merged)) if b[3] > 0.55 * dh and b[2] < 1.0 * dh]
    cand.sort(key=lambda b: b[0])
    digits = []
    for x, _, w, _ in cand:
        cols = (band[y0:y1, x:x + w] > 0).sum(axis=0)
        strong = np.where(cols >= 0.07 * dh)[0]
        if strong.size == 0:
            continue
        x0, x1 = x + int(strong[0]), x + int(strong[-1]) + 1
        # Dígito de verdade tem tinta descendo do topo por boa parte da altura
        # (unidade + sinal de menos empilhados não têm)
        if vertical_extent(band, x0, x1, top, dh) < 0.65 * dh:
            continue
        digits.append((x0, int(top), x1 - x0, int(dh)))
    return digits


def vertical_extent(ink, x0, x1, top, dh):
    """Até onde a tinta desce a partir do topo, tolerando vãos pequenos entre segmentos."""
    prof = ink[int(top):int(top + 1.2 * dh), x0:x1].any(axis=1)
    max_gap = max(2, int(0.12 * dh))
    last, gap, started = 0, 0, False
    for i, v in enumerate(prof):
        if v:
            if not started and i > 0.25 * dh:    # começa longe do topo: não é dígito
                return 0
            started, last, gap = True, i, 0
        elif started:
            gap += 1
            if gap > max_gap:
                break
    return last + 1 if started else 0


def keep_main_run(digits):
    """Os dígitos de um display são vizinhos com passo regular: fica a maior sequência assim.

    O passo é medido pelas bordas direitas (um "1" fica no lado direito da célula).
    """
    if len(digits) < 3:
        return digits
    right = np.array([d[0] + d[2] for d in digits], float)
    gaps = np.diff(right)
    pitch = float(np.median(gaps))
    runs, cur = [], [digits[0]]
    for d, g in zip(digits[1:], gaps):
        if 0.5 * pitch < g < 1.6 * pitch:
            cur.append(d)
        else:
            runs.append(cur)
            cur = [d]
    runs.append(cur)
    return max(runs, key=len)


def find_marks(ink, digits, top, dh):
    """Sinal de menos e ponto decimal, na tinta original, relativos à linha de dígitos."""
    bottom = top + dh
    mid = top + dh / 2
    first_x = digits[0][0]
    centers = [d[0] + d[2] / 2 for d in digits]
    in_digit = lambda cx: any(d[0] + 0.2 * d[2] < cx < d[0] + 0.8 * d[2] for d in digits)
    points, minus = [], []
    for x, y, ww, hh, area in boxes_of(ink):
        cx, cy = x + ww / 2, y + hh / 2
        aspect = ww / max(hh, 1)
        if (ww < 0.25 * dh and hh < 0.25 * dh and 0.4 < aspect < 2.5 and area > 0.3 * ww * hh
                and abs(y + hh - bottom) < 0.15 * dh and centers[0] < cx < centers[-1]
                and not in_digit(cx)):
            points.append((x, y, ww, hh))
        elif (aspect > 1.8 and hh < 0.35 * dh and 0.2 * dh < ww < 1.0 * dh
              and abs(cy - mid) < 0.3 * dh and x + ww <= first_x + 2
              and first_x - (x + ww) < 1.0 * dh):
            minus.append((x, y, ww, hh))
    points = sorted(points, key=lambda p: abs(p[1] + p[3] - bottom))[:1]
    if not points:
        points = point_in_gaps(ink, digits, bottom, dh)
    minus = sorted(minus, key=lambda m: first_x - (m[0] + m[2]))[:1]
    return points, minus


def point_in_gaps(ink, digits, bottom, dh):
    """Plano B para o ponto colado num dígito.

    Nas colunas do ponto só há tinta perto da base; toda coluna de dígito também tem tinta
    mais acima (segmentos a/g ou verticais). Procura uma sequência dessas colunas "só base"
    entre o primeiro e o último dígito.
    """
    top = bottom - dh
    x_start = int(digits[0][0] + digits[0][2] / 2)
    x_end = int(digits[-1][0] + digits[-1][2] / 2)
    yb0, yb1 = int(bottom - 0.2 * dh), int(min(ink.shape[0], bottom + 0.08 * dh))
    upper = ink[int(max(0, top)):int(bottom - 0.3 * dh), x_start:x_end].any(axis=0)
    base = ink[yb0:yb1, x_start:x_end].any(axis=0)
    only_base = base & ~upper
    best = []
    i, n = 0, len(only_base)
    while i < n:
        if only_base[i]:
            j = i
            while j < n and only_base[j]:
                j += 1
            w = j - i
            if 0.05 * dh <= w <= 0.25 * dh:
                region = ink[yb0:yb1, x_start + i:x_start + j]
                ys = np.nonzero(region.any(axis=1))[0]
                h = int(ys.max() - ys.min() + 1)
                if h <= 0.25 * dh and 0.4 < w / max(h, 1) < 2.5:
                    best.append((x_start + i, yb0 + int(ys.min()), w, h))
            i = j
        else:
            i += 1
    return sorted(best, key=lambda p: -p[2] * p[3])[:1]


# --------------------------------------------------------------------------
# Leitura dos segmentos
# --------------------------------------------------------------------------
def read_segments(ink, box, digit_w):
    """Fração de tinta em cada uma das 7 regiões do dígito."""
    x, y, w, h = box
    if w < digit_w:                  # mais estreito que o normal: alinha pela direita
        x, w = x + w - digit_w, digit_w
    fracs = []
    for name in "abcdefg":
        x0, x1, y0, y1 = SEGMENT_REGIONS[name]
        rx0, rx1 = int(x + x0 * w), int(x + x1 * w)
        ry0, ry1 = int(y + y0 * h), int(y + y1 * h)
        roi = ink[max(ry0, 0):max(ry1, ry0 + 1), max(rx0, 0):max(rx1, rx0 + 1)]
        fracs.append(float(np.mean(roi > 0)) if roi.size else 0.0)
    return fracs


def classify(fracs):
    """Dígito mais próximo do padrão medido; devolve (dígito, distância, padrão)."""
    on = tuple(int(f > SEGMENT_ON) for f in fracs)
    best, best_d = "?", 99
    for d, pattern in DIGITS.items():
        for p in [pattern] + ALTERNATES.get(d, []):
            dist = sum(a != b for a, b in zip(on, p))
            if dist < best_d:
                best, best_d = d, dist
    return best, best_d, on


# --------------------------------------------------------------------------
# Decodificação completa
# --------------------------------------------------------------------------
def best_shear(ink, top, dh):
    """Inclinação estimada só na faixa dos dígitos (a moldura não atrapalha)."""
    y0, y1 = int(max(0, top)), int(min(ink.shape[0], top + dh))
    _, s = deskew(ink[y0:y1])
    return s


def analyze(img, scale, digit_h=None):
    """Uma passada do pipeline numa escala. Devolve dicionário com tudo que foi achado."""
    g = preprocess(img, scale, digit_h)
    ink = remove_frame(to_ink(g))
    ref = digit_h if digit_h else 0.6 * ink.shape[0]       # chute antes de medir
    kv_list = [f * ref for f in (0.08, 0.15, 0.25, 0.35)]
    row = find_digit_row(ink, kv_list)
    if row is None:
        return {"ink": ink, "shear": 0.0, "digits": []}
    s = best_shear(ink, row[0], row[1])
    ink = shear(ink, s)
    grouping = without_small_blobs(ink, row[1])
    row = find_digit_row(grouping, kv_list, kw=max(3, int(0.05 * row[1])))
    if row is None:
        return {"ink": ink, "shear": s, "digits": []}
    top, dh, members = row
    new_top = refine_top(grouping, members, top, dh)
    dh, top = dh + (top - new_top), new_top
    dh = refine_height(grouping, members, top, dh)
    digits = keep_main_run(collect_digits(grouping, top, dh))
    return {"ink": ink, "shear": s, "digits": digits, "top": top, "dh": dh}


def decode(crop_bgr, debug=False):
    """Decodifica o recorte. Devolve (texto, info, imagem_debug ou None)."""
    # 1ª passada numa escala qualquer só para medir a altura dos dígitos
    scale = 200 / crop_bgr.shape[0]
    r = analyze(crop_bgr, scale)
    if not r["digits"]:
        return "", {"error": "nenhum dígito encontrado"}, (r["ink"] if debug else None)
    # 2ª passada com os dígitos em ~DIGIT_H_TARGET px (kernels e limiares ficam calibrados)
    scale *= DIGIT_H_TARGET / r["dh"]
    r = analyze(crop_bgr, scale, DIGIT_H_TARGET)
    if not r["digits"]:
        return "", {"error": "nenhum dígito encontrado"}, (r["ink"] if debug else None)

    ink, digits, top, dh = r["ink"], r["digits"], r["top"], r["dh"]
    points, minus = find_marks(ink, digits, top, dh)

    ws = sorted(d[2] for d in digits)
    digit_w = int(np.median(ws[len(ws) // 2:]))     # largura típica (exclui "1"s)
    if digit_w < 0.35 * dh:                          # só há "1"s
        digit_w = int(0.55 * dh)

    chars, info = [], {"shear": round(float(r["shear"]), 3), "digit_h": round(dh / scale, 1),
                       "digits": []}
    for b in digits:
        if b[2] < ONE_WIDTH * digit_w:
            d, dist, on = "1", 0, (0, 1, 1, 0, 0, 0, 0)
        else:
            d, dist, on = classify(read_segments(ink, b, digit_w))
        chars.append((b[0] + b[2] / 2, d))      # ordena pelo centro do dígito
        info["digits"].append({"digit": d, "dist": dist,
                               "segments": "".join(c for c, o in zip("abcdefg", on) if o)})
    for p in points:
        chars.append((p[0] + p[2] / 2, "."))
    chars.sort(key=lambda c: c[0])
    text = ("-" if minus else "") + "".join(c for _, c in chars)
    # Incerto se algum dígito não bateu exatamente ou se os dígitos são pequenos demais na
    # imagem original (menos de ~12 px de altura: pouca informação, alta chance de erro)
    info["unsure"] = any(d["dist"] > 0 for d in info["digits"]) or info["digit_h"] < 12

    dbg = None
    if debug:
        dbg = cv2.cvtColor(ink, cv2.COLOR_GRAY2BGR)
        cv2.line(dbg, (0, int(top)), (dbg.shape[1], int(top)), (0, 160, 0), 1)
        cv2.line(dbg, (0, int(top + dh)), (dbg.shape[1], int(top + dh)), (0, 160, 0), 1)
        for b in digits:
            x, y, w, h = b
            if w < digit_w:
                x, w = x + w - digit_w, digit_w
            cv2.rectangle(dbg, (x, y), (x + w, y + h), (0, 255, 0), 1)
            for name in "abcdefg":
                x0, x1, y0, y1 = SEGMENT_REGIONS[name]
                cv2.rectangle(dbg, (int(x + x0 * w), int(y + y0 * h)),
                              (int(x + x1 * w), int(y + y1 * h)), (255, 128, 0), 1)
        for b in points:
            cv2.rectangle(dbg, (b[0], b[1]), (b[0] + b[2], b[1] + b[3]), (0, 0, 255), 2)
        for b in minus:
            cv2.rectangle(dbg, (b[0], b[1]), (b[0] + b[2], b[1] + b[3]), (255, 0, 255), 2)
        cv2.putText(dbg, text, (5, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    return text, info, dbg


# --------------------------------------------------------------------------
# Linha de comando / webcam
# --------------------------------------------------------------------------
def run_files(patterns, debug):
    # O glob é feito aqui porque o cmd/PowerShell do Windows não expande curingas
    files = sorted({f for p in patterns for f in glob.glob(p)})
    if not files:
        print("Nenhum arquivo encontrado.")
    for f in files:
        img = cv2.imread(f)
        if img is None:
            continue
        text, info, dbg = decode(img, debug)
        flag = "  (incerto)" if info.get("unsure") else ""
        print(f"{Path(f).name}: {text}{flag}   {info}")
        if debug and dbg is not None:
            cv2.imwrite(str(Path(f).with_name(Path(f).stem + "_decode.png")), dbg)


def on_mouse(event, x, y, flags, userdata):
    global start_point, current_point, selected_roi, dragging
    if event == cv2.EVENT_LBUTTONDOWN:
        start_point = current_point = (x, y)
        dragging = True
    elif event == cv2.EVENT_MOUSEMOVE and dragging:
        current_point = (x, y)
    elif event == cv2.EVENT_LBUTTONUP and dragging:
        dragging = False
        x1, x2 = sorted((start_point[0], x))
        y1, y2 = sorted((start_point[1], y))
        if x2 - x1 >= 10 and y2 - y1 >= 10:
            selected_roi = (x1, y1, x2 - x1, y2 - y1)
            print(f"Selected display area: {selected_roi}", flush=True)
        else:
            print("Selection too small; drag a larger rectangle.", flush=True)
        start_point = current_point = None


def open_camera(index, width, height):
    camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not camera.isOpened():
        raise SystemExit(f"Could not open webcam {index}")
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    print(f"Webcam resolution: {int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
          f"{int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))}", flush=True)
    return camera


def clamp_roi(roi, shape):
    """Limita o retângulo à imagem (arrastar o mouse para fora da janela dá coordenadas
    negativas ou maiores que o frame, e o recorte sairia vazio ou errado)."""
    x, y, w, h = roi
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(shape[1], x + w), min(shape[0], y + h)
    if x1 - x0 < 10 or y1 - y0 < 10:
        return None
    return x0, y0, x1 - x0, y1 - y0


def median_crop(camera, roi, n_frames):
    """Captura n frames e devolve a mediana do recorte (reduz ruído e cintilação)."""
    x, y, w, h = roi
    crops = []
    for _ in range(n_frames):
        ok, frame = camera.read()
        if ok:
            crops.append(frame[y:y + h, x:x + w])
    if not crops:
        return None
    return np.median(np.stack(crops), axis=0).astype(np.uint8)


def run_camera(args):
    global selected_roi
    CAPTURE_DIR.mkdir(exist_ok=True)
    camera = open_camera(args.camera, args.width, args.height)
    window = "7-seg decoder | drag: select | p: read | r: reset | q: quit"
    result_window = "Decodificacao"   # sem acento: o Windows corrompe títulos não-ASCII
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window, on_mouse)
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                break
            preview = frame.copy()
            if selected_roi is not None:
                x, y, w, h = selected_roi
                cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
            if dragging and start_point and current_point:
                cv2.rectangle(preview, start_point, current_point, (0, 255, 255), 2)
            cv2.imshow(window, preview)
            key = cv2.waitKey(1) & 0xFF
            # q ou fechar a janela no "X" (sem isso o loop continuaria e recriaria a janela)
            if key == ord("q") or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key == ord("r"):
                selected_roi = None
            if key == ord("p"):
                roi = clamp_roi(selected_roi, frame.shape) if selected_roi else None
                if roi is None:
                    print("Select a display area first.", flush=True)
                    continue
                raw = median_crop(camera, roi, args.frames)
                if raw is None:
                    continue
                t0 = time.perf_counter()
                text, info, dbg = decode(raw, debug=True)
                ms = (time.perf_counter() - t0) * 1000
                flag = "  (incerto)" if info.get("unsure") else ""
                print(f"{text}{flag}   [{ms:.1f} ms]   {info}", flush=True)
                cv2.imwrite(str(CAPTURE_DIR / f"{time.strftime('%Y%m%d_%H%M%S')}_raw.png"), raw)
                cv2.imshow(result_window, dbg)
    finally:
        camera.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", nargs="+", help="arquivos (aceita curinga) para decodificar")
    parser.add_argument("--debug", action="store_true", help="salva *_decode.png ao lado")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--frames", type=int, default=8)
    args = parser.parse_args()
    if args.image:
        run_files(args.image, args.debug)
    else:
        run_camera(args)


if __name__ == "__main__":
    main()
