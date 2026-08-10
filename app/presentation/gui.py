"""Interfaz gráfica (Tkinter) para el conversor de archivos a audio (capa de presentación).

Recibe las dependencias ya inyectadas desde la raíz de composición
(``main.py``): la fábrica de use case y el repositorio. No importa
``data/`` ni instancia implementaciones concretas.
"""

import logging
import queue
import tempfile
import threading
import time
import tkinter as tk
import winsound
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk
from typing import Callable, Dict, List, Optional

from domain.entities.archivo import Archivo
from domain.repositories.motor_tts import (
    DEFAULT_LANG,
    DEFAULT_SPEED,
    DEFAULT_TTS_STEPS,
    DEFAULT_VOICE,
    LANGUAGES_VOZ,
)
from domain.repositories.repositorio_archivos import RepositorioArchivos
from domain.repositories.repositorio_preferencias import RepositorioPreferencias
from domain.use_cases.formato import FORMATOS_NATIVOS
from domain.use_cases.procesar_archivo import ProcesarArchivo
from domain.use_cases.sintetizar_muestra import SintetizarMuestra

log = logging.getLogger("lector")

VOCES: tuple = ("M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5")
"""Voces integradas del modelo supertonic-3 (M1-M5, F1-F5)."""

TEXTO_MUESTRA_IDIOMAS: dict = {
    "es": "Hola, soy la voz de Supertonic. Esta es una muestra de audio.",
    "en": "Hello, I am a Supertonic voice. This is an audio sample.",
    "fr": "Bonjour, je suis une voix Supertonic. Ceci est un échantillon audio.",
    "de": "Hallo, ich bin eine Supertonic-Stimme. Das ist eine Audioprobe.",
    "pt": "Olá, eu sou uma voz Supertonic. Esta é uma amostra de áudio.",
    "it": "Ciao, sono una voce Supertonic. Questo è un campione audio.",
    "nl": "Hallo, ik ben een Supertonic-stem. Dit is een audiofragment.",
    "pl": "Cześć, jestem głosem Supertonic. To jest próbka audio.",
    "ru": "Привет, я голос Supertonic. Это образец аудио.",
    "uk": "Привіт, я голос Supertonic. Це зразок аудіо.",
    "tr": "Merhaba, ben bir Supertonic sesiyim. Bu bir ses örneğidir.",
    "ja": "こんにちは、Supertonicの音声です。オーディオサンプルです。",
    "ko": "안녕하세요, Supertonic 음성입니다. 오디오 샘플입니다.",
    "ar": "مرحباً، أنا صوت سوبرتونيك. هذه عينة صوتية.",
    "hi": "नमस्ते, मैं Supertonic आवाज़ हूँ। यह एक ऑडियो नमूना है।",
    "vi": "Xin chào, tôi là giọng nói Supertonic. Đây là mẫu âm thanh.",
}
"""Texto de muestra por idioma de voz (los idiomas sin entrada usan el texto
traducido del idioma de la interfaz)."""

IDIOMAS_VOZ_NATIVOS: dict = {
    "en": "English", "es": "Español", "fr": "Français", "de": "Deutsch",
    "it": "Italiano", "pt": "Português", "nl": "Nederlands", "pl": "Polski",
    "ru": "Русский", "uk": "Українська", "tr": "Türkçe", "ar": "العربية",
    "hi": "हिन्दी", "ko": "한국어", "ja": "日本語", "bg": "Български",
    "cs": "Čeština", "da": "Dansk", "el": "Ελληνικά", "et": "Eesti",
    "fi": "Suomi", "hr": "Hrvatski", "hu": "Magyar", "id": "Bahasa Indonesia",
    "lt": "Lietuvių", "lv": "Latviešu", "ro": "Română", "sk": "Slovenčina",
    "sl": "Slovenščina", "sv": "Svenska", "vi": "Tiếng Việt",
}
"""Nombre nativo de cada idioma de voz (``na`` se traduce con la clave de UI)."""

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

NEUMO_CLARA: dict = {
    "fondo": "#E8E4F0",
    "superficie": "#E8E4F0",
    "superficie_variante": "#DDD8EA",
    "borde": "#CFC9DE",
    "luz": "#FDFBFF",
    "sombra": "#C2BAD6",
    "primario_luz": "#FFFFFF",
    "primario_sombra": "#574E8C",
}
"""Overrides neumórficos para el tema claro (se combinan con ``PALETA_CLARA``).

En neumorfismo la superficie coincide con el fondo: los elementos se
distinguen solo por las sombras suaves (``luz`` arriba-izquierda, ``sombra``
abajo-derecha). ``primario_luz``/``primario_sombra`` matizan el bisel del
botón de acción.
"""

NEUMO_OSCURA: dict = {
    "fondo": "#1C1A23",
    "superficie": "#1C1A23",
    "superficie_variante": "#232029",
    "borde": "#2C2836",
    "luz": "#302C3C",
    "sombra": "#0E0C12",
    "primario_luz": "#E7D4FF",
    "primario_sombra": "#8E77C8",
}
"""Overrides neumórficos para el tema oscuro (se combinan con ``PALETA_OSCURA``)."""

IDIOMAS: dict = {"es": "Español", "en": "English"}
"""Idiomas disponibles para la interfaz (código -> nombre mostrado)."""

