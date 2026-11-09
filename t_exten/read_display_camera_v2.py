"""
Leitor de display de 7 segmentos com pré-processamento do recorte.

Novidades em relação ao read_display_camera.py:
  - pede resolução maior à webcam (o DirectShow costuma abrir em 640x480);
  - no 'p', captura vários frames e tira a mediana do recorte (tira o ruído da webcam);
  - modos de filtro (tecla m), aplicados antes de enviar ao modelo:
      raw     = só a mediana dos frames
      enhance = remove ruído, amplia, contraste local (CLAHE) e nitidez; mantém a cor
      gray    = enhance em cinza com histograma esticado
      flat    = canal verde, iluminação corrigida (divide pelo fundo) e deconvolução (padrão)
      bin     = flat binarizado: dígitos pretos em fundo branco
  - ajuste manual de exposição e foco da webcam;
  - mostra lado a lado o recorte cru e o processado e salva os dois em captures/.

Teclas: arraste = seleciona | p = lê | m = troca o modo | r = limpa | q = sai
        [ e ] = exposição manual -/+ | , e . = foco manual -/+ (se a webcam suportar)

Testar os filtros numa imagem salva, sem webcam e sem chamar a API:
  python read_display_camera_v2.py --test-image captures/xxx_raw.png
"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np

WORKSPACE = "arthurs-workspace-pjgli"
WORKFLOW = "seven-segment-multi-display-reader-1793736667455"
API_KEY = "Fgugzd9PwTSrd4HTF8Nm"
WINDOW = "Display reader | drag: select | p: read | m: mode | [ ]: exposure | , .: focus | r: reset | q: quit"
CROP_WINDOW = "Recorte: cru (esq.) x processado (dir.)"

MODES = ["raw", "enhance", "gray", "flat", "bin"]
CAPTURE_DIR = Path(__file__).resolve().parent / "captures"

# Estado da seleção do retângulo
start_point = None
current_point = None
selected_roi = None  # (x, y, largura, altura)
dragging = False


# --------------------------------------------------------------------------
# Pré-processamento
# --------------------------------------------------------------------------
def upscale(img, target_h=200, max_scale=4.0):
    """Amplia recortes pequenos para que os segmentos tenham mais pixels."""
    h = img.shape[0]
    scale = min(max_scale, target_h / h)
    if scale <= 1.0:
        return img
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def unsharp(img, sigma=2.0, amount=1.0):
    """Realça bordas: img + amount * (img - borrada)."""
    blur = cv2.GaussianBlur(img, (0, 0), sigma)
    return cv2.addWeighted(img, 1.0 + amount, blur, -amount, 0)


def enhance(img):
    """Mantém a cor; melhora contraste e nitidez. Seguro para modelos treinados com fotos."""
    # Non-local means: tira o ruído granulado antes de ampliar (senão ele é ampliado junto)
    img = cv2.fastNlMeansDenoisingColored(img, None, h=7, hColor=7,
                                          templateWindowSize=5, searchWindowSize=15)
    img = upscale(img)
    # Filtro bilateral: suaviza o que sobrou sem borrar as bordas dos segmentos
    img = cv2.bilateralFilter(img, d=7, sigmaColor=30, sigmaSpace=7)
    # CLAHE só no canal de luminância (L do espaço LAB): compensa reflexo/iluminação desigual
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(2, 4))
    l = clahe.apply(l)
    img = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    return unsharp(img, sigma=2.0, amount=0.8)


def to_gray(img):
    g = cv2.cvtColor(enhance(img), cv2.COLOR_BGR2GRAY)
    g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)  # estica o histograma
    return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)


def flatten_background(gray, ratio=0.2):
    """Corrige iluminação desigual: estima o fundo do LCD e divide a imagem por ele.

    O fechamento morfológico (dilatação seguida de erosão) com um kernel maior que a
    espessura de um segmento "apaga" os dígitos escuros e deixa só o fundo iluminado.
    Dividir pela estimativa deixa o fundo ~uniforme, mesmo com reflexo ou sombra.
    """
    k = max(9, int(gray.shape[0] * ratio)) | 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
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


def flat(img):
    """Cinza com iluminação corrigida e desfoque reduzido. Mais robusto a reflexo/sombra."""
    # Canal verde em vez da média: os dígitos são escuros em todos os canais, mas
    # reflexos coloridos (ex.: o LED vermelho refletido no LCD) quase não aparecem no verde.
    # O verde também é o canal com menos ruído no sensor (tem 2x mais pixels no Bayer).
    g = upscale(img)[:, :, 1]
    g = cv2.fastNlMeansDenoising(g, None, h=3)
    g = flatten_background(g)
    return deblur(g)


def binarize(img):
    """Dígitos pretos em fundo branco, feito em cima do modo 'flat'."""
    g = flat(img)
    # Display de backlight (dígito claro em fundo escuro): inverte antes
    if np.median(g) < 127:
        g = 255 - g
    g = cv2.GaussianBlur(g, (5, 5), 0)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Apaga manchas pequenas e tudo que encosta na borda (moldura do display)
    ink = 255 - bw
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    h, w = bw.shape
    x, y, ww, hh, area = (stats[:, i] for i in range(5))
    touches_border = (x == 0) | (y == 0) | (x + ww >= w) | (y + hh >= h)
    erase = (area < (h ** 2) / 1000) | touches_border
    erase[0] = False                                   # o fundo não é apagado
    bw[erase[labels]] = 255                            # uma indexação para todos os componentes
    return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)


def preprocess(img, mode):
    if mode == "raw":
        return img
    if mode == "enhance":
        return enhance(img)
    if mode == "gray":
        return to_gray(img)
    if mode == "flat":
        return cv2.cvtColor(flat(img), cv2.COLOR_GRAY2BGR)
    if mode == "bin":
        return binarize(img)
    raise ValueError(mode)


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


def side_by_side(raw, processed):
    h = processed.shape[0]
    raw_r = cv2.resize(raw, (int(raw.shape[1] * h / raw.shape[0]), h),
                       interpolation=cv2.INTER_NEAREST)
    sep = np.full((h, 6, 3), (0, 255, 0), np.uint8)
    return np.hstack((raw_r, sep, processed))


# --------------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------------
def on_mouse(event, x, y, flags, userdata):
    global start_point, current_point, selected_roi, dragging

    if event == cv2.EVENT_LBUTTONDOWN:
        start_point = (x, y)
        current_point = (x, y)
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
        start_point = None
        current_point = None


def open_camera(index, width, height):
    camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not camera.isOpened():
        raise SystemExit(f"Could not open webcam {index}")
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # permite resoluções altas via USB
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    real_w = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    real_h = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Webcam resolution: {real_w}x{real_h}", flush=True)
    return camera


def run_test_image(path):
    img = cv2.imread(str(path))
    if img is None:
        raise SystemExit(f"Could not read {path}")
    out_dir = Path(path).with_suffix("")
    for mode in MODES:
        out = preprocess(img, mode)
        out_path = f"{out_dir}_{mode}.png"
        cv2.imwrite(out_path, out)
        print("saved", out_path)


def main():
    global selected_roi

    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--frames", type=int, default=8, help="frames para a mediana")
    parser.add_argument("--mode", choices=MODES, default="flat")
    parser.add_argument("--test-image", help="só aplica os filtros numa imagem e salva")
    args = parser.parse_args()

    if args.test_image:
        run_test_image(args.test_image)
        return

    from inference_sdk import InferenceHTTPClient
    client = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)

    mode = args.mode
    CAPTURE_DIR.mkdir(exist_ok=True)
    camera = open_camera(args.camera, args.width, args.height)
    exposure = int(camera.get(cv2.CAP_PROP_EXPOSURE)) or -6
    focus = int(camera.get(cv2.CAP_PROP_FOCUS)) or 0

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW, on_mouse)

    print("Drag a box around the LCD digits, including the sign and decimal.")
    print(f"Press p to read, m to change mode (now: {mode}), r to reselect, q to quit.")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("Could not read a webcam frame.")
                break

            preview = frame.copy()
            if selected_roi is not None:
                x, y, w, h = selected_roi
                cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
            if dragging and start_point is not None and current_point is not None:
                cv2.rectangle(preview, start_point, current_point, (0, 255, 255), 2)
            cv2.putText(preview, f"mode: {mode}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (0, 255, 255), 2)

            cv2.imshow(WINDOW, preview)
            key = cv2.waitKey(1) & 0xFF

            # q ou fechar a janela no "X" (sem isso o loop continuaria e recriaria a janela)
            if key == ord("q") or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break

            if key == ord("r"):
                selected_roi = None
                print("Selection cleared; drag a new box.", flush=True)

            if key in (ord("["), ord("]")):
                exposure += 1 if key == ord("]") else -1
                # Desliga a exposição automática. O valor que significa "manual" varia com o
                # backend e o driver; se a exposição não mudar, a webcam não aceita controle manual
                camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                camera.set(cv2.CAP_PROP_EXPOSURE, exposure)
                print(f"Exposure: {exposure} (lida: {camera.get(cv2.CAP_PROP_EXPOSURE)})", flush=True)

            if key in (ord(","), ord(".")):
                focus = max(0, min(255, focus + (5 if key == ord(".") else -5)))
                camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                camera.set(cv2.CAP_PROP_FOCUS, focus)
                print(f"Focus: {focus} (lido: {camera.get(cv2.CAP_PROP_FOCUS)})", flush=True)

            if key == ord("m"):
                mode = MODES[(MODES.index(mode) + 1) % len(MODES)]
                print(f"Mode: {mode}", flush=True)

            if key == ord("p"):
                roi = clamp_roi(selected_roi, frame.shape) if selected_roi else None
                if roi is None:
                    print("Select a display area first.", flush=True)
                    continue

                raw = median_crop(camera, roi, args.frames)
                if raw is None:
                    print("Could not capture frames.", flush=True)
                    continue
                crop = preprocess(raw, mode)

                stamp = time.strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(str(CAPTURE_DIR / f"{stamp}_raw.png"), raw)
                cv2.imwrite(str(CAPTURE_DIR / f"{stamp}_{mode}.png"), crop)
                cv2.imshow(CROP_WINDOW, side_by_side(raw, crop))

                print(f"Reading captured display (mode: {mode})...", flush=True)
                try:
                    result = client.run_workflow(
                        workspace_name=WORKSPACE,
                        workflow_id=WORKFLOW,
                        images={"image": crop},
                        use_cache=True,
                    )
                    output = result[0] if isinstance(result, list) else result
                    print(output["readings"], flush=True)
                except Exception as error:
                    print(f"Reading failed: {error}", flush=True)

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
