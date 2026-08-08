"""
lector_fanfiction_mejorado.py — Versión mejorada del conversor de capítulos
Markdown a audios WAV con voz sintética.

Mejoras respecto al original:
  - Barra de progreso con tqdm (opcional) para ver el avance en tiempo real
  - Natural sorting para archivos (cap10 va después de cap2)
  - Constantes con nombre (nada de números mágicos)
  - Motor TTS encapsulado en clase (sin global mutable)
  - logging en vez de print (control granular de salida)
  - pathlib en vez de os.path
  - Type hints en todas las funciones
  - CLI con argparse (--capitulo, --voz, --steps, --speed, --formato)
  - Split de oraciones con soporte para español (Dr., Sr., etc.)
  - Validación de voz antes de usar
  - Protección de memoria para libros largos (volcado incremental real)
  - Exportación multi-formato nativa: wav, flac, ogg y mp3 (sin ffmpeg)
  - Manejo de errores en síntesis (no explota en el primer fallo)
  - Docstrings en todas las funciones públicas

Uso:
    python lector_fanfiction_mejorado.py
    python lector_fanfiction_mejorado.py --capitulo capitulo3.md
    python lector_fanfiction_mejorado.py --voz F1 --steps 10
    python lector_fanfiction_mejorado.py --formato mp3
    python lector_fanfiction_mejorado.py --formato wav,mp3,flac
    python lector_fanfiction_mejorado.py --verbose
"""

import argparse
import logging
import os
import re
import struct
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf
from supertonic import TTS

# tqdm es opcional — si no está instalado se cae a un dummy
try:
    from tqdm import tqdm
except ImportError:
    class _DummyTqdm:  # type: ignore[no-redef]
        """Reemplazo mínimo de tqdm cuando no está instalado."""
        def __init__(self, iterable=None, **kwargs):
            self._iterable = iterable or []
        def __iter__(self):
            return iter(self._iterable)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def set_description(self, desc: str) -> None:
            pass
        def update(self, n: int = 1) -> None:
            pass
        def close(self) -> None:
            pass
        @staticmethod
        def write(*args, **kwargs) -> None:
            pass
    tqdm = _DummyTqdm

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
SAMPLE_RATE: int = 44100
"""Frecuencia de muestreo del audio generado (Hz)."""

MAX_CHARS_PER_SEGMENT: int = 1500
"""Máximo de caracteres por fragmento de audio."""

MERGE_THRESHOLD: int = 200
"""Párrafos con menos caracteres que este valor se fusionan con el siguiente."""

SILENCE_DURATION_SECS: float = 0.6
"""Silencio entre fragmentos (segundos)."""

SILENCE_SAMPLES: int = int(SAMPLE_RATE * SILENCE_DURATION_SECS)

DEFAULT_TTS_STEPS: int = 5
"""Pasos de inferencia del modelo TTS (más = mejor calidad, más lento)."""

DEFAULT_SPEED: float = 1.1
"""Velocidad de habla (1.0 = normal)."""

DEFAULT_VOICE: str = "M1"
"""Voz por defecto."""

FORMATOS_NATIVOS: Tuple[str, ...] = ("wav", "flac", "ogg", "mp3")
"""Formatos de salida soportados de forma nativa por soundfile (sin ffmpeg)."""

SUBTIPOS_AUDIO: Dict[str, str] = {
    "wav": "PCM_16",
    "flac": "PCM_16",
    "ogg": "VORBIS",
    "mp3": "MPEG_LAYER_III",
}
"""Subtipo soundfile correspondiente a cada formato de salida."""

MEMORY_SAFE_MARGIN_BYTES: int = 500 * 1024 * 1024
"""Si los fragmentos acumulados superan este tamaño, se escriben parcialmente
para evitar quedarse sin RAM (~500 MB)."""

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("lector")


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------

def crear_carpetas_si_no_existen(*carpetas: str) -> None:
    """Crea las carpetas indicadas si no existen.

    Args:
        *carpetas: Nombres de carpeta a crear (ej: 'fanfic', 'audio').
    """
    for nombre in carpetas:
        Path(nombre).mkdir(exist_ok=True)
        log.info("Carpeta asegurada: %s/", nombre)


