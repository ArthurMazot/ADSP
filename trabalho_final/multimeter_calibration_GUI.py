"""
Leitura automática de displays de multímetros na calibração — interface (Tkinter).

Usa a lógica de multimeter_calibration_api.py. Três etapas, uma em cada aba:

  1. Visualização : selecione o display no preview (arraste um retângulo). O teste de qualidade
                    (luminosidade, reflexo, contraste e nitidez) roda ao vivo e pode ser
                    comparado a uma imagem de referência em condições ideais.
  2. Configuração : intervalo, limite de imagens, arquivo de log, unidade, ponto de calibração,
                    ciclo, faixa esperada (opcional) e chave do Roboflow.
  3. Captura      : iniciar/parar, valor lido, alertas e tabela das leituras.

A captura roda numa thread (CaptureWorker); a janela só lê a fila de resultados com after().

    python multimeter_calibration_GUI.py          (ou: python run.py)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from collections import deque
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

import cv2
import numpy as np

import multimeter_calibration_api as api

# --------------------------------------------------------------------------
# Tema: cinza, azul e preto
# --------------------------------------------------------------------------
BLACK = "#0b0d12"        # fundo da janela e do preview
PANEL = "#171b22"        # painéis (cinza escuro)
FIELD = "#0f1218"        # campos de texto, tabelas
BTN = "#2a303b"          # botão (cinza)
BTN_HOVER = "#34507f"    # botão com o mouse em cima (azul acinzentado)
BORDER = "#363d4a"
FG = "#d7dce4"
MUTED = "#8a93a3"
BLUE = "#2f6fed"
BLUE_HOVER = "#4a86ff"
BLUE_PRESS = "#1c4fb8"
BLUE_LIGHT = "#6cb2ff"
AMBER = "#e3b341"        # só para alertas
RED = "#f0616d"          # só para falhas
DISABLED_BG = "#20252e"

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_BIG = ("Consolas", 44, "bold")

STATUS_COLOR = {"ok": BLUE_LIGHT, "duvidosa": AMBER, "falha": RED}
STATUS_LABEL = {"ok": "OK", "duvidosa": "DUVIDOSA", "falha": "FALHA"}
RULE_OPS = {"maior ou igual a  (≥)": ">=", "menor ou igual a  (≤)": "<=",
            "maior que  (>)": ">", "menor que  (<)": "<"}
RULE_SYMBOL = {">=": "≥", "<=": "≤", ">": ">", "<": "<"}
UNITS = ["V", "mV", "A", "mA", "µA", "Ω", "kΩ", "MΩ", "Hz", "°C", "F", "nF"]

SETTINGS_FILE = api.SETTINGS_DIR / "gui_settings.json"
LIVE_BUFFER = 5          # frames usados na mediana do teste de qualidade ao vivo
PREVIEW_MS = 50


def apply_theme(root: tk.Tk) -> None:
    root.configure(bg=BLACK)
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=PANEL, foreground=FG, fieldbackground=FIELD, bordercolor=BORDER,
                lightcolor=PANEL, darkcolor=PANEL, troughcolor=FIELD, focuscolor=PANEL,
                insertcolor=FG, font=FONT)
    s.configure("Black.TFrame", background=BLACK)
    s.configure("Dark.TLabel", background=BLACK, foreground=MUTED)
    s.configure("Muted.TLabel", foreground=MUTED)
    s.configure("Title.TLabel", font=("Segoe UI", 12, "bold"), foreground=BLUE_LIGHT)

    # Botões: cinza; com o mouse em cima ficam azuis; ao clicar, azul escuro
    for name, base, hover, press in (("TButton", BTN, BTN_HOVER, BLUE_PRESS),
                                     ("Accent.TButton", BLUE, BLUE_HOVER, BLUE_PRESS)):
        s.configure(name, background=base, foreground="white" if name != "TButton" else FG,
                    bordercolor=base, lightcolor=base, darkcolor=base, focusthickness=0,
                    focuscolor=base, padding=(12, 6), relief="flat", font=FONT_BOLD)
        s.map(name,
              background=[("disabled", DISABLED_BG), ("pressed", press), ("active", hover)],
              bordercolor=[("disabled", DISABLED_BG), ("pressed", press), ("active", hover)],
              lightcolor=[("disabled", DISABLED_BG), ("pressed", press), ("active", hover)],
              darkcolor=[("disabled", DISABLED_BG), ("pressed", press), ("active", hover)],
              foreground=[("disabled", MUTED)])

    s.configure("TNotebook", background=BLACK, borderwidth=0, tabmargins=(0, 0, 0, 0))
    s.configure("TNotebook.Tab", background=BTN, foreground=MUTED, padding=(14, 8),
                borderwidth=0, font=FONT_BOLD)
    s.map("TNotebook.Tab", background=[("selected", BLUE), ("active", BTN_HOVER)],
          foreground=[("selected", "white"), ("active", FG)])

    for name in ("TEntry", "TCombobox", "TSpinbox"):
        s.configure(name, fieldbackground=FIELD, foreground=FG, insertcolor=FG,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=4)
        s.map(name, bordercolor=[("focus", BLUE)], lightcolor=[("focus", BLUE)],
              darkcolor=[("focus", BLUE)], fieldbackground=[("disabled", DISABLED_BG)],
              foreground=[("disabled", MUTED)])
    for name in ("TCombobox", "TSpinbox"):
        s.configure(name, background=BTN, arrowcolor=FG)
        s.map(name, background=[("active", BTN_HOVER), ("pressed", BLUE_PRESS)])
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", BLUE)
    root.option_add("*TCombobox*Listbox.selectForeground", "white")
    root.option_add("*TCombobox*Listbox.font", FONT)

    s.configure("TCheckbutton", background=PANEL, foreground=FG, indicatorcolor=FIELD,
                indicatorbackground=FIELD, indicatorforeground="white", upperbordercolor=BORDER,
                lowerbordercolor=BORDER)
    s.map("TCheckbutton", indicatorcolor=[("selected", BLUE), ("active", BTN_HOVER)],
          indicatorbackground=[("selected", BLUE), ("active", BTN_HOVER)],
          background=[("active", PANEL)], foreground=[("disabled", MUTED)])
    s.configure("TLabelframe", background=PANEL, bordercolor=BORDER, lightcolor=BORDER,
                darkcolor=BORDER)
    s.configure("TLabelframe.Label", background=PANEL, foreground=BLUE_LIGHT, font=FONT_BOLD)

    s.configure("Treeview", background=FIELD, fieldbackground=FIELD, foreground=FG,
                rowheight=24, bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD)
    s.map("Treeview", background=[("selected", BLUE)], foreground=[("selected", "white")])
    s.configure("Treeview.Heading", background=BTN, foreground=FG, relief="flat",
                font=FONT_BOLD, bordercolor=BORDER, lightcolor=BTN, darkcolor=BTN)
    s.map("Treeview.Heading", background=[("active", BTN_HOVER), ("pressed", BLUE_PRESS)])
    s.configure("Vertical.TScrollbar", background=BTN, troughcolor=FIELD, bordercolor=FIELD,
                arrowcolor=FG, lightcolor=BTN, darkcolor=BTN)
    s.map("Vertical.TScrollbar", background=[("active", BTN_HOVER), ("pressed", BLUE_PRESS)])
    s.configure("Horizontal.TProgressbar", background=BLUE, troughcolor=FIELD,
                bordercolor=FIELD, lightcolor=BLUE, darkcolor=BLUE)


def to_photo(img_bgr: np.ndarray) -> tk.PhotoImage:
    """Imagem OpenCV (BGR) -> PhotoImage do Tk (via PPM, mais rápido que PNG)."""
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    return tk.PhotoImage(width=w, height=h, format="PPM",
                         data=b"P6 %d %d 255\n" % (w, h) + rgb.tobytes())


def fit(img: np.ndarray, box_w: int, box_h: int):
    """Reduz/amplia a imagem para caber na caixa. Devolve (imagem, escala)."""
    h, w = img.shape[:2]
    scale = min(box_w / w, box_h / h)
    size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return cv2.resize(img, size, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR), scale


class ScrollFrame(ttk.Frame):
    """Frame com rolagem vertical (roda do mouse). Coloque os widgets em `.body`."""

    def __init__(self, master, padding=12):
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._canvas = tk.Canvas(self, bg=PANEL, highlightthickness=0)
        bar = ttk.Scrollbar(self, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=bar.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        self.body = ttk.Frame(self._canvas, padding=padding)
        self._win = self._canvas.create_window(0, 0, anchor="nw", window=self.body)
        self.body.bind("<Configure>", lambda e: self._canvas.configure(
            scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._win, width=e.width))
        for w in (self._canvas, self.body):
            w.bind("<Enter>", self._bind_wheel)
            w.bind("<Leave>", self._unbind_wheel)

    def _bind_wheel(self, _):
        self._canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _):
        self._canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, e):
        first, last = self._canvas.yview()
        if first > 0 or last < 1:                    # só rola se o conteúdo não couber
            self._canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")


class App:
    def __init__(self, root: tk.Tk,
                 camera_factory: Callable[[int], "api.Camera"] = api.Camera,
                 reader_factory: Callable[[Optional[str]], object] = api.RoboflowReader,
                 connect_on_start: bool = True):
        self.root = root
        self.camera_factory, self.reader_factory = camera_factory, reader_factory
        self.cam = None
        self.cam_error = ""
        self.roi: Optional[api.Roi] = None          # em coordenadas do frame original
        self.reference: Optional[api.QualityReference] = None
        self.view: Optional[dict] = None            # escala/deslocamento do preview
        self.drag: Optional[list] = None
        self.worker: Optional[api.CaptureWorker] = None
        self.session: Optional[api.CaptureSession] = None
        self.last_status: Optional[str] = None
        self._reader = None
        self._reader_key: Optional[str] = None
        self._buf: deque = deque(maxlen=LIVE_BUFFER)
        self._last_frame_id = None
        self._tick = 0
        self._photo = None
        self._crop_photo = None
        self._locked: list = []                     # widgets desativados durante a captura

        apply_theme(root)
        root.title("Leitura automática de multímetros — calibração")
        root.geometry(f"{min(1320, root.winfo_screenwidth() - 60)}x"
                      f"{min(800, root.winfo_screenheight() - 100)}+20+20")
        root.minsize(1120, 700)
        self._init_vars()
        self._build()
        self._load_settings()
        self._refresh_key_info()
        self._sync_log_state()
        self.show_quality(None)
        root.protocol("WM_DELETE_WINDOW", self.close)
        threading.Thread(target=self._preload, daemon=True).start()
        self.update_preview()
        if connect_on_start:
            root.after(150, self.connect_camera)

    @staticmethod
    def _preload():
        try:
            import inference_sdk  # noqa: F401  (deixa a 1ª captura mais rápida)
        except Exception:
            pass

    # ======================================================================
    # Construção da janela
    # ======================================================================
    def _init_vars(self):
        v = tk.StringVar
        self.v_camera = v(value="0")
        self.v_interval, self.v_max = v(value="2"), v(value="10")
        self.value_rules: list[api.ValueAlert] = []
        self.v_rule_op = v(value=next(iter(RULE_OPS)))
        self.v_rule_value = v()
        self.v_log_enabled = tk.BooleanVar(value=True)
        self.v_log_name = v()                       # em branco: nome automático (data e hora)
        self.v_log_hint = v()
        self.v_log_name.trace_add("write", lambda *_: self._update_log_hint())
        self.v_unit, self.v_point, self.v_cycle = v(value="V"), v(), v()
        self.v_min, self.v_max_expected = v(), v()
        self.v_save_images = tk.BooleanVar(value=True)
        self.v_nframes, self.v_qevery, self.v_mevery = v(value="8"), v(value="5"), v(value="5")
        self.v_jump_rel, self.v_jump_abs = v(value="20"), v()
        self.v_key = v()
        self.v_remember = tk.BooleanVar(value=False)
        self.v_roi = v(value="Nenhuma área selecionada")
        self.v_refinfo = v(value="Referência: nenhuma (só os limites absolutos)")
        self.v_status = v(value="Conectando à câmera…")
        self.v_value = v(value="—")
        self.v_state = v(value="Aguardando captura")
        self.v_progress = v(value="")
        self.v_keyinfo = v()

    def _build(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=0)
        root.rowconfigure(0, weight=1)

        # ---- esquerda: câmera e preview ---------------------------------
        left = ttk.Frame(root, style="Black.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        bar = ttk.Frame(left, style="Black.TFrame")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(bar, text="Câmera", style="Dark.TLabel").pack(side="left")
        self.sp_camera = ttk.Spinbox(bar, from_=0, to=9, width=3, textvariable=self.v_camera)
        self.sp_camera.pack(side="left", padx=6)
        self.btn_connect = ttk.Button(bar, text="Reconectar", command=self.connect_camera)
        self.btn_connect.pack(side="left")
        self.lbl_res = ttk.Label(bar, text="", style="Dark.TLabel")
        self.lbl_res.pack(side="left", padx=10)

        self.canvas = tk.Canvas(left, bg=BLACK, highlightthickness=1,
                                highlightbackground=BORDER, cursor="crosshair")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.img_id = self.canvas.create_image(0, 0, anchor="nw", tags="img")
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        ttk.Label(left, text="Arraste sobre o display do multímetro para selecionar a área "
                             "de leitura.", style="Dark.TLabel").grid(row=2, column=0, sticky="w",
                                                                      pady=(6, 0))

        # ---- direita: abas das três etapas ------------------------------
        right = ttk.Frame(root, style="Black.TFrame", width=500)
        right.grid(row=0, column=1, sticky="ns", padx=(5, 10), pady=10)
        right.grid_propagate(False)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.nb = ttk.Notebook(right)
        self.nb.grid(row=0, column=0, sticky="nsew")
        self.tab1, self.tab3 = (ttk.Frame(self.nb, padding=12) for _ in range(2))
        self.tab2 = ScrollFrame(self.nb)                 # a aba 2 é a mais alta: rola se precisar
        self.nb.add(self.tab1, text="1 · Visualização")
        self.nb.add(self.tab2, text="2 · Configuração")
        self.nb.add(self.tab3, text="3 · Captura")
        self._build_tab1()
        self._build_tab2()
        self._build_tab3()

        # ---- barra de status --------------------------------------------
        ttk.Label(root, textvariable=self.v_status, style="Dark.TLabel", anchor="w").grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))

    # ---- aba 1 ----------------------------------------------------------
    def _build_tab1(self):
        t = self.tab1
        t.columnconfigure(0, weight=1)
        ttk.Label(t, text="Calibração da visualização", style="Title.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(t, textvariable=self.v_roi, style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 6))
        self.btn_clear = ttk.Button(t, text="Limpar seleção", command=self.clear_roi)
        self.btn_clear.grid(row=2, column=0, sticky="w")

        box = ttk.LabelFrame(t, text="Teste de qualidade (ao vivo)", padding=10)
        box.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        box.columnconfigure(0, weight=1)
        self.lbl_quality = tk.Label(box, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 13, "bold"),
                                    anchor="w")
        self.lbl_quality.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        for c, h in enumerate(("Métrica", "Atual", "Referência")):
            ttk.Label(box, text=h, style="Muted.TLabel").grid(row=1, column=c, sticky="w" if c == 0
                                                              else "e", padx=(0, 8))
        self.metric_rows = []
        for r, (name, fmt) in enumerate((("Luminosidade (fundo)", "{:.0f}"), ("Contraste", "{:.0f}"),
                                         ("Reflexo (%)", "{:.2f}"), ("Nitidez", "{:.2f}")), start=2):
            ttk.Label(box, text=name).grid(row=r, column=0, sticky="w", padx=(0, 8), pady=1)
            cur = tk.Label(box, text="—", bg=PANEL, fg=FG, font=("Consolas", 10), anchor="e")
            ref = tk.Label(box, text="—", bg=PANEL, fg=MUTED, font=("Consolas", 10), anchor="e")
            cur.grid(row=r, column=1, sticky="e", padx=(0, 8))
            ref.grid(row=r, column=2, sticky="e")
            self.metric_rows.append((cur, ref, fmt))
        self.lbl_issues = tk.Label(box, text="", bg=PANEL, fg=FG, justify="left", anchor="w",
                                   wraplength=400, font=FONT)
        self.lbl_issues.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        ref = ttk.LabelFrame(t, text="Imagem de referência (condições ideais)", padding=10)
        ref.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        ref.columnconfigure((0, 1), weight=1)
        ttk.Label(ref, textvariable=self.v_refinfo, style="Muted.TLabel", wraplength=420).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.btn_setref = ttk.Button(ref, text="Usar imagem atual", command=self.set_reference)
        self.btn_saveref = ttk.Button(ref, text="Salvar…", command=self.save_reference)
        self.btn_loadref = ttk.Button(ref, text="Carregar…", command=self.load_reference)
        self.btn_noref = ttk.Button(ref, text="Remover", command=self.remove_reference)
        for i, b in enumerate((self.btn_setref, self.btn_saveref, self.btn_loadref, self.btn_noref)):
            b.grid(row=1 + i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        self._locked += [self.btn_clear, self.btn_setref, self.btn_saveref, self.btn_loadref,
                         self.btn_noref, self.btn_connect, self.sp_camera]

        ttk.Button(t, text="Próximo: configuração  ›", style="Accent.TButton",
                   command=lambda: self.nb.select(self.tab2)).grid(row=5, column=0, sticky="e",
                                                                   pady=(14, 0))

    # ---- aba 2 ----------------------------------------------------------
    def _build_tab2(self):
        t = self.tab2.body
        t.columnconfigure(0, weight=1)
        ttk.Label(t, text="Configuração da captura", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6))

        def group(title, row):
            f = ttk.LabelFrame(t, text=title, padding=8)
            f.grid(row=row, column=0, sticky="ew", pady=(0, 8))
            f.columnconfigure(1, weight=1)
            f.columnconfigure(3, weight=1)
            return f

        def entry(parent, r, c, label, var, width=10, colspan=1):
            ttk.Label(parent, text=label).grid(row=r, column=c, sticky="w", padx=(0, 6), pady=3)
            e = ttk.Entry(parent, textvariable=var, width=width)
            e.grid(row=r, column=c + 1, columnspan=colspan, sticky="ew", padx=(0, 10), pady=3)
            self._locked.append(e)
            return e

        g = group("Captura", 1)
        entry(g, 0, 0, "Intervalo (s)", self.v_interval)
        entry(g, 0, 2, "Limite de imagens", self.v_max)
        ttk.Label(g, text="0 = sem limite (use Parar)", style="Muted.TLabel").grid(
            row=1, column=0, columnspan=4, sticky="w")

        g = group("Registro (log CSV)", 2)
        chk_log = ttk.Checkbutton(g, text="Gravar log (CSV)", variable=self.v_log_enabled,
                                  command=self._sync_log_state)
        chk_log.grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(g, text="Nome do arquivo").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=3)
        self.entry_log = ttk.Entry(g, textvariable=self.v_log_name)
        self.entry_log.grid(row=1, column=1, columnspan=3, sticky="ew", pady=3)
        ttk.Label(g, textvariable=self.v_log_hint, style="Muted.TLabel", wraplength=420,
                  justify="left").grid(row=2, column=0, columnspan=4, sticky="w")
        self._locked += [chk_log, self.entry_log]
        ttk.Label(g, text="Unidade").grid(row=3, column=0, sticky="w", pady=3)
        cb = ttk.Combobox(g, textvariable=self.v_unit, values=UNITS, width=12)
        cb.grid(row=3, column=1, sticky="ew", padx=(0, 10))
        self._locked.append(cb)
        entry(g, 4, 0, "Ponto de calibração", self.v_point, colspan=1)
        entry(g, 4, 2, "Ciclo", self.v_cycle)
        chk = ttk.Checkbutton(g, text="Salvar o recorte de cada leitura (PNG)",
                              variable=self.v_save_images)
        chk.grid(row=5, column=0, columnspan=4, sticky="w", pady=(4, 0))
        self._locked.append(chk)

        g = group("Faixa esperada (opcional)", 3)
        entry(g, 0, 0, "Mínimo", self.v_min)
        entry(g, 0, 2, "Máximo", self.v_max_expected)

        g = group("Alertas por valor (opcional)", 4)
        ttk.Label(g, text="Avisar quando a leitura for").grid(row=0, column=0, columnspan=4,
                                                              sticky="w", pady=(0, 4))
        self.cb_rule_op = ttk.Combobox(g, textvariable=self.v_rule_op, values=list(RULE_OPS),
                                       state="readonly", width=20)
        self.cb_rule_op.grid(row=1, column=0, columnspan=2, sticky="w", padx=(0, 6))
        self.entry_rule = ttk.Entry(g, textvariable=self.v_rule_value, width=10)
        self.entry_rule.grid(row=1, column=2, sticky="ew", padx=(0, 6))
        self.entry_rule.bind("<Return>", lambda e: self.add_rule())
        self.btn_add_rule = ttk.Button(g, text="Adicionar", command=self.add_rule)
        self.btn_add_rule.grid(row=1, column=3, sticky="e")
        self.rules_list = tk.Listbox(g, height=3, bg=FIELD, fg=FG, selectbackground=BLUE,
                                     highlightthickness=1, highlightbackground=BORDER,
                                     relief="flat", font=FONT, activestyle="none",
                                     exportselection=False)
        self.rules_list.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0), padx=(0, 6))
        self.btn_del_rule = ttk.Button(g, text="Remover", command=self.remove_rule)
        self.btn_del_rule.grid(row=2, column=3, sticky="ne", pady=(6, 0))
        ttk.Label(g, text="Pode adicionar vários. Cada leitura que cumprir uma regra vira "
                          "“duvidosa” e entra na lista de alertas.", style="Muted.TLabel",
                  wraplength=420, justify="left").grid(row=3, column=0, columnspan=4, sticky="w",
                                                       pady=(4, 0))
        self._locked += [self.cb_rule_op, self.entry_rule, self.btn_add_rule, self.rules_list,
                         self.btn_del_rule]

        g = group("Avançado", 5)
        entry(g, 0, 0, "Frames por leitura", self.v_nframes)
        entry(g, 0, 2, "Qualidade a cada N", self.v_qevery)
        entry(g, 1, 0, "Câmera movida a cada N", self.v_mevery)
        entry(g, 1, 2, "Salto brusco (%)", self.v_jump_rel)
        entry(g, 2, 0, "Salto absoluto", self.v_jump_abs)
        ttk.Label(g, text="O salto absoluto, se preenchido, substitui o percentual.",
                  style="Muted.TLabel").grid(row=3, column=0, columnspan=4, sticky="w")

        g = group("Leitor (Roboflow)", 6)
        ttk.Label(g, text="Chave da API").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        e = ttk.Entry(g, textvariable=self.v_key, show="•")
        e.grid(row=0, column=1, columnspan=3, sticky="ew", pady=3)
        self.entry_key = e
        chk = ttk.Checkbutton(g, text="Gravar no config.json", variable=self.v_remember)
        chk.grid(row=1, column=0, columnspan=2, sticky="w")
        b = ttk.Button(g, text="Apagar do config.json", command=self.forget_key)
        b.grid(row=1, column=2, columnspan=2, sticky="e")
        ttk.Label(g, textvariable=self.v_keyinfo, style="Muted.TLabel", wraplength=420).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(2, 0))
        self._locked += [e, chk, b]

        ttk.Button(t, text="Próximo: captura  ›", style="Accent.TButton",
                   command=lambda: self.nb.select(self.tab3)).grid(row=7, column=0, sticky="e")

    # ---- aba 3 ----------------------------------------------------------
    def _build_tab3(self):
        t = self.tab3
        t.columnconfigure(0, weight=1)
        t.rowconfigure(5, weight=1)
        ttk.Label(t, text="Captura e acompanhamento", style="Title.TLabel").grid(
            row=0, column=0, sticky="w")
        btns = ttk.Frame(t)
        btns.grid(row=1, column=0, sticky="ew", pady=(8, 8))
        btns.columnconfigure((0, 1), weight=1)
        self.btn_start = ttk.Button(btns, text="▶  Iniciar captura", style="Accent.TButton",
                                    command=self.start_capture)
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.btn_stop = ttk.Button(btns, text="■  Parar", command=self.stop_capture,
                                   state="disabled")
        self.btn_stop.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        box = tk.Frame(t, bg=FIELD, highlightthickness=1, highlightbackground=BORDER)
        box.grid(row=2, column=0, sticky="ew")
        box.columnconfigure(0, weight=1)
        self.lbl_value = tk.Label(box, textvariable=self.v_value, bg=FIELD, fg=BLUE_LIGHT,
                                  font=FONT_BIG)
        self.lbl_value.grid(row=0, column=0, columnspan=2, pady=(8, 0))
        self.lbl_state = tk.Label(box, textvariable=self.v_state, bg=FIELD, fg=MUTED, font=FONT)
        self.lbl_state.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))
        self.crop_canvas = tk.Canvas(box, width=150, height=56, bg=BLACK, highlightthickness=0)
        self.crop_canvas.grid(row=1, column=1, padx=10, pady=(0, 8))

        pr = ttk.Frame(t)
        pr.grid(row=3, column=0, sticky="ew", pady=(8, 4))
        pr.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(pr, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew")
        ttk.Label(pr, textvariable=self.v_progress, style="Muted.TLabel", width=14,
                  anchor="e").grid(row=0, column=1, padx=(8, 0))

        ttk.Label(t, text="Alertas", style="Muted.TLabel").grid(row=4, column=0, sticky="w")
        body = ttk.Frame(t)
        body.grid(row=5, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        body.rowconfigure(3, weight=2)
        lf = ttk.Frame(body)
        lf.grid(row=0, column=0, rowspan=2, sticky="nsew")
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)
        self.alerts = tk.Listbox(lf, height=5, bg=FIELD, fg=AMBER, selectbackground=BLUE,
                                 highlightthickness=1, highlightbackground=BORDER, relief="flat",
                                 font=FONT, activestyle="none")
        sb = ttk.Scrollbar(lf, command=self.alerts.yview)
        self.alerts.configure(yscrollcommand=sb.set)
        self.alerts.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        body.rowconfigure(0, weight=1)

        ttk.Label(body, text="Leituras", style="Muted.TLabel").grid(row=2, column=0, sticky="w",
                                                                    pady=(8, 0))
        tf = ttk.Frame(body)
        tf.grid(row=3, column=0, sticky="nsew")
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)
        cols = ("n", "hora", "valor", "unidade", "status", "alertas")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", height=8)
        for c, text, w in (("n", "#", 30), ("hora", "Hora", 66), ("valor", "Valor", 64),
                           ("unidade", "Unid.", 44), ("status", "Status", 92),
                           ("alertas", "Alertas", 200)):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=w, anchor="w", stretch=(c == "alertas"))
        for st, color in STATUS_COLOR.items():
            self.tree.tag_configure(st, foreground=color)
        sb2 = ttk.Scrollbar(tf, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb2.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb2.grid(row=0, column=1, sticky="ns")

        ttk.Button(t, text="Abrir pasta do log", command=self.open_log_folder).grid(
            row=6, column=0, sticky="w", pady=(8, 0))

    # ======================================================================
    # Câmera, preview e seleção do display
    # ======================================================================
    def connect_camera(self):
        if self.worker and self.worker.is_alive():
            return
        if self.cam is not None:
            self.cam.release()
            self.cam = None
        self._buf.clear()
        try:
            index = int(self.v_camera.get())
        except ValueError:
            index = 0
            self.v_camera.set("0")
        self.cam_error = "Conectando à câmera…"
        self.v_status.set(self.cam_error)
        self.root.update_idletasks()
        try:
            self.cam = self.camera_factory(index)
        except RuntimeError as error:
            self.cam_error = f"{error}. Feche outros programas que usem a câmera e clique em Reconectar."
            self.v_status.set(self.cam_error)
            self.lbl_res.config(text="")
            return
        self.cam_error = ""
        w, h = self.cam.resolution
        self.lbl_res.config(text=f"{w}×{h}")
        self.v_status.set("Câmera conectada. Selecione o display no preview.")

    def update_preview(self):
        try:
            frame = self.cam.read() if self.cam else None
            self.render(frame)
            if frame is not None:
                self.live_quality(frame)
        finally:
            self.root.after(PREVIEW_MS, self.update_preview)

    def render(self, frame: Optional[np.ndarray]):
        c = self.canvas
        c.delete("ov")
        cw, ch = c.winfo_width(), c.winfo_height()
        if frame is None:
            c.itemconfig(self.img_id, image="")
            self.view = None
            c.create_text(cw // 2, ch // 2, fill=MUTED, font=("Segoe UI", 12), tags="ov",
                          text=self.cam_error or "Sem imagem da câmera", width=max(100, cw - 60),
                          justify="center")
            return
        if cw < 10 or ch < 10:
            return
        small, scale = fit(frame, cw, ch)
        dh, dw = small.shape[:2]
        ox, oy = (cw - dw) // 2, (ch - dh) // 2
        self._photo = to_photo(small)                  # manter referência
        c.itemconfig(self.img_id, image=self._photo)
        c.coords(self.img_id, ox, oy)
        self.view = {"scale": scale, "ox": ox, "oy": oy, "fw": frame.shape[1], "fh": frame.shape[0]}
        if self.roi:
            color = STATUS_COLOR.get(self.last_status or "", BLUE_HOVER)
            self._draw_rect(self.roi, color, 2)
        if self.drag:
            (x0, y0), (x1, y1) = self.drag
            self._draw_rect(api.roi_from_points((x0, y0), (x1, y1)), AMBER, 1)
        if not self.roi and not self.drag:
            c.create_text(cw // 2, oy + 24, fill=BLUE_LIGHT, font=("Segoe UI", 12, "bold"),
                          tags="ov", text="Arraste um retângulo em volta do display")

    def _draw_rect(self, roi, color, width):
        v = self.view
        x, y, w, h = roi
        s = v["scale"]
        self.canvas.create_rectangle(v["ox"] + x * s, v["oy"] + y * s, v["ox"] + (x + w) * s,
                                     v["oy"] + (y + h) * s, outline=color, width=width, tags="ov")

    def _to_frame(self, x, y):
        v = self.view
        fx = min(max((x - v["ox"]) / v["scale"], 0), v["fw"])
        fy = min(max((y - v["oy"]) / v["scale"], 0), v["fh"])
        return int(fx), int(fy)

    def _selecting(self) -> bool:
        return self.view is not None and not (self.worker and self.worker.is_alive())

    def on_press(self, e):
        if self._selecting():
            p = self._to_frame(e.x, e.y)
            self.drag = [p, p]

    def on_drag(self, e):
        if self.drag and self.view:
            self.drag[1] = self._to_frame(e.x, e.y)

    def on_release(self, e):
        if not self.drag or not self.view:
            self.drag = None
            return
        self.drag[1] = self._to_frame(e.x, e.y)
        roi = api.clamp_roi(api.roi_from_points(*self.drag), (self.view["fh"], self.view["fw"]))
        self.drag = None
        if roi:
            self.set_roi(roi)
        else:
            self.v_status.set("Área muito pequena. Arraste um retângulo maior sobre o display.")

    def set_roi(self, roi: Optional[api.Roi]):
        self.roi = roi
        self._buf.clear()
        self.last_status = None
        if roi:
            x, y, w, h = roi
            self.v_roi.set(f"Área do display: {w}×{h} px (x={x}, y={y})")
            self.v_status.set("Display selecionado. Confira o teste de qualidade na aba 1.")
        else:
            self.v_roi.set("Nenhuma área selecionada")
            self.show_quality(None)

    def clear_roi(self):
        self.set_roi(None)

    # ======================================================================
    # Teste de qualidade (aba 1)
    # ======================================================================
    def live_quality(self, frame: np.ndarray):
        """Qualidade ao vivo: mediana dos últimos frames do recorte, a cada ~0,4 s."""
        if not self.roi:
            return
        r = api.clamp_roi(self.roi, frame.shape)
        if r is None:
            return
        if id(frame) != self._last_frame_id:
            self._last_frame_id = id(frame)
            piece = api.crop(frame, r)
            if self._buf and self._buf[0].shape != piece.shape:
                self._buf.clear()
            self._buf.append(piece)
        self._tick += 1
        if self._tick % 8 == 0 and len(self._buf) >= 3:
            img = np.median(np.stack(self._buf), axis=0).astype(np.uint8)
            self.show_quality(api.check_quality(img, self.reference))

    def show_quality(self, report: Optional[api.QualityReport]):
        if report is None:
            self.lbl_quality.config(text="Selecione o display", fg=MUTED)
            self.lbl_issues.config(text="")
            for cur, ref, _ in self.metric_rows:
                cur.config(text="—", fg=FG)
            self._show_reference_metrics()
            return
        if report.ok:
            self.lbl_quality.config(text="●  Qualidade OK", fg=BLUE_LIGHT)
        else:
            self.lbl_quality.config(text="●  Atenção: ajuste a imagem", fg=AMBER)
        m = report.metrics
        values = (m["background"], m["contrast"], m["saturated"] + m["colored"], m["sharpness"])
        bad = {0: {"escura", "estourada"}, 1: {"contraste"}, 2: {"reflexo"}, 3: {"desfocada"}}
        codes = {i.code for i in report.issues}
        for i, ((cur, _, fmt), val) in enumerate(zip(self.metric_rows, values)):
            cur.config(text=fmt.format(val), fg=AMBER if codes & bad[i] else FG)
        self._show_reference_metrics()
        self.lbl_issues.config(text="\n".join(f"• {i.message}: {i.suggestion}" for i in report.issues))

    def _show_reference_metrics(self):
        r = self.reference.metrics if self.reference else None
        vals = None if r is None else (r["background"], r["contrast"],
                                       r["saturated"] + r["colored"], r["sharpness"])
        for i, (_, ref, fmt) in enumerate(self.metric_rows):
            ref.config(text="—" if vals is None else fmt.format(vals[i]))

    # ---- referência de qualidade ----------------------------------------
    def set_reference(self):
        if not self.cam or not self.roi:
            return messagebox.showinfo("Referência", "Conecte a câmera e selecione o display primeiro.")
        self.v_status.set("Capturando a imagem de referência…")
        self.root.update_idletasks()
        img = self.cam.median_crop(self.roi, 8)
        if img is None:
            return messagebox.showerror("Referência", "Não foi possível capturar o recorte.")
        self.reference = api.QualityReference.from_image(img)
        self.v_refinfo.set(f"Referência: imagem atual ({datetime.now():%H:%M:%S})")
        self.v_status.set("Referência definida. Use-a quando as condições estiverem ideais.")
        self._show_reference_metrics()

    def save_reference(self):
        if not self.reference:
            return messagebox.showinfo("Referência", "Não há referência para salvar.")
        path = filedialog.asksaveasfilename(title="Salvar referência", defaultextension=".json",
                                            filetypes=[("JSON", "*.json")],
                                            initialfile="referencia_qualidade.json")
        if path:
            try:
                self.reference.save(path)
                self.v_status.set(f"Referência salva em {path}")
            except OSError as error:
                messagebox.showerror("Referência", f"Não foi possível salvar: {error}")

    def load_reference(self):
        path = filedialog.askopenfilename(title="Carregar referência",
                                          filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if not path:
            return
        try:
            self.reference = api.QualityReference.load(path)
        except (OSError, ValueError, KeyError) as error:
            return messagebox.showerror("Referência", f"Arquivo inválido: {error}")
        self.v_refinfo.set(f"Referência: {Path(path).name}")
        self.v_status.set("Referência carregada.")
        self._show_reference_metrics()

    def remove_reference(self):
        self.reference = None
        self.v_refinfo.set("Referência: nenhuma (só os limites absolutos)")
        self._show_reference_metrics()

    # ======================================================================
    # Configuração (aba 2)
    # ======================================================================
    # ---- alertas por valor ------------------------------------------------
    def _refresh_rules(self):
        self.rules_list.delete(0, "end")
        for r in self.value_rules:
            self.rules_list.insert("end", f"Alertar se a leitura for {RULE_SYMBOL[r.op]} {r.threshold:g}")

    def add_rule(self):
        errors: list[str] = []
        value = self._num(self.v_rule_value.get(), "Valor do alerta", errors)
        if errors or value is None or value != value or abs(value) == float("inf"):
            return messagebox.showerror("Alerta por valor", "Informe um número válido (ex.: 5 ou 12,5).")
        rule = api.ValueAlert(RULE_OPS[self.v_rule_op.get()], value)
        if rule not in self.value_rules:
            self.value_rules.append(rule)
            self._refresh_rules()
        self.v_rule_value.set("")

    def remove_rule(self):
        for i in reversed(self.rules_list.curselection()):
            del self.value_rules[i]
        self._refresh_rules()

    def _update_log_hint(self):
        folder = api.LOGS_DIR.name
        if not self.v_log_enabled.get():
            text = "Log desligado: as leituras aparecem só na tela."
        elif self.v_log_name.get().strip():
            name = Path(api.resolve_log_path(self.v_log_name.get())).name
            text = f"Será gravado em {folder}\\{name}. Se já existir, as leituras são acrescentadas."
        else:
            text = (f"Em branco: cria {folder}\\leituras_AAAAMMDD_HHMMSS.csv, "
                    "um arquivo novo a cada captura.")
        self.v_log_hint.set(text)

    def _sync_log_state(self):
        """O nome do arquivo só vale com o log ligado (e fora de uma captura)."""
        capturing = bool(self.worker and self.worker.is_alive())
        self.entry_log.config(state="normal" if self.v_log_enabled.get() and not capturing
                              else "disabled")
        self._update_log_hint()

    @staticmethod
    def _num(text: str, name: str, errors: list, kind=float, optional=False):
        text = text.strip().replace(",", ".")
        if not text:
            if not optional:
                errors.append(f"Preencha: {name}.")
            return None
        try:
            return kind(text)
        except ValueError:
            errors.append(f"Valor inválido em “{name}”.")
            return None

    def build_config(self) -> tuple[Optional[api.CaptureConfig], list[str]]:
        errors: list[str] = []
        n = self._num
        interval = n(self.v_interval.get(), "Intervalo", errors)
        max_images = n(self.v_max.get(), "Limite de imagens", errors, int)
        nframes = n(self.v_nframes.get(), "Frames por leitura", errors, int)
        qevery = n(self.v_qevery.get(), "Qualidade a cada N", errors, int)
        mevery = n(self.v_mevery.get(), "Câmera movida a cada N", errors, int)
        jump_rel = n(self.v_jump_rel.get(), "Salto brusco (%)", errors)
        jump_abs = n(self.v_jump_abs.get(), "Salto absoluto", errors, optional=True)
        vmin = n(self.v_min.get(), "Mínimo", errors, optional=True)
        vmax = n(self.v_max_expected.get(), "Máximo", errors, optional=True)
        if errors:
            return None, errors
        cfg = api.CaptureConfig(
            interval_s=interval, max_images=max_images,
            log_path=api.resolve_log_path(self.v_log_name.get()) if self.v_log_enabled.get() else None,
            unit=self.v_unit.get().strip(), calibration_point=self.v_point.get().strip() or None,
            cycle=self.v_cycle.get().strip() or None, min_expected=vmin, max_expected=vmax,
            value_alerts=list(self.value_rules),
            n_frames=nframes, quality_every=qevery, motion_every=mevery,
            max_jump_rel=jump_rel / 100, max_jump_abs=jump_abs,
            save_images=self.v_save_images.get())
        return cfg, cfg.validate()

    # ---- chave do Roboflow ----------------------------------------------
    def _refresh_key_info(self):
        cfg = api.CONFIG_FILE.name
        if str(api._read_config().get(api.CONFIG_KEY, "")).strip():
            info = f"Usando a chave do arquivo {cfg}."
        elif os.environ.get(api.API_KEY_ENV, "").strip():
            info = f"Usando a variável de ambiente {api.API_KEY_ENV}."
        else:
            info = f"Nenhuma chave definida: informe acima ou coloque em {cfg}."
        self.v_keyinfo.set(info + " Uma chave digitada acima tem prioridade.")

    def forget_key(self):
        api.forget_api_key()
        self._reader = self._reader_key = None
        self._refresh_key_info()

    def get_reader(self):
        """Leitor do Roboflow (reaproveitado enquanto a chave não mudar)."""
        key = self.v_key.get().strip() or None
        if self._reader is None or self._reader_key != key:
            self._reader = self.reader_factory(key)
            self._reader_key = key
        if key and self.v_remember.get():
            api.save_api_key(key)
            self._refresh_key_info()
        return self._reader

    # ======================================================================
    # Captura (aba 3)
    # ======================================================================
    def start_capture(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.cam:
            return messagebox.showwarning("Captura", "A câmera não está conectada.")
        if not self.roi:
            self.nb.select(self.tab1)
            return messagebox.showwarning("Captura", "Selecione o display no preview (aba 1).")
        cfg, errors = self.build_config()
        if errors:
            self.nb.select(self.tab2)
            return messagebox.showerror("Configuração", "\n".join(errors))
        try:
            reader = self.get_reader()
        except api.MissingApiKeyError as error:
            self.nb.select(self.tab2)
            self.entry_key.focus_set()
            return messagebox.showerror("Chave do Roboflow", str(error))
        except ImportError:
            return messagebox.showerror("Dependência ausente",
                                        "O pacote inference-sdk não está instalado.\n"
                                        "Rode: python -m pip install -r requirements.txt")
        try:
            self.session = api.CaptureSession(self.cam, reader, cfg, self.roi, self.reference)
        except (ValueError, RuntimeError, OSError) as error:
            return messagebox.showerror("Captura", str(error))
        self._save_settings()

        self.tree.delete(*self.tree.get_children())
        self.alerts.delete(0, "end")
        self.v_value.set("—")
        self.lbl_value.config(fg=BLUE_LIGHT)
        self.last_status = None
        if cfg.max_images > 0:
            self.progress.config(mode="determinate", maximum=cfg.max_images, value=0)
        else:
            self.progress.config(mode="indeterminate")
            self.progress.start(30)
        self.v_progress.set("0 leituras")
        self.v_state.set("Capturando…")
        self.v_status.set(f"Capturando a cada {cfg.interval_s:g} s. "
                          f"Log: {cfg.log_path or 'desligado'}")
        self.set_capturing(True)
        self.worker = api.CaptureWorker(self.session)
        self.worker.start()
        self.poll_results()

    def stop_capture(self):
        if self.worker:
            self.worker.stop()
            self.v_state.set("Parando…")

    def set_capturing(self, on: bool):
        for w in self._locked:
            w.config(state="disabled" if on else "normal")
        self.btn_start.config(state="disabled" if on else "normal")
        self.btn_stop.config(state="normal" if on else "disabled")
        self.canvas.config(cursor="arrow" if on else "crosshair")
        if not on:
            self._sync_log_state()

    def poll_results(self):
        worker = self.worker
        if worker is None:
            return
        finished = False
        while True:
            try:
                r = worker.results.get_nowait()
            except Exception:
                break
            if r is None:
                finished = True
                break
            self.show_result(r)
        if finished:
            return self.finish_capture(worker)
        self.root.after(100, self.poll_results)

    def show_result(self, r: api.CaptureResult):
        self.last_status = r.status
        self.v_value.set(f"{r.reading.text or '—'} {r.unit}".strip())
        self.lbl_value.config(fg=STATUS_COLOR[r.status])
        self.v_state.set(f"Leitura {r.index} · {STATUS_LABEL[r.status]} · {r.timestamp:%H:%M:%S}")
        cfg = self.session.config
        if cfg.max_images > 0:
            self.progress.config(value=r.index)
            self.v_progress.set(f"{r.index} / {cfg.max_images}")
        else:
            self.v_progress.set(f"{r.index} leituras")
        self.tree.insert("", 0, tags=(r.status,), values=(
            r.index, f"{r.timestamp:%H:%M:%S}", r.reading.text or "—", r.unit,
            STATUS_LABEL[r.status], " | ".join(a.message for a in r.alerts)))
        children = self.tree.get_children()
        for old in children[300:]:
            self.tree.delete(old)
        for a in reversed(r.alerts):
            self.alerts.insert(0, f"{r.timestamp:%H:%M:%S}  #{r.index}  {a.message}")
        if r.image_path:
            self.show_crop(r.image_path)

    def show_crop(self, path: str):
        img = cv2.imread(path)
        if img is None:
            return
        small, _ = fit(img, 150, 56)
        self._crop_photo = to_photo(small)
        self.crop_canvas.delete("all")
        self.crop_canvas.create_image(75, 28, image=self._crop_photo)

    def finish_capture(self, worker: api.CaptureWorker):
        self.progress.stop()
        self.set_capturing(False)
        n = worker.session.count
        log = worker.session.config.log_path
        self.v_state.set(f"Captura encerrada · {n} leituras")
        where = f"gravadas em {log}" if log else "feitas (log desligado)"
        self.v_status.set(f"Captura encerrada: {n} leituras {where}")
        if worker.error:
            self.v_state.set("Captura interrompida por erro")
            messagebox.showerror("Captura", f"A captura parou por um erro:\n{worker.error}")
        self.worker = None

    def open_log_folder(self):
        folder = api.LOGS_DIR
        if not folder.exists():
            return messagebox.showinfo("Log", "A pasta logs ainda não existe: ela é criada na "
                                              "primeira captura com log ou imagens.")
        if sys.platform == "win32":
            os.startfile(folder)                          # noqa: S606
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(folder)])

    # ======================================================================
    # Configurações salvas e encerramento
    # ======================================================================
    _SAVED = ("v_camera", "v_interval", "v_max", "v_log_enabled", "v_log_name", "v_unit", "v_point", "v_cycle", "v_min",
              "v_max_expected", "v_save_images", "v_nframes", "v_qevery", "v_mevery",
              "v_jump_rel", "v_jump_abs", "v_remember")

    def _load_settings(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for name in self._SAVED:
            if name in data:
                try:
                    getattr(self, name).set(data[name])
                except tk.TclError:
                    pass
        for op, thr in data.get("value_alerts", []):          # alertas por valor
            if op in api.VALUE_OPS and isinstance(thr, (int, float)):
                self.value_rules.append(api.ValueAlert(op, float(thr)))
        self._refresh_rules()

    def _save_settings(self):
        """Guarda o formulário (sem a chave da API) na pasta do usuário."""
        try:
            api.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            data = {n: getattr(self, n).get() for n in self._SAVED}
            data["value_alerts"] = [[r.op, r.threshold] for r in self.value_rules]
            SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
        except OSError:
            pass

    def close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("Sair", "Há uma captura em andamento. Parar e sair?"):
                return
            self.worker.stop()
            self.worker.join(5)
        self._save_settings()
        if self.cam:
            self.cam.release()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
