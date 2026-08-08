"""Self-test de la app (capa de presentación).

Verifica el motor de síntesis y la escritura de audio sin abrir la
ventana. Pensado para probar el ejecutable empaquetado.
"""

import sys
from pathlib import Path
from typing import Callable

import numpy as np

from domain.repositories.motor_tts import DEFAULT_SPEED, DEFAULT_TTS_STEPS, DEFAULT_VOICE
from domain.repositories.exportador_audio import ExportadorAudio


def self_test(
    fabrica_motor: Callable[[str], "object"],
    exportador: ExportadorAudio,
    carpeta_base: Path,
) -> int:
    """Verifica motor + síntesis sin abrir la ventana.

    Args:
        fabrica_motor: Crea el motor para una voz dada.
        exportador: Escritura de audio (inyectado).
        carpeta_base: Carpeta base de la app.

    Returns:
        0 si OK, 1 si falló.
    """
    try:
        motor = fabrica_motor(DEFAULT_VOICE)
        wav: np.ndarray = motor.sintetizar(
            "Prueba de síntesis del motor Supertonic.",
            steps=DEFAULT_TTS_STEPS,
            speed=DEFAULT_SPEED,
        )
        if wav.size == 0:
            print("SELF-TEST FAIL: no se generó audio.")
            return 1
        salida = carpeta_base / "audio" / "_self_test.wav"
        salida.parent.mkdir(exist_ok=True)
        exportador.escribir_audio([wav], salida, "wav")
        duracion = exportador.duracion_audio(salida)
        print(
            f"SELF-TEST OK voz={DEFAULT_VOICE} muestras={wav.size} "
            f"duracion={duracion:.1f}s salida={salida}"
        )
        return 0
    except Exception as exc:
        print(f"SELF-TEST FAIL: {exc}")
        return 1


def main(fabrica_motor: Callable[[str], "object"], exportador: ExportadorAudio, carpeta_base: Path) -> None:
    """Entry point del self-test: ejecuta y sale con el código correspondiente."""
    sys.exit(self_test(fabrica_motor, exportador, carpeta_base))