def normalizar_formatos(cadena: str) -> List[str]:
    """Normaliza una lista de formatos separada por comas.

    Convierte a minúsculas, elimina espacios, ignora duplicados y
    conserva el orden de aparición. Lanza ``ValueError`` si algún
    formato no está soportado.

    Args:
        cadena: Texto del argumento ``--formato`` (ej: "wav,MP3").

    Returns:
        Lista de formatos válidos y únicos.

    Raises:
        ValueError: Si hay un formato desconocido.
    """
    formatos: List[str] = []
    for token in cadena.split(","):
        formato = token.strip().lower()
        if not formato:
            continue
        if formato not in FORMATOS_NATIVOS:
            raise ValueError(
                f"Formato no soportado: '{formato}'. "
                f"Válidos: {', '.join(FORMATOS_NATIVOS)}."
            )
        if formato not in formatos:
            formatos.append(formato)
    return formatos


def listar_archivos_md(carpeta: str = "fanfic") -> List[Path]:
    """Busca archivos .md en la carpeta y los ordena numéricamente.

    Usa ordenamiento natural: capitulo2.md va antes que capitulo10.md.

    Args:
        carpeta: Directorio donde buscar.

    Returns:
        Lista de objetos Path ordenados.
    """
    ruta = Path(carpeta)
    if not ruta.exists():
        log.warning("La carpeta '%s/' no existe.", carpeta)
        return []

    archivos = sorted(
        [f for f in ruta.iterdir() if f.suffix.lower() == ".md"],
        key=_natural_sort_key,
    )

    if not archivos:
        log.warning("No se encontraron archivos .md en '%s/'.", carpeta)
    else:
        log.info(
            "Detectados %d capítulo(s): %s",
            len(archivos),
            ", ".join(p.name for p in archivos),
        )

    return archivos


def _natural_sort_key(path: Path) -> Tuple[int, ...]:
    """Genera clave de ordenamiento numérico-natural para un Path.

    Extrae todos los números del nombre del archivo y los usa como clave.
    Si no encuentra números, usa el nombre completo como string.

    Ejemplos:
        capitulo2.md  → (2,)
        capitulo10.md → (10,)
        epilogo.md    → ('epilogo.md',)  ← orden alfabético
    """
    numeros = re.findall(r"\d+", path.stem)
    if numeros:
        return tuple(int(n) for n in numeros)
    return (path.stem,)  # type: ignore[return-value]


def limpiar_markdown(texto: str) -> str:
    """Elimina toda la sintaxis Markdown y devuelve texto plano legible.

    Soporta: títulos, negrita/cursiva, inline code, links, imágenes,
    blockquotes, listas, líneas horizontales, y bloques de código.

    Args:
        texto: Texto con formato Markdown.

    Returns:
        Texto plano, sin formato, con saltos de línea normalizados.
    """
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", texto)
    texto = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", texto)
    texto = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", texto)
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r">\s?", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"[-*+]\s", "", texto)
    texto = re.sub(r"---|\*\*\*", "", texto)
    texto = re.sub(r"~~~.*?~~~", "", texto, flags=re.DOTALL)
    texto = re.sub(r"```.*?```", "", texto, flags=re.DOTALL)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


_ABREVIATURAS: Tuple[str, ...] = (
    "Dr", "Dra", "Sr", "Sra", "Sta", "Sto", "etc", "i.e", "e.g", "vs",
    "Lic", "Ing", "Mtro", "Mtra", "Prof", "Gral",
)
"""Abreviaturas cuyo punto no debe interpretarse como fin de oración."""

def _dividir_en_oraciones(texto: str) -> List[str]:
    """Divide texto en oraciones respetando abreviaturas del español.

    Python ``re`` no permite lookbehind de ancho variable, así que en vez
    de un patrón con alternancia de largos distintos (que crashea con
    ``re.error``), se protegen temporalmente los puntos de las
    abreviaturas con un carácter neutro, se parte por ``. `` y se
    restauran los puntos.

    Args:
        texto: Párrafo a dividir.

    Returns:
        Lista de oraciones (sin el punto de cierre).
    """
    protegido = texto
    for abr in _ABREVIATURAS:
        protegido = protegido.replace(abr + ".", abr + "\x00")
    subfrases = re.split(r"(?<=\.)\s+", protegido)
    return [f.replace("\x00", ".") for f in subfrases]


