"""Interfaz gráfica (Tkinter) para el conversor de archivos a audio (capa de presentación).

Recibe las dependencias ya inyectadas desde la raíz de composición
(``main.py``): la fábrica de use case y el repositorio. No importa
``data/`` ni instancia implementaciones concretas.
"""

import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk
from typing import Callable, Dict, List

from domain.entities.capitulo import Capitulo
from domain.repositories.motor_tts import DEFAULT_SPEED, DEFAULT_TTS_STEPS, DEFAULT_VOICE
from domain.repositories.repositorio_archivos import RepositorioArchivos
from domain.repositories.repositorio_preferencias import RepositorioPreferencias
from domain.use_cases.formato import FORMATOS_NATIVOS
from domain.use_cases.procesar_capitulo import ProcesarCapitulo

log = logging.getLogger("lector")

VOCES: tuple = ("M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5")
"""Voces integradas del modelo supertonic-3 (M1-M5, F1-F5)."""

UMBRAL_ANCHO = 900
"""Ancho mínimo de ventana para mostrar los paneles lado a lado (responsive)."""

PALETA_CLARA: dict = {
    "fondo": "#F4F1FA",
    "superficie": "#FFFFFF",
    "superficie_variante": "#E7E0EC",
    "primario": "#6750A4",
    "primario_claro": "#EADDFF",
    "primario_vivo": "#7B67C8",
    "sobre_primario": "#FFFFFF",
    "texto": "#1C1B1F",
    "texto_secundario": "#79747E",
    "borde": "#CAC4D0",
    "advertencia": "#B45309",
    "error": "#B3261E",
    "error_vivo": "#D0453E",
    "sobre_error": "#FFFFFF",
    "snackbar_fondo": "#322F35",
    "snackbar_texto": "#FFFFFF",
}
"""Paleta clara inspirada en Material Design 3 (baseline púrpura)."""

