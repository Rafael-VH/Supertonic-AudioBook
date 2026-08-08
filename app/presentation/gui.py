"""Interfaz gráfica (Tkinter) para el conversor de capítulos (capa de presentación).

Recibe las dependencias ya inyectadas desde la raíz de composición
(``main.py``): la fábrica de use case y el repositorio. No importa
``data/`` ni instancia implementaciones concretas.
"""

import logging
import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Callable, List

from domain.entities.capitulo import Capitulo
from domain.repositories.motor_tts import DEFAULT_SPEED, DEFAULT_TTS_STEPS, DEFAULT_VOICE
from domain.repositories.repositorio_archivos import RepositorioArchivos
from domain.use_cases.formato import FORMATOS_NATIVOS
from domain.use_cases.procesar_capitulo import ProcesarCapitulo

VOCES: tuple = ("M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5")
"""Voces integradas del modelo supertonic-3 (M1-M5, F1-F5)."""


class _LogHaciaCola(logging.Handler):
    """Handler de logging que reenvía los mensajes a la cola de la UI."""

    def __init__(self, cola: "queue.Queue") -> None:
        super().__init__(level=logging.INFO)
        self._cola = cola
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._cola.put(("log", record.levelname.lower(), self.format(record)))
        except Exception:
            pass


class AppLector(tk.Tk):
    """Ventana principal del conversor."""

    def __init__(
        self,
        *,
        fabrica_use_case: Callable[[str], ProcesarCapitulo],
        repositorio: RepositorioArchivos,
        carpeta_base: Path,
    ) -> None:
        """Args:
            fabrica_use_case: Crea ``ProcesarCapitulo`` para una voz dada.
            repositorio: Acceso a los capítulos en disco (inyectado).
            carpeta_base: Carpeta base de la app (modelo/, archivos/, audio/).
        """
        super().__init__()
        self._fabrica_use_case = fabrica_use_case
        self._repositorio = repositorio
        self._carpeta_base = carpeta_base

        self.title("Supertonic-AudioBook — Conversor de capítulos a audio")
        self.geometry("660x720")
        self.minsize(580, 640)

        self._cola: "queue.Queue" = queue.Queue()
        self._cancelar = threading.Event()
        self._hilo: threading.Thread | None = None
        self._en_ejecucion = False
        self._archivos: List[Path] = []
        self._seleccion: List[Path] = []

        self._handler_log = _LogHaciaCola(self._cola)
        logging.getLogger().addHandler(self._handler_log)

        self._construir_widgets()
        self.after(100, self._drenar_cola)
        self._refrescar_archivos()

    # ------------------------------------------------------------------ UI

    def _construir_widgets(self) -> None:
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        # --- Carpeta de entrada + lista de capítulos ---
        f_entrada = ttk.LabelFrame(main, text="Capítulos de entrada", padding=8)
        f_entrada.pack(fill="x")

        fila = ttk.Frame(f_entrada)
        fila.pack(fill="x")
        ttk.Label(fila, text="Carpeta:").pack(side="left")
        self._var_carpeta_in = tk.StringVar(value=str(self._carpeta_base / "archivos"))
        ttk.Entry(fila, textvariable=self._var_carpeta_in).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(fila, text="Examinar…", command=self._elegir_carpeta_in).pack(side="left")

        lista_frame = ttk.Frame(f_entrada)
        lista_frame.pack(fill="both", expand=True, pady=(8, 4))
        scroll = ttk.Scrollbar(lista_frame, orient="vertical")
        self.lista = tk.Listbox(
            lista_frame,
            selectmode="extended",
            height=8,
            activestyle="dotbox",
            yscrollcommand=scroll.set,
        )
        scroll.config(command=self.lista.yview)
        scroll.pack(side="right", fill="y")
        self.lista.pack(side="left", fill="both", expand=True)

        botones = ttk.Frame(f_entrada)
        botones.pack(fill="x")
        ttk.Button(botones, text="Todo", width=8, command=self._seleccionar_todo).pack(side="left")
        ttk.Button(botones, text="Nada", width=8, command=self._limpiar_seleccion).pack(side="left", padx=6)
        ttk.Button(botones, text="Refrescar", command=self._refrescar_archivos).pack(side="left")
        ttk.Label(
            botones, text="Ctrl+clic para elegir varios; vacío = todos", foreground="#666"
        ).pack(side="right")

        # --- Carpeta de salida ---
        f_salida = ttk.LabelFrame(main, text="Salida de audio", padding=8)
        f_salida.pack(fill="x", pady=(10, 0))
        fila = ttk.Frame(f_salida)
        fila.pack(fill="x")
        ttk.Label(fila, text="Carpeta:").pack(side="left")
        self._var_carpeta_out = tk.StringVar(value=str(self._carpeta_base / "audio"))
        ttk.Entry(fila, textvariable=self._var_carpeta_out).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(fila, text="Examinar…", command=self._elegir_carpeta_out).pack(side="left")

        # --- Opciones de síntesis ---
        f_opciones = ttk.LabelFrame(main, text="Opciones de síntesis", padding=8)
        f_opciones.pack(fill="x", pady=(10, 0))

        fila_formato = ttk.Frame(f_opciones)
        fila_formato.pack(fill="x")
        ttk.Label(fila_formato, text="Formatos:").pack(side="left")
        self._var_formato = {}
        for f in FORMATOS_NATIVOS:
            self._var_formato[f] = tk.BooleanVar(value=(f in ("wav", "mp3")))
            ttk.Checkbutton(
                fila_formato, text=f.upper(), variable=self._var_formato[f]
            ).pack(side="left", padx=4)

        fila_voz = ttk.Frame(f_opciones)
        fila_voz.pack(fill="x", pady=(6, 0))
        ttk.Label(fila_voz, text="Voz:").pack(side="left")
        self._var_voz = tk.StringVar(value=DEFAULT_VOICE)
        ttk.Combobox(fila_voz, textvariable=self._var_voz, values=VOCES, width=6, state="readonly").pack(side="left", padx=6)

        ttk.Label(fila_voz, text="   Pasos:").pack(side="left")
        self._var_steps = tk.IntVar(value=DEFAULT_TTS_STEPS)
        ttk.Scale(
            fila_voz,
            from_=5,
            to=12,
            variable=self._var_steps,
            orient="horizontal",
            length=160,
        ).pack(side="left")
        ttk.Label(fila_voz, textvariable=self._var_steps, width=2).pack(side="left")

        fila_speed = ttk.Frame(f_opciones)
        fila_speed.pack(fill="x", pady=(6, 0))
        ttk.Label(fila_speed, text="Velocidad:").pack(side="left")
        self._var_speed = tk.DoubleVar(value=DEFAULT_SPEED)
        ttk.Scale(
            fila_speed,
            from_=0.7,
            to=2.0,
            variable=self._var_speed,
            orient="horizontal",
            length=160,
        ).pack(side="left")
        ttk.Label(fila_speed, textvariable=self._var_speed, width=4).pack(side="left")
        ttk.Label(
            fila_speed,
            text="   (pasos = más calidad, más lento)",
            foreground="#666",
        ).pack(side="left")

        # --- Acciones ---
        f_accion = ttk.Frame(main)
        f_accion.pack(fill="x", pady=(12, 0))
        self._btn_procesar = ttk.Button(f_accion, text="▶  Procesar", command=self._procesar)
        self._btn_procesar.pack(side="left")
        self._btn_cancelar = ttk.Button(
            f_accion, text="■  Cancelar", command=self._cancelar_accion, state="disabled"
        )
        self._btn_cancelar.pack(side="left", padx=6)

        # --- Progreso ---
        self._barra = ttk.Progressbar(main, maximum=100)
        self._barra.pack(fill="x", pady=(12, 4))
        self._lbl_estado = ttk.Label(main, text="Listo.", anchor="w")
        self._lbl_estado.pack(fill="x")

        # --- Registro ---
        f_log = ttk.LabelFrame(main, text="Registro", padding=4)
        f_log.pack(fill="both", expand=True, pady=(8, 0))
        self._txt = scrolledtext.ScrolledText(f_log, height=12, state="disabled", wrap="word")
        self._txt.pack(fill="both", expand=True)
        self._txt.tag_configure("info", foreground="#222")
        self._txt.tag_configure("warning", foreground="#b45309")
        self._txt.tag_configure("error", foreground="#b91c1c")
        self._txt.tag_configure("debug", foreground="#888")

    # ------------------------------------------------------------- acciones

    def _elegir_carpeta_in(self) -> None:
        carpeta = filedialog.askdirectory(initialdir=self._var_carpeta_in.get())
        if carpeta:
            self._var_carpeta_in.set(carpeta)
            self._refrescar_archivos()

    def _elegir_carpeta_out(self) -> None:
        carpeta = filedialog.askdirectory(initialdir=self._var_carpeta_out.get())
        if carpeta:
            self._var_carpeta_out.set(carpeta)

    def _refrescar_archivos(self) -> None:
        self._archivos = self._repositorio.listar_archivos_md(self._var_carpeta_in.get())
        self.lista.delete(0, "end")
        for archivo in self._archivos:
            self.lista.insert("end", archivo.name)

    def _seleccionar_todo(self) -> None:
        if self.lista.size():
            self.lista.selection_set(0, "end")

    def _limpiar_seleccion(self) -> None:
        self.lista.selection_clear(0, "end")

    def _procesar(self) -> None:
        if self._en_ejecucion:
            return

        formatos = [f for f in FORMATOS_NATIVOS if self._var_formato[f].get()]
        if not formatos:
            messagebox.showwarning("Falta elegir formato", "Elegí al menos un formato de salida.")
            return

        self._seleccion = [self._archivos[i] for i in self.lista.curselection()]
        if not self._seleccion:
            self._seleccion = list(self._archivos)
        if not self._seleccion:
            messagebox.showwarning(
                "Sin capítulos",
                "No hay archivos .md en la carpeta de entrada.",
            )
            return

        self._set_ejecutando(True)
        self._cancelar.clear()
        self._hilo = threading.Thread(target=self._trabajo, daemon=True)
        self._hilo.start()

    def _cancelar_accion(self) -> None:
        if not self._en_ejecucion:
            return
        self._cancelar.set()
        self._btn_cancelar.config(state="disabled")
        self._lbl_estado.config(text="Cancelando (exporta lo generado hasta ahora)…")

    # ------------------------------------------------------------- worker

    def _trabajo(self) -> None:
        try:
            formatos = [f for f in FORMATOS_NATIVOS if self._var_formato[f].get()]
            voz = self._var_voz.get()
            steps = int(round(self._var_steps.get()))
            speed = float(self._var_speed.get())
            salida = Path(self._var_carpeta_out.get())
            self._repositorio.crear_carpetas_si_no_existen(str(salida))

            use_case = self._fabrica_use_case(voz)
            total_caps = len(self._seleccion)
            for i, ruta in enumerate(self._seleccion, 1):
                if self._cancelar.is_set():
                    break
                self._cola.put(("capitulo", i, total_caps, ruta.name))
                use_case.procesar(
                    Capitulo(ruta),
                    salida / ruta.stem,
                    steps=steps,
                    speed=speed,
                    formatos=formatos,
                    on_progreso=self._cb_progreso,
                    debe_detenerse=self._cb_detenerse,
                )
            self._cola.put(("fin", not self._cancelar.is_set(), total_caps))
        except Exception as exc:
            logging.getLogger("gui").exception("Error en el hilo de trabajo")
            self._cola.put(("error", str(exc)))

    def _cb_progreso(self, actual: int, total: int) -> None:
        self._cola.put(("progreso", actual, total))

    def _cb_detenerse(self) -> bool:
        return self._cancelar.is_set()

    # ------------------------------------------------------- consumo de cola

    def _drenar_cola(self) -> None:
        try:
            while True:
                self._manejar_msg(self._cola.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._drenar_cola)

    def _manejar_msg(self, msg: tuple) -> None:
        tipo = msg[0]
        if tipo == "log":
            _, nivel, texto = msg
            self._escribir_log(texto, nivel)
        elif tipo == "capitulo":
            _, i, n, nombre = msg
            self._lbl_estado.config(text=f"Capítulo {i} de {n}: {nombre}")
            self._barra.config(value=0)
        elif tipo == "progreso":
            _, actual, total = msg
            self._barra.config(value=actual / total * 100 if total else 0)
            self._lbl_estado.config(text=f"{actual}/{total} segmentos sintetizados")
        elif tipo == "fin":
            _, exito, n = msg
            self._set_ejecutando(False)
            if exito:
                self._lbl_estado.config(text=f"Listo: {n} capítulo(s) procesado(s).")
                messagebox.showinfo("Completado", f"Se procesaron {n} capítulo(s).")
            else:
                self._lbl_estado.config(text="Cancelado por el usuario.")
                messagebox.showwarning("Cancelado", "Se exportó lo generado hasta el momento.")
        elif tipo == "error":
            _, texto = msg
            self._set_ejecutando(False)
            self._lbl_estado.config(text="Error.")
            messagebox.showerror("Error", texto)

    def _escribir_log(self, texto: str, nivel: str = "info") -> None:
        self._txt.config(state="normal")
        self._txt.insert("end", texto + "\n", nivel if nivel in ("info", "warning", "error", "debug") else "info")
        self._txt.see("end")
        self._txt.config(state="disabled")

    def _set_ejecutando(self, activo: bool) -> None:
        self._en_ejecucion = activo
        self._btn_procesar.config(state="disabled" if activo else "normal")
        self._btn_cancelar.config(state="normal" if activo else "disabled")