def segmentar_texto(texto_plano: str) -> List[str]:
    """Divide texto plano en segmentos aptos para el TTS.

    Estrategia:
    1. Divide por saltos de línea (párrafos).
    2. Fusiona párrafos cortos (< MERGE_THRESHOLD) con el siguiente,
       siempre que no excedan MAX_CHARS_PER_SEGMENT.
    3. Si un segmento excede el límite, lo parte por oraciones
       (split en ". "), manejando correctamente títulos como Dr., Sr., etc.

    Args:
        texto_plano: Texto sin formato Markdown.

    Returns:
        Lista de strings, cada uno listo para sintetizar.
    """
    parrafos = [p.strip() for p in texto_plano.split("\n") if p.strip()]

    # --- 1. Fusión de párrafos cortos ---
    fusionados: List[str] = []
    buffer = ""
    for p in parrafos:
        if not buffer:
            buffer = p
        elif len(buffer) + len(p) < MAX_CHARS_PER_SEGMENT and len(p) < MERGE_THRESHOLD:
            buffer += " " + p
        else:
            fusionados.append(buffer)
            buffer = p
    if buffer:
        fusionados.append(buffer)

    # --- 2. División de párrafos largos ---
    resultado: List[str] = []
    for p in fusionados:
        if len(p) <= MAX_CHARS_PER_SEGMENT:
            resultado.append(p)
            continue

        # Split por ". " protegiendo abreviaturas españolas
        subfrases = _dividir_en_oraciones(p)
        buffer_frase = ""
        for frase in subfrases:
            if len(buffer_frase) + len(frase) + 2 <= MAX_CHARS_PER_SEGMENT:
                buffer_frase += frase + ". "
            else:
                resultado.append(buffer_frase.strip())
                buffer_frase = frase + ". "
        if buffer_frase:
            resultado.append(buffer_frase.strip())

    return resultado


# ---------------------------------------------------------------------------
# Motor TTS encapsulado
# ---------------------------------------------------------------------------

class MotorTTS:
    """Wrapper alrededor de ``supertonic.TTS`` con inicialización lazy.

    En lugar de usar una variable global mutable (como hacía el original),
    esto encapsula el engine y su estilo, y solo inicializa cuando se
    necesita realmente.
    """

    def __init__(self, voz: str = DEFAULT_VOICE) -> None:
        """Args:
            voz: Identificador de la voz a usar (ej: 'M1', 'F1').
        """
        self._voz = voz
        self._engine: Optional[TTS] = None
        self._style = None

    def _asegurar_inicializado(self) -> None:
        """Inicializa el engine TTS si es la primera vez que se usa."""
        if self._engine is not None:
            return
        log.info("Inicializando motor Supertonic (voz=%s)...", self._voz)
        self._engine = TTS(auto_download=True)

        # Validar que la voz pedida existe
        try:
            self._style = self._engine.get_voice_style(voice_name=self._voz)
        except Exception as exc:
            raise ValueError(
                f"La voz '{self._voz}' no está disponible. "
                f"Verificá las voces instaladas con engine.list_voices()."
            ) from exc

        log.info("Motor listo con voz '%s'.", self._voz)

    @property
    def engine(self) -> TTS:
        """Acceso al engine subyacente (inicialización lazy)."""
        self._asegurar_inicializado()
        assert self._engine is not None
        return self._engine

    @property
    def style(self):
        """Estilo de voz asociado a la voz seleccionada."""
        self._asegurar_inicializado()
        return self._style

    def sintetizar(
        self,
        texto: str,
        steps: int = DEFAULT_TTS_STEPS,
        speed: float = DEFAULT_SPEED,
    ) -> np.ndarray:
        """Convierte texto a audio.

        Args:
            texto: Texto a sintetizar.
            steps: Pasos de inferencia (más = mejor calidad).
            speed: Velocidad de habla.

        Returns:
            Array numpy 1D de float32 con las muestras de audio.
            Vacío si no se generó audio.
        """
        try:
            wav, _ = self.engine.synthesize(
                texto,
                voice_style=self.style,
                lang="es",
                total_steps=steps,
                speed=speed,
            )
        except Exception as exc:
            log.error("Error sintetizando texto (%.60s...): %s", texto, exc)
            return np.array([], dtype=np.float32)

        if wav.size == 0:
            log.warning("Fragmento silencioso (0 muestras). Se omite.")
            return np.array([], dtype=np.float32)

        return np.atleast_1d(wav.squeeze()).astype(np.float32)