PALETA_OSCURA: dict = {
    "fondo": "#141218",
    "superficie": "#211F26",
    "superficie_variante": "#49454F",
    "primario": "#D0BCFF",
    "primario_claro": "#4F378B",
    "primario_vivo": "#BBA6F4",
    "sobre_primario": "#381E72",
    "texto": "#E6E0E9",
    "texto_secundario": "#CAC4D0",
    "borde": "#4A4458",
    "advertencia": "#FDD663",
    "error": "#F2B8B5",
    "error_vivo": "#F8C7C4",
    "sobre_error": "#381E72",
    "snackbar_fondo": "#E6E0E9",
    "snackbar_texto": "#141218",
}
"""Paleta oscura inspirada en Material Design 3 (baseline púrpura)."""


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
        repositorio_preferencias: RepositorioPreferencias,
    ) -> None:
        """Args:
            fabrica_use_case: Crea ``ProcesarCapitulo`` para una voz dada.
            repositorio: Acceso a los archivos en disco (inyectado).
            carpeta_base: Carpeta base de la app (modelo/, archivos/, audio/).
            repositorio_preferencias: Persistencia de preferencias de la UI.
        """
        super().__init__()
        self._fabrica_use_case = fabrica_use_case
        self._repositorio = repositorio
        self._carpeta_base = carpeta_base
        self._repositorio_preferencias = repositorio_preferencias

        self.title("Supertonic-AudioBook — Conversor de archivos a audio")
        self.geometry("660x720")
        self.minsize(580, 640)

        self._tema_oscuro = False
        self._paleta = dict(PALETA_CLARA)
        self._preferencias_cargadas = self._repositorio_preferencias.cargar()

        self._cola: "queue.Queue" = queue.Queue()
        self._cancelar = threading.Event()
        self._hilo: threading.Thread | None = None
        self._en_ejecucion = False
        self._archivos: List[Path] = []
        self._seleccion: List[Path] = []

        self._handler_log = _LogHaciaCola(self._cola)
        logging.getLogger().addHandler(self._handler_log)
        logging.getLogger().setLevel(logging.INFO)

        self._construir_widgets()
        self._aplicar_preferencias(self._preferencias_cargadas)
        self.after(100, self._drenar_cola)
        self._refrescar_archivos()
        self._aplicar_tema(bool(self._preferencias_cargadas.get("tema_oscuro", False)))
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    # ------------------------------------------------------------------ UI

    def _construir_widgets(self) -> None:
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        # --- Cabecera con título y alternador de tema ---
        cabecera = ttk.Frame(main)
        cabecera.pack(fill="x", pady=(0, 10))
        ttk.Label(
            cabecera,
            text="Supertonic-AudioBook",
            style="Titulo.TLabel",
        ).pack(side="left")
        self._btn_tema = ttk.Button(cabecera, text="Modo oscuro", command=self._cambiar_tema)
        self._btn_tema.pack(side="right")

        # --- Zona de contenido: pestañas (angosto) o columnas lado a lado (ancho) ---
        self._contenido = ttk.Frame(main)
        self._contenido.pack(fill="both", expand=True)
        self._notebook = ttk.Notebook(self._contenido)
        self._modo_ancho = False

        self._panel_entrada = ttk.Frame(self._contenido, padding=4)
        self._panel_sintesis = ttk.Frame(self._contenido, padding=4)

        self._construir_panel_entrada()
        self._construir_panel_sintesis()

        self._notebook.add(self._panel_entrada, text="Entrada y salida")
        self._notebook.add(self._panel_sintesis, text="Síntesis y registro")
        self._notebook.pack(fill="both", expand=True)

        # --- Acciones ---
        f_accion = ttk.Frame(main)
        f_accion.pack(fill="x", pady=(12, 0))
        self._btn_procesar = ttk.Button(
            f_accion, text="▶  Procesar", style="Principal.TButton", command=self._procesar
        )
        self._btn_procesar.pack(side="left")
        self._btn_cancelar = ttk.Button(
            f_accion,
            text="■  Cancelar",
            command=self._cancelar_accion,
            state="disabled",
        )
        self._btn_cancelar.pack(side="left", padx=6)

        # --- Progreso ---
        self._barra = ttk.Progressbar(main, maximum=100)
        self._barra.pack(fill="x", pady=(12, 4))
        fila_progreso = ttk.Frame(main)
        fila_progreso.pack(fill="x")
        self._lbl_estado = ttk.Label(fila_progreso, text="Listo.", anchor="w")
        self._lbl_estado.pack(side="left", fill="x", expand=True)
        self._lbl_porcentaje = ttk.Label(
            fila_progreso, text="0%", style="Hint.TLabel", width=5, anchor="e"
        )
        self._lbl_porcentaje.pack(side="right")

        # --- Snackbar (aviso flotante estilo Material) ---
        self._snackbar = ttk.Label(
            self, text="", style="Snackbar.TLabel", padding=(16, 10), anchor="w"
        )
        self._snackbar_id: str | None = None

        self.bind("<Configure>", self._reajustar_layout)

    def _construir_panel_entrada(self) -> None:
        panel = self._panel_entrada

        # --- Carpeta de salida ---
        f_salida = ttk.LabelFrame(panel, text="Salida de audio", style="Tarjeta.TLabelframe", padding=8)
        f_salida.pack(fill="x")
        fila = ttk.Frame(f_salida, style="Tarjeta.TFrame")
        fila.pack(fill="x")
        ttk.Label(fila, text="Carpeta:", style="CardLabel.TLabel").pack(side="left")
        self._var_carpeta_out = tk.StringVar(value=str(self._carpeta_base / "audio"))
        ttk.Entry(fila, textvariable=self._var_carpeta_out).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(fila, text="Examinar…", command=self._elegir_carpeta_out).pack(side="left")

        # --- Carpeta de origen (selección separada de la lista) ---
        f_origen = ttk.LabelFrame(panel, text="Carpeta de origen", style="Tarjeta.TLabelframe", padding=8)
        f_origen.pack(fill="x", pady=(10, 0))
        fila = ttk.Frame(f_origen, style="Tarjeta.TFrame")
        fila.pack(fill="x")
        ttk.Label(fila, text="Carpeta:", style="CardLabel.TLabel").pack(side="left")
        self._var_carpeta_in = tk.StringVar(value=str(self._carpeta_base / "archivos"))
        ttk.Entry(fila, textvariable=self._var_carpeta_in).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(fila, text="Examinar…", command=self._elegir_carpeta_in).pack(side="left")

        # --- Archivos encontrados (lista) ---
        f_lista = ttk.LabelFrame(panel, text="Archivos Encontrados", style="Tarjeta.TLabelframe", padding=8)
        f_lista.pack(fill="both", expand=True, pady=(10, 0))

        fila_lista = ttk.Frame(f_lista, style="Tarjeta.TFrame")
        fila_lista.pack(fill="both", expand=True)

        lista_frame = ttk.Frame(fila_lista, style="Tarjeta.TFrame")
        lista_frame.pack(side="left", fill="both", expand=True)
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
        self.lista.bind("<<ListboxSelect>>", self._actualizar_conteo)

        panel_botones = ttk.Frame(fila_lista, style="Tarjeta.TFrame")
        panel_botones.pack(side="left", fill="y", padx=(8, 0))
        ttk.Button(panel_botones, text="Todo", width=9, command=self._seleccionar_todo).pack(fill="x")
        ttk.Button(panel_botones, text="Nada", width=9, command=self._limpiar_seleccion).pack(fill="x", pady=(6, 0))
        ttk.Button(panel_botones, text="Refrescar", width=9, command=self._refrescar_archivos).pack(fill="x", pady=(6, 0))
        ttk.Label(panel_botones, text="", style="CardHint.TLabel").pack(fill="x", expand=True)
        self._lbl_conteo = ttk.Label(panel_botones, text="", style="CardHint.TLabel", anchor="center")
        self._lbl_conteo.pack(fill="x", pady=(6, 0))
        ttk.Label(
            panel_botones,
            text="Ctrl+clic\npara varios;\nvacío = todos",
            style="CardHint.TLabel",
            justify="center",
            anchor="n",
        ).pack(fill="x", pady=(2, 0))

    def _construir_panel_sintesis(self) -> None:
        panel = self._panel_sintesis

        # --- Opciones de síntesis ---
        f_opciones = ttk.LabelFrame(
            panel, text="Opciones de síntesis", style="Tarjeta.TLabelframe", padding=12
        )
        f_opciones.pack(fill="x")
        f_opciones.columnconfigure(1, weight=1)

        # Formato (chips)
        ttk.Label(f_opciones, text="Formato", style="Etiqueta.TLabel").grid(
            row=0, column=0, sticky="nw", pady=(2, 0)
        )
        fila_formato = ttk.Frame(f_opciones, style="Tarjeta.TFrame")
        fila_formato.grid(row=0, column=1, sticky="w", padx=(12, 0))
        self._var_formato = {}
        for i, f in enumerate(FORMATOS_NATIVOS):
            self._var_formato[f] = tk.BooleanVar(value=(f in ("wav", "mp3")))
            ttk.Checkbutton(
                fila_formato,
                text=f.upper(),
                variable=self._var_formato[f],
                style="Chip.TCheckbutton",
            ).grid(row=0, column=i, padx=(0, 8))

        # Voz
        ttk.Label(f_opciones, text="Voz", style="Etiqueta.TLabel").grid(
            row=1, column=0, sticky="nw", pady=(14, 0)
        )
        fila_voz = ttk.Frame(f_opciones, style="Tarjeta.TFrame")
        fila_voz.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(10, 0))
        self._var_voz = tk.StringVar(value=DEFAULT_VOICE)
        ttk.Combobox(
            fila_voz, textvariable=self._var_voz, values=VOCES, width=6, state="readonly"
        ).pack(side="left")
        ttk.Label(
            fila_voz, text="Modelo supertonic-3", style="CardHint.TLabel"
        ).pack(side="left", padx=(10, 0))

        # Pasos
        ttk.Label(f_opciones, text="Pasos", style="Etiqueta.TLabel").grid(
            row=2, column=0, sticky="nw", pady=(16, 0)
        )
        fila_pasos = ttk.Frame(f_opciones, style="Tarjeta.TFrame")
        fila_pasos.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=(12, 0))
        fila_pasos.columnconfigure(0, weight=1)
        self._var_steps = tk.IntVar(value=DEFAULT_TTS_STEPS)
        self._lbl_valor_steps = tk.StringVar(value=str(DEFAULT_TTS_STEPS))
        ttk.Scale(
            fila_pasos,
            from_=5,
            to=12,
            variable=self._var_steps,
            orient="horizontal",
            command=lambda _v: self._lbl_valor_steps.set(str(int(round(self._var_steps.get())))),
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            fila_pasos, textvariable=self._lbl_valor_steps, style="Valor.TLabel", width=3, anchor="center"
        ).grid(row=0, column=1, padx=(10, 0))
        ttk.Label(
            fila_pasos, text="más calidad = más lento", style="CardHint.TLabel"
        ).grid(row=0, column=2, padx=(12, 0))

        # Velocidad
        ttk.Label(f_opciones, text="Velocidad", style="Etiqueta.TLabel").grid(
            row=3, column=0, sticky="nw", pady=(14, 0)
        )
        fila_speed = ttk.Frame(f_opciones, style="Tarjeta.TFrame")
        fila_speed.grid(row=3, column=1, sticky="ew", padx=(12, 0), pady=(10, 0))
        fila_speed.columnconfigure(0, weight=1)
        self._var_speed = tk.DoubleVar(value=DEFAULT_SPEED)
        self._lbl_valor_speed = tk.StringVar(value=f"{DEFAULT_SPEED:.2f}x")
        ttk.Scale(
            fila_speed,
            from_=0.7,
            to=2.0,
            variable=self._var_speed,
            orient="horizontal",
            command=lambda _v: self._lbl_valor_speed.set(f"{self._var_speed.get():.2f}x"),
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            fila_speed, textvariable=self._lbl_valor_speed, style="Valor.TLabel", width=5, anchor="center"
        ).grid(row=0, column=1, padx=(10, 0))
        ttk.Label(
            fila_speed, text="más rápido / más lento", style="CardHint.TLabel"
        ).grid(row=0, column=2, padx=(12, 0))

        # --- Registro ---
        f_log = ttk.LabelFrame(panel, text="Registro", style="Tarjeta.TLabelframe", padding=4)
        f_log.pack(fill="both", expand=True, pady=(8, 0))
        self._txt = scrolledtext.ScrolledText(f_log, width=40, height=12, state="disabled", wrap="word")
        self._txt.pack(fill="both", expand=True)

    def _reajustar_layout(self, evento) -> None:
        if evento.widget is not self:
            return
        ancho = evento.width
        if ancho >= UMBRAL_ANCHO:
            if not self._modo_ancho:
                self._modo_columnas()
        elif self._modo_ancho:
            self._modo_pestanas()

    def _modo_columnas(self) -> None:
        self._modo_ancho = True
        self._notebook.forget(self._panel_entrada)
        self._notebook.forget(self._panel_sintesis)
        self._notebook.pack_forget()
        self._contenido.rowconfigure(0, weight=1)
        self._contenido.columnconfigure(0, weight=1, uniform="col")
        self._contenido.columnconfigure(1, weight=1, uniform="col")
        self._panel_entrada.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self._panel_sintesis.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    def _modo_pestanas(self) -> None:
        self._modo_ancho = False
        self._panel_entrada.grid_forget()
        self._panel_sintesis.grid_forget()
        self._contenido.rowconfigure(0, weight=0)
        self._contenido.columnconfigure(0, weight=0, uniform="")
        self._contenido.columnconfigure(1, weight=0, uniform="")
        self._notebook.add(self._panel_entrada, text="Entrada y salida")
        self._notebook.add(self._panel_sintesis, text="Síntesis y registro")
        self._notebook.pack(fill="both", expand=True)

    # ------------------------------------------------------------- temas

    def _cambiar_tema(self) -> None:
        self._aplicar_tema(not self._tema_oscuro)
        self._guardar_preferencias()

    def _aplicar_tema(self, oscuro: bool) -> None:
        self._tema_oscuro = oscuro
        c = PALETA_OSCURA if oscuro else PALETA_CLARA
        self._paleta = c

        estilo = ttk.Style(self)
        estilo.theme_use("clam")

        estilo.configure(
            ".",
            background=c["fondo"],
            foreground=c["texto"],
            fieldbackground=c["superficie"],
            bordercolor=c["borde"],
            lightcolor=c["fondo"],
            darkcolor=c["borde"],
            troughcolor=c["superficie_variante"],
            font=("Segoe UI", 10),
        )
        estilo.configure("TFrame", background=c["fondo"])
        estilo.configure("TLabel", background=c["fondo"], foreground=c["texto"])
        estilo.configure(
            "Titulo.TLabel",
            background=c["fondo"],
            foreground=c["primario"],
            font=("Segoe UI", 16, "bold"),
        )
        estilo.configure("Hint.TLabel", background=c["fondo"], foreground=c["texto_secundario"])
        estilo.configure(
            "CardLabel.TLabel",
            background=c["superficie"],
            foreground=c["texto"],
        )
        estilo.configure(
            "CardHint.TLabel",
            background=c["superficie"],
            foreground=c["texto_secundario"],
        )
        estilo.configure(
            "Etiqueta.TLabel",
            background=c["superficie"],
            foreground=c["texto_secundario"],
            font=("Segoe UI", 10, "bold"),
        )
        estilo.configure(
            "Valor.TLabel",
            background=c["superficie"],
            foreground=c["primario"],
            font=("Segoe UI", 10, "bold"),
        )
        estilo.configure(
            "Snackbar.TLabel",
            background=c["snackbar_fondo"],
            foreground=c["snackbar_texto"],
            font=("Segoe UI", 10, "bold"),
        )
        estilo.configure(
            "SnackbarError.TLabel",
            background=c["error"],
            foreground=c["sobre_error"],
            font=("Segoe UI", 10, "bold"),
        )

        # Tarjetas (LabelFrame con superficie elevada)
        estilo.configure(
            "Tarjeta.TLabelframe",
            background=c["superficie"],
            bordercolor=c["borde"],
            relief="solid",
            borderwidth=1,
        )
        estilo.configure(
            "Tarjeta.TLabelframe.Label",
            background=c["superficie"],
            foreground=c["primario"],
            font=("Segoe UI", 10, "bold"),
        )
        estilo.configure("Tarjeta.TFrame", background=c["superficie"])

        # Pestañas (Notebook)
        estilo.configure(
            "TNotebook",
            background=c["fondo"],
            borderwidth=0,
            tabmargins=(4, 6, 4, 0),
        )
        estilo.configure(
            "TNotebook.Tab",
            background=c["superficie_variante"],
            foreground=c["texto_secundario"],
            padding=(20, 8),
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        estilo.map(
            "TNotebook.Tab",
            background=[("selected", c["superficie"])],
            foreground=[("selected", c["primario"])],
        )

        # Botón principal (relleno)
        estilo.configure(
            "Principal.TButton",
            background=c["primario"],
            foreground=c["sobre_primario"],
            borderwidth=0,
            padding=(18, 9),
            font=("Segoe UI", 10, "bold"),
            focusthickness=0,
        )
        estilo.map(
            "Principal.TButton",
            background=[
                ("active", c["primario_vivo"]),
                ("disabled", c["superficie_variante"]),
            ],
            foreground=[("disabled", c["texto_secundario"])],
        )

        # Botón estándar (contorno): Examinar…, Todo/Nada/Refrescar, tema, cancelar
        estilo.configure(
            "TButton",
            background=c["superficie"],
            foreground=c["primario"],
            bordercolor=c["primario"],
            borderwidth=1,
            padding=(14, 8),
            font=("Segoe UI", 10),
            focusthickness=0,
        )
        estilo.map(
            "TButton",
            background=[("active", c["primario_claro"])],
            foreground=[("active", c["primario"])],
        )

        # Entrada
        estilo.configure(
            "TEntry",
            fieldbackground=c["superficie"],
            foreground=c["texto"],
            insertcolor=c["texto"],
            bordercolor=c["borde"],
            padding=(8, 6),
        )
        estilo.map("TEntry", bordercolor=[("focus", c["primario"])])

        # Checkbutton, combobox, sliders, barra y scrollbar
        estilo.configure(
            "TCheckbutton",
            background=c["superficie"],
            foreground=c["texto"],
            focuscolor=c["fondo"],
        )
        estilo.map(
            "TCheckbutton",
            background=[("active", c["superficie"])],
            indicatorcolor=[("selected", c["primario"]), ("!selected", c["superficie"])],
        )
        # Chip de formato (checkbox tipo píldora)
        estilo.configure(
            "Chip.TCheckbutton",
            background=c["superficie_variante"],
            foreground=c["texto"],
            indicatorcolor=c["superficie_variante"],
            padding=(12, 6),
            focuscolor=c["fondo"],
        )
        estilo.map(
            "Chip.TCheckbutton",
            background=[("selected", c["primario_claro"]), ("active", c["primario_claro"])],
            foreground=[("selected", c["primario"]), ("active", c["texto"])],
            indicatorcolor=[("selected", c["primario"]), ("!selected", c["superficie_variante"])],
        )
        estilo.configure(
            "TCombobox",
            fieldbackground=c["superficie"],
            foreground=c["texto"],
            arrowcolor=c["primario"],
            bordercolor=c["borde"],
        )
        estilo.map(
            "TCombobox",
            fieldbackground=[("readonly", c["superficie"])],
            foreground=[("readonly", c["texto"])],
        )
        estilo.configure(
            "Horizontal.TScale",
            background=c["superficie"],
            troughcolor=c["superficie_variante"],
        )
        estilo.map("Horizontal.TScale", background=[("active", c["superficie"])])
        estilo.configure(
            "Horizontal.TProgressbar",
            background=c["primario"],
            troughcolor=c["superficie_variante"],
            borderwidth=0,
        )
        estilo.configure(
            "Vertical.TScrollbar",
            background=c["superficie_variante"],
            troughcolor=c["fondo"],
            borderwidth=0,
            arrowcolor=c["texto_secundario"],
        )
        estilo.map("Vertical.TScrollbar", background=[("active", c["primario"])])

        self.configure(bg=c["fondo"])
        self._estilizar_no_ttk()
        if hasattr(self, "_btn_tema"):
            self._btn_tema.config(text="Modo claro" if oscuro else "Modo oscuro")

    def _estilizar_no_ttk(self) -> None:
        c = self._paleta
        self.lista.configure(
            bg=c["superficie"],
            fg=c["texto"],
            selectbackground=c["primario"],
            selectforeground=c["sobre_primario"],
            highlightbackground=c["borde"],
            highlightcolor=c["primario"],
            relief="flat",
            borderwidth=1,
        )
        self._txt.configure(
            bg=c["superficie"],
            fg=c["texto"],
            insertbackground=c["texto"],
            selectbackground=c["primario"],
            selectforeground=c["sobre_primario"],
            relief="flat",
            borderwidth=1,
        )
        self._txt.tag_configure("info", foreground=c["texto"])
        self._txt.tag_configure("warning", foreground=c["advertencia"])
        self._txt.tag_configure("error", foreground=c["error"])
        self._txt.tag_configure("debug", foreground=c["texto_secundario"])

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
        self._actualizar_conteo()

    def _seleccionar_todo(self) -> None:
        if self.lista.size():
            self.lista.selection_set(0, "end")

    def _limpiar_seleccion(self) -> None:
        self.lista.selection_clear(0, "end")
        self._actualizar_conteo()

    # ------------------------------------------------------- preferencias

    def _actualizar_conteo(self, *_args) -> None:
        total = self.lista.size()
        seleccionados = len(self.lista.curselection())
        if seleccionados:
            self._lbl_conteo.config(text=f"{seleccionados}/{total} seleccionados")
        else:
            self._lbl_conteo.config(text=f"{total} archivos" if total else "Sin archivos")

    def _guardar_preferencias(self) -> None:
        try:
            self._repositorio_preferencias.guardar(
                {
                    "tema_oscuro": self._tema_oscuro,
                    "voz": self._var_voz.get(),
                    "steps": int(round(self._var_steps.get())),
                    "speed": float(self._var_speed.get()),
                    "formatos": [f for f in FORMATOS_NATIVOS if self._var_formato[f].get()],
                    "carpeta_in": self._var_carpeta_in.get(),
                    "carpeta_out": self._var_carpeta_out.get(),
                }
            )
        except Exception:
            logging.getLogger("lector").exception("No se pudieron guardar las preferencias")

    def _aplicar_preferencias(self, prefs: Dict[str, object]) -> None:
        if not isinstance(prefs, dict):
            return
        if isinstance(prefs.get("voz"), str) and prefs["voz"] in VOCES:
            self._var_voz.set(prefs["voz"])
        if isinstance(prefs.get("steps"), int):
            self._var_steps.set(max(5, min(12, prefs["steps"])))
            self._lbl_valor_steps.set(str(int(round(self._var_steps.get()))))
        if isinstance(prefs.get("speed"), (int, float)):
            self._var_speed.set(max(0.7, min(2.0, float(prefs["speed"]))))
            self._lbl_valor_speed.set(f"{self._var_speed.get():.2f}x")
        if isinstance(prefs.get("formatos"), list):
            for formato in FORMATOS_NATIVOS:
                self._var_formato[formato].set(formato in prefs["formatos"])
        if isinstance(prefs.get("carpeta_in"), str) and prefs["carpeta_in"]:
            self._var_carpeta_in.set(prefs["carpeta_in"])
        if isinstance(prefs.get("carpeta_out"), str) and prefs["carpeta_out"]:
            self._var_carpeta_out.set(prefs["carpeta_out"])

    def _cerrar(self) -> None:
        self._guardar_preferencias()
        self.destroy()

    def _mostrar_snackbar(self, texto: str, tipo: str = "info") -> None:
        if self._snackbar_id:
            self.after_cancel(self._snackbar_id)
            self._snackbar_id = None
        self._snackbar.config(
            text=texto,
            style="SnackbarError.TLabel" if tipo == "error" else "Snackbar.TLabel",
        )
        self._snackbar.place(relx=0.5, rely=1.0, anchor="s", y=-24, relwidth=0.96)
        self._snackbar.lift()
        self._snackbar_id = self.after(4000, self._ocultar_snackbar)

    def _ocultar_snackbar(self) -> None:
        self._snackbar_id = None
        self._snackbar.place_forget()

    def _procesar(self) -> None:
        if self._en_ejecucion:
            return

        self._guardar_preferencias()

        formatos = [f for f in FORMATOS_NATIVOS if self._var_formato[f].get()]
        if not formatos:
            self._mostrar_snackbar("Elegí al menos un formato de salida.", "error")
            log.warning("No se pudo iniciar: no se eligió ningún formato de salida.")
            return

        self._seleccion = [self._archivos[i] for i in self.lista.curselection()]
        if not self._seleccion:
            self._seleccion = list(self._archivos)
        if not self._seleccion:
            self._mostrar_snackbar("No hay archivos .md en la carpeta de entrada.", "error")
            log.warning("No se pudo iniciar: la carpeta de entrada no tiene archivos .md.")
            return

        log.info(
            "▶ Inicio: %d archivo(s) seleccionado(s) de %d disponible(s).",
            len(self._seleccion),
            len(self._archivos),
        )
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
        log.info("■ Cancelación solicitada: se exporta lo generado hasta el momento.")

    # ------------------------------------------------------------- worker

    def _trabajo(self) -> None:
        inicio = time.monotonic()
        try:
            formatos = [f for f in FORMATOS_NATIVOS if self._var_formato[f].get()]
            voz = self._var_voz.get()
            steps = int(round(self._var_steps.get()))
            speed = float(self._var_speed.get())
            salida = Path(self._var_carpeta_out.get())
            self._repositorio.crear_carpetas_si_no_existen(str(salida))

            log.info("=" * 60)
            log.info("  CONFIGURACIÓN")
            log.info("    Voz: %s   Pasos: %d   Velocidad: %.2fx", voz, steps, speed)
            log.info("    Formatos: %s", ", ".join(f.upper() for f in formatos))
            log.info("    Salida: %s", salida)
            log.info("=" * 60)

            use_case = self._fabrica_use_case(voz)
            total_caps = len(self._seleccion)
            for i, ruta in enumerate(self._seleccion, 1):
                if self._cancelar.is_set():
                    break
                self._cola.put(("capitulo", i, total_caps, ruta.name))
                log.info("▶ Archivo %d/%d: %s", i, total_caps, ruta.name)
                use_case.procesar(
                    Capitulo(ruta),
                    salida / ruta.stem,
                    steps=steps,
                    speed=speed,
                    formatos=formatos,
                    on_progreso=self._cb_progreso,
                    debe_detenerse=self._cb_detenerse,
                )
                log.info("✔ Archivo %d/%d terminado.", i, total_caps)
            elapsed = time.monotonic() - inicio
            self._cola.put(("fin", not self._cancelar.is_set(), total_caps, elapsed))
        except Exception as exc:
            logging.getLogger("gui").exception("Error en el hilo de trabajo")
            self._cola.put(("error", str(exc)))

    def _cb_progreso(self, actual: int, total: int) -> None:
        self._cola.put(("progreso", actual, total))
        paso = max(1, total // 20)
        if actual % paso == 0 or actual == total:
            self._cola.put(("log", "info", f"      Segmento {actual}/{total} sintetizado…"))

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
            self._lbl_estado.config(text=f"Archivo {i} de {n}: {nombre}")
            self._barra.config(value=0)
            self._lbl_porcentaje.config(text="0%")
        elif tipo == "progreso":
            _, actual, total = msg
            pct = actual / total * 100 if total else 0
            self._barra.config(value=pct)
            self._lbl_porcentaje.config(text=f"{pct:.0f}%")
            self._lbl_estado.config(text=f"{actual}/{total} segmentos sintetizados")
        elif tipo == "fin":
            _, exito, n, elapsed = msg
            self._set_ejecutando(False)
            texto_elapsed = self._formatear_tiempo(elapsed)
            if exito:
                self._barra.config(value=100)
                self._lbl_porcentaje.config(text="100%")
                self._lbl_estado.config(text=f"Listo: {n} archivo(s) en {texto_elapsed}.")
                self._mostrar_snackbar(f"Se procesaron {n} archivo(s) en {texto_elapsed}.")
                log.info("=" * 60)
                log.info("✔ PROCESAMIENTO COMPLETADO: %d archivo(s) en %s.", n, texto_elapsed)
                log.info("=" * 60)
            else:
                self._lbl_estado.config(text="Cancelado por el usuario.")
                self._mostrar_snackbar("Se exportó lo generado hasta el momento.")
                log.warning(
                    "✖ Procesamiento cancelado por el usuario tras %s.",
                    texto_elapsed,
                )
        elif tipo == "error":
            _, texto = msg
            self._set_ejecutando(False)
            self._lbl_estado.config(text="Error.")
            self._mostrar_snackbar(texto, "error")
            log.error("✖ ERROR: %s", texto)

    @staticmethod
    def _formatear_tiempo(segundos: float) -> str:
        total = int(segundos)
        if total < 60:
            return f"{total} s"
        minutos, seg = divmod(total, 60)
        if minutos < 60:
            return f"{minutos} min {seg} s"
        horas, min_ = divmod(minutos, 60)
        return f"{horas} h {min_} min"

    def _escribir_log(self, texto: str, nivel: str = "info") -> None:
        self._txt.config(state="normal")
        self._txt.insert("end", texto + "\n", nivel if nivel in ("info", "warning", "error", "debug") else "info")
        self._txt.see("end")
        self._txt.config(state="disabled")

    def _set_ejecutando(self, activo: bool) -> None:
        self._en_ejecucion = activo
        self._btn_procesar.config(state="disabled" if activo else "normal")
        self._btn_cancelar.config(state="normal" if activo else "disabled")
