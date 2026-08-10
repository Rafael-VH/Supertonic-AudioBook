"""Interfaz de línea de comandos (capa de presentación).

Recibe las dependencias ya inyectadas desde la raíz de composición
(``main.py``): nunca importa ``data/``. La barra de progreso (tqdm) es
responsabilidad de esta capa — es UI, no lógica de negocio.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Callable, List

from domain.entities.archivo import Archivo
from domain.repositories.motor_tts import DEFAULT_SPEED, DEFAULT_TTS_STEPS, DEFAULT_VOICE
from domain.repositories.repositorio_archivos import RepositorioArchivos
from domain.use_cases.formato import FORMATOS_NATIVOS, normalizar_formatos
from domain.use_cases.procesar_archivo import ProcesarArchivo

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

log = logging.getLogger("lector")


def _parse_args() -> argparse.Namespace:
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Convierte archivos en Markdown a audios (wav, flac, ogg, mp3) con voz sintética.",
        epilog="Ejemplo: python main.py --cli --archivo archivo3.md --voz F1 --steps 10 --formato mp3",
    )

    parser.add_argument(
        "--archivo", "-a",
        type=str,
        default=None,
        metavar="ARCHIVO",
        help="Procesar solo un archivo (ej: archivo3.md). Por defecto procesa todos.",
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
    # main.py invoca la CLI con "--cli" en el argv; se registra oculto para que
    # argparse lo acepte sin mostrarlo en la ayuda ni filtrar manualmente argv.
    parser.add_argument("--cli", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()
    try:
        args.formatos = normalizar_formatos(args.formato)
    except ValueError as exc:
        parser.error(str(exc))
    return args


def _configurar_logging(verbose: bool, quiet: bool) -> None:
    """Ajusta el nivel de logging según flags."""
    if quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif verbose:
        logging.getLogger().setLevel(logging.DEBUG)


def main(
    fabrica_use_case: Callable[[str], ProcesarArchivo],
    repositorio: RepositorioArchivos,
) -> None:
    """Punto de entrada de la CLI.

    Args:
        fabrica_use_case: Crea ``ProcesarArchivo`` para una voz dada.
        repositorio: Acceso a los archivos en disco (inyectado).
    """
    args = _parse_args()
    _configurar_logging(args.verbose, args.quiet)

    log.debug("Argumentos recibidos: %s", args)
    log.info("Formatos de salida: %s", ", ".join(args.formatos))

    # Asegurar estructura de carpetas
    repositorio.crear_carpetas_si_no_existen("archivos", "audio")

    # Determinar qué archivos procesar
    if args.archivo:
        ruta = Path("archivos") / args.archivo
        carpeta_archivos = Path("archivos").resolve()
        if not ruta.resolve().is_relative_to(carpeta_archivos):
            log.error("El archivo debe estar dentro de la carpeta 'archivos/'.")
            sys.exit(1)
        if not ruta.exists():
            log.error("El archivo '%s' no existe en la carpeta 'archivos/'.", ruta)
            sys.exit(1)
        archivos = [ruta]
    else:
        archivos = repositorio.listar_archivos_md()
        if not archivos:
            log.info("Creá un archivo .md dentro de 'archivos/' y ejecutá de nuevo.")
            return

    # Use case con el motor ya cableado para la voz pedida
    use_case = fabrica_use_case(args.voz)

    # Procesar cada archivo
    exitos = 0
    errores = 0
    for ruta in archivos:
        ruta_base = Path("audio") / ruta.stem
        cb_progreso, cerrar_barra = _barra_progreso(ruta.stem)
        try:
            use_case.procesar(
                Archivo(ruta),
                ruta_base,
                steps=args.steps,
                speed=args.speed,
                formatos=args.formatos,
                on_progreso=cb_progreso,
            )
            exitos += 1
        except Exception as exc:
            errores += 1
            log.error("Falla al procesar '%s': %s", ruta.name, exc)
        finally:
            cerrar_barra()

    if errores == 0:
        log.info("✅ Todos los archivos procesados con éxito (%d/%d).", exitos, len(archivos))
    else:
        log.warning("Finalizado con advertencias: %d procesado(s) OK, %d error(es).", exitos, errores)


def _barra_progreso(nombre: str) -> Tuple[Callable[[int, int], None], Callable[[], None]]:
    """Devuelve un callback ``on_progreso`` y una función para cerrar la barra tqdm."""
    total_ref: List[int] = [0]
    barra = tqdm(
        total=1,
        desc=f"Sintetizando {nombre}",
        unit="seg",
        ncols=80,
        bar_format="{desc:.30} |{bar}| {n_fmt}/{total_fmt} [{percentage:3.0f}%] {unit}",
    )

    def on_progreso(actual: int, total: int) -> None:
        if total != total_ref[0]:
            barra.total = total
            total_ref[0] = total
        barra.n = actual
        barra.refresh()

    def cerrar() -> None:
        try:
            barra.close()
        except Exception:
            pass

    return on_progreso, cerrar