# ---------------------------------------------------------------------------
# Procesamiento de capítulos
# ---------------------------------------------------------------------------

def procesar_capitulo(
    ruta_entrada: Path,
    ruta_base: Path,
    motor: MotorTTS,
    *,
    steps: int = DEFAULT_TTS_STEPS,
    speed: float = DEFAULT_SPEED,
    formatos: List[str],
    on_progreso: Optional[Callable[[int, int], None]] = None,
    debe_detenerse: Optional[Callable[[], bool]] = None,
) -> None:
    """Convierte un archivo Markdown en audios en los formatos pedidos.

    Lee el archivo, limpia el Markdown, segmenta el texto en fragmentos
    aptos para TTS, sintetiza cada uno, y exporta el audio final a cada
    formato solicitado (wav, flac, ogg, mp3).

    Args:
        ruta_entrada: Ruta al archivo .md de entrada.
        ruta_base: Ruta de salida sin extensión (ej: ``audio/capitulo``).
        motor: Instancia de MotorTTS ya configurada.
        steps: Pasos de inferencia para el TTS.
        speed: Velocidad de habla.
        formatos: Formatos de salida (lista normalizada).
        on_progreso: Callback ``(procesados, total)`` invocado por cada
            segmento procesado. Pensado para UI (la GUI lo llama desde
            otro hilo, ojo con thread-safety).
        debe_detenerse: Callback que, si devuelve ``True``, aborta la
            síntesis entre segmentos y exporta lo generado hasta el
            momento.
    """
    log.info("=" * 50)
    log.info("  Procesando: %s", ruta_entrada.name)
    log.info("=" * 50)

    # --- Leer y limpiar ---
    log.info("Leyendo y limpiando Markdown...")
    try:
        texto_plano = limpiar_markdown(ruta_entrada.read_text(encoding="utf-8"))
    except Exception as exc:
        log.error("No se pudo leer '%s': %s", ruta_entrada, exc)
        return

    if not texto_plano.strip():
        log.warning("El archivo está vacío después de limpiar. Se omite.")
        return

    # --- Segmentar ---
    segmentos = segmentar_texto(texto_plano)
    total = len(segmentos)
    log.info("  → %d segmento(s) para procesar.", total)

    # WAV de trabajo: es el destino final si 'wav' está pedido; si no, un
    # temporal que sirve de fuente intermedia y se borra al terminar.
    usando_wav = "wav" in formatos
    if usando_wav:
        ruta_wav_trabajo = ruta_base.with_suffix(".wav")
    else:
        fd, tmp = tempfile.mkstemp(suffix=".wav", dir=str(ruta_base.parent))
        os.close(fd)
        ruta_wav_trabajo = Path(tmp)

    # --- Sintetizar incrementalmente ---
    log.info("Generando voz sintética...")
    fragmentos: List[np.ndarray] = []
    memoria_acumulada = 0
    parcial_escrito = False
    cancelado = False

    try:
        with tqdm(
            iterable=segmentos,
            desc=f"Sintetizando {ruta_entrada.stem}",
            unit="seg",
            total=total,
            ncols=80,
            bar_format="{desc:.30} |{bar}| {n_fmt}/{total_fmt} [{percentage:3.0f}%] {unit}",
        ) as barra:
            procesados = 0
            for texto in barra:
                procesados += 1
                if debe_detenerse is not None and debe_detenerse():
                    cancelado = True
                    break

                wav = motor.sintetizar(texto, steps=steps, speed=speed)
                if on_progreso is not None:
                    on_progreso(procesados, total)
                if wav.size == 0:
                    barra.set_description(
                        f"Sintetizando {ruta_entrada.stem} (↓ fragmento vacío)"
                    )
                    continue

                fragmentos.append(wav)
                memoria_acumulada += wav.nbytes
                fragmentos.append(np.zeros(SILENCE_SAMPLES, dtype=np.float32))
                memoria_acumulada += SILENCE_SAMPLES * np.dtype(np.float32).itemsize

                # Si estamos acumulando mucha RAM, volcamos a disco
                if memoria_acumulada > MEMORY_SAFE_MARGIN_BYTES:
                    barra.set_description(
                        f"Sintetizando {ruta_entrada.stem} (volcando a disco...)"
                    )
                    _wav_append(fragmentos, ruta_wav_trabajo)
                    fragmentos.clear()
                    memoria_acumulada = 0
                    parcial_escrito = True
                    barra.set_description(
                        f"Sintetizando {ruta_entrada.stem}"
                    )

        if cancelado:
            log.warning("Cancelado por el usuario. Exportando lo generado hasta ahora...")

        if not fragmentos and not parcial_escrito:
            log.error("No se generó ningún fragmento de audio.")
            return

        # --- Exportar ---
        log.info("Exportando audio...")
        if parcial_escrito:
            _wav_append(fragmentos, ruta_wav_trabajo)
            if not usando_wav:
                for formato in formatos:
                    _convertir_desde_wav(
                        ruta_wav_trabajo,
                        ruta_base.with_suffix("." + formato),
                        formato,
                    )
            else:
                for formato in formatos:
                    if formato == "wav":
                        continue
                    _convertir_desde_wav(
                        ruta_wav_trabajo,
                        ruta_base.with_suffix("." + formato),
                        formato,
                    )
        else:
            for formato in formatos:
                _escribir_audio(
                    fragmentos,
                    ruta_base.with_suffix("." + formato),
                    formato,
                )
    finally:
        if not usando_wav and ruta_wav_trabajo.exists():
            ruta_wav_trabajo.unlink()

    for formato in formatos:
        ruta = ruta_base.with_suffix("." + formato)
        duracion = _duracion_audio(ruta)
        log.info("  + %s (%s): %.1f s", ruta.name, formato.upper(), duracion)


