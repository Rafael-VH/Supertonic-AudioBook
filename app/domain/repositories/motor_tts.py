"""Contrato del motor de síntesis de voz (capa de dominio).

Define la interfaz que los casos de uso consumen. La implementación
concreta (que envuelve el SDK de Supertonic) vive en ``data/``.
"""

from typing import Protocol

import numpy as np

DEFAULT_VOICE: str = "M1"
"""Voz por defecto del producto."""

DEFAULT_TTS_STEPS: int = 5
"""Pasos de inferencia del modelo TTS (más = mejor calidad, más lento)."""

DEFAULT_SPEED: float = 1.1
"""Velocidad de habla (1.0 = normal)."""


class MotorTTS(Protocol):
    """Abstracción del motor de síntesis de voz.

    La capa de dominio define SOLO la firma; nada de lo que el dominio
    conozca puede depender de Supertonic o de implementaciones concretas.
    """

    def sintetizar(
        self,
        texto: str,
        *,
        steps: int,
        speed: float,
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
        ...
