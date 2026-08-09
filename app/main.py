"""
main.py — Punto de entrada y raíz de composición de Supertonic-AudioBook.

Es el ÚNICO lugar que conoce las implementaciones concretas (``data/``)
y las inyecta en la capa de presentación. La presentación y el dominio
nunca importan ``data/``: solo consumen interfaces y casos de uso.

Uso:
    python main.py                  # lanzar la GUI
    python main.py --cli [opciones] # usar la línea de comandos
    python main.py --self-test      # verificar motor + síntesis sin GUI
"""

import sys
from pathlib import Path
from typing import Callable

from data.config import (
    MEMORY_SAFE_MARGIN_BYTES,
    SILENCE_SAMPLES,
    configurar_entorno,
)
from data.repositories.exportador_audio import ExportadorAudioSoundfile
from data.repositories.motor_tts import MotorSupertonic
from data.repositories.repositorio_archivos import RepositorioArchivosLocal
from data.repositories.repositorio_preferencias import PreferenciasJSONLocal
from domain.repositories.motor_tts import MotorTTS
from domain.use_cases.procesar_archivo import ProcesarArchivo
from domain.use_cases.sintetizar_muestra import SintetizarMuestra

CARPETA_BASE = configurar_entorno()


def fabrica_motor(voz: str) -> MotorTTS:
    """Crea el motor de síntesis con la voz pedida."""
    return MotorSupertonic(voz=voz)


def fabrica_muestra(voz: str) -> SintetizarMuestra:
    """Compone el caso de uso de muestra de voz con las implementaciones."""
    return SintetizarMuestra(motor=MotorSupertonic(voz=voz), exportador=ExportadorAudioSoundfile())


def fabrica_use_case(voz: str) -> ProcesarArchivo:
    """Compone un caso de uso completo con las implementaciones concretas."""
    return ProcesarArchivo(
        motor=MotorSupertonic(voz=voz),
        archivos=RepositorioArchivosLocal(),
        exportador=ExportadorAudioSoundfile(),
        silencio_muestras=SILENCE_SAMPLES,
        memoria_safe_margin_bytes=MEMORY_SAFE_MARGIN_BYTES,
    )


def main() -> None:
    if "--self-test" in sys.argv:
        from presentation.self_test import main as self_test_main

        self_test_main(fabrica_motor, ExportadorAudioSoundfile(), CARPETA_BASE)
        return

    if "--cli" in sys.argv:
        from presentation.cli import main as cli_main

        cli_main(fabrica_use_case, RepositorioArchivosLocal())
        return

    from presentation.gui import AppLector

    app = AppLector(
        fabrica_use_case=fabrica_use_case,
        fabrica_muestra=fabrica_muestra,
        repositorio=RepositorioArchivosLocal(),
        carpeta_base=CARPETA_BASE,
        repositorio_preferencias=PreferenciasJSONLocal(CARPETA_BASE / "preferencias.json"),
    )
    app.mainloop()


if __name__ == "__main__":
    main()