def _escribir_audio(
    fragmentos: List[np.ndarray],
    ruta: Path,
    formato: str,
) -> None:
    """Concatena fragmentos y los escribe en el formato indicado.

    Args:
        fragmentos: Lista de arrays de audio (float32, mono).
        ruta: Ruta de salida (con extensión del formato).
        formato: Uno de FORMATOS_NATIVOS.
    """
    if not fragmentos:
        return
    audio = np.concatenate(fragmentos, dtype=np.float32)
    ruta.parent.mkdir(exist_ok=True)
    sf.write(str(ruta), audio, SAMPLE_RATE, subtype=SUBTIPOS_AUDIO[formato])


def _wav_append(fragmentos: List[np.ndarray], ruta: Path) -> None:
    """Concatena fragmentos y los agrega al final de un WAV PCM_16.

    soundfile no tiene append nativo para WAV, así que se escriben los
    samples crudos (int16 little-endian) al final del archivo y se
    parchea el header RIFF (tamaño de chunk y de datos). Esto permite
    volcar capítulos enormes a disco sin perder lo ya escrito.

    Args:
        fragmentos: Lista de arrays de audio (float32, mono).
        ruta: Ruta al WAV destino (se crea si no existe).
    """
    if not fragmentos:
        return
    audio = np.concatenate(fragmentos, dtype=np.float32)
    pcm16 = np.clip(audio, -1.0, 1.0)
    pcm16 = (pcm16 * 32767.0).astype(np.int16)
    ruta.parent.mkdir(exist_ok=True)

    if not ruta.exists() or ruta.stat().st_size == 0:
        sf.write(str(ruta), pcm16, SAMPLE_RATE, subtype="PCM_16")
        return

    with ruta.open("ab") as f:
        f.write(pcm16.tobytes())

    tamaño = ruta.stat().st_size
    with ruta.open("r+b") as f:
        f.seek(4)
        f.write(struct.pack("<I", tamaño - 8))
        f.seek(40)
        f.write(struct.pack("<I", tamaño - 44))


def _convertir_desde_wav(ruta_wav: Path, ruta_destino: Path, formato: str) -> None:
    """Re-encoda un WAV existente al formato indicado.

    Args:
        ruta_wav: WAV fuente en disco.
        ruta_destino: Ruta de salida (con extensión del formato).
        formato: Uno de FORMATOS_NATIVOS.
    """
    data, sr = sf.read(str(ruta_wav))
    ruta_destino.parent.mkdir(exist_ok=True)
    sf.write(str(ruta_destino), data, sr, subtype=SUBTIPOS_AUDIO[formato])


