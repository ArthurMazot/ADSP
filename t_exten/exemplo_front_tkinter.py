"""
Exemplo mínimo de como o front usa o leitor_multimetro.py (Tkinter, sem dependências extras).

Mostra o padrão importante: a captura roda numa thread (CaptureWorker) e o Tkinter só lê a
fila de resultados com root.after(), porque o Tkinter não pode ser mexido de outra thread.

Fluxo: arraste um retângulo no preview -> "Testar qualidade" -> "Iniciar captura".
"""
import base64
import tkinter as tk

import cv2

import leitor_multimetro as lm

PREVIEW_W = 640                 # largura do preview na tela


class App:
    def __init__(self, root):
        self.root = root
        self.cam = lm.Camera(0)
        self.roi = None         # em coordenadas do frame original
        self.scale = 1.0        # frame -> tela
        self.drag_start = None
        self.worker = None

        self.canvas = tk.Canvas(root, width=PREVIEW_W, height=360, bg="black")
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        bar = tk.Frame(root)
        bar.pack(fill="x")
        tk.Button(bar, text="Testar qualidade", command=self.test_quality).pack(side="left")
        tk.Button(bar, text="Iniciar captura", command=self.start).pack(side="left")
        tk.Button(bar, text="Parar", command=self.stop).pack(side="left")
        self.value = tk.Label(root, text="—", font=("Consolas", 32))
        self.value.pack()
        self.status = tk.Label(root, text="Arraste um retângulo em volta do display", anchor="w")
        self.status.pack(fill="x")
        self.update_preview()

    # ---- preview e seleção do display -------------------------------------------------
    def update_preview(self):
        frame = self.cam.read()
        if frame is not None:
            self.scale = PREVIEW_W / frame.shape[1]
            view = cv2.resize(frame, None, fx=self.scale, fy=self.scale)
            png = cv2.imencode(".png", view)[1].tobytes()
            self.photo = tk.PhotoImage(data=base64.b64encode(png))   # manter referência
            self.canvas.config(height=view.shape[0])
            self.canvas.delete("img")
            self.canvas.create_image(0, 0, anchor="nw", image=self.photo, tags="img")
            self.canvas.tag_raise("roi")
        self.root.after(60, self.update_preview)

    def on_press(self, e):
        self.drag_start = (e.x, e.y)

    def on_drag(self, e):
        self.canvas.delete("roi")
        self.canvas.create_rectangle(*self.drag_start, e.x, e.y, outline="yellow", tags="roi")

    def on_release(self, e):
        x, y, w, h = lm.roi_from_points(self.drag_start, (e.x, e.y))
        s = self.scale
        self.roi = (int(x / s), int(y / s), int(w / s), int(h / s))    # tela -> frame
        self.status.config(text=f"Display selecionado: {self.roi}")

    # ---- etapa 1: qualidade --------------------------------------------------------------
    def test_quality(self):
        if not self.roi:
            return self.status.config(text="Selecione o display primeiro")
        img = self.cam.median_crop(self.roi, 8)
        if img is None:
            return self.status.config(text="Área inválida")
        report = lm.check_quality(img)        # passe reference=... se tiver uma
        text = report.summary()
        if report.issues:
            text += "\n" + "\n".join(f"- {i.suggestion}" for i in report.issues)
        self.status.config(text=text)

    # ---- etapas 2 e 3: configuração e captura -------------------------------------------
    def start(self):
        if not self.roi or (self.worker and self.worker.is_alive()):
            return
        cfg = lm.CaptureConfig(interval_s=2, max_images=10, log_path="leituras.csv", unit="V")
        try:
            session = lm.CaptureSession(self.cam, lm.RoboflowReader(), cfg, self.roi)
        except (ValueError, RuntimeError) as err:
            return self.status.config(text=str(err))
        self.worker = lm.CaptureWorker(session)
        self.worker.start()
        self.poll_results()

    def poll_results(self):
        while not self.worker.results.empty():
            r = self.worker.results.get_nowait()
            if r is None:                                     # terminou
                msg = f"Erro: {self.worker.error}" if self.worker.error else "Captura concluída"
                return self.status.config(text=msg)
            color = {"ok": "green", "duvidosa": "orange", "falha": "red"}[r.status]
            self.value.config(text=f"{r.reading.text or '—'} {r.unit}", fg=color)
            self.status.config(text=r.line())
        self.root.after(100, self.poll_results)

    def stop(self):
        if self.worker:
            self.worker.stop()

    def close(self):
        self.stop()
        if self.worker:
            self.worker.join(3)
        self.cam.release()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Leitura do multímetro")
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
