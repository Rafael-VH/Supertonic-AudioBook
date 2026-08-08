"""Implementación concreta del exportador de audio con soundfile + numpy.

Satisface el contrato ``ExportadorAudio`` de ``domain/repositories``.
"""

import logging
import struct
from pathlib import Path
from typing import List

import numpy as np
import soundfile as sf

from data.config import SAMPLE_RATE, SUBTIPOS_AUDIO

log = logging.getLogger("lector")


class ExportadorAudioSoundfile:
    """Escritura de archivos de audio en los 4 formatos nativos."""

    def escribir_audio(
        self,
        fragmentos: List[np.ndarray],
        ruta: Path,
        formato: str,
    ) -> None:
        """Concatena fragmentos y los escribe en el formato indicado (ver contrato)."""
        if not fragmentos:
            return
        audio = np.concatenate(fragmentos, dtype=np.float32)
        ruta.parent.mkdir(exist_ok=True)
        sf.write(str(ruta), audio, SAMPLE_RATE, subtype=SUBTIPOS_AUDIO[formato])

    def wav_append(self, fragmentos: List[np.ndarray], ruta: Path) -> None:
        """Concatena fragmentos y los agrega al final de un WAV PCM_16 (ver contrato).

        soundfile no tiene append nativo para WAV, así que se escriben los
        samples crudos (int16 little-endian) al final del archivo y se
        parchea el header RIFF (tamaño de chunk y de datos). Esto permite
        volcar capítulos enormes a disco sin perder lo ya escrito.
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

    def convertir_desde_wav(self, ruta_wav: Path, ruta_destino: Path, formato: str) -> None:
        """Re-encoda un WAV existente al formato indicado (ver contrato)."""
        data, sr = sf.read(str(ruta_wav))
        ruta_destino.parent.mkdir(exist_ok=True)
        sf.write(str(ruta_destino), data, sr, subtype=SUBTIPOS_AUDIO[formato])

    def duracion_audio(self, ruta: Path) -> float:
        """Devuelve la duración de un archivo de audio en segundos (ver contrato).

        Usa ``sf.info`` (lee solo la cabecera) en lugar de ``sf.read`` para
        no cargar el archivo completo en memoria.
        """
        try:
            info = sf.info(str(ruta))
            return float(info.frames / info.samplerate)
        except Exception as exc:
            log.warning("No se pudo leer duración de '%s': %s", ruta, exc)
            return 0.0