def _duracion_audio(ruta: Path) -> float:
    """Devuelve la duración de un archivo de audio en segundos.

    Usa ``sf.info`` (lee solo la cabecera) en lugar de ``sf.read`` para
    no cargar el archivo completo en memoria.

    Args:
        ruta: Ruta al archivo de audio.

    Returns:
        Duración en segundos, 0.0 si no se puede leer.
    """
    try:
        info = sf.info(str(ruta))
        return float(info.frames / info.samplerate)
    except Exception as exc:
        log.warning("No se pudo leer duración de '%s': %s", ruta, exc)
        return 0.0


# ---------------------------------------------------------------------------
# Interfaz de línea de comandos
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Convierte capítulos en Markdown a audios (wav, flac, ogg, mp3) con voz sintética.",
        epilog="Ejemplo: python lector_fanfiction_mejorado.py --capitulo cap3.md --voz F1 --steps 10 --formato mp3",
    )

    parser.add_argument(
        "--capitulo", "-c",
        type=str,
        default=None,
        metavar="ARCHIVO",
        help="Procesar solo un capítulo (ej: capitulo3.md). Por defecto procesa todos.",
    )
    parser.add_argument(
        "--voz", "-v",
        type=str,
        default=DEFAULT_VOICE,
        help=f"Voz a usar (default: {DEFAULT_VOICE}).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=DEFAULT_TTS_STEPS,
        help=f"Pasos de inferencia del TTS (default: {DEFAULT_TTS_STEPS}).",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=DEFAULT_SPEED,
        help=f"Velocidad de habla (default: {DEFAULT_SPEED}).",
    )
    parser.add_argument(
        "--formato", "-f",
        type=str,
        default="wav",
        metavar="FORMATOS",
        help=(
            "Formato(s) de salida separados por coma "
            f"(default: wav). Válidos: {', '.join(FORMATOS_NATIVOS)}."
        ),
    )
    parser.add_argument(
        "--verbose", "-V",
        action="store_true",
        help="Modo verbose (logging DEBUG). Muestra todo.",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Modo silencioso (solo warnings y errores).",
    )

    args = parser.parse_args()
    try:
        args.formatos = normalizar_formatos(args.formato)
    except ValueError as exc:
        parser.error(str(exc))
    return args


def _configurar_logging(verbose: bool, quiet: bool) -> None:
    """Ajusta el nivel de logging según flags.

    Args:
        verbose: Si True, DEBUG.
        quiet: Si True, solo WARNING.
    """
    if quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif verbose:
        logging.getLogger().setLevel(logging.DEBUG)


def main() -> None:
    """Punto de entrada principal."""
    args = _parse_args()
    _configurar_logging(args.verbose, args.quiet)

    log.debug("Argumentos recibidos: %s", args)
    log.info("Formatos de salida: %s", ", ".join(args.formatos))

    # Asegurar estructura de carpetas
    crear_carpetas_si_no_existen("fanfic", "audio")

    # Determinar qué archivos procesar
    if args.capitulo:
        ruta = Path("fanfic") / args.capitulo
        if not ruta.exists():
            log.error("El archivo '%s' no existe en la carpeta 'fanfic/'.", ruta)
            sys.exit(1)
        archivos = [ruta]
    else:
        archivos = listar_archivos_md()
        if not archivos:
            log.info("Creá un archivo .md dentro de 'fanfic/' y ejecutá de nuevo.")
            return

    # Inicializar motor TTS (una sola vez para todos los capítulos)
    try:
        motor = MotorTTS(voz=args.voz)
    except ValueError as exc:
        log.error(exc)
        sys.exit(1)

    # Procesar cada capítulo
    for ruta in archivos:
        ruta_base = Path("audio") / ruta.stem
        procesar_capitulo(
            ruta,
            ruta_base,
            motor,
            steps=args.steps,
            speed=args.speed,
            formatos=args.formatos,
        )

    log.info("✅ Todos los capítulos procesados.")


if __name__ == "__main__":
    main()
