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
        parchea dinámicamente el header RIFF (localizando el chunk 'data'). Esto
        permite volcar archivos enormes a disco sin perder lo ya escrito.
        """
        if not fragmentos:
            return
        audio = np.concatenate(fragmentos, dtype=np.float32)
        pcm16 = np.clip(audio, -1.0, 1.0)
        pcm16 = (pcm16 * 32767.0).astype("<i2")
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
            f.seek(12)  # Pasado RIFF header ('RIFFxxxxWAVE')
            while True:
                cabecera_chunk = f.read(8)
                if len(cabecera_chunk) < 8:
                    break
                chunk_id, chunk_size = struct.unpack("<4sI", cabecera_chunk)
                if chunk_id == b"data":
                    pos_size = f.tell() - 4
                    data_offset = f.tell()
                    nuevo_tamaño_data = tamaño - data_offset
                    f.seek(pos_size)
                    f.write(struct.pack("<I", nuevo_tamaño_data))
                    break
                # Saltar payload del chunk (con alineación par)
                offset_salto = chunk_size + (chunk_size % 2)
                f.seek(offset_salto, 1)

    def convertir_desde_wav(self, ruta_wav: Path, ruta_destino: Path, formato: str) -> None:
        """Re-encoda un WAV existente al formato indicado de forma eficiente en RAM.

        Lee y escribe en bloques (chunks) usando ``sf.SoundFile`` para no
        cargar el archivo WAV completo en memoria RAM.
        """
        ruta_destino.parent.mkdir(exist_ok=True)
        fmt_key = formato.lower()
        subtype = SUBTIPOS_AUDIO.get(fmt_key)
        with sf.SoundFile(str(ruta_wav), mode="r") as f_in:
            sr = f_in.samplerate
            channels = f_in.channels
            with sf.SoundFile(
                str(ruta_destino),
                mode="w",
                samplerate=sr,
                channels=channels,
                subtype=subtype,
            ) as f_out:
                for block in f_in.blocks(blocksize=65536, dtype="float32"):
                    f_out.write(block)

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
