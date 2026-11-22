"""
Leitura automática de displays de multímetros na calibração — API (lógica, sem interface).

Parte do leitor_multimetro.py, com as correções listadas no fim deste texto. O front
(multimeter_calibration_GUI.py) só importa este arquivo.

Etapas do documento de organização e o que usar em cada uma:

  1. Calibração da visualização
       Camera                    webcam; uma thread guarda sempre o último frame (o preview
                                 nunca espera a captura) e median_crop tira a mediana do recorte
       clamp_roi / roi_from_points / crop    retângulo do display
       check_quality             luminosidade, reflexo, contraste e nitidez do recorte
       QualityReference          métricas de uma imagem em condições ideais (salva/carrega JSON)

  2. Configuração da captura
       CaptureConfig             intervalo, limite de imagens, log, unidade, ponto, ciclo, mín/máx

  3. Captura e acompanhamento
       CaptureSession            uma leitura completa por chamada (capture_once)
       CaptureWorker             roda a sessão numa thread, no intervalo fixo, e entrega os
                                 resultados numa fila (o front lê a fila sem travar a janela)
       MotionMonitor             detecta câmera movida em relação ao início
       evaluate_alerts           leitura vazia, salto brusco, qualidade, câmera movida, faixa
       ReadingLogger             grava o log CSV

  Leitor: RoboflowReader (workflow "Seven Segment Multi-Display Reader").

Chave da API do Roboflow (não fica no código). Ordem de busca:
  1. argumento api_key; 2. config.json na pasta do projeto ({"roboflow_api_key": "..."});
  3. variável de ambiente ROBOFLOW_API_KEY.
  O config.json está no .gitignore; config.example.json mostra o formato.

Modo terminal (testa tudo sem front):
  python multimeter_calibration_api.py --interval 2 --max-images 10 --log calibracao_5V --unit V
  (o log é criado na pasta logs; sem --log o nome é leituras_AAAAMMDD_HHMMSS.csv; --no-log desliga)
  python multimeter_calibration_api.py --quality-only      (só seleção + teste de qualidade)

Correções em relação ao leitor_multimetro.py:
  - chave da API removida do código (MissingApiKeyError se não houver);
  - Camera com thread de captura: antes, median_crop segurava a trava por 8 frames e o preview
    travava a cada leitura; também passou a usar só frames novos (sem frame velho do buffer);
  - CaptureSession abria o arquivo de log antes de validar a câmera e a área (vazava o arquivo
    se desse erro); agora abre só depois de tudo validado;
  - a unidade informada pelo operador tem prioridade sobre a que o leitor devolve;
  - save_images (opcional) para não gravar um PNG por leitura.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import queue
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import cv2
import numpy as np

# --------------------------------------------------------------------------
# Configuração do Roboflow
# --------------------------------------------------------------------------
ROBOFLOW_URL = "https://serverless.roboflow.com"
WORKSPACE = "arthurs-workspace-pjgli"
WORKFLOW = "seven-segment-multi-display-reader-1793736667455"
API_KEY_ENV = "ROBOFLOW_API_KEY"
SETTINGS_DIR = Path.home() / ".multimeter_calibration"     # preferências da interface
CONFIG_FILE = Path(__file__).resolve().parent / "config.json"   # chave da API (fora do Git)
CONFIG_KEY = "roboflow_api_key"
LOGS_DIR = Path(__file__).resolve().parent / "logs"             # logs e imagens das capturas

Roi = tuple[int, int, int, int]   # (x, y, largura, altura)


class MissingApiKeyError(RuntimeError):
    """Nenhuma chave do Roboflow encontrada."""


def resolve_log_path(name: str = "", now: Optional[datetime] = None,
                     logs_dir: Path = LOGS_DIR) -> str:
    """Caminho do log, sempre dentro da pasta logs.

    Com nome: usa só o nome do arquivo (sem pastas) e acrescenta .csv se faltar; se o arquivo
    já existir, as leituras são acrescentadas. Sem nome: leituras_AAAAMMDD_HHMMSS.csv (novo).
    """
    now = now or datetime.now()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", Path((name or "").strip()).name).strip(" .")
    if not name:
        name = f"leituras_{now:%Y%m%d_%H%M%S}"
    if not name.lower().endswith(".csv"):
        name += ".csv"
    return str(Path(logs_dir) / name)


def _read_config() -> dict:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_api_key() -> Optional[str]:
    """Chave do config.json (na pasta do projeto) ou da variável de ambiente; None se não houver."""
    key = str(_read_config().get(CONFIG_KEY, "")).strip()
    return key or os.environ.get(API_KEY_ENV, "").strip() or None


def save_api_key(key: str) -> None:
    """Grava a chave no config.json (preserva os outros campos do arquivo)."""
    data = _read_config()
    data[CONFIG_KEY] = key.strip()
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def forget_api_key() -> None:
    data = _read_config()
    if data.pop(CONFIG_KEY, None) is not None:
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ==========================================================================
# Câmera e região de interesse
# ==========================================================================
def clamp_roi(roi: Optional[Roi], frame_shape) -> Optional[Roi]:
    """Limita o retângulo ao frame. Devolve None se ficar menor que 10x10 px.

    Arrastar o mouse para fora da janela gera coordenadas negativas ou maiores que o frame.
    """
    if roi is None:
        return None
    x, y, w, h = roi
    x0, y0 = max(0, int(x)), max(0, int(y))
    x1, y1 = min(frame_shape[1], int(x + w)), min(frame_shape[0], int(y + h))
    if x1 - x0 < 10 or y1 - y0 < 10:
        return None
    return x0, y0, x1 - x0, y1 - y0


def roi_from_points(p1, p2) -> Roi:
    """Retângulo a partir de dois cantos (ex.: clique e soltura do mouse no front)."""
    x1, x2 = sorted((int(p1[0]), int(p2[0])))
    y1, y2 = sorted((int(p1[1]), int(p2[1])))
    return x1, y1, x2 - x1, y2 - y1


def crop(frame: np.ndarray, roi: Roi) -> np.ndarray:
    x, y, w, h = roi
    return frame[y:y + h, x:x + w]


class Camera:
    """Webcam lida por uma thread própria, que guarda sempre o último frame.

        with Camera(0) as cam:
            frame = cam.read()                       # último frame (instantâneo; não altere)
            recorte = cam.median_crop(roi, n_frames=8)   # mediana de n frames NOVOS

    O preview do front e a captura rodam em threads diferentes sem esperar um pelo outro.
    """

    def __init__(self, index: int = 0, width: int = 1920, height: int = 1080,
                 first_frame_timeout: float = 5.0):
        # DirectShow só existe no Windows; nos outros sistemas usa o backend padrão
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        self._cap = cv2.VideoCapture(index, backend)
        if not self._cap.isOpened():
            raise RuntimeError(f"Não foi possível abrir a webcam {index}")
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cond = threading.Condition()
        self._frame: Optional[np.ndarray] = None
        self._seq = 0                      # nº do último frame lido
        self._running = True
        self._thread = threading.Thread(target=self._grab, daemon=True)
        self._thread.start()
        with self._cond:
            got = self._cond.wait_for(lambda: self._frame is not None, first_frame_timeout)
        if not got:
            self.release()
            raise RuntimeError(f"A webcam {index} abriu, mas não entregou imagem")

    def _grab(self):
        while self._running:
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.05)
                continue
            with self._cond:
                self._frame, self._seq = frame, self._seq + 1
                self._cond.notify_all()

    @property
    def resolution(self) -> tuple[int, int]:
        return (int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    def read(self) -> Optional[np.ndarray]:
        """Último frame BGR (somente leitura: não modifique), ou None se ainda não houver."""
        with self._cond:
            return self._frame

    def median_crop(self, roi: Roi, n_frames: int = 8, timeout: float = 5.0) -> Optional[np.ndarray]:
        """Mediana do recorte de n frames novos (tira ruído e cintilação).
        Devolve None se nenhum frame chegar ou o retângulo ficar fora do frame."""
        crops = []
        deadline = time.monotonic() + timeout
        with self._cond:
            last = self._seq
        while len(crops) < max(1, n_frames):
            with self._cond:
                self._cond.wait_for(lambda: self._seq != last or not self._running,
                                    max(0.0, deadline - time.monotonic()))
                if self._seq == last:          # timeout ou câmera fechada
                    break
                frame, last = self._frame, self._seq
            r = clamp_roi(roi, frame.shape)
            if r is None:
                return None
            crops.append(crop(frame, r))
        if not crops:
            return None
        return np.median(np.stack(crops), axis=0).astype(np.uint8)

    def release(self):
        self._running = False
        with self._cond:
            self._cond.notify_all()
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(2)
        self._cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()


# ==========================================================================
# 1. Teste de qualidade da imagem
# ==========================================================================
@dataclass
class QualityThresholds:
    """Limites absolutos, calibrados com as capturas do projeto (fotos boas x ruins).

    background_min:   nível do fundo do LCD (percentil 95 do cinza, 0-255). Fotos escuras ~60,
                      boas ~120.
    background_max:   acima disso a imagem está estourada.
    contrast_min:     diferença entre fundo e dígitos (p95 - p5). Ruins ~40-48, boas ~73.
    saturated_max:    % de pixels estourados (>= 245): reflexo branco da luz.
    colored_max:      % de pixels claros com cor diferente da do LCD: reflexo de LED/lâmpada.
                      Fotos sem reflexo: 0%; com o reflexo do LED vermelho: 1.7-3.1%.
    sharpness_min:    nitidez (gradiente máximo / contraste, com o recorte reduzido a 40 px).
                      Limite folgado, só pega desfoque grosseiro; a comparação com a referência
                      é bem mais sensível.
    """
    background_min: float = 65
    background_max: float = 245
    contrast_min: float = 50
    saturated_max: float = 1.0
    colored_max: float = 0.5
    sharpness_min: float = 1.3
    # Tolerâncias em relação à imagem de referência (frações)
    ref_background_tol: float = 0.25    # fundo pode variar ±25%
    ref_contrast_min: float = 0.75      # contraste >= 75% do da referência
    ref_sharpness_min: float = 0.80     # nitidez >= 80% da referência
    ref_reflection_margin: float = 0.5  # reflexo pode aumentar até +0.5 ponto percentual


@dataclass
class QualityIssue:
    code: str          # "escura", "estourada", "contraste", "reflexo", "desfocada"
    message: str       # o que está errado
    suggestion: str    # o que o operador deve fazer


@dataclass
class QualityReport:
    metrics: dict[str, float]
    issues: list[QualityIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def summary(self) -> str:
        m = self.metrics
        base = (f"fundo={m['background']:.0f} contraste={m['contrast']:.0f} "
                f"reflexo={m['saturated'] + m['colored']:.2f}% nitidez={m['sharpness']:.2f}")
        if self.ok:
            return "Qualidade OK  (" + base + ")"
        return "; ".join(i.message for i in self.issues) + "  (" + base + ")"


def measure_quality(img: np.ndarray) -> dict[str, float]:
    """Métricas do recorte: background, contrast, saturated, colored, sharpness."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    p5, p95 = np.percentile(gray, [5, 95])
    contrast = float(p95 - p5)
    # Reflexo: só no miolo do recorte (as bordas costumam pegar a moldura ou o que está fora do
    # multímetro). Branco = pixels estourados. Colorido = pixels claros (reflexo soma luz) com
    # cor bem diferente da cor dominante do LCD (cromaticidade r,g,b normalizada pela soma).
    h, w = gray.shape
    my, mx = int(h * 0.06), int(w * 0.06)
    inner, ginner = img[my:h - my, mx:w - mx], gray[my:h - my, mx:w - mx]
    saturated = float(np.mean(ginner >= 245) * 100)
    f = inner.astype(np.float32) + 1
    chrom = f / f.sum(axis=2, keepdims=True)
    dist = np.linalg.norm(chrom - np.median(chrom.reshape(-1, 3), axis=0), axis=2)
    colored = float(np.mean((dist > 0.08) & (ginner >= np.median(ginner))) * 100)
    # Nitidez independente do tamanho do recorte: reduz a 40 px de altura (só reduz, nunca
    # amplia, para a ampliação não mascarar o desfoque) e divide pelo contraste
    g = gray.astype(np.float32)
    s = 40 / g.shape[0]
    if s < 1:
        g = cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    sharpness = float(np.percentile(np.hypot(gx, gy), 99) / max(contrast, 1.0))
    return {"background": float(p95), "contrast": contrast, "saturated": saturated,
            "colored": colored, "sharpness": sharpness}