TRADUCCIONES: dict = {
    "es": {
        "ventana_titulo": "Supertonic-AudioBook — Conversor de archivos a audio",
        "ajustes": "Ajustes",
        "tema": "Tema",
        "idioma": "Idioma",
        "claro": "Claro",
        "oscuro": "Oscuro",
        "estilo": "Estilo",
        "estilo_material": "Material (actual)",
        "estilo_neumorfismo": "Neumorfismo",
        "cerrar": "Cerrar",
        "tab_entrada": "Entrada y salida",
        "tab_sintesis": "Síntesis y registro",
        "salida_audio": "Salida de audio",
        "carpeta_origen": "Carpeta de origen",
        "etiqueta_carpeta": "Carpeta:",
        "examinar": "Examinar…",
        "archivos_encontrados": "Archivos Encontrados",
        "todo": "Todo",
        "nada": "Nada",
        "refrescar": "Refrescar",
        "ayuda_seleccion": "Marcá los que querés\nsin marcas = todos",
        "opciones_sintesis": "Opciones de síntesis",
        "formato": "Formato",
        "voz": "Voz",
        "modelo_supertonic": "Modelo supertonic-3",
        "pasos": "Pasos",
        "calidad_lento": "más calidad = más lento",
        "velocidad": "Velocidad",
        "rapido_lento": "más rápido / más lento",
        "idioma_voz": "Idioma de la voz",
        "idioma_voz_auto": "Auto (sin idioma)",
        "escuchar": "Escuchar",
        "muestra_texto": "Esta es una muestra de la voz sintética.",
        "log_muestra": "    Generando muestra de voz {voz} ({lang})...",
        "log_muestra_fin": "    Muestra lista. Reproduciendo...",
        "log_muestra_error": "    No se pudo generar o reproducir la muestra.",
        "registro": "Registro",
        "btn_procesar": "▶  Procesar",
        "btn_cancelar": "■  Cancelar",
        "estado_listo": "Listo.",
        "estado_archivo": "Archivo {i} de {n}: {nombre}",
        "estado_segmentos": "{actual}/{total} segmentos sintetizados",
        "estado_listo_n": "Listo: {n} archivo(s) en {tiempo}.",
        "estado_cancelando": "Cancelando (exporta lo generado hasta ahora)…",
        "estado_cancelado": "Cancelado por el usuario.",
        "estado_error": "Error.",
        "estado_con_errores": "Completado con errores: {exitos}/{total} OK, {errores} error/es.",
        "snackbar_formato": "Elegí al menos un formato de salida.",
        "snackbar_sin_md": "No hay archivos .md en la carpeta de entrada.",
        "snackbar_procesado": "Se procesaron {n} archivo(s) en {tiempo}.",
        "snackbar_exportado": "Se exportó lo generado hasta el momento.",
        "snackbar_con_errores": "{exitos} procesado(s), {errores} error(es) en {tiempo}.",
        "conteo_seleccionados": "{sel}/{total} seleccionados",
        "conteo_archivos": "{total} archivos",
        "conteo_sin": "Sin archivos",
        "log_inicio": "▶ Inicio: {sel} archivo(s) seleccionado(s) de {total} disponible(s).",
        "log_formato_no_ok": "No se pudo iniciar: no se eligió ningún formato de salida.",
        "log_sin_md": "No se pudo iniciar: la carpeta de entrada no tiene archivos .md.",
        "log_cancelar": "■ Cancelación solicitada: se exporta lo generado hasta el momento.",
        "log_config_titulo": "  CONFIGURACIÓN",
        "log_config_voz": "    Voz: {voz}   Pasos: {pasos}   Velocidad: {vel}",
        "log_config_lang": "    Idioma de la voz: {lang}",
        "log_config_formatos": "    Formatos: {formatos}",
        "log_config_salida": "    Salida: {salida}",
        "log_archivo": "▶ Archivo {i}/{n}: {nombre}",
        "log_segmento": "      Segmento {actual}/{total} sintetizado…",
        "log_archivo_fin": "✔ Archivo {i}/{n} terminado.",
        "log_completado": "✔ PROCESAMIENTO COMPLETADO: {n} archivo(s) en {tiempo}.",
        "log_con_errores": "Finalizado con {errores} error(es) de {total} archivo(s).",
        "log_cancelado": "✖ Procesamiento cancelado por el usuario tras {tiempo}.",
        "log_error": "✖ ERROR: {texto}",
        "tiempo_seg": "{total} s",
        "tiempo_min_seg": "{min} min {seg} s",
        "tiempo_hora_min": "{horas} h {min} min",
    },
    "en": {
        "ventana_titulo": "Supertonic-AudioBook — File to audio converter",
        "ajustes": "Settings",
        "tema": "Theme",
        "idioma": "Language",
        "claro": "Light",
        "oscuro": "Dark",
        "estilo": "Style",
        "estilo_material": "Material (current)",
        "estilo_neumorfismo": "Neumorphism",
        "cerrar": "Close",
        "tab_entrada": "Input & output",
        "tab_sintesis": "Synthesis & log",
        "salida_audio": "Audio output",
        "carpeta_origen": "Source folder",
        "etiqueta_carpeta": "Folder:",
        "examinar": "Browse…",
        "archivos_encontrados": "Files Found",
        "todo": "All",
        "nada": "None",
        "refrescar": "Refresh",
        "ayuda_seleccion": "Check the ones you want\nnone checked = all",
        "opciones_sintesis": "Synthesis options",
        "formato": "Format",
        "voz": "Voice",
        "modelo_supertonic": "supertonic-3 model",
        "pasos": "Steps",
        "calidad_lento": "more quality = slower",
        "velocidad": "Speed",
        "rapido_lento": "faster / slower",
        "idioma_voz": "Voice language",
        "idioma_voz_auto": "Auto (no language)",
        "escuchar": "Listen",
        "muestra_texto": "This is a sample of the synthetic voice.",
        "log_muestra": "    Generating sample of voice {voz} ({lang})...",
        "log_muestra_fin": "    Sample ready. Playing...",
        "log_muestra_error": "    Could not generate or play the sample.",
        "registro": "Log",
        "btn_procesar": "▶  Process",
        "btn_cancelar": "■  Cancel",
        "estado_listo": "Ready.",
        "estado_archivo": "File {i} of {n}: {nombre}",
        "estado_segmentos": "{actual}/{total} segments synthesized",
        "estado_listo_n": "Done: {n} file(s) in {tiempo}.",
        "estado_cancelando": "Cancelling (exports what was generated so far)…",
        "estado_cancelado": "Cancelled by the user.",
        "estado_error": "Error.",
        "estado_con_errores": "Finished with errors: {exitos}/{total} OK, {errores} error(s).",
        "snackbar_formato": "Choose at least one output format.",
        "snackbar_sin_md": "There are no .md files in the input folder.",
        "snackbar_procesado": "{n} file(s) processed in {tiempo}.",
        "snackbar_exportado": "Exported what was generated so far.",
        "snackbar_con_errores": "{exitos} processed, {errores} error(s) in {tiempo}.",
        "conteo_seleccionados": "{sel}/{total} selected",
        "conteo_archivos": "{total} files",
        "conteo_sin": "No files",
        "log_inicio": "▶ Start: {sel} file(s) selected of {total} available.",
        "log_formato_no_ok": "Could not start: no output format was chosen.",
        "log_sin_md": "Could not start: the input folder has no .md files.",
        "log_cancelar": "■ Cancellation requested: what was generated so far will be exported.",
        "log_config_titulo": "  CONFIGURATION",
        "log_config_voz": "    Voice: {voz}   Steps: {pasos}   Speed: {vel}",
        "log_config_lang": "    Voice language: {lang}",
        "log_config_formatos": "    Formats: {formatos}",
        "log_config_salida": "    Output: {salida}",
        "log_archivo": "▶ File {i}/{n}: {nombre}",
        "log_segmento": "      Segment {actual}/{total} synthesized…",
        "log_archivo_fin": "✔ File {i}/{n} finished.",
        "log_completado": "✔ PROCESSING COMPLETED: {n} file(s) in {tiempo}.",
        "log_con_errores": "Finished with {errores} error(s) out of {total} file(s).",
        "log_cancelado": "✖ Processing cancelled by the user after {tiempo}.",
        "log_error": "✖ ERROR: {texto}",
        "tiempo_seg": "{total} s",
        "tiempo_min_seg": "{min} min {seg} s",
        "tiempo_hora_min": "{horas} h {min} min",
    },
}


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
        fabrica_use_case: Callable[[str], ProcesarArchivo],
        fabrica_muestra: Optional[Callable[[str], SintetizarMuestra]] = None,
        repositorio: RepositorioArchivos,
        carpeta_base: Path,
        repositorio_preferencias: RepositorioPreferencias,
    ) -> None:
        """Args:
            fabrica_use_case: Crea ``ProcesarArchivo`` para una voz dada.
            fabrica_muestra: Crea ``SintetizarMuestra`` para probar la voz
                (``None`` oculta el botón "Escuchar").
            repositorio: Acceso a los archivos en disco (inyectado).
            carpeta_base: Carpeta base de la app (modelo/, archivos/, audio/).
            repositorio_preferencias: Persistencia de preferencias de la UI.
        """
        super().__init__()
        self._fabrica_use_case = fabrica_use_case
        self._fabrica_muestra = fabrica_muestra
        self._repositorio = repositorio
        self._carpeta_base = carpeta_base
        self._repositorio_preferencias = repositorio_preferencias

        self._tema_oscuro = False
        self._estilo_neumo = False
        self._paleta = dict(PALETA_CLARA)
        self._preferencias_cargadas = self._repositorio_preferencias.cargar()

        prefs = self._preferencias_cargadas if isinstance(self._preferencias_cargadas, dict) else {}
        idioma = prefs.get("idioma", "es")
        self._idioma = idioma if idioma in IDIOMAS else "es"

        self.title(self.t("ventana_titulo"))
        self.geometry("660x720")
        self.minsize(580, 640)

        self._cola: "queue.Queue" = queue.Queue()
        self._cancelar = threading.Event()
        self._hilo: threading.Thread | None = None
        self._en_ejecucion = False
        self._probando_voz = False
        self._archivos: List[Path] = []
        self._vars_check: Dict[int, tk.BooleanVar] = {}
        self._checks: Dict[int, tk.Checkbutton] = {}
        self._seleccion: List[Path] = []
        self._ventana_ajustes: tk.Toplevel | None = None
        self._main: ttk.Frame | None = None
        self._snackbar: ttk.Label | None = None
        self._snackbar_id: str | None = None
        self._btn_escuchar: ttk.Button | None = None
        self._txt: scrolledtext.ScrolledText | None = None

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
        if self._main is not None:
            self._main.destroy()
        if self._snackbar is not None:
            self._snackbar.destroy()
            self._snackbar = None
        self._snackbar_id = None
        self._modo_ancho = False
        self._vars_check = {}
        self._checks = {}

        main = ttk.Frame(self, padding=12)
        self._main = main
        main.pack(fill="both", expand=True)

        # --- Cabecera con título y botón de ajustes ---
        cabecera = ttk.Frame(main)
        cabecera.pack(fill="x", pady=(0, 10))
        ttk.Label(
            cabecera,
            text="Supertonic-AudioBook",
            style="Titulo.TLabel",
        ).pack(side="left")
        self._btn_ajustes = ttk.Button(cabecera, text="⚙", width=3, command=self._abrir_ajustes)
        self._btn_ajustes.pack(side="right")

        # --- Zona de contenido: pestañas (angosto) o columnas lado a lado (ancho) ---
        self._contenido = ttk.Frame(main)
        self._contenido.pack(fill="both", expand=True)
        self._notebook = ttk.Notebook(self._contenido)
        self._modo_ancho = False

        self._panel_entrada = ttk.Frame(self._contenido, padding=4)
        self._panel_sintesis = ttk.Frame(self._contenido, padding=4)

        self._construir_panel_entrada()
        self._construir_panel_sintesis()

        self._notebook.add(self._panel_entrada, text=self.t("tab_entrada"))
        self._notebook.add(self._panel_sintesis, text=self.t("tab_sintesis"))
        self._notebook.pack(fill="both", expand=True)

        # --- Acciones ---
        f_accion = ttk.Frame(main)
        f_accion.pack(fill="x", pady=(12, 0))
        self._btn_procesar = ttk.Button(
            f_accion, text=self.t("btn_procesar"), style="Principal.TButton", command=self._procesar
        )
        self._btn_procesar.pack(side="left")
        self._btn_cancelar = ttk.Button(
            f_accion,
            text=self.t("btn_cancelar"),
            command=self._cancelar_accion,
            state="disabled",
        )
        self._btn_cancelar.pack(side="left", padx=6)

        # --- Progreso ---
        self._barra = ttk.Progressbar(main, maximum=100)
        self._barra.pack(fill="x", pady=(12, 4))
        fila_progreso = ttk.Frame(main)
        fila_progreso.pack(fill="x")
        self._lbl_estado = ttk.Label(fila_progreso, text=self.t("estado_listo"), anchor="w")
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
        # Rueda del mouse: binding en el toplevel, no en bind_all, para no
        # pisar bindings "all" ajenos ni acumular handlers en cada rebuild.
        self.bind("<MouseWheel>", self._scroll_lienzo)

    def _construir_panel_entrada(self) -> None:
        panel = self._panel_entrada

        # --- Carpeta de salida ---
        f_salida = ttk.LabelFrame(panel, text=self.t("salida_audio"), style="Tarjeta.TLabelframe", padding=8)
        f_salida.pack(fill="x")
        fila = ttk.Frame(f_salida, style="Tarjeta.TFrame")
        fila.pack(fill="x")
        ttk.Label(fila, text=self.t("etiqueta_carpeta"), style="CardLabel.TLabel").pack(side="left")
        self._var_carpeta_out = tk.StringVar(value=str(self._carpeta_base / "audio"))
        ttk.Entry(fila, textvariable=self._var_carpeta_out).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(fila, text=self.t("examinar"), command=self._elegir_carpeta_out).pack(side="left")

        # --- Carpeta de origen (selección separada de la lista) ---
        f_origen = ttk.LabelFrame(panel, text=self.t("carpeta_origen"), style="Tarjeta.TLabelframe", padding=8)
        f_origen.pack(fill="x", pady=(10, 0))
        fila = ttk.Frame(f_origen, style="Tarjeta.TFrame")
        fila.pack(fill="x")
        ttk.Label(fila, text=self.t("etiqueta_carpeta"), style="CardLabel.TLabel").pack(side="left")
        self._var_carpeta_in = tk.StringVar(value=str(self._carpeta_base / "archivos"))
        ttk.Entry(fila, textvariable=self._var_carpeta_in).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(fila, text=self.t("examinar"), command=self._elegir_carpeta_in).pack(side="left")

        # --- Archivos encontrados (lista) ---
        f_lista = ttk.LabelFrame(panel, text=self.t("archivos_encontrados"), style="Tarjeta.TLabelframe", padding=8)
        f_lista.pack(fill="both", expand=True, pady=(10, 0))

        fila_lista = ttk.Frame(f_lista, style="Tarjeta.TFrame")
        fila_lista.pack(fill="both", expand=True)

        lista_frame = ttk.Frame(fila_lista, style="Tarjeta.TFrame")
        lista_frame.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(lista_frame, orient="vertical")
        self._scrollbar_lista = scroll
        self._lienzo = tk.Canvas(
            lista_frame,
            highlightthickness=0,
            yscrollcommand=scroll.set,
        )
        self._contenedor_check = tk.Frame(self._lienzo)
        self._ventana_lienzo = self._lienzo.create_window(
            (0, 0), window=self._contenedor_check, anchor="nw"
        )
        scroll.config(command=self._lienzo.yview)
        scroll.pack(side="right", fill="y")
        self._lienzo.pack(side="left", fill="both", expand=True)
        self._contenedor_check.bind(
            "<Configure>", lambda e: self._lienzo.configure(scrollregion=self._lienzo.bbox("all"))
        )
        self._lienzo.bind(
            "<Configure>", lambda e: self._lienzo.itemconfig(self._ventana_lienzo, width=e.width)
        )

        panel_botones = ttk.Frame(fila_lista, style="Tarjeta.TFrame")
        panel_botones.pack(side="left", fill="y", padx=(8, 0))
        ttk.Button(panel_botones, text=self.t("todo"), width=9, command=self._seleccionar_todo).pack(fill="x")
        ttk.Button(panel_botones, text=self.t("nada"), width=9, command=self._limpiar_seleccion).pack(fill="x", pady=(6, 0))
        ttk.Button(panel_botones, text=self.t("refrescar"), width=9, command=self._refrescar_archivos).pack(fill="x", pady=(6, 0))
        ttk.Label(panel_botones, text="", style="CardHint.TLabel").pack(fill="x", expand=True)
        self._lbl_conteo = ttk.Label(panel_botones, text="", style="CardHint.TLabel", anchor="center")
        self._lbl_conteo.pack(fill="x", pady=(6, 0))
        ttk.Label(
            panel_botones,
            text=self.t("ayuda_seleccion"),
            style="CardHint.TLabel",
            justify="center",
            anchor="n",
        ).pack(fill="x", pady=(2, 0))

    def _construir_panel_sintesis(self) -> None:
        panel = self._panel_sintesis

        # --- Opciones de síntesis ---
        f_opciones = ttk.LabelFrame(
            panel, text=self.t("opciones_sintesis"), style="Tarjeta.TLabelframe", padding=12
        )
        f_opciones.pack(fill="x")
        f_opciones.columnconfigure(1, weight=1)

        # Formato (chips)
        ttk.Label(f_opciones, text=self.t("formato"), style="Etiqueta.TLabel").grid(
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
        ttk.Label(f_opciones, text=self.t("voz"), style="Etiqueta.TLabel").grid(
            row=1, column=0, sticky="nw", pady=(14, 0)
        )
        fila_voz = ttk.Frame(f_opciones, style="Tarjeta.TFrame")
        fila_voz.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(10, 0))
        self._var_voz = tk.StringVar(value=DEFAULT_VOICE)
        ttk.Combobox(
            fila_voz, textvariable=self._var_voz, values=VOCES, width=6, state="readonly"
        ).pack(side="left")
        ttk.Label(
            fila_voz, text=self.t("modelo_supertonic"), style="CardHint.TLabel"
        ).pack(side="left", padx=(10, 0))
        if self._fabrica_muestra is not None:
            self._btn_escuchar = ttk.Button(
                fila_voz, text=self.t("escuchar"), command=self._escuchar_muestra
            )
            self._btn_escuchar.pack(side="left", padx=(12, 0))

        # Pasos
        ttk.Label(f_opciones, text=self.t("pasos"), style="Etiqueta.TLabel").grid(
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
            fila_pasos, text=self.t("calidad_lento"), style="CardHint.TLabel"
        ).grid(row=0, column=2, padx=(12, 0))

        # Velocidad
        ttk.Label(f_opciones, text=self.t("velocidad"), style="Etiqueta.TLabel").grid(
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
            fila_speed, text=self.t("rapido_lento"), style="CardHint.TLabel"
        ).grid(row=0, column=2, padx=(12, 0))

        # Idioma de la voz
        ttk.Label(f_opciones, text=self.t("idioma_voz"), style="Etiqueta.TLabel").grid(
            row=4, column=0, sticky="nw", pady=(14, 0)
        )
        fila_lang = ttk.Frame(f_opciones, style="Tarjeta.TFrame")
        fila_lang.grid(row=4, column=1, sticky="w", padx=(12, 0), pady=(10, 0))
        self._var_lang_voz = tk.StringVar(value=self._nombre_idioma_voz(DEFAULT_LANG))
        ttk.Combobox(
            fila_lang,
            textvariable=self._var_lang_voz,
            values=self._nombres_idiomas_voz(),
            state="readonly",
            width=16,
        ).pack(side="left")

        # --- Registro ---
        f_log = ttk.LabelFrame(panel, text=self.t("registro"), style="Tarjeta.TLabelframe", padding=4)
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
        self._notebook.add(self._panel_entrada, text=self.t("tab_entrada"))
        self._notebook.add(self._panel_sintesis, text=self.t("tab_sintesis"))
        self._notebook.pack(fill="both", expand=True)

    # ------------------------------------------------------------- temas

    def t(self, clave: str) -> str:
        """Devuelve el texto traducido para la clave dada en el idioma activo."""
        return TRADUCCIONES.get(self._idioma, TRADUCCIONES["es"]).get(clave, clave)

    def _nombre_idioma_voz(self, codigo: str) -> str:
        """Nombre visible del idioma de voz (nativo; ``na`` usa la clave de UI)."""
        if codigo == "na":
            return self.t("idioma_voz_auto")
        return IDIOMAS_VOZ_NATIVOS.get(codigo, codigo)

    def _nombres_idiomas_voz(self) -> List[str]:
        return [self._nombre_idioma_voz(codigo) for codigo in LANGUAGES_VOZ]

    def _codigo_idioma_voz(self) -> str:
        """Código del idioma seleccionado (inverso de ``_nombre_idioma_voz``).

        Tolerante al idioma de la UI: el combo puede mostrar el nombre de
        ``na`` en el idioma anterior durante una reconstrucción, así que
        acepta cualquiera de las traducciones conocidas.
        """
        nombre = self._var_lang_voz.get()
        etiquetas_na = {
            TRADUCCIONES.get(idioma, TRADUCCIONES["es"])["idioma_voz_auto"]
            for idioma in IDIOMAS
        }
        for codigo in LANGUAGES_VOZ:
            if codigo == "na":
                if nombre in etiquetas_na:
                    return codigo
            elif nombre == codigo or IDIOMAS_VOZ_NATIVOS.get(codigo) == nombre:
                return codigo
        return DEFAULT_LANG

    def _abrir_ajustes(self) -> None:
        """Abre (o trae al frente) la ventana flotante de configuración."""
        if self._ventana_ajustes is not None and self._ventana_ajustes.winfo_exists():
            self._ventana_ajustes.deiconify()
            self._ventana_ajustes.lift()
            return

        ventana = tk.Toplevel(self)
        ventana.title(self.t("ajustes"))
        ventana.transient(self)
        ventana.resizable(False, False)
        self._ventana_ajustes = ventana
        ventana.protocol("WM_DELETE_WINDOW", self._cerrar_ajustes)

        marco = ttk.Frame(ventana, padding=16)
        marco.pack(fill="both", expand=True)

        ttk.Label(marco, text=self.t("ajustes"), style="Titulo.TLabel").pack(anchor="w", pady=(0, 12))

        # --- Tema ---
        f_tema = ttk.LabelFrame(marco, text=self.t("tema"), style="Tarjeta.TLabelframe", padding=10)
        f_tema.pack(fill="x")
        var_tema = tk.StringVar(value="oscuro" if self._tema_oscuro else "claro")
        self._var_tema_ajustes = var_tema
        for valor, etiqueta in (("claro", self.t("claro")), ("oscuro", self.t("oscuro"))):
            ttk.Radiobutton(
                f_tema,
                text=etiqueta,
                variable=var_tema,
                value=valor,
                command=self._aplicar_tema_desde_ajustes,
            ).pack(anchor="w", pady=2)

        # --- Estilo ---
        f_estilo = ttk.LabelFrame(marco, text=self.t("estilo"), style="Tarjeta.TLabelframe", padding=10)
        f_estilo.pack(fill="x", pady=(10, 0))
        var_estilo = tk.StringVar(value="neumo" if self._estilo_neumo else "material")
        self._var_estilo_ajustes = var_estilo
        for valor, etiqueta in (
            ("material", self.t("estilo_material")),
            ("neumo", self.t("estilo_neumorfismo")),
        ):
            ttk.Radiobutton(
                f_estilo,
                text=etiqueta,
                variable=var_estilo,
                value=valor,
                command=self._aplicar_estilo_desde_ajustes,
            ).pack(anchor="w", pady=2)

        # --- Idioma ---
        f_idioma = ttk.LabelFrame(marco, text=self.t("idioma"), style="Tarjeta.TLabelframe", padding=10)
        f_idioma.pack(fill="x", pady=(10, 0))
        var_idioma = tk.StringVar(value=IDIOMAS[self._idioma])
        self._var_idioma_ajustes = var_idioma
        ttk.Combobox(
            f_idioma,
            textvariable=var_idioma,
            values=list(IDIOMAS.values()),
            state="readonly",
            width=12,
        ).pack(anchor="w")
        var_idioma.trace_add("write", self._aplicar_idioma_desde_ajustes)

        f_acciones = ttk.Frame(marco)
        f_acciones.pack(fill="x", pady=(14, 0))
        ttk.Button(f_acciones, text=self.t("cerrar"), command=self._cerrar_ajustes).pack(side="right")

        # Centrar la ventana sobre la principal y teñirla con el tema actual
        ventana.configure(bg=self._paleta["fondo"])
        ventana.update_idletasks()
        ancho = max(ventana.winfo_reqwidth(), 320)
        alto = ventana.winfo_reqheight()
        x = self.winfo_rootx() + (self.winfo_width() - ancho) // 2
        y = self.winfo_rooty() + max(0, (self.winfo_height() - alto) // 3)
        ventana.geometry(f"{ancho}x{alto}+{max(x, 0)}+{y}")

    def _aplicar_tema_desde_ajustes(self) -> None:
        self._aplicar_tema(self._var_tema_ajustes.get() == "oscuro")
        self._guardar_preferencias()

    def _aplicar_estilo_desde_ajustes(self) -> None:
        self._aplicar_tema(
            self._tema_oscuro,
            neumo=self._var_estilo_ajustes.get() == "neumo",
        )
        self._guardar_preferencias()

    def _aplicar_idioma_desde_ajustes(self, *_args) -> None:
        nombre = self._var_idioma_ajustes.get()
        idioma = next((c for c, n in IDIOMAS.items() if n == nombre), self._idioma)
        if idioma == self._idioma:
            return
        self._idioma = idioma
        self._guardar_preferencias()
        self._reconstruir_ui()

    def _cerrar_ajustes(self) -> None:
        if self._ventana_ajustes is not None:
            self._ventana_ajustes.destroy()
            self._ventana_ajustes = None

    def _reconstruir_ui(self) -> None:
        """Reconstruye la interfaz (al cambiar idioma), preservando valores y log."""
        prefs = self._preferencias_actuales()
        log_texto = ""
        if self._txt is not None and self._txt.winfo_exists():
            self._txt.config(state="normal")
            log_texto = self._txt.get("1.0", "end-1c")
            self._txt.config(state="disabled")
        self._construir_widgets()
        self._aplicar_preferencias(prefs)
        self._aplicar_tema(self._tema_oscuro)
        if log_texto:
            self._txt.config(state="normal")
            self._txt.insert("end", log_texto)
            self._txt.config(state="disabled")
            self._txt.see("end")
        self._refrescar_archivos()
        self.title(self.t("ventana_titulo"))
        if self.winfo_width() >= UMBRAL_ANCHO and not self._modo_ancho:
            self._modo_columnas()
        if self._ventana_ajustes is not None and self._ventana_ajustes.winfo_exists():
            self._cerrar_ajustes()
            self._abrir_ajustes()
        self._set_ejecutando(self._en_ejecucion)

    def _aplicar_tema(self, oscuro: bool, neumo: Optional[bool] = None) -> None:
        self._tema_oscuro = oscuro
        if neumo is not None:
            self._estilo_neumo = neumo
        c = dict(PALETA_OSCURA if oscuro else PALETA_CLARA)
        if self._estilo_neumo:
            c.update(NEUMO_OSCURA if oscuro else NEUMO_CLARA)
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

        # Botón estándar (contorno): Examinar…, Todo/Nada/Refrescar, ajustes, cancelar
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
        # Radiobutton (temas en la ventana de ajustes)
        estilo.configure(
            "TRadiobutton",
            background=c["superficie"],
            foreground=c["texto"],
            focuscolor=c["fondo"],
        )
        estilo.map(
            "TRadiobutton",
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

        if self._estilo_neumo:
            self._configurar_estilo_neumo(estilo, c)

        self.configure(bg=c["fondo"])
        self._estilizar_no_ttk()
        if self._ventana_ajustes is not None and self._ventana_ajustes.winfo_exists():
            self._ventana_ajustes.configure(bg=c["fondo"])

    def _configurar_estilo_neumo(self, estilo: ttk.Style, c: dict) -> None:
        """Ajusta los estilos base al look neumórfico (biseles luz/sombra suaves).

        Tkinter no tiene sombras nativas; el neumorfismo se simula con el
        relieve de clam: ``raised`` usa ``lightcolor`` arriba-izquierda y
        ``darkcolor`` abajo-derecha (elemento saliente), ``sunken`` lo invierte
        (elemento hundido). La superficie coincide con el fondo.
        """
        superficie = c["fondo"]

        # Tarjetas: elevadas, sin borde duro
        estilo.configure(
            "Tarjeta.TLabelframe",
            background=superficie,
            bordercolor=c["borde"],
            relief="raised",
            borderwidth=1,
            lightcolor=c["luz"],
            darkcolor=c["sombra"],
        )
        estilo.configure("Tarjeta.TLabelframe.Label", background=superficie)

        # Botón estándar: elevado; al presionar se hunde
        estilo.configure(
            "TButton",
            background=superficie,
            foreground=c["primario"],
            bordercolor=c["borde"],
            borderwidth=1,
            relief="raised",
            lightcolor=c["luz"],
            darkcolor=c["sombra"],
            padding=(14, 8),
            font=("Segoe UI", 10),
            focusthickness=0,
        )
        estilo.map(
            "TButton",
            relief=[("pressed", "sunken"), ("active", "raised")],
            background=[("active", superficie)],
        )

        # Botón de acción: relleno primario con bisel en tonos del primario
        estilo.configure(
            "Principal.TButton",
            background=c["primario"],
            foreground=c["sobre_primario"],
            borderwidth=1,
            relief="raised",
            lightcolor=c["primario_luz"],
            darkcolor=c["primario_sombra"],
            padding=(18, 9),
            font=("Segoe UI", 10, "bold"),
            focusthickness=0,
        )
        estilo.map(
            "Principal.TButton",
            relief=[("pressed", "sunken")],
            background=[
                ("active", c["primario_vivo"]),
                ("disabled", c["superficie_variante"]),
            ],
            foreground=[("disabled", c["texto_secundario"])],
        )

        # Entradas y combos: hundidos (inset)
        estilo.configure(
            "TEntry",
            fieldbackground=superficie,
            foreground=c["texto"],
            insertcolor=c["texto"],
            bordercolor=c["borde"],
            lightcolor=c["luz"],
            darkcolor=c["sombra"],
            borderwidth=1,
            padding=(8, 6),
        )
        estilo.map("TEntry", bordercolor=[("focus", c["primario"])])
        estilo.configure(
            "TCombobox",
            fieldbackground=superficie,
            foreground=c["texto"],
            arrowcolor=c["primario"],
            bordercolor=c["borde"],
            lightcolor=c["luz"],
            darkcolor=c["sombra"],
            borderwidth=1,
        )
        estilo.map(
            "TCombobox",
            fieldbackground=[("readonly", superficie)],
            foreground=[("readonly", c["texto"])],
        )

        # Checkbuttons y radiobuttons sobre superficie uniforme
        estilo.configure(
            "TCheckbutton",
            background=superficie,
            foreground=c["texto"],
            focuscolor=superficie,
            bordercolor=c["borde"],
        )
        estilo.map(
            "TCheckbutton",
            background=[("active", superficie)],
            indicatorcolor=[("selected", c["primario"]), ("!selected", superficie)],
        )
        estilo.configure(
            "TRadiobutton",
            background=superficie,
            foreground=c["texto"],
            focuscolor=superficie,
        )
        estilo.map(
            "TRadiobutton",
            background=[("active", superficie)],
            indicatorcolor=[("selected", c["primario"]), ("!selected", superficie)],
        )

        # Chip de formato: elevado; seleccionado = hundido con acento primario
        estilo.configure(
            "Chip.TCheckbutton",
            background=superficie,
            foreground=c["texto"],
            indicatorcolor=superficie,
            bordercolor=c["borde"],
            borderwidth=1,
            relief="raised",
            lightcolor=c["luz"],
            darkcolor=c["sombra"],
            padding=(12, 6),
            focuscolor=superficie,
        )
        estilo.map(
            "Chip.TCheckbutton",
            relief=[("selected", "sunken")],
            background=[("selected", superficie), ("active", superficie)],
            foreground=[("selected", c["primario"]), ("active", c["texto"])],
            indicatorcolor=[("selected", c["primario"]), ("!selected", superficie)],
        )

        # Slider, barra de progreso y scrollbar: canal hundido
        estilo.configure(
            "Horizontal.TScale",
            background=superficie,
            troughcolor=c["superficie_variante"],
            borderwidth=1,
            relief="sunken",
            lightcolor=c["luz"],
            darkcolor=c["sombra"],
        )
        estilo.map("Horizontal.TScale", background=[("active", superficie)])
        estilo.configure(
            "Horizontal.TProgressbar",
            background=c["primario"],
            troughcolor=c["superficie_variante"],
            borderwidth=1,
            relief="sunken",
            lightcolor=c["luz"],
            darkcolor=c["sombra"],
        )
        estilo.configure(
            "Vertical.TScrollbar",
            background=c["superficie_variante"],
            troughcolor=superficie,
            borderwidth=0,
            arrowcolor=c["texto_secundario"],
        )
        estilo.map("Vertical.TScrollbar", background=[("active", c["primario"])])

    def _estilizar_no_ttk(self) -> None:
        c = self._paleta
        if self._estilo_neumo:
            superficie = c["fondo"]
            self._lienzo.configure(bg=superficie, relief="sunken", bd=1, highlightthickness=0)
            self._contenedor_check.configure(bg=superficie)
            for check in self._checks.values():
                check.configure(
                    bg=superficie,
                    fg=c["texto"],
                    activebackground=superficie,
                    activeforeground=c["texto"],
                    selectcolor=superficie,
                    bd=0,
                    highlightthickness=0,
                )
            self._txt.configure(
                bg=superficie,
                fg=c["texto"],
                insertbackground=c["texto"],
                selectbackground=c["primario"],
                selectforeground=c["sobre_primario"],
                relief="sunken",
                bd=1,
                highlightthickness=0,
            )
            self._txt.tag_configure("info", foreground=c["texto"])
            self._txt.tag_configure("warning", foreground=c["advertencia"])
            self._txt.tag_configure("error", foreground=c["error"])
            self._txt.tag_configure("debug", foreground=c["texto_secundario"])
            return

        self._lienzo.configure(bg=c["superficie"])
        self._contenedor_check.configure(bg=c["superficie"])
        for check in self._checks.values():
            check.configure(
                bg=c["superficie"],
                fg=c["texto"],
                activebackground=c["superficie"],
                activeforeground=c["texto"],
                selectcolor=c["fondo"],
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
        for hijo in self._contenedor_check.winfo_children():
            hijo.destroy()
        self._vars_check = {}
        self._checks = {}
        c = self._paleta
        for i, archivo in enumerate(self._archivos):
            var = tk.BooleanVar(value=False)
            check = tk.Checkbutton(
                self._contenedor_check,
                text=archivo.name,
                variable=var,
                anchor="w",
                justify="left",
                bg=c["superficie"],
                fg=c["texto"],
                activebackground=c["superficie"],
                activeforeground=c["texto"],
                selectcolor=c["fondo"],
                highlightthickness=0,
                bd=0,
                padx=4,
                pady=2,
                command=self._actualizar_conteo,
            )
            check.pack(fill="x")
            self._vars_check[i] = var
            self._checks[i] = check
        self._actualizar_conteo()

    def _scroll_lienzo(self, event) -> None:
        """Scrollea la lista solo si la rueda ocurre sobre ella o sus hijos.

        El binding está en el toplevel (``self.bind``): el evento se entrega
        al widget bajo el puntero (p. ej. un ``tk.Checkbutton``, que no tiene
        binding propio) y su cadena de bindtags incluye este toplevel. Si el
        puntero está fuera de la lista (p. ej. sobre el Registro), no se hace
        nada y el widget de abajo conserva su scroll nativo.
        """
        if not hasattr(self, "_lienzo"):
            return
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except tk.TclError:
            return
        while widget is not None and widget is not self:
            if widget is self._lienzo or widget is self._scrollbar_lista:
                # Windows entrega deltas de ±120 (rueda) o fracciones en
                # touchpads de precisión: se usa solo la dirección para que los
                # pasos cortos no se trunquen a 0 (sin scroll).
                self._lienzo.yview_scroll(-1 if event.delta > 0 else 1, "units")
                return "break"
            widget = getattr(widget, "master", None)
        return None

    def _seleccionar_todo(self) -> None:
        for var in self._vars_check.values():
            var.set(True)
        self._actualizar_conteo()

    def _limpiar_seleccion(self) -> None:
        for var in self._vars_check.values():
            var.set(False)
        self._actualizar_conteo()

    # ------------------------------------------------------- preferencias

    def _actualizar_conteo(self, *_args) -> None:
        total = len(self._archivos)
        seleccionados = sum(1 for var in self._vars_check.values() if var.get())
        if seleccionados:
            self._lbl_conteo.config(
                text=self.t("conteo_seleccionados").format(sel=seleccionados, total=total)
            )
        elif total:
            self._lbl_conteo.config(text=self.t("conteo_archivos").format(total=total))
        else:
            self._lbl_conteo.config(text=self.t("conteo_sin"))

    def _preferencias_actuales(self) -> Dict[str, object]:
        return {
            "tema_oscuro": self._tema_oscuro,
            "estilo": "neumo" if self._estilo_neumo else "material",
            "idioma": self._idioma,
            "voz": self._var_voz.get(),
            "steps": int(round(self._var_steps.get())),
            "speed": float(self._var_speed.get()),
            "lang_voz": self._codigo_idioma_voz(),
            "formatos": [f for f in FORMATOS_NATIVOS if self._var_formato[f].get()],
            "carpeta_in": self._var_carpeta_in.get(),
            "carpeta_out": self._var_carpeta_out.get(),
        }

    def _guardar_preferencias(self) -> None:
        try:
            self._repositorio_preferencias.guardar(self._preferencias_actuales())
        except Exception:
            logging.getLogger("lector").exception("No se pudieron guardar las preferencias")

    def _aplicar_preferencias(self, prefs: Dict[str, object]) -> None:
        if not isinstance(prefs, dict):
            return
        if isinstance(prefs.get("estilo"), str):
            self._estilo_neumo = prefs["estilo"] == "neumo"
        if isinstance(prefs.get("voz"), str) and prefs["voz"] in VOCES:
            self._var_voz.set(prefs["voz"])
        if isinstance(prefs.get("steps"), int):
            self._var_steps.set(max(5, min(12, prefs["steps"])))
            self._lbl_valor_steps.set(str(int(round(self._var_steps.get()))))
        if isinstance(prefs.get("speed"), (int, float)):
            self._var_speed.set(max(0.7, min(2.0, float(prefs["speed"]))))
            self._lbl_valor_speed.set(f"{self._var_speed.get():.2f}x")
        if isinstance(prefs.get("lang_voz"), str) and prefs["lang_voz"] in LANGUAGES_VOZ:
            self._var_lang_voz.set(self._nombre_idioma_voz(prefs["lang_voz"]))
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
            self._mostrar_snackbar(self.t("snackbar_formato"), "error")
            log.warning(self.t("log_formato_no_ok"))
            return

        self._seleccion = [self._archivos[i] for i, var in self._vars_check.items() if var.get()]
        if not self._seleccion:
            self._seleccion = list(self._archivos)
        if not self._seleccion:
            self._mostrar_snackbar(self.t("snackbar_sin_md"), "error")
            log.warning(self.t("log_sin_md"))
            return

        self._txt.config(state="normal")
        self._txt.delete("1.0", "end")
        self._txt.config(state="disabled")

        log.info(
            self.t("log_inicio").format(sel=len(self._seleccion), total=len(self._archivos))
        )
        voz = self._var_voz.get()
        steps = int(round(self._var_steps.get()))
        speed = float(self._var_speed.get())
        lang = self._codigo_idioma_voz()
        salida = Path(self._var_carpeta_out.get())

        self._set_ejecutando(True)
        self._cancelar.clear()
        self._hilo = threading.Thread(
            target=self._trabajo,
            args=(formatos, voz, steps, speed, lang, salida),
            daemon=True,
        )
        self._hilo.start()

    def _cancelar_accion(self) -> None:
        if not self._en_ejecucion:
            return
        self._cancelar.set()
        self._btn_cancelar.config(state="disabled")
        self._lbl_estado.config(text=self.t("estado_cancelando"))
        log.info(self.t("log_cancelar"))

    # ------------------------------------------------------------- worker

    def _escuchar_muestra(self) -> None:
        """Sintetiza y reproduce una muestra de la voz e idioma seleccionados."""
        if self._probando_voz or self._fabrica_muestra is None:
            return
        self._probando_voz = True
        if self._btn_escuchar is not None:
            self._btn_escuchar.config(state="disabled")
        voz = self._var_voz.get()
        lang = self._codigo_idioma_voz()
        texto = TEXTO_MUESTRA_IDIOMAS.get(lang, self.t("muestra_texto"))
        threading.Thread(
            target=self._generar_y_reproducir, args=(voz, lang, texto), daemon=True
        ).start()

    def _generar_y_reproducir(self, voz: str, lang: str, texto: str) -> None:
        try:
            self._cola.put(("log", "info", self.t("log_muestra").format(voz=voz, lang=lang)))
            muestra = self._fabrica_muestra(voz)
            ruta = Path(tempfile.gettempdir()) / f"supertonic_muestra_{voz}_{lang}.wav"
            muestra.generar(texto, lang=lang, ruta=ruta)
            winsound.PlaySound(str(ruta), winsound.SND_FILENAME | winsound.SND_ASYNC)
            self._cola.put(("log", "info", self.t("log_muestra_fin")))
        except Exception:
            logging.getLogger("gui").exception("Error al reproducir la muestra")
            self._cola.put(("log", "error", self.t("log_muestra_error")))
        finally:
            self._cola.put(("btn_muestra",))

    def _trabajo(
        self,
        formatos: List[str],
        voz: str,
        steps: int,
        speed: float,
        lang: str,
        salida: Path,
    ) -> None:
        inicio = time.monotonic()
        try:
            self._repositorio.crear_carpetas_si_no_existen(str(salida))

            log.info("=" * 60)
            log.info(self.t("log_config_titulo"))
            log.info(
                self.t("log_config_voz").format(voz=voz, pasos=steps, vel=f"{speed:.2f}x")
            )
            log.info(self.t("log_config_lang").format(lang=lang))
            log.info(
                self.t("log_config_formatos").format(formatos=", ".join(f.upper() for f in formatos))
            )
            log.info(self.t("log_config_salida").format(salida=salida))
            log.info("=" * 60)

            use_case = self._fabrica_use_case(voz)
            total_archivos = len(self._seleccion)
            exitos = 0
            errores = 0
            for i, ruta in enumerate(self._seleccion, 1):
                if self._cancelar.is_set():
                    break
                self._cola.put(("archivo", i, total_archivos, ruta.name))
                log.info(self.t("log_archivo").format(i=i, n=total_archivos, nombre=ruta.name))
                try:
                    use_case.procesar(
                        Archivo(ruta),
                        salida / ruta.stem,
                        steps=steps,
                        speed=speed,
                        lang=lang,
                        formatos=formatos,
                        on_progreso=self._cb_progreso,
                        debe_detenerse=self._cb_detenerse,
                    )
                    log.info(self.t("log_archivo_fin").format(i=i, n=total_archivos))
                    exitos += 1
                except Exception as exc:
                    errores += 1
                    logging.getLogger("gui").exception("Error procesando el archivo '%s'", ruta.name)
                    self._cola.put(("log", "error", f"Error en {ruta.name}: {exc}"))
            elapsed = time.monotonic() - inicio
            self._cola.put(("fin", not self._cancelar.is_set(), exitos, errores, total_archivos, elapsed))
        except Exception as exc:
            logging.getLogger("gui").exception("Error en el hilo de trabajo")
            self._cola.put(("error", str(exc)))

    def _cb_progreso(self, actual: int, total: int) -> None:
        self._cola.put(("progreso", actual, total))
        paso = max(1, total // 20)
        if actual % paso == 0 or actual == total:
            self._cola.put(
                ("log", "info", self.t("log_segmento").format(actual=actual, total=total))
            )

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
        elif tipo == "btn_muestra":
            self._probando_voz = False
            if self._btn_escuchar is not None:
                self._btn_escuchar.config(state="normal")
        elif tipo == "archivo":
            _, i, n, nombre = msg
            self._lbl_estado.config(text=self.t("estado_archivo").format(i=i, n=n, nombre=nombre))
            self._barra.config(value=0)
            self._lbl_porcentaje.config(text="0%")
        elif tipo == "progreso":
            _, actual, total = msg
            pct = actual / total * 100 if total else 0
            self._barra.config(value=pct)
            self._lbl_porcentaje.config(text=f"{pct:.0f}%")
            self._lbl_estado.config(text=self.t("estado_segmentos").format(actual=actual, total=total))
        elif tipo == "fin":
            _, finalizado_ok, exitos, errores, total_archivos, elapsed = msg
            self._set_ejecutando(False)
            texto_elapsed = self._formatear_tiempo(elapsed)
            if finalizado_ok and errores == 0:
                self._barra.config(value=100)
                self._lbl_porcentaje.config(text="100%")
                self._lbl_estado.config(text=self.t("estado_listo_n").format(n=exitos, tiempo=texto_elapsed))
                self._mostrar_snackbar(self.t("snackbar_procesado").format(n=exitos, tiempo=texto_elapsed))
                log.info("=" * 60)
                log.info(self.t("log_completado").format(n=exitos, tiempo=texto_elapsed))
                log.info("=" * 60)
            elif finalizado_ok and errores > 0:
                self._lbl_estado.config(
                    text=self.t("estado_con_errores").format(exitos=exitos, total=total_archivos, errores=errores)
                )
                self._mostrar_snackbar(
                    self.t("snackbar_con_errores").format(exitos=exitos, errores=errores, tiempo=texto_elapsed),
                    "error",
                )
                log.warning(self.t("log_con_errores").format(errores=errores, total=total_archivos))
            else:
                self._lbl_estado.config(text=self.t("estado_cancelado"))
                self._mostrar_snackbar(self.t("snackbar_exportado"))
                log.warning(self.t("log_cancelado").format(tiempo=texto_elapsed))
        elif tipo == "error":
            _, texto = msg
            self._set_ejecutando(False)
            self._lbl_estado.config(text=self.t("estado_error"))
            self._mostrar_snackbar(texto, "error")
            log.error(self.t("log_error").format(texto=texto))

    def _formatear_tiempo(self, segundos: float) -> str:
        total = int(segundos)
        if total < 60:
            return self.t("tiempo_seg").format(total=total)
        minutos, seg = divmod(total, 60)
        if minutos < 60:
            return self.t("tiempo_min_seg").format(min=minutos, seg=seg)
        horas, min_ = divmod(minutos, 60)
        return self.t("tiempo_hora_min").format(horas=horas, min=min_)

    def _escribir_log(self, texto: str, nivel: str = "info") -> None:
        self._txt.config(state="normal")
        self._txt.insert("end", texto + "\n", nivel if nivel in ("info", "warning", "error", "debug") else "info")
        idx_final = self._txt.index("end-1c")
        num_lineas = int(idx_final.split(".")[0])
        if num_lineas > 3000:
            self._txt.delete("1.0", f"{num_lineas - 2500}.0")
        self._txt.see("end")
        self._txt.config(state="disabled")

    def _set_ejecutando(self, activo: bool) -> None:
        self._en_ejecucion = activo
        self._btn_procesar.config(state="disabled" if activo else "normal")
        self._btn_cancelar.config(state="normal" if activo else "disabled")
