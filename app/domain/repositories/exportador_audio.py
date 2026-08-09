"""Contrato del exportador de audio (capa de dominio).

Abstrae la escritura de audio a disco. La implementación concreta
(soundfile + numpy) vive en ``data/``.
"""

from pathlib import Path
from typing import List, Protocol

import numpy as np


class ExportadorAudio(Protocol):
    """Escritura de archivos de audio en múltiples formatos."""

    def escribir_audio(
        self,
        fragmentos: List[np.ndarray],
        ruta: Path,
        formato: str,
    ) -> None:
        """Concatena fragmentos y los escribe en el formato indicado.

        Args:
            fragmentos: Lista de arrays de audio (float32, mono).
            ruta: Ruta de salida (con extensión del formato).
            formato: Uno de los formatos nativos soportados.
        """
        ...

    def wav_append(self, fragmentos: List[np.ndarray], ruta: Path) -> None:
        """Agrega fragmentos al final de un WAV PCM_16 existente.

        Se usa para volcar a disco archivos enormes sin perder lo ya
        escrito (protección de memoria).

        Args:
            fragmentos: Lista de arrays de audio (float32, mono).
            ruta: Ruta al WAV destino (se crea si no existe).
        """
        ...

    def convertir_desde_wav(self, ruta_wav: Path, ruta_destino: Path, formato: str) -> None:
        """Re-encoda un WAV existente al formato indicado.

        Args:
            ruta_wav: WAV fuente en disco.
            ruta_destino: Ruta de salida (con extensión del formato).
            formato: Uno de los formatos nativos soportados.
        """
        ...

    def duracion_audio(self, ruta: Path) -> float:
        """Devuelve la duración de un archivo de audio en segundos.

        Args:
            ruta: Ruta al archivo de audio.

        Returns:
            Duración en segundos, 0.0 si no se puede leer.
        """
        ...