@dataclass
class QualityReference:
    """Métricas de uma imagem em condições ideais, para comparar depois."""
    metrics: dict[str, float]

    @classmethod
    def from_image(cls, img: np.ndarray) -> "QualityReference":
        return cls(measure_quality(img))

    def save(self, path) -> None:
        Path(path).write_text(json.dumps(self.metrics, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path) -> "QualityReference":
        metrics = json.loads(Path(path).read_text(encoding="utf-8"))
        missing = {"background", "contrast", "saturated", "colored", "sharpness"} - set(metrics)
        if missing:
            raise ValueError("Arquivo de referência inválido (faltam: " + ", ".join(sorted(missing)) + ")")
        return cls({k: float(v) for k, v in metrics.items()})


def check_quality(img: np.ndarray, reference: Optional[QualityReference] = None,
                  thresholds: QualityThresholds = QualityThresholds()) -> QualityReport:
    """Teste de qualidade do recorte: limites absolutos e, se houver, comparação com a
    referência. Cada problema vem com uma sugestão para o operador."""
    m = measure_quality(img)
    t = thresholds
    issues: list[QualityIssue] = []

    def add(code, message, suggestion):
        if code not in {i.code for i in issues}:
            issues.append(QualityIssue(code, message, suggestion))

    # Limites absolutos
    if m["background"] < t.background_min:
        add("escura", "Imagem escura", "Aumente a iluminação do display ou a exposição da câmera")
    if m["background"] > t.background_max:
        add("estourada", "Imagem estourada", "Diminua a iluminação ou a exposição da câmera")
    if m["contrast"] < t.contrast_min:
        add("contraste", "Pouco contraste entre dígitos e fundo",
            "Melhore a iluminação e posicione a câmera de frente para o display")
    if m["saturated"] > t.saturated_max or m["colored"] > t.colored_max:
        add("reflexo", "Reflexo no display",
            "Mude o ângulo da luz ou da câmera; use luz difusa e lateral")
    if m["sharpness"] < t.sharpness_min:
        add("desfocada", "Imagem desfocada",
            "Ajuste o foco ou afaste a câmera (webcams de foco fixo focam a partir de ~40 cm)")

    # Comparação com a referência
    if reference is not None:
        r = reference.metrics
        if m["background"] < r["background"] * (1 - t.ref_background_tol):
            add("escura", "Mais escura que a referência",
                "Aumente a iluminação até chegar perto da imagem de referência")
        if m["background"] > r["background"] * (1 + t.ref_background_tol):
            add("estourada", "Mais clara que a referência",
                "Diminua a iluminação até chegar perto da imagem de referência")
        if m["contrast"] < r["contrast"] * t.ref_contrast_min:
            add("contraste", "Contraste menor que o da referência",
                "Verifique iluminação, ângulo e reflexos")
        if (m["saturated"] + m["colored"]) > (r["saturated"] + r["colored"]) + t.ref_reflection_margin:
            add("reflexo", "Mais reflexo que na referência",
                "Mude o ângulo da luz ou da câmera")
        if m["sharpness"] < r["sharpness"] * t.ref_sharpness_min:
            add("desfocada", "Menos nítida que a referência",
                "Ajuste o foco ou a distância da câmera")
    return QualityReport(m, issues)


# ==========================================================================
# Câmera movida
# ==========================================================================
class MotionMonitor:
    """Detecta se a câmera (ou o multímetro) saiu do lugar desde o início da captura.

    Guarda a região do display com uma margem em volta (pega a carcaça do multímetro, que
    não muda) e procura essa região no frame atual (correlação normalizada). Se o melhor
    encaixe se deslocou ou a semelhança caiu, a câmera provavelmente foi movida.
    Os dígitos mudam entre leituras, mas a margem em volta mantém o encaixe estável.
    """

    def __init__(self, reference_frame: np.ndarray, roi: Roi, margin: float = 0.3,
                 max_shift: float = 0.15, min_score: float = 0.5):
        x, y, w, h = roi
        mx, my = int(w * margin), int(h * margin)
        H, W = reference_frame.shape[:2]
        self.x0, self.y0 = max(0, x - mx), max(0, y - my)
        self.x1, self.y1 = min(W, x + w + mx), min(H, y + h + my)
        gray = cv2.cvtColor(reference_frame, cv2.COLOR_BGR2GRAY)
        self.template = gray[self.y0:self.y1, self.x0:self.x1]
        self.max_shift_px = max(5.0, max_shift * h)     # deslocamento tolerado
        self.min_score = min_score
        self.search = int(max(w, h) * 0.5)               # quanto procurar em volta

    def check(self, frame: np.ndarray) -> bool:
        """True se a câmera (ou o multímetro) parece ter sido movida."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        H, W = gray.shape
        sx0, sy0 = max(0, self.x0 - self.search), max(0, self.y0 - self.search)
        sx1, sy1 = min(W, self.x1 + self.search), min(H, self.y1 + self.search)
        region = gray[sy0:sy1, sx0:sx1]
        th, tw = self.template.shape
        if region.shape[0] < th or region.shape[1] < tw:
            return True
        res = cv2.matchTemplate(region, self.template, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(res)
        dx, dy = (sx0 + loc[0]) - self.x0, (sy0 + loc[1]) - self.y0
        return math.hypot(dx, dy) > self.max_shift_px or score < self.min_score


# ==========================================================================
# Leitor (Roboflow)
# ==========================================================================
@dataclass
class Reading:
    value: Optional[float]   # número lido (None se vazio/ilegível)
    text: str                # como apareceu no display (ex.: "-03.2")
    unit: str                # unidade, se o workflow devolver (senão "")
    raw: Any                 # resposta bruta do campo readings
    error: str = ""          # erro da requisição, se houver

    @property
    def decimals(self) -> int:
        """Casas decimais do texto lido (resolução do display), ex.: "05.5" -> 1."""
        m = re.search(r"[.,](\d+)", self.text)
        return len(m.group(1)) if m else 0


_NUMBER_RE = re.compile(r"([-+]?\s*\d+(?:[.,]\d+)?)\s*([a-zA-ZµμΩ°%]*)")


def parse_readings(readings: Any) -> tuple[Optional[float], str, str]:
    """Extrai (valor, texto, unidade) do campo 'readings' do workflow.

    Aceita os formatos mais prováveis: texto ("-03.2", "12.5 mV"), número, lista (usa o
    primeiro item legível) ou dicionário (procura chaves como value/reading/text e unit).
    """
    if readings is None:
        return None, "", ""
    if isinstance(readings, bool):
        return None, str(readings), ""
    if isinstance(readings, (int, float)):
        return float(readings), str(readings), ""
    if isinstance(readings, str):
        m = _NUMBER_RE.search(readings)
        if not m:
            return None, readings.strip(), ""
        num = m.group(1).replace(" ", "").replace(",", ".")
        try:
            return float(num), m.group(1).replace(" ", ""), m.group(2)
        except ValueError:
            return None, readings.strip(), ""
    if isinstance(readings, (list, tuple)):
        for item in readings:
            value, text, unit = parse_readings(item)
            if value is not None:
                return value, text, unit
        return None, "", ""
    if isinstance(readings, dict):
        unit = ""
        for k in ("unit", "units", "unidade"):
            if isinstance(readings.get(k), str):
                unit = readings[k]
        for k in ("value", "reading", "readings", "text", "display", "number", "prediction"):
            if k in readings:
                value, text, u = parse_readings(readings[k])
                if value is not None or text:
                    return value, text, unit or u
        return parse_readings(list(readings.values()))
    return None, str(readings), ""


class RoboflowReader:
    """Envia o recorte ao workflow do Roboflow e interpreta a resposta.

        reader = RoboflowReader()          # chave: ver load_api_key()
        leitura = reader.read(img)         # -> Reading

    Levanta MissingApiKeyError se não houver chave e ImportError se o inference-sdk faltar.
    """

    def __init__(self, api_key: Optional[str] = None, workspace: str = WORKSPACE,
                 workflow: str = WORKFLOW, api_url: str = ROBOFLOW_URL):
        key = (api_key or "").strip() or load_api_key()
        if not key:
            raise MissingApiKeyError(
                f"Chave do Roboflow não encontrada. Coloque-a em {CONFIG_FILE.name} "
                f'({{"{CONFIG_KEY}": "..."}}), defina a variável {API_KEY_ENV} ou informe a chave na interface.')
        from inference_sdk import InferenceHTTPClient    # só exigido quem usa o leitor
        self.client = InferenceHTTPClient(api_url=api_url, api_key=key)
        self.workspace, self.workflow = workspace, workflow

    def read(self, img: np.ndarray) -> Reading:
        try:
            result = self.client.run_workflow(workspace_name=self.workspace,
                                              workflow_id=self.workflow,
                                              images={"image": img}, use_cache=True)
            output = result[0] if isinstance(result, list) and result else result
            raw = output.get("readings") if isinstance(output, dict) else output
        except Exception as error:                     # rede, chave, limite de uso...
            return Reading(None, "", "", None, error=f"{type(error).__name__}: {error}")
        value, text, unit = parse_readings(raw)
        return Reading(value, text, unit, raw)


# ==========================================================================
# 2. Configuração da captura
# ==========================================================================
VALUE_OPS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
             ">": lambda a, b: a > b, "<": lambda a, b: a < b}


@dataclass
class ValueAlert:
    """Alerta definido pelo operador: avisa quando a leitura satisfaz a condição.
    Ex.: ValueAlert(">=", 5.0) avisa quando a leitura for maior ou igual a 5."""
    op: str            # ">=", "<=", ">" ou "<"
    threshold: float

    def matches(self, value: float) -> bool:
        return VALUE_OPS[self.op](value, self.threshold)

    def describe(self) -> str:
        return f"leitura {self.op} {self.threshold:g}"


@dataclass
class CaptureConfig:
    interval_s: float = 2.0                  # intervalo fixo entre capturas
    max_images: int = 10                     # limite de imagens (0 = sem limite)
    log_path: Optional[str] = None           # arquivo CSV (ver resolve_log_path); None = sem log
    unit: str = ""                           # unidade informada pelo operador (ex.: "V")
    calibration_point: Optional[str] = None  # opcional
    cycle: Optional[str] = None              # opcional
    min_expected: Optional[float] = None     # opcional: alerta se a leitura sair da faixa
    max_expected: Optional[float] = None
    value_alerts: list = field(default_factory=list)   # lista de ValueAlert (qualquer quantidade)
    n_frames: int = 8                       # frames na mediana do recorte
    quality_every: int = 5                   # teste de qualidade a cada N capturas (1 = toda)
    motion_every: int = 5                    # verificação de câmera movida a cada N capturas
    max_jump_rel: float = 0.2                # salto brusco: variação > 20% do valor anterior
    max_jump_abs: Optional[float] = None     # se definido, substitui o relativo (ex.: 0.5 V)
    save_images: bool = True                 # salvar o recorte de cada leitura
    images_dir: Optional[str] = None         # onde salvar os recortes (padrão: ao lado do log)

    def validate(self) -> list[str]:
        """Problemas na configuração (lista vazia = ok). Útil para o front validar o formulário."""
        errors = []
        if self.interval_s <= 0:
            errors.append("O intervalo deve ser maior que zero.")
        if self.max_images < 0:
            errors.append("O limite de imagens não pode ser negativo.")
        if self.n_frames < 1:
            errors.append("A mediana precisa de pelo menos 1 frame.")
        if self.max_jump_rel < 0 or (self.max_jump_abs is not None and self.max_jump_abs < 0):
            errors.append("O limite de salto brusco não pode ser negativo.")
        if (self.min_expected is not None and self.max_expected is not None
                and self.min_expected > self.max_expected):
            errors.append("O mínimo esperado é maior que o máximo.")
        for rule in self.value_alerts:
            if rule.op not in VALUE_OPS or not math.isfinite(rule.threshold):
                errors.append(f"Alerta por valor inválido: {rule.op} {rule.threshold}.")
        return errors


# ==========================================================================
# 3. Alertas, log e sessão de captura
# ==========================================================================
@dataclass
class Alert:
    code: str      # "leitura_vazia", "salto_brusco", "casas_decimais", "qualidade",
                   # "camera_movida", "fora_da_faixa", "alerta_valor"
    message: str


def evaluate_alerts(reading: Reading, previous: Optional[Reading], config: CaptureConfig,
                    quality: Optional[QualityReport] = None,
                    moved: Optional[bool] = None) -> list[Alert]:
    """Alertas da leitura atual. 'quality' e 'moved' só entram quando foram verificados."""
    alerts = []
    if reading.value is None:
        detail = f" ({reading.error})" if reading.error else ""
        alerts.append(Alert("leitura_vazia", "Leitura vazia ou ilegível" + detail))
    if reading.value is not None and previous is not None and previous.value is not None:
        delta = abs(reading.value - previous.value)
        if config.max_jump_abs is not None:
            limit = config.max_jump_abs
        else:
            # Relativo ao valor anterior, com piso de 5 contagens da resolução do display
            # (perto de zero a variação relativa explode: 0.1 -> 0.2 seria "100%")
            floor = 5 * 10 ** -max(reading.decimals, previous.decimals)
            limit = max(config.max_jump_rel * abs(previous.value), floor)
        if delta > limit:
            alerts.append(Alert("salto_brusco",
                                f"Salto brusco: {previous.text} -> {reading.text}"))
        # Ponto decimal perdido ou trocado pelo leitor (ex.: display 37.9 lido como "379").
        # Pode ser legítimo se o multímetro trocar de escala sozinho; por isso só "duvidosa".
        if reading.decimals != previous.decimals:
            alerts.append(Alert("casas_decimais",
                                f"Casas decimais mudaram: {previous.text} -> {reading.text}"))
    if quality is not None and not quality.ok:
        alerts.append(Alert("qualidade", "Qualidade: " + ", ".join(i.message for i in quality.issues)))
    if moved:
        alerts.append(Alert("camera_movida", "Câmera ou multímetro possivelmente movido"))
    if reading.value is not None:
        if config.min_expected is not None and reading.value < config.min_expected:
            alerts.append(Alert("fora_da_faixa", f"Abaixo do mínimo ({config.min_expected:g})"))
        if config.max_expected is not None and reading.value > config.max_expected:
            alerts.append(Alert("fora_da_faixa", f"Acima do máximo ({config.max_expected:g})"))
        for rule in config.value_alerts:
            if rule.matches(reading.value):
                alerts.append(Alert("alerta_valor",
                                    f"Alerta de valor: {rule.describe()} (lido {reading.text})"))
    return alerts


def reading_status(reading: Reading, alerts: list[Alert]) -> str:
    """'falha' sem número; 'duvidosa' com qualquer alerta; 'ok' caso contrário."""
    if reading.value is None:
        return "falha"
    return "duvidosa" if alerts else "ok"


def format_number(reading: Reading) -> str:
    """Número para o log, com as casas decimais do display. "-00.0" vira "0.0" (zero sem sinal)."""
    if reading.value is None:
        return ""
    text = f"{reading.value:.{reading.decimals}f}"
    return text[1:] if text.startswith("-") and float(text) == 0 else text


def raw_text(reading: Reading, limit: int = 300) -> str:
    """Resposta bruta do leitor para o log (texto direto; outros tipos em JSON), ou o erro."""
    if reading.raw is None:
        return reading.error
    if isinstance(reading.raw, str):
        return reading.raw[:limit]
    return json.dumps(reading.raw, ensure_ascii=False, default=str)[:limit]


LOG_COLUMNS = ["tempo", "numero", "unidade", "ponto_calibracao", "ciclo", "status",
               "imagem", "alertas", "leitura_bruta"]


class ReadingLogger:
    """Log CSV. Separador ';' e ponto decimal; UTF-8 com BOM para o Excel mostrar os acentos.
    Se o arquivo já existir, as linhas são acrescentadas (o cabeçalho não se repete)."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists() or self.path.stat().st_size == 0
        self._file = open(self.path, "a", newline="", encoding="utf-8-sig" if new else "utf-8")
        self._writer = csv.writer(self._file, delimiter=";")
        if new:
            self._writer.writerow(LOG_COLUMNS)
            self._file.flush()

    def write(self, row: dict) -> None:
        self._writer.writerow(["" if row.get(c) is None else row.get(c) for c in LOG_COLUMNS])
        self._file.flush()          # cada linha vai para o disco na hora (não perde se travar)

    def close(self):
        self._file.close()


@dataclass
class CaptureResult:
    index: int                       # nº da captura (1, 2, ...)
    timestamp: datetime
    reading: Reading
    unit: str                        # unidade final (da configuração ou do leitor)
    status: str                      # "ok", "duvidosa", "falha"
    alerts: list[Alert]
    quality: Optional[QualityReport]  # None quando não foi verificada nesta captura
    moved: Optional[bool]             # idem
    image_path: str                   # "" se não salvou a imagem

    def line(self) -> str:
        """Resumo em uma linha (terminal / barra de status)."""
        val = self.reading.text or "—"
        unit = f" {self.unit}" if self.unit else ""
        al = ("  ! " + " | ".join(a.message for a in self.alerts)) if self.alerts else ""
        return f"[{self.index}] {self.timestamp:%H:%M:%S}  {val}{unit}  ({self.status}){al}"


class CaptureSession:
    """Uma sessão de captura: cada capture_once() faz uma leitura completa.

    recorte (mediana de frames) -> leitor -> qualidade/câmera movida (periódicos)
    -> alertas -> salva imagem -> grava no log.
    """

    def __init__(self, camera: Camera, reader, config: CaptureConfig, roi: Roi,
                 quality_reference: Optional[QualityReference] = None,
                 thresholds: QualityThresholds = QualityThresholds()):
        errors = config.validate()
        if errors:
            raise ValueError(" ".join(errors))
        frame = camera.read()
        if frame is None:
            raise RuntimeError("Não foi possível ler um frame da câmera.")
        self.roi = clamp_roi(roi, frame.shape)
        if self.roi is None:
            raise ValueError("Área do display inválida (fora do frame ou muito pequena).")
        self.camera, self.reader, self.config = camera, reader, config
        self.quality_reference, self.thresholds = quality_reference, thresholds
        self.count = 0
        self.previous: Optional[Reading] = None   # última leitura aceita (referência do salto)
        self._pending: Optional[Reading] = None   # leitura que saltou, aguardando confirmação
        self.started = datetime.now()
        log = Path(config.log_path) if config.log_path else None
        self.images_dir: Optional[Path] = None
        if config.save_images:
            if config.images_dir:
                self.images_dir = Path(config.images_dir)
            else:
                base, stem = (log.parent, log.stem) if log else (LOGS_DIR, "leituras")
                # nome automático do log já traz data e hora; não repete
                suffix = "" if re.search(r"\d{8}_\d{6}$", stem) else f"_{self.started:%Y%m%d_%H%M%S}"
                self.images_dir = base / f"imagens_{stem}{suffix}"
            self.images_dir.mkdir(parents=True, exist_ok=True)
        self.motion = MotionMonitor(frame, self.roi)
        # por último: só abre depois de tudo validado; sem log_path não grava CSV
        self.logger: Optional[ReadingLogger] = ReadingLogger(log) if log else None

    @property
    def finished(self) -> bool:
        return self.config.max_images > 0 and self.count >= self.config.max_images

    def capture_once(self) -> CaptureResult:
        cfg = self.config
        self.count += 1
        now = datetime.now()
        raw = self.camera.median_crop(self.roi, cfg.n_frames)
        if raw is None:
            reading = Reading(None, "", "", None, error="falha ao capturar a imagem")
        else:
            reading = self.reader.read(raw)

        # Verificações periódicas (a 1ª captura sempre verifica)
        quality = moved = None
        periodic = lambda every: every > 0 and (self.count - 1) % every == 0
        if raw is not None and periodic(cfg.quality_every):
            quality = check_quality(raw, self.quality_reference, self.thresholds)
        if periodic(cfg.motion_every):
            frame = self.camera.read()
            if frame is not None:
                moved = self.motion.check(frame)

        alerts = evaluate_alerts(reading, self.previous, cfg, quality, moved)
        # Salto brusco: um valor espúrio isolado é marcado, mas não vira a nova referência
        # (senão a leitura normal seguinte também seria "salto"). Se a leitura seguinte
        # confirmar o novo patamar, ele é aceito sem alerta (mudança real de valor).
        jumped = any(a.code == "salto_brusco" for a in alerts)
        if jumped and self._pending is not None and not any(
                a.code == "salto_brusco" for a in evaluate_alerts(reading, self._pending, cfg)):
            alerts = [a for a in alerts if a.code != "salto_brusco"]
            jumped = False
        status = reading_status(reading, alerts)
        unit = cfg.unit or reading.unit          # o que o operador informou tem prioridade

        image_path = ""
        if raw is not None and self.images_dir is not None:
            p = self.images_dir / f"{self.count:04d}_{now:%H%M%S}.png"
            if cv2.imwrite(str(p), raw):
                image_path = str(p)

        if self.logger:
            self.logger.write({
                "tempo": now.strftime("%Y-%m-%d %H:%M:%S"),
                "numero": format_number(reading),
                "unidade": unit,
                "ponto_calibracao": cfg.calibration_point,
                "ciclo": cfg.cycle,
                "status": status,
                "imagem": image_path,
                "alertas": " | ".join(a.message for a in alerts),
                "leitura_bruta": raw_text(reading),
            })
        if reading.value is not None:
            if jumped:
                self._pending = reading
            else:
                self.previous, self._pending = reading, None
        return CaptureResult(self.count, now, reading, unit, status, alerts, quality, moved,
                             image_path)

    def close(self):
        if self.logger:
            self.logger.close()


class CaptureWorker(threading.Thread):
    """Roda a sessão numa thread, no intervalo fixo, até o limite de imagens ou stop().

    Os resultados vão para a fila `results` (CaptureResult); ao terminar, chega None.
    O Tkinter não pode ser mexido de outra thread: o front lê a fila com root.after().

        worker = CaptureWorker(session)
        worker.start()
        ...  # no front: while not worker.results.empty(): r = worker.results.get_nowait()
        worker.stop()
    """

    def __init__(self, session: CaptureSession,
                 on_result: Optional[Callable[[CaptureResult], None]] = None):
        super().__init__(daemon=True)
        self.session = session
        self.on_result = on_result
        self.results: "queue.Queue[Optional[CaptureResult]]" = queue.Queue()
        self.error: Optional[BaseException] = None
        self._stop_event = threading.Event()   # "_stop" é nome interno do Thread

    def stop(self):
        self._stop_event.set()

    def run(self):
        next_t = time.monotonic()
        try:
            while not self._stop_event.is_set() and not self.session.finished:
                result = self.session.capture_once()
                self.results.put(result)
                if self.on_result:
                    self.on_result(result)
                # Intervalo fixo medido entre inícios de captura (não acumula o atraso da leitura)
                next_t += self.session.config.interval_s
                self._stop_event.wait(max(0.0, next_t - time.monotonic()))
        except BaseException as error:    # repassa ao front em vez de morrer em silêncio
            self.error = error
        finally:
            self.session.close()
            self.results.put(None)


# ==========================================================================
# Modo terminal
# ==========================================================================
def select_roi_window(camera: Camera, title: str = "Selecione o display") -> Optional[Roi]:
    """Seleção do display numa janela do OpenCV (para testar sem o front).
    Arraste um retângulo; Enter/espaço confirma, r limpa, q/Esc cancela."""
    state = {"start": None, "cur": None, "roi": None, "drag": False}

    def on_mouse(event, x, y, flags, _):
        if event == cv2.EVENT_LBUTTONDOWN:
            state.update(start=(x, y), cur=(x, y), drag=True)
        elif event == cv2.EVENT_MOUSEMOVE and state["drag"]:
            state["cur"] = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and state["drag"]:
            state.update(roi=roi_from_points(state["start"], (x, y)), drag=False)

    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(title, on_mouse)
    try:
        while True:
            frame = camera.read()
            if frame is None:
                return None
            view = frame.copy()
            r = clamp_roi(state["roi"], frame.shape)
            if r:
                x, y, w, h = r
                cv2.rectangle(view, (x, y), (x + w, y + h), (0, 255, 0), 2)
                rep = check_quality(crop(frame, r))
                color = (0, 200, 0) if rep.ok else (0, 0, 255)
                cv2.putText(view, rep.summary()[:90], (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, color, 2)
            if state["drag"] and state["start"] and state["cur"]:
                cv2.rectangle(view, state["start"], state["cur"], (0, 255, 255), 2)
            cv2.imshow(title, view)
            key = cv2.waitKey(1) & 0xFF
            if key in (13, 32) and r:
                return r
            if key == ord("r"):
                state["roi"] = None
            if key in (ord("q"), 27) or cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                return None
    finally:
        cv2.destroyWindow(title)


def main():
    p = argparse.ArgumentParser(description="Leitura automática do display do multímetro")
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--interval", type=float, default=2.0, help="segundos entre capturas")
    p.add_argument("--max-images", type=int, default=10, help="0 = sem limite (Ctrl+C para)")
    p.add_argument("--log", default="", help="nome do arquivo (criado na pasta logs); em branco: "
                                              "leituras_AAAAMMDD_HHMMSS.csv")
    p.add_argument("--no-log", action="store_true", help="não gravar o log CSV")
    p.add_argument("--unit", default="")
    p.add_argument("--point", help="ponto de calibração")
    p.add_argument("--cycle", help="ciclo")
    p.add_argument("--min", type=float, dest="min_expected")
    p.add_argument("--max", type=float, dest="max_expected")
    p.add_argument("--no-images", action="store_true", help="não salvar o recorte de cada leitura")
    p.add_argument("--reference", help="JSON de referência de qualidade (carrega se existir; "
                                       "senão pergunta se quer salvar o atual)")
    p.add_argument("--quality-only", action="store_true", help="só seleção + teste de qualidade")
    a = p.parse_args()

    with Camera(a.camera, a.width, a.height) as cam:
        print(f"Webcam: {cam.resolution[0]}x{cam.resolution[1]}")
        print("1) Arraste um retângulo em volta do display e confirme com Enter.")
        roi = select_roi_window(cam)
        if roi is None:
            print("Cancelado.")
            return
        sample = cam.median_crop(roi, 8)
        if sample is None:
            print("Não foi possível capturar o recorte.")
            return
        reference = None
        if a.reference and Path(a.reference).exists():
            reference = QualityReference.load(a.reference)
            print(f"Referência carregada de {a.reference}")
        report = check_quality(sample, reference)
        print("Teste de qualidade:", report.summary())
        for issue in report.issues:
            print(f"  - {issue.message}: {issue.suggestion}")
        if a.reference and reference is None:
            if input("Salvar esta imagem como referência de qualidade? [s/N] ").lower() == "s":
                QualityReference.from_image(sample).save(a.reference)
                print(f"Referência salva em {a.reference}")
        if a.quality_only:
            return

        cfg = CaptureConfig(interval_s=a.interval, max_images=a.max_images, log_path=None if a.no_log else resolve_log_path(a.log),
                            unit=a.unit, calibration_point=a.point, cycle=a.cycle,
                            min_expected=a.min_expected, max_expected=a.max_expected,
                            save_images=not a.no_images)
        try:
            session = CaptureSession(cam, RoboflowReader(), cfg, roi, reference)
        except (MissingApiKeyError, ImportError, ValueError, RuntimeError) as error:
            print("Erro:", error)
            return
        print(f"2) Capturando a cada {cfg.interval_s:g} s "
              f"({'sem limite' if not cfg.max_images else f'{cfg.max_images} imagens'}). "
              f"Log: {cfg.log_path or 'desligado'}  (Ctrl+C para parar)")
        worker = CaptureWorker(session, on_result=lambda r: print(r.line(), flush=True))
        worker.start()
        try:
            while worker.is_alive():
                worker.join(0.2)
        except KeyboardInterrupt:
            worker.stop()
            worker.join()
        if worker.error:
            print("Erro na captura:", worker.error)
        where = f"; imagens em {session.images_dir}" if session.images_dir else ""
        saved = f"gravadas em {cfg.log_path}" if cfg.log_path else "feitas (sem log)"
        print(f"Fim. {session.count} leituras {saved}{where}")


if __name__ == "__main__":
    main()
