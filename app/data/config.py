"""Configuración técnica de la capa de datos.

Constantes del mundo del audio y valores por defecto de ejecución.
La lógica de negocio (reglas) vive en ``domain/``; acá solo lo técnico.
"""

import os
import sys
from pathlib import Path
from typing import Dict

SAMPLE_RATE: int = 44100
"""Frecuencia de muestreo del audio generado (Hz)."""

SILENCE_DURATION_SECS: float = 0.6
"""Silencio entre fragmentos (segundos)."""

SILENCE_SAMPLES: int = int(SAMPLE_RATE * SILENCE_DURATION_SECS)

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


def _carpeta_base() -> Path:
    """Carpeta base de la app: junto al exe si está empaquetada, si no la app."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _carpeta_modelo() -> Path:
    """Carpeta canónica del modelo TTS.

    - Empaquetado (``sys.frozen``): junto al .exe (``base/modelo``), para que
      el portable funcione offline y las descargas queden junto a la app.
    - En desarrollo: ``resource/modelo`` en la raíz del proyecto, que es la
      fuente de verdad que los builds copian al dist. Así un rebuild de
      PyInstaller (que borra ``app/dist``) no pierde el modelo descargado.
    """
    if getattr(sys, "frozen", False):
        return _carpeta_base() / "modelo"
    return _carpeta_base().parent / "resource" / "modelo"


def configurar_entorno() -> Path:
    """Apuntar la caché del modelo TTS a la carpeta local correspondiente.

    Se llama antes de instanciar el motor. Devuelve la carpeta base.
    """
    base = _carpeta_base()
    os.environ.setdefault("SUPERTONIC_CACHE_DIR", str(_carpeta_modelo()))
    return base
